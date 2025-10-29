#!/usr/bin/env python3
"""
Módulo do Worker ARINC 615A

Define o QRunnable 'ArincWorker' que executa o
processo de upload em uma thread separada,
evitando que a GUI congele.

Ele atua como a "cola" entre o 'UploadController' (Qt)
e a 'Arinc615ASession' (lógica pura).
"""

import traceback
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

# Importa os módulos de protocolo que criamos
from backend.protocols.tftp_client import TFTPClient
from backend.protocols.arinc615a import Arinc615ASession


class WorkerSignals(QObject):
    """
    Define os sinais disponíveis para um 'worker' thread.
    - log: Emite uma mensagem de log (str)
    - progress: Emite o progresso (int 0-100)
    - finished: Emite quando o trabalho termina (bool_success)
    """

    log = Signal(str)
    progress = Signal(int)
    finished = Signal(bool)


class ArincWorker(QRunnable):
    """
    Worker thread que executa a lógica de transferência ARINC.
    """

    def __init__(self, ip: str, file_path: str, pn: str, signals: WorkerSignals):
        """
        :param ip: IP do target (ex: "192.168.4.1")
        :param file_path: Caminho completo do arquivo BIN a ser enviado
        :param pn: Part Number (ex: "EMB-0001-021-045")
        :param signals: Instância de WorkerSignals para comunicação com a thread principal
        """
        super().__init__()
        self.ip = ip
        self.file_path = file_path
        self.pn = pn
        self.signals = signals

    @Slot()
    def run(self):
        """
        A função principal do worker, executada na QThreadPool.
        Configura e executa a sessão ARINC 615A.
        """
        self.signals.log.emit(f"[WORKER] Iniciando thread para {self.ip}...")
        client = None

        try:
            # 1. Define os callbacks que a sessão ARINC usará para
            #    se comunicar de volta com a thread da GUI.
            def logger(msg):
                self.signals.log.emit(msg)

            def progress(pct):
                self.signals.progress.emit(pct)

            # 2. Monta as dependências
            # Instancia o transportador (TFTP)
            client = TFTPClient(self.ip, logger=logger)

            # Conecta o transportador
            if not client.connect():
                raise Exception("Falha ao criar socket principal do TFTPClient")

            # Instancia o cérebro (ARINC) e injeta as dependências
            session = Arinc615ASession(
                tftp_client=client, logger=logger, progress_callback=progress
            )

            # 3. Executa o fluxo principal
            # O 'session' agora cuida de todos os 5 passos.
            session.run_upload_flow(self.file_path, self.pn)

            # 4. Reporta sucesso
            self.signals.finished.emit(True)

        except Exception as e:
            # 5. Reporta falha
            self.signals.log.emit(f"[WORKER-ERRO] Erro fatal na thread: {e}")
            self.signals.log.emit(traceback.format_exc())  # Log detalhado do erro
            self.signals.finished.emit(False)

        finally:
            # 6. Limpeza
            if client:
                client.close()
            self.signals.log.emit("[WORKER] Thread encerrada e sockets limpos.")
