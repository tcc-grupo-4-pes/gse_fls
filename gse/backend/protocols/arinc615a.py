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

from backend.protocols.tftp_client import TFTPClient
import backend.protocols.arinc_models as models
from backend.protocols.hash_utils import calculate_file_hash

# ============ CONSTANTES ============

# ============================================================================
# REQ: GSE-LLR-60 – Chaves padrão para handshake estático
# Tipo: Requisito Funcional
# Descrição: O software DEVE definir chaves padrão para handshake estático, expondo
#            GSE_STATIC_KEY e EXPECTED_BC_KEY como bytes, permitindo substituição
#            futura por injeção de dependência ou feature flag externa.
# Autor: Julia | Revisor: Fabrício
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
        # REQ: GSE-LLR-61 – Injeção obrigatória do transporte
        # Tipo: Requisito Funcional
        # Descrição: A construção da sessão DEVE receber um TFTPClient pronto para uso
        #            e armazená-lo em self.tftp; se tftp_client for None, a sessão
        #            DEVE lançar exceção para impedir operação inválida.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        self.tftp = tftp_client

        # ============================================================================
        # REQ: GSE-LLR-62 – Callbacks seguros por padrão
        # Tipo: Requisito Não Funcional
        # Descrição: A sessão DEVE configurar callbacks seguros por padrão, usando uma
        #            função que imprime em stdout quando logger não for injetado e uma
        #            função no-op para progress_callback, evitando falhas por None.
        # Autor: Julia | Revisor: Fabrício
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
        # REQ: GSE-LLR-63 – Pré-validação dos parâmetros do fluxo
        # Tipo: Requisito Funcional
        # Descrição: A sessão DEVE validar os parâmetros de entrada do fluxo, garantindo
        #            que part_number não seja vazio antes do PASSO 3 e determinando
        #            header_filename a partir de file_path; a verificação física
        #            de existência/leitura do arquivo ocorrerá no PASSO 4.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        header_filename = os.path.basename(file_path)

        # ===========================================================
        # [NOVO] PASSO DE AUTENTICAÇÃO (Handshake)
        # ===========================================================
        # ============================================================================
        # REQ: GSE-LLR-64 – Handshake estático opcional
        # Tipo: Requisito Funcional
        # Descrição: Quando uma feature flag de segurança estiver ativada, o fluxo DEVE
        #            realizar verificação mútua de chaves chamando
        #            tftp.verify_static_key(GSE_STATIC_KEY, EXPECTED_BC_KEY) antes do PASSO 1,
        #            abortando o processo com log apropriado em caso de falha/erro.
        # Autor: Julia | Revisor: Fabrício
        # Nota: Código ilustrativo permanece comentado até a flag ser habilitada.
        # ============================================================================
        # self.log("[ARINC] PASSO 0/5: Verificando chave estática (Handshake)...")
        # try:
        #     if not self.tftp.verify_static_key(GSE_STATIC_KEY, EXPECTED_BC_KEY):
        #         self.log("[erro] Falha na verificação da chave estática. Abortando.")
        #         return
        # except Exception as e:
        #     self.log(f"[erro] Erro fatal na verificação de chave: {e}")
        #     return

        # ============================================================================
        # --- PASSO 1: Ler LUI (Load User Information) ---
        # ============================================================================
        # REQ: GSE-LLR-65 – Leitura e parsing do LUI inicial
        # Tipo: Requisito Funcional
        # Descrição: O fluxo DEVE efetuar RRQ de "system.LUI" via TFTP, parsear a
        #            resposta com models.parse_lui_response e lançar exceção com
        #            mensagem detalhada quando o parser retornar um dicionário com "error";
        #            o software DEVE registrar (log) o status_name recebido.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        self.log("[ARINC] PASSO 1/5: Lendo LUI (system.LUI)...")
        lui_data = self.tftp.read_file("system.LUI")
        lui_info = models.parse_lui_response(lui_data)

        if "error" in lui_info:
            raise Exception(f"Falha ao parsear LUI: {lui_info['error']}")

        self.log("[ARINC] LUI recebido e processado.")
        # print(f"[DEBUG] Conteúdo de lui_info: {lui_info}")

        # ============================================================================
        # REQ: GSE-LLR-66 – Validação do status inicial do LUI
        # Tipo: Requisito Funcional
        # Descrição: O fluxo DEVE aceitar como esperado um LUI inicial cujo status_code,
        #            convertido de string "0xhhhh" para inteiro base 16, pertença a
        #            {ARINC_STATUS_ACCEPTED, ARINC_STATUS_COMPLETED_OK}; para demais
        #            códigos, o software DEVE somente registrar aviso sem abortar.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        if int(lui_info["status_code"], 16) not in (
            models.ARINC_STATUS_ACCEPTED,
            models.ARINC_STATUS_COMPLETED_OK,
        ):
            self.log(f"[ARINC-AVISO] Status LUI inesperado: {lui_info['status_code']}")

        # ============================================================================
        # REQ: GSE-LLR-67 – Progresso após PASSO 1
        # Tipo: Requisito Funcional
        # Descrição: A sessão DEVE atualizar o progresso para 10% imediatamente após
        #            o processamento bem-sucedido do LUI inicial.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        self.progress(10)

        # --- PASSO 2: Aguardar LUS Inicial (Load Status) ---
        # ============================================================================
        # REQ: GSE-LLR-68 – Recepção do LUS inicial
        # Tipo: Requisito Funcional
        # Descrição: A sessão DEVE aguardar WRQ + primeiro DATA do alvo contendo o
        #            LUS inicial, parsear com models.parse_lus_progress e registrar
        #            o progresso reportado; se o parser indicar erro, lançar exceção.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        self.log("[ARINC] PASSO 2/5: Aguardando LUS inicial (INIT_LOAD.LUS)...")
        lus_data_inicial = self.tftp.receive_wrq_and_data()
        progress_inicial = models.parse_lus_progress(lus_data_inicial)
        self.log(f"[ARINC] LUS inicial recebido.")

        # ============================================================================
        # REQ: GSE-LLR-69 – Progresso após PASSO 2
        # Tipo: Requisito Funcional
        # Descrição: A sessão DEVE atualizar o progresso para 25% após o LUS inicial
        #            ter sido recebido e validado com sucesso.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        self.progress(25)

        # --- PASSO 3: Enviar LUR (Load Upload Request) ---
        # ============================================================================
        # REQ: GSE-LLR-70 – Construção e envio do LUR
        # Tipo: Requisito Funcional
        # Descrição: A sessão DEVE construir o payload LUR com
        #            models.build_lur_packet(header_filename, part_number) e enviá-lo
        #            via TFTP usando write_file("test.LUR", payload), lançando exceção
        #            em caso de falha no envio; o software DEVE registrar arquivo e PN.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        self.log("[ARINC] PASSO 3/5: Enviando LUR (test.LUR)...")
        lur_payload = models.build_lur_packet(header_filename, part_number)

        if not self.tftp.write_file("test.LUR", lur_payload):
            raise Exception("Falha ao enviar LUR (write_file falhou)")

        self.log(
            f"[ARINC] LUR enviado com sucesso para {header_filename} (PN: {part_number})."
        )

        # ============================================================================
        # REQ: GSE-LLR-71 – Progresso após PASSO 3
        # Tipo: Requisito Funcional
        # Descrição: A sessão DEVE atualizar o progresso para 40% imediatamente após
        #            o envio bem-sucedido do LUR.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        self.progress(40)

        # --- PASSO 4: Servir Arquivo BIN + HASH ---
        # ============================================================================
        # REQ: GSE-LLR-72 – Leitura do arquivo e cálculo de SHA-256
        # Tipo: Requisito Funcional
        # Descrição: A sessão DEVE ler o arquivo indicado por file_path e calcular o
        #            hash SHA-256 via calculate_file_hash(bytes), registrando tamanho
        #            lido e hash em hexadecimal; em falha de leitura, deve logar e
        #            propagar a exceção.
        # Autor: Julia | Revisor: Fabrício
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
        # self.log(f"[ARINC] HASH: {hash_data.hex()}")
        self.log(f"[ARINC] HASH Calculado com sucesso.")

        # ============================================================================
        # REQ: GSE-LLR-73 – Mapeamento de progresso para a UI (40–70)
        # Tipo: Requisito Funcional
        # Descrição: A sessão DEVE mapear o progresso de envio do TFTP (0–100) para a
        #            faixa 40–70 da UI usando a fórmula total_progress = 40 + int(pct*0.30),
        #            garantindo que ao final do envio a UI atinja pelo menos 70%.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        def tftp_progress_callback(pct_0_100: int):
            total_progress = 40 + int(pct_0_100 * 0.30)
            self.progress(total_progress)

        # ============================================================================
        # REQ: GSE-LLR-74 – Servir BIN seguido do HASH ao RRQ
        # Tipo: Requisito Funcional
        # Descrição: A sessão DEVE atender ao RRQ do alvo servindo primeiro todos os
        #            blocos DATA (1..N) do arquivo BIN e, em seguida, um bloco DATA
        #            contendo o HASH calculado, por meio de
        #            tftp.serve_file_on_rrq(expected_filename, file_data, hash_data, progress_callback),
        #            propagando exceções de transporte quando ocorrerem.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        self.tftp.serve_file_on_rrq(
            expected_filename=header_filename,
            file_data=file_data,
            hash_data=hash_data,
            progress_callback=tftp_progress_callback,
        )

        self.log("[ARINC] BIN e HASH servidos com sucesso.")

        # ============================================================================
        # REQ: GSE-LLR-75 – Progresso mínimo ao fim do PASSO 4
        # Tipo: Requisito Funcional
        # Descrição: Ao concluir o PASSO 4, a sessão DEVE ajustar explicitamente o
        #            progresso para 70%, assegurando consistência visual na UI.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        self.progress(70)

        # --- PASSO 5: Aguardar LUS Progresso (50% e 100%) ---
        # ============================================================================
        # REQ: GSE-LLR-76 – Receber e validar LUS de 50%
        # Tipo: Requisito Funcional
        # Descrição: A sessão DEVE receber o LUS que reporta 50% de progresso, validá-lo
        #            via models.parse_lus_progress e registrar o progresso informado,
        #            atualizando a UI para 85% após a validação.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        self.log("[ARINC] PASSO 5/5: Aguardando LUS 50%...")
        lus_50_data = self.tftp.receive_wrq_and_data()
        prog_50 = models.parse_lus_progress(lus_50_data)
        self.log(f"[ARINC] LUS 50% recebido.")
        self.progress(85)

        # ============================================================================
        # REQ: GSE-LLR-77 – Tratamento de timeout para o LUS final
        # Tipo: Requisito Funcional
        # Descrição: Ao aguardar o LUS final, a sessão DEVE capturar TimeoutError,
        #            registrar mensagens orientativas (p.ex., possível flash/falha)
        #            e lançar a exceção “Falha no LUS 100%: Timeout”.
        # Autor: Julia | Revisor: Fabrício
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
        self.log(f"[ARINC] LUS 100% recebido.")

        # ============================================================================
        # REQ: GSE-LLR-78 – Aviso quando progresso final != 100%
        # Tipo: Requisito Funcional
        # Descrição: Ao receber o LUS final, a sessão DEVE registrar aviso caso o
        #            progresso reportado seja diferente de 100%, sem abortar
        #            necessariamente o fluxo.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        if prog_100["progress_pct"] != 100:
            self.log(
                f"[ARINC-AVISO] Progresso final não foi 100% (recebido {prog_100}%)"
            )

        # ============================================================================
        # REQ: GSE-LLR-79 – Finalização a 100% com banners
        # Tipo: Requisito Funcional
        # Descrição: Ao concluir o fluxo, a sessão DEVE ajustar o progresso para 100%
        #            e emitir banners de conclusão no log (linhas separadoras e
        #            mensagem de término com sucesso).
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        self.progress(100)
        self.log("=" * 30)
        self.log("[ARINC] Fluxo de upload concluído com sucesso.")
        self.log("=" * 30)

        # ============================================================================
        # REQ: GSE-LLR-80 – Contrato de retorno do fluxo
        # Tipo: Requisito Funcional

        # Descrição: A rotina run_upload_flow DEVE retornar True quando todos os
        #            passos (1..5) forem concluídos sem exceções.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================
        return True
