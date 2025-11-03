# backend/general.py
from __future__ import annotations
from PySide6.QtCore import QObject, Slot, Signal
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QGuiApplication
from pathlib import Path
import json, os, base64, hashlib


class BackendController(QObject):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        # ------------------------------------------------------------------
        # REQ: GSE-HLR-22 / GSE-LLR-28 – Credenciais a partir de fonte local
        # Carrega credenciais (usuário + hash PBKDF2) do arquivo JSON isolado
        # ------------------------------------------------------------------
        self._credentials = {}
        self._load_credentials_from_json()

    # ------------------------ Suporte a PBKDF2 ----------------------------
    # Formato armazenado: pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>
    _ALG = "pbkdf2_sha256"
    _DEFAULT_ITERS = 260000

    @staticmethod
    def _pbkdf2_hash(
        password: str, *, iterations: int = _DEFAULT_ITERS, salt: bytes | None = None
    ) -> str:
        if salt is None:
            salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        salt_b64 = base64.b64encode(salt).decode("ascii")
        hash_b64 = base64.b64encode(dk).decode("ascii")
        return f"{BackendController._ALG}${iterations}${salt_b64}${hash_b64}"

    @staticmethod
    def _pbkdf2_verify(stored: str, password: str) -> bool:
        import base64, hashlib, hmac

        try:
            # Formato compacto: pbkdf2_sha256$<iters>$<salt_b64>$<hash_b64>
            parts = stored.split("$")
            if len(parts) == 4:
                alg, iters_s, salt_b64, hash_b64 = parts
                alg_norm = alg.replace("-", "_")
                if alg_norm != BackendController._ALG:
                    return False
                iterations = int(iters_s)
                salt = base64.b64decode(salt_b64)
                expected = base64.b64decode(hash_b64)
                dk = hashlib.pbkdf2_hmac(
                    "sha256", password.encode("utf-8"), salt, iterations
                )
                return hmac.compare_digest(dk, expected)  # <- mudança aqui

            return False
        except Exception:
            return False

    # ---------------------- Carregar credenciais --------------------------
    def _load_credentials_from_json(self) -> None:
        import json
        from pathlib import Path

        # Caminho fixo do arquivo de credenciais no sistema
        cfg_path = Path(r"C:\ProgramData\Emb-GSE\credentials.json")
        self._credentials = {}

        try:
            if not cfg_path.exists():
                print(f"[Credenciais] Arquivo não encontrado: {cfg_path}")
                return

            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            required = {"username", "salt_b64", "hash_b64", "kdf", "iterations"}
            if not (isinstance(data, dict) and set(data.keys()) == required):
                raise ValueError(
                    "Formato de credenciais inválido: chaves diferentes das esperadas."
                )

            if str(data["kdf"]).strip() != "pbkdf2-sha256":
                raise ValueError("KDF não suportado. Use exatamente 'pbkdf2-sha256'.")

            user = str(data["username"]).strip()
            iters = int(data["iterations"])
            salt_b64 = str(data["salt_b64"]).strip()
            hash_b64 = str(data["hash_b64"]).strip()

            if not user or not salt_b64 or not hash_b64 or iters <= 0:
                raise ValueError(
                    "Conteúdo inválido em users.json (valores ausentes ou inconsistentes)."
                )

            # Normaliza para o formato compacto que o verificador já usa
            alg_compact = "pbkdf2_sha256"  # mapeia o hífen para underscore
            compact = f"{alg_compact}${iters}${salt_b64}${hash_b64}"

            self._credentials = {user: compact}
            print(f"[Credenciais] Carregadas: {list(self._credentials.keys())}")

        except FileNotFoundError:
            print(f"[Credenciais] Arquivo não encontrado: {cfg_path}")
        except Exception as e:
            print(f"[Credenciais] Erro ao ler {cfg_path}: {e}")

    # ---------------------------------------------------------------------
    # GSE-LLR-27 / GSE-LLR-28 – Autenticação e verificação de credenciais
    # Sinais expostos ao QML:
    loginSuccess = Signal()  # navega para a página de upload
    loginFailed = Signal(str)  # exibe mensagem de erro no login

    # ---------------------------------------------------------------------
    @Slot(str, str)
    def verifyLogin(self, username: str, password: str) -> None:
        user = (username or "").strip()
        pwd = password or ""

        if not user or not pwd:
            self.loginFailed.emit("Informe usuário e senha.")
            return

        stored = self._credentials.get(user)
        if not stored:
            self.loginFailed.emit("Usuário não encontrado.")
            return

        if not self._pbkdf2_verify(stored, pwd):
            self.loginFailed.emit("Usuário ou senha inválidos.")
            return

        self.loginSuccess.emit()

    # ============================================================================
    # REQ: GSE-LLR-24 – Encerramento da Aplicação ao Pressionar o Botão "X"
    # Tipo: Requisito Funcional
    # Descrição: Ao pressionar o botão "X" na barra de topo, a aplicação do GSE
    # deve ser encerrada de forma segura e controlada, garantindo o fechamento
    # completo da interface e liberação dos recursos utilizados.
    # Autor: Fabrício
    # Revisor: Julia
    # ============================================================================
    @Slot()
    def closeApp(self):
        """Fecha a aplicação quando chamado pelo QML (botão 'X')."""
        app = QApplication.instance()
        if app is not None:
            app.quit()

    # ============================================================================
    # REQ: GSE-LLR-3 – Minimizar Aplicação ao Pressionar o Botão "_"
    # Tipo: Requisito Funcional
    # Descrição: A interface deve incluir um botão de minimizar localizado na
    # barra de topo, permitindo ao operador reduzir a janela principal do GSE
    # Autor: Fabrício
    # Revisor: Julia
    # ============================================================================
    @Slot()
    def minimizeApp(self):
        """Minimiza a janela principal quando chamado pelo QML (botão '_')."""
        try:
            root_objects = self.engine.rootObjects()
            if root_objects:
                win = root_objects[0]
                win.showMinimized()
            else:
                print("[WindowControls] Nenhuma janela raiz encontrada para minimizar.")
        except Exception as e:
            print(f"[WindowControls] Erro ao minimizar janela: {e}")

    # ============================================================================
    # REQ: GSE-LLR-23 – Movimentação da Janela pela Barra de Topo
    # Tipo: Requisito Funcional
    # Descrição: A aplicação do GSE deve permitir que o operador mova a janela
    # principal clicando e arrastando a barra de topo (Top Bar). Esse comportamento
    # deve simular o movimento padrão de janelas do sistema operacional, oferecendo
    # uma experiência de uso intuitiva e fluida, mesmo em modo frameless.
    # Autor: Fabrício
    # Revisor: Julia
    # ============================================================================
    @Slot()
    def startDrag(self):
        """Inicia o movimento da janela principal (drag pela barra de topo)."""
        try:
            root_objects = self.engine.rootObjects()
            if root_objects:
                win = root_objects[0]
                win.startSystemMove()
            else:
                print("[WindowControls] Nenhuma janela raiz encontrada.")
        except Exception as e:
            print(f"[WindowControls] Erro ao mover janela: {e}")

    # ============================================================================
    # REQ: GSE-LLR-22 – Botão “Sair” (Encerrar Aplicação)
    # Tipo: Requisito Funcional
    # Descrição: A página de upload deve conter um botão rotulado “Sair”, posicionado
    # na mesma linha dos demais botões de ação. Esse botão deve permitir ao operador
    # encerrar o software GSE de forma segura e controlada, retornando à tela de login
    # ou fechando a aplicação conforme o contexto operacional.
    # Autor: Fabrício
    # Revisor: Julia
    # ============================================================================
    logoutRequested = Signal()
    @Slot()
    def requestLogout(self):
        """Emite o sinal para retornar à tela de login."""
        self.logoutRequested.emit()
