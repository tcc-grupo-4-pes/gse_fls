import QtQuick 2.15
import QtQuick.Controls 2.15


// ============================================================================
// REQ: GSE-LLR-13 – Página Dedicada de Login do GSE-SW
// Tipo: Requisito Funcional
// Descrição: O sistema deve conter uma página exclusiva de login, responsável por
// autenticar o operador antes de liberar o acesso às demais funcionalidades do software.
// A página de login deve seguir o padrão visual da Embraer, apresentando campos para
// usuário e senha, além de um botão “Entrar”. Ela deve ser a primeira tela exibida ao
// iniciar o aplicativo, bloqueando o acesso às demais páginas até que o login seja
// concluído com sucesso.
// Autor: Fabrício
// Revisor: Julia
// ============================================================================
Item {
    Rectangle {
        id: content
        color: "#ffffff"
        anchors.fill: parent

        // ============================================================================
        // REQ: GSE-LLR-7 – Exibição do Logotipo Azul da Embraer na Tela de Login
        // Tipo: Requisito Funcional
        // Descrição: A tela de login deve exibir o logotipo oficial da Embraer na cor
        // azul, centralizado na parte superior sobre fundo branco, mantendo proporções
        // originais e legibilidade conforme a identidade visual da marca.
        // Autor: Fabrício
        // Revisor: Julia
        // ============================================================================
        Image {
            id: embraerLogo
            height: 100
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 120
            anchors.rightMargin: 120
            anchors.topMargin: 40
            source: "../../images/png_images/embraer_logo.png"
            fillMode: Image.PreserveAspectFit
        }

        // ============================================================================
        // REQ: GSE-LLR-8 – Campo de Entrada para Nome de Usuário
        // Tipo: Requisito Funcional
        // Descrição: A tela de login do software GSE deve conter um campo de entrada de
        // texto destinado ao nome de usuário. Esse campo deve permitir a digitação livre,
        // aceitar letras, números e caracteres especiais comuns (como “@” e “.”), e exibir
        // um texto de placeholder que indique claramente sua função (por exemplo,
        // “Usuário ou e-mail”).
        // Autor: Fabrício
        // Revisor: Julia
        // ============================================================================
        TextField {
            id: userField
            placeholderText: qsTr("Usuário ou e-mail")
            objectName: "userField"
            enabled: true
            focus: true
            color: "#1f2937"
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: embraerLogo.bottom
            anchors.leftMargin: 120
            anchors.rightMargin: 120
            anchors.topMargin: 50
            background: Rectangle {
                color: "#ffffff"
                border.color: "#d9e4ec"
                radius: 4
            }
        }

        // ============================================================================
        // REQ: GSE-LLR-9 – Campo de Entrada para Senha
        // Tipo: Requisito Funcional
        // Descrição: A tela de login do software GSE deve conter um campo de entrada de
        // senha posicionado abaixo do campo de nome de usuário. O campo deve mascarar os
        // caracteres digitados, exibindo pontos ou asteriscos no lugar dos caracteres reais,
        // preservando a confidencialidade das credenciais. Além disso, deve apresentar um
        // texto de placeholder informativo (por exemplo, “Senha”), estar visualmente
        // alinhado aos demais elementos da tela e respeitar as cores e margens do padrão
        // visual da Embraer.
        // Autor: Fabrício
        // Revisor: Julia
        // ============================================================================
        TextField {
            id: passwordField
            placeholderText: qsTr("Senha")
            objectName: "passwordField"
            echoMode: TextInput.Password
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: userField.bottom
            anchors.leftMargin: 120
            anchors.rightMargin: 120
            anchors.topMargin: 20
            color: "#1f2937"
            background: Rectangle {
                color: "#ffffff"
                border.color: "#d9e4ec"
                radius: 4
            }
        }

        // ============================================================================
        // REQ: GSE-LLR-10 – Exibição de Mensagem de Erro para Credenciais Inválidas
        // Tipo: Requisito Funcional
        // Descrição: A tela de login do software GSE deve exibir uma mensagem de erro textual
        // sempre que o operador inserir credenciais inválidas (usuário ou senha incorretos).
        // Essa mensagem deve ser apresentada abaixo do campo de senha, em cor vermelha (#d14343)
        // e com fonte legível, de forma clara e objetiva. O texto deve desaparecer
        // automaticamente quando o operador corrigir as informações ou após uma nova tentativa
        // bem-sucedida de login. Quando nenhuma falha estiver presente, o campo de erro deve
        // permanecer invisível, não ocupando espaço extra na interface.
        // Autor: Fabrício
        // Revisor: Julia
        // ============================================================================
        Label {
            id: errorLabel
            text: qsTr("Usuário ou senha inválidos.")
            color: "#d14343"
            visible: false
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: passwordField.bottom
            anchors.leftMargin: 120
            anchors.rightMargin: 120
            anchors.topMargin: 10
            wrapMode: Text.WordWrap
            font.pixelSize: 13
        }

        // ============================================================================
        // REQ: GSE-LLR-11 – Botão de Login “Entrar” com Cores da Embraer
        // Tipo: Requisito Funcional
        // Descrição: A tela de login deve conter um botão de ação principal identificado
        // pelo texto “Entrar”, utilizando as cores institucionais da Embraer, centralizado
        // abaixo dos campos de login e senha.
        // Autor: Fabrício
        // Revisor: Julia
        // ============================================================================
        Button {
            id: loginButton
            text: qsTr("Entrar")
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: errorLabel.bottom
            anchors.leftMargin: 120
            anchors.rightMargin: 120
            anchors.topMargin: 20
            height: 42
            enabled: true

            contentItem: Label {
                text: loginButton.text
                color: "#ffffff"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.bold: true
                font.pixelSize: 14
            }

            background: Rectangle {
                radius: 4
                color: loginButton.down ? "#017cd4" : "#0164ac"
                border.color: "#015a9b"
                border.width: 1
                opacity: loginButton.enabled ? 1 : 0.6
            }

            // --------------------------------------------------------------------------
            // REQ: GSE-LLR-28 – Verificação das credenciais ao pressionar "Entrar"
            // Tipo: Requisito Funcional
            // Descrição: Ao clicar no botão "Entrar", o sistema deve ler usuário e senha
            // informados e solicitar ao backend a verificação das credenciais.
            // Autor: Fabrício | Revisor: Julia
            // --------------------------------------------------------------------------
            onClicked: {
                errorLabel.visible = false
                backend.verifyLogin(userField.text, passwordField.text)
            }
        }

        // ============================================================================
        // REQ: GSE-LLR-10 – Exibição de Mensagem de Erro para Credenciais Inválidas
        // Tipo: Requisito Funcional
        // Descrição: A tela de login do software GSE deve exibir uma mensagem de erro textual
        // sempre que o operador inserir credenciais inválidas (usuário ou senha incorretos).
        // Essa mensagem deve ser apresentada abaixo do campo de senha, em cor vermelha (#d14343)
        // e com fonte legível, de forma clara e objetiva. O texto deve desaparecer
        // automaticamente quando o operador corrigir as informações ou após uma nova tentativa
        // bem-sucedida de login. Quando nenhuma falha estiver presente, o campo de erro deve
        // permanecer invisível, não ocupando espaço extra na interface.
        // Autor: Fabrício
        // Revisor: Julia
        // ============================================================================
        Connections {
            target: backend
            function onLoginFailed(msg) {
                errorLabel.text = msg
                errorLabel.visible = true
            }
        }
    }
}
