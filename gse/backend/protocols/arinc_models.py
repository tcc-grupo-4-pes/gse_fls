#!/usr/bin/env python3
"""
Módulo de Modelos de Dados ARINC 615A

Contém funções "helper" puras para construir e analisar
os pacotes de metadados (LUI, LUS, LUR) e calcular hashes
usados no fluxo de transferência.

Não contém dependências do Qt (PySide6) nem lógica TFTP.
"""

import struct
import hashlib
from typing import Dict, Any

# ============ CONSTANTES DE STATUS ARINC ============
ARINC_STATUS_ACCEPTED = 0x0001
ARINC_STATUS_IN_PROGRESS = 0x0002
ARINC_STATUS_COMPLETED_OK = 0x0003
ARINC_STATUS_REJECTED = 0x1000

# Mapeamento de status para nomes legíveis
ARINC_STATUS_MAP = {
    ARINC_STATUS_ACCEPTED: "Operação Aceita",
    ARINC_STATUS_IN_PROGRESS: "Em Progresso",
    ARINC_STATUS_COMPLETED_OK: "Concluído com Sucesso",
    ARINC_STATUS_REJECTED: "Operação Rejeitada",
}

# ============ FUNÇÕES DE PARSING (Leitura) ============


def parse_lui_response(data: bytes) -> Dict[str, Any]:
    """
    Analisa a resposta de um arquivo LUI (Load Unit Information).
    Formato: [file_length(4)][protocol_version(2)][status_code(2)][desc_length(1)][description(n)]
    """
    if len(data) < 9:
        return {"error": "Dados LUI insuficientes"}

    try:
        file_length = struct.unpack("!L", data[0:4])[0]
        protocol_version = data[4:6].decode("ascii", errors="ignore")
        status_code = struct.unpack("!H", data[6:8])[0]
        desc_length = data[8]
        description = data[9 : 9 + desc_length].decode("ascii", errors="ignore")

        return {
            "file_length": file_length,
            "protocol_version": protocol_version,
            "status_code": f"0x{status_code:04x}",
            "status_name": ARINC_STATUS_MAP.get(status_code, "Desconhecido"),
            "desc_length": desc_length,
            "description": description,
        }
    except Exception as e:
        return {"error": f"Erro ao analisar LUI: {e}"}


def parse_lus_progress(data: bytes) -> Dict[str, Any]:
    """
    Analisa um arquivo LUS (Load Unit Status) para extrair o progresso.
    Formato: [file_length(4)][protocol_version(2)][status_code(2)][desc_length(1)][description(n)][...][progress(3)]

    Nota: O progresso (ex: "050", "100") são os 3 últimos bytes do payload.
    """
    if len(data) < 12:  # 9 bytes de header + 3 de progresso
        return {"error": "Dados LUS insuficientes"}

    try:
        # Analisa o cabeçalho LUS (idêntico ao LUI)
        lus_data = parse_lui_response(data)
        if "error" in lus_data:
            return lus_data  # Propaga o erro de parsing do LUI

        # Extrai o progresso dos últimos 3 bytes
        progress_str = data[-3:].decode("ascii")
        progress_pct = int(progress_str)

        lus_data["progress_str"] = progress_str
        lus_data["progress_pct"] = progress_pct

        return lus_data

    except Exception as e:
        return {"error": f"Erro ao analisar progresso LUS: {e}"}


# ============ FUNÇÕES DE CONSTRUÇÃO (Escrita) ============


def build_lur_packet(header_filename: str, part_number: str) -> bytes:
    """
    Constrói o payload de um arquivo LUR (Load Unit Request).

    :param header_filename: O nome do arquivo .bin que será solicitado (ex: "fw.bin")
    :param part_number: O Part Number (ex: "PN12345")
    :return: Payload (bytes) do arquivo LUR.
    """

    # 1. Converte strings para bytes
    header_bytes = header_filename.encode("ascii")
    pn_bytes = part_number.encode("ascii")

    # 2. Define os campos de tamanho
    len_header = len(header_bytes)
    len_pn = len(pn_bytes)

    # 3. Calcula o tamanho total do arquivo LUR
    # (4) file_length + (2) protocol_version + (2) num_headers +
    # (1) len_header + (n) header_bytes +
    # (1) len_pn + (m) pn_bytes
    total_length = 4 + 2 + 2 + 1 + len_header + 1 + len_pn

    # 4. Monta o pacote
    pkt = b""
    pkt += struct.pack("!L", total_length)  # file_length (4 bytes)
    pkt += b"A4"  # protocol_version (2 bytes)
    pkt += struct.pack("!H", 1)  # num_headers (2 bytes)

    # Header 1: Nome do arquivo
    pkt += struct.pack("!B", len_header)  # Comprimento do nome (1 byte)
    pkt += header_bytes  # Nome do arquivo (n bytes)

    # Header 2: Part Number
    pkt += struct.pack("!B", len_pn)  # Comprimento do PN (1 byte)
    pkt += pn_bytes  # Part Number (m bytes)

    return pkt


# ============ FUNÇÕES DE HASHING ============


def calculate_file_hash(data: bytes) -> bytes:
    """
    Calcula o hash SHA-256 de um bloco de dados.

    :param data: Os dados completos do arquivo (ex: fw.bin).
    :return: O hash SHA-256 "cru" (32 bytes).
    """
    try:
        return hashlib.sha256(data).digest()
    except Exception as e:
        print(f"[MODEL-ERRO] Falha ao calcular hash: {e}")
        return bytes(32)  # Retorna um hash nulo de 32 bytes em caso de falha
