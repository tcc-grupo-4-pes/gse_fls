import struct
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.protocols import arinc_models  # import do modelo a ser testado

# ============================================================================
# REQ: GSE-HLR-43 – Padronizar tratamento de erros de parsing
# Tipo: Requisito Funcional
# Descrição: O sistema DEVE padronizar as respostas de erro para todas as
#            funções de parsing e validação dos arquivos ARINC, retornando
#            mensagens claras e estruturadas no formato {"error": <mensagem>}.
# Autor: Felipe Rosa
# ============================================================================


@pytest.fixture
def sample_lui_payload():
    file_length = 9 + 5  # base 9 bytes + description length
    payload = struct.pack("!L", file_length)
    payload += b"A4"
    payload += struct.pack("!H", 0x0003)
    payload += struct.pack("!B", 5)
    payload += b"READY"
    return payload


def test_parse_lui_response_standard_error_format(monkeypatch, sample_lui_payload):
    def _boom(*_args, **_kwargs):
        raise RuntimeError("falha teste")

    # monkeypatch.setattr() substitui temporariamente struct.unpack 
    # por uma função que sempre gera exceção
    monkeypatch.setattr(arinc_models.struct, "unpack", _boom)
    result = arinc_models.parse_lui_response(sample_lui_payload)

    # Verificação se foi gerado um erro no formato esperado
    assert result == {"error": "Erro ao analisar LUI: falha teste"}


def test_parse_lus_progress_propagates_lui_error(sample_lui_payload):
    # Modifica o payload LUI para criar dados malformados
    malformed = bytearray(sample_lui_payload)
    malformed[8] = 10  # inconsistent length to trigger LUI error
    malformed = bytes(malformed) + b"000"
    
    # Chama parse_lus_progress que internamente chama parse_lui_response
    result = arinc_models.parse_lus_progress(malformed)
    
    # Verificação se o erro do LUI foi propagado corretamente no formato esperado
    assert result == {"error": "Dados LUI incompletos para description"}


def test_parse_lus_progress_standard_error_format(monkeypatch, sample_lui_payload):
    def _explode(_data):
        raise ValueError("falha interna")

    # monkeypatch.setattr() substitui temporariamente parse_lui_response
    # por uma função que sempre gera exceção
    monkeypatch.setattr(arinc_models, "parse_lui_response", _explode)
    payload = sample_lui_payload + b"000"
    result = arinc_models.parse_lus_progress(payload)
    
    # Verificação se foi gerado um erro no formato esperado
    assert result == {"error": "Erro ao analisar progresso LUS: falha interna"}
