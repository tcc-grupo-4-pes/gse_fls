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

---

## Procedimentos de Execução

O repositório agrupa dois projetos principais:

- `gse/`: aplicação GSE em Python/Qt (frontend + backend + suíte de testes).
- `modulo_bc/`: firmware do módulo embarcado baseado no ESP-IDF.

As seções abaixo detalham como preparar, executar e validar cada um dos módulos.

### GSE (Python/Qt)

#### Pré-requisitos

- Windows 11 ou Linux com Python 3.12 instalado.
- Git, Visual Studio Code (recomendado) e ferramentas de linha de comando PySide6.

#### Passos

1. Entre na pasta `gse/` e crie um ambiente virtual:
	```powershell
	cd gse
	python -m venv .venv
	.\.venv\Scripts\Activate.ps1
	```
2. Instale as dependências do projeto:
	```powershell
	pip install -r requirements.txt
	```
3. Execute a aplicação GSE com interface Qt:
	```powershell
	python main.py
	```
4. Gere um executável standalone com PyInstaller,
	nesse arquivo, estão descritas as configurações para geração do executável:
	```powershell
	pyinstaller .\main.spec
	```
5. Execute a suíte de testes (pytest já configurado em `pytest.ini`):
	```powershell
	pytest
	# ou
	pytest -m <path_arquivo_teste>
	```

### Módulo BC (ESP-IDF)

#### Pré-requisitos

- ESP-IDF 5.4 instalado.
- Ferramentas USB/serial para comunicação com o ESP32.

#### Passos 

0. Para todas operações a nível de target-Hardware B/C, utilizar terminal integrado ESP-IDF
1. Ative o ambiente ESP-IDF na pasta `modulo_bc/`, basta abrir o vscode nessa pasta:
	```powershell
	cd modulo_bc
	# Ajuste o caminho para o script export do seu ESP-IDF
	C:\esp-idf\export.ps1
	```
2. Configure o alvo e compile:
	```powershell
	idf.py set-target esp32
	idf.py build
	```
3. Faça o flash e abra o monitor serial:
	```powershell
	idf.py flash
	idf.py monitor
	```