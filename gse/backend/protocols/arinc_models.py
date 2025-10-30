import struct
from typing import Dict, Any

# ======================================================================
# REQ: GSE-LLR-XXX – Expor constantes de status ARINC
# Tipo: Requisito Funcional
# Descrição: Expor constantes ARINC_STATUS_* e o dicionário ARINC_STATUS_MAP.
# Critérios de Aceitação:
#  - Manter valores: 0x0001, 0x0002, 0x0003, 0x1000.
#  - A função de parsing deve mapear status_code para status_name.
# Autor: (preencher)
# Revisor: (preencher)
# ======================================================================
ARINC_STATUS_ACCEPTED = 0x0001
ARINC_STATUS_IN_PROGRESS = 0x0002
ARINC_STATUS_COMPLETED_OK = 0x0003
ARINC_STATUS_REJECTED = 0x1000

ARINC_STATUS_MAP = {
    ARINC_STATUS_ACCEPTED: "Operação Aceita",
    ARINC_STATUS_IN_PROGRESS: "Em Progresso",
    ARINC_STATUS_COMPLETED_OK: "Concluído com Sucesso",
    ARINC_STATUS_REJECTED: "Operação Rejeitada",
}


def parse_lui_response(data: bytes) -> Dict[str, Any]:
    """
    Analisa a resposta de um arquivo LUI (Load Unit Information).
    Formato: [file_length(4)][protocol_version(2)][status_code(2)][desc_length(1)][description(n)]
    """

    # ============================================================================
    # REQ: GSE-LLR-120 – Interpretar campos básicos de LUI
    # Tipo: Requisito Funcional
    # Descrição: Analisar o payload LUI e extrair file_length (4B big-endian),
    # protocol_version (2B ASCII), status_code (2B big-endian), desc_length (1B)
    # e description (desc_length B ASCII).
    # Critérios de Aceitação:
    #  - Retornar dict com chaves: file_length, protocol_version, status_code,
    #    status_name, desc_length, description.
    #  - Usar decodificação ASCII com ignore para bytes inválidos.
    # Autor: (preencher)
    # Revisor: (preencher)
    # ============================================================================

    # ============================================================================
    # REQ: GSE-LLR-121 – Validar tamanho mínimo de LUI
    # Tipo: Requisito Funcional
    # Descrição: Rejeitar dados LUI com menos de 9 bytes.
    # Critérios de Aceitação:
    #  - Quando len(data) < 9, retornar {"error": "Dados LUI insuficientes"}.
    # Autor: (preencher)
    # Revisor: (preencher)
    # ============================================================================
    if len(data) < 9:
        return {"error": "Dados LUI insuficientes"}

    try:
        # ============================================================================
        # REQ: GSE-LLR-134 – Validar protocol_version (2 bytes ASCII)
        # Tipo: Requisito Funcional
        # Descrição: Garantir que protocol_version tenha exatamente 2 bytes ASCII.
        # Critérios de Aceitação:
        #  - Decodificar 2 bytes e expor como string de tamanho 2.
        #  - Em caso de tamanho inválido, retornar erro claro.
        # Autor: (preencher)
        # Revisor: (preencher)
        # ============================================================================
        file_length = struct.unpack("!L", data[0:4])[0]
        proto_raw = data[4:6]
        if len(proto_raw) != 2:
            return {"error": "Protocol Version inválido (tamanho != 2 bytes)"}
        protocol_version = proto_raw.decode("ascii", errors="ignore")
        if len(protocol_version) != 2:
            return {"error": "Protocol Version inválido (não ASCII de 2 chars)"}

        status_code = struct.unpack("!H", data[6:8])[0]
        desc_length = data[8]

        # ============================================================================
        # REQ: GSE-LLR-132 – Padronizar mensagem de erro de campos incompletos
        # Tipo: Requisito Não Funcional
        # Descrição: Se description não couber no buffer, retornar erro padronizado.
        # Critérios de Aceitação:
        #  - len(data) < 9 + desc_length → {"error": "Dados LUI incompletos para description"}.
        # Autor: (preencher)
        # Revisor: (preencher)
        # ============================================================================
        if len(data) < 9 + desc_length:
            return {"error": "Dados LUI incompletos para description"}

        description = data[9 : 9 + desc_length].decode("ascii", errors="ignore")

        # ============================================================================
        # REQ: GSE-LLR-122 – Mapear status ARINC para nome legível
        # Tipo: Requisito Funcional
        # Descrição: Mapear status_code para status_name usando ARINC_STATUS_MAP.
        # Critérios de Aceitação:
        #  - status_code como string "0xhhhh" (hex minúsculo, 4 dígitos).
        #  - Códigos desconhecidos → "Desconhecido".
        # Autor: (preencher)
        # Revisor: (preencher)
        # ============================================================================
        return {
            "file_length": file_length,
            "protocol_version": protocol_version,
            "status_code": f"0x{status_code:04x}",
            "status_name": ARINC_STATUS_MAP.get(status_code, "Desconhecido"),
            "desc_length": desc_length,
            "description": description,
        }

    except Exception as e:
        # ============================================================================
        # REQ: GSE-LLR-123 – Tratar exceções de parsing LUI
        # Tipo: Requisito Funcional
        # Descrição: Capturar exceções de parsing e retornar erro padronizado.
        # Critérios de Aceitação:
        #  - Retornar {"error": "Erro ao analisar LUI: <msg>"} em qualquer exceção.
        # Autor: (preencher)
        # Revisor: (preencher)
        # ============================================================================
        return {"error": f"Erro ao analisar LUI: {e}"}


def parse_lus_progress(data: bytes) -> Dict[str, Any]:
    """
    Analisa um arquivo LUS (Load Unit Status) para extrair o progresso.
    Formato: [file_length(4)][protocol_version(2)][status_code(2)][desc_length(1)][description(n)][...][progress(3)]
    Nota: O progresso (ex: "050", "100") são os 3 últimos bytes do payload.
    """

    # ============================================================================
    # REQ: GSE-LLR-124 – Validar tamanho mínimo de LUS
    # Tipo: Requisito Funcional
    # Descrição: Rejeitar dados LUS com menos de 12 bytes (9 de header + 3 de progresso).
    # Critérios de Aceitação:
    #  - Quando len(data) < 12, retornar {"error": "Dados LUS insuficientes"}.
    # Autor: (preencher)
    # Revisor: (preencher)
    # ============================================================================
    if len(data) < 12:
        return {"error": "Dados LUS insuficientes"}

    try:
        # ============================================================================
        # REQ: GSE-LLR-124 – Reutilizar parsing de LUI
        # Tipo: Requisito Funcional
        # Descrição: Reutilizar parse_lui_response e propagar seus erros.
        # Critérios de Aceitação:
        #  - Se parse_lui_response retornar {"error": ...}, repassar o erro.
        # Autor: (preencher)
        # Revisor: (preencher)
        # ============================================================================
        lus = parse_lui_response(data)
        if "error" in lus:
            return lus

        # ============================================================================
        # REQ: GSE-LLR-125 – Validar progresso LUS como ASCII numérico
        # Tipo: Requisito Funcional
        # Descrição: Validar que os 3 últimos bytes são dígitos ASCII ('0'–'9').
        # Critérios de Aceitação:
        #  - Valores aceitos: "000" a "100".
        #  - Caso inválido: retornar {"error": "Progresso LUS inválido (deve ser '000'..'100')"}.
        # Autor: (preencher)
        # Revisor: (preencher)
        # ============================================================================
        progress_bytes = data[-3:]
        try:
            progress_str = progress_bytes.decode("ascii")
        except Exception:
            return {"error": "Progresso LUS inválido (não ASCII)"}

        if len(progress_str) != 3 or not progress_str.isdigit():
            return {"error": "Progresso LUS inválido (deve ser '000'..'100')"}

        progress_pct = int(progress_str)

        # ============================================================================
        # REQ: GSE-LLR-138 – Limitar progress_pct ao intervalo 0..100
        # Tipo: Requisito Funcional
        # Descrição: Rejeitar progresso fora do intervalo válido.
        # Critérios de Aceitação:
        #  - progress_pct < 0 ou > 100 → erro padronizado.
        # Autor: (preencher)
        # Revisor: (preencher)
        # ============================================================================
        if not (0 <= progress_pct <= 100):
            return {"error": "Progresso LUS fora da faixa (0..100)"}

        lus["progress_str"] = progress_str
        lus["progress_pct"] = progress_pct
        return lus

    except Exception as e:
        # ============================================================================
        # REQ: GSE-LLR-124/132 – Padronizar erro em exceções de LUS
        # Tipo: Requisito Não Funcional
        # Descrição: Capturar exceções e retornar erro padronizado.
        # Critérios de Aceitação:
        #  - Retornar {"error": "Erro ao analisar progresso LUS: <msg>"}.
        # Autor: (preencher)
        # Revisor: (preencher)
        # ============================================================================
        return {"error": f"Erro ao analisar progresso LUS: {e}"}


def build_lur_packet(header_filename: str, part_number: str) -> bytes:
    """
    Constrói o payload de um arquivo LUR (Load Unit Request).
    Formato:
      [file_length(4, BE)][protocol_version(2 ASCII)][num_headers(2, BE)]
      [len_header(1)][header_bytes][len_pn(1)][pn_bytes]
    """

    # ============================================================================
    # REQ: GSE-LLR-136 – Rejeitar entradas vazias em LUR
    # Tipo: Requisito Funcional
    # Descrição: Validar que header_filename e part_number não sejam vazios.
    # Critérios de Aceitação:
    #  - Se vazio, lançar ValueError com mensagem clara.
    # Autor: (preencher)
    # Revisor: (preencher)
    # ============================================================================
    if not header_filename:
        raise ValueError("header_filename vazio")
    if not part_number:
        raise ValueError("part_number vazio")

    # ============================================================================
    # REQ: GSE-LLR-126 – Codificar campos em ASCII estrito
    # Tipo: Requisito Funcional
    # Descrição: Codificar header_filename e part_number como ASCII estrito.
    # Critérios de Aceitação:
    #  - Em caractere não ASCII, lançar ValueError.
    # Autor: (preencher)
    # Revisor: (preencher)
    # ============================================================================
    try:
        header_bytes = header_filename.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError("header_filename contém caracteres não-ASCII")

    try:
        pn_bytes = part_number.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError("part_number contém caracteres não-ASCII")

    len_header = len(header_bytes)
    len_pn = len(pn_bytes)

    # ============================================================================
    # REQ: GSE-LLR-129 – Limitar tamanhos a 1 byte
    # Tipo: Requisito Funcional
    # Descrição: Limitar len_header e len_pn ao intervalo 0..255.
    # Critérios de Aceitação:
    #  - Se >255, lançar ValueError.
    # Autor: (preencher)
    # Revisor: (preencher)
    # ============================================================================
    if len_header > 255:
        raise ValueError("header_filename excede 255 bytes ASCII")
    if len_pn > 255:
        raise ValueError("part_number excede 255 bytes ASCII")

    # ============================================================================
    # REQ: GSE-LLR-134 – Fixar protocol_version como "A4"
    # Tipo: Requisito Funcional
    # Descrição: Gravar exatamente 2 bytes ASCII "A4".
    # Critérios de Aceitação:
    #  - protocol_version == b"A4".
    # Autor: (preencher)
    # Revisor: (preencher)
    # ============================================================================
    protocol_version = b"A4"

    # ============================================================================
    # REQ: GSE-LLR-130 – Definir num_headers conforme ICD
    # Tipo: Requisito Funcional
    # Descrição: Ajustar num_headers ao número de campos considerados “headers”.
    # Critérios de Aceitação:
    #  - Se filename e PN forem headers no ICD, usar 2; caso contrário, documentar.
    # Autor: (preencher)
    # Revisor: (preencher)
    # ============================================================================
    num_headers = 2  # ajuste aqui conforme a sua convenção/ICD

    # ============================================================================
    # REQ: GSE-LLR-128 – Calcular file_length corretamente
    # Tipo: Requisito Funcional
    # Descrição: file_length = tamanho total do payload LUR.
    # Critérios de Aceitação:
    #  - 4 + 2 + 2 + 1 + len_header + 1 + len_pn.
    # Autor: (preencher)
    # Revisor: (preencher)
    # ============================================================================
    total_length = 4 + 2 + 2 + 1 + len_header + 1 + len_pn

    # ============================================================================
    # REQ: GSE-LLR-127 – Compor layout binário do LUR (big-endian)
    # Tipo: Requisito Funcional
    # Descrição: Montar os campos exatamente na ordem especificada.
    # Critérios de Aceitação:
    #  - Inteiros em big-endian ('!L', '!H', '!B').
    # Autor: (preencher)
    # Revisor: (preencher)
    # ============================================================================
    pkt = b""
    pkt += struct.pack("!L", total_length)
    pkt += protocol_version
    pkt += struct.pack("!H", num_headers)
    pkt += struct.pack("!B", len_header)
    pkt += header_bytes
    pkt += struct.pack("!B", len_pn)
    pkt += pn_bytes

    # ============================================================================
    # REQ: GSE-LLR-135 – Garantir determinismo binário
    # Tipo: Requisito Não Funcional
    # Descrição: Para mesmas entradas, produzir bytes idênticos.
    # Critérios de Aceitação:
    #  - Validar em teste unitário por igualdade byte a byte.
    # Autor: (preencher)
    # Revisor: (preencher)
    # ============================================================================
    return pkt
