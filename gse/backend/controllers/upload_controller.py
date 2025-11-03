#!/usr/bin/env python3
"""
Módulo do Controlador da UI de Upload

Define a classe 'UploadController' (um QObject) que é
exposta ao QML.

Esta classe recebe os eventos da UI (cliques de botão)
e delega o trabalho pesado para o 'ArincWorker'
em uma thread separada.
"""

import os
import shutil  # Importado para operações de cópia de arquivo
from PySide6.QtCore import QObject, QThreadPool, Signal, Slot, QCoreApplication

# Importa o novo Worker e os Sinais
from backend.workers.arinc_worker import ArincWorker, WorkerSignals

# Importa o logger de arquivo
from backend.logsGSE.gse_logger import GseLogger

# ============================================================================
# REQ: GSE-LLR-151: Constante de Armazenamento Interno
# Descrição: O software DEVE definir a constante do diretório de
#   armazenamento interno (GSE_STORAGE_DIR) como "gse_storage".
# Autor: Julia
# Revisor: Fabrício
# ============================================================================
GSE_STORAGE_DIR = "gse_storage"


# ============================================================================
# REQ: GSE-LLR-152: Definição da Interface do Controlador
# Descrição: DEVE existir uma interface de controlador da UI que sirva
#   como ponte de comunicação (via sinais e slots) entre a UI e a
#   lógica de negócios.
#
# Autor: Julia
# Revisor: Fabrício
# ============================================================================
class UploadController(QObject):
    """
    O Backend/Controller que se comunica com o QML.
    Ele gerencia a 'thread pool' e os 'workers'.
    Implementa: GSE-LLR-152 (através da herança de QObject)
    """

    # ============================================================================
    # REQ: GSE-LLR-153: Sinal de Log (UI)
    # Descrição: A interface de controlador da UI DEVE definir um sinal
    #   `logMessage` que emite `str`.
    # ---
    # REQ: GSE-LLR-154: Sinal de Progresso (UI)
    # Descrição: A interface de controlador da UI DEVE definir um sinal
    #   `progressChanged` que emite `int`.
    # ---
    # REQ: GSE-LLR-155: Sinal de Início de Transferência (UI)
    # Descrição: A interface de controlador da UI DEVE definir um sinal
    #   `transferStarted` que emite `str` (o IP do alvo).
    # ---
    # REQ: GSE-LLR-156: Sinal de Fim de Transferência (UI)
    # Descrição: A interface de controlador da UI DEVE definir um sinal
    #   `transferFinished` que emite `bool` (sucesso/falha).
    # ---
    # REQ: GSE-LLR-157: Sinal de Detalhes do Arquivo (UI)
    # Descrição: A interface de controlador da UI DEVE definir um sinal
    #   `fileDetailsReady` que emite `str, str` (o PN e o caminho do arquivo).
    #
    # Autor: Julia
    # Revisor: Fabrício
    # ============================================================================
    logMessage = Signal(str)
    progressChanged = Signal(int)
    transferStarted = Signal(str)
    transferFinished = Signal(bool)
    fileDetailsReady = Signal(str, str)

    # ============================================================================
    # REQ: GSE-LLR-158: Inicialização (Pool de Threads)
    # Descrição: A interface de inicialização do controlador DEVE instanciar
    #   um serviço de gerenciamento de threads (pool de threads) e
    #   armazená-lo para uso futuro.
    # ---
    # REQ: GSE-LLR-159: Inicialização (Logger de Sessão)
    # Descrição: A interface de inicialização do controlador DEVE instanciar o
    #   `GseLogger` e armazená-lo para uso futuro.
    # ---
    # REQ: GSE-LLR-160: Inicialização (Log de Início de Sessão)
    # Descrição: A interface de inicialização do controlador DEVE invocar o
    #   handler de log (GSE-LLR-162) com uma mensagem "SESSÃO GSE INICIADA".
    # ---
    # REQ: GSE-LLR-161: Inicialização (Log de Caminho)
    # Descrição: A interface de inicialização do controlador DEVE logar o
    #   caminho do arquivo de log (obtido da interface do `GseLogger`).
    #
    # Autor: Julia
    # Revisor: Fabrício
    # ============================================================================
    def __init__(self, parent=None):
        """
        Implementa: GSE-LLR-158, 159, 160, 161
        """
        super().__init__(parent)
        # GSE-LLR-158
        self.threadpool = QThreadPool()

        # GSE-LLR-159
        self.file_logger = GseLogger()

        self.selected_path = ""
        self.selected_pn = ""

        # GSE-LLR-160
        self._log_handler(f"--- SESSÃO GSE INICIADA ---")
        self._log_handler(
            f"Controlador de Upload inicializado. Threads: {self.threadpool.maxThreadCount()}"
        )
        # GSE-LLR-161
        self._log_handler(f"Log de sessão salvo em: {self.file_logger.get_log_path()}")

    # ============================================================================
    # REQ: GSE-LLR-162: Interface Interna (Handler de Log)
    # Descrição: DEVE existir uma interface de logging central (handler de log)
    #   que aceite uma `message` (str).
    # ---
    # REQ: GSE-LLR-163: Lógica (Handler de Log - UI)
    # Descrição: A interface de logging central DEVE emitir o sinal `logMessage`
    #   (GSE-LLR-153) com a `message` recebida.
    # ---
    # REQ: GSE-LLR-164: Lógica (Handler de Log - Arquivo)
    # Descrição: A interface de logging central DEVE invocar a interface
    #   de escrita do `GseLogger` com a `message` recebida.
    # ---
    # REQ: GSE-LLR-165: Lógica (Handler de Log - Proteção)
    # Descrição: A interface de logging central DEVE ser encapsulada em um
    #   bloco de tratamento de exceções para garantir que uma falha no
    #   logging não interrompa a aplicação.
    #
    # Autor: Julia
    # Revisor: Fabrício
    # ============================================================================
    def _log_handler(self, message: str):
        """
        Um handler privado que envia logs para DOIS lugares:
        1. Para a UI (QML) através do sinal logMessage.
        2. Para o arquivo de log (GseLogger).
        Implementa: GSE-LLR-162, 163, 164, 165
        """
        # GSE-LLR-165
        try:
            if "[erro]" in message.lower() or "[auth-erro]" in message.lower():
                print(message)

            # GSE-LLR-163
            self.logMessage.emit(message)

            # GSE-LLR-164
            if self.file_logger:
                self.file_logger.write_log(message)

        except Exception as e:
            print(f"ERRO NO LOG HANDLER: {e}")

    # ============================================================================
    # REQ: GSE-LLR-166: Interface Interna (Análise de PN)
    # Descrição: DEVE existir uma interface interna de análise de PN que
    #   aceite um `filename` (str) e retorne o PN (str).
    # ---
    # REQ: GSE-LLR-167: Lógica (Análise de PN - Sucesso)
    # Descrição: A interface interna de análise de PN DEVE extrair o nome
    #   base (sem extensão) e, se o nome base começar com "EMB-",
    #   DEVE retorná-lo.
    # ---
    # REQ: GSE-LLR-168: Lógica (Análise de PN - Falha)
    # Descrição: Se o padrão "EMB-" não for encontrado, a interface interna
    #   de análise de PN DEVE retornar a string "PN_NAO_ENCONTRADO".
    #
    # Autor: Julia
    # Revisor: Fabrício
    # ============================================================================
    def parse_pn_from_filename(self, filename: str) -> str:
        """
        Extrai o PN do nome do arquivo.
        Implementa: GSE-LLR-166, 167, 168
        """
        # GSE-LLR-167
        base_name = os.path.splitext(filename)[0]
        if base_name.startswith("EMB-"):
            return base_name

        # GSE-LLR-168
        return "PN_NAO_ENCONTRADO"

    # ============================================================================
    # REQ: GSE-LLR-169: Interface de Seleção de Imagem (Slot)
    # Descrição: DEVE existir uma interface de seleção de imagem exposta à
    #   camada de UI para receber o `path` (caminho original, str)
    #   do arquivo selecionado pelo operador.
    # ---
    # REQ: GSE-LLR-170: Lógica (Seleção de Imagem - Log)
    # Descrição: A interface de seleção de imagem DEVE logar (via handler de
    #   log) o `path` original selecionado.
    # ---
    # REQ: GSE-LLR-171: Lógica (Importação - Criação de Diretório)
    # Descrição: A interface de seleção de imagem DEVE garantir que o
    #   diretório `GSE_STORAGE_DIR` (GSE-LLR-151) exista.
    # ---
    # REQ: GSE-LLR-172: Lógica (Importação - Definição de Caminho)
    # Descrição: A interface de seleção de imagem DEVE definir um `new_path`
    #   (caminho de destino) como o `filename` (base do `path`) dentro do
    #   `GSE_STORAGE_DIR`.
    # ---
    # REQ: GSE-LLR-173: Lógica (Importação - Cópia de Arquivo)
    # Descrição: A interface de seleção de imagem DEVE copiar o arquivo do
    #   `path` (origem) para o `new_path` (destino).
    # ---
    # REQ: GSE-LLR-174: Lógica (Importação - Sucesso)
    # Descrição: Em caso de sucesso na cópia, a interface de seleção de
    #   imagem DEVE armazenar o `new_path` para uso futuro.
    # ---
    # REQ: GSE-LLR-175: Lógica (Importação - Falha)
    # Descrição: Em caso de falha na cópia (Exceção), a interface de seleção
    #   de imagem DEVE logar um `[ERRO]`, limpar os caminhos e PNs
    #   armazenados, emitir o sinal `fileDetailsReady` (GSE-LLR-157)
    #   com strings vazias e a mensagem de erro, e DEVE retornar.
    # ---
    # REQ: GSE-LLR-176: Lógica (Seleção - Análise de PN)
    # Descrição: A interface de seleção de imagem DEVE, após a cópia,
    #   invocar a interface de análise de PN (GSE-LLR-166).
    # ---
    # REQ: GSE-LLR-177: Lógica (Seleção - Emissão de Sinal)
    # Descrição: A interface de seleção de imagem DEVE emitir o sinal
    #   `fileDetailsReady` (GSE-LLR-157) com o PN analisado e o `new_path`
    #   (o novo caminho interno).
    #
    # Autor: Julia
    # Revisor: Fabrício
    # ============================================================================
    @Slot(str)
    def handleImageSelected(self, path: str):
        """
        Chamado pelo QML (FileDialog) quando um arquivo é selecionado.
        Copia o arquivo para o armazenamento interno.
        Implementa: GSE-LLR-169 a GSE-LLR-177
        """
        # GSE-LLR-170
        self._log_handler(f"Arquivo selecionado pelo operador: {path}")
        if not path:
            return

        # GSE-LLR-175 (try block)
        try:
            # GSE-LLR-171
            storage_dir = os.path.abspath(GSE_STORAGE_DIR)
            os.makedirs(storage_dir, exist_ok=True)

            filename = os.path.basename(path)
            # GSE-LLR-172
            new_path = os.path.join(storage_dir, filename)

            self._log_handler(
                f"Importando arquivo para o armazenamento interno do GSE..."
            )

            # GSE-LLR-173
            shutil.copy(path, new_path)

            self._log_handler(f"Arquivo importado com sucesso para: {new_path}")

        except Exception as e:
            # GSE-LLR-175 (except block)
            self._log_handler(
                f"[ERRO] Falha ao importar o arquivo para o controle do GSE: {e}"
            )
            self._log_handler(
                "[ERRO] A transferência não pode continuar. Verifique as permissões do GSE."
            )
            self.selected_path = ""
            self.selected_pn = ""
            self.fileDetailsReady.emit("", f"Falha na importação: {e}")
            return

        # GSE-LLR-174
        self.selected_path = new_path

        # GSE-LLR-176
        self.selected_pn = self.parse_pn_from_filename(filename)
        self._log_handler(f"PN detectado: {self.selected_pn}")

        # GSE-LLR-177
        self.fileDetailsReady.emit(self.selected_pn, self.selected_path)

    # ============================================================================
    # REQ: GSE-LLR-178: Interface de Início de Transferência (Slot)
    # Descrição: DEVE existir uma interface de início de transferência
    #   exposta à camada de UI para receber o `ip_address` (str) do alvo.
    # ---
    # REQ: GSE-LLR-179: Lógica (Transferência - Validação)
    # Descrição: A interface de início de transferência DEVE validar que o
    #   caminho do arquivo selecionado não está vazio e que o PN não é
    #   "PN_NAO_ENCONTRADO". Se falhar, DEVE logar um `[erro]` e retornar.
    # ---
    # REQ: GSE-LLR-180: Lógica (Transferência - Log de Acesso)
    # Descrição: A interface de início de transferência DEVE logar (via
    #   handler de log) o usuário (ex: "OPERADOR_PADRAO") e o
    #   `ip_address` do alvo.
    # ---
    # REQ: GSE-LLR-181: Lógica (Transferência - Emissão de Sinais UI)
    # Descrição: A interface de início de transferência DEVE emitir
    #   `progressChanged(0)` (GSE-LLR-154) e `transferStarted(ip_address)`
    #   (GSE-LLR-155).
    # ---
    # REQ: GSE-LLR-182: Lógica (Transferência - Criação do Worker)
    # Descrição: A interface de início de transferência DEVE instanciar a
    #   interface de sinais (GSE-LLR-132) e a interface do worker
    #   assíncrona (GSE-LLR-136), injetando o `ip_address`, o caminho
    #   interno, o PN e os sinais.
    # ---
    # REQ: GSE-LLR-183: Lógica (Transferência - Conexão de Sinais)
    # Descrição: A interface de início de transferência DEVE conectar os
    #   sinais do worker aos handlers/sinais da thread principal:
    #   1. `log` DEVE conectar-se ao handler de log (GSE-LLR-162).
    #   2. `progress` DEVE conectar-se a `progressChanged` (GSE-LLR-154).
    #   3. `finished` DEVE conectar-se a `transferFinished` (GSE-LLR-156).
    # ---
    # REQ: GSE-LLR-184: Lógica (Transferência - Início da Thread)
    # Descrição: A interface de início de transferência DEVE iniciar o
    #   worker no serviço de gerenciamento de threads (GSE-LLR-158).
    #
    # Autor: Julia
    # Revisor: Fabrício
    # ============================================================================
    @Slot(str)
    def startTransfer(self, ip_address: str):
        """
        Chamado pelo QML (Botão "Transferir").
        Inicia o ArincWorker em uma nova thread.
        Implementa: GSE-LLR-178 a GSE-LLR-184
        """

        # GSE-LLR-179
        if not self.selected_path or not self.selected_pn:
            self._log_handler("[erro] Nenhum arquivo ou PN válido selecionado.")
            return
        if "PN_NAO_ENCONTRADO" in self.selected_pn:
            self._log_handler(
                "[erro] PN inválido. Não é possível iniciar a transferência."
            )
            return

        # GSE-LLR-180
        self.username = "OPERADOR_PADRAO"
        self._log_handler(f"Usuário [{self.username}] iniciou a transferência.")
        self._log_handler(f"Alvo (BC): {ip_address}")

        self._log_handler(
            f"Iniciando transferência de {self.selected_path} para {ip_address}..."
        )

        # GSE-LLR-181
        self.progressChanged.emit(0)
        self.transferStarted.emit(ip_address)

        # GSE-LLR-182
        worker_signals = WorkerSignals()
        worker = ArincWorker(
            ip=ip_address,
            file_path=self.selected_path,  # Agora usa o caminho interno
            pn=self.selected_pn,
            signals=worker_signals,
        )

        # GSE-LLR-183
        worker_signals.log.connect(self._log_handler)
        worker_signals.progress.connect(self.progressChanged)
        worker_signals.finished.connect(self.transferFinished)

        # GSE-LLR-184
        self.threadpool.start(worker)

    # ============================================================================
    # REQ: GSE-LLR-190: Interface de Logout (Slot)
    # Descrição: DEVE existir uma interface de logout da sessão exposta à
    #   camada de UI para lidar com o encerramento da sessão de upload.
    # ---
    # REQ: GSE-LLR-191: Lógica (Logout - Log)
    # Descrição: A interface de logout da sessão DEVE logar (via handler de
    #   log) a solicitação de encerramento.
    # ---
    # REQ: GSE-LLR-192: Lógica (Logout - Fechamento do Logger)
    # Descrição: A interface de logout da sessão DEVE invocar a interface
    #   de fechamento do `GseLogger` se o logger existir.
    # ---
    # REQ: GSE-LLR-193: Lógica (Logout - Sair da Aplicação)
    # Descrição: A interface de logout da sessão DEVE invocar a função de
    #   encerramento da aplicação.
    #
    # Autor: Julia
    # Revisor: Fabrício
    # ============================================================================
    @Slot()
    def requestLogout(self):
        """
        Chamado pelo botão Sair do QML
        (Nota: No seu 'general.py' este sinal volta ao Login.
         Este aqui encerra o App. Ajuste conforme necessário)
        Implementa: GSE-LLR-190, 191, 192, 193
        """

        # GSE-LLR-191
        self._log_handler("Solicitação de logout recebida. Encerrando aplicação.")

        # GSE-LLR-192
        if self.file_logger:
            self.file_logger.close()

        # GSE-LLR-193
        QCoreApplication.quit()
