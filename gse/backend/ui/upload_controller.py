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
from PySide6.QtCore import QObject, QThreadPool, Signal, Slot, QCoreApplication

# Importa o novo Worker e os Sinais
from backend.workers.arinc_worker import ArincWorker, WorkerSignals

# Remove todas as classes de protocolo (TFTP, ARINC, etc)
# que estavam aqui antes.


class UploadController(QObject):
    """
    O Backend/Controller que se comunica com o QML.
    Ele gerencia a 'thread pool' e os 'workers'.
    """

    # Sinais que o QML vai ouvir
    logMessage = Signal(str)
    progressChanged = Signal(int)
    transferStarted = Signal()
    transferFinished = Signal(bool)

    # Sinal para atualizar PN/Imagem na UI
    fileDetailsReady = Signal(str, str)  # (pn, filename)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.threadpool = QThreadPool()
        print(
            f"UploadController inicializado. Threads: {self.threadpool.maxThreadCount()}"
        )

        self.selected_path = ""
        self.selected_pn = ""

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
        """
        self.logMessage.emit(f"Arquivo selecionado: {path}")
        if not path:
            return

        self.selected_path = path
        filename = os.path.basename(path)

        # Extrai o PN (REQ: GSE-LLR-12)
        self.selected_pn = self.parse_pn_from_filename(filename)
        self.logMessage.emit(f"PN detectado: {self.selected_pn}")
        i = 0
        self.logMessage.emit(f"Teste: {i}")
        i+= 1
        self.logMessage.emit(f"Teste: {i}")
        i+= 1
        self.logMessage.emit(f"Teste: {i}")
        i+= 1
        self.logMessage.emit(f"Teste: {i}")
        i+= 1
        self.logMessage.emit(f"Teste: {i}")
        i+= 1
        self.logMessage.emit(f"Teste: {i}")
        i+= 1
        self.logMessage.emit(f"Teste: {i}")
        i+= 1
        self.logMessage.emit(f"Teste: {i}")
        i+= 1
        self.logMessage.emit(f"Teste: {i}")
        i+= 1
        self.logMessage.emit(f"Teste: {i}")
        i+= 1
        self.logMessage.emit(f"Teste: {i}")
        i+= 1
        self.logMessage.emit(f"Final")


        # Envia os detalhes de volta para a UI
        self.fileDetailsReady.emit(self.selected_pn, path)

    @Slot(str)
    def startTransfer(self, ip_address: str):
        """
        Chamado pelo QML (Botão "Transferir").
        Inicia o ArincWorker em uma nova thread.
        """
        if not self.selected_path or not self.selected_pn:
            self.logMessage.emit("[erro] Nenhum arquivo ou PN válido selecionado.")
            return
        if "PN_NAO_ENCONTRADO" in self.selected_pn:
            self.logMessage.emit(
                "[erro] PN inválido. Não é possível iniciar a transferência."
            )
            return

        self.logMessage.emit(
            f"Iniciando transferência de {self.selected_path} para {ip_address}..."
        )
        self.progressChanged.emit(0)

        # 1. Avisa o QML que a transferência começou
        self.transferStarted.emit()

        # 2. Cria os sinais e o NOVO worker
        worker_signals = WorkerSignals()
        worker = ArincWorker(
            ip=ip_address,
            file_path=self.selected_path,
            pn=self.selected_pn,
            signals=worker_signals,
        )

        # 3. Conecta os sinais do worker aos sinais deste backend
        #    (Isso garante que os sinais sejam tratados na thread principal da GUI)
        worker_signals.log.connect(self.logMessage)
        worker_signals.progress.connect(self.progressChanged)
        worker_signals.finished.connect(self.transferFinished)

        # 4. Inicia o worker na thread pool
        self.threadpool.start(worker)

    @Slot()
    def requestLogout(self):
        """Chamado pelo botão Sair do QML"""
        self.logMessage.emit("Solicitação de logout recebida. Encerrando aplicação.")
        QCoreApplication.quit()
