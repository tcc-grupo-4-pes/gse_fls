# backend/general.py

"""
\file general.py
\brief Funções utilitárias e controlador principal do backend do GSE.

\details
Este módulo fornece:
- A função \c set_application_icon(), responsável por definir o ícone oficial
  da aplicação GSE utilizando o logotipo institucional da Embraer.
- A classe \c BackendController, responsável por validar credenciais, interagir
  com QML via sinais/slots e controlar ações como login, logout, minimizar,
  fechar e movimentar a janela principal.

Ele implementa requisitos funcionais do GSE (LLR) e oferece integração direta
com a camada gráfica em QML.
"""

from __future__ import annotations
from PySide6.QtCore import QObject, Slot, Signal
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QGuiApplication, QIcon
from pathlib import Path
import json, os, base64, hashlib, sys

# =============================================================================
# REQ: GSE-LLR-27 – Ícone do aplicativo com logotipo da Embraer
# Tipo: Requisito Funcional | Rastreado de: GSE-HLR-20
# Título: Ícone do aplicativo com logotipo da Embraer
# Descrição: O software GSE deve utilizar o logotipo oficial da Embraer como
# ícone da aplicação, preservando proporções e a cor azul institucional
# (#0067B1) sobre fundo branco, visível na barra de título, barra de tarefas
# e atalhos do sistema operacional.
# Autor: Fabrício | Revisor: Julia
# Arquivo: general.py
# =============================================================================
def set_application_icon(app: QApplication) -> None:
    """
    \brief Define o ícone da aplicação GSE.

    \details
    A função determina automaticamente o diretório base da aplicação
    (tanto em modo desenvolvimento quanto empacotado via PyInstaller),
    localiza o ícone institucional da Embraer e o aplica à janela principal.

    Caso o ícone não seja encontrado, uma mensagem de aviso é exibida.

    \param app Instância da aplicação Qt à qual o ícone será aplicado.
    """
    # Determina o diretório base do aplicativo
    if getattr(sys, 'frozen', False):
        # Rodando como executável empacotado pelo PyInstaller
        base_path = Path(sys._MEIPASS)
    else:
        # Rodando em modo de desenvolvimento
        base_path = Path(__file__).resolve().parent.parent.parent
    
    icon_path = base_path / "frontend" / "images" / "svg_images" / "embraer_icon.svg"

    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
        print(f"[INFO] Ícone do aplicativo definido: {icon_path.name}")
    else:
        print(f"[AVISO] Ícone não encontrado. Base: {base_path}, Procurando: embraer_icon.svg")


class BackendController(QObject):
    """
    \class BackendController
    \brief Controlador principal do backend do GSE.

    \details
    Esta classe expõe à camada QML operações essenciais do sistema, incluindo:
    - Validação de credenciais (PBKDF2-HMAC-SHA256)
    - Emissão de sinais de sucesso ou falha no login
    - Encerramento seguro da aplicação
    - Minimização da interface
    - Movimentação (drag) da janela principal
    - Solicitação de logout

    O controlador mantém carregado o conjunto de credenciais armazenadas em
    ``C:\\ProgramData\\Emb-GSE\\credentials.json`` e realiza verificações seguras
    utilizando hashing PBKDF2.
    """
    def __init__(self, engine, parent=None):
        """
        \brief Construtor do controlador do backend.

        \details
        Inicializa o mecanismo QML, carrega o arquivo de credenciais local,
        registra sinais e prepara os métodos para chamada via QML.
        """
        super().__init__(parent)
        self.engine = engine
        
        # ============================================================================
        # REQ: GSE-LLR-28 – Validação de Credenciais ao Pressionar o Botão “Entrar”
        # Tipo: Requisito Funcional
        # Rastreabilidade: GSE-HLR-18, GSE-HLR-19, GSE-HLR-20
        # Título: Validação de Credenciais ao Pressionar o Botão “Entrar”
        # Descrição: Ao pressionar o botão “Entrar” na tela de login, o sistema deve obter
        # o nome de usuário e a senha informados nos campos correspondentes e realizar a
        # validação das credenciais. A verificação deve ser feita comparando o usuário e a
        # senha digitados com os dados armazenados localmente (arquivo de credenciais
        # protegido), utilizando o mecanismo de hash seguro PBKDF2-HMAC-SHA256 conforme
        # definido nos requisitos de segurança. Caso as credenciais sejam válidas, o
        # sistema deve liberar o acesso à interface principal do GSE; caso contrário, deve
        # exibir uma mensagem de erro conforme especificado no requisito GSE-LLR-10.
        # Autor: Fabrício
        # Revisor: Julia
        # ============================================================================
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
        """
        \brief Gera um hash PBKDF2-HMAC-SHA256 para a senha especificada.

        \param password Senha em texto puro.
        \param iterations Número de iterações do algoritmo.
        \param salt Salt criptográfico; se omitido, será gerado automaticamente.

        \return Hash no formato:
                ``pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>``
        """
        if salt is None:
            salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        salt_b64 = base64.b64encode(salt).decode("ascii")
        hash_b64 = base64.b64encode(dk).decode("ascii")
        return f"{BackendController._ALG}${iterations}${salt_b64}${hash_b64}"

    @staticmethod
    def _pbkdf2_verify(stored: str, password: str) -> bool:
        """
        \brief Verifica se a senha fornecida corresponde ao hash PBKDF2 armazenado.

        \param stored Hash armazenado no formato compacto.
        \param password Senha informada pelo usuário.

        \return ``True`` se a senha for válida; caso contrário, ``False``.
        """
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
        """
        \brief Carrega o arquivo de credenciais local.

        \details
        O arquivo deve seguir o formato:

        - ``username``  
        - ``salt_b64``  
        - ``hash_b64``  
        - ``kdf`` (deve ser ``pbkdf2-sha256``)  
        - ``iterations``  

        O método valida o formato e normaliza os dados para o padrão
        utilizado pela função de verificação PBKDF2.

        Mensagens de diagnóstico são exibidas em caso de erro.
        """
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

    # ============================================================================
    # REQ: GSE-LLR-28 – Validação de Credenciais ao Pressionar o Botão “Entrar”
    # Tipo: Requisito Funcional
    # Rastreabilidade: GSE-HLR-18, GSE-HLR-19, GSE-HLR-20
    # Título: Validação de Credenciais ao Pressionar o Botão “Entrar”
    # Descrição: Ao pressionar o botão “Entrar” na tela de login, o sistema deve obter
    # o nome de usuário e a senha informados nos campos correspondentes e realizar a
    # validação das credenciais. A verificação deve ser feita comparando o usuário e a
    # senha digitados com os dados armazenados localmente (arquivo de credenciais
    # protegido), utilizando o mecanismo de hash seguro PBKDF2-HMAC-SHA256 conforme
    # definido nos requisitos de segurança. Caso as credenciais sejam válidas, o
    # sistema deve liberar o acesso à interface principal do GSE; caso contrário, deve
    # exibir uma mensagem de erro conforme especificado no requisito GSE-LLR-10.
    # Autor: Fabrício
    # Revisor: Julia
    # ============================================================================
    loginSuccess = Signal()  # navega para a página de upload
    loginFailed = Signal(str)  # exibe mensagem de erro no login

    @Slot(str, str)
    def verifyLogin(self, username: str, password: str) -> None:
        """
        \brief Verifica credenciais informadas pelo usuário.

        \details
        A senha é validada usando PBKDF2-HMAC-SHA256.  
        O método emite:
        - \c loginSuccess se a autenticação for bem-sucedida  
        - \c loginFailed com mensagem apropriada caso contrário

        \param username Nome de usuário informado.
        \param password Senha informada.
        """
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
        """
        \brief Encerra a aplicação do GSE.

        \details
        Chamado pelo QML quando o usuário pressiona o botão "X".
        Realiza o encerramento seguro via \c QApplication.quit().
        """
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
        """
        \brief Minimiza a janela principal do GSE.

        \details
        Chamado pelo botão "_" da barra de topo.
        Tenta localizar a janela raiz carregada pelo QML e solicita ao Qt
        que a minimize.
        """
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
        """
        \brief Inicia o movimento da janela pela barra de topo.

        \details
        Permite ao operador arrastar a janela, simulando comportamento
        padrão de janelas do sistema operacional, mesmo em interfaces
        frameless.
        """
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
        """
        \brief Solicita o retorno à tela de login.

        \details
        Emite o sinal \c logoutRequested para permitir que a interface
        QML realize a transição adequada.
        """
        self.logoutRequested.emit()
