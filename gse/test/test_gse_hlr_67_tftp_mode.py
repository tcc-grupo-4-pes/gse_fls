import struct
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.protocols.tftp_client import TFTPClient, TFTP_OPCODE  # noqa: E402


# ============================================================================
# REQ: GSE-LLR-67 – Enforce de modo “octet” nas transferências
# Descrição: Utilizar exclusivamente o modo “octet” nas operações TFTP, 
# rejeitando modos alternativos.
# Tipo: Requisito Funcional
# Autor: Bruno Melão
# ============================================================================

class _DummySocket:
    """Socket falso para capturar dados enviados sem abrir rede real."""

    def __init__(self):
        self.last_data = None
        self.last_addr = None

    def sendto(self, data, addr):
        self.last_data = data
        self.last_addr = addr


@pytest.fixture
def tftp_client():
    client = TFTPClient("127.0.0.1", logger=lambda _msg: None)
    client.sock = _DummySocket()
    return client


def _extract_mode_from_request(payload: bytes) -> str:
    # payload layout: 2 bytes opcode, filename\0, mode\0
    rest = payload[2:]
    parts = rest.split(b"\0")
    # parts[0]=filename, parts[1]=mode
    if len(parts) < 2:
        return ""
    return parts[1].decode(errors="ignore")


def test_rrq_force_octet_mode(tftp_client):
    """RRQ deve sempre usar o modo 'octet' mesmo que outro modo seja solicitado."""
    # Aceitamos duas implementações válidas:
    # 1) Forçar serializar 'octet' independentemente do argumento
    # 2) Rejeitar modos alternativos levantando ValueError
    try:
        tftp_client._send_rrq("../payloads/firmware.bin", "netascii", ("10.0.0.2", 69))
    except ValueError:
        # comportamento aceitável: rejeita modo não-octet
        return

    payload = tftp_client.sock.last_data
    assert payload is not None
    mode = _extract_mode_from_request(payload)
    assert mode == "octet"


def test_wrq_force_octet_mode(tftp_client):
    """WRQ deve sempre usar o modo 'octet' mesmo que outro modo seja solicitado."""
    try:
        tftp_client._send_wrq("..\\bad\\firmware.bin", "ascii", ("10.0.0.2", 69))
    except ValueError:
        return

    payload = tftp_client.sock.last_data
    assert payload is not None
    mode = _extract_mode_from_request(payload)
    assert mode == "octet"
