#!/usr/bin/env python3
"""
Módulo Utilitário de Hashing

Fornece funções para operações de criptografia,
especificamente o cálculo de hash SHA-256.
"""

# ============================================================================
# REQ: GSE-LLR-81 – Uso de hashlib da biblioteca padrão
# Tipo: Requisito Não Funcional
# Descrição: O módulo DEVE utilizar exclusivamente a biblioteca padrão 'hashlib'
#            para o cálculo de SHA-256, evitando dependências externas e garantindo
#            portabilidade.
# Autor: Julia | Revisor: Fabrício
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
    # REQ: GSE-LLR-82 – Interface de entrada bytes-like
    # Tipo: Requisito Funcional
    # Descrição: A função DEVE aceitar dados do tipo bytes, bytearray ou memoryview
    #            e, quando receber bytearray/memoryview, DEVE convertê-los para bytes
    #            sem alterar o conteúdo original, preservando o comportamento de
    #            somente leitura do buffer.
    # Autor: Julia | Revisor: Fabrício
    # ============================================================================
    if isinstance(data, (bytearray, memoryview)):
        data = bytes(data)
    elif not isinstance(data, (bytes,)):
        # ============================================================================
        # REQ: GSE-LLR-83 – Tratamento padronizado de tipo inválido
        # Tipo: Requisito Não Funcional
        # Descrição: Quando o parâmetro 'data' não for um tipo suportado, a função
        #            DEVE registrar uma mensagem padronizada iniciando com
        #            "[HASH-ERRO]" indicando o tipo inválido e DEVE retornar um
        #            hash nulo de 32 bytes (bytes(32)) sem lançar exceção, para não
        #            interromper o fluxo de chamada.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================
        print(f"[HASH-ERRO] Tipo inválido para 'data': {type(data).__name__}")
        return bytes(32)

    # ============================================================================
    # REQ: GSE-LLR-84 – Cálculo de digest SHA-256
    # Tipo: Requisito Funcional
    # Descrição: A função DEVE calcular o digest SHA-256 dos dados fornecidos usando
    #            hashlib.sha256(data).digest(), sem modificar o conteúdo de 'data'.
    # Autor: Julia | Revisor: Fabrício
    # ============================================================================
    try:
        digest = hashlib.sha256(data).digest()

        # ============================================================================
        # REQ: GSE-LLR-85 – Tamanho e determinismo do resultado
        # Tipo: Requisito Não Funcional
        # Descrição: O resultado DEVE possuir exatamente 32 bytes e o cálculo DEVE ser
        #            determinístico (mesma entrada resulta no mesmo digest); caso o
        #            tamanho seja diferente de 32, a função DEVE registrar
        #            "[HASH-ERRO] Digest SHA-256 com tamanho inesperado." e retornar
        #            bytes(32).
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================
        if len(digest) != 32:
            print("[HASH-ERRO] Digest SHA-256 com tamanho inesperado.")
            return bytes(32)

        return digest

    except Exception as e:
        # ============================================================================
        # REQ: GSE-LLR-86 – Resiliência a exceções no hashing
        # Tipo: Requisito Não Funcional
        # Descrição: Em qualquer exceção durante o cálculo do hash, a função DEVE
        #            registrar a mensagem iniciando com "[HASH-ERRO]" seguida do erro
        #            original e DEVE retornar bytes(32), assegurando continuidade do
        #            fluxo do chamador.
        # Autor: Julia | Revisor: Fabrício
        # ============================================================================
        print(f"[HASH-ERRO] Falha ao calcular hash: {e}")
        return bytes(32)
