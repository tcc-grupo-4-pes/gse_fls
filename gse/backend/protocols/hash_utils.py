#!/usr/bin/env python3
"""
Módulo Utilitário de Hashing

Fornece funções para operações de criptografia,
especificamente o cálculo de hash SHA-256.
"""

# ============================================================================
# REQ: GSE-LLR-300 – Usar biblioteca padrão para hashing
# Tipo: Requisito Não Funcional
# Descrição: Utilizar hashlib da biblioteca padrão para SHA-256, evitando
#            dependências externas.
# Critérios de Aceitação:
#  - Importar apenas 'hashlib'.
# Autor: (preencher) | Revisor: (preencher)
# ============================================================================
import hashlib
from typing import Union


def calculate_file_hash(data: Union[bytes, bytearray, memoryview]) -> bytes:
    """
    Calcula o hash SHA-256 de um bloco de dados.

    :param data: Os dados completos do arquivo (ex: fw.bin).
    :return: O hash SHA-256 "cru" (32 bytes).
    """

    # ============================================================================
    # REQ: GSE-LLR-301 – Interface de entrada bytes-like
    # Tipo: Requisito Funcional
    # Descrição: Aceitar dados do tipo bytes, bytearray ou memoryview.
    # Critérios de Aceitação:
    #  - Converter bytearray/memoryview para bytes sem cópias desnecessárias.
    #  - Rejeitar tipos não suportados com mensagem de erro clara.
    # Autor: (preencher) | Revisor: (preencher)
    # ============================================================================
    if isinstance(data, (bytearray, memoryview)):
        data = bytes(data)
    elif not isinstance(data, (bytes,)):
        # ============================================================================
        # REQ: GSE-LLR-304 – Tratamento padronizado de erro de tipo
        # Tipo: Requisito Não Funcional
        # Descrição: Em tipo inválido, registrar mensagem padronizada e
        #            retornar hash nulo (32 bytes) sem lançar exceção.
        # Critérios de Aceitação:
        #  - Mensagem iniciando com "[HASH-ERRO]".
        #  - Retornar bytes(32).
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        print(f"[HASH-ERRO] Tipo inválido para 'data': {type(data).__name__}")
        return bytes(32)

    # ============================================================================
    # REQ: GSE-LLR-302 – Cálculo com SHA-256
    # Tipo: Requisito Funcional
    # Descrição: Calcular o digest SHA-256 dos dados fornecidos.
    # Critérios de Aceitação:
    #  - Usar hashlib.sha256(data).digest().
    #  - Não alterar 'data'.
    # Autor: (preencher) | Revisor: (preencher)
    # ============================================================================

    try:
        digest = hashlib.sha256(data).digest()

        # ============================================================================
        # REQ: GSE-LLR-303 – Tamanho e determinismo do resultado
        # Tipo: Requisito Não Funcional
        # Descrição: Garantir que o resultado tenha 32 bytes e que a função seja
        #            determinística (mesma entrada → mesmo digest).
        # Critérios de Aceitação:
        #  - len(digest) == 32.
        #  - Teste com vetor conhecido (entrada vazia).
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        if len(digest) != 32:
            print("[HASH-ERRO] Digest SHA-256 com tamanho inesperado.")
            return bytes(32)

        return digest

    except Exception as e:
        # ============================================================================
        # REQ: GSE-LLR-305 – Resiliência a exceções de hashing
        # Tipo: Requisito Não Funcional
        # Descrição: Em qualquer exceção de hashing, registrar erro e retornar
        #            hash nulo (32 bytes) para não interromper o fluxo.
        # Critérios de Aceitação:
        #  - Mensagem iniciando com "[HASH-ERRO]".
        #  - Retornar bytes(32).
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        print(f"[HASH-ERRO] Falha ao calcular hash: {e}")
        return bytes(32)
