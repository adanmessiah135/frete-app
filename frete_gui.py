from decimal import Decimal
import mysql.connector

# Constante para a origem fixa
ORIGEM_FIXA = "bebedouro"

def conectar_bd():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="",
        database="frete_db"
    )

def carregar_tarifas_e_pesos_minimos():
    with conectar_bd() as mydb:
        with mydb.cursor(dictionary=True) as mycursor:
            # Obter tarifas, destinos e id_veiculo
            mycursor.execute("""
                SELECT f.destino, f.tarifa, f.id_veiculo
                FROM frete f
                WHERE f.origem = %s
            """, (ORIGEM_FIXA,))
            tarifas_data = mycursor.fetchall()
            
            # Obter tarifas e associar id_veiculo
            tarifas = {row["destino"].strip().lower(): Decimal(str(row["tarifa"])) for row in tarifas_data}
            id_veiculos = {row["destino"].strip().lower(): row["id_veiculo"] for row in tarifas_data}
            
            # Buscar peso_minimo com base no id_veiculo
            pesos_minimos = {}
            for destino, id_veiculo in id_veiculos.items():
                if id_veiculo is not None:
                    mycursor.execute("SELECT peso_minimo FROM tipos_veiculo WHERE id = %s", (id_veiculo,))
                    peso_minimo = mycursor.fetchone()
                    if peso_minimo:
                        pesos_minimos[destino] = Decimal(str(peso_minimo["peso_minimo"]))
                        print(f"Depuração: Destino {destino}, id_veiculo {id_veiculo}, peso_minimo {peso_minimo['peso_minimo']}")
                    else:
                        pesos_minimos[destino] = Decimal('0.0')
                        print(f"Depuração: Nenhum peso_minimo encontrado para id_veiculo {id_veiculo} no destino {destino}")
                else:
                    pesos_minimos[destino] = Decimal('0.0')
                    print(f"Depuração: id_veiculo nulo para destino {destino}")
            return tarifas, pesos_minimos

def calcular_frete(cidades, pesos, valores_produtos, num_entregas):
    tarifas, pesos_minimos = carregar_tarifas_e_pesos_minimos()
    cidades_validas = [cidade.strip().lower() for cidade in cidades]
    
    # Validar cidades
    tarifas_encontradas = [tarifas[cidade] for cidade in cidades_validas if cidade in tarifas]
    cidades_sem_tarifa = [cidade for cidade in cidades_validas if cidade not in tarifas]
    
    if cidades_sem_tarifa:
        print(f"Atenção: Cidades sem tarifa cadastrada: {cidades_sem_tarifa}")
    if not tarifas_encontradas:
        raise ValueError("Nenhuma das cidades informadas possui tarifa cadastrada.")
    
    # Determinar a maior tarifa e o peso mínimo associado
    maior_frete = max(tarifas_encontradas)
    destino_maior_frete = next(cidade for cidade in cidades_validas if cidade in tarifas and tarifas[cidade] == maior_frete)
    peso_minimo = pesos_minimos.get(destino_maior_frete, Decimal('0.0'))
    
    # Calcular peso total e peso usado
    peso_total = sum(Decimal(str(peso)) for peso in pesos)
    peso_usado = peso_total if peso_total >= peso_minimo else peso_minimo
    
    # Calcular o valor total do frete
    valor_total_frete = maior_frete * peso_usado
    
    # Aplicar acréscimo de 5% se número de entregas > 2
    acrescimo = Decimal("1.05") if num_entregas > 2 else Decimal("1.0")
    valor_total_frete *= acrescimo
    
    # Calcular o GRIS (0,002% do valor total dos produtos)
    valor_total_produtos = sum(Decimal(str(valor)) for valor in valores_produtos)
    gris_total = valor_total_produtos * Decimal('0.00002')
    valor_total_frete += gris_total
    valor_total_frete = valor_total_frete.quantize(Decimal('0.01'))
    
    # Calcular o frete desmembrado por cidade usando a MAIOR TARIFA
    fretes_desmembrados = []
    soma_fretes_desmembrados = Decimal('0.0')
    
    for i, (cidade, peso, valor_produto) in enumerate(zip(cidades_validas, pesos, valores_produtos)):
        # Converter peso e valor para Decimal
        peso = Decimal(str(peso))
        valor_produto = Decimal(str(valor_produto))
        
        # Usar a MAIOR TARIFA para todas as cidades
        tarifa_usada = maior_frete
        
        # Calcular o peso proporcional: (peso da cidade / peso total) * peso usado
        proporcao_peso = peso / peso_total if peso_total > 0 else Decimal('0.0')
        peso_proporcional = proporcao_peso * peso_usado
        
        # Calcular o valor base do frete para a cidade usando a maior tarifa
        valor_frete_cidade = tarifa_usada * peso_proporcional
        
        # Aplicar o acréscimo proporcional
        valor_frete_cidade *= acrescimo
        
        # Calcular o GRIS proporcional: (valor do produto da cidade / valor total dos produtos) * GRIS total
        proporcao_valor = valor_produto / valor_total_produtos if valor_total_produtos > 0 else Decimal('0.0')
        gris_cidade = gris_total * proporcao_valor
        
        # Somar o GRIS ao valor do frete da cidade
        valor_frete_cidade += gris_cidade
        valor_frete_cidade = valor_frete_cidade.quantize(Decimal('0.01'))
        
        # Adicionar ao total desmembrado
        soma_fretes_desmembrados += valor_frete_cidade
        
        # Armazenar o resultado desmembrado
        fretes_desmembrados.append({
            'cidade': cidade,
            'tarifa': tarifa_usada,  # Usar a maior tarifa
            'peso': peso,
            'valor_produto': valor_produto,
            'valor_frete': valor_frete_cidade
        })
    
    # Ajustar o último valor desmembrado para corrigir possíveis erros de arredondamento
    if fretes_desmembrados:
        diferenca = valor_total_frete - soma_fretes_desmembrados
        fretes_desmembrados[-1]['valor_frete'] += diferenca
        soma_fretes_desmembrados = sum(item['valor_frete'] for item in fretes_desmembrados)
    
    return maior_frete, peso_usado, valor_total_frete, peso_minimo, valor_total_produtos, gris, fretes_desmembrados

# Entrada do usuário com validação
cidades = input("Digite as cidades de destino separadas por vírgula (1 ou mais): ").lower().split(",")

pesos = []
valores_produtos = []
for cidade in cidades:
    while True:
        try:
            peso = float(input(f"Digite o peso para {cidade.strip().title()}: "))
            pesos.append(peso)
            break
        except ValueError:
            print("Por favor, digite um número válido para o peso.")
    
    while True:
        try:
            valor = float(input(f"Digite o valor do produto para {cidade.strip().title()} (em R$): "))
            valores_produtos.append(valor)
            break
        except ValueError:
            print("Por favor, digite um número válido para o valor do produto.")

while True:
    try:
        num_entregas = int(input("Digite a quantidade de entregas: "))
        break
    except ValueError:
        print("Por favor, digite um número inteiro válido para as entregas.")

# Validar que pelo menos 1 cidade foi fornecida
if len(cidades) < 1:
    raise ValueError("Por favor, forneça pelo menos uma cidade de destino.")

# Calcular o frete
try:
    maior_frete, peso_usado, valor_total_frete, peso_minimo, valor_total_produtos, gris, fretes_desmembrados = calcular_frete(
        cidades, pesos, valores_produtos, num_entregas
    )
    
    # Exibir os dados
    print("\nResumo do Cálculo do Frete:")
    print(f"Origem: {ORIGEM_FIXA.title()}")
    print(f"Cidades de Destino: {', '.join(cidades)}")
    print(f"Pesos Fornecidos: {', '.join(f'{p:.3f}t' for p in pesos)}")
    print(f"Valores dos Produtos: {', '.join(f'R$ {v:.2f}' for v in valores_produtos)}")
    print(f"Peso Usado no Cálculo: {peso_usado:.3f}t")
    print(f"Peso Mínimo da Categoria: {peso_minimo:.3f}t")
    print(f"Número de Entregas: {num_entregas}")
    print(f"Maior Tarifa Usada: R$ {maior_frete:.2f}")
    print(f"Valor Total dos Produtos: R$ {valor_total_produtos:.2f}")
    print(f"GRIS (0,002% do valor dos produtos): R$ {gris:.2f}")
    
    # Exibir os fretes desmembrados
    print("\nFretes Desmembrados por Cidade (usando a maior tarifa):")
    for item in fretes_desmembrados:
        print(f"- Cidade: {item['cidade'].title()}")
        print(f"  Tarifa Usada: R$ {item['tarifa']:.2f}")
        print(f"  Peso: {item['peso']:.3f}t")
        print(f"  Valor do Produto: R$ {item['valor_produto']:.2f}")
        print(f"  Valor do Frete: R$ {item['valor_frete']:.2f}")
    
    # Exibir o valor total do frete
    print(f"\nValor Total do Frete: R$ {valor_total_frete:.2f}")
    
    # Verificar se a soma dos fretes desmembrados é igual ao valor total
    soma_fretes_desmembrados = sum(item['valor_frete'] for item in fretes_desmembrados)
    print(f"Soma dos Fretes Desmembrados: R$ {soma_fretes_desmembrados:.2f}")
    if soma_fretes_desmembrados != valor_total_frete:
        print("Atenção: A soma dos fretes desmembrados não é igual ao valor total do frete!")

except ValueError as e:
    print(f"Erro: {e}")
except Exception as e:
    print(f"Erro inesperado: {e}")