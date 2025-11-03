#!/usr/bin/env python3
"""
Módulo de Logger de Sessão do GSE

Fornece uma classe 'GseLogger' que gerencia a criação e escrita
de arquivos de log baseados em sessão.

Cada instância da classe cria um novo arquivo de log com timestamp
em um subdiretório 'logs/'.
"""

import os
import datetime
from typing import TextIO


class GseLogger:
    """
    Gerencia um único arquivo de log para uma sessão de
    transferência do GSE.
    """

    LOG_DIR = "logs"

    def __init__(self):
        """
        Inicializa o logger, cria o diretório de logs (se não existir)
        e abre o arquivo de log da sessão.
        """
        self.log_file: TextIO | None = None
        self.log_path: str = ""
        self._init_log_file()

    def _init_log_file(self):
        """
        Cria o diretório e o arquivo de log com timestamp.
        """
        try:
            # Garante que o diretório 'logs' exista
            # (path relativo a onde o script está rodando)
            log_dir_path = os.path.abspath(self.LOG_DIR)
            os.makedirs(log_dir_path, exist_ok=True)

            # Gera um nome de arquivo único
            now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"GSE_Sessao_{now_str}.txt"

            self.log_path = os.path.join(log_dir_path, filename)

            # Abre o arquivo em modo 'append' (a) com encoding utf-8
            self.log_file = open(self.log_path, "a", encoding="utf-8")

            print(f"Sessão de log iniciada. Arquivo: {self.log_path}")

        except Exception as e:
            print(f"ERRO CRÍTICO: Falha ao inicializar logger de arquivo: {e}")
            self.log_file = None

    def get_log_path(self) -> str:
        """Retorna o caminho do arquivo de log atual."""
        return self.log_path

    def write_log(self, message: str):
        """
        Escreve uma única mensagem formatada no arquivo de log.
        """
        if not self.log_file:
            print(f"LOG (sem arquivo): {message}")
            return

        try:
            # Adiciona timestamp a cada linha
            # ex: [10:53:01.123] Mensagem...
            now = datetime.datetime.now()
            timestamp = now.strftime("%H:%M:%S")
            ms = now.microsecond // 1000  # Pega milissegundos

            formatted_message = f"[{timestamp}.{ms:03d}] {message}\n"

            self.log_file.write(formatted_message)
            self.log_file.flush()  # Garante que o log seja escrito imediatamente

        except Exception as e:
            print(f"ERRO CRÍTICO: Falha ao escrever no log: {e}")

    def close(self):
        """
        Fecha o arquivo de log da sessão.
        """
        if self.log_file:
            self.write_log("--- SESSÃO GSE FINALIZADA ---")
            self.log_file.close()
            self.log_file = None
