import pandas as pd
import chardet
from rapidfuzz import fuzz, process
from datetime import datetime
import unicodedata
import re

def log(message):
    """Função simples para exibir mensagens de log."""
    print(f"[LOG] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")

def detectar_encoding(file_path, sample_size=10000):
    """Detects the encoding of a file using chardet."""
    with open(file_path, 'rb') as f:
        data = f.read(sample_size)
        result = chardet.detect(data)
        log(f"Encoding detectado para '{file_path}': {result['encoding']}")
        return result['encoding']

def validar_cpf(cpf):
    """Valida se um CPF é válido."""
    if pd.isna(cpf):  # Verifica se o CPF é nulo
        return False
    cpf = str(cpf).strip()  # Converte para string e remove espaços extras
    if len(cpf) != 11 or not cpf.isdigit():  # Verifica comprimento e se é numérico
        return False
    return True  # Simplificação; aplicar validação completa se necessário

def normalizar_texto(texto):
    """Remove acentos, normaliza para maiúsculo e remove espaços extras."""
    if pd.isna(texto):
        return None
    texto = unicodedata.normalize('NFKD', texto)
    texto = texto.encode('ascii', 'ignore').decode('utf-8').upper()
    return re.sub(r'\s+', ' ', texto).strip()

def comparar_dados_e_salvar(obitos_path_csv, csv_path, output_csv_path, 
                            similarity_threshold=85,
                            columns_to_compare=[('Nome Civil', 'NOME_Obito'), 
                                                ('Data de Nascimento', 'DT_NASCIMENTO'), 
                                                ('Genitor', 'PAI'), 
                                                ('Genitora', 'MAE')],
                            coluna_processo='numeroProcesso'):

    log("Iniciando o processo de comparação de dados.")

    # Detect encoding
    encoding_obitos = detectar_encoding(obitos_path_csv)
    encoding_csv = detectar_encoding(csv_path)

    log("Lendo os arquivos CSV.")
    obitos_info = pd.read_csv(obitos_path_csv, encoding=encoding_obitos, dtype={'CPF': str})
    dados_partes = pd.read_csv(csv_path, encoding=encoding_csv, dtype={'CPF': str})

    log("Normalizando os CPFs e os dados de texto.")
    obitos_info['CPF'] = obitos_info['CPF'].str.replace(r'\D', '', regex=True)
    dados_partes['CPF'] = dados_partes['CPF'].str.replace(r'\D', '', regex=True)

    for parte_col, obito_col in columns_to_compare:
        if parte_col in dados_partes.columns:
            dados_partes[parte_col] = dados_partes[parte_col].apply(normalizar_texto)
        if obito_col in obitos_info.columns:
            obitos_info[obito_col] = obitos_info[obito_col].apply(normalizar_texto)

    log("Iniciando a comparação dos registros.")
    resultados = []
    descartados = []

    for index, parte_row in dados_partes.iterrows():
        log(f"Processando registro {index + 1}/{len(dados_partes)}.")
        cpf_parte = parte_row['CPF']
        nome_civil = parte_row.get('Nome Civil', None)

        match_cpf = None
        if validar_cpf(cpf_parte):
            match_cpf = obitos_info[obitos_info['CPF'] == cpf_parte]

        if match_cpf is not None and not match_cpf.empty:
            log(f"CPF igual encontrado para o registro {index + 1}. Registro adicionado sem verificações adicionais.")
            resultado = {**parte_row.to_dict(), 'Encontrador_atraves': 'CPF'}
            for _, obito_row in match_cpf.iterrows():
                resultado.update({
                    'PAI_obt': obito_row.get('PAI', None),
                    'MAE_obt': obito_row.get('MAE', None),
                    'DT_NASCIMENTO_obt': obito_row.get('DT_NASCIMENTO', None)
                })
            resultados.append(resultado)
            continue

        if validar_cpf(cpf_parte):
            cpf_diferente = obitos_info[(obitos_info['CPF'] != cpf_parte) & (~obitos_info['CPF'].isna())]
            if not cpf_diferente.empty:
                log(f"CPF diferente encontrado para o registro {index + 1}. Registro descartado.")
                descartados.append({**parte_row.to_dict(), 'Motivo': 'CPF diferente'})
                continue

        match_nome = None
        if nome_civil:
            for _, obito_row in obitos_info.iterrows():
                nome_obito = obito_row.get('NOME_Obito', None)
                if nome_obito and fuzz.ratio(nome_civil, nome_obito) >= similarity_threshold:
                    match_nome = obito_row
                    break

        if match_nome is None:
            log(f"Nome não congruente para o registro {index + 1}. Registro descartado.")
            descartados.append({**parte_row.to_dict(), 'Motivo': 'Nome não congruente'})
            continue

        # Comparação dos campos secundários
        campos_congruentes = []
        campos_divergentes = []
        resultado = {**parte_row.to_dict(), 'Encontrador_atraves': 'Dados Secundarios'}

        for parte_col, obito_col in columns_to_compare[1:]:  # Ignora 'Nome Civil'
            val_parte = parte_row.get(parte_col, None)
            val_obito = match_nome.get(obito_col, None)

            resultado[f"{obito_col}_obt"] = val_obito

            if pd.notna(val_parte) and pd.notna(val_obito):
                if parte_col == 'Data de Nascimento':
                    try:
                        data_parte = datetime.strptime(val_parte, '%d/%m/%Y')
                        data_obito = datetime.strptime(val_obito, '%d/%m/%Y')
                        if data_parte == data_obito:
                            campos_congruentes.append(parte_col)
                        else:
                            campos_divergentes.append(parte_col)
                    except ValueError:
                        campos_divergentes.append(parte_col)
                else:
                    if fuzz.ratio(val_parte, val_obito) >= similarity_threshold:
                        campos_congruentes.append(parte_col)
                    else:
                        campos_divergentes.append(parte_col)

        if campos_divergentes:
            log(f"Campos divergentes encontrados no registro {index + 1}: {', '.join(campos_divergentes)}.")
            descartados.append({**parte_row.to_dict(), 'Motivo': f"Campos divergentes: {', '.join(campos_divergentes)}"})
            continue

        if campos_congruentes:
            log(f"Adicionando registro {index + 1} com campos congruentes: {', '.join(campos_congruentes)}.")
            resultado['Campos_Congruentes'] = ', '.join(campos_congruentes)
            resultados.append(resultado)

    log("Removendo campos desnecessários do resultado final.")
    campos_a_remover = ['Classe', 'Assunto', 'Área', 'Nome da Parte']
    for resultado in resultados:
        for campo in campos_a_remover:
            resultado.pop(campo, None)

    log("Salvando os resultados.")
    if resultados:
        final_df = pd.DataFrame(resultados)
        colunas_ordenadas = [
            'numeroProcesso', 'Polo', 'CPF', 'Nome Civil', 'Data de Nascimento',
            'DT_NASCIMENTO_obt', 'Genitor', 'PAI_obt', 'Genitora', 'MAE_obt',
            'Encontrador_atraves', 'Campos_Congruentes'
        ]
        final_df = final_df[colunas_ordenadas]
        final_df.to_csv(output_csv_path, index=False, encoding='utf-8')
        log(f"Resultados salvos em {output_csv_path}.")
    if descartados:
        pd.DataFrame(descartados).to_csv(output_csv_path.replace('.csv', '_descartados.csv'), index=False, encoding='utf-8')
        log(f"Registros descartados salvos em {output_csv_path.replace('.csv', '_descartados.csv')}.")

    log("Processo concluído.")

comparar_dados_e_salvar(
    'Possiveis_Obitos_Processos.csv',
    'dados_partes.csv',
    'resultadoCompareDatePjeAndObt.csv'
)
