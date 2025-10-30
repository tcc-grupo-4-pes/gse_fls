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

# ============================================================================
# REQ: GSE-LLR-400 – Independência de UI/Qt e foco em RFC 1350
# Tipo: Não Funcional
# Descrição: Este módulo não deve importar PySide/Qt nem conter regras ARINC.
# Critérios de Aceitação:
#  - Apenas stdlib + tipagem/enum; regras ARINC ficam em camadas superiores.
# Autor: (preencher) | Revisor: (preencher)
# ============================================================================
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
# ============================================================================
# REQ: GSE-LLR-401 – Parâmetros padrão de transporte
# Tipo: Requisito Funcional
# Descrição: Definir porta padrão (69), BLOCK_SIZE=512, timeout e tentativas.
# Critérios de Aceitação:
#  - TFTP_PORT == 69; BLOCK_SIZE == 512; TIMEOUT_SEC >= 30; MAX_RETRIES >= 3.
# Autor: (preencher) | Revisor: (preencher)
# ============================================================================
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
        # ============================================================================
        # REQ: GSE-LLR-402 – Injeção de parâmetros de transporte
        # Tipo: Funcional
        # Descrição: Permitir configurar IP, porta 69 e timeout no construtor.
        # Critérios de Aceitação:
        #  - Armazenar server_ip, server_port_69, timeout.
        #  - logger default imprime em stdout.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
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
        # ============================================================================
        # REQ: GSE-LLR-403 – Criação e configuração de socket UDP
        # Tipo: Funcional
        # Descrição: Criar socket UDP, aplicar timeout e registrar sucesso/erro.
        # Critérios de Aceitação:
        #  - settimeout(self.timeout) aplicado.
        #  - Em erro, logar [TFTP-ERRO] e retornar False.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
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
        # ============================================================================
        # REQ: GSE-LLR-404 – Encerramento limpo do socket
        # Tipo: Não Funcional
        # Descrição: Fechar o socket principal se existir e logar ação.
        # Critérios de Aceitação:
        #  - Após fechar, self.sock = None.
        #  - Logar "[TFTP-OK] Socket principal fechado".
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        if self.sock:
            self.sock.close()
            self.sock = None
            self.log(f"[TFTP-OK] Socket principal fechado")

    # =================================================================
    # [NOVO] MÉTODO DE VERIFICAÇÃO DE CHAVE (Handshake)
    # =================================================================

    def verify_static_key(
        self, gse_key: bytes, expected_bc_key: bytes, auth_port: int = 69
    ) -> bool:
        """
        Envia uma chave estática (ping) e espera a chave do BC de volta.
        Usa um timeout curto dedicado.
        """
        # ============================================================================
        # REQ: GSE-LLR-405 – Handshake simples por troca de chaves
        # Tipo: Funcional
        # Descrição: Enviar gse_key, aguardar resposta e comparar com expected_bc_key.
        # Critérios de Aceitação:
        #  - Timeout reduzido (≈5s) apenas durante o handshake, depois restaurar.
        #  - Em sucesso, retornar True; em falha/timeout/exceção, retornar False.
        #  - Logar [AUTH-*] eventos e restaurar timeout original.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        self.log("[AUTH] Iniciando verificação de chave estática...")
        if not self.sock:
            self.log("[AUTH-ERRO] Socket não está conectado.")
            return False

        original_timeout = None
        try:
            # 1. Define um timeout curto para esta operação
            original_timeout = self.sock.gettimeout()
            self.sock.settimeout(5.0)  # 5 segundos para o handshake

            # 2. Define o endereço de destino (Porta 69 do BC)
            auth_addr = (self.server_ip, auth_port)

            # 3. Envia a chave do GSE
            self.sock.sendto(gse_key, auth_addr)
            self.log(f"[AUTH-SEND] Chave GSE enviada para {auth_addr}")

            # 4. Aguarda a resposta do BC
            data, addr = self.sock.recvfrom(1024)
            self.log(f"[AUTH-RECV] Resposta recebida de {addr}")

            # 5. Compara a resposta com a chave esperada
            if data == expected_bc_key:
                self.log("[AUTH-OK] Chave BC recebida é válida. Handshake OK.")
                return True
            else:
                self.log(f"[AUTH-ERRO] Chave BC inválida!")
                self.log(f"   Esperado: {expected_bc_key}")
                self.log(f"   Recebido: {data}")
                return False

        except socket.timeout:
            self.log(
                "[AUTH-ERRO] Timeout. O alvo (BC) não respondeu à verificação de chave."
            )
            return False
        except Exception as e:
            self.log(f"[AUTH-ERRO] Erro inesperado no handshake: {e}")
            return False
        finally:
            # 6. Restaura o timeout original (MUITO IMPORTANTE)
            if original_timeout is not None:
                self.sock.settimeout(original_timeout)
                self.log(
                    f"[AUTH] Timeout do socket restaurado para {original_timeout}s."
                )

    # =================================================================
    # MÉTODOS TFTP "PUROS" (Abstrações RFC 1350)
    # =================================================================

    def read_file(self, filename: str, mode: str = "octet") -> bytes:
        """
        Executa um 'Read Request' (RRQ) completo e retorna os dados do arquivo.
        (Usado para o LUI)
        """
        # ============================================================================
        # REQ: GSE-LLR-406 – Fluxo RRQ com TID e ACKs
        # Tipo: Funcional
        # Descrição: Enviar RRQ, receber DATA(1..N) do TID do servidor, ACK a cada bloco.
        # Critérios de Aceitação:
        #  - Definir server_tid a partir do primeiro DATA recebido.
        #  - Validar bloco esperado; se fora de ordem, reenviar ACK do último válido.
        #  - Finalizar quando payload < BLOCK_SIZE.
        #  - Tentar novamente em timeout (até MAX_RETRIES), reemitindo RRQ se necessário.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
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
        # ============================================================================
        # REQ: GSE-LLR-407 – Fluxo WRQ com ACK(0) e envio em blocos
        # Tipo: Funcional
        # Descrição: Enviar WRQ, aguardar ACK(0), enviar DATA(1..N) e checar ACK(N).
        # Critérios de Aceitação:
        #  - Armazenar TID do servidor a partir do ACK(0).
        #  - Validar ACK(N) correspondente ao bloco enviado.
        #  - Interromper após chunk final (< BLOCK_SIZE) ou último DATA 0-byte.
        #  - Em timeout/erro, logar e propagar exceção.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
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
        # ============================================================================
        # REQ: GSE-LLR-408 – Recepção de WRQ + primeiro DATA
        # Tipo: Funcional
        # Descrição: Aceitar WRQ no socket principal, responder ACK(0), receber DATA(1)
        #            do mesmo remetente e responder ACK(1), retornando o payload.
        # Critérios de Aceitação:
        #  - Validar opcode WRQ e depois DATA com block==1.
        #  - Rejeitar pacotes inesperados com exceção.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
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
        # ============================================================================
        # REQ: GSE-LLR-409 – Servir arquivo em resposta a RRQ com socket efêmero
        # Tipo: Funcional
        # Descrição: Ao RRQ do nome esperado, abrir socket efêmero e enviar DATA(1..N)
        #            do arquivo, aguardando ACK a cada bloco, e depois enviar o HASH.
        # Critérios de Aceitação:
        #  - Validar que filename == expected_filename.
        #  - Usar retries até MAX_RETRIES em cada bloco (helper _send_data_and_wait_ack).
        #  - Se arquivo for múltiplo de 512, enviar pacote 0-byte final antes do HASH.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
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
                    # ============================================================================
                    # REQ: GSE-LLR-410 – Callback de progresso 0..100
                    # Tipo: Funcional
                    # Descrição: Informar progresso inteiro 0..100 durante envio do arquivo.
                    # Critérios de Aceitação:
                    #  - prog_pct = int(100 * offset/total_bytes) antes de avançar o offset.
                    #  - Não chamar para o bloco de HASH.
                    # Autor: (preencher) | Revisor: (preencher)
                    # ============================================================================
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
            # ============================================================================
            # REQ: GSE-LLR-411 – Envio de HASH após arquivo
            # Tipo: Funcional
            # Descrição: Enviar hash_data em um DATA adicional e aguardar ACK.
            # Critérios de Aceitação:
            #  - Enviar no bloco subsequente ao último do arquivo.
            #  - Logar sucesso após ACK.
            # Autor: (preencher) | Revisor: (preencher)
            # ============================================================================
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
        # ============================================================================
        # REQ: GSE-LLR-412 – Retransmissão com limite de tentativas por bloco
        # Tipo: Funcional
        # Descrição: Reenviar DATA(block) até MAX_RETRIES quando não chegar ACK adequado.
        # Critérios de Aceitação:
        #  - Validar opcode==ACK e ack_block==block; ignorar ACK de outro endereço.
        #  - Em estouro de tentativas, lançar exceção descritiva.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
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
        # ============================================================================
        # REQ: GSE-LLR-413 – Formato de RRQ (opcode, filename, mode, \0)
        # Tipo: Funcional
        # Descrição: Montar RRQ com opcode 1, filename\0, mode\0 (ASCII).
        # Critérios de Aceitação:
        #  - struct '!H' para opcode; filename e mode codificados e terminados com NUL.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        pkt = struct.pack("!H", TFTP_OPCODE.RRQ.value)
        pkt += filename.encode() + b"\0"
        pkt += mode.encode() + b"\0"
        self.sock.sendto(pkt, addr)
        self.log(f"[TFTP-SEND] RRQ: {filename} para {addr[0]}:{addr[1]}")

    def _send_wrq(self, filename: str, mode: str, addr: Tuple[str, int]):
        # ============================================================================
        # REQ: GSE-LLR-414 – Formato de WRQ (opcode, filename, mode, \0)
        # Tipo: Funcional
        # Descrição: Montar WRQ com opcode 2, filename\0, mode\0 (ASCII).
        # Critérios de Aceitação:
        #  - struct '!H' para opcode; filename e mode codificados e terminados com NUL.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        pkt = struct.pack("!H", TFTP_OPCODE.WRQ.value)
        pkt += filename.encode() + b"\0"
        pkt += mode.encode() + b"\0"
        self.sock.sendto(pkt, addr)
        self.log(f"[TFTP-SEND] WRQ: {filename} para {addr[0]}:{addr[1]}")

    def _send_ack(self, block: int, addr: Tuple[str, int], sock: socket.socket = None):
        # ============================================================================
        # REQ: GSE-LLR-415 – Formato de ACK
        # Tipo: Funcional
        # Descrição: Montar ACK como opcode 4 + block (16-bit).
        # Critérios de Aceitação:
        #  - struct '!HH' com opcode=4 e número do bloco.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        pkt = struct.pack("!HH", TFTP_OPCODE.ACK.value, block)
        (sock or self.sock).sendto(pkt, addr)
        # (Log omitido para não poluir)

    def _send_data(
        self, block: int, data: bytes, addr: Tuple[str, int], sock: socket.socket = None
    ):
        # ============================================================================
        # REQ: GSE-LLR-416 – Formato de DATA
        # Tipo: Funcional
        # Descrição: Montar DATA como opcode 3 + block (16-bit) + payload (<=512B).
        # Critérios de Aceitação:
        #  - struct '!HH' com opcode=3 e número do bloco; payload de até BLOCK_SIZE.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        pkt = struct.pack("!HH", TFTP_OPCODE.DATA.value, block) + data
        (sock or self.sock).sendto(pkt, addr)
        # (Log omitido para não poluir)

    def _parse_data_packet(self, data: bytes) -> Tuple[TFTP_OPCODE, int, bytes]:
        # ============================================================================
        # REQ: GSE-LLR-417 – Parsing de DATA
        # Tipo: Funcional
        # Descrição: Validar tamanho mínimo (4B), extrair opcode, block e payload.
        # Critérios de Aceitação:
        #  - Se len(data)<4, retornar (None, 0, b"").
        #  - opcode convertido para TFTP_OPCODE.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        if len(data) < 4:
            return (None, 0, b"")
        opcode = struct.unpack("!H", data[0:2])[0]
        block = struct.unpack("!H", data[2:4])[0]
        payload = data[4:]
        return (TFTP_OPCODE(opcode), block, payload)

    def _parse_ack_packet(self, data: bytes) -> Tuple[TFTP_OPCODE, int]:
        # ============================================================================
        # REQ: GSE-LLR-418 – Parsing de ACK
        # Tipo: Funcional
        # Descrição: Validar tamanho mínimo (4B) e extrair opcode e número do bloco.
        # Critérios de Aceitação:
        #  - Se len(data)<4, retornar (None, 0).
        #  - opcode convertido para TFTP_OPCODE.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        if len(data) < 4:
            return (None, 0)
        opcode = struct.unpack("!H", data[0:2])[0]
        block = struct.unpack("!H", data[2:4])[0]
        return (TFTP_OPCODE(opcode), block)

    def _parse_rrq_packet(self, data: bytes) -> Tuple[TFTP_OPCODE, str]:
        # ============================================================================
        # REQ: GSE-LLR-419 – Parsing de RRQ/WRQ (filename)
        # Tipo: Funcional
        # Descrição: Extrair opcode e filename (string até NUL após opcode).
        # Critérios de Aceitação:
        #  - Se len(data)<4, retornar (None, "").
        #  - Decodificar UTF-8 com split no '\0'; ignorar opções extras.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        if len(data) < 4:
            return (None, "")
        opcode = struct.unpack("!H", data[0:2])[0]
        filename = data[2:].decode("utf-8").split("\0")[0]
        return (TFTP_OPCODE(opcode), filename)

    def _parse_wrq_packet(self, data: bytes) -> Tuple[TFTP_OPCODE, str]:
        return self._parse_rrq_packet(data)  # Formato é idêntico

    def _parse_error_packet(self, data: bytes) -> Tuple[int, str]:
        # ============================================================================
        # REQ: GSE-LLR-420 – Parsing de ERROR
        # Tipo: Funcional
        # Descrição: Extrair error_code (16-bit) e mensagem terminada em NUL.
        # Critérios de Aceitação:
        #  - Se len(data)<5, retornar (0, "Pacote de erro malformado").
        #  - Mensagem decodificada em UTF-8 com ignore e strip do NUL final.
        # Autor: (preencher) | Revisor: (preencher)
        # ============================================================================
        if len(data) < 5:
            return (0, "Pacote de erro malformado")
        error_code = struct.unpack("!H", data[2:4])[0]
        error_msg = data[4:].decode("utf-8", errors="ignore").rstrip("\0")
        return (error_code, error_msg)
