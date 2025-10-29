#!/usr/bin/env python3
"""
Cliente TFTP para testar servidor ESP32 ARINC 615A
Testa RRQ (Read Request) de arquivo .LUI
"""

import socket
import struct
import sys
import hashlib
import time

from backend.tftp.tftp_lib import (
    TFTPClient,
    TFTP_OPCODE,
    BLOCK_SIZE,
    MAX_RETRIES,
    DEFAULT_TIMEOUT,
)
from backend.arinc.arinc_lib import (
    ARINC_STATUS_ACCEPTED,
    parse_arinc_status_message,
    create_lur_packet,
)

# ============ CONSTANTES ============
# Timeout (seconds) to wait for the final LUS (100%) after receiving the 50% LUS
FINAL_LUS_TIMEOUT = 120


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
            lui_response = parse_arinc_status_message(data)
            print(f"\nResposta ARINC 615A (LUI):")
            if "error" in lui_response:
                print(f"  Erro: {lui_response['error']}")
            else:
                print(f"  File Length: {lui_response['file_length']}")
                print(f"  Protocol Version: {lui_response['protocol_version']}")
                print(f"  Status Code: 0x{lui_response['status_code']:04x}")
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

                filename = data[2:].decode("utf-8").split("\0")[0]
                print(
                    f"[✓] WRQ recebido para arquivo: {filename} de {addr[0]}:{addr[1]}"
                )

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
                    lus_response = parse_arinc_status_message(lus_data)

                    print(f"\nConteúdo do LUS:")
                    print(f"  File Length: {lus_response['file_length']}")
                    print(f"  Protocol Version: {lus_response['protocol_version']}")
                    print(f"  Status Code: 0x{lus_response['status_code']:04x}")
                    print(f"  Description Length: {lus_response['desc_length']}")
                    print(f"  Description: {lus_response['description']}")

                    status_ok = lus_response["status_code"] == ARINC_STATUS_ACCEPTED
                    print(f"\nVerificação do Status:")
                    print(f"  Recebido: 0x{lus_response['status_code']:04x}")
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

                # Prepara dados do LUR (exemplo simplificado)
                header_filename = "fw.bin"
                part_number = "PN12345"
                lur_data = create_lur_packet(header_filename, part_number)

                # Usa função write_file que implementa TFTP com portas efêmeras
                if client.write_file(lur_filename, lur_data):
                    print(f"[✓] LUR enviado com sucesso!")

                    # Agora aguardamos um RRQ do BC para o header (fw.bin)
                    print("\n[...] Aguardando RRQ do Target para enviar fw.bin...")

                    try:
                        rrq_data, rrq_addr = client.sock.recvfrom(516)
                        if len(rrq_data) >= 4:
                            rrq_opcode = struct.unpack("!H", rrq_data[0:2])[0]
                            if rrq_opcode == TFTP_OPCODE.RRQ.value:
                                requested = rrq_data[2:].decode("utf-8").split("\0")[0]
                                print(
                                    f"[✓] RRQ recebido por {requested} de {rrq_addr[0]}:{rrq_addr[1]}"
                                )
                                if requested == header_filename:
                                    # Cria socket efêmero para servir o arquivo (protocolo TFTP padrão)
                                    transfer_sock = socket.socket(
                                        socket.AF_INET, socket.SOCK_DGRAM
                                    )
                                    transfer_sock.settimeout(DEFAULT_TIMEOUT)
                                    # Bind em porta efêmera (0 = sistema escolhe)
                                    transfer_sock.bind(("", 0))
                                    transfer_port = transfer_sock.getsockname()[1]
                                    print(
                                        f"[✓] Socket de transferência criado na porta {transfer_port} (TID)"
                                    )

                                    # Serve o arquivo local fw.bin via TFTP
                                    try:
                                        with open(requested, "rb") as f:
                                            file_data = f.read()
                                            block_num = 1
                                            offset = 0

                                            while offset < len(file_data):
                                                chunk = file_data[
                                                    offset : offset + BLOCK_SIZE
                                                ]
                                                data_pkt = (
                                                    struct.pack(
                                                        "!HH",
                                                        TFTP_OPCODE.DATA.value,
                                                        block_num,
                                                    )
                                                    + chunk
                                                )
                                                retries = 0
                                                while retries < MAX_RETRIES:
                                                    # Envia DATA do socket efêmero
                                                    transfer_sock.sendto(
                                                        data_pkt,
                                                        (rrq_addr[0], rrq_addr[1]),
                                                    )
                                                    try:
                                                        # Aguarda ACK no socket efêmero
                                                        ack_pkt, _ = (
                                                            transfer_sock.recvfrom(516)
                                                        )
                                                        ack_opcode = struct.unpack(
                                                            "!H", ack_pkt[0:2]
                                                        )[0]
                                                        ack_block = struct.unpack(
                                                            "!H", ack_pkt[2:4]
                                                        )[0]
                                                        if (
                                                            ack_opcode
                                                            == TFTP_OPCODE.ACK.value
                                                            and ack_block == block_num
                                                        ):
                                                            break
                                                        retries += 1
                                                    except socket.timeout:
                                                        retries += 1

                                                if retries >= MAX_RETRIES:
                                                    print(
                                                        f"[✗] Falha: ACK não recebido para bloco {block_num}"
                                                    )
                                                    break
                                                print(
                                                    f"[✓] Bloco {block_num} enviado e ACK recebido ({len(chunk)} bytes)"
                                                )
                                                offset += len(chunk)
                                                if offset >= len(file_data):
                                                    print(
                                                        f"[✓] Transferência de {requested} concluída"
                                                    )

                                                    # Enviar pacote com hash real do arquivo
                                                    try:
                                                        real_hash = hashlib.sha256(
                                                            file_data
                                                        ).digest()
                                                    except Exception as e:
                                                        print(
                                                            f"[✗] Falha ao calcular hash do arquivo: {e}"
                                                        )
                                                        real_hash = bytes(32)

                                                    hash_packet = (
                                                        struct.pack(
                                                            "!HH",
                                                            TFTP_OPCODE.DATA.value,
                                                            block_num + 1,
                                                        )
                                                        + real_hash
                                                    )
                                                    transfer_sock.sendto(
                                                        hash_packet,
                                                        (rrq_addr[0], rrq_addr[1]),
                                                    )
                                                    print(
                                                        f"[✓] Hash de verificação enviado (SHA-256: {real_hash.hex()})"
                                                    )

                                                    # Aguardar ACK do hash
                                                    try:
                                                        ack_pkt, _ = (
                                                            transfer_sock.recvfrom(516)
                                                        )
                                                        if len(ack_pkt) >= 4:
                                                            ack_opcode, ack_block = (
                                                                struct.unpack(
                                                                    "!HH", ack_pkt[:4]
                                                                )
                                                            )
                                                            if (
                                                                ack_opcode
                                                                == TFTP_OPCODE.ACK.value
                                                                and ack_block
                                                                == block_num + 1
                                                            ):
                                                                print(
                                                                    "[✓] ACK do hash recebido"
                                                                )
                                                            else:
                                                                print(
                                                                    "[✗] ACK do hash inválido"
                                                                )
                                                    except socket.timeout:
                                                        print(
                                                            "[✗] Timeout aguardando ACK do hash"
                                                        )

                                                    # Aguardar atualizações LUS (50% e 100%)
                                                    print(
                                                        "\n[...] Aguardando atualizações de progresso (LUS)..."
                                                    )

                                                    for expected_progress in [50, 100]:
                                                        # Only increase the socket timeout for the final LUS (100%)
                                                        restore_timeout = False
                                                        old_timeout = None
                                                        if expected_progress == 100:
                                                            try:
                                                                old_timeout = (
                                                                    client.sock.gettimeout()
                                                                )
                                                            except Exception:
                                                                old_timeout = None
                                                            try:
                                                                client.sock.settimeout(
                                                                    FINAL_LUS_TIMEOUT
                                                                )
                                                                restore_timeout = True
                                                            except Exception:
                                                                # If we cannot set timeout, continue with default
                                                                restore_timeout = False

                                                        try:
                                                            print(
                                                                f"\n[...] Aguardando LUS com progresso {expected_progress}%..."
                                                            )
                                                            wrq_data, wrq_addr = (
                                                                client.sock.recvfrom(
                                                                    516
                                                                )
                                                            )

                                                            if (
                                                                len(wrq_data) >= 4
                                                                and struct.unpack(
                                                                    "!H", wrq_data[:2]
                                                                )[0]
                                                                == TFTP_OPCODE.WRQ.value
                                                            ):
                                                                # Envia ACK para o WRQ (bloco 0)
                                                                ack_pkt = struct.pack(
                                                                    "!HH",
                                                                    TFTP_OPCODE.ACK.value,
                                                                    0,
                                                                )
                                                                client.sock.sendto(
                                                                    ack_pkt,
                                                                    (
                                                                        wrq_addr[0],
                                                                        wrq_addr[1],
                                                                    ),
                                                                )

                                                                # Recebe o DATA do LUS
                                                                data_pkt, _ = (
                                                                    client.sock.recvfrom(
                                                                        516
                                                                    )
                                                                )
                                                                if len(data_pkt) >= 4:
                                                                    opcode, block = (
                                                                        struct.unpack(
                                                                            "!HH",
                                                                            data_pkt[
                                                                                :4
                                                                            ],
                                                                        )
                                                                    )
                                                                    if (
                                                                        opcode
                                                                        == TFTP_OPCODE.DATA.value
                                                                    ):
                                                                        lus_data = (
                                                                            data_pkt[4:]
                                                                        )
                                                                        # Verifica o progresso no LUS
                                                                        load_list_ratio = lus_data[
                                                                            -3:
                                                                        ].decode(
                                                                            "ascii"
                                                                        )
                                                                        progress = int(
                                                                            load_list_ratio
                                                                        )

                                                                        # Envia ACK para o bloco de dados
                                                                        ack_pkt = struct.pack(
                                                                            "!HH",
                                                                            TFTP_OPCODE.ACK.value,
                                                                            block,
                                                                        )
                                                                        client.sock.sendto(
                                                                            ack_pkt,
                                                                            (
                                                                                wrq_addr[
                                                                                    0
                                                                                ],
                                                                                wrq_addr[
                                                                                    1
                                                                                ],
                                                                            ),
                                                                        )

                                                                        print(
                                                                            f"[✓] LUS recebido - Progresso: {progress}%"
                                                                        )
                                                                        if (
                                                                            progress
                                                                            != expected_progress
                                                                        ):
                                                                            print(
                                                                                f"[!] Progresso inesperado: esperado {expected_progress}%, recebido {progress}%"
                                                                            )

                                                        except socket.timeout:
                                                            print(
                                                                f"[✗] Timeout aguardando LUS {expected_progress}%"
                                                            )
                                                        except Exception as e:
                                                            print(
                                                                f"[✗] Erro ao processar LUS {expected_progress}%: {e}"
                                                            )
                                                        finally:
                                                            # Restore original timeout if we changed it for the final LUS
                                                            if (
                                                                restore_timeout
                                                                and old_timeout
                                                                is not None
                                                            ):
                                                                try:
                                                                    client.sock.settimeout(
                                                                        old_timeout
                                                                    )
                                                                except Exception:
                                                                    pass

                                                    break
                                                block_num += 1

                                        transfer_sock.close()
                                        print(f"[✓] Socket de transferência fechado")
                                    except FileNotFoundError:
                                        print(
                                            f"[✗] Arquivo local {requested} não encontrado"
                                        )
                                    except Exception as e:
                                        print(
                                            f"[✗] Erro ao servir arquivo {requested}: {e}"
                                        )
                                else:
                                    print(
                                        f"[✗] RRQ pedido por arquivo diferente: {requested}"
                                    )
                            else:
                                print(
                                    f"[✗] Pacote inesperado enquanto aguardava RRQ: opcode={rrq_opcode}"
                                )
                        else:
                            print("[✗] RRQ recebido muito pequeno")
                    except socket.timeout:
                        print("[✗] Timeout aguardando RRQ do Target")
                    except Exception as e:
                        print(f"[✗] Erro ao processar RRQ: {e}")
                else:
                    print(f"[✗] Falha ao enviar LUR")

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


if __name__ == "__main__":
    # Detecta IP do servidor
    if len(sys.argv) > 1:
        server_ip = sys.argv[1]
    else:
        server_ip = "192.168.4.1"  # IP padrão do AP ESP32

    print(f"Conectando ao servidor: {server_ip}")

    # Executa testes
    test_tftp_connection(server_ip)
