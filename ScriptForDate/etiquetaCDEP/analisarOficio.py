import os
import re
import json
from PyPDF2 import PdfReader, PdfWriter

# Diretórios de entrada e saída
input_dir = "./documento_Oficio"
output_dir = "./Result"
json_output = "./Result/resultado.json"

# Criar diretório de saída se não existir
os.makedirs(output_dir, exist_ok=True)

# Padrões PRINCIPAIS (prioridade na busca)
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

# Dicionário para armazenar os resultados
resultado = {"processados": [], "nao_processados": []}

def extrair_paginas_uteis(pdf_path, output_path):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    
    writer.add_page(reader.pages[0])  # Sempre adiciona a primeira página
    
    # Percorre as páginas procurando primeiro pelos padrões de prioridade
    paginas_adicionadas = 1  # Contamos a primeira página já adicionada
    encontrou_pagina = False
    
    for i in range(1, len(reader.pages)):  # Começa da segunda página
        texto_pagina = reader.pages[i].extract_text()
        if texto_pagina:
            # Procura primeiro os padrões de prioridade
            if any(re.search(pattern, texto_pagina, re.IGNORECASE) for pattern in priority_patterns):
                writer.add_page(reader.pages[i])
                paginas_adicionadas += 1
                encontrou_pagina = True
                continue  # Se encontrar um padrão prioritário, não verifica os secundários nessa página
            
            # Se nenhum padrão prioritário for encontrado, procura nos padrões secundários
            if any(re.search(pattern, texto_pagina, re.IGNORECASE) for pattern in secondary_patterns):
                writer.add_page(reader.pages[i])
                paginas_adicionadas += 1
                encontrou_pagina = True

    # Salva o novo PDF se houver mais de uma página
    if encontrou_pagina:
        with open(output_path, "wb") as output_pdf:
            writer.write(output_pdf)
        resultado["processados"].append(pdf_path)
        print(f"Novo PDF salvo: {output_path}")
    else:
        resultado["nao_processados"].append(pdf_path)
        print(f"Nenhuma página correspondente encontrada em {pdf_path}, além da primeira.")

# Processa todos os PDFs na pasta de entrada
pdf_encontrados = False
for pdf_file in os.listdir(input_dir):
    if pdf_file.lower().endswith(".pdf"):
        pdf_encontrados = True
        pdf_path = os.path.join(input_dir, pdf_file)
        output_path = os.path.join(output_dir, f"filtrado_{pdf_file}")
        extrair_paginas_uteis(pdf_path, output_path)

if not pdf_encontrados:
    print("Nenhum arquivo PDF encontrado na pasta de entrada.")

# Salva os resultados em JSON
with open(json_output, "w", encoding="utf-8") as json_file:
    json.dump(resultado, json_file, indent=4, ensure_ascii=False)

print(f"\nArquivo JSON com os resultados salvo em: {json_output}")
