import struct
from typing import Dict, Any

# ======================================================================
# REQ: GSE-LLR-30 – Valor da constante ARINC_STATUS_ACCEPTED
# Tipo: Requisito Funcional
# Descrição: A constante ARINC_STATUS_ACCEPTED DEVE possuir o valor 0x0001.
# Autor: Julia | Revisor: Fabrício
# ======================================================================

# ======================================================================
# REQ: GSE-LLR-31 – Valor da constante ARINC_STATUS_IN_PROGRESS
# Tipo: Requisito Funcional
# Descrição: A constante ARINC_STATUS_IN_PROGRESS DEVE possuir o valor 0x0002.
# Autor: Julia | Revisor: Fabrício
# ======================================================================

# ======================================================================
# REQ: GSE-LLR-32 – Valor da constante ARINC_STATUS_COMPLETED_OK
# Tipo: Requisito Funcional
# Descrição: A constante ARINC_STATUS_COMPLETED_OK DEVE possuir o valor 0x0003.
# Autor: Julia | Revisor: Fabrício
# ======================================================================

# ======================================================================
# REQ: GSE-LLR-33 – Valor da constante ARINC_STATUS_REJECTED
# Tipo: Requisito Funcional
# Descrição: A constante ARINC_STATUS_REJECTED DEVE possuir o valor 0x1000.
# Autor: Julia | Revisor: Fabrício
# =====================================================================

ARINC_STATUS_ACCEPTED = 0x0001
ARINC_STATUS_IN_PROGRESS = 0x0002
ARINC_STATUS_COMPLETED_OK = 0x0003
ARINC_STATUS_REJECTED = 0x1000

# ======================================================================
# REQ: GSE-LLR-34 – Definir dicionário ARINC_STATUS_MAP
# Tipo: Requisito Funcional
# Descrição: O software DEVE expor o dicionário ARINC_STATUS_MAP mapeando:
#            0x0001→"Operação Aceita", 0x0002→"Em Progresso",
#            0x0003→"Concluído com Sucesso", 0x1000→"Operação Rejeitada".
# Autor: Julia | Revisor: Fabrício
# ======================================================================

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
    # REQ: GSE-LLR-35 – Interpretar estrutura básica LUI
    # Tipo: Requisito Funcional
    # Descrição: A interface DEVE interpretar o payload LUI no formato
    #            [file_length(4, BE)][protocol_version(2, ASCII)]
    #            [status_code(2, BE)][desc_length(1)][description(desc_length, ASCII)]
    #            e retornar um dicionário com as chaves:
    #            file_length (int), protocol_version (str), status_code (str),
    #            status_name (str), desc_length (int), description (str).
    # Autor: Julia | Revisor: Fabrício
    # ============================================================================

    # ============================================================================
    # REQ: GSE-LLR-36 – Validar tamanho mínimo LUI
    # Tipo: Requisito Funcional
    # Descrição: Se len(data) < 9, a interface DEVE retornar exatamente:
    #            {"error": "Dados LUI insuficientes"}.
    # Autor: Julia | Revisor: Fabrício
    # ============================================================================

    if len(data) < 9:
        return {"error": "Dados LUI insuficientes"}

    try:

        file_length = struct.unpack("!L", data[0:4])[0]

        # ============================================================================
        # REQ: GSE-LLR-37 – protocol_version com 2 bytes no buffer
        # Tipo: Requisito Funcional
        # Descrição: O buffer bruto DEVE conter exatamente 2 bytes para protocol_version;
        #            caso contrário, retornar {"error": "Protocol Version inválido (tamanho != 2 bytes)"}.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        proto_raw = data[4:6]
        if len(proto_raw) != 2:
            return {"error": "Protocol Version inválido (tamanho != 2 bytes)"}

        # ============================================================================
        # REQ: GSE-LLR-38 – protocol_version ASCII de 2 caracteres
        # Tipo: Requisito Funcional
        # Descrição: Após decodificação ASCII (errors="ignore"), protocol_version DEVE
        #            ter comprimento 2; caso contrário, retornar
        #            {"error": "Protocol Version inválido (não ASCII de 2 chars)"}.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        protocol_version = proto_raw.decode("ascii", errors="ignore")
        if len(protocol_version) != 2:
            return {"error": "Protocol Version inválido (não ASCII de 2 chars)"}

        status_code = struct.unpack("!H", data[6:8])[0]
        desc_length = data[8]

        # ============================================================================
        # REQ: GSE-LLR-39 – description completa no buffer
        # Tipo: Requisito Não Funcional
        # Descrição: Se len(data) < 9 + desc_length, a interface DEVE retornar exatamente:
        #            {"error": "Dados LUI incompletos para description"}.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        if len(data) < 9 + desc_length:
            return {"error": "Dados LUI incompletos para description"}

        description = data[9 : 9 + desc_length].decode("ascii", errors="ignore")

        # ============================================================================
        # REQ: GSE-LLR-40 – Formatar status_code como "0xhhhh"
        # Tipo: Requisito Funcional
        # Descrição: A interface DEVE expor status_code no dicionário como string
        #            no formato "0xhhhh", em minúsculas e com 4 dígitos.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        # ============================================================================
        # REQ: GSE-LLR-41 – Mapear status_name via ARINC_STATUS_MAP
        # Tipo: Requisito Funcional
        # Descrição: A interface DEVE preencher status_name usando ARINC_STATUS_MAP e,
        #            para códigos desconhecidos, DEVE usar a string "Desconhecido".
        # Autor: Julia | Revisor: Fabrício
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
        # REQ: GSE-LLR-42 – Padronizar erro em exceções de LUI
        # Tipo: Requisito Funcional
        # Descrição: Em qualquer exceção durante o parsing de LUI, a interface DEVE
        #            retornar exatamente {"error": f"Erro ao analisar LUI: {msg}"}.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================
        return {"error": f"Erro ao analisar LUI: {e}"}


def parse_lus_progress(data: bytes) -> Dict[str, Any]:
    """
    Analisa um arquivo LUS (Load Unit Status) para extrair o progresso.
    Formato: [file_length(4)][protocol_version(2)][status_code(2)][desc_length(1)][description(n)][...][progress(3)]
    Nota: O progresso (ex: "050", "100") são os 3 últimos bytes do payload.
    """

    # ============================================================================
    # REQ: GSE-LLR-43 – Validar tamanho mínimo LUS
    # Tipo: Requisito Funcional
    # Descrição: Se len(data) < 12, a interface DEVE retornar exatamente:
    #            {"error": "Dados LUS insuficientes"}.
    # Autor: Julia | Revisor: Fabrício
    # ============================================================================

    if len(data) < 12:
        return {"error": "Dados LUS insuficientes"}

    try:
        # ============================================================================
        # REQ: GSE-LLR-44 – Reutilizar parsing de LUI no LUS
        # Tipo: Requisito Funcional
        # Descrição: A interface DEVE chamar parse_lui_response(data) e,
        #            se esta retornar um dicionário com "error", DEVE propagar esse
        #            mesmo dicionário de erro sem alterações.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        lus = parse_lui_response(data)
        if "error" in lus:
            return lus

        progress_bytes = data[-3:]

        # ============================================================================
        # REQ: GSE-LLR-45 – Progresso LUS ASCII válido (3 chars)
        # Tipo: Requisito Funcional
        # Descrição: Os 3 bytes finais DEVE[M] ser decodificáveis como ASCII; se a
        #            decodificação falhar, retornar {"error": "Progresso LUS inválido (não ASCII)"}.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        try:
            progress_str = progress_bytes.decode("ascii")
        except Exception:
            return {"error": "Progresso LUS inválido (não ASCII)"}

        # ============================================================================
        # REQ: GSE-LLR-46 – Progresso LUS é dígito ASCII (len==3 e isdigit)
        # Tipo: Requisito Funcional
        # Descrição: A interface DEVE validar que progress_str possui len==3 e todos
        #            os caracteres são dígitos; em caso negativo, retornar exatamente
        #            {"error": "Progresso LUS inválido (deve ser '000'..'100')"}.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        if len(progress_str) != 3 or not progress_str.isdigit():
            return {"error": "Progresso LUS inválido (deve ser '000'..'100')"}

        progress_pct = int(progress_str)

        # ============================================================================
        # REQ: GSE-LLR-47 – Intervalo válido de progresso (0..100)
        # Tipo: Requisito Funcional
        # Descrição: Se progress_pct < 0 ou progress_pct > 100, a interface DEVE
        #            retornar exatamente {"error": "Progresso LUS fora da faixa (0..100)"}.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================

        if not (0 <= progress_pct <= 100):
            return {"error": "Progresso LUS fora da faixa (0..100)"}

        lus["progress_str"] = progress_str
        lus["progress_pct"] = progress_pct
        return lus

    except Exception as e:
        # ============================================================================
        # REQ: GSE-LLR-48 – Padronizar erro em exceções de LUS
        # Tipo: Requisito Não Funcional
        # Descrição: Em qualquer exceção durante o parsing de LUS, a interface DEVE
        #            retornar exatamente {"error": f"Erro ao analisar progresso LUS: {msg}"}.
        # Autor: Julia | Revisor: Fabrício
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
    # REQ: GSE-LLR-49 – header_filename não pode ser vazio
    # Tipo: Requisito Funcional
    # Descrição: Se header_filename for vazio, a função DEVE lançar
    #            ValueError("header_filename vazio").
    # Autor: Julia | Revisor: Fabrício
    # ============================================================================

    if not header_filename:
        raise ValueError("header_filename vazio")

    # ============================================================================
    # REQ: GSE-LLR-50 – part_number não pode ser vazio
    # Tipo: Requisito Funcional
    # Descrição: Se part_number for vazio, a função DEVE lançar
    #            ValueError("part_number vazio").
    # Autor: Julia | Revisor: Fabrício
    # ============================================================================

    if not part_number:
        raise ValueError("part_number vazio")

    # ============================================================================
    # REQ: GSE-LLR-51 – header_filename em ASCII estrito
    # Tipo: Requisito Funcional
    # Descrição: O campo header_filename DEVE ser codificado em ASCII; em caso de
    #            UnicodeEncodeError, DEVE lançar ValueError("header_filename contém caracteres não-ASCII").
    # Autor: Julia | Revisor: Fabrício
    # ============================================================================

    try:
        header_bytes = header_filename.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError("header_filename contém caracteres não-ASCII")

    # ============================================================================
    # REQ: GSE-LLR-52 – part_number em ASCII estrito
    # Tipo: Requisito Funcional
    # Descrição: O campo part_number DEVE ser codificado em ASCII; em caso de
    #            UnicodeEncodeError, DEVE lançar ValueError("part_number contém caracteres não-ASCII").
    # Autor: Julia | Revisor: Fabrício
    # ============================================================================

    try:
        pn_bytes = part_number.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError("part_number contém caracteres não-ASCII")

    len_header = len(header_bytes)
    len_pn = len(pn_bytes)

    # ============================================================================
    # REQ: GSE-LLR-53 – Limite de comprimento para header_filename (0..255)
    # Tipo: Requisito Funcional
    # Descrição: Se len(header_bytes) > 255, a função DEVE lançar
    #            ValueError("header_filename excede 255 bytes ASCII").
    # Autor: Julia | Revisor: Fabrício
    # ============================================================================

    if len_header > 255:
        raise ValueError("header_filename excede 255 bytes ASCII")

    # ============================================================================
    # REQ: GSE-LLR-54 – Limite de comprimento para part_number (0..255)
    # Tipo: Requisito Funcional
    # Descrição: Se len(pn_bytes) > 255, a função DEVE lançar
    #            ValueError("part_number excede 255 bytes ASCII").
    # Autor: Julia | Revisor: Fabrício
    # ============================================================================

    if len_pn > 255:
        raise ValueError("part_number excede 255 bytes ASCII")

    # ============================================================================
    # REQ: GSE-LLR-55 – protocol_version fixo "A4"
    # Tipo: Requisito Funcional
    # Descrição: O campo protocol_version do LUR DEVE ser exatamente os bytes b"A4".
    # Autor: Julia | Revisor: Fabrício
    # ============================================================================

    protocol_version = b"A4"

    # ============================================================================
    # REQ: GSE-LLR-56 – Definir num_headers conforme ICD
    # Tipo: Requisito Funcional
    # Descrição: O campo num_headers DEVE refletir o número de headers incluídos;
    #            quando filename e PN forem considerados headers pelo ICD, num_headers DEVE ser 2.
    # Autor: Julia | Revisor: Fabrício
    # ============================================================================

    num_headers = 2  # ajuste aqui conforme a sua convenção/ICD

    # ============================================================================
    # REQ: GSE-LLR-57 – Cálculo de file_length do LUR
    # Tipo: Requisito Funcional
    # Descrição: O campo file_length DEVE ser calculado como
    #            4 + 2 + 2 + 1 + len_header + 1 + len_pn (big-endian).
    # Autor: Julia | Revisor: Fabrício
    # ============================================================================

    total_length = 4 + 2 + 2 + 1 + len_header + 1 + len_pn

    # ============================================================================
    # REQ: GSE-LLR-58 – Layout binário do LUR (big-endian)
    # Tipo: Requisito Funcional
    # Descrição: O payload DEVE ser montado exatamente na ordem:
    #            file_length ('!L'), protocol_version (2 bytes), num_headers ('!H'),
    #            len_header ('!B'), header_bytes, len_pn ('!B'), pn_bytes.
    # Autor: Julia | Revisor: Fabrício
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
    # REQ: GSE-LLR-59 – Determinismo binário do LUR
    # Tipo: Requisito Não Funcional
    # Descrição: Para mesmas entradas (header_filename, part_number), a função DEVE
    #            produzir bytes idênticos em execuções repetidas (determinismo).
    # Autor: Julia | Revisor: Fabrício
    # ============================================================================

    return pkt
