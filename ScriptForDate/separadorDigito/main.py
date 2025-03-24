import pandas as pd
import json

def atribuir_servidor(digito, configuracao):
    """
    Atribui um servidor com base no dígito usando a configuração fornecida.
    """
    for servidor, intervalos in configuracao['intervalos_servidores'].items():
        for intervalo in intervalos:
            if intervalo[0] <= digito <= intervalo[1]:
                return servidor
    return "Desconhecido"

def processar_arquivo(arquivo_entrada, arquivo_configuracao, arquivo_saida):
    with open(arquivo_configuracao, 'r') as f:
        configuracao = json.load(f)

    df = pd.read_excel(arquivo_entrada)

    coluna_processos = configuracao['coluna_processos']
    df['Dígito'] = df[coluna_processos].str.extract(r'-(\d{2})\.')[0].astype(int)

    df['Servidor'] = df['Dígito'].apply(lambda x: atribuir_servidor(x, configuracao))

    df.to_excel(arquivo_saida, index=False)
    print(f"Arquivo salvo em {arquivo_saida}")

if __name__ == "__main__":

    arquivo_configuracao = "configuracao_servidores.json"


    print(f"Configuração salva em {arquivo_configuracao}")

    arquivo_entrada = "Felipe.xlsx" 
    arquivo_saida = "processos_com_servidores.xlsx"
    processar_arquivo(arquivo_entrada, arquivo_configuracao, arquivo_saida)
