import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.protocols import hash_utils  # noqa: E402


# ============================================================================
# REQ: HLR-58 / GSE-LLR-86 – Resiliência do cálculo de hash
# Tipo: Requisito Não Funcional
# Descrição: O sistema DEVE manter a continuidade do fluxo em caso de entradas
# inválidas ou exceções no cálculo do hash, registrando erro padronizado e
# retornando valor nulo convencionado (32 bytes) para tratamento a jusante.
# Autor: Bruno Melão
# ============================================================================


def test_calculate_file_hash_with_invalid_type_returns_null_hash(capsys):
    """Quando receber tipo inválido, retorna bytes(32) e loga '[HASH-ERRO]'."""
    res = hash_utils.calculate_file_hash("not-bytes")
    assert isinstance(res, (bytes, bytearray))
    assert res == bytes(32)

    captured = capsys.readouterr()
    assert "[HASH-ERRO]" in captured.out
    assert "Tipo inválido" in captured.out


def test_calculate_file_hash_handles_internal_exception(monkeypatch, capsys):
    """Se hashlib.sha256 levantar exceção, a função deve capturar, logar e retornar bytes(32)."""

    # Substitui sha256 por uma função que levanta erro ao ser chamada
    def fake_sha256(data):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(hash_utils.hashlib, "sha256", fake_sha256)

    res = hash_utils.calculate_file_hash(b"some data")
    assert res == bytes(32)

    captured = capsys.readouterr()
    assert "[HASH-ERRO]" in captured.out
    assert "Falha ao calcular hash" in captured.out
