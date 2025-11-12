import struct
import socket
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.protocols.tftp_client import TFTPClient, TFTP_OPCODE, BLOCK_SIZE  # noqa: E402

# ============================================================================
# REQ: GSE-LLR-63 – Proteção a UNKNOWN_TID e consistência de sessão
# Descrição: Aceitar/responder apenas pacotes do TID do servidor associado à 
# transferência ativa; ignorar TIDs estranhos.
# Tipo: Requisito Funcional
# Autor: Bruno Melão
# ============================================================================


def make_data_packet(block, payload: bytes) -> bytes:
    return struct.pack("!HH", TFTP_OPCODE.DATA.value, block) + payload


class MockSocket:
    def __init__(self, responses):
        # responses: list of tuples (packet_bytes, (ip, port)) to be returned by recvfrom
        self._responses = list(responses)
        self.sent = []
        self._timeout = 10
        self.closed = False

    def settimeout(self, t):
        self._timeout = t

    def gettimeout(self):
        return self._timeout

    def sendto(self, pkt, addr):
        # record sent packets for inspection
        self.sent.append((pkt, addr))

    def recvfrom(self, n):
        if not self._responses:
            raise socket.timeout()
        return self._responses.pop(0)

    def close(self):
        self.closed = True


@pytest.fixture
def tftp_client():
    """Instancia um TFTPClient com logger no-op (seguindo outros testes do projeto)."""
    client = TFTPClient("127.0.0.1", logger=lambda _msg: None)
    return client


def test_tftp_tid_filters_unrelated_tids(tftp_client):
    """Verifica que pacotes vindo de TIDs não relacionados são ignorados."""
    logs = []
    # instrui o cliente a usar nosso capturador de logs
    tftp_client.logger = lambda m: logs.append(m)

    # Prepara três pacotes: DATA(1) from server:50000, DATA(2) from wrong:40000, DATA(2) from server:50000
    # Make first block full-size so read_file does not treat it as the final block
    pkt1 = make_data_packet(1, b'A' * BLOCK_SIZE)
    pkt_wrong = make_data_packet(2, b'WRONG')
    pkt2 = make_data_packet(2, b'world')

    server_ip = '127.0.0.1'
    responses = [
        (pkt1, (server_ip, 50000)),
        (pkt_wrong, (server_ip, 40000)),
        (pkt2, (server_ip, 50000)),
    ]

    mock_sock = MockSocket(responses)
    tftp_client.sock = mock_sock

    result = tftp_client.read_file('somefile.bin')

    # final result should contain the full first block followed by the second small block
    assert result.endswith(b'world')
    assert result.startswith(b'A' * 4)  # quick sanity check the large block is present
    assert tftp_client.server_tid == 50000
    assert any('TID inesperado' in str(m) for m in logs)
