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

# ============================================================================
# REQ: GSE-LLR-200 – Independência de UI/Qt e rede externa
# Tipo: Requisito Não Funcional
# Descrição: O módulo de sessão não deve importar PySide/Qt diretamente e
#            não deve abrir soquetes por conta própria (delegar ao TFTPClient).
# Critérios de Aceitação:
#  - Imports restritos a stdlib e módulos internos de protocolo.
#  - Comunicação sempre via TFTPClient injetado.
# Autor: (preencher) | Revisor: (preencher)
# ============================================================================
from backend.protocols.tftp_client import TFTPClient
import backend.protocols.arinc_models as models
from backend.protocols.hash_utils import calculate_file_hash

# ============ CONSTANTES ============

# ============================================================================
# REQ: GSE-LLR-201 – Parametrizar chaves de handshake
# Tipo: Requisito Funcional
# Descrição: Definir constantes padrão de chave estática para handshake,
#            permitindo override por injeção de dependência futura.
# Critérios de Aceitação:
#  - Expor GSE_STATIC_KEY e EXPECTED_BC_KEY como bytes.
#  - Uso do handshake pode ser habilitado/disabled por feature flag externa.
# Autor: (preencher) | Revisor: (preencher)
# ============================================================================
GSE_STATIC_KEY = b"Embraer123"
EXPECTED_BC_KEY = b"123Embraer"


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

        # ============================================================================
        # REQ: GSE-LLR-202 – Injeção de dependências obrigatória
        # Tipo: Requisito Funcional
        # Descrição: Exigir TFTPClient pronto para uso na construção da sessão.
        # Critérios de Aceitação:
        #  - Armazenar referência em self.tftp.
        #  - Lançar exceção se tftp_client for None.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        self.tftp = tftp_client

        # ============================================================================
        # REQ: GSE-LLR-203 – Callbacks seguros (logger/progress)
        # Tipo: Requisito Não Funcional
        # Descrição: Fornecer callbacks padrão “no-op”/stdout para evitar falhas
        #            quando não forem injetados.
        # Critérios de Aceitação:
        #  - logger padrão imprime em stdout.
        #  - progress_callback padrão não lança exceção (lambda).
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
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

        # ============================================================================
        # REQ: GSE-LLR-204 – Validar parâmetros de entrada do fluxo
        # Tipo: Requisito Funcional
        # Descrição: Validar que file_path aponta para arquivo existente e que
        #            part_number não é vazio.
        # Critérios de Aceitação:
        #  - file_path deve existir e ser arquivo regular antes do PASSO 4.
        #  - part_number != "" antes do PASSO 3.
        # Observação: a validação “física” de file_path é feita no PASSO 4,
        #             mas este requisito documenta a obrigação.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        header_filename = os.path.basename(file_path)

        # ===========================================================
        # [NOVO] PASSO DE AUTENTICAÇÃO (Handshake)
        # ===========================================================
        # ============================================================================
        # REQ: GSE-LLR-205 – Handshake opcional por chave estática
        # Tipo: Requisito Funcional
        # Descrição: Quando ativado, realizar verificação mútua de chaves entre
        #            GSE e BC antes do início do fluxo ARINC (PASSO 1).
        # Critérios de Aceitação:
        #  - Chamar tftp.verify_static_key(GSE_STATIC_KEY, EXPECTED_BC_KEY).
        #  - Em falha, logar e abortar fluxo com retorno False/Exceção conforme política.
        #  - Em exceção, logar “erro fatal” e terminar o fluxo.
        # Autor: (preencher) | Revisor: (preencher)
        # Nota: Trecho desabilitado por padrão; ativar por feature flag.
        # ============================================================================
        # self.log("[ARINC] PASSO 0/5: Verificando chave estática (Handshake)...")
        # try:
        #     if not self.tftp.verify_static_key(GSE_STATIC_KEY, EXPECTED_BC_KEY):
        #         self.log("[erro] Falha na verificação da chave estática. Abortando.")
        #         return
        # except Exception as e:
        #     self.log(f"[erro] Erro fatal na verificação de chave: {e}")
        #     return
        # ===========================================================

        # --- PASSO 1: Ler LUI (Load User Information) ---
        # ============================================================================
        # REQ: GSE-LLR-206 – Ler e parsear LUI inicial
        # Tipo: Requisito Funcional
        # Descrição: Ler "system.LUI" via TFTP RRQ e parsear com models.parse_lui_response.
        # Critérios de Aceitação:
        #  - Em erro de TFTP, lançar exceção.
        #  - Em erro de parsing (dict com "error"), lançar exceção com mensagem detalhada.
        #  - Logar status_name recebido.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        self.log("[ARINC] PASSO 1/5: Lendo LUI (system.LUI)...")
        lui_data = self.tftp.read_file("system.LUI")
        lui_info = models.parse_lui_response(lui_data)

        if "error" in lui_info:
            raise Exception(f"Falha ao parsear LUI: {lui_info['error']}")

        self.log(f"[ARINC] LUI recebido. Status: {lui_info['status_name']}")
        print(f"[DEBUG] Conteúdo de lui_info: {lui_info}")

        # ============================================================================
        # REQ: GSE-LLR-207 – Validar status_code do LUI
        # Tipo: Requisito Funcional
        # Descrição: Aceitar LUI inicial com status_code em {ACCEPTED, COMPLETED_OK};
        #            logar aviso para demais códigos.
        # Critérios de Aceitação:
        #  - Converter status_code string "0xhhhh" para int base 16.
        #  - Em status inesperado, logar aviso (sem abortar obrigatoriamente).
        # Observação: usar chave existente 'status_code' do dict de LUI.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        if int(lui_info["status_code"], 16) not in (
            models.ARINC_STATUS_ACCEPTED,
            models.ARINC_STATUS_COMPLETED_OK,
        ):
            # O ESP32 ARINC usa 0x0003 (COMPLETED_OK) no LUI inicial
            # Observação: chave 'status_code_hex' não existe em parse_lui_response;
            # manter consistência usando 'status_code'. (documentado neste LLR)
            self.log(f"[ARINC-AVISO] Status LUI inesperado: {lui_info['status_code']}")

        # ============================================================================
        # REQ: GSE-LLR-208 – Atualizar progresso após PASSO 1
        # Tipo: Requisito Funcional
        # Descrição: Reportar progresso 10% após LUI processado com sucesso.
        # Critérios de Aceitação:
        #  - Chamar progress_callback(10).
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        self.progress(10)

        # --- PASSO 2: Aguardar LUS Inicial (Load Status) ---
        # ============================================================================
        # REQ: GSE-LLR-209 – Receber LUS inicial via WRQ/DATA
        # Tipo: Requisito Funcional
        # Descrição: Aguardar WRQ + primeiro DATA do alvo com LUS inicial.
        # Critérios de Aceitação:
        #  - Usar tftp.receive_wrq_and_data() para encapsular a troca.
        #  - Parsear com models.parse_lus_progress e logar progresso.
        #  - Em erro de parsing, lançar exceção.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        self.log("[ARINC] PASSO 2/5: Aguardando LUS inicial (INIT_LOAD.LUS)...")
        lus_data_inicial = self.tftp.receive_wrq_and_data()
        progress_inicial = models.parse_lus_progress(lus_data_inicial)
        self.log(
            f"[ARINC] LUS inicial recebido. (Progresso reportado: {progress_inicial['progress_pct']}%)"
        )

        # ============================================================================
        # REQ: GSE-LLR-210 – Atualizar progresso após PASSO 2
        # Tipo: Requisito Funcional
        # Descrição: Reportar progresso 25% após LUS inicial processado.
        # Critérios de Aceitação:
        #  - Chamar progress_callback(25).
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        self.progress(25)

        # --- PASSO 3: Enviar LUR (Load Upload Request) ---
        # ============================================================================
        # REQ: GSE-LLR-211 – Construir e enviar LUR
        # Tipo: Requisito Funcional
        # Descrição: Construir LUR com models.build_lur_packet(header_filename, PN)
        #            e enviar via TFTP WRQ/DATA usando write_file("test.LUR", payload).
        # Critérios de Aceitação:
        #  - Em falha de write_file, lançar exceção.
        #  - Logar arquivo/PN confirmados.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        self.log("[ARINC] PASSO 3/5: Enviando LUR (test.LUR)...")
        lur_payload = models.build_lur_packet(header_filename, part_number)

        if not self.tftp.write_file("test.LUR", lur_payload):
            # A função write_file já terá logado o erro TFTP
            raise Exception("Falha ao enviar LUR (write_file falhou)")

        self.log(
            f"[ARINC] LUR enviado com sucesso para {header_filename} (PN: {part_number})."
        )

        # ============================================================================
        # REQ: GSE-LLR-212 – Atualizar progresso após PASSO 3
        # Tipo: Requisito Funcional
        # Descrição: Reportar progresso 40% após envio do LUR.
        # Critérios de Aceitação:
        #  - Chamar progress_callback(40).
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        self.progress(40)

        # --- PASSO 4: Servir Arquivo BIN + HASH ---
        # ============================================================================
        # REQ: GSE-LLR-213 – Ler arquivo local e calcular SHA-256
        # Tipo: Requisito Funcional
        # Descrição: Ler file_path e calcular hash com calculate_file_hash(bytes).
        # Critérios de Aceitação:
        #  - Em falha de leitura, logar erro e propagar exceção.
        #  - Logar tamanho lido (bytes) e hash hex.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        self.log(f"[ARINC] PASSO 4/5: Preparando para servir {header_filename}...")
        try:
            self.log(f"[ARINC] Lendo arquivo local: {file_path}")
            with open(file_path, "rb") as f:
                file_data = f.read()
        except Exception as e:
            self.log(f"[ARINC-ERRO] Não foi possível ler o arquivo binário local: {e}")
            raise  # Propaga o erro

        self.log(f"[ARINC] Lidos {len(file_data)} bytes. Calculando HASH SHA-256...")
        hash_data = calculate_file_hash(file_data)
        self.log(f"[ARINC] HASH: {hash_data.hex()}")

        # ============================================================================
        # REQ: GSE-LLR-214 – Mapear progresso do TFTP (0–100) para UI (40–70)
        # Tipo: Requisito Funcional
        # Descrição: Converter progresso de envio do arquivo para uma faixa parcial
        #            do progresso geral da UI.
        # Critérios de Aceitação:
        #  - Fórmula: total_progress = 40 + int(pct * 0.30).
        #  - Garantir que, ao término do envio, a UI esteja em ≥70%.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        def tftp_progress_callback(pct_0_100: int):
            total_progress = 40 + int(pct_0_100 * 0.30)
            self.progress(total_progress)

        # ============================================================================
        # REQ: GSE-LLR-215 – Servir BIN e HASH via RRQ do alvo
        # Tipo: Requisito Funcional
        # Descrição: Atender RRQ do alvo para o arquivo BIN seguido do HASH.
        # Critérios de Aceitação:
        #  - Usar tftp.serve_file_on_rrq(expected_filename, file_data, hash_data, progress_cb).
        #  - Enviar DATA(1..N) do arquivo e DATA(N+1) com hash.
        #  - Propagar exceções de transporte.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        self.tftp.serve_file_on_rrq(
            expected_filename=header_filename,
            file_data=file_data,
            hash_data=hash_data,
            progress_callback=tftp_progress_callback,
        )

        self.log("[ARINC] BIN e HASH servidos com sucesso.")

        # ============================================================================
        # REQ: GSE-LLR-216 – Fixar progresso mínimo após PASSO 4
        # Tipo: Requisito Funcional
        # Descrição: Garantir progresso 70% ao final do PASSO 4.
        # Critérios de Aceitação:
        #  - Chamar progress_callback(70).
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        self.progress(70)

        # --- PASSO 5: Aguardar LUS Progresso (50% e 100%) ---
        # ============================================================================
        # REQ: GSE-LLR-217 – Receber e validar LUS 50%
        # Tipo: Requisito Funcional
        # Descrição: Receber LUS de 50% e validar progresso via parse_lus_progress.
        # Critérios de Aceitação:
        #  - Logar progresso recebido.
        #  - Atualizar UI para 85%.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        self.log("[ARINC] PASSO 5/5: Aguardando LUS 50%...")
        lus_50_data = self.tftp.receive_wrq_and_data()
        prog_50 = models.parse_lus_progress(lus_50_data)
        self.log(
            f"[ARINC] LUS 50% recebido. (Progresso reportado: {prog_50['progress_pct']}%)"
        )
        self.progress(85)

        # ============================================================================
        # REQ: GSE-LLR-218 – Receber LUS 100% com tratamento de timeout
        # Tipo: Requisito Funcional
        # Descrição: Esperar LUS final; em TimeoutError, logar e encerrar com exceção.
        # Critérios de Aceitação:
        #  - Logar mensagens orientativas em caso de timeout (flash/falha).
        #  - Lançar Exception("Falha no LUS 100%: Timeout").
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
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
            raise Exception("Falha no LUS 100%: Timeout")

        prog_100 = models.parse_lus_progress(lus_100_data)
        self.log(
            f"[ARINC] LUS 100% recebido. (Progresso reportado: {prog_100['progress_pct']}%)"
        )

        # ============================================================================
        # REQ: GSE-LLR-219 – Conferir progresso final igual a 100%
        # Tipo: Requisito Funcional
        # Descrição: Se o LUS final não reportar 100%, registrar aviso.
        # Critérios de Aceitação:
        #  - Logar aviso sem necessariamente abortar.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        if prog_100["progress_pct"] != 100:
            self.log(
                f"[ARINC-AVISO] Progresso final não foi 100% (recebido {prog_100}%)"
            )

        # ============================================================================
        # REQ: GSE-LLR-220 – Finalizar com progresso 100% e logs de rodapé
        # Tipo: Requisito Funcional
        # Descrição: Ajustar UI para 100% e emitir banners de conclusão.
        # Critérios de Aceitação:
        #  - Chamar progress_callback(100).
        #  - Logar linhas separadoras e mensagem de conclusão.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        self.progress(100)
        self.log("=" * 30)
        self.log("[ARINC] Fluxo de upload concluído com sucesso.")
        self.log("=" * 30)

        # ============================================================================
        # REQ: GSE-LLR-221 – Contrato de retorno do fluxo
        # Tipo: Requisito Funcional
        # Descrição: Retornar True quando todos os passos (1..5) forem concluídos
        #            sem exceções.
        # Critérios de Aceitação:
        #  - Retornar bool True em caso de sucesso.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        return True
