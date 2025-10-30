import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Dialogs

// ============================================================================
// REQ: GSE-LLR-12 – Exibição do PN em Campo Específico
// Tipo: Requisito Funcional
// Descrição: A página de upload deve exibir o PN da imagem selecionada em um
// campo exclusivo, somente leitura, atualizado imediatamente após a seleção.
// Autor: Fabrício
// Revisor: Julia
// ============================================================================

Item {
    id: uploadPage

    property string selectedPN: ""
    property string selectedImage: ""

    function appendLog(msg) {
        logsArea.text += msg + "\n"
        logsArea.cursorPosition = logsArea.length
    }
    //NOVO
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
            // Desabilita botões durante a transferência
            btnTransferir.enabled = false
            btnSelecionarImagem.enabled = false
            btnCancelar.enabled = true // Habilita o cancelamento
        }
        function onTransferFinished(ok) {
            appendLog(ok ? "[ok] Transferência concluída." : "[erro] Transferência falhou.")
            // Reabilita botões
            btnSelecionarImagem.enabled = true
            btnCancelar.enabled = false
            // O 'enabled' do btnTransferir será reavaliado automaticamente
            // com base nas propriedades 'selectedPN' e 'selectedImage'
        }
        
        // NOVO: Recebe os detalhes do arquivo do backend
        function onFileDetailsReady(pn, filename) {

            uploadPage.selectedPN = pn
            uploadPage.selectedImage = filename
            
            // Habilita o botão de transferir se tudo estiver ok
            btnTransferir.enabled = (pn.length > 0 && filename.length > 0)
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
                    text: uploadPage.selectedPN.length > 0 ? uploadPage.selectedPN : qsTr("—")
                }
            }
        }

        // ============================================================================
        // REQ: GSE-LLR-16 – Campo de Exibição da Imagem Selecionada
        // Tipo: Requisito Funcional
        // Descrição: A página de upload deve conter um campo para exibir o nome da imagem
        // selecionada, acompanhado do rótulo “Imagem:”. O campo deve manter o mesmo padrão
        // visual do campo PN e estar perfeitamente alinhado horizontalmente com ele.
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
                    text: uploadPage.selectedImage.length > 0 ? uploadPage.selectedImage : qsTr("Nenhuma imagem selecionada")
                }
            }
        }

        // ============================================================================
        // REQ: GSE-LLR-17 – Área de Logs com Rolagem
        // Tipo: Requisito Funcional
        // Descrição: Disponibilizar uma área somente leitura para exibição contínua de
        // logs da operação, com rolagem vertical e API para acréscimo de mensagens.
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
            spacing: 8
            anchors.top: uploadProgressBar.bottom
            anchors.topMargin: 16
            anchors.left: parent.left
            anchors.leftMargin: pnRow.anchors.leftMargin + 80 + pnRow.spacing
            width: imageValueContainer.width
            height: 36

            property int buttonWidth: 144

            // ============================================================================
            // REQ: GSE-LLR-19 – Botão “Transferir” (Iniciar Upload)
            // Tipo: Requisito Funcional
            // Descrição: A página de upload deve apresentar um botão de ação principal
            // rotulado “Transferir”, posicionado em uma linha de ações logo abaixo da barra
            // de progresso. O botão deve iniciar o processo de carregamento da imagem para o
            // Módulo B/C quando acionado. Ele deve permanecer desabilitado até que uma imagem
            // válida e um PN tenham sido selecionados. O estilo do botão deve seguir as cores
            // institucionais da Embraer, utilizando fundo azul (#0067B1), variação para hover/
            // pressed (#017CD4) e texto branco.
            // Autor: Fabrício
            // Revisor: Julia
            // ============================================================================
            Button {
                id: btnTransferir
                text: qsTr("Transferir")
                enabled: uploadPage.selectedPN.length > 0 && uploadPage.selectedImage.length > 0
                width: parent.buttonWidth
                height: 36

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

                // TODO: implemente aqui a chamada que inicia o upload
                onClicked: {
                    // Exemplo: logs e reset do progresso
                    if (!enabled) return
                    uploadProgressBar.value = 0
                    uploadBackend.startTransfer("192.168.4.1"); // seu IP do ESP32
                    // sinal/slot para backend:
                    // uploadPage.startUpload(uploadPage.selectedPN, uploadPage.selectedImage)
                }
            }

            // ============================================================================
            // REQ: GSE-LLR-20 – Botão “Selecionar Imagem” (Escolha de Arquivo)
            // Tipo: Requisito Funcional
            // Descrição: A página de upload deve conter um botão rotulado “Selecionar Imagem”,
            // posicionado na mesma linha dos botões de ação logo abaixo da barra de progresso.
            // Esse botão deve abrir uma janela do sistema operacional que permita ao operador
            // escolher o arquivo de imagem a ser carregado. O estilo visual deve seguir o
            // padrão da Embraer, com fundo azul (#0067B1), variação azul-claro (#017CD4) ao
            // pressionar, e texto branco centralizado.
            // Autor: Fabrício
            // Revisor: Julia
            // ============================================================================
            Button {
                id: btnSelecionarImagem
                text: qsTr("Selecionar Imagem")
                width: parent.buttonWidth
                height: 36

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

                onClicked: {
                    fileDialog.open()
                }
            }

            // ============================================================================
            // REQ: GSE-LLR-21 – Botão “Cancelar” (Interrupção do Upload)
            // Tipo: Requisito Funcional
            // Descrição: A página de upload deve conter um botão rotulado “Cancelar”,
            // localizado na mesma linha dos botões de ação logo abaixo da barra de
            // progresso. Esse botão deve permitir ao operador interromper o processo
            // de upload em andamento de forma segura, retornando a interface ao estado
            // inicial. O botão deve seguir o padrão visual Embraer, utilizando fundo
            // azul (#0067B1), variação azul-claro (#017CD4) ao pressionar e texto branco
            // centralizado.
            // Autor: Fabrício
            // Revisor: Julia
            // ============================================================================
            Button {
                id: btnCancelar
                text: qsTr("Cancelar")
                width: parent.buttonWidth
                height: 36
                enabled: true

                contentItem: Label {
                    text: btnCancelar.text
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.bold: true
                }

                background: Rectangle {
                    radius: 4
                    color: btnCancelar.down ? "#017cd4" : "#0067b1"
                    border.color: "#015a9b"
                    border.width: 1
                    opacity: btnCancelar.enabled ? 1 : 0.6
                }

                onClicked: {
                    // TODO: implementar lógica de cancelamento de upload e reset de estado
                }
            }
            // ============================================================================
            // REQ: GSE-LLR-22 – Botão “Sair” (Encerramento da Aplicação)
            // Tipo: Requisito Funcional
            // Descrição: A página de upload deve conter um botão rotulado “Sair”,
            // localizado na mesma linha dos demais botões logo abaixo da barra de
            // progresso. Esse botão deve permitir ao operador encerrar o software
            // GSE de forma segura e controlada, seguindo o padrão visual Embraer
            // com fundo azul (#0067B1), variação azul-claro (#017CD4) ao pressionar
            // e texto branco centralizado.
            // Autor: Fabrício
            // Revisor: Julia
            // ============================================================================
            Button {
                id: btnSair
                text: qsTr("Sair")
                width: parent.buttonWidth
                height: 36

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
    // Descrição: Abrir um diálogo do SO para o operador escolher o arquivo de imagem.
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
                // QUrl
                path = url.toLocalFile()
            } else {
                // String URL (ex.: "file:///C:/.../EMB-0001-021-045.bin")
                path = url.toString ? url.toString() : String(url)
                if (path.startsWith("file:///")) {
                    path = decodeURIComponent(path.substring(8)) // remove "file:///"
                } else if (path.startsWith("file://")) {
                    path = decodeURIComponent(path.substring(7)) // fallback
                }
            }

            uploadBackend.handleImageSelected(path)
            
        }
    }
}


