# This Python file uses the following encoding: utf-8
import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from gse.backend.controllers.general import BackendController
from backend.controllers.upload_controller import UploadController  # << NOVO IMPORT

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
    if not engine.rootObjects():
        sys.exit(-1)
    sys.exit(app.exec())
