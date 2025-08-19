// qml/pages/LoginPage.qml
import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Page {
    id: loginPage
    title: qsTr("Entrar")

    signal loginRequested(string username, string password)
    property bool loggingIn: false
    function setError(msg) { errorLabel.text = msg; errorLabel.visible = msg.length > 0 }

    property url logoSource: "../../images/png_images/embraer_logo.png"

    readonly property color brand:      "#0164ac"
    readonly property color brandLight: "#017cd4"
    readonly property color text:       "#1f2937"
    readonly property color muted:      "#6b7280"
    readonly property color danger:     "#d14343"

    background: Rectangle { color: "transparent" }   // sem card/sombra

    // Conteúdo central, responsivo
    ColumnLayout {
        id: form
        anchors.centerIn: parent
        // largura responsiva: encolhe em telas pequenas, limita em telas grandes
        width: Math.min(parent ? parent.width - 160 : 600, 520)
        spacing: 18

        // --- LOGO (proporcional, sem ficar gigante) ---
        Item {
            Layout.fillWidth: true
            implicitHeight: logo.height    // altura do container segue a do logo

            Image {
                id: logo
                anchors.horizontalCenter: parent.horizontalCenter
                source: loginPage.logoSource
                fillMode: Image.PreserveAspectFit
                smooth: true
                mipmap: true

                // largura do logo: até 60% da coluna, com teto
                width: Math.min(parent.width * 0.60, 360)

                // mantém proporção do PNG (1915x322 ≈ 5.94:1). Quando a imagem carregar, usamos o real.
                readonly property real aspect:
                    (status === Image.Ready && sourceSize.height > 0)
                    ? sourceSize.width / sourceSize.height : 5.94
                height: Math.round(width / aspect)
            }
        }

        // Subtítulo
        Label {
            Layout.fillWidth: true
            text: qsTr("Faça login para continuar")
            color: muted
            font.pixelSize: 15
            horizontalAlignment: Text.AlignHCenter
        }

        // --- Campo Usuário (alto e flat) ---
        TextField {
            id: userField
            Layout.fillWidth: true
            height: 52
            placeholderText: qsTr("Usuário ou e-mail")
            font.pixelSize: 15
            enabled: !loginPage.loggingIn
            focus: true
            onAccepted: loginBtn.clicked()
        }

        // --- Campo Senha (alto e flat) ---
        TextField {
            id: passField
            Layout.fillWidth: true
            height: 52
            echoMode: showPass.checked ? TextInput.Normal : TextInput.Password
            placeholderText: qsTr("Senha")
            font.pixelSize: 15
            enabled: !loginPage.loggingIn
            Keys.onReturnPressed: loginBtn.clicked()
        }

        CheckBox {
            id: showPass
            text: qsTr("Mostrar senha")
            enabled: !loginPage.loggingIn
        }

        // Mensagem de erro
        Label {
            id: errorLabel
            Layout.fillWidth: true
            visible: false
            color: danger
            wrapMode: Text.WordWrap
            font.pixelSize: 13
        }

        // --- Botão Entrar (flat, largura total) ---
        Button {
            id: loginBtn
            Layout.fillWidth: true
            height: 54
            enabled: !loginPage.loggingIn

            onClicked: {
                errorLabel.visible = false
                if (userField.text.trim().length === 0) {
                    loginPage.setError(qsTr("Informe o usuário/e-mail."))
                    userField.forceActiveFocus()
                    return
                }
                if (passField.text.length === 0) {
                    loginPage.setError(qsTr("Informe a senha."))
                    passField.forceActiveFocus()
                    return
                }
                loginPage.loggingIn = true
                loginRequested(userField.text.trim(), passField.text)
            }

            contentItem: Label {
                text: loginPage.loggingIn ? qsTr("Entrando...") : qsTr("Entrar")
                color: "#ffffff"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 16
                font.bold: true
            }
            background: Rectangle {
                color: loginBtn.down ? brandLight : brand
                radius: 0   // estilo Metro: sem cantos
                opacity: loginBtn.enabled ? 1 : 0.6
            }
        }

        BusyIndicator {
            running: loginPage.loggingIn
            visible: running
            Layout.alignment: Qt.AlignHCenter
        }

        // Rodapé
        Label {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("© %1 • Embraer").arg(new Date().getFullYear())
            color: muted
            font.pixelSize: 11
        }
    }
}
