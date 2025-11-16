## @file main.py
#  @brief Ponto de entrada da aplicação gráfica PySide6/QML.
#
#  @details Este módulo inicializa a aplicação Qt baseada em QGuiApplication,
#  #         carrega o arquivo QML principal e inicia o loop de eventos.
#  #         Se o carregamento do QML falhar, a aplicação termina com código -1.
#  #
#  #  Dependências principais:
#  #  - PySide6.QtGui.QGuiApplication
#  #  - PySide6.QtQml.QQmlApplicationEngine
#  #  - main.qml (interface em QML localizada no mesmo diretório deste script)

import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine



## @brief Função principal da aplicação.
#
#  @details Esta função:
#  #  1. Cria a instância de QGuiApplication.
#  #  2. Cria o mecanismo QQmlApplicationEngine.
#  #  3. Resolve o caminho do arquivo main.qml no diretório do script.
#  #  4. Carrega o QML no mecanismo.
#  #  5. Verifica se o carregamento foi bem sucedido.
#  #  6. Inicia o loop de eventos da aplicação.
#
#  @return Código de saída da aplicação (0 em caso de término normal,
#          -1 se o QML não puder ser carregado).
if __name__ == "__main__":
    app = QGuiApplication(sys.argv)


    engine = QQmlApplicationEngine()
    qml_file = Path(__file__).resolve().parent / "main.qml"
    engine.load(qml_file)
    if not engine.rootObjects():
        sys.exit(-1)
    sys.exit(app.exec())
