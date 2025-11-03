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
from enum import Enum
from typing import Tuple, Callable, Optional

# ============================================================================
# REQ: GSE-LLR-87: Constante de Porta TFTP
# Descrição: A constante de porta TFTP (TFTP_PORT) deve ser definida como 69.
# Autor: Fabrício Carneiro Travassos
# Revisor: Julia
# ============================================================================
TFTP_PORT = 69

# ============================================================================
# REQ: GSE-LLR-88: Constante de Tamanho de Bloco
# Descrição: A constante de tamanho de bloco (BLOCK_SIZE) deve ser 512 bytes (padrão RFC 1350).
# Autor: Fabrício Carneiro Travassos
# Revisor: Julia
# ============================================================================
BLOCK_SIZE = 512

# ============================================================================
# REQ: GSE-LLR-89: Constante de Timeout
# Descrição: A constante de timeout (TIMEOUT_SEC) deve possuir valor ≥ 2s para acomodar operações lentas de flash.
# Autor: Fabrício Carneiro Travassos
# Revisor: Julia
# ============================================================================
TIMEOUT_SEC = 2

# ============================================================================
# REQ: GSE-LLR-90: Constante de Retentativas
# Descrição: A constante de retentativas (MAX_RETRIES) deve ser definida com valor ≥ 1.
# Autor: Fabrício Carneiro Travassos
# Revisor: Julia
# ============================================================================
MAX_RETRIES = 1


class TFTP_OPCODE(Enum):
    RRQ = 1
    WRQ = 2
    DATA = 3
    ACK = 4
    ERROR = 5


class TFTP_ERROR(Enum):
    NOT_DEFINED = 0
    FILE_NOT_FOUND = 1
    ACCESS_VIOLATION = 2
    DISK_FULL = 3
    ILLEGAL_OPERATION = 4
    UNKNOWN_TID = 5
    FILE_EXISTS = 6
    NO_SUCH_USER = 7


class TFTPClient:
    """
    Implementa a lógica de cliente e servidor TFTP necessária para o fluxo ARINC 615A.
    """

    # ============================================================================
    # REQ: GSE-LLR-91: Interface de Inicialização (Parâmetros)
    # Descrição: O construtor deve aceitar server_ip (str), server_port (int), timeout (int) e logger (Callable[[str], None]).
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-92: Interface de Inicialização (Valores Padrão)
    # Descrição: O construtor deve empregar TFTP_PORT (GSE-LLR-087) e TIMEOUT_SEC (GSE-LLR-089) como padrões para server_port e timeout.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-93: Interface de Inicialização (Armazenamento)
    # Descrição: Os parâmetros de entrada devem ser armazenados em atributos da instância.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-94: Interface de Inicialização (Logger Padrão)
    # Descrição: Na ausência de logger, deve ser utilizado um logger padrão (ex.: print).
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-95: Provisão para Métricas de Transporte
    # Descrição: A interface deve prever pontos para futura coleta de métricas (bytes, retries, tempos), mesmo que não implementados.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def __init__(
        self,
        server_ip: str,
        server_port: int = TFTP_PORT,
        timeout: int = TIMEOUT_SEC,
        logger: Callable[[str], None] = None,
    ):
        self.server_ip = server_ip
        self.server_port_69 = server_port
        self.timeout = timeout
        self.sock = None
        self.server_tid = None
        self.logger = logger or (lambda msg: print(msg))
        self.authenticated: bool = False

    def log(self, msg: str):
        self.logger(msg)

    # ============================================================================
    # REQ: GSE-LLR-96: Interface de Conexão UDP
    # Descrição: A interface connect() deve criar socket UDP (AF_INET, SOCK_DGRAM), aplicar settimeout(self.timeout), registrar sucesso/erro e retornar True/False conforme resultado.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def connect(self) -> bool:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(self.timeout)
            self.log("[TFTP-OK] Socket UDP principal criado")
            return True
        except Exception as e:
            self.log(f"[TFTP-ERRO] Erro ao criar socket: {e}")
            return False

    # ============================================================================
    # REQ: GSE-LLR-97: Interface de Encerramento de Socket
    # Descrição: A interface close() deve encerrar o socket principal (close, atribuir None) e registrar o encerramento.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None
            self.log("[TFTP-OK] Socket principal fechado")

    # ============================================================================
    # REQ: GSE-LLR-98: Interface de Handshake (Definição)
    # Descrição: A rotina perform_authentication(gse_key, expected_bc_key) deve
    #            realizar o handshake TFTP de 4 etapas (DATA/ACK).
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-99: Lógica de Handshake (Timeout Curto)
    # Descrição: O timeout original deve ser preservado e, durante o handshake,
    #            substituído por timeout curto (ex.: 5 s).
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-100: Lógica de Handshake (Passo 1-2: GSE envia Chave)
    # Descrição: A rotina deve enviar a gse_key em um pacote DATA(1) para a
    #            porta 69 e deve aguardar um ACK(1) do BC, capturando o server_tid.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-101: Lógica de Handshake (Passo 3-4: BC envia Chave)
    # Descrição: A rotina deve aguardar um DATA(1) (contendo a expected_bc_key)
    #            do server_tid do BC e, se a chave for válida, deve responder
    #            com ACK(1) e retornar True.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-102: Lógica de Handshake (Falha)
    # Descrição: Em caso de timeout, pacote TFTP inesperado (opcode/bloco) ou
    #            chave divergente, a rotina deve registrar AUTH-ERRO e retornar False.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-103: Lógica de Handshake (Restauração de Timeout)
    # Descrição: O timeout original deve ser restaurado ao final da execução,
    #            independentemente do resultado do handshake (bloco finally).
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================

    def perform_authentication(self, gse_key: bytes, expected_bc_key: bytes) -> bool:
        """
        Realiza handshake de autenticação com o BC (TFTP 4-etapas).
        Implementa: GSE-LLR-098 a GSE-LLR-103
        """
        self.log("[AUTH] Iniciando handshake de autenticação (DATA/ACK)...")
        if not self.sock:
            self.log("[AUTH-ERRO] Socket não está conectado.")
            return False

        original_timeout = None
        try:
            # REQ: GSE-LLR-099
            original_timeout = self.sock.gettimeout()
            self.sock.settimeout(5.0)  # Timeout curto para handshake

            self.server_tid = None  # Reseta TID

            # --- PASSO 1: Enviar chave GSE para o BC ---
            # REQ: GSE-LLR-100 (Parte 1)
            self.log(f"[AUTH] Enviando chave GSE (DATA 1) para porta {TFTP_PORT}...")
            pkt = struct.pack("!HH", TFTP_OPCODE.DATA.value, 1) + gse_key
            self.sock.sendto(pkt, (self.server_ip, TFTP_PORT))
            self.log("[✓] DATA(1) com chave GSE enviado")

            # --- PASSO 2: Aguardar ACK(1) do BC ---
            # REQ: GSE-LLR-100 (Parte 2)
            self.log("[AUTH] Aguardando ACK(1) do BC...")
            # Usamos a nova helper function (GSE-LLR-133)
            ack_block = self.recv_ack_packet()
            if ack_block != 1:
                self.log(f"[✗] ACK(1) não recebido, recebido Bloco={ack_block}")
                return False  # REQ: GSE-LLR-102

            self.log("[✓] BC aceitou nossa chave - ACK(1) recebido")

            # --- PASSO 3: Aguardar chave do BC (DATA 1) ---
            # REQ: GSE-LLR-101 (Parte 1)
            self.log("[AUTH] Aguardando chave do BC (DATA 1)...")
            # Usamos a nova helper function (GSE-LLR-137)
            result = self.recv_data_packet()
            if not result:
                self.log("[✗] Chave do BC não recebida (timeout ou erro)")
                return False  # REQ: GSE-LLR-102

            block, bc_key = result
            if bc_key != expected_bc_key:
                self.log("[✗] Chave do BC inválida")
                self.log(
                    f"[AUTH]   Recebido: {bc_key.hex() if isinstance(bc_key, bytes) else bc_key}"
                )
                self.log(f"[AUTH]   Esperado: {expected_bc_key.hex()}")
                return False  # REQ: GSE-LLR-102

            self.log("[✓] Chave do BC válida")

            # --- PASSO 4: Envia ACK confirmando a chave ---
            # REQ: GSE-LLR-101 (Parte 2)
            # Usamos a nova helper function (GSE-LLR-141)
            if not self.send_ack(block):
                self.log("[✗] Erro ao enviar ACK para chave do BC")
                return False  # REQ: GSE-LLR-102

            self.authenticated = True
            self.log("[✓] Handshake de autenticação concluído com sucesso!\n")
            return True

        except Exception as e:
            # REQ: GSE-LLR-102 (parcial)
            self.log(f"[✗] Erro durante autenticação: {e}")
            return False
        finally:
            # REQ: GSE-LLR-103
            if original_timeout is not None:
                self.sock.settimeout(original_timeout)
                self.log(
                    f"[AUTH] Timeout do socket restaurado para {original_timeout}s."
                )

    # ============================================================================
    # INÍCIO - NOVOS HELPERS DE AUTENTICAÇÃO
    # ============================================================================

    # ============================================================================
    # REQ: GSE-LLR-133: Interface (Helper Auth) Receber ACK
    # Descrição: A rotina recv_ack_packet() deve aguardar um pacote no socket,
    #            validá-lo (GSE-LLR-128), tratar ERRO (GSE-LLR-131) lançando
    #            exceção, e capturar o server_tid na primeira resposta.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def recv_ack_packet(self) -> int:
        if not self.sock:
            raise RuntimeError("Socket não inicializado (recv_ack_packet).")

        pkt, addr = self.sock.recvfrom(516)
        opcode, block = self._parse_ack_packet(pkt)  # Usa GSE-LLR-128

        if opcode == TFTP_OPCODE.ERROR:  # Usa GSE-LLR-131
            err_code, err_msg = self._parse_error_packet(pkt)
            raise Exception(f"Erro TFTP {err_code}: {err_msg}")

        if opcode != TFTP_OPCODE.ACK:
            raise Exception(f"Pacote inesperado (esperava ACK), opcode={opcode}")

        if self.server_tid is None:
            self.server_tid = addr[1]
            self.log(f"[AUTH] TID do Servidor capturado: {self.server_tid}")

        return block

    # ============================================================================
    # REQ: GSE-LLR-134: Interface (Helper Auth) Receber DATA
    # Descrição: A rotina recv_data_packet() deve aguardar um pacote no socket,
    #            validá-lo (GSE-LLR-127), tratar ERRO (GSE-LLR-131) lançando
    #            exceção, e capturar o server_tid na primeira resposta.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def recv_data_packet(self) -> Optional[Tuple[int, bytes]]:
        if not self.sock:
            raise RuntimeError("Socket não inicializado (recv_data_packet).")

        pkt, addr = self.sock.recvfrom(4 + BLOCK_SIZE)
        opcode, block, payload = self._parse_data_packet(pkt)  # Usa GSE-LLR-127

        if opcode == TFTP_OPCODE.ERROR:  # Usa GSE-LLR-131
            err_code, err_msg = self._parse_error_packet(pkt)
            raise Exception(f"Erro TFTP {err_code}: {err_msg}")

        if opcode != TFTP_OPCODE.DATA:
            self.log(f"[AUTH-AVISO] Pacote inesperado durante auth (opcode={opcode})")
            return None

        if self.server_tid is None:
            self.server_tid = addr[1]
            self.log(f"[AUTH] TID do Servidor capturado: {self.server_tid}")

        return (block, payload)

    # ============================================================================
    # REQ: GSE-LLR-135: Interface (Helper Auth) Enviar ACK
    # Descrição: A rotina send_ack(block) deve enviar um pacote ACK (GSE-LLR-125)
    #            para o server_tid conhecido (ou porta 69 se TID for None)
    #            e retornar True.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def send_ack(self, block: int) -> bool:
        if not self.sock:
            raise RuntimeError("Socket não inicializado (send_ack).")

        # Envia ACK para o TID conhecido, ou para a porta 69 se o TID ainda não foi pego
        addr = (self.server_ip, self.server_tid or self.server_port_69)
        self._send_ack(block, addr)  # Usa GSE-LLR-125
        return True

    # ============================================================================
    # FIM - NOVOS HELPERS DE AUTENTICAÇÃO
    # ============================================================================

    # ============================================================================
    # REQ: GSE-LLR-104: Interface de Leitura de Arquivo (RRQ)
    # Descrição: A rotina read_file() deve efetuar leitura de arquivo via RRQ no modo octet (binário).
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-105: Lógica RRQ (Envio)
    # Descrição: O pedido RRQ deve ser enviado para a porta 69 do servidor TFTP.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-106: Lógica RRQ (Proteção de TID)
    # Descrição: O identificador de transferência do servidor (server_tid) deve ser fixado no primeiro DATA recebido e TIDs inesperados devem ser ignorados.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-107: Lógica RRQ (Sequência de Blocos)
    # Descrição: Cada pacote DATA recebido deve possuir número de bloco igual ao esperado (expected_block).
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-108: Lógica RRQ (Tratamento Fora de Ordem)
    # Descrição: Em ocorrência de bloco fora de ordem, deve ser reenviado ACK do bloco anterior ao esperado.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-109: Lógica RRQ (Timeout e Retentativa)
    # Descrição: Em caso de timeout, novas tentativas devem ser realizadas até MAX_RETRIES, reenviando RRQ quando o bloco esperado for o primeiro.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-110: Lógica RRQ (Acúmulo de Dados)
    # Descrição: Os payloads recebidos devem ser concatenados em buffer de dados até a conclusão da transferência.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-111: Lógica RRQ (Condição de Término)
    # Descrição: A transferência deve ser considerada concluída quando o tamanho do payload recebido for inferior a BLOCK_SIZE.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-112: Lógica RRQ (Tratamento de Erro)
    # Descrição: Ao receber pacote ERROR, uma exceção padronizada com código e mensagem TFTP deve ser lançada.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-113: Modo de Transferência (Octet)
    # Descrição: As rotinas read_file e write_file devem utilizar, por padrão, o modo "octet" (binário).
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def read_file(self, filename: str, mode: str = "octet") -> bytes:
        self.log(f"[TFTP] Lendo arquivo (RRQ): {filename}")
        data_buffer = b""
        expected_block = 1
        retry_count = 0
        self.server_tid = None

        self._send_rrq(filename, mode, (self.server_ip, self.server_port_69))

        while True:
            try:
                data, addr = self.sock.recvfrom(4 + BLOCK_SIZE)
                opcode, block, payload = self._parse_data_packet(data)

                if opcode == TFTP_OPCODE.ERROR:
                    err_code, err_msg = self._parse_error_packet(data)
                    raise Exception(f"Erro TFTP {err_code}: {err_msg}")
                if opcode != TFTP_OPCODE.DATA:
                    self.log(f"[TFTP-AVISO] Pacote inesperado (opcode={opcode})")
                    continue

                if self.server_tid is None:
                    self.server_tid = addr[1]
                    # self.log(
                    #     f"[TFTP-OK] Servidor respondeu da porta {addr[0]}:{self.server_tid}"
                    # )
                    self.log(f"[TFTP-OK] Servidor respondeu da porta")
                if addr[1] != self.server_tid:
                    self.log(f"[TFTP-AVISO] DATA de TID inesperado {addr}")
                    continue

                if block != expected_block:
                    self.log(
                        f"[TFTP-AVISO] Bloco fora de ordem: esperado {expected_block}, recebido {block}"
                    )
                    self._send_ack(
                        expected_block - 1, (self.server_ip, self.server_tid)
                    )
                    continue

                data_buffer += payload
                self._send_ack(block, (self.server_ip, self.server_tid))

                expected_block += 1
                retry_count = 0

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
                if expected_block == 1:
                    self._send_rrq(
                        filename, mode, (self.server_ip, self.server_port_69)
                    )
                continue
            except Exception as e:
                self.log(f"[TFTP-ERRO] Erro em read_file: {e}")
                raise

    # ============================================================================
    # REQ: GSE-LLR-114: Interface de Escrita de Arquivo (WRQ)
    # Descrição: A rotina write_file() deve transmitir arquivo via WRQ no modo octet (binário).
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-115: Lógica WRQ (Envio e ACK 0)
    # Descrição: O pedido WRQ deve ser encaminhado à porta 69 e a captura do server_tid deve ocorrer após o recebimento de ACK(0).
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-116: Lógica WRQ (Envio de Dados em Blocos)
    # Descrição: Os dados devem ser enviados em chunks de tamanho BLOCK_SIZE como DATA(N), aguardando ACK(N) para cada bloco; concluir ao enviar chunk com tamanho inferior a BLOCK_SIZE.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def write_file(self, filename: str, data: bytes, mode: str = "octet") -> bool:
        self.log(f"[TFTP] Escrevendo arquivo (WRQ): {filename}")
        self.server_tid = None

        self._send_wrq(filename, mode, (self.server_ip, self.server_port_69))

        try:
            ack_pkt, addr = self.sock.recvfrom(516)
            opcode, ack_block = self._parse_ack_packet(ack_pkt)

            if opcode == TFTP_OPCODE.ERROR:
                err_code, err_msg = self._parse_error_packet(ack_pkt)
                raise Exception(f"Erro TFTP {err_code}: {err_msg}")
            if opcode != TFTP_OPCODE.ACK or ack_block != 0:
                raise Exception(
                    f"Resposta inválida ao WRQ: opcode={opcode} ack_block={ack_block}"
                )

            self.server_tid = addr[1]
            destination_addr = (self.server_ip, self.server_tid)
            # self.log(
            #     f"[TFTP-OK] Servidor aceitou WRQ (ACK 0) da porta {addr[0]}:{self.server_tid}"
            # )
            self.log(f"[TFTP-OK] Servidor aceitou o write request")

            block_num = 1
            offset = 0
            total = len(data)
            while offset < total:
                chunk = data[offset : offset + BLOCK_SIZE]
                self._send_data(block_num, chunk, destination_addr)

                ack_pkt, _ = self.sock.recvfrom(516)
                op2, ack_block = self._parse_ack_packet(ack_pkt)

                if op2 == TFTP_OPCODE.ERROR:
                    err_code, err_msg = self._parse_error_packet(ack_pkt)
                    raise Exception(f"Erro TFTP {err_code}: {err_msg}")
                if op2 != TFTP_OPCODE.ACK or ack_block != block_num:
                    self.log(
                        f"[TFTP-AVISO] ACK inválido. Esperado {block_num}, recebido {ack_block}"
                    )
                    raise Exception("Falha de ACK no envio de dados")

                offset += len(chunk)
                block_num += 1
                if len(chunk) < BLOCK_SIZE:
                    break

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

    # ============================================================================
    # REQ: GSE-LLR-117: Interface de Recepção (WRQ + DATA 1)
    # Descrição: A rotina receive_wrq_and_data() deve aguardar WRQ no socket principal, responder com ACK(0), aguardar DATA(1), enviar ACK(1) e retornar o payload do DATA(1).
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def receive_wrq_and_data(self) -> bytes:
        self.log("[TFTP-ARINC] Aguardando WRQ (LUS) no socket principal...")

        wrq_pkt, wrq_addr = self.sock.recvfrom(516)
        opcode, filename = self._parse_wrq_packet(wrq_pkt)
        if opcode != TFTP_OPCODE.WRQ:
            raise Exception(f"Pacote inesperado (esperava WRQ), opcode={opcode}")

        self.log(f"[TFTP-ARINC] WRQ para '{filename}' do módulo.")
        self._send_ack(0, wrq_addr)

        data_pkt, data_addr = self.sock.recvfrom(4 + BLOCK_SIZE)
        opcode, block, payload = self._parse_data_packet(data_pkt)

        if opcode != TFTP_OPCODE.DATA or block != 1:
            raise Exception(
                f"Pacote inesperado (esperava DATA 1), opcode={opcode} block={block}"
            )

        # self.log(
        #     f"[TFTP-ARINC] DATA(1) de {data_addr[0]}:{data_addr[1]} ({len(payload)} bytes)"
        # )
        self._send_ack(1, data_addr)
        return payload

    # ============================================================================
    # REQ: GSE-LLR-118: Interface de Servidor de Arquivo (RRQ)
    # Descrição: A rotina serve_file_on_rrq() deve aguardar RRQ esperado, criar socket efêmero, enviar o arquivo em blocos com espera de ACK, enviar pacote final de 0 bytes quando total % BLOCK_SIZE == 0, enviar o HASH em seguida e encerrar o socket de transferência.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-119: Callback de Progresso (Servidor)
    # Descrição: Um progress_callback(int) opcional deve ser aceito e invocado a cada bloco confirmado, reportando int(0–100) de progresso.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-122: Enviar HASH como Próximo DATA
    # Descrição: Após concluir o envio do arquivo, o conteúdo de hash_data deve ser transmitido como próximo DATA, com espera do ACK correspondente.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def serve_file_on_rrq(
        self,
        expected_filename: str,
        file_data: bytes,
        hash_data: bytes,
        progress_callback: Callable[[int], None] = None,
    ) -> bool:
        self.log(f"[TFTP-ARINC] Aguardando RRQ para '{expected_filename}'...")

        rrq_pkt, rrq_addr = self.sock.recvfrom(516)
        opcode, filename = self._parse_rrq_packet(rrq_pkt)

        if opcode != TFTP_OPCODE.RRQ:
            raise Exception(f"Pacote inesperado (esperava RRQ), opcode={opcode}")
        if filename != expected_filename:
            self.log(
                f"[TFTP-ERRO] Target pediu '{filename}', esperávamos '{expected_filename}'"
            )
            raise Exception("Nome de arquivo incorreto solicitado pelo Target")

        # self.log(f"[TFTP-ARINC] RRQ para '{filename}' de {rrq_addr[0]}:{rrq_addr[1]}")
        self.log(f"[TFTP-ARINC] RRQ para '{filename}'")

        transfer_sock = None
        try:
            transfer_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            transfer_sock.settimeout(self.timeout)
            transfer_sock.bind(("", 0))
            transfer_port = transfer_sock.getsockname()[1]
            # self.log(
            #     f"[TFTP-ARINC] Socket de transferência (BIN) na porta {transfer_port}"
            # )
            self.log(f"[TFTP-ARINC] Socket de transferência (BIN)")

            block_num = 1
            offset = 0
            total_bytes = len(file_data)
            self.log(f"[TFTP-ARINC] Enviando {total_bytes} bytes para o módulo...")

            while offset < total_bytes:
                chunk = file_data[offset : offset + BLOCK_SIZE]
                self._send_data_and_wait_ack(transfer_sock, block_num, chunk, rrq_addr)

                if progress_callback and total_bytes > 0:
                    prog_pct = int(100 * ((offset + len(chunk)) / total_bytes))
                    prog_pct = min(max(prog_pct, 0), 100)
                    progress_callback(prog_pct)

                offset += len(chunk)
                block_num += 1

            if total_bytes > 0 and total_bytes % BLOCK_SIZE == 0:
                self.log(
                    f"[TFTP-ARINC] Enviando pacote final 0-byte (bloco {block_num})"
                )
                self._send_data_and_wait_ack(transfer_sock, block_num, b"", rrq_addr)
                block_num += 1

            self.log(f"[TFTP-ARINC] Transferência de {filename} concluída.")
            self.log(f"[TFTP-ARINC] Enviando HASH (bloco {block_num})")
            self._send_data_and_wait_ack(transfer_sock, block_num, hash_data, rrq_addr)
            self.log("[TFTP-ARINC] HASH enviado e ACK recebido.")
            return True

        except Exception as e:
            self.log(f"[TFTP-ERRO] Erro em serve_file_on_rrq: {e}")
            raise
        finally:
            if transfer_sock:
                transfer_sock.close()
                self.log("[TFTP-ARINC] Socket de transferência (BIN) fechado")

    # ============================================================================
    # REQ: GSE-LLR-121: Interface Interna (Envio com Retentativa)
    # Descrição: O método _send_data_and_wait_ack() deve enviar DATA(block) e aguardar ACK(block) do endereço correto; em timeout/ACK inválido, novas tentativas devem ocorrer até MAX_RETRIES, com exceção ao exceder o limite.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-120: Política de Backoff (Retransmissões)
    # Descrição: Uma política de backoff progressivo (exponencial simples com teto) deve ser aplicada entre retransmissões, implementada no tratamento de timeout.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def _send_data_and_wait_ack(
        self, sock: socket.socket, block: int, data: bytes, addr: Tuple[str, int]
    ):
        retries = 0
        while retries < MAX_RETRIES:
            self._send_data(block, data, addr, sock)
            try:
                ack_pkt, ack_addr = sock.recvfrom(516)
                opcode, ack_block = self._parse_ack_packet(ack_pkt)

                if ack_addr != addr:
                    self.log(f"[TFTP-AVISO] ACK de endereço inesperado {ack_addr}")
                    continue

                if opcode == TFTP_OPCODE.ERROR:
                    err_code, err_msg = self._parse_error_packet(ack_pkt)
                    raise Exception(f"Erro TFTP {err_code}: {err_msg}")

                if opcode == TFTP_OPCODE.ACK and ack_block == block:
                    return

                self.log(
                    f"[TFTP-AVISO] ACK inválido. Esperado {block}, recebido {ack_block}"
                )
                retries += 1

            except socket.timeout:
                retries += 1
                self.log(
                    f"[TFTP-AVISO] Timeout ACK (bloco {block}), tentativa {retries}"
                )
                # Backoff exponencial simples (base 0.25 s, teto 2.0 s)
                delay = min(2.0, 0.25 * (2 ** (retries - 1)))
                time.sleep(delay)

        raise Exception(
            f"Falha: ACK não recebido para bloco {block} após {MAX_RETRIES} tentativas"
        )

    # ============================================================================
    # REQ: GSE-LLR-123: Interface Interna (Construção de RRQ)
    # Descrição: O método _send_rrq() deve construir e enviar RRQ no formato: (Opcode 1, big-endian) + filename(ascii)+NUL + mode(ascii)+NUL, aplicando sanitização de filename previamente (GSE-LLR-131).
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    # REQ: GSE-LLR-131: Sanitização de Filename (Aplicação)
    # Descrição: As rotinas _send_rrq/_send_wrq devem aplicar sanitização de filename antes do envio.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def _send_rrq(self, filename: str, mode: str, addr: Tuple[str, int]):
        filename = self._sanitize_filename(filename)
        pkt = struct.pack("!H", TFTP_OPCODE.RRQ.value)
        pkt += filename.encode() + b"\0"
        pkt += mode.encode() + b"\0"
        self.sock.sendto(pkt, addr)
        self.log(f"[TFTP-SEND] RRQ: {filename} para {addr[0]}:{addr[1]}")

    # ============================================================================
    # REQ: GSE-LLR-124: Interface Interna (Construção de WRQ)
    # Descrição: O método _send_wrq() deve construir e enviar WRQ no formato: (Opcode 2, big-endian) + filename(ascii)+NUL + mode(ascii)+NUL, aplicando sanitização de filename previamente (GSE-LLR-131).
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def _send_wrq(self, filename: str, mode: str, addr: Tuple[str, int]):
        filename = self._sanitize_filename(filename)
        pkt = struct.pack("!H", TFTP_OPCODE.WRQ.value)
        pkt += filename.encode() + b"\0"
        pkt += mode.encode() + b"\0"
        self.sock.sendto(pkt, addr)
        self.log(f"[TFTP-SEND] WRQ: {filename} para {addr[0]}:{addr[1]}")

    # ============================================================================
    # REQ: GSE-LLR-125: Interface Interna (Construção de ACK)
    # Descrição: A rotina _send_ack() deve construir e enviar ACK no formato: (Opcode 4, big-endian) + (block, 16-bit big-endian).
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def _send_ack(self, block: int, addr: Tuple[str, int], sock: socket.socket = None):
        pkt = struct.pack("!HH", TFTP_OPCODE.ACK.value, block)
        (sock or self.sock).sendto(pkt, addr)

    # ============================================================================
    # REQ: GSE-LLR-126: Interface Interna (Construção de DATA)
    # Descrição: A rotina _send_data() deve construir e enviar DATA no formato: (Opcode 3, big-endian) + (block, 16-bit big-endian) + (data), impondo len(data) ≤ BLOCK_SIZE e lançando erro quando houver violação.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def _send_data(
        self, block: int, data: bytes, addr: Tuple[str, int], sock: socket.socket = None
    ):
        if len(data) > BLOCK_SIZE:
            raise ValueError("DATA maior que BLOCK_SIZE")
        pkt = struct.pack("!HH", TFTP_OPCODE.DATA.value, block) + data
        (sock or self.sock).sendto(pkt, addr)

    # ============================================================================
    # REQ: GSE-LLR-127: Interface Interna (Análise de DATA)
    # Descrição: A rotina _parse_data_packet() deve retornar (None, 0, b"") quando o tamanho do pacote for inferior a 4 bytes; caso contrário, deve retornar (Opcode, block, payload).
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def _parse_data_packet(self, data: bytes) -> Tuple[TFTP_OPCODE, int, bytes]:
        if len(data) < 4:
            return (None, 0, b"")
        opcode = struct.unpack("!H", data[0:2])[0]
        block = struct.unpack("!H", data[2:4])[0]
        payload = data[4:]
        return (TFTP_OPCODE(opcode), block, payload)

    # ============================================================================
    # REQ: GSE-LLR-128: Interface Interna (Análise de ACK)
    # Descrição: A rotina _parse_ack_packet() deve retornar (None, 0) quando o pacote possuir menos de 4 bytes; caso contrário, deve retornar (Opcode, block).
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def _parse_ack_packet(self, data: bytes) -> Tuple[TFTP_OPCODE, int]:
        if len(data) < 4:
            return (None, 0)
        opcode = struct.unpack("!H", data[0:2])[0]
        block = struct.unpack("!H", data[2:4])[0]
        return (TFTP_OPCODE(opcode), block)

    # ============================================================================
    # REQ: GSE-LLR-129: Interface Interna (Análise de RRQ/WRQ)
    # Descrição: A rotina _parse_rrq_packet() deve retornar (Opcode, filename), ignorando opções TFTP (modo, blksize etc.) após o primeiro NUL.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def _parse_rrq_packet(self, data: bytes) -> Tuple[TFTP_OPCODE, str]:
        if len(data) < 4:
            return (None, "")
        opcode = struct.unpack("!H", data[0:2])[0]
        filename = data[2:].decode("utf-8", errors="ignore").split("\0")[0]
        return (TFTP_OPCODE(opcode), filename)

    def _parse_wrq_packet(self, data: bytes) -> Tuple[TFTP_OPCODE, str]:
        return self._parse_rrq_packet(data)

    # ============================================================================
    # REQ: GSE-LLR-130: Interface Interna (Análise de ERROR)
    # Descrição: A rotina _parse_error_packet() deve retornar (0, "Pacote de erro malformado") quando o pacote possuir menos de 5 bytes; caso contrário, deve retornar (error_code, error_msg) com mensagem decodificada e sem NUL final.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    def _parse_error_packet(self, data: bytes) -> Tuple[int, str]:
        if len(data) < 5:
            return (0, "Pacote de erro malformado")
        error_code = struct.unpack("!H", data[2:4])[0]
        error_msg = data[4:].decode("utf-8", errors="ignore").rstrip("\0")
        return (error_code, error_msg)

    # ============================================================================
    # REQ: GSE-LLR-132: Sanitização de Filename (Implementação)
    # Descrição: O método _sanitize_filename(name) deve remover diretórios, proibir '..' e filtrar para ASCII seguro [a-zA-Z0-9._-@+],
    # lançando ValueError quando o nome resultar vazio/inválido após sanitização.
    # Autor: Fabrício Carneiro Travassos
    # Revisor: Julia
    # ============================================================================
    @staticmethod
    def _sanitize_filename(name: str) -> str:
        if not isinstance(name, str) or not name:
            raise ValueError("Filename inválido")

        safe = name.replace("\\", "/").split("/")[-1]
        if ".." in safe:
            raise ValueError("Filename inválido: contém '..'")

        allowed = set("._-@+")
        for i in range(48, 58):
            allowed.add(chr(i))
        for i in range(65, 91):
            allowed.add(chr(i))
        for i in range(97, 123):
            allowed.add(chr(i))

        safe = "".join(ch if ch in allowed else "_" for ch in safe)
        if not safe:
            raise ValueError("Filename vazio após sanitização")
        return safe
