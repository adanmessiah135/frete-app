from flask import Flask, render_template, request, redirect, url_for, send_file
from decimal import Decimal
import psycopg2
import psycopg2.extras
from datetime import datetime
import os

app = Flask(__name__)

# Constante para a origem fixa
ORIGEM_FIXA = "bebedouro"

# Conexão com o banco de dados
def conectar_bd():
    # Configuração para o banco local
    return psycopg2.connect(
        dbname="frete_db",
        user="frete_user",
        password="ad1ro2ar3",
        host="localhost",
        port="5432"
    )

# Carregar cidades disponíveis
def carregar_cidades():
    try:
        with conectar_bd() as mydb:
            with mydb.cursor(cursor_factory=psycopg2.extras.DictCursor) as mycursor:
                mycursor.execute("""
                    SELECT DISTINCT destino
                    FROM frete
                    WHERE origem = %s
                """, (ORIGEM_FIXA.upper(),))
                cidades_data = mycursor.fetchall()
                if not cidades_data:
                    print("Nenhuma cidade encontrada na tabela frete para origem =", ORIGEM_FIXA)
                    return []
                cidades = [row["destino"].strip().lower() for row in cidades_data]
                print(f"Cidades carregadas: {cidades}")  # Depuração
                return cidades
    except Exception as e:
        print(f"Erro ao carregar cidades: {str(e)}")
        return []

# Carregar tarifas e pesos mínimos
def carregar_tarifas_e_pesos_minimos():
    try:
        with conectar_bd() as mydb:
            with mydb.cursor(cursor_factory=psycopg2.extras.DictCursor) as mycursor:
                mycursor.execute("""
                    SELECT f.destino, f.tarifa, f.id_veiculo
                    FROM frete f
                    WHERE f.origem = %s
                """, (ORIGEM_FIXA.upper(),))
                tarifas_data = mycursor.fetchall()
                
                tarifas = {row["destino"].strip().lower(): Decimal(str(row["tarifa"])) for row in tarifas_data}
                id_veiculos = {row["destino"].strip().lower(): row["id_veiculo"] for row in tarifas_data}
                
                pesos_minimos = {}
                for destino, id_veiculo in id_veiculos.items():
                    if id_veiculo is not None:
                        mycursor.execute("SELECT peso_minimo FROM tipos_veiculo WHERE id = %s", (id_veiculo,))
                        peso_minimo = mycursor.fetchone()
                        if peso_minimo:
                            pesos_minimos[destino] = Decimal(str(peso_minimo["peso_minimo"]))
                        else:
                            pesos_minimos[destino] = Decimal('0.0')
                    else:
                        pesos_minimos[destino] = Decimal('0.0')
                return tarifas, pesos_minimos
    except Exception as e:
        print(f"Erro ao carregar tarifas e pesos mínimos: {str(e)}")
        return {}, {}

# Função para calcular o frete
def calcular_frete(cidades, pesos, valores_produtos, num_entregas):
    tarifas, pesos_minimos = carregar_tarifas_e_pesos_minimos()
    cidades_validas = [cidade.strip().lower() for cidade in cidades]
    
    tarifas_encontradas = [tarifas[cidade] for cidade in cidades_validas if cidade in tarifas]
    cidades_sem_tarifa = [cidade for cidade in cidades_validas if cidade not in tarifas]
    
    if cidades_sem_tarifa:
        raise ValueError(f"Cidades sem tarifa cadastrada: {', '.join(cidades_sem_tarifa)}")
    if not tarifas_encontradas:
        raise ValueError("Nenhuma das cidades informadas possui tarifa cadastrada.")
    
    maior_frete = max(tarifas_encontradas)
    destino_maior_frete = next(cidade for cidade in cidades_validas if cidade in tarifas and tarifas[cidade] == maior_frete)
    peso_minimo = pesos_minimos.get(destino_maior_frete, Decimal('0.0'))
    
    peso_total = sum(Decimal(str(peso)) for peso in pesos)
    peso_usado = peso_total if peso_total >= peso_minimo else peso_minimo
    
    valor_total_frete = maior_frete * peso_usado
    
    acrescimo = Decimal("1.05") if num_entregas > 2 else Decimal("1.0")
    valor_total_frete *= acrescimo
    
    valor_total_produtos = sum(Decimal(str(valor)) for valor in valores_produtos)
    gris_total = valor_total_produtos * Decimal('0.00002')
    valor_total_frete += gris_total
    valor_total_frete = valor_total_frete.quantize(Decimal('0.01'))
    
    fretes_desmembrados = []
    soma_fretes_desmembrados = Decimal('0.0')
    
    for i, (cidade, peso, valor_produto) in enumerate(zip(cidades_validas, pesos, valores_produtos)):
        peso = Decimal(str(peso))
        valor_produto = Decimal(str(valor_produto))
        
        tarifa_usada = maior_frete
        
        proporcao_peso = peso / peso_total if peso_total > 0 else Decimal('0.0')
        peso_proporcional = proporcao_peso * peso_usado
        
        valor_frete_cidade = tarifa_usada * peso_proporcional
        valor_frete_cidade *= acrescimo
        
        proporcao_valor = valor_produto / valor_total_produtos if valor_total_produtos > 0 else Decimal('0.0')
        gris_cidade = gris_total * proporcao_valor
        
        valor_frete_cidade += gris_cidade
        valor_frete_cidade = valor_frete_cidade.quantize(Decimal('0.01'))
        
        soma_fretes_desmembrados += valor_frete_cidade
        
        fretes_desmembrados.append({
            'cidade': cidade,
            'tarifa': tarifa_usada,
            'peso': peso,
            'valor_produto': valor_produto,
            'valor_frete': valor_frete_cidade
        })
    
    if fretes_desmembrados:
        diferenca = valor_total_frete - soma_fretes_desmembrados
        fretes_desmembrados[-1]['valor_frete'] += diferenca
    
    return maior_frete, peso_usado, valor_total_frete, peso_minimo, valor_total_produtos, gris_total, fretes_desmembrados

# Função para salvar os dados na tabela viagens
def salvar_viagem(data_viagem, cte, cidades, nfs, peso_total, valor_frete, placa, dt, tipo):
    try:
        with conectar_bd() as mydb:
            with mydb.cursor() as mycursor:
                sql = """
                    INSERT INTO viagens (data_viagem, cte, cidades, nfs, peso_total, valor_frete, placa, dt, tipo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                valores = (data_viagem, cte, cidades, nfs, peso_total, valor_frete, placa, dt, tipo)
                mycursor.execute(sql, valores)
                mydb.commit()
    except Exception as e:
        print(f"Erro ao salvar viagem: {str(e)}")
        raise

# Rota para a página inicial
@app.route('/', methods=['GET', 'POST'])
def index():
    cidades_disponiveis = carregar_cidades()  # Carregar as cidades disponíveis
    if request.method == 'POST':
        try:
            num_cidades = int(request.form['num_cidades'])
            cidades = []
            pesos = []
            valores = []
            for i in range(num_cidades):
                cidade = request.form[f'cidade_{i}']
                peso = request.form[f'peso_{i}']
                valor = request.form[f'valor_{i}']
                if not cidade or not peso or not valor:
                    raise ValueError("Todos os campos devem ser preenchidos.")
                cidades.append(cidade)
                pesos.append(float(peso))
                valores.append(float(valor))
            
            num_entregas = int(request.form['num_entregas'])
            
            # Dados adicionais
            data_viagem = request.form['data_viagem']
            cte = request.form['cte']
            nfs = request.form['nfs']
            placa = request.form['placa']
            dt = request.form['dt']
            tipo = request.form['tipo']

            # Validar data
            try:
                data_viagem = datetime.strptime(data_viagem, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError("Data da viagem inválida. Use o formato AAAA-MM-DD.")

            # Calcular o frete
            maior_frete, peso_usado, valor_total_frete, peso_minimo, valor_total_produtos, gris_total, fretes_desmembrados = calcular_frete(
                cidades, pesos, valores, num_entregas
            )

            # Preparar o resultado
            resultado = {
                'origem': ORIGEM_FIXA.title(),
                'cidades': cidades,
                'pesos': [f"{p:.3f}t" for p in pesos],
                'valores': [f"R$ {v:.2f}" for v in valores],
                'peso_usado': f"{peso_usado:.3f}t",
                'peso_minimo': f"{peso_minimo:.3f}t",
                'num_entregas': num_entregas,
                'maior_frete': f"R$ {maior_frete:.2f}",
                'valor_total_produtos': f"R$ {valor_total_produtos:.2f}",
                'gris': f"R$ {gris_total:.2f}",
                'valor_total_frete': f"R$ {valor_total_frete:.2f}",
                'fretes_desmembrados': [
                    {
                        'cidade': item['cidade'].title(),
                        'tarifa': f"R$ {item['tarifa']:.2f}",
                        'peso': f"{item['peso']:.3f}t",
                        'valor_produto': f"R$ {item['valor_produto']:.2f}",
                        'valor_frete': f"R$ {item['valor_frete']:.2f}"
                    }
                    for item in fretes_desmembrados
                ],
                'data_viagem': data_viagem.strftime('%d/%m/%Y'),
                'cte': cte,
                'nfs': nfs,
                'placa': placa,
                'dt': dt,
                'tipo': tipo
            }

            # Salvar no banco de dados
            cidades_str = ", ".join(cidades)
            salvar_viagem(
                data_viagem=data_viagem,
                cte=cte,
                cidades=cidades_str,
                nfs=nfs,
                peso_total=peso_usado,
                valor_frete=valor_total_frete,
                placa=placa,
                dt=dt,
                tipo=tipo
            )

            return render_template('result.html', resultado=resultado)

        except ValueError as e:
            return render_template('index.html', error=str(e), cidades_disponiveis=cidades_disponiveis)
        except Exception as e:
            return render_template('index.html', error=f"Erro inesperado: {str(e)}", cidades_disponiveis=cidades_disponiveis)

    return render_template('index.html', cidades_disponiveis=cidades_disponiveis)

if __name__ == '__main__':
    app.run(debug=True)