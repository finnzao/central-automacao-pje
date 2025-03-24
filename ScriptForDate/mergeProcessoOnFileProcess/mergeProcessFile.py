import os
import pandas as pd

# Diretório contendo os arquivos CSV
directory = './processos'

# Lista para armazenar os DataFrames
dataframes = []

# Nomes das colunas, conforme fornecido
columns = [
    'poloAtivo', 'poloPassivo', 'numeroProcesso', 'classeJudicial',
    'orgaoJulgador', 'dataChegada', 'conferido', 'nomeTarefa', 
     'tagsProcessoList', 'podeMovimentarEmLote',
    'podeMinutarEmLote', 'podeIntimarEmLote', 'podeDesignarAudienciaEmLote',
    'podeDesignarPericiaEmLote', 'podeRenajudEmLote', 'assuntoPrincipal',
    'cargoJudicial', 'ultimoMovimento', 'descricaoUltimoMovimento'
]

# Iterar sobre todos os arquivos no diretório
for filename in os.listdir(directory):
    if filename.endswith('.csv'):
        file_path = os.path.join(directory, filename)
        try:
            # Ler o arquivo CSV com ponto-e-vírgula como separador
            df = pd.read_csv(file_path, sep=';', usecols=columns, engine='python')
            dataframes.append(df)
        except Exception as e:
            print(f"Erro ao processar o arquivo {filename}: {e}")

# Concatenar todos os DataFrames em um único
if dataframes:
    merged_df = pd.concat(dataframes, ignore_index=True)
    
    # Salvar o resultado em um novo arquivo CSV
    merged_df.to_csv('merged_processos.csv', sep=',', index=False)
    print("Arquivos combinados e salvos como 'merged_processos.csv'.")
else:
    print("Nenhum arquivo válido encontrado para combinar.")
