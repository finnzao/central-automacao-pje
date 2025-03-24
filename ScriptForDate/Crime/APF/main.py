import pandas as pd
import re

def extrair_ano_processo(numero_processo):
    """Extrai o ano do processo a partir do número do processo usando regex."""
    match_ano = re.search(r'\d{7}-\d{2}\.(\d{4})\.', str(numero_processo))
    return int(match_ano.group(1)) if match_ano else None

def comparar_arquivos_csv(arquivo1, arquivo2, coluna_comparacao, coluna_processo1, coluna_processo2, coluna_classe1, coluna_classe2, saida):
    # Carregar os arquivos CSV
    df1 = pd.read_csv(arquivo1, sep=';', encoding='utf-8')
    df2 = pd.read_csv(arquivo2, sep=',', encoding='utf-8')
    
    # Normalizar os valores para garantir comparações corretas
    df1[coluna_comparacao] = df1[coluna_comparacao].str.strip().str.upper()
    df2[coluna_comparacao] = df2[coluna_comparacao].str.strip().str.upper()
    
    # Renomear colunas para diferenciação
    df1 = df1.rename(columns={coluna_processo1: f"{coluna_processo1}_APF", coluna_classe1: f"{coluna_classe1}_APF"})
    df2 = df2.rename(columns={coluna_processo2: f"{coluna_processo2}_AÇÂO", coluna_classe2: f"{coluna_classe2}_AÇÂO"})
    
    # Selecionar apenas as colunas necessárias para a saída
    colunas_necessarias1 = [f"{coluna_processo1}_APF", f"{coluna_classe1}_APF", coluna_comparacao]
    colunas_necessarias2 = [f"{coluna_processo2}_AÇÂO", f"{coluna_classe2}_AÇÂO", coluna_comparacao, "assuntoPrincipal", "nomeTarefa", "poloAtivo"]
    df1 = df1[colunas_necessarias1]
    df2 = df2[colunas_necessarias2]
    
    # Adicionar coluna de ano extraído para ambos os processos
    df1['Ano_APF'] = df1[f"{coluna_processo1}_APF"].apply(extrair_ano_processo)
    df2['Ano_AÇÂO'] = df2[f"{coluna_processo2}_AÇÂO"].apply(extrair_ano_processo)
    
    # Mesclar os dados com base na coluna de comparação
    correspondencias = pd.merge(df1, df2, on=coluna_comparacao, how='inner')
    
    # Filtrar os casos onde o ano da AÇÃO é superior ao ano do APF
    correspondencias = correspondencias[correspondencias['Ano_AÇÂO'] > correspondencias['Ano_APF']]
    
    # Remover registros onde classeJudicial_AÇÂO é 'AuPrFl'
    correspondencias = correspondencias[correspondencias[f"{coluna_classe2}_AÇÂO"] != "AuPrFl"]
    
    # Criar uma nova coluna indicando se o Polo Passivo aparece apenas uma vez
    ocorrencias_polo = correspondencias[coluna_comparacao].value_counts()
    correspondencias['PoloPassivo_Unico'] = correspondencias[coluna_comparacao].map(lambda x: ocorrencias_polo[x] == 1)
    
    # Reorganizar as colunas na ordem desejada
    colunas_ordenadas = [
        f"{coluna_processo1}_APF", "Ano_APF", "nomeTarefa", "Ano_AÇÂO", f"{coluna_processo2}_AÇÂO", 
        coluna_comparacao, f"{coluna_classe1}_APF", f"{coluna_classe2}_AÇÂO", "assuntoPrincipal", "poloAtivo", "PoloPassivo_Unico"
    ]
    correspondencias = correspondencias[colunas_ordenadas]
    
    # Encontrar os registros que estão apenas no primeiro arquivo
    nao_encontrados = df1[~df1[coluna_comparacao].isin(df2[coluna_comparacao])]
    
    # Criar o arquivo de saída
    with pd.ExcelWriter(saida) as writer:
        correspondencias.to_excel(writer, index=False, sheet_name='Correspondências')
        nao_encontrados.to_excel(writer, index=False, sheet_name='Não Encontrados')
    
    print(f'Resultado salvo em {saida}')

# Definir os arquivos e executar a comparação
arquivo1 = "(CR) Processos arquivados.csv"
arquivo2 = "todosProcessosCrime12.02.csv"
coluna_comparacao = "Polo Passivo"
coluna_processo1 = "numeroProcesso"
coluna_processo2 = "numeroProcesso"
coluna_classe1 = "classeJudicial"
coluna_classe2 = "classeJudicial"
saida = "Comparacao_Resultados.xlsx"


comparar_arquivos_csv(arquivo1, arquivo2, coluna_comparacao, coluna_processo1, coluna_processo2, coluna_classe1, coluna_classe2, saida)
