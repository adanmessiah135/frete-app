let cidadeCount = 1;

// Função para adicionar uma nova cidade
function adicionarCidade() {
    console.log("Botão Adicionar Cidade clicado!"); // Depuração
    const container = document.getElementById('cidadesContainer');
    if (!container) {
        console.error("Container 'cidadesContainer' não encontrado!");
        return;
    }

    const newRow = document.createElement('div');
    newRow.className = 'cidade-row';

    // Criar a lista suspensa
    let selectOptions = '<option value="" disabled selected>Selecione a Cidade</option>';
    if (!cidadesDisponiveis) {
        console.error("cidadesDisponiveis não está definido!");
        return;
    }

    cidadesDisponiveis.forEach(cidade => {
        selectOptions += `<option value="${cidade}">${cidade.charAt(0).toUpperCase() + cidade.slice(1)}</option>`;
    });

    newRow.innerHTML = `
        <select name="cidade_${cidadeCount}" required>
            ${selectOptions}
        </select>
        <input type="number" name="peso_${cidadeCount}" placeholder="Peso (toneladas)" step="0.001" required>
        <input type="number" name="valor_${cidadeCount}" placeholder="Valor do Produto (R$)" step="0.01" required>
    `;
    container.appendChild(newRow);
    cidadeCount++;
    document.getElementById('numCidades').value = cidadeCount;
    console.log(`Nova cidade adicionada, total: ${cidadeCount}`); // Depuração
}

// Função para exibir mensagens de erro
function mostrarErro(mensagem) {
    const erroDiv = document.getElementById('formError');
    erroDiv.textContent = mensagem;
    erroDiv.style.display = 'block';
    setTimeout(() => {
        erroDiv.style.display = 'none';
    }, 5000); // Esconder após 5 segundos
}

// Função para validar o formulário
function validarFormulario() {
    console.log("Validando formulário..."); // Depuração

    // Limpar mensagem de erro
    const erroDiv = document.getElementById('formError');
    erroDiv.style.display = 'none';

    // Obter todas as linhas de cidades
    const cidadeRows = document.querySelectorAll('.cidade-row');
    const cidadesSelecionadas = [];
    let erro = false;

    // Validar cada linha de cidade
    cidadeRows.forEach((row, index) => {
        const selectCidade = row.querySelector(`select[name="cidade_${index}"]`);
        const inputPeso = row.querySelector(`input[name="peso_${index}"]`);
        const inputValor = row.querySelector(`input[name="valor_${index}"]`);

        // Validar cidade
        const cidade = selectCidade.value;
        if (!cidade) {
            mostrarErro("Selecione uma cidade em todas as linhas.");
            erro = true;
            return;
        }

        // Verificar cidades duplicadas
        if (cidadesSelecionadas.includes(cidade)) {
            mostrarErro(`A cidade "${cidade.charAt(0).toUpperCase() + cidade.slice(1)}" foi selecionada mais de uma vez.`);
            erro = true;
            return;
        }
        cidadesSelecionadas.push(cidade);

        // Validar peso
        const peso = parseFloat(inputPeso.value);
        if (isNaN(peso) || peso <= 0) {
            mostrarErro(`O peso na linha ${index + 1} deve ser maior que zero.`);
            erro = true;
            return;
        }

        // Validar valor do produto
        const valor = parseFloat(inputValor.value);
        if (isNaN(valor) || valor <= 0) {
            mostrarErro(`O valor do produto na linha ${index + 1} deve ser maior que zero.`);
            erro = true;
            return;
        }
    });

    // Validar número de entregas
    const numEntregasInput = document.querySelector('input[name="num_entregas"]');
    const numEntregas = parseInt(numEntregasInput.value);
    if (isNaN(numEntregas) || numEntregas <= 0) {
        mostrarErro("O número de entregas deve ser um número inteiro maior que zero.");
        erro = true;
        return;
    }

    // Validar data da viagem
    const dataViagemInput = document.querySelector('input[name="data_viagem"]');
    if (!dataViagemInput.value) {
        mostrarErro("A data da viagem é obrigatória.");
        erro = true;
        return;
    }

    // Validar CTE
    const cteInput = document.querySelector('input[name="cte"]');
    if (!cteInput.value.trim()) {
        mostrarErro("O número do CTE é obrigatório.");
        erro = true;
        return;
    }

    // Validar NFs
    const nfsInput = document.querySelector('input[name="nfs"]');
    if (!nfsInput.value.trim()) {
        mostrarErro("As notas fiscais são obrigatórias.");
        erro = true;
        return;
    }

    // Validar placa
    const placaInput = document.querySelector('input[name="placa"]');
    if (!placaInput.value.trim()) {
        mostrarErro("A placa do veículo é obrigatória.");
        erro = true;
        return;
    }

    // Validar DT
    const dtInput = document.querySelector('input[name="dt"]');
    if (!dtInput.value.trim()) {
        mostrarErro("O número do DT é obrigatório.");
        erro = true;
        return;
    }

    // Validar tipo
    const tipoInput = document.querySelector('select[name="tipo"]');
    if (!tipoInput.value) {
        mostrarErro("O tipo de transporte é obrigatório.");
        erro = true;
        return;
    }

    if (erro) {
        return false; // Impedir o envio do formulário
    }

    console.log("Formulário válido, enviando..."); // Depuração
    return true; // Permitir o envio do formulário
}