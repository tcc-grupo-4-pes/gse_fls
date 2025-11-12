import struct
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.protocols.tftp_client import TFTPClient, TFTP_OPCODE  # noqa: E402

# ============================================================================
# REQ: GSE-HLR-71 – Parsing estrito e robusto de pacotes TFTP
# Tipo: Requisito Funcional
# Descrição: Parsear estritamente DATA/ACK/RRQ/WRQ/ERROR, validar tamanhos
#            mínimos e campos big-endian, retornando estruturas/erros
#            padronizados.
# Autor: Felipe Rosa
# ============================================================================


@pytest.fixture
def tftp_client():
    """Instancia um cliente TFTP sem interação de rede real."""
    return TFTPClient("127.0.0.1", logger=lambda _msg: None)


@pytest.mark.hlr71
@pytest.mark.functional
@pytest.mark.parametrize(
    "packet,expected",
    [
        (
            struct.pack("!HH", TFTP_OPCODE.DATA.value, 42) + b"PAYLOAD",
            (TFTP_OPCODE.DATA, 42, b"PAYLOAD"),
        ),
        (b"\x00\x03\x00", (None, 0, b"")),
    ],
)
def test_gse_hlr_71_parse_data_packet(tftp_client, packet, expected):
    """Valida parsing de DATA em casos normal e truncado."""
    assert tftp_client._parse_data_packet(packet) == expected


@pytest.mark.hlr71
@pytest.mark.functional
@pytest.mark.parametrize(
    "packet,expected",
    [
        (struct.pack("!HH", TFTP_OPCODE.ACK.value, 7), (TFTP_OPCODE.ACK, 7)),
        (b"\x00\x04\x00", (None, 0)),
    ],
)
def test_gse_hlr_71_parse_ack_packet(tftp_client, packet, expected):
    """Valida parsing de ACK em casos normal e truncado."""
    assert tftp_client._parse_ack_packet(packet) == expected


@pytest.mark.hlr71
@pytest.mark.functional
@pytest.mark.parametrize(
    "packet,expected",
    [
        (
            struct.pack("!H", TFTP_OPCODE.RRQ.value)
            + b"firmware.bin\0octet\0",
            (TFTP_OPCODE.RRQ, "firmware.bin"),
        ),
        (b"\x00\x01\x00", (None, "")),
    ],
)
def test_gse_hlr_71_parse_rrq_packet(tftp_client, packet, expected):
    """Valida parsing de RRQ em cenários válido e inválido."""
    assert tftp_client._parse_rrq_packet(packet) == expected


@pytest.mark.hlr71
@pytest.mark.functional
@pytest.mark.parametrize(
    "packet,expected",
    [
        (
            struct.pack("!HH", TFTP_OPCODE.ERROR.value, 5) + b"Disk full\0",
            (5, "Disk full"),
        ),
        (b"\x00\x05\x00", (0, "Pacote de erro malformado")),
    ],
)
def test_gse_hlr_71_parse_error_packet(tftp_client, packet, expected):
    """Valida parsing de ERROR em cenários válido e truncado."""
    assert tftp_client._parse_error_packet(packet) == expected
