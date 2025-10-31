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
import shutil  # NOVO: Importado para operações de cópia de arquivo
from PySide6.QtCore import QObject, QThreadPool, Signal, Slot, QCoreApplication

# Importa o novo Worker e os Sinais
from backend.workers.arinc_worker import ArincWorker, WorkerSignals

# NOVO: Importa o logger de arquivo
from backend.logs.gse_logger import GseLogger

# NOVO: Define a pasta de armazenamento interno
GSE_STORAGE_DIR = "gse_storage"


class UploadController(QObject):
    """
    O Backend/Controller que se comunica com o QML.
    Ele gerencia a 'thread pool' e os 'workers'.
    """

    # Sinais que o QML vai ouvir
    logMessage = Signal(str)
    progressChanged = Signal(int)
    transferStarted = Signal(str)  # MODIFICADO: Envia o IP
    transferFinished = Signal(bool)

    # Sinal para atualizar PN/Imagem na UI
    fileDetailsReady = Signal(str, str)  # (pn, filename)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.threadpool = QThreadPool()

        # NOVO: Inicializa o logger de arquivo
        # Isso cria o arquivo logs/GSE_Sessao_...txt
        self.file_logger = GseLogger()

        self.selected_path = ""
        self.selected_pn = ""

        # NOVO: Log de "quem acessou" (início da sessão)
        # O print() original foi removido e substituído por este handler
        self._log_handler(f"--- SESSÃO GSE INICIADA ---")
        self._log_handler(
            f"Controlador de Upload inicializado. Threads: {self.threadpool.maxThreadCount()}"
        )
        self._log_handler(f"Log de sessão salvo em: {self.file_logger.get_log_path()}")

    # ========================================================================
    # NOVO: Handler de Log Centralizado
    # ========================================================================
    def _log_handler(self, message: str):
        """
        Um handler privado que envia logs para DOIS lugares:
        1. Para a UI (QML) através do sinal logMessage.
        2. Para o arquivo de log (GseLogger).
        """
        try:
            if "[erro]" in message.lower() or "[auth-erro]" in message.lower():
                # Opcional: printar erros no console também
                print(message)

            # 1. Envia para o QML
            self.logMessage.emit(message)

            # 2. Envia para o arquivo de log
            if self.file_logger:
                self.file_logger.write_log(message)

        except Exception as e:
            # Evita que o logger quebre a aplicação
            print(f"ERRO NO LOG HANDLER: {e}")

    # ========================================================================

    def parse_pn_from_filename(self, filename: str) -> str:
        """
        Extrai o PN do nome do arquivo.
        REQ: GSE-LLR-12
        """
        # Exemplo: "EMB-0001-021-045.bin" -> "EMB-0001-021-045"
        # Implementação simples baseada no nome do arquivo
        base_name = os.path.splitext(filename)[0]
        if base_name.startswith("EMB-"):
            return base_name

        # Fallback se não encontrar o padrão
        # (Você pode querer uma lógica mais robusta aqui)
        return "PN_NAO_ENCONTRADO"

    @Slot(str)
    def handleImageSelected(self, path: str):
        """
        Chamado pelo QML (FileDialog) quando um arquivo é selecionado.
        NOVO: Agora copia o arquivo para o armazenamento interno.
        """
        # Loga o caminho original selecionado pelo operador
        self._log_handler(f"Arquivo selecionado pelo operador: {path}")
        if not path:
            return

        # ====================================================================
        # NOVO: Lógica de Importação de Arquivo (REQ GSE-XXX)
        # ====================================================================
        try:
            # Garante que o caminho de destino seja absoluto
            storage_dir = os.path.abspath(GSE_STORAGE_DIR)
            os.makedirs(storage_dir, exist_ok=True)

            filename = os.path.basename(path)
            # O novo caminho é o arquivo dentro da pasta interna
            new_path = os.path.join(storage_dir, filename)

            self._log_handler(
                f"Importando arquivo para o armazenamento interno do GSE..."
            )

            # Executa a cópia (sobrescreve se já existir)
            shutil.copy(path, new_path)

            self._log_handler(f"Arquivo importado com sucesso para: {new_path}")

        except Exception as e:
            self._log_handler(
                f"[ERRO] Falha ao importar o arquivo para o controle do GSE: {e}"
            )
            self._log_handler(
                "[ERRO] A transferência não pode continuar. Verifique as permissões do GSE."
            )
            # Limpa a seleção para evitar transferência de um arquivo inválido
            self.selected_path = ""
            self.selected_pn = ""
            # Informa a UI da falha
            self.fileDetailsReady.emit("", f"Falha na importação: {e}")
            return
        # ====================================================================

        # Armazena o NOVO caminho (o caminho interno)
        self.selected_path = new_path
        # (filename já foi extraído acima)

        # Extrai o PN (REQ: GSE-LLR-12)
        self.selected_pn = self.parse_pn_from_filename(filename)

        self._log_handler(f"PN detectado: {self.selected_pn}")

        # Envia os detalhes de volta para a UI
        # self.selected_path agora contém o novo caminho interno
        self.fileDetailsReady.emit(self.selected_pn, self.selected_path)

    @Slot(str)
    def startTransfer(self, ip_address: str):
        """
        Chamado pelo QML (Botão "Transferir").
        Inicia o ArincWorker em uma nova thread.
        """

        # MODIFICADO: Usa o novo handler de log
        if not self.selected_path or not self.selected_pn:
            # self.logMessage.emit("[erro] Nenhum arquivo ou PN válido selecionado.")
            self._log_handler("[erro] Nenhum arquivo ou PN válido selecionado.")
            return
        if "PN_NAO_ENCONTRADO" in self.selected_pn:
            # self.logMessage.emit(...)
            self._log_handler(
                "[erro] PN inválido. Não é possível iniciar a transferência."
            )
            return

        # NOVO: Log de "quem acessou" (tentativa de transmissão)
        # (Você pode substituir 'OPERADOR_PADRAO' por uma variável de usuário se tiver login)
        self.username = "OPERADOR_PADRAO"
        self._log_handler(f"Usuário [{self.username}] iniciou a transferência.")
        self._log_handler(f"Alvo (BC): {ip_address}")

        # MODIFICADO: Usa o novo handler de log
        # self.logMessage.emit(...)
        self._log_handler(
            f"Iniciando transferência de {self.selected_path} para {ip_address}..."
        )
        self.progressChanged.emit(0)

        # 1. Avisa o QML que a transferência começou
        # self.transferStarted.emit()
        self.transferStarted.emit(ip_address)  # MODIFICADO

        # 2. Cria os sinais e o NOVO worker
        worker_signals = WorkerSignals()
        worker = ArincWorker(
            ip=ip_address,
            file_path=self.selected_path,  # Agora usa o caminho interno
            pn=self.selected_pn,
            signals=worker_signals,
        )

        # 3. MODIFICADO: Conecta os sinais do worker ao
        #    nosso NOVO handler de log centralizado.
        # worker_signals.log.connect(self.logMessage)
        worker_signals.log.connect(self._log_handler)
        worker_signals.progress.connect(self.progressChanged)
        worker_signals.finished.connect(self.transferFinished)

        # 4. Inicia o worker na thread pool
        self.threadpool.start(worker)

    @Slot()
    def requestLogout(self):
        """Chamado pelo botão Sair do QML"""

        # MODIFICADO: Usa o novo handler de log
        # self.logMessage.emit("Solicitação de logout recebida. Encerrando aplicação.")
        self._log_handler("Solicitação de logout recebida. Encerrando aplicação.")

        # NOVO: Fecha o arquivo de log antes de sair
        if self.file_logger:
            self.file_logger.close()

        QCoreApplication.quit()
