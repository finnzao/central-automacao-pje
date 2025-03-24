import streamlit as st
import pandas as pd
import json
import os

# Caminho do arquivo de configuração
CONFIG_FILE = "configuracao.json"

# Função para atribuir servidor
def atribuir_servidor(digito, configuracao):
    for servidor, intervalos in configuracao['intervalos_servidores'].items():
        for intervalo in intervalos:
            if intervalo[0] <= digito <= intervalo[1]:
                return servidor
    return "Desconhecido"

# Processar planilha Excel
def processar_excel(planilha, configuracao):
    df = pd.read_excel(planilha)
    return processar_dataframe(df, configuracao)

# Processar arquivo CSV
def processar_csv(planilha, configuracao, delimiter):
    df = pd.read_csv(planilha, delimiter=delimiter)
    return processar_dataframe(df, configuracao)

# Processar DataFrame
def processar_dataframe(df, configuracao):
    coluna_processos = configuracao['coluna_processos']
    # Extração do dígito com tratamento de NaN
    df['Dígito'] = df[coluna_processos].str.extract(r'-(\d{2})\.')[0]
    df['Dígito'] = pd.to_numeric(df['Dígito'], errors='coerce')  # Converte para números, mantendo NaN
    df['Dígito'] = df['Dígito'].fillna(0).astype(int)  # Substitui NaN por 0 e converte para inteiro
    # Atribuir servidores
    df['Servidor'] = df['Dígito'].apply(lambda x: atribuir_servidor(x, configuracao))
    return df

# Inicializar o estado
if "configuracao" not in st.session_state:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            st.session_state.configuracao = json.load(f)
    else:
        st.session_state.configuracao = {
            "intervalos_servidores": {
                "Abel": [[1, 17]],
                "Carlos": [[18, 34]],
                "Jackmara": [[35, 51]],
                "LEIDIANE": [[52, 68]],
                "Tânia": [[69, 85]],
                "Eneida": [[86, 99], [0, 0]]
            },
            "coluna_processos": "Processos"
        }

if "servidor_selecionado" not in st.session_state:
    st.session_state.servidor_selecionado = "Adicionar Novo"

# Formulário de configuração
st.title("Processador de Planilhas - Atribuição de Servidores")
st.sidebar.header("Configuração")

coluna_processos = st.sidebar.text_input(
    "Nome da coluna dos processos:", st.session_state.configuracao["coluna_processos"]
)

# Configurações para CSV
st.sidebar.subheader("Configurações de CSV")
csv_delimiter = st.sidebar.text_input("Delimitador para CSV:", value=";")

# Upload de arquivo
uploaded_file = st.file_uploader("Envie sua planilha (Excel ou CSV)", type=["xlsx", "csv"])
if uploaded_file:
    try:
        if uploaded_file.name.endswith(".xlsx"):
            df_resultado = processar_excel(uploaded_file, st.session_state.configuracao)
        elif uploaded_file.name.endswith(".csv"):
            df_resultado = processar_csv(uploaded_file, st.session_state.configuracao, csv_delimiter)
        else:
            st.error("Formato de arquivo não suportado. Envie um arquivo .xlsx ou .csv.")
        
        st.success("Arquivo processado com sucesso!")
        st.dataframe(df_resultado)

        # Opção para download
        output_file = "arquivo_processado.xlsx"
        df_resultado.to_excel(output_file, index=False)
        with open(output_file, "rb") as f:
            st.download_button(
                label="Baixar arquivo processado",
                data=f,
                file_name="arquivo_processado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")

# Salvar configuração
if st.sidebar.button("Salvar Configuração"):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(st.session_state.configuracao, f, indent=4)
    st.sidebar.success("Configuração salva com sucesso!")
