import struct
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.protocols import arinc_models  # import do modelo a ser testado

# ============================================================================
# REQ: GSE-HLR-42 – Validar conformidade binária e limites de campos
# Tipo: Requisito Funcional
# Descrição: O software DEVE validar tamanhos, limites e codificações ASCII
#            dos campos dos arquivos LUI, LUS e LUR, garantindo a conformidade
#            com o formato big-endian e os limites máximos de 1 byte (0 a 255)
#            para campos de comprimento.
# Autor: Felipe Rosa
# ============================================================================


@pytest.fixture
def sample_lui_payload():
    """Return a canonical LUI payload with ASCII fields and valid lengths."""
    file_length = 9 + 5  # base 9 bytes + description length
    protocol_version = b"A4"
    status_code = 0x0003
    description = b"READY"
    desc_length = len(description)

    payload = struct.pack("!L", file_length)
    payload += protocol_version
    payload += struct.pack("!H", status_code)
    payload += struct.pack("!B", desc_length)
    payload += description
    return payload


def test_parse_lui_response_validates_ascii_protocol_version(sample_lui_payload):
    # Modifica o campo Protocol Version para conter bytes não-ASCII
    payload = bytearray(sample_lui_payload)
    payload[4:6] = b"\xff\xfe"  # Not decodable as ASCII 2 chars
    
    # Tenta fazer o parsing do payload modificado
    result = arinc_models.parse_lui_response(bytes(payload))
    
    # Verificação se a validação ASCII rejeitou o payload inválido
    assert result == {"error": "Protocol Version inválido (não ASCII de 2 chars)"}


def test_parse_lui_response_rejects_truncated_description(sample_lui_payload):
    # Remove bytes do final do payload para truncar o campo description
    truncated = sample_lui_payload[:-2]  # remove two bytes from description
    
    # Tenta fazer o parsing do payload truncado
    result = arinc_models.parse_lui_response(truncated)
    
    # Verificação se detectou dados incompletos
    assert result == {"error": "Dados LUI incompletos para description"}


def test_parse_lui_response_parses_big_endian_fields(sample_lui_payload):
    # Faz o parsing do payload LUI
    result = arinc_models.parse_lui_response(sample_lui_payload)
    
    # Verificação se os campos big-endian foram interpretados corretamente
    assert result["file_length"] == struct.unpack("!L", sample_lui_payload[:4])[0]
    assert result["status_code"] == "0x0003"
    assert result["desc_length"] == 5
    assert result["description"] == "READY"


def test_parse_lus_progress_validates_ascii_and_range(sample_lui_payload):
    # Testa com progresso contendo caractere não-numérico ASCII
    payload = sample_lui_payload + b"1x0"  # invalid ascii digit
    result = arinc_models.parse_lus_progress(payload)
    
    # Verificação se rejeitou progresso com caracteres inválidos
    assert result == {"error": "Progresso LUS inválido (deve ser '000'..'100')"}

    # Testa com progresso numérico mas fora da faixa permitida
    payload = sample_lui_payload + b"150"  # numeric but out of range
    result = arinc_models.parse_lus_progress(payload)
    
    # Verificação se rejeitou progresso fora da faixa 0-100
    assert result == {"error": "Progresso LUS fora da faixa (0..100)"}


def test_build_lur_packet_enforces_ascii_and_limits():
    # Define parâmetros válidos para geração do pacote LUR
    header = "header.bin"
    part_number = "EMB-SW-007-137-045"
    lur_bytes = arinc_models.build_lur_packet(header, part_number)

    # Verificação se o campo total_length em big-endian corresponde ao tamanho real
    total_length = struct.unpack("!L", lur_bytes[:4])[0]
    assert total_length == len(lur_bytes)

    # Verificação se o campo num_headers está correto (2 headers: header + part_number)
    num_headers = struct.unpack("!H", lur_bytes[6:8])[0]
    assert num_headers == 2

    # Verificação se o campo header_len (1 byte) está dentro do limite de 0-255
    header_len = lur_bytes[8]
    assert header_len == len(header.encode("ascii"))

    # Verificação se o campo part_number_len (1 byte) está correto
    pn_len_index = 9 + header_len
    pn_len = lur_bytes[pn_len_index]
    assert pn_len == len(part_number.encode("ascii"))

    # Verificação se rejeita header_filename com caracteres não-ASCII
    with pytest.raises(ValueError, match="header_filename contém caracteres não-ASCII"):
        arinc_models.build_lur_packet("cabeçalho.bin", part_number)

    # Verificação se rejeita header_filename excedendo limite de 255 bytes
    with pytest.raises(ValueError, match="header_filename excede 255 bytes ASCII"):
        arinc_models.build_lur_packet("a" * 256, part_number)

    # Verificação se rejeita part_number excedendo limite de 255 bytes
    with pytest.raises(ValueError, match="part_number excede 255 bytes ASCII"):
        arinc_models.build_lur_packet(header, "9" * 256)
