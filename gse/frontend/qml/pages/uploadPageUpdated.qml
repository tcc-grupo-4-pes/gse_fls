import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Dialogs

// ============================================================================
// REQ: GSE-LLR-12 – Página Dedicada para Upload de Imagens (GSE)
// Tipo: Requisito Funcional
// Descrição: O sistema deve disponibilizar uma página exclusiva de Upload
// responsável por concentrar as funções de seleção de imagem, confirmação de envio,
// apresentação de progresso de transferência e exibição do status final (sucesso ou falha).
// Autor: Fabrício
// Revisor: Julia
// ============================================================================
Item {
    id: uploadPage

    // Estado e seleção atuais
    property string selectedPN: ""
    property string selectedImage: ""
    // Flag para controle de UI durante transferência
    property bool isTransferring: false

    function appendLog(msg) {
        logsArea.text += msg + "\n"
        logsArea.cursorPosition = logsArea.length
    }

    // Conexões com o backend da tela de upload
    Connections {
        target: uploadBackend

        function onLogMessage(msg) {
            appendLog(msg)
        }

        function onProgressChanged(pct) {
            uploadProgressBar.value = pct
        }

        function onTransferStarted() {
            appendLog("[info] Transferência iniciada.")
            // Entra em modo de transferência: desabilita todos os botões via binding
            isTransferring = true
        }

        function onTransferFinished(ok) {
            appendLog(ok ? "[ok] Transferência concluída." : "[erro] Transferência falhou.")
            // Sai do modo de transferência
            isTransferring = false

            // Limpa seleção (imagem e PN) e reseta progresso.
            // Mantém apenas os logs, retornando ao estado inicial.
            selectedImage = ""
            selectedPN = ""
            uploadProgressBar.value = 0
        }

        // Recebe detalhes do arquivo selecionado (PN e nome) do backend
        function onFileDetailsReady(pn, filename) {
            uploadPage.selectedPN = pn
            uploadPage.selectedImage = filename
            // Habilitação do botão Transferir é automática via binding
        }
    }

    Rectangle {
        id: content
        color: "#ffffff"
        anchors.fill: parent

        // ============================================================================
        // REQ: GSE-LLR-14 – Exibição do Campo Part Number (PN)
        // Tipo: Requisito Funcional
        // Descrição: A página de upload deve exibir um campo contendo o texto “PN:”
        // seguido do número da imagem selecionada, atualizado automaticamente e
        // visível durante todo o processo de upload. O campo do PN deve possuir
        // um contorno sutil para destacar o valor exibido.
        // Autor: Fabrício
        // Revisor: Julia
        // ============================================================================
        Row {
            id: pnRow
            spacing: 8
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.leftMargin: 40
            anchors.topMargin: 30

            Label {
                text: qsTr("PN:")
                color: "#1f2937"
                font.pixelSize: 14
                font.bold: true
                width: 80
                verticalAlignment: Text.AlignVCenter
            }

            Rectangle {
                id: pnValueContainer
                color: "#ffffff"
                border.color: "#d9e4ec"
                border.width: 1
                radius: 4
                width: 600
                height: 28

                Label {
                    id: pnValue
                    anchors.fill: parent
                    anchors.leftMargin: 6
                    verticalAlignment: Text.AlignVCenter
                    color: "#1f2937"
                    font.pixelSize: 14
                    elide: Text.ElideRight
                    clip: true  
                    text: uploadPage.selectedPN.length > 0 ? uploadPage.selectedPN : qsTr("—")
                }
            }
        }

        // ============================================================================
        // REQ: GSE-LLR-16 – Campo de exibição (pré-visualização) da imagem selecionada
        // Tipo: Requisito Funcional
        // Rastreabilidade: GSE-HLR-1, GSE-HLR-5
        // Título: Campo de exibição (pré-visualização) da imagem selecionada
        // Descrição: A página de upload deve apresentar um campo de pré-visualização que
        // mostre o caminho da imagem do arquivo selecionado (quando aplicável). Quando não
        // houver seleção, esse campo deve estar vazio.
        // Autor: Fabrício
        // Revisor: Julia
        // ============================================================================
        Row {
            id: imageRow
            spacing: 8
            anchors.top: pnRow.bottom
            anchors.left: parent.left
            anchors.leftMargin: 40
            anchors.topMargin: 20

            Label {
                text: qsTr("Imagem:")
                color: "#1f2937"
                font.pixelSize: 14
                font.bold: true
                width: 80
                verticalAlignment: Text.AlignVCenter
            }

            Rectangle {
                id: imageValueContainer
                color: "#ffffff"
                border.color: "#d9e4ec"
                border.width: 1
                radius: 4
                width: 600
                height: 28

                Label {
                    id: imageValue
                    anchors.fill: parent
                    anchors.leftMargin: 6
                    verticalAlignment: Text.AlignVCenter
                    color: "#1f2937"
                    font.pixelSize: 14
                    elide: Text.ElideRight
                    clip: true  
                    text: uploadPage.selectedImage.length > 0 ? uploadPage.selectedImage : qsTr("Nenhuma imagem selecionada")
                }
            }
        }

        // ============================================================================
        // REQ: GSE-LLR-17 – Área de exibição de logs (somente leitura) com barra de rolagem
        // Tipo: Requisito Funcional
        // Rastreabilidade: GSE-HLR-5, GSE-HLR-31
        // Título: Área de exibição de logs (somente leitura) com barra de rolagem
        // Descrição: A página de upload deve disponibilizar uma área de logs para exibir
        // mensagens de operação (ex.: seleção, início de upload, progresso, sucesso/falha).
        // O campo deve ser somente leitura e possuir barra de rolagem vertical, permitindo
        // ao operador visualizar todo o histórico de mensagens sem perda de informações.
        // Autor: Fabrício
        // Revisor: Julia
        // ============================================================================
        Label {
            id: logsTitle
            text: qsTr("Logs:")
            color: "#1f2937"
            font.pixelSize: 14
            font.bold: true
            anchors.top: imageRow.bottom
            anchors.topMargin: 20
            anchors.left: parent.left
            anchors.leftMargin: pnRow.anchors.leftMargin
            width: 80
            verticalAlignment: Text.AlignVCenter
        }

        Rectangle {
            id: logsFrame
            height: 200
            width: imageValueContainer.width
            color: "#ffffff"
            border.color: "#d9e4ec"
            border.width: 1
            radius: 4
            anchors.top: imageRow.bottom
            anchors.topMargin: 20
            anchors.left: parent.left
            anchors.leftMargin: pnRow.anchors.leftMargin + 80 + pnRow.spacing

            ScrollView {
                anchors.fill: parent
                clip: true

                TextArea {
                    id: logsArea
                    readOnly: true
                    wrapMode: TextArea.WrapAnywhere
                    text: ""
                    font.family: "monospace"
                    font.pixelSize: 12
                    selectByMouse: true
                    cursorVisible: false
                    background: Rectangle { color: "transparent" }
                }
            }
        }

        // ============================================================================
        // REQ: GSE-LLR-18 – Barra de Progresso com Cores da Embraer
        // Tipo: Requisito Funcional
        // Descrição: A página de upload deve conter uma barra de progresso horizontal
        // posicionada abaixo da área de logs, exibindo visualmente o andamento da
        // transferência de imagem. A barra deve utilizar as cores padrão da Embraer,
        // sendo o azul institucional para a área preenchida e um tom azul-claro para
        // o contorno ou fundo.
        // Autor: Fabrício
        // Revisor: Julia
        // ============================================================================
        Label {
            id: progressLabel
            text: qsTr("Progresso:")
            color: "#1f2937"
            font.pixelSize: 14
            font.bold: true
            anchors.top: logsFrame.bottom
            anchors.topMargin: 20
            anchors.left: parent.left
            anchors.leftMargin: pnRow.anchors.leftMargin
            width: 80
            verticalAlignment: Text.AlignVCenter
        }

        ProgressBar {
            id: uploadProgressBar
            from: 0
            to: 100
            value: 0

            anchors.top: logsFrame.bottom
            anchors.topMargin: 20
            anchors.left: parent.left
            anchors.leftMargin: pnRow.anchors.leftMargin + 80 + pnRow.spacing
            width: imageValueContainer.width
            height: 22

            background: Rectangle {
                radius: 4
                color: "#d9e4ec"
                border.color: "#b0c6d4"
                border.width: 1
            }

            contentItem: Item {
                anchors.fill: parent
                clip: true
                Rectangle {
                    anchors.left: parent.left
                    width: parent.width * uploadProgressBar.visualPosition
                    height: parent.height
                    radius: 4
                    color: "#0067b1"
                }
            }
        }

        // Linha de ações abaixo da barra de progresso
        Row {
            id: actionRow
            spacing: 9
            anchors.top: uploadProgressBar.bottom
            anchors.topMargin: 16
            anchors.left: parent.left
            anchors.leftMargin: pnRow.anchors.leftMargin + 80 + pnRow.spacing
            width: imageValueContainer.width
            height: 36

            property int buttonWidth: 194

            // ============================================================================
            // REQ: GSE-LLR-19 – Botão “Transferir” (Iniciar Upload)
            // Tipo: Requisito Funcional
            // Rastreabilidade: GSE-HLR-2, GSE-HLR-7
            // Título: Botão “Transferir” (Iniciar Upload)
            // Descrição: A página de upload deve apresentar um botão de ação principal rotulado
            // “Transferir”, posicionado em uma linha de ações logo abaixo da barra de progresso.
            // O botão deve iniciar o processo de carregamento da imagem para o Módulo B/C quando
            // acionado. Ele deve permanecer desabilitado até que uma imagem válida e um PN tenham
            // sido selecionados, garantindo que a operação ocorra apenas com dados válidos.
            // Autor: Fabrício
            // Revisor: Julia
            // ============================================================================
            Button {
                id: btnTransferir
                text: qsTr("Transferir")
                width: parent.buttonWidth
                height: 36

                // Habilita apenas se houver imagem + não estiver transferindo
                enabled: uploadPage.selectedImage.length > 0 && !uploadPage.isTransferring

                contentItem: Label {
                    text: btnTransferir.text
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.bold: true
                }
                background: Rectangle {
                    radius: 4
                    color: btnTransferir.down ? "#017cd4" : "#0067b1"
                    border.color: "#015a9b"
                    border.width: 1
                    opacity: btnTransferir.enabled ? 1.0 : 0.5
                }

                onClicked: {
                    if (!enabled) return
                    uploadProgressBar.value = 0
                    // Inicia no backend (exemplo IP)
                    uploadBackend.startTransfer("192.168.4.1")
                    // O isTransferring passa a true via onTransferStarted()
                }
            }

            // ============================================================================
            // REQ: GSE-LLR-20 – Botão “Selecionar Imagem” (Escolha de Arquivo)
            // Tipo: Requisito Funcional
            // Rastreabilidade: GSE-HLR-7
            // Título: Botão “Selecionar Imagem” (Escolha de Arquivo)
            // Descrição: A página de upload deve conter um botão rotulado “Selecionar Imagem”,
            // localizado na mesma linha de ações abaixo da barra de progresso. Esse botão deve
            // abrir uma janela do sistema operacional que permita ao operador selecionar o
            // arquivo de imagem a ser carregado. Após a seleção, o sistema deve atualizar os
            // campos correspondentes e registrar o evento no log de operação.
            // Autor: Fabrício
            // Revisor: Julia
            // ============================================================================
            Button {
                id: btnSelecionarImagem
                text: qsTr("Selecionar Imagem")
                width: parent.buttonWidth
                height: 36

                // Bloqueia durante transferência
                enabled: !uploadPage.isTransferring

                contentItem: Label {
                    text: btnSelecionarImagem.text
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.bold: true
                }

                background: Rectangle {
                    radius: 4
                    color: btnSelecionarImagem.down ? "#017cd4" : "#0067b1"
                    border.color: "#015a9b"
                    border.width: 1
                    opacity: btnSelecionarImagem.enabled ? 1 : 0.6
                }

                onClicked: fileDialog.open()
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
            Button {
                id: btnSair
                text: qsTr("Sair")
                width: parent.buttonWidth
                height: 36

                // Também desabilitado durante transferência
                enabled: !uploadPage.isTransferring

                contentItem: Label {
                    text: btnSair.text
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.bold: true
                }

                background: Rectangle {
                    radius: 4
                    color: btnSair.down ? "#017cd4" : "#0067b1"
                    border.color: "#015a9b"
                    border.width: 1
                    opacity: btnSair.enabled ? 1 : 0.6
                }

                onClicked: {
                    backend.requestLogout()
                }
            }
        }
    }

    // ============================================================================
    // REQ: GSE-LLR-20 – Botão “Selecionar Imagem” (Escolha de Arquivo)
    // Tipo: Requisito Funcional
    // Rastreabilidade: GSE-HLR-7
    // Título: Botão “Selecionar Imagem” (Escolha de Arquivo)
    // Descrição: A página de upload deve conter um botão rotulado “Selecionar Imagem”,
    // localizado na mesma linha de ações abaixo da barra de progresso. Esse botão deve
    // abrir uma janela do sistema operacional que permita ao operador selecionar o
    // arquivo de imagem a ser carregado. Após a seleção, o sistema deve atualizar os
    // campos correspondentes e registrar o evento no log de operação.
    // Autor: Fabrício
    // Revisor: Julia
    // ============================================================================
    FileDialog {
        id: fileDialog
        title: qsTr("Selecionar imagem")
        fileMode: FileDialog.OpenFile
        nameFilters: [
            qsTr("Imagens Embraer (*.LUI *.LUR *.LUS *.LNS *.BIN)"),
            qsTr("Todos os arquivos (*)")
        ]

        onAccepted: {
            // Pode ser QUrl OU string, dependendo da variante do FileDialog
            var url = fileDialog.selectedFile || fileDialog.fileUrl || ""
            // Normaliza para caminho local
            var path = ""
            if (url && url.toLocalFile) {
                path = url.toLocalFile()
            } else {
                path = url.toString ? url.toString() : String(url)
                if (path.startsWith("file:///")) {
                    path = decodeURIComponent(path.substring(8))
                } else if (path.startsWith("file://")) {
                    path = decodeURIComponent(path.substring(7))
                }
            }
            uploadBackend.handleImageSelected(path)
        }
    }
}
