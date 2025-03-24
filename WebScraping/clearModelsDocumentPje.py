import re
import json  # Importado para salvar erros em JSON
import time
import os
from functools import wraps
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    NoSuchElementException,
)

# Variáveis globais para driver e wait
driver = None
wait = None

def switch_to_new_window(original_handles, timeout=20):
    """
    Alterna para a nova janela que foi aberta após a execução de uma ação.
    """
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.window_handles) > len(original_handles)
        )
        new_handles = set(driver.window_handles) - original_handles
        if new_handles:
            new_window = new_handles.pop()
            driver.switch_to.window(new_window)
            print(f"Alternado para a nova janela: {new_window}")
            return new_window
        else:
            raise TimeoutException("Nova janela não foi encontrada dentro do tempo especificado.")
    except TimeoutException as e:
        save_exception_screenshot("switch_to_new_window_timeout.png")
        print("TimeoutException: Não foi possível encontrar a nova janela. Captura de tela salva.")
        raise e

def switch_to_original_window(original_handle):
    """
    Alterna de volta para a janela original.
    """
    try:
        driver.switch_to.window(original_handle)
        print(f"Retornado para a janela original: {original_handle}")
    except Exception as e:
        save_exception_screenshot("switch_to_original_window_exception.png")
        print(f"Erro ao retornar para a janela original. Captura de tela salva. Erro: {e}")
        raise e

def retry(max_retries=2):
    """
    Decorador para tentar novamente a execução de uma função em caso de exceção.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (TimeoutException, StaleElementReferenceException) as e:
                    retries += 1
                    print(f"Tentativa {retries} falhou com erro: {e}. Tentando novamente...")
                    if retries >= max_retries:
                        raise TimeoutException(f"Falha ao executar {func.__name__} após {max_retries} tentativas")
        return wrapper
    return decorator

def initialize_driver():
    """
    Inicializa o driver do Chrome com as configurações desejadas, como pasta de download.
    """
    global driver, wait
    chrome_options = webdriver.ChromeOptions()
    user_home = os.path.expanduser("~")
    download_directory = os.path.join(user_home, "Downloads", "processosBaixadosEtiqueta")
    os.makedirs(download_directory, exist_ok=True)
    print(f"Diretório de download configurado para: {download_directory}")

    prefs = {
        "plugins.always_open_pdf_externally": True,
        "download.default_directory": download_directory,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 50)

def save_exception_screenshot(filename):
    """
    Salva um screenshot atual do driver na pasta '.logs/exception'.
    """
    directory = ".logs/exception"
    if not os.path.exists(directory):
        os.makedirs(directory)
    filepath = os.path.join(directory, filename)
    driver.save_screenshot(filepath)
    print(f"Screenshot salvo em: {filepath}")

@retry()
def acessar_pagina_modelo_documento():
    """
    Acessa a página de modelos de documentos, insere 'Novo' no campo de busca e clica no botão de pesquisa.
    """
    try:
        # Acessar a página do modelo de documento
        driver.get("https://pje.tjba.jus.br/pje/ModeloDocumento/listView.seam")
        
        # Esperar o campo de entrada estar presente e interagível
        input_element = wait.until(
            EC.presence_of_element_located(
                (By.ID, "modeloSearchForm:tituloModeloDocumentoDecoration:tituloModeloDocumento")
            )
        )

        # Clicar no campo e inserir 'Novo'
        input_element.click()
        input_element.send_keys("Novo")

        print("Texto 'Novo' inserido com sucesso no campo de pesquisa de modelo de documento.")

        # Esperar o botão de pesquisa estar presente e interagível
        search_button = wait.until(
            EC.element_to_be_clickable((By.ID, "modeloSearchForm:searchButton"))
        )

        # Clicar no botão de pesquisa
        search_button.click()

        print("Botão 'Pesquisar' clicado com sucesso.")

    except Exception as e:
        save_exception_screenshot("acessar_pagina_modelo_documento_exception.png")
        print(f"Erro ao acessar a página de modelo de documento. Captura de tela salva. Erro: {e}")
        raise e


@retry()
def excluir_todos_modelos():
    """
    Exclui todos os modelos disponíveis na listagem, um por vez, até que a tabela fique vazia.
    Utiliza JavaScript para clicar no botão de exclusão e aguarda corretamente antes de cada clique.
    """
    try:
        while True:
            # Esperar um tempo para garantir que a página carregou antes de tentar excluir
            print("Aguardando 6 segundos antes de verificar a lista de modelos...")
            time.sleep(6)

            # Obter todos os modelos presentes
            modelos_presentes = driver.find_elements(By.XPATH, "//tr[contains(@class, 'rich-table-row')]")
            if not modelos_presentes:
                print("Nenhum modelo restante para excluir.")
                break

            # Selecionar o botão de exclusão usando JavaScript
            script = 'return document.querySelector("#modeloGrid\\\\:0\\\\:j_id262\\\\:modeloGrid");'
            botao_excluir = driver.execute_script(script)

            if botao_excluir:
                print("Botão de exclusão encontrado. Tentando clicar com JavaScript...")

                # Clicar no botão de exclusão usando JavaScript
                driver.execute_script("arguments[0].click();", botao_excluir)
                print("Cliquei para excluir um modelo.")

                # Confirmar a exclusão na janela de alerta (caso apareça)
                try:
                    WebDriverWait(driver, 5).until(EC.alert_is_present())
                    alert = driver.switch_to.alert
                    alert.accept()
                    print("Confirmação de exclusão aceita.")
                except TimeoutException:
                    print("Nenhuma confirmação de alerta encontrada.")

                # Esperar para garantir que a linha foi removida antes de continuar
                print("Aguardando 3 segundos para garantir que o modelo foi removido...")
                time.sleep(3)

                # Atualizar a lista para verificar o próximo modelo
                modelos_restantes = driver.find_elements(By.XPATH, "//tr[contains(@class, 'rich-table-row')]")
                if not modelos_restantes:
                    print("Todos os modelos foram excluídos.")
                    break

                print("Modelo excluído com sucesso. Verificando se há mais modelos...")

            else:
                print("Botão de exclusão não encontrado, encerrando a exclusão.")
                break

    except NoSuchElementException:
        print("Nenhum modelo encontrado para exclusão.")
    except Exception as e:
        save_exception_screenshot("excluir_todos_modelos_exception.png")
        print(f"Erro ao excluir modelos. Captura de tela salva. Erro: {e}")
        raise e

   

@retry()
def login(user, password):
    login_url = 'https://pje.tjba.jus.br/pje/login.seam'
    driver.get(login_url)
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, 'ssoFrame')))
    username_input = wait.until(EC.presence_of_element_located((By.ID, 'username')))
    password_input = wait.until(EC.presence_of_element_located((By.ID, 'password')))
    login_button = wait.until(EC.presence_of_element_located((By.ID, 'kc-login')))
    username_input.send_keys(user)
    password_input.send_keys(password)
    login_button.click()
    driver.switch_to.default_content()

@retry()
def skip_token():
    proceed_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),'Prosseguir sem o Token')]"))
    )
    proceed_button.click()

@retry()
def select_profile(profile):
    dropdown = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'dropdown-toggle')))
    dropdown.click()
    button_xpath = f"//a[contains(text(), '{profile}')]"
    desired_button = wait.until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
    driver.execute_script("arguments[0].scrollIntoView(true);", desired_button)
    driver.execute_script("arguments[0].click();", desired_button)

@retry()
def search_process(classeJudicial='', nomeParte='', numOrgaoJustica='0216', numeroOAB='', estadoOAB=''):
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, 'ngFrame')))
    icon_search_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'li#liConsultaProcessual i.fas')))
    icon_search_button.click()
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, 'frameConsultaProcessual')))
    elemento_num_orgao = wait.until(EC.presence_of_element_located((By.ID, 'fPP:numeroProcesso:NumeroOrgaoJustica')))
    elemento_num_orgao.send_keys(numOrgaoJustica)
   
    # OAB
    if estadoOAB:
        elemento_num_oab = wait.until(EC.presence_of_element_located((By.ID, 'fPP:decorationDados:numeroOAB')))
        elemento_num_oab.send_keys(numeroOAB)
        elemento_estados_oab = wait.until(EC.presence_of_element_located((By.ID, 'fPP:decorationDados:ufOABCombo')))
        lista_estados_oab = Select(elemento_estados_oab)
        lista_estados_oab.select_by_value(estadoOAB)
    
    consulta_classe = wait.until(EC.presence_of_element_located((By.ID, 'fPP:j_id245:classeJudicial')))
    consulta_classe.send_keys(classeJudicial)
    
    elemento_nome_parte = wait.until(EC.presence_of_element_located((By.ID, 'fPP:j_id150:nomeParte')))
    elemento_nome_parte.send_keys(nomeParte)
    
    btn_procurar = wait.until(EC.presence_of_element_located((By.ID, 'fPP:searchProcessos')))
    btn_procurar.click()

@retry()
def preencher_formulario(numProcesso=None, Comp=None, Etiqueta=None):
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.CLASS_NAME, 'ng-frame')))
    if numProcesso:
        num_processo_input = wait.until(EC.presence_of_element_located((By.ID, "itNrProcesso")))
        driver.execute_script("arguments[0].scrollIntoView(true);", num_processo_input)
        num_processo_input.clear()
        num_processo_input.send_keys(numProcesso)
    if Comp:
        competencia_input = wait.until(EC.presence_of_element_located((By.ID, "itCompetencia")))
        driver.execute_script("arguments[0].scrollIntoView(true);", competencia_input)
        competencia_input.clear()
        competencia_input.send_keys(Comp)
    if Etiqueta:
        etiqueta_input = wait.until(EC.presence_of_element_located((By.ID, "itEtiqueta")))
        driver.execute_script("arguments[0].scrollIntoView(true);", etiqueta_input)
        etiqueta_input.clear()
        etiqueta_input.send_keys(Etiqueta)
    
    pesquisar_xpath = "//button[text()='Pesquisar']"
    click_element(pesquisar_xpath)
    print("Formulário preenchido e pesquisa iniciada com sucesso!")
    time.sleep(10)

def input_tag(search_text):
    search_input = wait.until(EC.element_to_be_clickable((By.ID, "itPesquisarEtiquetas")))
    search_input.clear()
    search_input.send_keys(search_text)
    click_element("/html/body/app-root/selector/div/div/div[2]/right-panel/div/etiquetas/div[1]/div/div[1]/div[2]/div[1]/span/button[1]")
    time.sleep(1)
    print(f"Pesquisa realizada com o texto: {search_text}")
    click_element("/html/body/app-root/selector/div/div/div[2]/right-panel/div/etiquetas/div[1]/div/div[2]/ul/p-datalist/div/div/ul/li/div/li/div[2]/span/span")

def nav_tag():
    xpath = "/html/body/app-root/selector/div/div/div[1]/side-bar/nav/ul/li[5]/a"
    click_element(xpath)

def get_process_list():
    """
    Retorna uma lista de elementos representando os processos encontrados.
    """
    try:
        process_xpath = "//processo-datalist-card"
        processes = wait.until(EC.presence_of_all_elements_located((By.XPATH, process_xpath)))
        print(f"Número de processos encontrados: {len(processes)}")
        return processes
    except Exception as e:
        save_exception_screenshot("get_process_list_exception.png")
        print(f"Erro ao obter a lista de processos. Erro: {e}")
        raise e

def click_on_process(process_element):
    """
    Clica no elemento do processo e alterna para a nova janela.
    """
    try:
        original_handles = set(driver.window_handles)
        driver.execute_script("arguments[0].scrollIntoView(true);", process_element)
        driver.execute_script("arguments[0].click();", process_element)
        print("Processo clicado com sucesso!")
        switch_to_new_window(original_handles)
    except Exception as e:
        save_exception_screenshot("click_on_process_exception.png")
        print(f"Erro ao clicar no processo. Erro: {e}")
        raise e

@retry()
def click_element(xpath):
    """
    Clica em um elemento identificado pelo XPath.
    """
    try:
        element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        try:
            element.click()
            print(f"Elemento clicado com sucesso: {xpath}")
        except (ElementClickInterceptedException, Exception) as e:
            print(f"Erro ao clicar normalmente: {e}. Tentando JavaScript...")
            driver.execute_script("arguments[0].click();", element)
            print(f"Elemento clicado com JavaScript: {xpath}")
    except Exception as e:
        save_exception_screenshot("click_element_exception.png")
        print(f"Erro ao clicar no elemento. Captura de tela salva. Erro: {e}")
        raise e

@retry()
def select_tipo_documento(tipoDocumento):
    """
    Seleciona o tipo de documento no dropdown com base no valor informado.
    """
    try:
        select_element = wait.until(EC.presence_of_element_located((By.ID, 'navbar:cbTipoDocumento')))
        select = Select(select_element)
        select.select_by_visible_text(tipoDocumento)
        print(f"Tipo de documento '{tipoDocumento}' selecionado com sucesso.")
    except Exception as e:
        save_exception_screenshot("select_tipo_documento_exception.png")
        print(f"Erro ao selecionar o tipo de documento. Captura de tela salva. Erro: {e}")
        raise e


def main():
    load_dotenv()
    initialize_driver()
    try:
        user, password = os.getenv("USER"), os.getenv("PASSWORD")
        login(user, password)
        select_profile("V DOS FEITOS DE REL DE CONS CIV E COMERCIAIS DE RIO REAL / Direção de Secretaria / Diretor de Secretaria")
        acessar_pagina_modelo_documento()
        excluir_todos_modelos()
        time.sleep(10)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
