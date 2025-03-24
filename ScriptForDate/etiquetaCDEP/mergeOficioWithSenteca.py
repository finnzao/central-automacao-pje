#!/usr/bin/env python3
import os
import re
from PyPDF2 import PdfReader, PdfWriter
from openpyxl import Workbook

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
    print(f"Arquivo mesclado salvo em: {output_path}")

def main():
    # Diretórios de entrada
    dir_oficio = "./Result"               # Diretório dos ofícios
    dir_sentenca = "./documento_sentença" # Diretório das sentenças

    # Diretório de saída para os PDFs mesclados
    dir_output = "ArquivosProntosCDEP"

    # Cria o diretório de saída, caso não exista
    if not os.path.exists(dir_output):
        os.makedirs(dir_output)

    # Dicionários para mapear { numero_processo: caminho_pdf }
    pdf_oficio = {}
    pdf_sentenca = {}

    # ------------------------------------------------------------
    # Regex que captura exatos 15 caracteres (podendo ser dígitos,
    # ponto ou hífen) imediatamente antes de ".8.05.0216".
    # Exemplo: 0001176-79.2013.8.05.0216 ou 8001176-79.2013.8.05.0216
    # ------------------------------------------------------------
    pattern = re.compile(r'(?P<processo>[0-9.\-]{15}\.8\.05\.0216)')

    # -----------------------------
    # Verifica se os diretórios de ofício e sentença existem
    # -----------------------------
    if not os.path.isdir(dir_oficio):
        print(f"Atenção: o caminho {dir_oficio} não existe ou não é um diretório.")
        return
    if not os.path.isdir(dir_sentenca):
        print(f"Atenção: o caminho {dir_sentenca} não existe ou não é um diretório.")
        return

    # -----------------------------
    # Leitura dos arquivos de Ofício
    # -----------------------------
    for arquivo in os.listdir(dir_oficio):
        if arquivo.lower().endswith(".pdf"):
            caminho = os.path.join(dir_oficio, arquivo)
            match = pattern.search(arquivo)
            if match:
                num_processo = match.group("processo")
                pdf_oficio[num_processo] = caminho

    # -----------------------------
    # Leitura dos arquivos de Sentença
    # -----------------------------
    for arquivo in os.listdir(dir_sentenca):
        if arquivo.lower().endswith(".pdf"):
            caminho = os.path.join(dir_sentenca, arquivo)
            match = pattern.search(arquivo)
            if match:
                num_processo = match.group("processo")
                pdf_sentenca[num_processo] = caminho

    # -----------------------------
    # Identifica processos encontrados em ambos
    # -----------------------------
    processos_comuns = set(pdf_oficio.keys()) & set(pdf_sentenca.keys())

    # -----------------------------
    # Faz o merge dos arquivos para os processos que possuem ambos os PDFs
    # -----------------------------
    for processo in processos_comuns:
        print(f"Fazendo merge para o processo: {processo}")
        arquivos_para_merge = [pdf_oficio[processo], pdf_sentenca[processo]]

        # Monta o caminho de saída no diretório "ArquivosProntosCDEP"
        output_filename = os.path.join(dir_output, f"{processo}.pdf")

        merge_pdfs(arquivos_para_merge, output_filename)

    # -----------------------------
    # Cria a planilha de resumo
    # -----------------------------
    # Cabeçalho: Processo, Status, Erro
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumo de Processos"
    ws.append(["Processo", "Status", "Erro"])

    # -----------------------------
    # Preenche a planilha
    # -----------------------------
    # Processos que já apareceram (ou só ofício, ou só sentença, ou ambos)
    all_processos = set(pdf_oficio.keys()) | set(pdf_sentenca.keys())

    for processo in sorted(all_processos):
        if processo in processos_comuns:
            # Merge concluído
            status = "Concluído"
            erro = ""
        else:
            # Faltou algum dos dois
            status = "Incompleto"
            # Descobre se faltou Ofício, Sentença ou ambos
            falta_oficio = (processo not in pdf_oficio)
            falta_sentenca = (processo not in pdf_sentenca)

            if falta_oficio and falta_sentenca:
                erro = "Falta Ofício e Sentença"
            elif falta_oficio:
                erro = "Falta Ofício"
            elif falta_sentenca:
                erro = "Falta Sentença"
            else:
                erro = "Desconhecido"  # Caso improvável

        ws.append([processo, status, erro])

    # -----------------------------
    # Salva a planilha
    # -----------------------------
    planilha_saida = "ResumoProcessos.xlsx"
    wb.save(planilha_saida)
    print(f"\nPlanilha '{planilha_saida}' criada com sucesso.")

if __name__ == "__main__":
    main()
