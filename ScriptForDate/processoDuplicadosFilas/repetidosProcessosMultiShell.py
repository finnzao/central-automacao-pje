""


import os
import csv
import glob
import pandas as pd

def detectar_delimitador(caminho_arquivo, amostra_maxima=2048):
    """
    Detecta o delimitador do arquivo CSV lendo um bloco de dados (amostra) e
    usando o csv.Sniffer. Se não for possível, retorna ';'.
    """
    with open(caminho_arquivo, 'r', encoding='utf-8', errors='ignore') as f:
        amostra = f.read(amostra_maxima)
        f.seek(0)
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(amostra)
        return dialect.delimiter
    except csv.Error:
        return ';'

def padronizar_nome_coluna(colunas):
    """
    Faz a padronização dos nomes de colunas, para que colunas como
    'numeroProcesso', 'numero_processo' etc. sejam tratadas como 'numeroProcesso',
    e 'NomeTarefa'/'nomeTarefa' sejam tratadas como 'NomeTarefa'.
    """
    possiveis_nomes_numero_processo = [
        "numeroProcesso", "numero_processo", "numeroProcesso ", "numero_processo "
    ]
    possiveis_nomes_tarefa = [
        "NomeTarefa", "nomeTarefa", "NomeTarefa ", "nomeTarefa "
    ]
    
    mapeamento = {}
    for col in colunas:
        col_limpo = col.strip()
        col_lower = col_limpo.lower()
        
        if col_lower in [nome.lower() for nome in possiveis_nomes_numero_processo]:
            mapeamento[col] = "numeroProcesso"
        elif col_lower in [nome.lower() for nome in possiveis_nomes_tarefa]:
            mapeamento[col] = "NomeTarefa"
        else:
            mapeamento[col] = col_limpo
    return mapeamento

def processar_pasta(pasta_raiz, subpasta, tarefas_ignoradas):
    """
    Lê todos os arquivos CSV dentro de `pasta_raiz/subpasta`,
    concatena em um único DataFrame, processa tarefas repetidas/ignoradas
    e retorna o DataFrame final.
    """
    caminho_subpasta = os.path.join(pasta_raiz, subpasta)
    arquivos_csv = glob.glob(os.path.join(caminho_subpasta, "*.csv"))
    
    df_total = pd.DataFrame()
    
    for arquivo in arquivos_csv:
        delimitador = detectar_delimitador(arquivo)
        
        try:
            df = pd.read_csv(
                arquivo,
                delimiter=delimitador,
                encoding='utf-8',
                engine='python'
            )
        except Exception as e:
            print(f"Erro ao ler o arquivo {arquivo}: {e}")
            continue
        
        # Padroniza nomes de colunas
        mapeamento = padronizar_nome_coluna(df.columns)
        df.rename(columns=mapeamento, inplace=True)
        
        # Concatena ao DataFrame total
        df_total = pd.concat([df_total, df], ignore_index=True)
    
    if df_total.empty:
        print(f"Não foram encontrados arquivos válidos em: {caminho_subpasta}")
        return pd.DataFrame()  # Retorna DataFrame vazio
    
    # Verifica se as colunas essenciais existem
    if "numeroProcesso" not in df_total.columns or "NomeTarefa" not in df_total.columns:
        print(f"[{subpasta}] Não foi possível encontrar as colunas 'numeroProcesso' e/ou 'NomeTarefa'.")
        return pd.DataFrame()  # Retorna DataFrame vazio
    
    # Remove linhas sem numeroProcesso
    df_total.dropna(subset=["numeroProcesso"], inplace=True)
    
    # Identifica processos repetidos
    freq = df_total["numeroProcesso"].value_counts()
    processos_repetidos = freq[freq > 1].index
    df_repetidos = df_total[df_total["numeroProcesso"].isin(processos_repetidos)]
    
    # Função para processar as tarefas dentro de cada processo
    def agrupar_tarefas(grupo):
        tarefas_unicas = grupo.dropna().unique()
        
        # Se houver apenas uma tarefa e ela estiver na lista de ignoradas, descartar (retorna None)
        if len(tarefas_unicas) == 1 and tarefas_unicas[0] in tarefas_ignoradas:
            return None
        
        # Concatenar todas as tarefas (inclusive as ignoradas, se houver mais de uma)
        return ', '.join(tarefas_unicas)
    
    # Corrigido: agrupar somente a coluna "NomeTarefa" e usar .reset_index(name="nomeTarefa")
    # Isso evita o conflito de colunas na hora do reset_index() e remove o DeprecationWarning.
    df_final = (
        df_repetidos
        .groupby("numeroProcesso")["NomeTarefa"]  
        .apply(agrupar_tarefas)
        .reset_index(name="nomeTarefa")
    )
    
    # Remove processos onde a tarefa resultou em None
    df_final = df_final[df_final["nomeTarefa"].notna()]

    return df_final

def main():
    pasta_analisar = "analisar"
    
    # Subpastas esperadas:
    subpastas = [
        "Civil Direção",
        "Crime Direção",
        "Civil Assessoria",
        "Crime Assessoria"
    ]
    
    # Tarefas que devem ser ignoradas em certos casos
    tarefas_ignoradas = ["Arquivo definitivo", "Imprimir Expediente","(CR) Processos arquivados"]
    
    # Nome do arquivo de saída (Excel)
    nome_arquivo_saida = "processos_repetidos_por_subpasta.xlsx"
    
    # Usa ExcelWriter para criar/atualizar o arquivo Excel
    with pd.ExcelWriter(nome_arquivo_saida) as writer:
        for subpasta in subpastas:
            print(f"\nProcessando subpasta: {subpasta}")
            df_resultado = processar_pasta(pasta_analisar, subpasta, tarefas_ignoradas)
            
            if df_resultado.empty:
                print(f"Nenhum resultado para subpasta: {subpasta}")
                continue
            
            # Salva em uma nova aba (sheet) com o nome da subpasta
            sheet_name = subpasta  # Ajuste se quiser remover espaços ou caracteres especiais
            df_resultado.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"Resultados de '{subpasta}' adicionados na aba '{sheet_name}'.")
    
    print(f"\nArquivo Excel '{nome_arquivo_saida}' gerado com sucesso!")

if __name__ == "__main__":
    main()
