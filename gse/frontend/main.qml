import QtQuick
import QtQuick.Window
import QtQuick.Controls 2.15
import "qml/controls"
import QtQuick.Layouts 2.15
import Qt5Compat.GraphicalEffects

// ============================================================================
// REQ: GSE-LLR-4 – Dimensão Mínima da Janela Principal
// Tipo: Requisito Funcional
// Descrição: A interface deve manter uma dimensão mínima de 800x500 px para
// garantir a legibilidade e estabilidade dos elementos gráficos da aplicação.
// A janela pode ser redimensionada, mas não deve ser menor que esses valores.
// Autor: Fabrício
// Revisor: Julia
// ============================================================================
Window {
    id: mainWindow
    width: 800
    height: 500
    visible: true
    color: "#00ffffff"
    title: qsTr("GSE")

    // ============================================================================
    // REQ: GSE-LLR-1 – Barra de Topo
    // Tipo: Requisito Funcional
    // Descrição: A interface deve exibir uma barra de status fixa no topo
    // (ou imediatamente abaixo do cabeçalho) com as cores padrão da Embraer.
    // Autor: Fabrício
    // Revisor: Julia
    // ============================================================================
    flags: Qt.Window | Qt.FramelessWindowHint

    Rectangle {
        id: application
        color: "#ffffff"
        anchors.fill: parent

        Rectangle {
            id: bg
            color: "#ffffff"
            anchors.fill: parent

            Rectangle {
                id: topBar
                height: 35
                color: "#0067b1"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.leftMargin: 0
                anchors.rightMargin: 0
                anchors.topMargin: 0

                // ============================================================================
                // REQ: GSE-LLR-2 – Botão de Fechamento
                // Tipo: Requisito Funcional
                // Descrição: A interface deve incluir um botão “X” no canto superior direito
                // da barra de topo, permitindo ao operador encerrar a aplicação do GSE
                // de forma direta e intuitiva, conforme o padrão visual Embraer.
                // Autor: Fabrício
                // Revisor: Julia
                // ============================================================================
                TopBarButton {
                    id: closeButton
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.rightMargin: 0
                    anchors.topMargin: 0
                    anchors.bottomMargin: 0
                    btnIconSource: "../../images/svg_images/close_icon.svg"

                     // Desabilita enquanto a página atual estiver transferindo
                     enabled: !(windowContent.currentItem && windowContent.currentItem.isTransferring)
                     opacity: enabled ? 1.0 : 0.4

                    // ============================================================================
                    // REQ: GSE-LLR-24 – Encerramento da Aplicação ao Pressionar o Botão "X"
                    // Tipo: Requisito Funcional
                    // Descrição: Ao pressionar o botão “X” na barra de topo, a aplicação do GSE
                    // deve ser encerrada de forma segura e controlada, garantindo o fechamento
                    // completo da interface e a liberação adequada dos recursos utilizados.
                    // Autor: Fabrício
                    // Revisor: Julia
                    // ============================================================================
                    onClicked: {
                       // Cinto de segurança: não fecha se estiver transferindo
                        const pg = windowContent.currentItem
                        if (pg && pg.isTransferring) return
                        backend.closeApp()
             }
                }

                // ============================================================================
                // REQ: GSE-LLR-3 – Botão de Minimizar
                // Tipo: Requisito Funcional
                // Descrição: A interface deve incluir um botão de minimizar localizado na
                // barra de topo, permitindo ao operador reduzir a janela principal do GSE
                // para a barra de tarefas do sistema operacional, mantendo o aplicativo em execução.
                // Autor: Fabrício
                // Revisor: Julia
                // ============================================================================
                TopBarButton {
                    id: minimizeButton
                    anchors.right: closeButton.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.rightMargin: 0
                    anchors.topMargin: 0
                    anchors.bottomMargin: 0
                    // ============================================================================
                    // REQ: GSE-LLR-3 – Minimizar Aplicação ao Pressionar o Botão "_"
                    // Tipo: Requisito Funcional
                    // Descrição: A interface deve incluir um botão de minimizar localizado na
                    // barra de topo, permitindo ao operador reduzir a janela principal do GSE
                    // Autor: Fabrício
                    // Revisor: Julia
                    // ============================================================================
                    onClicked: backend.minimizeApp()
                }

                // ============================================================================
                // REQ: GSE-LLR-5 – Logotipo da Embraer na Barra Superior
                // Tipo: Requisito Funcional
                // Descrição: A interface deve exibir o logotipo oficial da Embraer na cor
                // branca, posicionado no lado esquerdo da barra superior, mantendo as
                // proporções originais e o padrão visual da marca.
                // Autor: Fabrício
                // Revisor: Julia
                // ============================================================================
                Image {
                    id: image
                    width: 100
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: 5
                    anchors.topMargin: 0
                    anchors.bottomMargin: 0
                    source: "images/png_images/embraer_white.png"
                    sourceSize.height: 24
                    sourceSize.width: 24
                    fillMode: Image.PreserveAspectFit
                }

                // ============================================================================
                // REQ: GSE-LLR-23 – Movimentação da Janela pela Barra de Topo
                // Tipo: Requisito Funcional
                // Descrição: A aplicação do GSE deve permitir que o operador mova a janela
                // principal clicando e arrastando a barra de topo (Top Bar). Esse comportamento
                // deve simular o movimento padrão de janelas do sistema operacional, oferecendo
                // uma experiência de uso intuitiva e fluida, mesmo em modo frameless.
                // Autor: Fabrício
                // Revisor: Julia
                // ============================================================================
                Rectangle {
                    id: dragBar
                    x: 10
                    y: 0
                    width: 715
                    height: 20
                    color: "#00ffffff"
                    border.color: "#00000000"

                    MouseArea {
                        anchors.fill: parent
                        onPressed: backend.startDrag()
                        hoverEnabled: true
                    }
                }
            }

            // ============================================================================
            // REQ: GSE-LLR-6 – Exibição Automática da Tela de Login
            // Tipo: Requisito Funcional
            // Descrição: Ao iniciar o software GSE, a primeira tela exibida deve ser a tela
            // de login, bloqueando o acesso às demais funcionalidades até que o operador
            // seja autenticado com sucesso.
            // Autor: Fabrício
            // Revisor: Julia
            // ============================================================================

            Rectangle {
                id: content
                color: "#ffffff"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: topBar.bottom
                anchors.bottom: parent.bottom
                anchors.topMargin: 0


                StackView {
                    id: windowContent
                    anchors.fill: parent
                    Component.onCompleted: windowContent.push(Qt.resolvedUrl("qml/pages/loginPageUpdated.qml"))
                    // Component.onCompleted: windowContent.push(Qt.resolvedUrl("qml/pages/uploadPageUpdated.qml"))
                }

                Connections {
                    target: backend
                    // --------------------------------------------------------------------------
                    // REQ: GSE-LLR-6 – Exibição automática da tela de login e navegação pós-login
                    // Tipo: Requisito Funcional
                    // Descrição: Após autenticação bem-sucedida, a UI deve avançar da página de
                    // login para a página de upload.
                    // Autor: Fabrício | Revisor: Julia
                    // --------------------------------------------------------------------------
                    function onLoginSuccess() {
                        windowContent.push(Qt.resolvedUrl("qml/pages/uploadPageUpdated.qml"))
                    }

                    // ---------------------------------------------------------------------
                    // REQ: GSE-LLR-22 – Retorno à Tela de Login ao Clicar em “Sair”
                    // Tipo: Requisito Funcional
                    // Descrição: Ao pressionar o botão “Sair” na página de upload, o sistema
                    // deve encerrar a sessão atual e retornar à tela de login.
                    // Autor: Fabrício
                    // Revisor: Julia
                    // ---------------------------------------------------------------------
                    function onLogoutRequested() {
                    if (windowContent) {
                        windowContent.clear()
                        windowContent.push(Qt.resolvedUrl("qml/pages/loginPageUpdated.qml"))
                        }
                    }
                }
            }
        }
    }
}
