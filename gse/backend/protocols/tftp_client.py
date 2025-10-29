#!/usr/bin/env python3
"""
Módulo de Protocolo TFTP

Fornece uma classe TFTPClient "pura" para lidar com a
transferência de arquivos TFTP (RFC 1350).

Esta classe é deliberadamente "burra" sobre o ARINC 615A.
Ela apenas sabe como:
1. Ler um arquivo (RRQ)
2. Escrever um arquivo (WRQ)
3. Aguardar um WRQ e receber o arquivo (para LUS)
4. Aguardar um RRQ e servir um arquivo (para BIN/HASH)

Não contém dependências do Qt (PySide6).
"""

import socket
import struct
import time
import hashlib
from enum import Enum
from typing import Optional, Tuple, Callable


# ============ CÓDIGOS TFTP ============
class TFTP_OPCODE(Enum):
    RRQ = 1  # Read request (download)
    WRQ = 2  # Write request (upload)
    DATA = 3  # Pacote de dados
    ACK = 4  # Confirmação
    ERROR = 5  # Erro


class TFTP_ERROR(Enum):
    NOT_DEFINED = 0
    FILE_NOT_FOUND = 1
    ACCESS_VIOLATION = 2
    DISK_FULL = 3
    ILLEGAL_OPERATION = 4
    UNKNOWN_TID = 5
    FILE_EXISTS = 6
    NO_SUCH_USER = 7


# ============ CONSTANTES ============
TFTP_PORT = 69
BLOCK_SIZE = 512
TIMEOUT_SEC = 60
MAX_RETRIES = 5


class TFTPClient:
    """
    Implementa a lógica de cliente e servidor TFTP
    necessária para o fluxo ARINC 615A.
    """

    def __init__(
        self,
        server_ip: str,
        server_port: int = TFTP_PORT,
        timeout: int = TIMEOUT_SEC,
        logger: Callable[[str], None] = None,
    ):
        """
        Inicializa o cliente TFTP.

        :param server_ip: IP do servidor TFTP principal (porta 69)
        :param logger: Uma função (como print ou log.debug) para logar mensagens.
        """
        self.server_ip = server_ip
        self.server_port_69 = server_port  # Porta principal (69)
        self.timeout = timeout
        self.sock = None  # Socket principal, usado para iniciar transferências
        self.server_tid = None  # O Transfer ID (porta efêmera) do servidor

        # Define um logger. Se nenhum for passado, usa print.
        self.logger = logger or (lambda msg: print(msg))

    def log(self, msg: str):
        """Helper para logar mensagens"""
        self.logger(msg)

    def connect(self) -> bool:
        """Cria o socket UDP principal."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(self.timeout)
            self.log(f"[TFTP-OK] Socket UDP principal criado")
            return True
        except Exception as e:
            self.log(f"[TFTP-ERRO] Erro ao criar socket: {e}")
            return False

    def close(self):
        """Fecha o socket principal."""
        if self.sock:
            self.sock.close()
            self.sock = None
            self.log(f"[TFTP-OK] Socket principal fechado")

    # =================================================================
    # MÉTODOS TFTP "PUROS" (Abstrações RFC 1350)
    # =================================================================

    def read_file(self, filename: str, mode: str = "octet") -> bytes:
        """
        Executa um 'Read Request' (RRQ) completo e retorna os dados do arquivo.
        (Usado para o LUI)
        """
        self.log(f"[TFTP] Lendo arquivo (RRQ): {filename}")
        data_buffer = b""
        expected_block = 1
        retry_count = 0
        self.server_tid = None  # Reseta o TID para a nova transferência

        # 1. Envia RRQ para a porta 69
        self._send_rrq(filename, mode, (self.server_ip, self.server_port_69))

        while True:
            try:
                # 2. Recebe DATA (de uma porta efêmera)
                data, addr = self.sock.recvfrom(4 + BLOCK_SIZE)

                # 3. Valida o pacote DATA
                opcode, block, payload = self._parse_data_packet(data)

                if opcode == TFTP_OPCODE.ERROR:
                    err_code, err_msg = self._parse_error_packet(data)
                    raise Exception(f"Erro TFTP {err_code}: {err_msg}")
                if opcode != TFTP_OPCODE.DATA:
                    self.log(
                        f"[TFTP-AVISO] Pacote inesperado (esperava DATA), opcode={opcode}"
                    )
                    continue

                # 4. Define o TID do servidor na primeira resposta
                if self.server_tid is None:
                    self.server_tid = addr[1]
                    self.log(
                        f"[TFTP-OK] Servidor respondeu da porta {addr[0]}:{self.server_tid}"
                    )

                # 5. Verifica o número do bloco
                if block != expected_block:
                    self.log(
                        f"[TFTP-AVISO] Bloco fora de ordem: esperado {expected_block}, recebido {block}"
                    )
                    # Reenvia ACK do último bloco válido
                    self._send_ack(
                        expected_block - 1, (self.server_ip, self.server_tid)
                    )
                    continue

                # 6. Salva dados e envia ACK
                data_buffer += payload
                self._send_ack(block, (self.server_ip, self.server_tid))

                expected_block += 1
                retry_count = 0  # Reseta retries em pacote válido

                # 7. Verifica fim da transferência
                if len(payload) < BLOCK_SIZE:
                    self.log(
                        f"[TFTP-OK] Leitura (RRQ) de {filename} concluída ({len(data_buffer)} bytes)"
                    )
                    return data_buffer

            except socket.timeout:
                retry_count += 1
                if retry_count >= MAX_RETRIES:
                    self.log(
                        f"[TFTP-ERRO] Timeout: Limite de tentativas atingido ao ler {filename}"
                    )
                    raise
                self.log(
                    f"[TFTP-AVISO] Timeout (RRQ), tentativa {retry_count}/{MAX_RETRIES}"
                )
                # Reenvia o RRQ inicial se nunca recebemos o DATA(1)
                if expected_block == 1:
                    self._send_rrq(
                        filename, mode, (self.server_ip, self.server_port_69)
                    )
                continue
            except Exception as e:
                self.log(f"[TFTP-ERRO] Erro em read_file: {e}")
                raise

    def write_file(self, filename: str, data: bytes, mode: str = "octet") -> bool:
        """
        Executa um 'Write Request' (WRQ) completo e envia os dados.
        (Usado para o LUR)
        """
        self.log(f"[TFTP] Escrevendo arquivo (WRQ): {filename}")
        self.server_tid = None  # Reseta o TID

        # 1. Envia WRQ para a porta 69
        self._send_wrq(filename, mode, (self.server_ip, self.server_port_69))

        try:
            # 2. Espera ACK(0) da porta efêmera do servidor
            ack_pkt, addr = self.sock.recvfrom(516)
            opcode, ack_block = self._parse_ack_packet(ack_pkt)

            if opcode == TFTP_OPCODE.ERROR:
                err_code, err_msg = self._parse_error_packet(ack_pkt)
                raise Exception(f"Erro TFTP {err_code}: {err_msg}")
            if opcode != TFTP_OPCODE.ACK or ack_block != 0:
                raise Exception(
                    f"Resposta inválida ao WRQ: opcode={opcode} ack_block={ack_block}"
                )

            # 3. Armazena o TID (porta efêmera) do servidor
            self.server_tid = addr[1]
            destination_addr = (self.server_ip, self.server_tid)
            self.log(
                f"[TFTP-OK] Servidor aceitou WRQ (ACK 0) da porta {addr[0]}:{self.server_tid}"
            )

            # 4. Envia dados em blocos
            block_num = 1
            offset = 0
            while offset < len(data):
                chunk = data[offset : offset + BLOCK_SIZE]

                # 4a. Envia DATA(N)
                self._send_data(block_num, chunk, destination_addr)

                # 4b. Espera ACK(N)
                ack_pkt, _ = self.sock.recvfrom(516)
                opcode, ack_block = self._parse_ack_packet(ack_pkt)

                if opcode != TFTP_OPCODE.ACK or ack_block != block_num:
                    self.log(
                        f"[TFTP-AVISO] ACK inválido. Esperado {block_num}, recebido {ack_block}"
                    )
                    # (Aqui deveria ter lógica de retry, mas simplificamos por enquanto)
                    raise Exception("Falha de ACK no envio de dados")

                # 4c. Avança
                offset += len(chunk)
                block_num += 1

                if len(chunk) < BLOCK_SIZE:
                    break  # Fim da transferência

            self.log(
                f"[TFTP-OK] Escrita (WRQ) de {filename} concluída ({len(data)} bytes)"
            )
            return True

        except socket.timeout:
            self.log(
                f"[TFTP-ERRO] Timeout: Servidor não respondeu ao WRQ de {filename}"
            )
            raise
        except Exception as e:
            self.log(f"[TFTP-ERRO] Erro em write_file: {e}")
            raise

    # =================================================================
    # MÉTODOS DE FLUXO ARINC (Abstrações Específicas)
    # =================================================================

    def receive_wrq_and_data(self) -> bytes:
        """
        Aguarda um WRQ, envia ACK(0), recebe DATA(1), envia ACK(1).
        Retorna o payload (bytes) do DATA(1).
        (Usado para LUS 50% e 100%)
        """
        self.log(f"[TFTP-ARINC] Aguardando WRQ (LUS) no socket principal...")

        # 1. Espera WRQ
        wrq_pkt, wrq_addr = self.sock.recvfrom(516)
        opcode, filename = self._parse_wrq_packet(wrq_pkt)
        if opcode != TFTP_OPCODE.WRQ:
            raise Exception(f"Pacote inesperado (esperava WRQ), opcode={opcode}")

        self.log(
            f"[TFTP-ARINC] WRQ recebido para '{filename}' de {wrq_addr[0]}:{wrq_addr[1]}"
        )

        # 2. Envia ACK(0) de volta para o remetente (porta efêmera do Target)
        self._send_ack(0, wrq_addr)

        # 3. Espera DATA(1)
        data_pkt, data_addr = self.sock.recvfrom(4 + BLOCK_SIZE)
        opcode, block, payload = self._parse_data_packet(data_pkt)

        if opcode != TFTP_OPCODE.DATA or block != 1:
            raise Exception(
                f"Pacote inesperado (esperava DATA 1), opcode={opcode} block={block}"
            )

        self.log(
            f"[TFTP-ARINC] DATA(1) recebido de {data_addr[0]}:{data_addr[1]} ({len(payload)} bytes)"
        )

        # 4. Envia ACK(1) de volta para o remetente
        self._send_ack(1, data_addr)

        return payload

    def serve_file_on_rrq(
        self,
        expected_filename: str,
        file_data: bytes,
        hash_data: bytes,
        progress_callback: Callable[[int], None] = None,
    ) -> bool:
        """
        Aguarda um RRQ, cria um socket efêmero, e serve o arquivo
        (file_data) seguido pelo pacote de hash (hash_data).
        (Usado para o BIN + HASH)
        """
        self.log(f"[TFTP-ARINC] Aguardando RRQ para '{expected_filename}'...")

        # 1. Espera RRQ no socket principal
        rrq_pkt, rrq_addr = self.sock.recvfrom(516)
        opcode, filename = self._parse_rrq_packet(rrq_pkt)

        if opcode != TFTP_OPCODE.RRQ:
            raise Exception(f"Pacote inesperado (esperava RRQ), opcode={opcode}")
        if filename != expected_filename:
            self.log(
                f"[TFTP-ERRO] Target pediu '{filename}', esperávamos '{expected_filename}'"
            )
            raise Exception("Nome de arquivo incorreto solicitado pelo Target")

        self.log(
            f"[TFTP-ARINC] RRQ recebido para '{filename}' de {rrq_addr[0]}:{rrq_addr[1]}"
        )

        # 2. Cria socket de transferência efêmero
        transfer_sock = None
        try:
            transfer_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            transfer_sock.settimeout(self.timeout)
            transfer_sock.bind(("", 0))  # Bind em porta efêmera (0 = OS escolhe)
            transfer_port = transfer_sock.getsockname()[1]
            self.log(
                f"[TFTP-ARINC] Socket de transferência (BIN) criado na porta {transfer_port}"
            )

            # 3. Serve o ARQUIVO (file_data)
            block_num = 1
            offset = 0
            total_bytes = len(file_data)
            self.log(
                f"[TFTP-ARINC] Iniciando envio de {total_bytes} bytes para {rrq_addr}..."
            )

            while offset < total_bytes:
                chunk = file_data[offset : offset + BLOCK_SIZE]

                # Envia DATA(N) e espera ACK(N) com retries
                self._send_data_and_wait_ack(transfer_sock, block_num, chunk, rrq_addr)

                # Reporta progresso (convertido para 0-100)
                if progress_callback:
                    prog_pct = int(100 * (offset / total_bytes))
                    progress_callback(prog_pct)

                offset += len(chunk)
                block_num += 1

            # 3b. Envia pacote 0-byte se o arquivo for múltiplo de 512
            if total_bytes > 0 and total_bytes % BLOCK_SIZE == 0:
                self.log(
                    f"[TFTP-ARINC] Enviando pacote final 0-byte (bloco {block_num})"
                )
                self._send_data_and_wait_ack(transfer_sock, block_num, b"", rrq_addr)
                block_num += 1

            self.log(f"[TFTP-ARINC] Transferência de {filename} concluída.")

            # 4. Serve o HASH (hash_data)
            self.log(f"[TFTP-ARINC] Enviando HASH (bloco {block_num})")
            self._send_data_and_wait_ack(transfer_sock, block_num, hash_data, rrq_addr)
            self.log(f"[TFTP-ARINC] HASH enviado e ACK recebido.")

            return True

        except Exception as e:
            self.log(f"[TFTP-ERRO] Erro em serve_file_on_rrq: {e}")
            raise  # Propaga o erro
        finally:
            if transfer_sock:
                transfer_sock.close()
                self.log(f"[TFTP-ARINC] Socket de transferência (BIN) fechado")

    # =================================================================
    # MÉTODOS HELPER (Pacotes e Lógica Interna)
    # =================================================================

    def _send_data_and_wait_ack(
        self, sock: socket.socket, block: int, data: bytes, addr: Tuple[str, int]
    ):
        """Helper interno para o loop de 'servir arquivo' (etapa 4)"""
        retries = 0
        while retries < MAX_RETRIES:
            # Envia DATA
            self._send_data(block, data, addr, sock)
            try:
                # Aguarda ACK
                ack_pkt, ack_addr = sock.recvfrom(516)
                opcode, ack_block = self._parse_ack_packet(ack_pkt)

                if ack_addr != addr:
                    self.log(f"[TFTP-AVISO] ACK de endereço inesperado {ack_addr}")
                    continue
                if opcode == TFTP_OPCODE.ACK and ack_block == block:
                    return  # Sucesso

                self.log(
                    f"[TFTP-AVISO] ACK inválido. Esperado {block}, recebido {ack_block}"
                )
                retries += 1

            except socket.timeout:
                retries += 1
                self.log(
                    f"[TFTP-AVISO] Timeout ACK (bloco {block}), tentativa {retries}"
                )

        raise Exception(
            f"Falha: ACK não recebido para bloco {block} após {MAX_RETRIES} tentativas"
        )

    def _send_rrq(self, filename: str, mode: str, addr: Tuple[str, int]):
        pkt = struct.pack("!H", TFTP_OPCODE.RRQ.value)
        pkt += filename.encode() + b"\0"
        pkt += mode.encode() + b"\0"
        self.sock.sendto(pkt, addr)
        self.log(f"[TFTP-SEND] RRQ: {filename} para {addr[0]}:{addr[1]}")

    def _send_wrq(self, filename: str, mode: str, addr: Tuple[str, int]):
        pkt = struct.pack("!H", TFTP_OPCODE.WRQ.value)
        pkt += filename.encode() + b"\0"
        pkt += mode.encode() + b"\0"
        self.sock.sendto(pkt, addr)
        self.log(f"[TFTP-SEND] WRQ: {filename} para {addr[0]}:{addr[1]}")

    def _send_ack(self, block: int, addr: Tuple[str, int], sock: socket.socket = None):
        pkt = struct.pack("!HH", TFTP_OPCODE.ACK.value, block)
        (sock or self.sock).sendto(pkt, addr)
        # (Log omitido para não poluir)

    def _send_data(
        self, block: int, data: bytes, addr: Tuple[str, int], sock: socket.socket = None
    ):
        pkt = struct.pack("!HH", TFTP_OPCODE.DATA.value, block) + data
        (sock or self.sock).sendto(pkt, addr)
        # (Log omitido para não poluir)

    def _parse_data_packet(self, data: bytes) -> Tuple[TFTP_OPCODE, int, bytes]:
        if len(data) < 4:
            return (None, 0, b"")
        opcode = struct.unpack("!H", data[0:2])[0]
        block = struct.unpack("!H", data[2:4])[0]
        payload = data[4:]
        return (TFTP_OPCODE(opcode), block, payload)

    def _parse_ack_packet(self, data: bytes) -> Tuple[TFTP_OPCODE, int]:
        if len(data) < 4:
            return (None, 0)
        opcode = struct.unpack("!H", data[0:2])[0]
        block = struct.unpack("!H", data[2:4])[0]
        return (TFTP_OPCODE(opcode), block)

    def _parse_rrq_packet(self, data: bytes) -> Tuple[TFTP_OPCODE, str]:
        if len(data) < 4:
            return (None, "")
        opcode = struct.unpack("!H", data[0:2])[0]
        filename = data[2:].decode("utf-8").split("\0")[0]
        return (TFTP_OPCODE(opcode), filename)

    def _parse_wrq_packet(self, data: bytes) -> Tuple[TFTP_OPCODE, str]:
        return self._parse_rrq_packet(data)  # Formato é idêntico

    def _parse_error_packet(self, data: bytes) -> Tuple[int, str]:
        if len(data) < 5:
            return (0, "Pacote de erro malformado")
        error_code = struct.unpack("!H", data[2:4])[0]
        error_msg = data[4:].decode("utf-8", errors="ignore").rstrip("\0")
        return (error_code, error_msg)
