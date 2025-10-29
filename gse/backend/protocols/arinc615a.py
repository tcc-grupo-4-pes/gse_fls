#!/usr/bin/env python3
"""
Módulo de Sessão ARINC 615A

Contém a classe 'Arinc615ASession' que atua como o
"cérebro" (máquina de estados) para orquestrar o
fluxo de upload completo de 5 passos.

Depende de:
- tftp_client.py (para o transporte)
- arinc_models.py (para construir/parsear LUI/LUR/LUS)

Não contém dependências do Qt (PySide6).
"""

import os
from typing import Callable

# Importa os módulos que criamos
from backend.protocols.tftp_client import TFTPClient
import backend.protocols.arinc_models as models


class Arinc615ASession:
    """
    Orquestra o fluxo de upload ARINC 615A, passo a passo.
    """

    def __init__(
        self,
        tftp_client: TFTPClient,
        logger: Callable[[str], None] = None,
        progress_callback: Callable[[int], None] = None,
    ):
        """
        Inicializa a sessão ARINC.

        :param tftp_client: Uma instância já conectada de TFTPClient.
        :param logger: Callback para enviar mensagens de log (ex: self.signals.log.emit)
        :param progress_callback: Callback para enviar progresso 0-100 (ex: self.signals.progress.emit)
        """
        self.tftp = tftp_client

        # Define callbacks "seguros" que não falham se forem Nones
        self.log = logger or (lambda msg: print(msg))
        self.progress = progress_callback or (lambda pct: None)

    def run_upload_flow(self, file_path: str, part_number: str) -> bool:
        """
        Executa a sequência completa de upload ARINC 615A.
        Lança exceções em caso de falha.

        :param file_path: Caminho completo para o arquivo binário a ser enviado.
        :param part_number: O Part Number (PN) a ser incluído no LUR.
        :return: True se bem-sucedido.
        """

        # Extrai o nome do arquivo (ex: "EMB-0001-021-045.bin")
        header_filename = os.path.basename(file_path)

        # --- PASSO 1: Ler LUI (Load User Information) ---
        self.log("[ARINC] PASSO 1/5: Lendo LUI (system.LUI)...")
        lui_data = self.tftp.read_file("system.LUI")
        lui_info = models.parse_lui_response(lui_data)

        if "error" in lui_info:
            raise Exception(f"Falha ao parsear LUI: {lui_info['error']}")

        self.log(f"[ARINC] LUI recebido. Status: {lui_info['status_name']}")
        print(f"[DEBUG] Conteúdo de lui_info: {lui_info}")
        if int(lui_info["status_code"], 16) not in (
            models.ARINC_STATUS_ACCEPTED,
            models.ARINC_STATUS_COMPLETED_OK,
        ):
            # O ESP32 ARINC usa 0x0003 (COMPLETED_OK) no LUI inicial
            self.log(
                f"[ARINC-AVISO] Status LUI inesperado: {lui_info['status_code_hex']}"
            )

        self.progress(10)

        # --- PASSO 2: Aguardar LUS Inicial (Load Status) ---
        self.log("[ARINC] PASSO 2/5: Aguardando LUS inicial (INIT_LOAD.LUS)...")
        # O tftp.receive_wrq_and_data() abstrai:
        # 1. Espera WRQ
        # 2. Envia ACK(0)
        # 3. Recebe DATA(1)
        # 4. Envia ACK(1)
        lus_data_inicial = self.tftp.receive_wrq_and_data()

        # (Opcional) Validar o conteúdo do LUS inicial
        progress_inicial = models.parse_lus_progress(lus_data_inicial)
        self.log(
            f"[ARINC] LUS inicial recebido. (Progresso reportado: {progress_inicial}%)"
        )
        self.progress(25)

        # --- PASSO 3: Enviar LUR (Load Upload Request) ---
        self.log("[ARINC] PASSO 3/5: Enviando LUR (test.LUR)...")
        lur_payload = models.build_lur_packet(header_filename, part_number)

        if not self.tftp.write_file("test.LUR", lur_payload):
            # A função write_file já terá logado o erro TFTP
            raise Exception("Falha ao enviar LUR (write_file falhou)")

        self.log(
            f"[ARINC] LUR enviado com sucesso para {header_filename} (PN: {part_number})."
        )
        self.progress(40)

        # --- PASSO 4: Servir Arquivo BIN + HASH ---
        self.log(f"[ARINC] PASSO 4/5: Preparando para servir {header_filename}...")

        try:
            self.log(f"[ARINC] Lendo arquivo local: {file_path}")
            with open(file_path, "rb") as f:
                file_data = f.read()
        except Exception as e:
            self.log(f"[ARINC-ERRO] Não foi possível ler o arquivo binário local: {e}")
            raise  # Propaga o erro

        self.log(f"[ARINC] Lidos {len(file_data)} bytes. Calculando HASH SHA-256...")
        hash_data = models.calculate_file_hash(file_data)
        self.log(f"[ARINC] HASH: {hash_data.hex()}")

        # Define um callback interno para mapear o progresso do TFTP (0-100)
        # para o progresso geral da UI (40-70)
        def tftp_progress_callback(pct_0_100: int):
            # Mapeia 0-100 para 40-70 (30% do total)
            total_progress = 40 + int(pct_0_100 * 0.30)
            self.progress(total_progress)

        # O tftp.serve_file_on_rrq() abstrai:
        # 1. Espera RRQ
        # 2. Cria socket efêmero
        # 3. Envia DATA(1..N) do 'file_data'
        # 4. Envia DATA(N+1) do 'hash_data'
        self.tftp.serve_file_on_rrq(
            expected_filename=header_filename,
            file_data=file_data,
            hash_data=hash_data,
            progress_callback=tftp_progress_callback,
        )

        self.log("[ARINC] BIN e HASH servidos com sucesso.")
        self.progress(70)  # Garante que atingiu 70%

        # --- PASSO 5: Aguardar LUS Progresso (50% e 100%) ---
        self.log("[ARINC] PASSO 5/5: Aguardando LUS 50%...")
        lus_50_data = self.tftp.receive_wrq_and_data()
        prog_50 = models.parse_lus_progress(lus_50_data)
        self.log(f"[ARINC] LUS 50% recebido. (Progresso reportado: {prog_50}%)")
        self.progress(85)  # Define progresso estático da UI

        self.log("[ARINC] Aguardando LUS 100%...")
        try:
            lus_100_data = self.tftp.receive_wrq_and_data()
        except TimeoutError:
            self.log(
                "[ARINC-ERRO] Timeout! O dispositivo não enviou o LUS 100% a tempo."
            )
            self.log(
                "[ARINC-ERRO] O alvo pode estar ocupado (flash) ou pode ter falhado."
            )
            # Você deve lançar uma exceção customizada ou retornar um status de falha
            # para que o 'run_upload_flow' pare de forma limpa.
            raise Exception("Falha no LUS 100%: Timeout")
        prog_100 = models.parse_lus_progress(lus_100_data)
        self.log(f"[ARINC] LUS 100% recebido. (Progresso reportado: {prog_100}%)")

        if prog_100 != 100:
            self.log(
                f"[ARINC-AVISO] Progresso final não foi 100% (recebido {prog_100}%)"
            )

        self.progress(100)
        self.log("=" * 30)
        self.log("[ARINC] Fluxo de upload concluído com sucesso.")
        self.log("=" * 30)

        return True
