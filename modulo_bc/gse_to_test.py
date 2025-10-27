#!/usr/bin/env python3
"""
Cliente TFTP para testar servidor ESP32 ARINC 615A
Testa RRQ (Read Request) de arquivo .LUI
"""

import socket
import struct
import time
import sys
from enum import Enum
from typing import Optional, Tuple
import hashlib

# ============ CÓDIGOS TFTP ============
class TFTP_OPCODE(Enum):
    RRQ = 1      # Read request (download)
    WRQ = 2      # Write request (upload)
    DATA = 3     # Pacote de dados
    ACK = 4      # Confirmação
    ERROR = 5    # Erro

# ============ CÓDIGOS DE ERRO TFTP ============
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
TIMEOUT_SEC = 5
MAX_RETRIES = 5
# Timeout (seconds) to wait for the final LUS (100%) after receiving the 50% LUS
FINAL_LUS_TIMEOUT = 120

# ============ STATUS ARINC ============
ARINC_STATUS_ACCEPTED = 0x0001
ARINC_STATUS_IN_PROGRESS = 0x0002
ARINC_STATUS_COMPLETED_OK = 0x0003
ARINC_STATUS_REJECTED = 0x1000


class TFTPClient:
    def __init__(self, server_ip: str, server_port: int = TFTP_PORT, timeout: int = TIMEOUT_SEC):
        """Inicializa cliente TFTP"""
        self.server_ip = server_ip
        self.server_port = server_port
        self.timeout = timeout
        self.sock = None
        self.server_tid = None  # Transfer ID (porta do servidor)
        
    def connect(self) -> bool:
        """Cria socket UDP"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(self.timeout)
            print(f"[✓] Socket UDP criado")
            return True
        except Exception as e:
            print(f"[✗] Erro ao criar socket: {e}")
            return False
    
    def close(self):
        """Fecha socket"""
        if self.sock:
            self.sock.close()
            print(f"[✓] Socket fechado")
    
    def send_rrq(self, filename: str, mode: str = "octet") -> bool:
        """
        Envia Read Request (RRQ)
        Formato: [opcode(2)][filename\0][mode\0]
        """
        try:
            # Monta pacote RRQ
            pkt = struct.pack("!H", TFTP_OPCODE.RRQ.value)
            pkt += filename.encode() + b'\0'
            pkt += mode.encode() + b'\0'
            
            # Envia para porta 69
            self.sock.sendto(pkt, (self.server_ip, TFTP_PORT))
            print(f"[✓] RRQ enviado: {filename} (modo: {mode})")
            return True
        except Exception as e:
            print(f"[✗] Erro ao enviar RRQ: {e}")
            return False
    
    def recv_data_packet(self) -> Optional[Tuple[int, bytes]]:
        """
        Recebe pacote DATA
        Retorna (block_number, data)
        """
        try:
            data, addr = self.sock.recvfrom(4 + BLOCK_SIZE)
            
            if len(data) < 4:
                print(f"[✗] Pacote muito pequeno: {len(data)} bytes")
                return None
            
            opcode = struct.unpack("!H", data[0:2])[0]
            
            if opcode != TFTP_OPCODE.DATA.value:
                if opcode == TFTP_OPCODE.ERROR.value:
                    error_code = struct.unpack("!H", data[2:4])[0]
                    error_msg = data[4:].decode('utf-8', errors='ignore').rstrip('\0')
                    print(f"[✗] Erro TFTP {error_code}: {error_msg}")
                    return None
                print(f"[✗] Opcode inesperado: {opcode}")
                return None
            
            block = struct.unpack("!H", data[2:4])[0]
            payload = data[4:]
            
            # Guarda TID do servidor (porta)
            self.server_tid = addr[1]
            
            print(f"[✓] DATA bloco {block} recebido ({len(payload)} bytes) de {addr[0]}:{addr[1]}")
            return (block, payload)
            
        except socket.timeout:
            print(f"[✗] Timeout ao receber DATA")
            return None
        except Exception as e:
            print(f"[✗] Erro ao receber DATA: {e}")
            return None
    
    def send_ack(self, block: int) -> bool:
        """
        Envia ACK
        Formato: [opcode(2)][block(2)]
        """
        try:
            if not self.server_tid:
                print(f"[✗] TID do servidor desconhecido")
                return False
            
            pkt = struct.pack("!HH", TFTP_OPCODE.ACK.value, block)
            self.sock.sendto(pkt, (self.server_ip, self.server_tid))
            print(f"[✓] ACK enviado para bloco {block}")
            return True
        except Exception as e:
            print(f"[✗] Erro ao enviar ACK: {e}")
            return False
    
    def read_file(self, filename: str) -> Optional[bytes]:
        """
        Lê arquivo via TFTP (RRQ)
        Retorna conteúdo do arquivo ou None em caso de erro
        """
        data_buffer = b''
        expected_block = 1
        retry_count = 0
        
        # Envia RRQ inicial
        if not self.send_rrq(filename):
            return None
        
        while True:
            # Recebe bloco de dados
            result = self.recv_data_packet()
            
            if result is None:
                retry_count += 1
                if retry_count >= MAX_RETRIES:
                    print(f"[✗] Limite de tentativas atingido")
                    return None
                print(f"[⟳] Retry {retry_count}/{MAX_RETRIES}")
                time.sleep(1)
                continue
            
            block, payload = result
            retry_count = 0
            
            # Verifica bloco esperado
            if block != expected_block:
                print(f"[✗] Bloco fora de ordem: esperado {expected_block}, recebido {block}")
                # Reenvia ACK do último bloco válido
                self.send_ack(expected_block - 1)
                continue
            
            # Acumula dados
            data_buffer += payload
            
            # Envia ACK
            self.send_ack(block)
            
            # Se recebeu menos que BLOCK_SIZE, é o último bloco
            if len(payload) < BLOCK_SIZE:
                print(f"[✓] Transfer completo! Total: {len(data_buffer)} bytes")
                return data_buffer
            
            expected_block += 1


def parse_lui_response(data: bytes) -> dict:
    """
    Parseia resposta LUI ARINC 615A
    Formato: [file_length(4)][protocol_version(2)][status_code(2)][desc_length(1)][description(n)]
    """
    if len(data) < 9:
        return {"error": "Dados insuficientes"}
    
    # Parse dos campos na ordem correta
    file_length = struct.unpack("!L", data[0:4])[0]
    protocol_version = data[4:6].decode('ascii', errors='ignore')
    status_code = struct.unpack("!H", data[6:8])[0]
    desc_length = data[8]
    description = data[9:9+desc_length].decode('ascii', errors='ignore')
    
    status_map = {
        ARINC_STATUS_ACCEPTED: "Operação Aceita",
        ARINC_STATUS_IN_PROGRESS: "Em Progresso",
        ARINC_STATUS_COMPLETED_OK: "Concluído com Sucesso",
        ARINC_STATUS_REJECTED: "Operação Rejeitada",
    }
    
    return {
        "file_length": file_length,
        "protocol_version": protocol_version,
        "status_code": f"0x{status_code:04x}",
        "status_name": status_map.get(status_code, "Desconhecido"),
        "desc_length": desc_length,
        "description": description
    }


def test_tftp_connection(server_ip: str):
    """Testa conexão com servidor TFTP ESP32"""
    print(f"\n{'='*60}")
    print(f"TESTE DE CLIENTE TFTP - ESP32 ARINC 615A")
    print(f"{'='*60}\n")
    
    client = TFTPClient(server_ip)
    
    # Conecta
    if not client.connect():
        return
    
    try:
        # Teste 1: Requisição válida de arquivo .LUI
        print(f"[TESTE 1] Requisição de arquivo .LUI válido")
        print(f"-" * 60)
        
        filename = "system.LUI"
        data = client.read_file(filename)
        
        if data:
            print(f"\n[✓] Arquivo LUI recebido com sucesso!")
            print(f"Tamanho: {len(data)} bytes")
            print(f"Hex: {data.hex()}")
            
            # Parseia resposta ARINC
            lui_response = parse_lui_response(data)
            print(f"\nResposta ARINC 615A (LUI):")
            if "error" in lui_response:
                print(f"  Erro: {lui_response['error']}")
            else:
                print(f"  File Length: {lui_response['file_length']}")
                print(f"  Protocol Version: {lui_response['protocol_version']}")
                print(f"  Status Code: {lui_response['status_code']}")
                print(f"  Status: {lui_response['status_name']}")
                print(f"  Description Length: {lui_response['desc_length']}")
                print(f"  Description: {lui_response['description']}")
                
            # Aguarda e recebe o arquivo LUS do Target
            print(f"\n[...] Aguardando arquivo LUS do Target...")
            
            # Espera WRQ do Target (BC envia WRQ->GSE quando quer mandar LUS)
            try:
                data, addr = client.sock.recvfrom(516)
                if len(data) < 4:
                    print(f"[✗] Pacote WRQ muito pequeno: {len(data)} bytes")
                    return

                opcode = struct.unpack("!H", data[0:2])[0]
                if opcode != TFTP_OPCODE.WRQ.value:
                    print(f"[✗] Opcode inesperado no WRQ: {opcode}")
                    return

                filename = data[2:].decode('utf-8').split('\0')[0]
                print(f"[✓] WRQ recebido para arquivo: {filename} de {addr[0]}:{addr[1]}")

                # Salva TID do servidor (porta) e envia ACK(0)
                client.server_tid = addr[1]
                client.send_ack(0)

                # Recebe o DATA (LUS) enviado pelo BC
                lus_data = None
                result = client.recv_data_packet()
                if result:
                    block, lus_data = result
                    # Confirma o bloco recebido
                    client.send_ack(block)

                if lus_data and len(lus_data) >= 4:
                    print(f"\n[✓] Arquivo LUS recebido com sucesso!")
                    print(f"Tamanho: {len(lus_data)} bytes")
                    print(f"Hex: {lus_data.hex()}")

                    # Parse do LUS - Formato específico ARINC 615A
                    file_length = struct.unpack("!L", lus_data[0:4])[0]
                    protocol_version = lus_data[4:6].decode('ascii')  # A4
                    status_code = struct.unpack("!H", lus_data[6:8])[0]
                    desc_length = lus_data[8]
                    description = lus_data[9:9+desc_length].decode('ascii')

                    print(f"\nConteúdo do LUS:")
                    print(f"  File Length: {file_length}")
                    print(f"  Protocol Version: {protocol_version}")
                    print(f"  Status Code: 0x{status_code:04x}")
                    print(f"  Description Length: {desc_length}")
                    print(f"  Description: {description}")

                    status_ok = status_code == ARINC_STATUS_ACCEPTED
                    print(f"\nVerificação do Status:")
                    print(f"  Recebido: 0x{status_code:04x}")
                    print(f"  Esperado: 0x{ARINC_STATUS_ACCEPTED:04x}")
                    print(f"  Resultado: {'[✓] OK' if status_ok else '[✗] FALHA'}")

                    if not status_ok:
                        print(f"[✗] Status LUS incorreto!")
                else:
                    print(f"[✗] Falha ao receber arquivo LUS")
                    # Não prossegue com envio do LUR se não recebeu LUS
                    return

                # Após receber e processar o LUS, enviaremos o arquivo LUR para o BC
                print(f"\n[...] Enviando arquivo LUR para o Target...")

                lur_filename = "test.LUR"
                wrq_pkt = struct.pack("!H", TFTP_OPCODE.WRQ.value)
                wrq_pkt += lur_filename.encode() + b'\0'
                wrq_pkt += b'octet\0'

                # Envia WRQ para o Target usando a porta (TID) do servidor
                client.sock.sendto(wrq_pkt, (server_ip, client.server_tid))
                print(f"[✓] WRQ enviado para arquivo: {lur_filename}")

                # Espera ACK do bloco 0
                try:
                    ack_data, ack_addr = client.sock.recvfrom(516)
                    if len(ack_data) < 4:
                        print(f"[✗] ACK muito pequeno: {len(ack_data)} bytes")
                        return

                    ack_opcode = struct.unpack("!H", ack_data[0:2])[0]
                    ack_block = struct.unpack("!H", ack_data[2:4])[0]

                    if ack_opcode != TFTP_OPCODE.ACK.value or ack_block != 0:
                        print(f"[✗] ACK inválido: opcode={ack_opcode}, block={ack_block}")
                        return

                    print(f"[✓] ACK recebido para bloco 0")

                    # Prepara dados do LUR (exemplo simplificado)
                    lur_data = struct.pack("!L", 64)  # file_length (4 bytes)
                    lur_data += b"A4"  # protocol_version (2 bytes)
                    lur_data += struct.pack("!H", 1)  # num_headers (2 bytes)
                    # Header filename que o BC vai solicitar depois via RRQ
                    header_filename = "fw.bin"
                    lur_data += struct.pack("!B", len(header_filename))
                    lur_data += header_filename.encode()
                    part_number = "PN12345"
                    lur_data += struct.pack("!B", len(part_number))
                    lur_data += part_number.encode()

                    # Envia bloco de dados (block 1)
                    data_pkt = struct.pack("!HH", TFTP_OPCODE.DATA.value, 1)
                    data_pkt += lur_data
                    client.sock.sendto(data_pkt, (server_ip, client.server_tid))
                    print(f"[✓] Dados LUR enviados ({len(lur_data)} bytes)")

                    # Espera ACK final
                    ack_data, _ = client.sock.recvfrom(516)
                    if len(ack_data) >= 4:
                        ack_opcode = struct.unpack("!H", ack_data[0:2])[0]
                        ack_block = struct.unpack("!H", ack_data[2:4])[0]
                        if ack_opcode == TFTP_OPCODE.ACK.value and ack_block == 1:
                            print(f"[✓] LUR enviado com sucesso!")

                            # Agora aguardamos um RRQ do BC para o header (fw.bin)
                            print("\n[...] Aguardando RRQ do Target para enviar fw.bin...")

                            try:
                                rrq_data, rrq_addr = client.sock.recvfrom(516)
                                if len(rrq_data) >= 4:
                                    rrq_opcode = struct.unpack("!H", rrq_data[0:2])[0]
                                    if rrq_opcode == TFTP_OPCODE.RRQ.value:
                                        requested = rrq_data[2:].decode('utf-8').split('\0')[0]
                                        print(f"[✓] RRQ recebido por {requested} de {rrq_addr[0]}:{rrq_addr[1]}")
                                        if requested == header_filename:
                                            # Serve o arquivo local fw.bin via TFTP
                                            try:
                                                with open(requested, 'rb') as f:
                                                    file_data = f.read()
                                                    block_num = 1
                                                    offset = 0
                                                    
                                                    while offset < len(file_data):
                                                        chunk = file_data[offset:offset + BLOCK_SIZE]
                                                        data_pkt = struct.pack("!HH", TFTP_OPCODE.DATA.value, block_num) + chunk
                                                        retries = 0
                                                        while retries < MAX_RETRIES:
                                                            client.sock.sendto(data_pkt, (rrq_addr[0], rrq_addr[1]))
                                                            try:
                                                                ack_pkt, ack_addr2 = client.sock.recvfrom(516)
                                                                if ack_addr2[0] != rrq_addr[0] or ack_addr2[1] != rrq_addr[1]:
                                                                    # pacote de outro peer, ignora
                                                                    continue
                                                                if len(ack_pkt) >= 4:
                                                                    ack_op = struct.unpack("!H", ack_pkt[0:2])[0]
                                                                    ack_b = struct.unpack("!H", ack_pkt[2:4])[0]
                                                                    if ack_op == TFTP_OPCODE.ACK.value and ack_b == block_num:
                                                                        break
                                                            except socket.timeout:
                                                                retries += 1
                                                                print(f"[↻] Timeout aguardando ACK do bloco {block_num}, retry {retries}/{MAX_RETRIES}")
                                                                continue
                                                        if retries >= MAX_RETRIES:
                                                            print(f"[✗] Falha: ACK não recebido para bloco {block_num}")
                                                            break
                                                        print(f"[✓] Bloco {block_num} enviado e ACK recebido ({len(chunk)} bytes)")
                                                        offset += len(chunk)
                                                        if offset >= len(file_data):
                                                            print(f"[✓] Transferência de {requested} concluída")
                                                            
                                                            # Enviar pacote com hash real do arquivo
                                                            try:
                                                                real_hash = hashlib.sha256(file_data).digest()
                                                            except Exception as e:
                                                                print(f"[✗] Falha ao calcular hash do arquivo: {e}")
                                                                real_hash = bytes(32)

                                                            hash_packet = struct.pack("!HH", TFTP_OPCODE.DATA.value, block_num + 1) + real_hash
                                                            client.sock.sendto(hash_packet, (rrq_addr[0], rrq_addr[1]))
                                                            print(f"[✓] Hash de verificação enviado (SHA-256: {real_hash.hex()})")
                                                            
                                                            # Aguardar ACK do hash
                                                            try:
                                                                ack_pkt, _ = client.sock.recvfrom(516)
                                                                if len(ack_pkt) >= 4:
                                                                    ack_opcode, ack_block = struct.unpack("!HH", ack_pkt[:4])
                                                                    if ack_opcode == TFTP_OPCODE.ACK.value and ack_block == block_num + 1:
                                                                        print("[✓] ACK do hash recebido")
                                                                    else:
                                                                        print("[✗] ACK do hash inválido")
                                                            except socket.timeout:
                                                                print("[✗] Timeout aguardando ACK do hash")
                                                            
                                                            # Aguardar atualizações LUS (50% e 100%)
                                                            print("\n[...] Aguardando atualizações de progresso (LUS)...")
                                                            
                                                            for expected_progress in [50, 100]:
                                                                # Only increase the socket timeout for the final LUS (100%)
                                                                restore_timeout = False
                                                                old_timeout = None
                                                                if expected_progress == 100:
                                                                    try:
                                                                        old_timeout = client.sock.gettimeout()
                                                                    except Exception:
                                                                        old_timeout = None
                                                                    try:
                                                                        client.sock.settimeout(FINAL_LUS_TIMEOUT)
                                                                        restore_timeout = True
                                                                    except Exception:
                                                                        # If we cannot set timeout, continue with default
                                                                        restore_timeout = False

                                                                try:
                                                                    print(f"\n[...] Aguardando LUS com progresso {expected_progress}%...")
                                                                    wrq_data, wrq_addr = client.sock.recvfrom(516)

                                                                    if len(wrq_data) >= 4 and struct.unpack("!H", wrq_data[:2])[0] == TFTP_OPCODE.WRQ.value:
                                                                        # Envia ACK para o WRQ (bloco 0)
                                                                        ack_pkt = struct.pack("!HH", TFTP_OPCODE.ACK.value, 0)
                                                                        client.sock.sendto(ack_pkt, (wrq_addr[0], wrq_addr[1]))

                                                                        # Recebe o DATA do LUS
                                                                        data_pkt, _ = client.sock.recvfrom(516)
                                                                        if len(data_pkt) >= 4:
                                                                            opcode, block = struct.unpack("!HH", data_pkt[:4])
                                                                            if opcode == TFTP_OPCODE.DATA.value:
                                                                                lus_data = data_pkt[4:]
                                                                                # Verifica o progresso no LUS
                                                                                load_list_ratio = lus_data[-3:].decode('ascii')
                                                                                progress = int(load_list_ratio)

                                                                                # Envia ACK para o bloco de dados
                                                                                ack_pkt = struct.pack("!HH", TFTP_OPCODE.ACK.value, block)
                                                                                client.sock.sendto(ack_pkt, (wrq_addr[0], wrq_addr[1]))

                                                                                print(f"[✓] LUS recebido - Progresso: {progress}%")
                                                                                if progress != expected_progress:
                                                                                    print(f"[!] Progresso inesperado: esperado {expected_progress}%, recebido {progress}%")

                                                                except socket.timeout:
                                                                    print(f"[✗] Timeout aguardando LUS {expected_progress}%")
                                                                except Exception as e:
                                                                    print(f"[✗] Erro ao processar LUS {expected_progress}%: {e}")
                                                                finally:
                                                                    # Restore original timeout if we changed it for the final LUS
                                                                    if restore_timeout and old_timeout is not None:
                                                                        try:
                                                                            client.sock.settimeout(old_timeout)
                                                                        except Exception:
                                                                            pass
                                                            
                                                            break
                                                        block_num += 1
                                            except FileNotFoundError:
                                                print(f"[✗] Arquivo local {requested} não encontrado")
                                            except Exception as e:
                                                print(f"[✗] Erro ao servir arquivo {requested}: {e}")
                                        else:
                                            print(f"[✗] RRQ pedido por arquivo diferente: {requested}")
                                    else:
                                        print(f"[✗] Pacote inesperado enquanto aguardava RRQ: opcode={rrq_opcode}")
                                else:
                                    print("[✗] RRQ recebido muito pequeno")
                            except socket.timeout:
                                print("[✗] Timeout aguardando RRQ do Target")
                        else:
                            print(f"[✗] ACK final inválido")
                    else:
                        print(f"[✗] ACK final muito pequeno")

                except socket.timeout:
                    print(f"[✗] Timeout aguardando ACK do Target")
                except Exception as e:
                    print(f"[✗] Erro ao enviar LUR: {e}")

            except socket.timeout:
                print(f"[✗] Timeout aguardando WRQ do Target")
            except Exception as e:
                print(f"[✗] Erro ao receber LUS: {e}")
        else:
            print(f"[✗] Falha ao receber arquivo LUI")
    except KeyboardInterrupt:
        print(f"\n[!] Teste interrompido pelo usuário")
    except Exception as e:
        print(f"[✗] Erro durante teste: {e}")
    finally:
        client.close()
    
    print(f"\n{'='*60}\n")


def test_tftp_reliability(server_ip: str, num_requests: int = 5):
    """Testa confiabilidade com múltiplas requisições"""
    print(f"\n{'='*60}")
    print(f"TESTE DE CONFIABILIDADE - {num_requests} REQUISIÇÕES")
    print(f"{'='*60}\n")
    
    success_count = 0
    
    for i in range(num_requests):
        print(f"[REQUISIÇÃO {i+1}/{num_requests}]")
        print(f"-" * 60)
        
        client = TFTPClient(server_ip)
        
        if not client.connect():
            continue
        
        try:
            data = client.read_file(f"test_{i}.LUI")
            if data:
                success_count += 1
                print(f"[✓] Sucesso!")
            else:
                print(f"[✗] Falha!")
        finally:
            client.close()
        
        time.sleep(1)
    
    print(f"\n{'='*60}")
    print(f"Resultados: {success_count}/{num_requests} sucessos ({100*success_count//num_requests}%)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # Detecta IP do servidor
    if len(sys.argv) > 1:
        server_ip = sys.argv[1]
    else:
        server_ip = "192.168.4.1"  # IP padrão do AP ESP32
    
    print(f"Conectando ao servidor: {server_ip}:{TFTP_PORT}")
    
    # Executa testes
    test_tftp_connection(server_ip)
    
   