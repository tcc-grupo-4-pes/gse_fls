# GSE FLS - TCC PES 2025

[![Documentação Doxygen](https://img.shields.io/badge/Doxygen-Documentação-blue?logo=github)](https://tcc-grupo-4-pes.github.io/gse_fls/index.html)

# GSE FLS PES 2025
Simulador de Carregamento de Field Loadable Software (FLS) via Wi-Fi

Este projeto implementa um ambiente completo para simular o carregamento de Field Loadable Software (FLS) utilizando um Ground Support Equipment (GSE) conectado a um módulo embarcado que executa o processo de boot e carregamento.  
O trabalho foi desenvolvido como parte do Programa de Especialização em Software (PES) 2025 – Embraer.

---

## Visão Geral

O sistema reproduz o fluxo real de atualização de FLS em aeronaves, permitindo que um operador utilize um notebook (GSE) para:

- Selecionar um pacote de software FLS
- Verificar sua integridade por meio de SHA-256
- Conectar-se a um módulo embarcado simulado (ESP32)
- Enviar o arquivo via TCP
- Acompanhar o processo de recepção, validação e gravação

O fluxo segue princípios inspirados em documentos como ARINC 615A, DO-178C, mantendo foco educacional e demonstrativo.

---

## Arquitetura do Sistema

O projeto é composto por dois módulos principais:

### 1. GSE (Ground Support Equipment)  
Aplicação desenvolvida em Python/Qt responsável por:
- Interface gráfica baseada em PySide6 / Qt
- Leitura de metadados do FLS e validação SHA-256
- Gerenciamento de conexão Wi-Fi/TCP com o módulo embarcado
- Envio do arquivo FLS
- Exibição de logs operacionais
- Controle dos estados internos do fluxo de carregamento

### 2. Módulo de Boot/Carregamento (ESP32)
Responsável por:
- Anunciar SSID próprio (modo Access Point)
- Estabelecer socket TCP para recepção do arquivo
- Validar estrutura e tamanho do pacote recebido
- Conferir hash SHA-256
- Armazenar o FLS recebido em SPIFFS
- Simular a lógica de boot/entrada em modo de carregamento

---

## Funcionalidades

- Interface gráfica responsiva
- Validação criptográfica via SHA-256
- Conexão direta com o módulo embarcado via Wi-Fi
- Transferência TCP do pacote FLS
- Logs completos para auditoria
- Módulo de boot inspirado em implementações reais

---

## Fluxo de Operação

1. O operador abre o GSE.  
2. Seleciona o arquivo FLS e seu arquivo de metadados.  
3. O GSE calcula o SHA-256 e valida a integridade.  
4. Estabelece conexão com o ESP32 em modo Access Point.  
5. Envia o arquivo FLS via TCP.  
6. O módulo embarcado valida o pacote e confirma o carregamento.  
7. O GSE exibe o status final da operação.
