# This Python file uses the following encoding: utf-8
"""
@file main.py
@brief Ponto de entrada da aplicação GSE FLS PES 2025.

Este módulo inicializa a aplicação Qt/QML responsável por simular o
carregamento de Field Loadable Software (FLS) via Wi-Fi. Ele cria o
QGuiApplication, carrega o arquivo QML principal e expõe ao contexto QML
os controladores Python responsáveis pela lógica de negócio.

Principais responsabilidades:
    - Criar a instância da aplicação Qt (QGuiApplication).
    - Carregar o engine QML (QQmlApplicationEngine) e o arquivo main.qml.
    - Instanciar e expor o BackendController para integração geral com o QML.
    - Instanciar e expor o UploadController para o fluxo de upload de FLS.
    - Configurar o ícone da aplicação.
"""
import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from backend.controllers.general import BackendController, set_application_icon
from backend.controllers.upload_controller import UploadController

# -----------------------------------------------------------------------------
# Função principal
# -----------------------------------------------------------------------------
# \fn int main()
# \brief Inicializa o ambiente Qt/QML e executa o loop principal da aplicação.
#
# Esta função:
#   - Cria o QGuiApplication.
#   - Cria o QQmlApplicationEngine.
#   - Instancia os controladores Python (BackendController e UploadController).
#   - Expõe esses controladores ao contexto QML como "backend" e "uploadBackend".
#   - Carrega o arquivo main.qml.
#   - Configura o ícone da aplicação.
#   - Inicia o loop de eventos da aplicação.
#
# \return Código de saída da aplicação (0 em encerramento bem-sucedido,
#         -1 em caso de falha ao carregar o QML).
if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    # Instancia e expõe controladores
    backend = BackendController(engine)
    engine.rootContext().setContextProperty("backend", backend)

    upload_backend = UploadController()  # << NOVO OBJETO
    engine.rootContext().setContextProperty(
        "uploadBackend", upload_backend
    )  # << EXPOSTO AO QML

    qml_file = Path(__file__).resolve().parent / "frontend/main.qml"
    engine.load(qml_file)
    set_application_icon(app)
    if not engine.rootObjects():
        sys.exit(-1)
    sys.exit(app.exec())
