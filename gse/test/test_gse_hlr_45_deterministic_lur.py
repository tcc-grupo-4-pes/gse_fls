import hashlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.protocols import arinc_models  # import do modelo a ser testado

# ============================================================================
# REQ: GSE-HLR-45 – Garantir consistência e determinismo binário
# Tipo: Requisito Funcional
# Descrição: O sistema DEVE garantir que a geração de pacotes LUR (Load
#            Upload Request) seja determinística, produzindo binários idênticos
#            para as mesmas entradas (header_filename e part_number).
# Autor: Felipe Rosa
# ============================================================================


def _generate_lur_bytes(header_filename: str, part_number: str) -> bytes:
    """Isola a chamada real de geração de LUR usada pelo sistema."""
    return arinc_models.build_lur_packet(header_filename, part_number)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.mark.hlr45
@pytest.mark.functional
def test_lur_generation_is_deterministic():
    """Mesmas entradas devem produzir binários idênticos."""
    # Define os parâmetros de entrada para geração do LUR
    header = "GSE-HEADER"
    part_number = "EMB-123456"
    
    # Gera o pacote LUR duas vezes com os mesmos parâmetros
    first = _generate_lur_bytes(header, part_number)
    second = _generate_lur_bytes(header, part_number)
    
    # Verificação se os binários são idênticos (determinismo)
    assert first == second, (
        "LURs divergentes para as mesmas entradas (header_filename/part_number)"
    )
    
    # Verificação adicional usando SHA-256 para garantir integridade completa
    assert _sha256(first) == _sha256(second), (
        "SHA-256 diferente para a mesma entrada"
    )

