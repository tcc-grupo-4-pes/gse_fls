#!/usr/bin/env python3
"""
\file gse_logger.py
\brief Módulo responsável pelo gerenciamento de logs de sessão do GSE.

\details
Este módulo fornece a classe \c GseLogger, responsável por criar, escrever
e gerenciar arquivos de log gerados durante a operação do GSE.  
Cada instância da classe cria automaticamente um arquivo de log exclusivo,
com timestamp no nome, dentro do diretório ``logs/``.

O objetivo é fornecer um mecanismo simples e consistente para registrar
eventos, mensagens de depuração e rastreamento de fluxo durante a execução
da aplicação.
"""

import datetime
from typing import TextIO
from pathlib import Path


class GseLogger:
    """
    \class GseLogger
    \brief Gerencia um único arquivo de log para uma sessão do GSE.

    \details
    A classe cria automaticamente o diretório ``logs`` (se ainda não existir)
    e gera um arquivo de log com um nome baseado em data e hora.  
    Todos os métodos são seguros quanto a erros e garantem que o GSE não
    interrompa sua execução caso o log não possa ser criado.
    """

    LOG_DIR = Path(__file__).resolve().parents[2] / "logs"

    def __init__(self):
        """
        \brief Construtor do logger.

        \details
        Inicializa o logger, cria o diretório de logs (se necessário)
        e abre o arquivo de log da sessão.  
        O caminho completo do arquivo criado pode ser recuperado por
        \ref get_log_path().
        """
        self.log_file: TextIO | None = None
        self.log_path: str = ""
        self._init_log_file()

    def _init_log_file(self):
        """
        \brief Inicializa o arquivo de log.

        \details
        Cria o diretório ``logs`` (caso não exista) e abre um arquivo
        cujo nome inclui timestamp no formato ``YYYY-MM-DD_HH-MM-SS``.
        O arquivo é sempre aberto no modo append (``a``), permitindo
        continuar sessões interrompidas ou acrescentar novas entradas.
        """
        try:
            log_dir_path = self.LOG_DIR
            log_dir_path.mkdir(parents=True, exist_ok=True)

            now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"GSE_Sessao_{now_str}.txt"
            log_path = log_dir_path / filename

            self.log_path = str(log_path)
            self.log_file = log_path.open("a", encoding="utf-8")

            print(f"Sessão de log iniciada. Arquivo: {self.log_path}")

        except Exception as e:
            print(f"ERRO CRÍTICO: Falha ao inicializar logger de arquivo: {e}")
            self.log_file = None

    def get_log_path(self) -> str:
        """
        \brief Retorna o caminho do arquivo de log atual.

        \return Caminho completo do arquivo de log em uso.
        """
        return self.log_path

    def write_log(self, message: str):
        """
        \brief Escreve uma mensagem formatada no arquivo de log.

        \details
        Cada linha é automaticamente prefixada com timestamp incluindo
        horas, minutos, segundos e milissegundos no formato:

        ``[HH:MM:SS.mmm] Mensagem...``

        \param message Texto da mensagem a ser registrada.
        """
        if not self.log_file:
            print(f"LOG (sem arquivo): {message}")
            return

        try:
            now = datetime.datetime.now()
            timestamp = now.strftime("%H:%M:%S")
            ms = now.microsecond // 1000

            formatted_message = f"[{timestamp}.{ms:03d}] {message}\n"

            self.log_file.write(formatted_message)
            self.log_file.flush()

        except Exception as e:
            print(f"ERRO CRÍTICO: Falha ao escrever no log: {e}")

    def close(self):
        """
        \brief Fecha o arquivo de log da sessão.

        \details
        Antes de encerrar, registra a mensagem de término:

        ``--- SESSÃO GSE FINALIZADA ---``

        Após o fechamento, o atributo \c log_file passa a ser ``None``.
        """
        if self.log_file:
            self.write_log("--- SESSÃO GSE FINALIZADA ---")
            self.log_file.close()
            self.log_file = None
