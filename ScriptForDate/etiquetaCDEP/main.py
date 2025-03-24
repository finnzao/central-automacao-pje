import os
import re
import json
import csv
from PyPDF2 import PdfReader, PdfWriter
from openpyxl import Workbook

# -------------- CONFIGURAÇÕES INICIAIS --------------
# Diretório de arquivos originais de Ofício
DIR_OFICIOS_ORIGINAIS = "./documento_Oficio"

# Diretório onde serão salvos os Ofícios filtrados
DIR_OFICIOS_FILTRADOS = "./Result"

# Caminho do arquivo JSON para salvar o resultado do filtro
JSON_OUTPUT = "./Result/resultado.json"

# Diretório de Sentenças
DIR_SENTENCAS = "./documento_sentença"

# Caminho da planilha CSV contendo TODOS os processos esperados
CSV_TODOS_PROCESSOS = "./TodosOsProcessos.csv"

# Diretório final para salvar PDFs mesclados
DIR_MERGES = "./ArquivosProntosCDEP"

# Caminho da planilha Excel de resumo
XLSX_RESUMO = "ResumoProcessos.xlsx"

# ----------------------------------------------------

# ----------- PADRÕES PARA FILTRAR PÁGINAS NO OFÍCIO -----------
priority_patterns = [
    # Padrão 1: Comunicação de Indiciamento e Solicitação de Antecedentes Criminais
    r"Assunto:\s*Comunicação\s*de\s*Indiciamento\s*e\s*Solicitação\s*de\s*Antecedentes\s*Criminais",
    
    # Padrão 2: Pedido de Informações sobre Antecedentes
    r"A\s*fim\s*de\s*instruir\s*Inquérito\s*Policial\s*instaurado\s*nesta\s*Delegacia\s*Circunscricional\s*de\s*Polícia,?\s*"
    r"solicito\s*de\s*Vossa\s*Senhoria,?\s*a\s*prestimosa\s*colaboração\s*no\s*sentido\s*de\s*informar\s*o\s*que\s*consta\s*"
    r"nesse\s*órgão\s*em\s*desfavor\s*do\(a\)\s*indiciado\(a\)\s*abaixo\s*qualificado\(a\):",
    
    # Padrão 3: Solicitação de Vida Pregressa
    r"por\s*infração\s*a\s*legislação\s*abaixo\s*indicada,?\s*ao\s*tempo\s*em\s*que\s*solicitamos\s*os\s*bons\s*préstimos\s*"
    r"de\s*V\.?\s*Exa\.?\s*no\s*sentido\s*de\s*que\s*nos\s*seja\s*informado\s*o\s*que\s*consta\s*nos\s*arquivos\s*dessa\s*"
    r"Coordenação\s*a\s*respeito\s*da\s*sua\s*vida\s*pregressa"
]

# Padrões SECUNDÁRIOS (apenas se os principais não forem encontrados)
secondary_patterns = [
    r"Nome:\s*\w+",  # Padrão para encontrar a lista de qualificação do indiciado
    r"Inquérito Policial:\s*\d+/\d{4}",  # Informação sobre inquérito
    r"Data do fato:\s*\d{2}/\d{2}/\d{4}",  # Data do crime
    r"Data da Instauração:\s*\d{2}/\d{2}/\d{4}",  # Data de instauração do inquérito
    r"Infração Penal:\s*Artigo\s*\d+\s*do\s*CPB",  # Infração penal mencionada
]

# Estrutura para armazenar resultado do filtro (Ofícios)
resultado_filtro_oficios = {"processados": [], "nao_processados": []}

def extrair_paginas_uteis(pdf_path, output_path):
    """
    Extrai a primeira página e páginas que contenham padrões
    (prioritários ou secundários) de um PDF de Ofício.
    Salva o PDF filtrado em output_path se encontrar algo além da primeira página.
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    
    # Adiciona SEMPRE a primeira página
    writer.add_page(reader.pages[0])  
    
    paginas_adicionadas = 1
    encontrou_pagina = False
    
    # Percorre as páginas (a partir da segunda) procurando padrões
    for i in range(1, len(reader.pages)):
        texto_pagina = reader.pages[i].extract_text()
        if texto_pagina:
            # Primeiro procura pelos padrões prioritários
            if any(re.search(pattern, texto_pagina, re.IGNORECASE) for pattern in priority_patterns):
                writer.add_page(reader.pages[i])
                paginas_adicionadas += 1
                encontrou_pagina = True
                # Não verifica padrões secundários se já achou prioridade
                continue
            
            # Se não achou prioridade, verifica padrões secundários
            if any(re.search(pattern, texto_pagina, re.IGNORECASE) for pattern in secondary_patterns):
                writer.add_page(reader.pages[i])
                paginas_adicionadas += 1
                encontrou_pagina = True

    # Se encontrar algo além da primeira, salva um novo PDF
    if encontrou_pagina:
        with open(output_path, "wb") as output_pdf:
            writer.write(output_pdf)
        resultado_filtro_oficios["processados"].append(pdf_path)
        print(f"[Filtrar] Novo PDF salvo: {output_path}")
    else:
        # Caso não tenha páginas relevantes, só salva a primeira mesmo,
        # mas pode-se decidir não salvar se preferir.
        # Exemplo: salvando mesmo assim
        with open(output_path, "wb") as output_pdf:
            writer.write(output_pdf)
        resultado_filtro_oficios["nao_processados"].append(pdf_path)
        print(f"[Filtrar] Somente primeira página (nenhuma página com padrões) em: {pdf_path}")

def filtrar_oficios():
    """
    Filtra todos os PDFs no diretório de Ofícios (DIR_OFICIOS_ORIGINAIS),
    salvando a saída no DIR_OFICIOS_FILTRADOS.
    """
    # Garantir que a pasta de saída exista
    os.makedirs(DIR_OFICIOS_FILTRADOS, exist_ok=True)
    
    pdf_encontrados = False
    for pdf_file in os.listdir(DIR_OFICIOS_ORIGINAIS):
        if pdf_file.lower().endswith(".pdf"):
            pdf_encontrados = True
            pdf_path = os.path.join(DIR_OFICIOS_ORIGINAIS, pdf_file)
            output_path = os.path.join(DIR_OFICIOS_FILTRADOS, f"filtrado_{pdf_file}")
            extrair_paginas_uteis(pdf_path, output_path)

    if not pdf_encontrados:
        print("Nenhum arquivo PDF encontrado na pasta de entrada de Ofícios.")

    # Salva os resultados do filtro em JSON
    with open(JSON_OUTPUT, "w", encoding="utf-8") as json_file:
        json.dump(resultado_filtro_oficios, json_file, indent=4, ensure_ascii=False)
    print(f"\n[Filtrar] Arquivo JSON com resultados salvo em: {JSON_OUTPUT}")

# -------------------- FUNÇÃO PARA MERGE DE PDFs --------------------
def merge_pdfs(pdf_paths, output_path):
    """Mescla (merge) a lista de PDFs em um único arquivo."""
    writer = PdfWriter()
    for path in pdf_paths:
        try:
            reader = PdfReader(path)
            for page in reader.pages:
                writer.add_page(page)
        except Exception as e:
            print(f"Erro ao processar {path}: {e}")
    with open(output_path, "wb") as out_file:
        writer.write(out_file)
    print(f"[Merge] Arquivo mesclado salvo em: {output_path}")

# -------------------- FUNÇÃO PRINCIPAL --------------------
def main():
    """
    1. Filtra os Ofícios (mantendo as funções originais);
    2. Identifica números de processo em Ofícios filtrados e Sentenças;
    3. Compara com a lista de "TodosOsProcessos.csv";
    4. Gera planilha de resumo indicando presença/ausência;
    5. Gera PDFs mesclados quando ambos (Ofício e Sentença) existirem.
    """

    # 1. Filtra todos os Ofícios
    filtrar_oficios()

    # Garante a existência do diretório para PDFs mesclados
    if not os.path.exists(DIR_MERGES):
        os.makedirs(DIR_MERGES)

    # 2. Regex para capturar o número de processo no formato:
    #    ex: 0001176-79.2013.8.05.0216
    #    Pega 15 caracteres (dígitos, ponto, hífen) antes de ".8.05.0216"
    pattern_processo = re.compile(r'(?P<processo>[0-9.\-]{15}\.8\.05\.0216)')

    # Dicionários para mapear {numero_processo: caminho_pdf}
    pdf_oficios_dict = {}
    pdf_sentenças_dict = {}

    # 2a. Identificar processos nos Ofícios (filtrados) ----------------
    if os.path.isdir(DIR_OFICIOS_FILTRADOS):
        for arquivo in os.listdir(DIR_OFICIOS_FILTRADOS):
            if arquivo.lower().endswith(".pdf"):
                caminho = os.path.join(DIR_OFICIOS_FILTRADOS, arquivo)
                match = pattern_processo.search(arquivo)
                if match:
                    num_processo = match.group("processo")
                    pdf_oficios_dict[num_processo] = caminho

    # 2b. Identificar processos nas Sentenças --------------------------
    if os.path.isdir(DIR_SENTENCAS):
        for arquivo in os.listdir(DIR_SENTENCAS):
            if arquivo.lower().endswith(".pdf"):
                caminho = os.path.join(DIR_SENTENCAS, arquivo)
                match = pattern_processo.search(arquivo)
                if match:
                    num_processo = match.group("processo")
                    pdf_sentenças_dict[num_processo] = caminho

    # 3. Ler a lista de TODOS os processos a partir do CSV -------------
    todos_processos = []
    if os.path.isfile(CSV_TODOS_PROCESSOS):
        with open(CSV_TODOS_PROCESSOS, "r", encoding="utf-8") as f:
            leitor = csv.DictReader(f, delimiter=";")
            for linha in leitor:
                # Supondo que a coluna seja exatamente "numeroProcesso"
                todos_processos.append(linha["numeroProcesso"])
    else:
        print(f"ERRO: O arquivo {CSV_TODOS_PROCESSOS} não foi encontrado.")
        return

    # 4. Criar planilha de resumo --------------------------------------
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumo de Processos"

    # Cabeçalho
    ws.append([
        "numeroProcesso", 
        "Presente em Sentenças?",
        "Presente em Ofícios?",
        "Status do Merge",
        "Motivo"
    ])

    # Conjuntos para verificar presença
    set_oficios = set(pdf_oficios_dict.keys())
    set_sentenças = set(pdf_sentenças_dict.keys())

    # 5. Verificar cada processo esperado e realizar merges quando possível
    for processo in todos_processos:
        presente_sentenca = processo in set_sentenças
        presente_oficio = processo in set_oficios

        # Define flags "Sim" ou "Não"
        sentenca_flag = "Sim" if presente_sentenca else "Não"
        oficio_flag = "Sim" if presente_oficio else "Não"

        if presente_sentenca and presente_oficio:
            # Merge se ambos existem
            status = "Concluído"
            motivo = ""

            # Caminhos dos PDFs que serão mesclados
            lista_pdfs = [pdf_oficios_dict[processo], pdf_sentenças_dict[processo]]
            nome_saida = os.path.join(DIR_MERGES, f"{processo}.pdf")
            merge_pdfs(lista_pdfs, nome_saida)

        else:
            # Se estiver faltando algum
            status = "Incompleto"
            if (not presente_sentenca) and (not presente_oficio):
                motivo = "ausente em ambos"
            elif not presente_sentenca:
                motivo = "ausente no arquivo de Sentenças"
            elif not presente_oficio:
                motivo = "ausente no arquivo de Ofícios"
            else:
                motivo = "desconhecido"  # caso inesperado

        # Adiciona linha no Excel
        ws.append([
            processo,
            sentenca_flag,
            oficio_flag,
            status,
            motivo
        ])

    # 6. Salvar o Excel de resumo --------------------------------------
    wb.save(XLSX_RESUMO)
    print(f"\nPlanilha de resumo '{XLSX_RESUMO}' criada com sucesso.")

# ---------- DISPARA O SCRIPT PRINCIPAL -----------
if __name__ == "__main__":
    main()
