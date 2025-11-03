# ============================================================================
# Utilitário de provisionamento de credenciais locais do GSE
# Cumpre: GSE-HLR-22 (armazenamento local isolado) e GSE-LLR-8/9/10/11/13
# Autor: Fabrício Travassos
# Revisor: Julia
# Descrição:
#   Cria o arquivo de credenciais "credentials.json" no diretório do GSE,
#   contendo usuário e senha com hash PBKDF2-HMAC-SHA256 + salt.
# ============================================================================

import os, json, base64, hashlib
from pathlib import Path

ITERATIONS = 200_000

def _app_dir():
    if os.name == "nt":
        base = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    else:
        base = "/etc"
    d = Path(base) / "Emb-GSE"
    d.mkdir(parents=True, exist_ok=True)
    return d

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

if __name__ == "__main__":
    create_credentials("operador", "embraer")
