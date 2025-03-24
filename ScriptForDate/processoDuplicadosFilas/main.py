import os
import csv
import glob
import pandas as pd

def detectar_delimitador(caminho_arquivo, amostra_maxima=2048):
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

def main():
    pasta_analisar = "analisar"
    arquivos_csv = glob.glob(os.path.join(pasta_analisar, "*.csv"))
    
    tarefas_ignoradas = ["Arquivo definitivo", "Imprimir Expediente", "(CR) Processos arquivados"] 
    
    df_total = pd.DataFrame()
    
    for arquivo in arquivos_csv:
        delimitador = detectar_delimitador(arquivo)
        
        try:
            df = pd.read_csv(arquivo, delimiter=delimitador, encoding='utf-8', engine='python')
        except Exception as e:
            print(f"Erro ao ler o arquivo {arquivo}: {e}")
            continue
        
        mapeamento = padronizar_nome_coluna(df.columns)
        df.rename(columns=mapeamento, inplace=True)
        
        df_total = pd.concat([df_total, df], ignore_index=True)
    
    if "numeroProcesso" not in df_total.columns or "NomeTarefa" not in df_total.columns:
        print("Não foi possível encontrar as colunas 'numeroProcesso' e/ou 'NomeTarefa' em alguns arquivos.")
        return
    
    df_total = df_total.dropna(subset=["numeroProcesso"])
    
    # Identifica processos repetidos
    freq = df_total["numeroProcesso"].value_counts()
    processos_repetidos = freq[freq > 1].index
    df_repetidos = df_total[df_total["numeroProcesso"].isin(processos_repetidos)]
    
    def processar_tarefas(grupo):
        tarefas_unicas = grupo.dropna().unique()
        
        # Se houver apenas uma tarefa e ela estiver na lista de ignoradas, o processo será excluído
        if len(tarefas_unicas) == 1 and tarefas_unicas[0] in tarefas_ignoradas:
            return None
        
        # Retorna as tarefas concatenadas
        return ', '.join(tarefas_unicas)

    # Usa o nome 'tarefasAssociadas' direto no reset_index()
    df_final = (
        df_repetidos
        .groupby("numeroProcesso")["NomeTarefa"]
        .apply(processar_tarefas)
        .reset_index(name="tarefasAssociadas")
    )

    # Renomeia 'numeroProcesso' para 'processoID'
    df_final.rename(columns={"numeroProcesso": "processoID"}, inplace=True)
    
    # Remove processos onde o resultado é None
    df_final = df_final[df_final["tarefasAssociadas"].notna()]
    
    # Salva o resultado no CSV final
    nome_arquivo_saida = "processos_repetidos.csv"
    df_final.to_csv(nome_arquivo_saida, index=False, encoding='utf-8', sep=';')
    
    print(f"Arquivo '{nome_arquivo_saida}' gerado com sucesso!")

if __name__ == "__main__":
    main()
