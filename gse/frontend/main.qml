import QtQuick
import QtQuick.Window
import QtQuick.Controls 2.15
import "qml/controls"
import QtQuick.Layouts 2.15
import Qt5Compat.GraphicalEffects

// ============================================================================
// REQ: GSE-LLR-4 – Dimensão Fixa da Janela Principal
// Tipo: Requisito Funcional
// Descrição: A interface deve manter uma dimensão fixa de 800x500 px para
// garantir a legibilidade e estabilidade dos elementos gráficos da aplicação.
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
                    // REQ: GSE-LLR-24 – Fechamento da Janela pelo Botão “X”
                    // Tipo: Requisito Funcional
                    // Descrição: Ao pressionar o botão “X” localizado no canto superior direito da
                    // barra de topo, o sistema deve encerrar imediatamente a aplicação do GSE,
                    // finalizando todos os processos associados de forma segura. O fechamento deve
                    // liberar corretamente os recursos utilizados (como conexões, arquivos e memória).
                    // O botão deve permanecer visível e funcional em todos os estados da interface.
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
                    
                    onClicked: backend.minimizeApp()
                }

                // ============================================================================
                // REQ: GSE-LLR-5 – Logo na Barra Superior
                // Tipo: Requisito Funcional
                // Descrição: A interface do GSE deve apresentar o logotipo oficial da Embraer
                // na barra superior (Top Bar) da aplicação. O logotipo deve estar na cor branca,
                // ter proporções preservadas e ser posicionado no lado esquerdo da barra,
                // respeitando a hierarquia visual da interface.
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
                // REQ: GSE-LLR-23 – Arrastar Janela pela Barra de Topo
                // Tipo: Requisito Funcional
                // Descrição: Ao clicar e segurar com o botão esquerdo do mouse sobre a barra de
                // topo, o operador deve poder arrastar a janela do GSE livremente pela tela
                // (comportamento de “drag/move”). O recurso deve funcionar com a janela em estado
                // normal, e o cursor deve indicar movimentação conforme os padrões do sistema
                // operacional.
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
            // REQ: GSE-LLR-6 – Exibição Automática da Tela de Login ao Iniciar o Aplicativo
            // Tipo: Requisito Funcional
            // Descrição: Ao iniciar o software GSE, a primeira tela exibida ao operador deve
            // ser a tela de login, exigindo autenticação por meio de usuário e senha antes de
            // liberar o acesso a qualquer funcionalidade do sistema. A tela deve ser apresentada
            // automaticamente durante o carregamento da interface principal, bloqueando a
            // navegação e o acesso aos módulos até que as credenciais sejam validadas com sucesso.
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
                }

                Connections {
                    target: backend
                    function onLoginSuccess() {
                        windowContent.push(Qt.resolvedUrl("qml/pages/uploadPageUpdated.qml"))
                    }

                    // ============================================================================
                    // REQ: GSE-LLR-22 – Botão “Sair” (Encerrar Aplicação)
                    // Tipo: Requisito Funcional
                    // Descrição: A página de upload deve conter um botão rotulado “Sair”, posicionado
                    // na mesma linha dos demais botões de ação. Esse botão deve permitir ao operador
                    // encerrar o software GSE de forma segura e controlada, retornando à tela de login
                    // ou fechando a aplicação conforme o contexto operacional.
                    // Autor: Fabrício
                    // Revisor: Julia
                    // ============================================================================

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
