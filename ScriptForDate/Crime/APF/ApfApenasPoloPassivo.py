import pandas as pd
import re
import unicodedata

def remover_acentos(texto):
    """
    Remove acentos de uma string utilizando normalização Unicode.
    """
    if isinstance(texto, str):
        return ''.join(
            c for c in unicodedata.normalize('NFD', texto)
            if unicodedata.category(c) != 'Mn'
        )
    return texto

def extrair_ano_processo(numero_processo):
    match_ano = re.search(r'\d{7}-\d{2}\.(\d{4})\.', str(numero_processo))
    return int(match_ano.group(1)) if match_ano else None

def comparar_arquivos_csv_dupla(arquivo1, arquivo2, 
                                coluna_comparacao, 
                                coluna_processo1, coluna_processo2, 
                                coluna_classe1, coluna_classe2, 
                                saida):
    # Carregar os arquivos CSV
    df1 = pd.read_csv(arquivo1, sep=';', encoding='utf-8')
    df2 = pd.read_csv(arquivo2, sep=',', encoding='utf-8')
    
    # Normalizar a coluna de comparação no arquivo1 (APF)
    df1[coluna_comparacao] = df1[coluna_comparacao].str.strip().str.upper().apply(remover_acentos)
    
    # No arquivo2 (Ação Penal), normalizar as colunas "Polo Passivo" e "poloAtivo"
    df2[coluna_comparacao] = df2[coluna_comparacao].str.strip().str.upper().apply(remover_acentos)
    df2['poloAtivo'] = df2['poloAtivo'].str.strip().str.upper().apply(remover_acentos)
    
    # Renomear colunas para diferenciar os dados de APF e Ação Penal
    df1 = df1.rename(columns={
        coluna_processo1: f"{coluna_processo1}_APF", 
        coluna_classe1: f"{coluna_classe1}_APF"
    })
    df2 = df2.rename(columns={
        coluna_processo2: f"{coluna_processo2}_ACAO", 
        coluna_classe2: f"{coluna_classe2}_ACAO"
    })
    
    # Selecionar apenas as colunas necessárias para a comparação
    colunas_necessarias1 = [f"{coluna_processo1}_APF", f"{coluna_classe1}_APF", coluna_comparacao]
    colunas_necessarias2 = [f"{coluna_processo2}_ACAO", f"{coluna_classe2}_ACAO", 
                            coluna_comparacao, "assuntoPrincipal", "nomeTarefa", "poloAtivo"]
    df1 = df1[colunas_necessarias1].copy()
    df2 = df2[colunas_necessarias2].copy()
    
    # Extrair o ano do processo para os dois DataFrames
    df1['Ano_APF'] = df1[f"{coluna_processo1}_APF"].apply(extrair_ano_processo)
    df2['Ano_ACAO'] = df2[f"{coluna_processo2}_ACAO"].apply(extrair_ano_processo)
    
    # --- Realizar a comparação utilizando duas junções ---
    # 1. Comparação: APF[coluna_comparacao] com Ação Penal[coluna_comparacao] (Polo Passivo)
    merge_passivo = pd.merge(df1, df2, on=coluna_comparacao, how='left', suffixes=('', '_ACAO'))
    merge_passivo['Tipo_Match'] = 'Polo Passivo'
    
    # 2. Comparação: APF[coluna_comparacao] com Ação Penal['poloAtivo']
    merge_ativo = pd.merge(df1, df2, left_on=coluna_comparacao, right_on='poloAtivo', how='left', suffixes=('', '_ACAO'))
    merge_ativo['Tipo_Match'] = 'poloAtivo'
    
    # Combinar os resultados das duas junções
    merged = pd.concat([merge_passivo, merge_ativo], ignore_index=True)
    
    # Criar a coluna unificada "Nome do Polo"
    merged['Nome do Polo'] = merged.apply(
        lambda row: row[coluna_comparacao] if row['Tipo_Match'] == 'Polo Passivo' else row['poloAtivo'],
        axis=1
    )
    
    # --- Validação das Correspondências ---
    # A correspondência é válida se:
    # - O ano do processo da Ação Penal não for nulo;
    # - O ano da Ação Penal for maior ou igual ao ano do APF;
    # - A classe judicial da Ação Penal for diferente de "AuPrFl".
    merged['Valido'] = (
        merged['Ano_ACAO'].notnull() &
        (merged['Ano_ACAO'] >= merged['Ano_APF']) &
        (merged[f"{coluna_classe2}_ACAO"] != "AuPrFl")
    )
    
    # Selecionar apenas as linhas com correspondências válidas
    correspondencias = merged[merged['Valido']].copy()
    
    # Verificar se o "Nome do Polo" aparece apenas uma vez entre as correspondências
    if not correspondencias.empty:
        freq = correspondencias['Nome do Polo'].value_counts()
        correspondencias['PoloPassivo_Unico'] = correspondencias['Nome do Polo'].map(lambda x: freq[x] == 1)
    else:
        correspondencias['PoloPassivo_Unico'] = []
    
    # Reorganizar as colunas para a saída
    colunas_ordenadas = [
        f"{coluna_processo1}_APF", "Ano_APF", "nomeTarefa", "Ano_ACAO",
        f"{coluna_processo2}_ACAO", "Nome do Polo",
        f"{coluna_classe1}_APF", f"{coluna_classe2}_ACAO",
        "assuntoPrincipal", "PoloPassivo_Unico"
    ]
    correspondencias = correspondencias[[col for col in colunas_ordenadas if col in correspondencias.columns]]
    
    # Identificar os processos do APF que NÃO tiveram nenhum match válido
    valid_por_processo = merged.groupby(f"{coluna_processo1}_APF")['Valido'].any().reset_index()
    nao_encontrados_ids = valid_por_processo[~valid_por_processo['Valido']][f"{coluna_processo1}_APF"]
    nao_encontrados = df1[df1[f"{coluna_processo1}_APF"].isin(nao_encontrados_ids)].copy()
    
    # Garantir que a coluna Ano_APF esteja presente
    if 'Ano_APF' not in nao_encontrados.columns:
        nao_encontrados['Ano_APF'] = nao_encontrados[f"{coluna_processo1}_APF"].apply(extrair_ano_processo)
    
    # Criar o arquivo de saída com duas sheets: Correspondências e Não Encontrados
    with pd.ExcelWriter(saida) as writer:
        correspondencias.to_excel(writer, index=False, sheet_name='Correspondências')
        nao_encontrados.to_excel(writer, index=False, sheet_name='Não Encontrados')
    
    print(f'Resultado salvo em {saida}')

# --- Parâmetros e Execução ---
arquivo1 = "(CR) Processos arquivados.csv"   # Arquivo APF
arquivo2 = "todosProcessosCrime12.02.csv"     # Arquivo Ação Penal
coluna_comparacao = "Polo Passivo"            # Coluna para comparação (APF e, no primeiro caso, Ação Penal)
coluna_processo1 = "numeroProcesso"
coluna_processo2 = "numeroProcesso"
coluna_classe1 = "classeJudicial"
coluna_classe2 = "classeJudicial"
saida = "Comparacao_Resultados.xlsx"

comparar_arquivos_csv_dupla(arquivo1, arquivo2, 
                           coluna_comparacao, 
                           coluna_processo1, coluna_processo2, 
                           coluna_classe1, coluna_classe2, 
                           saida)
