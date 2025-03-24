from selenium import webdriver
from selenium.common.exceptions import (
    StaleElementReferenceException,
    ElementClickInterceptedException,
    TimeoutException,
    NoSuchElementException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from openpyxl import Workbook
from openpyxl.styles import Font
from functools import wraps
import time
from dotenv import load_dotenv
import os
import logging
import re

# Configuração básica do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("script_log_getDatePartiesByTag.log"),
        logging.StreamHandler()
    ]
)

class PJEAutomation:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.process_data_list = []

    # Decorador para gerenciar tentativas de execução com retry
    def retry(max_retries=2):
        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                retries = 0
                while retries < max_retries:
                    try:
                        return func(self, *args, **kwargs)
                    except (TimeoutException, StaleElementReferenceException) as e:
                        retries += 1
                        logging.warning(f"Tentativa {retries} falhou com erro: {e}. Tentando novamente...")
                        if retries >= max_retries:
                            logging.error(f"Falha ao executar {func.__name__} após {max_retries} tentativas")
                            raise TimeoutException(f"Falha ao executar {func.__name__} após {max_retries} tentativas")
            return wrapper
        return decorator

    def initialize_driver(self):
        # Configurações do Chrome
        chrome_options = webdriver.ChromeOptions()

        # Diretório para onde os downloads serão salvos
        download_directory = os.path.abspath("C:/Users/lfmdsantos/Downloads/processosBaixados")  # Altere para o caminho desejado

        # Criar o diretório se não existir
        os.makedirs(download_directory, exist_ok=True)

        # Configurações de preferências
        prefs = {
            "plugins.always_open_pdf_externally": True,  # Baixar PDFs em vez de abrir no navegador
            "download.default_directory": download_directory,  # Diretório padrão de download
            "download.prompt_for_download": False,  # Não perguntar onde salvar
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True  # Habilitar navegação segura
        }

        chrome_options.add_argument("--disable-extensions")  # Desativa extensões
        chrome_options.add_argument("--no-sandbox")  # Ignora restrições de segurança
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_experimental_option("prefs", prefs)
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 120, poll_frequency=2, ignored_exceptions=[NoSuchElementException])
        logging.info("Driver inicializado com sucesso.")

    @retry()
    def login(self, user, password):
        login_url = 'https://pje.tjba.jus.br/pje/login.seam'
        self.driver.get(login_url)
        logging.info(f"Navegando para a URL de login: {login_url}")

        self.wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, 'ssoFrame')))
        logging.info("Alternado para o frame 'ssoFrame'.")

        username_input = self.wait.until(EC.presence_of_element_located((By.ID, 'username')))
        password_input = self.wait.until(EC.presence_of_element_located((By.ID, 'password')))
        login_button = self.wait.until(EC.presence_of_element_located((By.ID, 'kc-login')))

        username_input.send_keys(user)
        password_input.send_keys(password)
        logging.info("Credenciais inseridas.")

        login_button.click()
        logging.info("Botão de login clicado.")

        self.driver.switch_to.default_content()
        logging.info("Voltando para o conteúdo principal após o login.")

    @retry()
    def select_profile(self, profile):
        dropdown = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'dropdown-toggle')))
        dropdown.click()
        logging.info("Dropdown de perfil clicado.")

        button_xpath = f"//a[contains(text(), '{profile}')]"
        desired_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
        self.driver.execute_script("arguments[0].scrollIntoView(true);", desired_button)
        self.driver.execute_script("arguments[0].click();", desired_button)
        logging.info(f"Perfil '{profile}' selecionado com sucesso.")

    @retry()
    def search_on_tag(self, search):
        self.switch_to_ng_frame()
        logging.info("Alternado para o frame 'ngFrame'.")

        original_handles = set(self.driver.window_handles)
        logging.info(f"Handles originais das janelas: {original_handles}")

        self.nav_tag()
        self.input_tag(search)

    def nav_tag(self):
        xpath = "/html/body/app-root/selector/div/div/div[1]/side-bar/nav/ul/li[5]/a"
        self.click_element(xpath)
        logging.info("Navegando para a seção de etiquetas.")

    def input_tag(self, search_text):
        search_input = self.wait.until(EC.element_to_be_clickable((By.ID, "itPesquisarEtiquetas")))
        search_input.clear()
        search_input.send_keys(search_text)
        logging.info(f"Texto de pesquisa inserido: {search_text}")

        # Capturar os handles antes do clique
        current_handles = set(self.driver.window_handles)

        self.click_element("/html/body/app-root/selector/div/div/div[2]/right-panel/div/etiquetas/div[1]/div/div[1]/div[2]/div[1]/span/button[1]")
        logging.info("Botão de pesquisa de etiquetas clicado.")

        # Esperar até que uma nova janela seja aberta, se aplicável
        time.sleep(2)  # Ajuste conforme necessário

        # Capturar os handles após o clique
        new_handles = set(self.driver.window_handles)

        # Verificar se uma nova janela foi aberta
        if len(new_handles) > len(current_handles):
            data_window = (new_handles - current_handles).pop()
            self.driver.switch_to.window(data_window)
            logging.info(f"Alternado para a nova janela de pesquisa de etiquetas: {data_window}")

            # Fechar a nova janela após a interação, se necessário
            self.driver.close()
            logging.info("Nova janela de pesquisa de etiquetas fechada.")

            # Voltar para a janela original
            self.driver.switch_to.default_content()
            logging.info("Retornado para a janela original após fechar a nova janela.")
        else:
            logging.info("Nenhuma nova janela foi aberta após a pesquisa de etiquetas.")

        # Continuar com a navegação
        self.click_element("/html/body/app-root/selector/div/div/div[2]/right-panel/div/etiquetas/div[1]/div/div[2]/ul/p-datalist/div/div/ul/li/div/li/div[2]/span/span")
        logging.info("Etiqueta selecionada na lista de resultados.")

    def get_process_list(self):
        """
        Retorna uma lista de elementos que representam os processos encontrados.
        """
        try:
            # XPath para localizar todos os itens da lista de processos
            process_xpath = "//processo-datalist-card"
            processes = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, process_xpath)))
            logging.info(f"Número de processos encontrados: {len(processes)}")
            return processes
        except Exception as e:
            self.driver.save_screenshot("get_process_list_exception.png")
            logging.error(f"Ocorreu uma exceção ao obter a lista de processos. Captura de tela salva como 'get_process_list_exception.png'. Erro: {e}")
            raise e

    def click_on_process(self, process_element):
        try:
            original_handles = set(self.driver.window_handles)
            self.driver.execute_script("arguments[0].scrollIntoView(true);", process_element)
            self.driver.execute_script("arguments[0].click();", process_element)
            logging.info("Processo clicado com sucesso!")

            # Alternar para a nova janela aberta após clicar no processo
            new_window_handle = self.switch_to_new_window(original_handles)
            logging.info(f"Alternado para a nova janela do processo: {new_window_handle}")
            return new_window_handle

        except Exception as e:
            self.driver.save_screenshot("click_on_process_exception.png")
            logging.error(f"Ocorreu uma exceção ao clicar no processo. Captura de tela salva como 'click_on_process_exception.png'. Erro: {e}")
            raise e

    def switch_to_new_window(self, original_handles, timeout=20):
        """
        Alterna para a nova janela que foi aberta após a execução de uma ação.

        :param original_handles: Set contendo os handles das janelas originais.
        :param timeout: Tempo máximo de espera para a nova janela aparecer.
        :return: Handle da nova janela.
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: len(d.window_handles) > len(original_handles)
            )
            new_handles = set(self.driver.window_handles) - original_handles
            if new_handles:
                new_window = new_handles.pop()
                self.driver.switch_to.window(new_window)
                logging.info(f"Alternado para a nova janela: {new_window}")
                return new_window
            else:
                raise TimeoutException("Nova janela não foi encontrada dentro do tempo especificado.")
        except TimeoutException as e:
            self.driver.save_screenshot("switch_to_new_window_timeout.png")
            logging.error("TimeoutException: Não foi possível encontrar a nova janela. Captura de tela salva como 'switch_to_new_window_timeout.png'")
            raise e

    @retry()
    def click_element(self, xpath):
        """
        Clica em um elemento localizado pelo XPath fornecido.
        Usa JavaScript como fallback se o clique normal falhar.

        :param xpath: O XPath do elemento a ser clicado.
        """
        try:
            element = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            try:
                element.click()
                logging.info(f"Elemento clicado com sucesso: {xpath}")
            except (ElementClickInterceptedException, Exception) as e:
                logging.warning(f"Erro ao clicar no elemento normalmente: {e}. Tentando com JavaScript...")
                self.driver.execute_script("arguments[0].click();", element)
                logging.info(f"Elemento clicado com sucesso usando JavaScript: {xpath}")
        except Exception as e:
            self.driver.save_screenshot("click_element_exception.png")
            logging.error(f"Ocorreu uma exceção ao clicar no elemento. Captura de tela salva como 'click_element_exception.png'. Erro: {e}")
            raise e

    def collect_data_parties(self):
        """
        Coleta informações específicas das partes de um processo e as armazena em um dicionário.
        Se um elemento não for encontrado, atribui um valor padrão e continua.

        Retorna:
            dict: Dicionário contendo os dados coletados.
        """
        try:
            logging.info("Iniciando coleta de dados das partes.")

            data = {}

            # Lista de campos e seus XPaths
            fields = {
                'CPF': '//*[@id="pessoaFisicaViewView:j_id58"]/div/div[2]',
                'Nome Civil': '//*[@id="pessoaFisicaViewView:j_id80"]/div/div[2]',
                'Data de Nascimento': '//*[@id="pessoaFisicaViewView:j_id157"]/div/div[2]',
                'Genitor': '//*[@id="pessoaFisicaViewView:j_id168"]/div/div[2]',
                'Genitora': '//*[@id="pessoaFisicaViewView:j_id179"]/div/div[2]',
            }

            for field_name, xpath in fields.items():
                try:
                    element = self.driver.find_element(By.XPATH, xpath)
                    data[field_name] = element.text.strip()
                    logging.info(f"{field_name}: {data[field_name]}")
                except NoSuchElementException:
                    logging.warning(f"{field_name} não encontrado.")
                    data[field_name] = ''  # Atribuir valor padrão

            logging.info(f"Dados coletados: {data}")
            return data

        except Exception as e:
            logging.error(f"Ocorreu uma exceção ao coletar dados das partes: {e}")
            self.driver.save_screenshot("collectDataParties_exception.png")
            raise e

    def collect_process_info(self):
        """
        Coleta informações adicionais do processo, como classe, assunto, etc.
        """
        try:
            logging.info("Coletando informações adicionais do processo.")

            process_info = {}

            fields = {
                'Classe': '//*[@id="classeProcesso"]',
                'Assunto': '//*[@id="assuntoProcesso"]',
                'Área': '//*[@id="areaProcesso"]',
            }

            for field_name, xpath in fields.items():
                try:
                    element = self.driver.find_element(By.XPATH, xpath)
                    process_info[field_name] = element.text.strip()
                    logging.info(f"{field_name}: {process_info[field_name]}")
                except NoSuchElementException:
                    logging.warning(f"{field_name} não encontrado.")
                    process_info[field_name] = ''  # Atribuir valor padrão

            return process_info

        except Exception as e:
            logging.error(f"Ocorreu uma exceção ao coletar informações do processo: {e}")
            self.driver.save_screenshot("collectProcessInfo_exception.png")
            raise e

    def get_data_parties(self, process_window_handle, process_number, process_info):
        try:
            # Garantir que estamos na janela do processo
            self.driver.switch_to.window(process_window_handle)
            logging.info("Alternado para a janela do processo.")
        
            # Clicar no elemento da navbar para navegar até a seção de partes
            self.click_element('//*[@id="navbar"]/ul/li/a[1]')
            logging.info("Elemento da navbar clicado com sucesso.")
        
            # Esperar até que o polo passivo esteja presente na página
            self.wait.until(EC.presence_of_element_located((By.ID, 'poloPassivo')))
        
            # Encontrar o div com o ID do polo passivo
            polo_div = self.driver.find_element(By.ID, 'poloPassivo')
        
            # Encontrar todos os links das partes dentro do polo passivo
            party_links = polo_div.find_elements(By.CSS_SELECTOR, 'tbody tr td a')
        
            logging.info(f"Encontrado {len(party_links)} partes no polo passivo")
            logging.info(f"Links das partes: {party_links}")
        
            for index in range(len(party_links)):
                # Atualizar a referência dos elementos para evitar StaleElementReferenceException
                polo_div = self.driver.find_element(By.ID, 'poloPassivo')
                party_links = polo_div.find_elements(By.CSS_SELECTOR, 'tbody tr td a')
                party_link = party_links[index]
        
                # Capturar o nome da parte antes de clicar no link
                party_name = party_link.text.strip()
        
                # Salvar os handles antes de clicar
                handles_before_click = set(self.driver.window_handles)
        
                # Clicar no link da parte
                self.driver.execute_script("arguments[0].click();", party_link)
                logging.info("Link da parte clicado")
                acutal_window = self.driver.current_window_handle
                # Esperar por uma nova janela
                WebDriverWait(self.driver, 10).until(EC.new_window_is_opened(handles_before_click))
        
                handles_after_click = set(self.driver.window_handles)
                new_handles = handles_after_click - handles_before_click
        
                party_window_handle = new_handles.pop()
                self.driver.switch_to.window(party_window_handle)
                logging.info("Aba de dados da parte aberta")

                # Coletar dados
                data = self.collect_data_parties()
                data['Número do Processo'] = process_number
                data['Polo'] = 'Passivo'
                data['Nome da Parte'] = party_name

                # Adicionar informações adicionais do processo
                data.update(process_info)

                self.process_data_list.append(data)

                # Fechar a aba de dados da parte
                self.driver.close()
                logging.info("Aba de dados da parte fechada")

                # Retornar para a janela do processo
                self.driver.switch_to.window(process_window_handle)
                logging.info("Retornando para a janela do processo")

                time.sleep(0.5)

        except Exception as e:
            logging.error(f"Falha em coletar dados das partes. Erro: {e}")
            self.driver.save_screenshot("getDataParties_exception.png")
            raise e

    def switch_to_ng_frame(self):
        """
        Alterna o contexto do Selenium para o frame 'ngFrame'.
        """
        try:
            self.driver.switch_to.default_content()
            self.wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, 'ngFrame')))
            logging.info("Alternado para o frame 'ngFrame'.")
        except TimeoutException:
            logging.error("Timeout ao tentar alternar para o frame 'ngFrame'.")
            self.driver.save_screenshot("switch_to_ngFrame_timeout.png")
            raise

    def info_parties_process_on_tag_search(self):
        try:
            original_window = self.driver.current_window_handle  # Salva o handle da janela original (lista de processos)

            # Obter o número total de processos
            self.switch_to_ng_frame()
            process_list = self.get_process_list()
            total_processes = len(process_list)
            logging.info(f"Total de processos a serem processados: {total_processes}")

            for index in range(1, total_processes + 1):  # Ajustar índice para começar em 1
                logging.info(f"Iniciando o processamento do processo {index} de {total_processes}")

                # Garantir que estamos no frame 'ngFrame' antes de cada iteração
                self.switch_to_ng_frame()

                # Gerar o XPath relativo para localizar o processo
                process_xpath = f"(//processo-datalist-card)[{index}]//a/div/span[2]"
                logging.info(f"XPath gerado: {process_xpath}")

                try:
                    # Localizar o elemento do processo
                    process_element = self.wait.until(EC.element_to_be_clickable((By.XPATH, process_xpath)))
                except TimeoutException:
                    logging.error(f"Timeout ao localizar o elemento do processo no índice {index} com XPath: {process_xpath}")
                    self.driver.save_screenshot(f"process_element_{index}_timeout.png")
                    continue  # Pular para o próximo processo

                # Extrair o número do processo
                raw_process_number = process_element.text.strip()
                process_number = re.sub(r'\D', '', raw_process_number)
                if len(process_number) >= 17:
                    process_number = f"{process_number[:7]}-{process_number[7:9]}.{process_number[9:13]}.{process_number[13]}.{process_number[14:16]}.{process_number[16:]}"
                else:
                    process_number = raw_process_number  # Fallback caso o formato esperado não seja encontrado

                logging.info(f"Número do Processo: {process_number}")
                print(process_number)

                # Clicar no elemento do processo e obter o handle da nova janela
                try:
                    process_window_handle = self.click_on_process(process_element)
                except Exception as e:
                    logging.error(f"Falha ao clicar no processo no índice {index}: {e}")
                    self.driver.save_screenshot(f"click_process_{index}_exception.png")
                    continue  # Pular para o próximo processo

                # Coletar informações adicionais do processo
                process_info = self.collect_process_info()

                # Navegar para a página de dados das partes e coletar dados
                try:
                    self.get_data_parties(process_window_handle=process_window_handle, process_number=process_number, process_info=process_info)
                except Exception as e:
                    logging.error(f"Falha ao coletar dados para o processo {process_number}: {e}")
                    self.driver.save_screenshot(f"getDataParties_{process_number}_exception.png")

                # Fechar a aba do processo
                try:
                    self.driver.close()
                    logging.info("Aba do processo fechada com sucesso.")
                except Exception as e:
                    logging.error(f"Falha ao fechar a aba do processo {process_number}: {e}")

                # Retornar para a janela original (lista de processos)
                try:
                    self.driver.switch_to.window(original_window)
                    logging.info("Retornado para a janela original.")
                except Exception as e:
                    logging.error(f"Falha ao retornar para a janela original: {e}")

                time.sleep(1)

            logging.info("Processamento concluído.")

            # Retornar os dados coletados
            return self.process_data_list

        except Exception as e:
            self.driver.save_screenshot("InfoPartiesProcessOnTagSearch_exception.png")
            logging.error(f"Ocorreu uma exceção em 'InfoPartiesProcessOnTagSearch'. Captura de tela salva como 'InfoPartiesProcessOnTagSearch_exception.png'. Erro: {e}")
            raise e

def save_data_to_excel(data_list, filename="dados_partes.xlsx"):
    """
    Salva a lista de dicionários em um arquivo Excel.

    :param data_list: Lista de dicionários contendo os dados a serem salvos.
    :param filename: Nome do arquivo Excel de saída.
    """
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Dados das Partes"

        # Cabeçalhos atualizados em português
        headers = ['Número do Processo', 'Polo', 'Nome da Parte', 'CPF', 'Nome Civil', 'Data de Nascimento', 'Genitor', 'Genitora', 'Classe', 'Assunto', 'Área']
        ws.append(headers)

        # Estilização dos cabeçalhos
        bold_font = Font(bold=True)
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = bold_font

        # Adicionar os dados
        for data in data_list:
            ws.append([
                data.get('Número do Processo', ''),
                data.get('Polo', ''),
                data.get('Nome da Parte', ''),
                data.get('CPF', ''),
                data.get('Nome Civil', ''),
                data.get('Data de Nascimento', ''),
                data.get('Genitor', ''),
                data.get('Genitora', ''),
                data.get('Classe', ''),
                data.get('Assunto', ''),
                data.get('Área', '')
            ])

        # Ajustar a largura das colunas
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter  # Obtém a letra da coluna
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            ws.column_dimensions[column_letter].width = adjusted_width

        # Salvar o arquivo
        wb.save(filename)
        logging.info(f"Dados salvos com sucesso no arquivo '{filename}'.")

    except Exception as e:
        logging.error(f"Ocorreu uma exceção ao salvar os dados no Excel. Erro: {e}")
        raise e

def main():
    load_dotenv()
    automation = PJEAutomation()
    automation.initialize_driver()
    try:
        user, password = os.getenv("USER"), os.getenv("PASSWORD")
        automation.login(user, password)
        profile = os.getenv("PROFILE")
        automation.select_profile("VARA CRIMINAL DE RIO REAL / Direção de Secretaria / Diretor de Secretaria")

        automation.search_on_tag("Possivel OBT")
        process_data_list = automation.info_parties_process_on_tag_search()
        save_data_to_excel(process_data_list)
        time.sleep(5)
    finally:
        automation.driver.quit()
        logging.info("Driver encerrado.")

if __name__ == "__main__":
    main()
