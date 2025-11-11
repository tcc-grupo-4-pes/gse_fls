

import struct
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.protocols.tftp_client import TFTPClient, TFTP_OPCODE  # noqa: E402, import do modelo a ser testado

# ============================================================================
# REQ: GSE-HLR-68 – Sanitização de nomes de arquivo
# Tipo: Requisito Não Funcional
# Descrição: Sanitizar nomes em RRQ/WRQ para impedir path traversal,
#            caracteres de controle e separadores inválidos.
# Autor: Felipe Rosa
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
    """Instancia um TFTPClient com socket falso para observar RRQ/WRQ."""
    client = TFTPClient("127.0.0.1", logger=lambda _msg: None)
    client.sock = _DummySocket()
    return client


def test_gse_hlr_68_remove_path_segments():
    """remove diretórios e limpa segmentos '..'."""
    # Testa sanitização de nome de arquivo com path traversal
    sanitized = TFTPClient._sanitize_filename("..\\etc/passwd")
    
    # Verificação se removeu diretórios e segmentos perigosos
    assert sanitized == "passwd"
    assert ".." not in sanitized


@pytest.mark.parametrize(
    "raw_name,expected",
    [
        ("..\\firmware.bin", "firmware.bin"),
        ("/tmp/EMB-123?.bin", "EMB-123_.bin"),
        ("firmware\x00.bin", "firmware_.bin"),
    ],
)
def test_gse_hlr_68_replace_invalid_characters(raw_name, expected):
    """substitui caracteres fora da whitelist por '_'."""
    # Testa sanitização de caracteres inválidos em nomes de arquivo
    sanitized = TFTPClient._sanitize_filename(raw_name)
    
    # Verificação se caracteres perigosos foram substituídos por '_'
    assert sanitized == expected


def test_gse_hlr_68_rejects_dotdot_sequence():
    """rejeita nomes ainda contendo '..' após limpeza inicial."""
    # Testa se rejeita sequência '..' que permanece após sanitização
    with pytest.raises(ValueError):
        TFTPClient._sanitize_filename("firmware..bin")


def test_gse_hlr_68_rrq_uses_sanitized_name(tftp_client):
    """RRQ deve serializar apenas o filename sanitizado."""
    # Envia uma requisição RRQ com nome de arquivo malicioso
    tftp_client._send_rrq("../payloads/firmware?.bin", "octet", ("10.0.0.2", 69))

    # Captura o payload enviado pelo socket falso
    payload = tftp_client.sock.last_data
    opcode = struct.unpack("!H", payload[:2])[0]
    filename = payload[2:].split(b"\0", 1)[0].decode()

    # Verificação se o RRQ foi serializado com opcode correto e nome sanitizado
    assert opcode == TFTP_OPCODE.RRQ.value
    assert filename == "firmware_.bin"
    assert b".." not in payload


def test_gse_hlr_68_wrq_uses_sanitized_name(tftp_client):
    """WRQ aplica o mesmo sanitizador antes do envio."""
    # Envia uma requisição WRQ com nome de arquivo malicioso
    tftp_client._send_wrq("..\\bad\\firmware.bin", "octet", ("10.0.0.2", 69))

    # Captura o payload enviado pelo socket falso
    payload = tftp_client.sock.last_data
    opcode = struct.unpack("!H", payload[:2])[0]
    filename = payload[2:].split(b"\0", 1)[0].decode()

    # Verificação se o WRQ foi serializado com opcode correto e nome sanitizado
    assert opcode == TFTP_OPCODE.WRQ.value
    assert filename == "firmware.bin"
    assert "/" not in filename
