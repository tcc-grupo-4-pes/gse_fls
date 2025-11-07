#!/usr/bin/env python3
"""
Módulo Utilitário de Wi-Fi

Fornece funções para verificar o estado da conexão
Wi-Fi do computador (GSE) de forma independente de plataforma.
"""

import subprocess
import platform
import re
from typing import Callable


# ============================================================================
# REQ: GSE-LLR-198 – Contrato de Interface
# HLR: GSE-HLR-79
# Tipo: Requisito Funcional
# Descrição: O módulo DEVE expor uma interface que receba o SSID alvo (string)
#            e um callback de log como entrada.
# Autor: Julia | Revisor: Julia
# ============================================================================
def check_wifi_connection(target_ssid: str, logger: Callable[[str], None]):
    """
    Verifica se o computador (GSE) está conectado ao SSID Wi-Fi correto.

    Levanta uma 'Exception' em caso de falha (não conectado, erro de
    comando, etc.), permitindo que o chamador aborte a operação.

    :param target_ssid: O nome (SSID) da rede Wi-Fi esperada.
    :param logger: Uma função (como 'print' ou 'self.log') para
                   registrar o progresso.
    """

    # ============================================================================
    # REQ: GSE-LLR-199 – Detecção de Plataforma
    # HLR: GSE-HLR-80
    # Tipo: Requisito Funcional
    # Descrição: O módulo DEVE determinar o sistema operacional (SO) em execução
    #            para selecionar a estratégia de verificação de rede apropriada.
    # Autor: Julia | Revisor: Julia
    # ============================================================================
    system = platform.system()
    logger(f"[WIFI] Verificando conexão Wi-Fi.")

    try:
        # ============================================================================
        # REQ: GSE-LLR-200 – Lógica de Verificação (Windows)
        # HLR: GSE-HLR-80
        # Tipo: Requisito Funcional
        # Descrição: Em plataformas Windows, o módulo DEVE consultar os serviços
        #            nativos do SO para obter o status da interface de rede sem fio.
        # Autor: Julia | Revisor: Julia
        # ============================================================================
        if system == "Windows":
            command = ["netsh", "wlan", "show", "interfaces"]
            output = subprocess.check_output(
                command, shell=True, stderr=subprocess.DEVNULL, timeout=5
            )
            try:
                decoded_output = output.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    decoded_output = output.decode("latin-1")
                except UnicodeDecodeError:
                    decoded_output = output.decode("cp850", errors="ignore")

            # ============================================================================
            # REQ: GSE-LLR-201 – Análise de Saída (Windows)
            # HLR: GSE-HLR-80
            # Tipo: Requisito Funcional
            # Descrição: O módulo DEVE ser capaz de analisar a resposta da consulta
            #            ao SO e extrair o SSID da rede Wi-Fi atualmente conectada.
            # Autor: Julia | Revisor: Julia
            # ============================================================================
            match = re.search(r"SSID\s+:\s(.*)", decoded_output)
            if match:
                current_ssid = match.group(1).strip()
                logger(f"[WIFI] SSID atual detectado: '{current_ssid}'")

                # ============================================================================
                # REQ: GSE-LLR-206 – Critério de Sucesso
                # HLR: GSE-HLR-79
                # Tipo: Requisito Funcional
                # Descrição: A verificação DEVE ser considerada bem-sucedida somente se o
                #            SSID atualmente conectado for idêntico ao SSID alvo recebido.
                # Autor: Julia | Revisor: Julia
                # ============================================================================
                if current_ssid == target_ssid:
                    return  # Sucesso!

                # ============================================================================
                # REQ: GSE-LLR-207 – Critério de Falha (SSID Incorreto)
                # HLR: GSE-HLR-79, GSE-HLR-81
                # Tipo: Requisito Funcional
                # Descrição: Se o SSID atual for determinado e for diferente do SSID
                #            alvo, o módulo DEVE sinalizar uma falha via exceção.
                # Autor: Julia | Revisor: Julia
                # ============================================================================
                else:
                    raise Exception(f"Não está no Wi-Fi correto.")
            else:
                # ============================================================================
                # REQ: GSE-LLR-208 – Critério de Falha (Não Conectado)
                # HLR: GSE-HLR-81
                # Tipo: Requisito Funcional
                # Descrição: Se a consulta ao SO não retornar um SSID (indicando um
                #            estado desconectado ou inativo), o módulo DEVE
                #            sinalizar uma falha via exceção.
                # Autor: Julia | Revisor: Julia
                # ============================================================================
                raise Exception(
                    "Não foi possível se conectar ao Wi-fi. Verifique se está no modo de Manuntenção."
                )

        # ============================================================================
        # REQ: GSE-LLR-202 – Lógica de Verificação (Linux)
        # HLR: GSE-HLR-80
        # Tipo: Requisito Funcional
        # Descrição: Em plataformas Linux, o módulo DEVE consultar os serviços
        #            nativos do SO para obter o SSID da interface sem fio ativa.
        # Autor: Julia | Revisor: Julia
        # ============================================================================
        elif system == "Linux":
            command = ["iwgetid", "-r"]
            output = subprocess.check_output(
                command, stderr=subprocess.DEVNULL, text=True, timeout=5
            )
            current_ssid = output.strip()
            logger(f"[WIFI] SSID atual detectado: '{current_ssid}'")

            # Implementação de GSE-LLR-206 (Sucesso)
            if current_ssid == target_ssid:
                return  # Sucesso!
            # Implementação de GSE-LLR-207 (Falha: Incorreto)
            else:
                raise Exception(f"Não está no Wi-Fi correto.")

        # ============================================================================
        # REQ: GSE-LLR-203 – Lógica de Verificação (macOS)
        # HLR: GSE-HLR-80
        # Tipo: Requisito Funcional
        # Descrição: Em plataformas macOS, o módulo DEVE consultar os serviços
        #            nativos do SO para obter o status da interface de rede sem fio.
        # Autor: Julia | Revisor: Julia
        # ============================================================================
        elif system == "Darwin":  # macOS
            command = [
                "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport",
                "-I",
            ]
            output = subprocess.check_output(
                command, stderr=subprocess.DEVNULL, text=True, timeout=5
            )

            # ============================================================================
            # REQ: GSE-LLR-204 – Análise de Saída (macOS)
            # HLR: GSE-HLR-80
            # Tipo: Requisito Funcional
            # Descrição: O módulo DEVE ser capaz de analisar a resposta da consulta
            #            ao SO e extrair o SSID da rede Wi-Fi atualmente conectada.
            # Autor: Julia | Revisor: Julia
            # ============================================================================
            match = re.search(r"^\s*SSID:\s(.*)$", output, re.MULTILINE)
            if match:
                current_ssid = match.group(1).strip()
                logger(f"[WIFI] SSID atual detectado: '{current_ssid}'")

                # Implementação de GSE-LLR-206 (Sucesso)
                if current_ssid == target_ssid:
                    return  # Sucesso!
                # Implementação de GSE-LLR-207 (Falha: Incorreto)
                else:
                    raise Exception(f"Não está no Wi-Fi correto.")
            else:
                # Implementação de GSE-LLR-208 (Falha: Não Conectado)
                raise Exception(
                    "Não foi possível extrair o SSID (interface Wi-Fi inativa?)"
                )

        else:
            # ============================================================================
            # REQ: GSE-LLR-205 – Contenção de SO Desconhecido
            # HLR: GSE-HLR-80
            # Tipo: Requisito Funcional
            # Descrição: Se o SO detectado não for suportado (diferente de Windows,
            #            Linux, macOS), o módulo DEVE registrar um aviso e
            #            sinalizar sucesso.
            # Autor: Julia | Revisor: Julia
            # ============================================================================
            logger(
                f"[WIFI-AVISO] Verificação de Wi-Fi não suportada em {system}. Pulando verificação."
            )
            return  # Não bloquear em SOs desconhecidos

    # ============================================================================
    # REQ: GSE-LLR-209 – Tratamento de Erro de Execução
    # HLR: GSE-HLR-81
    # Tipo: Requisito Funcional
    # Descrição: O módulo DEVE tratar erros operacionais durante a consulta ao SO
    #            (como falhas de execução, timeouts ou permissões) e traduzi-los
    #            em uma falha via exceção.
    # Autor: Julia | Revisor: Julia
    # ============================================================================
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ) as e:
        logger("[WIFI-ERRO] Falha ao executar comando de verificação de Wi-Fi.")
        logger(
            "[WIFI-ERRO] (Verifique se o Wi-Fi está ligado ou se 'iwgetid'/'netsh' está instalado)"
        )
        raise Exception(f"Erro ao verificar Wi-Fi: {e}")

    # ============================================================================
    # REQ: GSE-LLR-210 – Contrato de Exceção
    # HLR: GSE-HLR-81
    # Tipo: Requisito Funcional
    # Descrição: Qualquer falha na verificação DEVE ser propagada para o
    #            chamador através do levantamento de uma exceção.
    # (Este 'except' implementa LLR-207, LLR-208 e LLR-210)
    # Autor: Julia | Revisor: Julia
    # ============================================================================
    except Exception as e:
        # Pega outras falhas (ex: Wi-Fi não conectado / SSID incorreto)
        logger(f"[WIFI-ERRO] {e}")
        raise Exception(f"Falha na verificação do Wi-Fi: {e}")
