import hashlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.protocols.hash_utils import calculate_file_hash  # noqa: E402, import do modelo a ser testado

# ============================================================================
# REQ: GSE-HLR-59 – Interface de hashing compatível com buffers
# Tipo: Requisito Funcional
# Descrição: O sistema DEVE aceitar buffers do tipo bytes-like (bytes,
#            bytearray, memoryview) sem efeitos colaterais sobre os dados
#            de entrada.
# Autor: Felipe Rosa
# ============================================================================


@pytest.fixture
def sample_payload():
    return b"ARINC-615A-hash"


@pytest.fixture
def expected_digest(sample_payload):
    return hashlib.sha256(sample_payload).digest()


def test_gse_hlr_59_accepts_bytes(sample_payload, expected_digest):
    """Critério 1 – aceita `bytes` sem alterações."""
    # Calcula o hash SHA-256 do payload usando tipo bytes
    digest = calculate_file_hash(sample_payload)
    
    # Verificação se o hash calculado é idêntico ao esperado
    assert digest == expected_digest


def test_gse_hlr_59_accepts_bytearray(sample_payload, expected_digest):
    """Critério 2 – bytearray é convertido sem mutação do buffer."""
    # Cria um bytearray e guarda uma cópia para verificar não-mutação
    buffer = bytearray(sample_payload)
    original_copy = bytes(buffer)

    # Calcula o hash SHA-256 do buffer bytearray
    digest = calculate_file_hash(buffer)

    # Verificação se o hash está correto e o buffer não foi modificado
    assert digest == expected_digest
    assert bytes(buffer) == original_copy


def test_gse_hlr_59_accepts_memoryview(sample_payload, expected_digest):
    """Critério 3 – memoryview é suportado sem alterar o conteúdo base."""
    # Cria um memoryview a partir de um bytearray
    backing = bytearray(sample_payload)
    view = memoryview(backing)

    # Calcula o hash SHA-256 usando memoryview
    digest = calculate_file_hash(view)

    # Verificação se o hash está correto e o buffer backing não foi modificado
    assert digest == expected_digest
    assert bytes(backing) == sample_payload


def test_gse_hlr_59_invalid_type_returns_null_hash(capsys):
    """Critério 4 – tipo inválido gera bytes(32) e log padronizado."""
    # Passa um tipo inválido (string) para a função de hash
    digest = calculate_file_hash("not-bytes")

    # Captura a saída do console para verificar mensagem de erro
    captured = capsys.readouterr()
    
    # Verificação se retornou hash nulo e gerou log de erro padronizado
    assert digest == bytes(32)
    assert "[HASH-ERRO]" in captured.out
