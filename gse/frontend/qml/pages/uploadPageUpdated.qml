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

    // Estado e seleção atuais
    property string selectedPN: ""
    property string selectedImage: ""
    // Flag para controle de UI durante transferência
    property bool isTransferring: false
    property bool lastTransferFailed: false
   
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
            lastTransferFailed = false            // ← limpa falha ao iniciar
        }

        function onTransferFinished(ok) {
            appendLog(ok ? "[ok] Transferência concluída." : "[erro] Transferência falhou.")
            // Sai do modo de transferência
            isTransferring = false
            lastTransferFailed = !ok              // ← grava falha se necessário

            // Limpa seleção (imagem e PN) e reseta progresso.
            // Mantém apenas os logs, retornando ao estado inicial.
            selectedImage = ""
            selectedPN = ""
            
        }

        // Recebe detalhes do arquivo selecionado (PN e nome) do backend
        function onFileDetailsReady(pn, filename) {
            uploadPage.selectedPN = pn
            uploadPage.selectedImage = filename
            uploadProgressBar.value = 0
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
                    elide: Text.ElideRight
                    clip: true  
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
            
        // === Indicador à direita da barra ===
        Item {
            id: transferIndicator
            width: 24
            height: 24
            anchors.left: uploadProgressBar.right
            anchors.leftMargin: 10
            anchors.verticalCenter: uploadProgressBar.verticalCenter

        
        // ============================================================================
        // REQ: GSE-LLR-215 – Spinner de Transferência 
        // Tipo: Requisito Funcional
        // Descrição: A interface de upload DEVE exibir, à direita da barra de progresso,
        // um spinner animado durante a transferência.
        // Autor: Nara
        // Revisor: Fabrício
        // ============================================================================
        Canvas {
            id: spinnerCanvas
            anchors.fill: parent
            visible: isTransferring
            onPaint: {
                var ctx = getContext("2d");
                ctx.reset();
                var w = width;
                var h = height;
                var r = Math.min(w, h)/2 - 2;

                ctx.translate(w/2, h/2);
                ctx.rotate(spinnerCanvas.rotation * Math.PI / 180);

            // arco
                ctx.lineWidth = 3;
                ctx.lineCap = "round";
                ctx.strokeStyle = "#0067B1";   // azul GSE
                ctx.beginPath();
            // ~300° de arco, deixando gap
                ctx.arc(0, 0, r, 0.0, 1.7*Math.PI, false);
                ctx.stroke();

            // "ponta" do arco (dot)
                ctx.beginPath();
                ctx.fillStyle = "#0067B1";
                var angle = 1.7*Math.PI;
                ctx.arc(Math.cos(angle)*r, Math.sin(angle)*r, 2.3, 0, 2*Math.PI);
                ctx.fill();
        }

            // rotação contínua
        NumberAnimation on rotation {
            from: 0; to: 360; duration: 900
            loops: Animation.Infinite
            running: isTransferring
        }
    }

        // ============================================================================
        // REQ: GSE-LLR- 197 – Indicador visual de conclusão
        // Tipo: Requisito Funcional
        // Descrição:A interface de upload DEVE exibir um indicador visual à direita da 
        // barra de progresso,mostrando animação de carregamento durante a transferência 
        // e ícone de confirmação (✓) quando concluída com sucesso.
        // Autor: Nara
        // Revisor: Fabrício
        // ============================================================================
        Rectangle {
            id: successCheck
            anchors.fill: parent
            radius: width/2
            color: "#10b981"     // verde sucesso
            border.width: 1
            border.color: "#0d8f6d"
            visible: !isTransferring && uploadProgressBar.value === 100

        Text {
            anchors.centerIn: parent
            text: "✓"
            color: "white"
            font.pixelSize: 14
            font.bold: true
        }
        
    }
       // ============================================================================
        // REQ: GSE-LLR-216 – Indicador de Falha na Transferência
        // Tipo: Requisito Funcional
        // Descrição: A interface de upload DEVE exibir, à direita da barra de progresso,
        // um ícone de falha (X em fundo vermelho) quando a transferência for sem sucesso.
        // Autor: Nara
        // Revisor: Fabrício
        // ============================================================================
    Rectangle {
        id: failBadge
        anchors.fill: parent
        radius: width / 2
        color: "#ef4444"          // vermelho
        border.width: 1
        border.color: "#b91c1c"
        visible: !isTransferring && lastTransferFailed

    Text {
        anchors.centerIn: parent
        text: "✕"             // ou "X"
        color: "white"
        font.pixelSize: 14
        font.bold: true
    }
}

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
