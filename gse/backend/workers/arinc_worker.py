#!/usr/bin/env python3
"""
Módulo do Worker ARINC 615A

Define a implementação do worker assíncrono (usando QRunnable) que
executa o processo de upload em uma thread separada,
evitando que a GUI congele.

Ele atua como a "cola" entre o 'UploadController' (Qt)
e a 'Arinc615ASession' (lógica pura).
"""

import traceback
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

# Importa os módulos de protocolo que criamos
from backend.protocols.tftp_client import TFTPClient
from backend.protocols.arinc615a import Arinc615ASession


# ============================================================================
# REQ: GSE-LLR-132: Interface de Sinais do Worker (Definição)
# Descrição: DEVE existir uma interface de sinais para comunicação segura e
#   assíncrona da thread de trabalho para a thread principal da UI.
# ---
# REQ: GSE-LLR-133: Interface de Sinais (Log)
# Descrição: A interface de sinais do worker DEVE definir um sinal `log` que
#   emite `str`.
# ---
# REQ: GSE-LLR-134: Interface de Sinais (Progresso)
# Descrição: A interface de sinais do worker DEVE definir um sinal `progress`
#   que emite `int` (0-100).
# ---
# REQ: GSE-LLR-135: Interface de Sinais (Conclusão)
# Descrição: A interface de sinais do worker DEVE definir um sinal `finished`
#   que emite `bool` (indicando sucesso ou falha).
#
# Autor: Julia
# Revisor: Fabrício
# ============================================================================
class WorkerSignals(QObject):
    """
    Define os sinais disponíveis para um 'worker' thread.
    Implementa: GSE-LLR-132, 133, 134, 135
    """

    log = Signal(str)
    progress = Signal(int)
    finished = Signal(bool)


# ============================================================================
# REQ: GSE-LLR-136: Interface do Worker (Assíncrona)
# Descrição: DEVE existir uma interface de worker assíncrona que execute
#   a lógica de transferência em uma thread separada para não bloquear a UI.
#
# Autor: Julia
# Revisor: Fabrício
# ============================================================================
class ArincWorker(QRunnable):
    """
    Worker thread que executa a lógica de transferência ARINC.
    Implementa: GSE-LLR-136 (através da herança de QRunnable)
    """

    # ============================================================================
    # REQ: GSE-LLR-137: Interface do Worker (Inicialização)
    # Descrição: A interface de worker assíncrona DEVE aceitar e armazenar os
    #   parâmetros de entrada: `ip` (str), `file_path` (str), `pn` (str) e
    #   a interface de sinais (GSE-LLR-132).
    #
    # Autor: Julia
    # Revisor: Fabrício
    # ============================================================================
    def __init__(self, ip: str, file_path: str, pn: str, signals: WorkerSignals):
        """
        Implementa: GSE-LLR-137
        """
        super().__init__()
        self.ip = ip
        self.file_path = file_path
        self.pn = pn
        self.signals = signals

    # ============================================================================
    # REQ: GSE-LLR-138: Execução (Log de Início)
    # Descrição: O método de execução da thread de trabalho DEVE emitir um log
    #   de início (ex: "[WORKER]...") através da interface de sinais.
    # ---
    # REQ: GSE-LLR-139: Execução (Definição de Callbacks)
    # Descrição: O método de execução da thread de trabalho DEVE definir funções
    #   de callback locais (`logger`, `progress`) que, quando chamadas,
    #   DEVEM emitir os sinais correspondentes (`signals.log`, `signals.progress`).
    # ---
    # REQ: GSE-LLR-140: Execução (Instanciação do TFTP)
    # Descrição: O método de execução da thread de trabalho DEVE instanciar a
    #   interface de cliente TFTP (GSE-LLR-091) injetando o `ip` e o
    #   callback `logger`.
    # ---
    # REQ: GSE-LLR-141: Execução (Conexão do TFTP)
    # Descrição: O método de execução da thread de trabalho DEVE invocar a
    #   interface de conexão (GSE-LLR-096) do cliente TFTP. Se a conexão
    #   retornar `False`, DEVE lançar uma exceção.
    # ---
    # REQ: GSE-LLR-142: Execução (Instanciação da Sessão ARINC)
    # Descrição: O método de execução da thread de trabalho DEVE instanciar a
    #   interface de sessão ARINC injetando o cliente TFTP, o callback
    #   `logger` e o callback `progress`.
    # ---
    # REQ: GSE-LLR-143: Execução (Início do Fluxo)
    # Descrição: O método de execução da thread de trabalho DEVE invocar a
    #   interface de fluxo de upload da sessão ARINC utilizando o
    #   `file_path` e o `pn`.
    # ---
    # REQ: GSE-LLR-144: Execução (Reporte de Sucesso)
    # Descrição: Se o fluxo de upload for concluído sem exceções, o método
    #   de execução DEVE emitir o sinal de conclusão (GSE-LLR-135) com
    #   status `True`.
    # ---
    # REQ: GSE-LLR-145: Execução (Tratamento de Exceção)
    # Descrição: O método de execução da thread de trabalho DEVE encapsular
    #   toda a lógica de execução (da instanciação à conclusão) em um
    #   bloco de tratamento de exceções.
    # ---
    # REQ: GSE-LLR-146: Execução (Log de Erro)
    # Descrição: Em caso de exceção, o método de execução DEVE logar a
    #   mensagem de erro (ex: `f"[WORKER-ERRO] {e}"`) através da
    #   interface de sinais.
    # ---
    # REQ: GSE-LLR-147: Execução (Log de Traceback)
    # Descrição: Em caso de exceção, o método de execução DEVE logar o
    #   *traceback* completo da pilha de erros para fins de depuração.
    # ---
    # REQ: GSE-LLR-148: Execução (Reporte de Falha)
    # Descrição: Em caso de exceção, o método de execução DEVE emitir o
    #   sinal de conclusão (GSE-LLR-135) com status `False`.
    # ---
    # REQ: GSE-LLR-149: Execução (Limpeza de Socket)
    # Descrição: O método de execução da thread de trabalho DEVE garantir
    #   (em um bloco `finally`) que a interface de encerramento de socket
    #   (GSE-LLR-097) seja chamada se o cliente TFTP foi instanciado.
    # ---
    # REQ: GSE-LLR-150: Execução (Log de Encerramento)
    # Descrição: O método de execução da thread de trabalho DEVE garantir
    #   (em um bloco `finally`) que um log de encerramento
    #   (ex: "[WORKER] Thread encerrada...") seja emitido pela interface de sinais.
    #
    # Autor: Julia
    # Revisor: Fabrício
    # ============================================================================
    @Slot()
    def run(self):
        """
        A função principal do worker, executada na QThreadPool.
        Configura e executa a sessão ARINC 615A.
        Implementa: GSE-LLR-138 a GSE-LLR-150
        """
        # GSE-LLR-138
        self.signals.log.emit(f"[WORKER] Iniciando thread para {self.ip}...")
        client = None

        # GSE-LLR-145
        try:
            # GSE-LLR-139
            def logger(msg):
                self.signals.log.emit(msg)

            def progress(pct):
                self.signals.progress.emit(pct)

            # GSE-LLR-140
            client = TFTPClient(self.ip, logger=logger)

            # GSE-LLR-141
            if not client.connect():
                raise Exception("Falha ao criar socket principal do TFTPClient")

            # GSE-LLR-142
            session = Arinc615ASession(
                tftp_client=client, logger=logger, progress_callback=progress
            )

            # GSE-LLR-143
            session.run_upload_flow(self.file_path, self.pn)

            # GSE-LLR-144
            self.signals.finished.emit(True)

        except Exception as e:
            # GSE-LLR-146
            self.signals.log.emit(f"[WORKER-ERRO] Erro fatal na thread: {e}")
            # GSE-LLR-147
            self.signals.log.emit(traceback.format_exc())
            # GSE-LLR-148
            self.signals.finished.emit(False)

        finally:
            # GSE-LLR-149
            if client:
                client.close()
            # GSE-LLR-150
            self.signals.log.emit("[WORKER] Thread encerrada e sockets limpos.")
