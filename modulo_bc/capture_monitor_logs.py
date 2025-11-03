#!/usr/bin/env python3
"""
Captura logs do ESP-IDF Monitor e salva em log.txt
Uso: python capture_monitor_logs.py [porta_serial]
"""
import subprocess, sys, os, json, signal
from datetime import datetime

def load_settings():
    """Carrega .vscode/settings.json"""
    try:
        with open('.vscode/settings.json', 'r', encoding='utf-8') as f:
            content = '\n'.join(line.split('//')[0] for line in f)
            return json.loads(content)
    except:
        return {}

def get_paths(settings, port):
    """Retorna python_exe, idf_monitor, porta"""
    port = port or settings.get('idf.portWin', 'COM8')
    
    # Usa o Python do ambiente virtual do ESP-IDF, não o standalone
    tools_path = settings.get('idf.toolsPathWin', '')
    idf_path = settings.get('idf.espIdfPathWin', '').rstrip('/\\')
    
    # Procura pelo Python do ambiente virtual (idf5.3_py3.11_env)
    if tools_path:
        python_env_path = os.path.join(tools_path, 'python_env', 'idf5.3_py3.11_env', 'Scripts', 'python.exe')
    else:
        python_env_path = None
    
    monitor = os.path.join(idf_path, 'tools', 'idf_monitor.py') if idf_path else None
    return python_env_path, monitor, port

def main():
    if not os.path.exists('CMakeLists.txt'):
        sys.exit("[ERRO] Execute no diretório raiz do projeto")
    
    settings = load_settings()
    python, monitor, port = get_paths(settings, sys.argv[1] if len(sys.argv) > 1 else None)
    elf = "build/state_machine.elf"
    
    # Validações
    if not python or not os.path.exists(python):
        sys.exit(f"[ERRO] Python não encontrado: {python}")
    if not monitor or not os.path.exists(monitor):
        sys.exit(f"[ERRO] idf_monitor.py não encontrado: {monitor}")
    if not os.path.exists(elf):
        sys.exit(f"[ERRO] Execute 'idf.py build' primeiro!")
    
    # Abre log
    print("="*60)
    print("  Captura Automática de Logs - ESP32")
    print("="*60)
    print(f"Log: {os.path.abspath('log.txt')}")
    print(f"Porta: {port}\n")
    
    log_file = open('log.txt', 'a', encoding='utf-8')
    log_file.write(f"\n{'='*60}\n")
    log_file.write(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Porta: {port}\n")
    log_file.write(f"{'='*60}\n")
    log_file.flush()
    
    # Inicia monitor
    cmd = [python, monitor, "-p", port, "-b", "115200", 
           "--toolchain-prefix", "xtensa-esp32-elf-", "--target", "esp32", elf]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               universal_newlines=True, bufsize=1)
    
    def cleanup(sig=None, frame=None):
        process.terminate()
        process.wait()
        log_file.write(f"\n{'='*60}\n")
        log_file.write(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write(f"{'='*60}\n\n")
        log_file.close()
        print(f"\n\n[INFO] Logs salvos em: {os.path.abspath('log.txt')}\n")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup)
    
    try:
        for line in process.stdout:
            print(line, end='', flush=True)
            log_file.write(line)
            log_file.flush()
        process.wait()
    except Exception as e:
        print(f"\n[ERRO] {e}")
    finally:
        cleanup()

if __name__ == '__main__':
    main()
