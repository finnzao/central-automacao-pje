"Verificação BD Obitos com todos os dados Pje"

import pandas as pd

def comparar_nomes_e_salvar_com_processos(arquivo_obitos_path, arquivo_polos_path, output_csv_path, 
                                          coluna_obitos='NOME', colunas_polos=('poloAtivo', 'poloPassivo'), 
                                          coluna_processo='numeroProcesso', 
                                          coluna_orgao_julgador='orgaoJulgador',
                                          chunksize=10**6):

    # Defina a codificação correta com base na codificação real dos arquivos
    encoding = 'utf-8'  # ou 'latin1', dependendo da codificação do seu arquivo

    # Especifica os tipos de dados para garantir que o CPF seja lido como string
    dtype_obitos = {'CPF': str}

    # Função auxiliar para ler arquivos .csv ou .xlsx
    def carregar_arquivo(caminho, usecols, dtype=None):
        if caminho.lower().endswith('.csv'):
            return pd.read_csv(caminho, usecols=usecols, encoding=encoding, dtype=dtype)
        elif caminho.lower().endswith('.xlsx'):
            return pd.read_excel(caminho, usecols=usecols, dtype=dtype)
        else:
            raise ValueError("O arquivo deve ser no formato .csv ou .xlsx")

    # Carrega os dados de óbitos
    obitos_info = carregar_arquivo(arquivo_obitos_path, usecols=['NOME', 'CPF', 'DT_NASCIMENTO', 'PAI', 'MAE'], dtype=dtype_obitos)

    # Converte a coluna de nomes para um set para facilitar a busca
    nomes_obitos = set(obitos_info['NOME'].dropna().tolist())

    # Inicializa lista para armazenar os resultados
    resultados = []

    # Processa a segunda planilha para comparar com os nomes de óbitos
    if arquivo_polos_path.lower().endswith('.csv'):
        reader = pd.read_csv(arquivo_polos_path, usecols=[*colunas_polos, coluna_processo, coluna_orgao_julgador], 
                             chunksize=chunksize, encoding=encoding ,sep=',' )
    elif arquivo_polos_path.lower().endswith('.xlsx'):
        reader = pd.read_excel(arquivo_polos_path, usecols=[*colunas_polos, coluna_processo, coluna_orgao_julgador], 
                               chunksize=chunksize)
    else:
        raise ValueError("O arquivo deve ser no formato .csv ou .xlsx")

    for chunk in reader:
        # Adiciona as colunas "poloAtivoObito" e "poloPassivoObito" verificando se o nome está nos óbitos
        chunk['poloAtivoObito'] = chunk[colunas_polos[0]].apply(lambda nome: nome if nome in nomes_obitos else None)
        chunk['poloPassivoObito'] = chunk[colunas_polos[1]].apply(lambda nome: nome if nome in nomes_obitos else None)

        # Filtra somente as linhas que têm correspondência com óbitos em "poloAtivoObito" ou "poloPassivoObito"
        chunk_resultado = chunk[['numeroProcesso', 'poloAtivoObito', 'poloPassivoObito', coluna_orgao_julgador]].dropna(how='all', subset=['poloAtivoObito', 'poloPassivoObito'])

        if not chunk_resultado.empty:
            # Cria a coluna "POLO" com base em qual polo (ativo ou passivo) o nome foi encontrado
            chunk_resultado['POLO'] = chunk_resultado.apply(lambda row: 'ATIVO' if pd.notnull(row['poloAtivoObito']) else 'PASSIVO', axis=1)

            # Verifica em qual coluna (polo ativo ou passivo) o nome corresponde ao óbito e faz o merge com as informações adicionais
            chunk_resultado['NOME_Obito'] = chunk_resultado['poloAtivoObito'].combine_first(chunk_resultado['poloPassivoObito'])

            # Faz o merge com as informações adicionais da tabela de óbitos
            chunk_resultado = pd.merge(chunk_resultado, obitos_info, left_on='NOME_Obito', right_on='NOME', how='left')

            # Seleciona as colunas que serão salvas (número do processo, órgão julgador, CPF, DT_NASCIMENTO, PAI, MAE e POLO)
            chunk_resultado_final = chunk_resultado[['numeroProcesso', coluna_orgao_julgador, 'NOME_Obito', 'CPF', 'DT_NASCIMENTO', 'PAI', 'MAE', 'POLO']]

            # Renomeia as colunas para manter o padrão correto
            chunk_resultado_final.columns = ['numeroProcesso', 'orgaoJulgador', 'NOME_Obito', 'CPF', 'DT_NASCIMENTO', 'PAI', 'MAE', 'POLO']

            # Adiciona os resultados do chunk processado à lista
            resultados.append(chunk_resultado_final)

    # Concatena todos os chunks processados
    if resultados:
        df_resultado = pd.concat(resultados)

        # Salva o resultado em um novo arquivo CSV com a codificação correta
        df_resultado.to_csv(output_csv_path, index=False, encoding='utf-8')
        print(f"Resultado com os números de processo e dados adicionais salvo em '{output_csv_path}' com sucesso!")
    else:
        print("Nenhum resultado encontrado para salvar.")

# Uso da função
comparar_nomes_e_salvar_com_processos('./docs/Obitos_10anos_scc.csv', './docs/merged_processos.csv', 'Possiveis_Obitos_Processos.csv')
