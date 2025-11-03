# Captura Automática de Logs do ESP32

## Como Usar

```cmd
python capture_monitor_logs.py
```

## O que faz

1. **Detecta automaticamente** os caminhos do ESP-IDF instalado
2. **Inicia o monitor** usando `idf_monitor.py` diretamente
3. **Captura TODAS as linhas** do monitor serial (porta COM8 padrão)
4. **Exibe no terminal** em tempo real
5. **Salva automaticamente** em `log.txt` no diretório do projeto
6. **Adiciona cabeçalho** com timestamp de início e porta serial
7. **Adiciona rodapé** com timestamp de fim quando você para (Ctrl+C)

## Formato do arquivo log.txt

```
============================================================
Início da captura: 2025-11-02 15:30:45
Porta: COM8
============================================================

I (328) cpu_start: Starting scheduler on APP CPU.
I (338) STATE_INIT: INIT ST_INIT
I (348) STATE_MAINT_WAIT: INIT ST_MAINT_WAIT
...

============================================================
Fim da captura: 2025-11-02 15:45:20
============================================================
```

## Recursos

- ✅ **Detecção automática**: Encontra ESP-IDF instalado
- ✅ **Captura contínua**: Funciona durante toda a execução
- ✅ **Append mode**: Cada execução adiciona ao final do arquivo
- ✅ **Tempo real**: Vê os logs no terminal enquanto salva
- ✅ **Automático**: Sem necessidade de copiar/colar
- ✅ **Histórico**: Mantém log de todas as execuções
- ✅ **Porta configurável**: Aceita COM3, COM8, etc como argumento
- ✅ **Integração VS Code**: Tasks prontas para execução rápida

## 🚀 Como Fazer Executar AUTOMATICAMENTE

### Método 1: Substituir comando padrão de monitor
Crie um alias ou substitua `idf.py monitor` por `auto_monitor.bat`:

1. **Via terminal**: Em vez de digitar `idf.py monitor`, use:
   ```cmd
   auto_monitor.bat
   ```

2. **Via VS Code settings**: Adicione em `.vscode/settings.json`:
   ```json
   {
     "terminal.integrated.profiles.windows": {
       "ESP-IDF Monitor": {
         "path": "cmd.exe",
         "args": ["/K", "cd", "${workspaceFolder}", "&&", "auto_monitor.bat"]
       }
     },
     "terminal.integrated.defaultProfile.windows": "ESP-IDF Monitor"
   }
   ```
   Agora todo novo terminal abrirá com o monitor automático!

### Método 2: Atalho de teclado (Recomendado)
Adicione em `.vscode/keybindings.json` (crie se não existir):
```json
[
  {
    "key": "ctrl+shift+m",
    "command": "workbench.action.tasks.runTask",
    "args": "Monitor Serial com Log Automático"
  }
]
```
Agora **Ctrl+Shift+M** inicia o monitor com captura automática!

### Método 3: Botão no VS Code (Mais visual)
1. Instale a extensão "Task Runner" ou "Taskbar"
2. Configure para mostrar a task "Monitor Serial com Log Automático" na barra
3. Clique no botão para iniciar

### Método 4: Script de startup
Crie um arquivo `monitor.cmd` na raiz do projeto:
```cmd
@echo off
cd /d "%~dp0"
auto_monitor.bat
```
Sempre que quiser monitorar, execute `monitor.cmd`

## Porta Serial

Por padrão usa **COM8**. Para mudar:
```cmd
python capture_monitor_logs.py COM3
```

## Para parar

Pressione **Ctrl+C** no terminal

O arquivo será automaticamente fechado com timestamp de fim.

## Limpar logs antigos

Se quiser começar um arquivo novo:
```cmd
del log.txt
python capture_monitor_logs.py
```

## Requisitos

- ESP-IDF instalado (detecta automaticamente em `D:\bruno\Espressif`)
- Projeto compilado (`build/state_machine.elf` deve existir)
