# ============================================================================
# Utilitário de provisionamento de credenciais locais do GSE
# Cumpre: GSE-HLR-22 (armazenamento local isolado) e GSE-LLR-8/9/10/11/13
# Autor: Fabrício Travassos
# Revisor: Julia
# Descrição:
#   Cria o arquivo de credenciais "credentials.json" no diretório do GSE,
#   contendo usuário e senha com hash PBKDF2-HMAC-SHA256 + salt.
# ============================================================================


## @file credentials.py
#  @brief Utilitário para criação de credenciais locais do GSE.
#
#  @details
#  Este módulo implementa o provisionamento de credenciais locais utilizadas pelo
#  Ground Support Equipment (GSE).  
#  Ele cria o arquivo `credentials.json` contendo:
#  - nome de usuário  
#  - salt codificado em Base64  
#  - hash PBKDF2-HMAC-SHA256 codificado em Base64  
#  - parâmetros de derivação (kdf e iterations)  
#
#  O utilitário atende aos requisitos:
#  - **GSE-HLR-22** — Armazenamento local isolado  
#  - **GSE-LLR-8/9/10/11/13** — Regras relacionadas à persistência e segurança  
#
#  Destinado ao uso durante instalação e provisionamento do GSE.
import os, json, base64, hashlib
from pathlib import Path

## @brief Número padrão de iterações usadas no PBKDF2-HMAC-SHA256.
ITERATIONS = 200_000

## @brief Obtém o diretório local onde as credenciais do GSE são armazenadas.
#
#  @details
#  Em Windows, o diretório utilizado é `C:\\ProgramData\\Emb-GSE`.  
#  Em Linux, utiliza-se `/etc/Emb-GSE`.  
#  O diretório é criado se não existir (com `parents=True`).
#
#  @return Objeto `Path` apontando para o diretório do GSE.
def _app_dir():
    if os.name == "nt":
        base = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    else:
        base = "/etc"
    d = Path(base) / "Emb-GSE"
    d.mkdir(parents=True, exist_ok=True)
    return d

## @brief Cria o arquivo de credenciais com hash seguro PBKDF2-HMAC-SHA256.
#
#  @details
#  Esta função gera um *salt* aleatório de 16 bytes e deriva um hash PBKDF2-HMAC-SHA256
#  utilizando o número fixo de iterações (`ITERATIONS`).  
#  Os valores são convertidos para Base64 e armazenados no arquivo
#  `credentials.json` dentro do diretório do GSE.
#
#  O arquivo gerado contém:
#  - `"username"` — nome do usuário
#  - `"salt_b64"` — salt em Base64
#  - `"hash_b64"` — hash PBKDF2 em Base64
#  - `"kdf"` — algoritmo de derivação ("pbkdf2-sha256")
#  - `"iterations"` — número de iterações usadas
#
#  @param username Nome do usuário a ser provisionado.
#  @param password Senha original em texto plano (não armazenada).
#
#  @return None
def create_credentials(username: str, password: str):
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)

    data = {
        "username": username,
        "salt_b64": base64.b64encode(salt).decode("ascii"),
        "hash_b64": base64.b64encode(dk).decode("ascii"),
        "kdf": "pbkdf2-sha256",
        "iterations": ITERATIONS
    }

    cred_path = _app_dir() / "credentials.json"
    cred_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"[OK] Credenciais criadas em: {cred_path}")
    print(f"Usuário: {username}")
    print(f"Senha (não armazenada em texto): {password}")
    
## @brief Execução direta do utilitário de credenciais.
#
#  @details
#  Quando o script é executado diretamente, cria automaticamente credenciais
#  padrão para o usuário `"operador"` com senha `"embraer"`.  
#  Este comportamento destina-se **apenas ao provisionamento inicial**.
if __name__ == "__main__":
    create_credentials("operador", "embraer")
