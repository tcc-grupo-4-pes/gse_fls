// qml/pages/UploadPage.qml
import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Page {
    id: page
    title: qsTr("Upload de Imagens FLS")

    // ======= Sinais p/ backend =======
    signal extractPnRequested(url fileUrl)
    signal hashRequested(url fileUrl)
    signal declaredInfoRequested(url fileUrl)
    signal transferRequested(var image)

    // Callbacks (chame de fora)
    function onPnExtracted(fileUrl, pn) { imagesModel.updateField(fileUrl, "pn", pn) }
    function onHashReady(fileUrl, sha)   { imagesModel.updateField(fileUrl, "shaComputed", sha); imagesModel.updateVerification(fileUrl) }
    function onDeclaredInfoReady(fileUrl, declaredSha, compatList) {
        imagesModel.updateField(fileUrl, "shaDeclared", declaredSha)
        imagesModel.updateField(fileUrl, "compatList", compatList)
        imagesModel.updateVerification(fileUrl)
    }
    function onTransferProgress(fileUrl, percent) { imagesModel.updateField(fileUrl, "progress", Math.max(0, Math.min(100, percent))) }
    function onTransferFinished(fileUrl, ok, message) {
        imagesModel.updateField(fileUrl, "status", ok ? "success" : "failed")
        if (message) log(message)
    }

    // ======= Paleta =======
    readonly property color brand:      "#0164ac"
    readonly property color brandLight: "#017cd4"
    readonly property color text:       "#1f2937"
    readonly property color muted:      "#6b7280"
    readonly property color danger:     "#d14343"
    readonly property color borderCol:  "#d9e4ec"

    background: Rectangle { color: "transparent" }

    // ======= Modelo =======
    ListModel {
        id: imagesModel
        function byUrl(fileUrl) { for (var i=0;i<count;i++) if (get(i).fileUrl === fileUrl) return i; return -1 }
        function addImage(fileUrl) {
            if (!fileUrl || byUrl(fileUrl) !== -1) return
            append({
                fileUrl: fileUrl,
                fileName: fileUrl.toString().split(/[\/\\]/).pop(),
                pn: "",
                shaDeclared: "",
                shaComputed: "",
                compatList: [],
                status: "pending",   // pending | ready | verified | transferring | success | failed
                progress: 0
            })
        }
        function removeAtIndex(i) { if (i>=0 && i<count) remove(i) }
        function updateField(fileUrl, key, value) {
            var i = byUrl(fileUrl); if (i !== -1) set(i, Object.assign({}, get(i), {[key]: value}))
        }
        function updateVerification(fileUrl) {
            var i = byUrl(fileUrl); if (i === -1) return
            var it = get(i)
            var hasBasics = (it.pn && it.shaDeclared)
            var verified  = hasBasics && it.shaDeclared && it.shaComputed
                            && (it.shaDeclared.toLowerCase() === it.shaComputed.toLowerCase())
            var newStatus = verified ? "verified" : (hasBasics ? "ready" : "pending")
            set(i, Object.assign({}, it, { status: newStatus }))
        }
    }

    // ======= Seleção / logs =======
    property int currentIndex: imagesView.currentIndex
    function currentItem() { return currentIndex>=0 && currentIndex<imagesModel.count ? imagesModel.get(currentIndex) : null }

    function log(msg) {
        logsModel.append({ "text": (new Date().toLocaleString()) + " - " + msg })
        Qt.callLater(function(){ logsView.positionViewAtEnd() })
    }

    // ======= FileDialog dinâmico + fallback robusto =======
    function openFilePicker() {
        // 1) Tenta QtQuick.Dialogs 1.3 (Qt5)
        try {
            var src1 =
                    'import QtQuick 2.15\n' +
                    'import QtQuick.Dialogs 1.3\n' +
                    'FileDialog {\n' +
                    '  title: "Selecionar imagem FLS"\n' +
                    '  selectExisting: true\n' +
                    '  nameFilters: [ "Imagens FLS (*.fls *.bin *.img *.zip)", "Todos (*.*)" ]\n' +
                    '  onAccepted: { var u = fileUrl; page._onFilePicked(u); destroy(); }\n' +
                    '  onRejected: { destroy(); }\n' +
                    '}\n';
            var dlg1 = Qt.createQmlObject(src1, page, "DynFD_QQD");
            if (dlg1) { dlg1.open(); return; }
        } catch (e1) {
            console.warn("QtQuick.Dialogs indisponível:", e1);
        }

        // 2) Tenta Qt.labs.platform 1.1 (Qt5/6)
        try {
            var src2 =
                    'import QtQuick 2.15\n' +
                    'import Qt.labs.platform 1.1\n' +
                    'FileDialog {\n' +
                    '  title: "Selecionar imagem FLS"\n' +
                    '  nameFilters: [ "Imagens FLS (*.fls *.bin *.img *.zip)", "Todos (*.*)" ]\n' +
                    '  onAccepted: { var u = file; page._onFilePicked(u); destroy(); }\n' +
                    '  onRejected: { destroy(); }\n' +
                    '}\n';
            var dlg2 = Qt.createQmlObject(src2, page, "DynFD_LABS");
            if (dlg2) { dlg2.open(); return; }
        } catch (e2) {
            console.warn("Qt.labs.platform indisponível:", e2);
        }

        // 3) Fallback SEMPRE abre se os dois acima falharem
        fallback.visible = true;
        fallbackPath.text = "";
        fallbackPath.forceActiveFocus();
    }

    function _onFilePicked(u) {
        imagesModel.addImage(u)
        declaredInfoRequested(u)
        extractPnRequested(u)
        hashRequested(u)
        log(qsTr("Imagem adicionada: %1").arg(u))
    }

    // ======= Fallback embutido (apenas quando nativo indisponível) =======
    Rectangle {
        id: fallback
        visible: false
        anchors.fill: parent
        color: "#80000000"
        z: 999

        Rectangle {
            width: Math.min(parent.width - 80, 560)
            anchors.centerIn: parent
            color: "#ffffff"
            border.color: borderCol; border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Label { text: qsTr("Adicionar imagem FLS"); font.pixelSize: 16; font.bold: true; color: text }
                Label {
                    text: qsTr("Cole o caminho do arquivo (ex.: file:///C:/imagens/arquivo.fls ou /home/user/arquivo.fls)")
                    color: muted; wrapMode: Text.WordWrap
                }
                TextField {
                    id: fallbackPath
                    Layout.fillWidth: true
                    placeholderText: "file:///caminho/para/arquivo.fls"
                    selectByMouse: true
                    onAccepted: btnFallbackAdd.clicked()
                }
                RowLayout {
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }
                    Button {
                        id: btnFallbackCancel
                        text: qsTr("Cancelar")
                        hoverEnabled: true
                        onClicked: fallback.visible = false
                        background: Rectangle {
                            color: btnFallbackCancel.down ? "#e6f1fb" : (btnFallbackCancel.hovered ? "#f3f8fe" : "transparent")
                            border.width: 1; border.color: brand; radius: 0
                        }
                        contentItem: Label { text: btnFallbackCancel.text; color: brand; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }
                    Button {
                        id: btnFallbackAdd
                        text: qsTr("Adicionar")
                        hoverEnabled: true
                        onClicked: {
                            var u = fallbackPath.text
                            if (!u || u.trim().length === 0) return
                            fallback.visible = false
                            _onFilePicked(u)
                        }
                        background: Rectangle { color: btnFallbackAdd.down ? brandLight : (btnFallbackAdd.hovered ? brandLight : brand); radius: 0 }
                        contentItem: Label { text: btnFallbackAdd.text; color: "white"; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }
                }
            }
        }

        MouseArea { anchors.fill: parent; onClicked: fallback.visible = false }
    }

    // ======= Layout principal =======
    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16

        // ---- Esquerda: lista + ações ----
        ColumnLayout {
            Layout.preferredWidth: Math.min(parent.width * 0.35, 420)
            Layout.fillHeight: true
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                // Botão primário (azul) — sem "..."
                Button {
                    id: btnAdd
                    text: qsTr("Adicionar imagem")
                    hoverEnabled: true
                    onClicked: openFilePicker()
                    background: Rectangle {
                        color: btnAdd.down ? brandLight : (btnAdd.hovered ? brandLight : brand)
                        radius: 0
                    }
                    contentItem: Label {
                        text: btnAdd.text
                        color: "white"; font.bold: true
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                }

                // Botão secundário (contornado)
                Button {
                    id: btnRemove
                    text: qsTr("Remover")
                    hoverEnabled: true
                    enabled: imagesModel.count>0 && currentIndex>=0
                    onClicked: {
                        if (currentIndex>=0) {
                            log(qsTr("Imagem removida: %1").arg(imagesModel.get(currentIndex).fileName))
                            imagesModel.removeAtIndex(currentIndex)
                        }
                    }
                    background: Rectangle {
                        color: btnRemove.down ? "#e6f1fb" : (btnRemove.hovered ? "#f3f8fe" : "transparent")
                        border.width: 1
                        border.color: btnRemove.enabled ? brand : "#c7c7c7"
                        radius: 0
                    }
                    contentItem: Label {
                        text: btnRemove.text
                        color: btnRemove.enabled ? brand : "#9ca3af"
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                }

                Item { Layout.fillWidth: true }
                Label { text: qsTr("%1 itens").arg(imagesModel.count); color: muted }
            }

            // Lista
            ListView {
                id: imagesView
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: imagesModel
                delegate: Rectangle {
                    width: ListView.view.width
                    height: 64
                    color: ListView.isCurrentItem ? "#eef6ff" : "transparent"
                    border.color: borderCol
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 10

                        // faixa de status
                        Rectangle {
                            width: 10; Layout.fillHeight: true
                            color: {
                                switch (model.status) {
                                case "verified":      return "#16a34a";
                                case "ready":         return "#f59e0b";
                                case "transferring":  return "#0ea5e9";
                                case "success":       return "#22c55e";
                                case "failed":        return "#ef4444";
                                default:              return "#9ca3af";
                                }
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Label { text: model.pn && model.pn.length ? model.pn : model.fileName; font.bold: true; color: text; elide: Text.ElideRight }
                            Label { text: model.status; color: muted; font.pixelSize: 12 }
                        }

                        ProgressBar {
                            Layout.preferredWidth: 120
                            from: 0; to: 100
                            value: model.progress
                            visible: model.status === "transferring"
                        }
                    }

                    MouseArea { anchors.fill: parent; onClicked: imagesView.currentIndex = index }
                }
            }
        }

        // ---- Direita: detalhes + ações ----
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            RowLayout {
                Layout.fillWidth: true

                Label {
                    text: currentItem() ? (currentItem().pn || currentItem().fileName) : qsTr("Selecione uma imagem")
                    font.pixelSize: 18; font.bold: true; color: text
                }
                Item { Layout.fillWidth: true }

                // Verificar (contornado)
                Button {
                    id: btnVerify
                    text: qsTr("Verificar agora")
                    hoverEnabled: true
                    enabled: !!currentItem()
                    onClicked: {
                        var it = currentItem(); if (!it) return
                        declaredInfoRequested(it.fileUrl)
                        extractPnRequested(it.fileUrl)
                        hashRequested(it.fileUrl)
                        log(qsTr("Verificação solicitada: %1").arg(it.fileName))
                    }
                    background: Rectangle {
                        color: btnVerify.down ? "#e6f1fb" : (btnVerify.hovered ? "#f3f8fe" : "transparent")
                        border.width: 1
                        border.color: btnVerify.enabled ? brand : "#c7c7c7"
                        radius: 0
                    }
                    contentItem: Label {
                        text: btnVerify.text
                        color: btnVerify.enabled ? brand : "#9ca3af"
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                }

                // Transferir (primário)
                Button {
                    id: btnTransfer
                    text: qsTr("Transferir")
                    hoverEnabled: true
                    enabled: !!currentItem() && (currentItem().status === "verified" || currentItem().status === "ready")
                    onClicked: {
                        var it = currentItem(); if (!it) return
                        imagesModel.updateField(it.fileUrl, "status", "transferring")
                        imagesModel.updateField(it.fileUrl, "progress", 0)
                        transferRequested(it)
                        log(qsTr("Transferência iniciada: %1 (PN %2)").arg(it.fileName).arg(it.pn))
                    }
                    background: Rectangle {
                        color: btnTransfer.enabled
                               ? (btnTransfer.down ? brandLight : (btnTransfer.hovered ? brandLight : brand))
                               : "#9ca3af"
                        radius: 0
                    }
                    contentItem: Label {
                        text: btnTransfer.text
                        color: "white"; font.bold: true
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            // Grid de informações
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                rowSpacing: 6; columnSpacing: 12

                Label { text: qsTr("Arquivo:"); color: muted }
                Label { text: currentItem() ? currentItem().fileName : "-"; color: text; elide: Text.ElideRight }

                Label { text: qsTr("PN:"); color: muted }
                Label { text: currentItem() ? (currentItem().pn || qsTr("(extraindo…)")) : "-"; color: text }

                Label { text: qsTr("SHA declarado:"); color: muted }
                Label { text: currentItem() ? (currentItem().shaDeclared || qsTr("(lendo…)")) : "-"; color: text; font.family: "monospace" }

                Label { text: qsTr("SHA calculado:"); color: muted }
                RowLayout {
                    Label { text: currentItem() ? (currentItem().shaComputed || qsTr("(calculando…)")) : "-"; color: text; font.family: "monospace" }
                    Rectangle {
                        width: 10; height: 10
                        color: {
                            if (!currentItem()) return "transparent"
                            var it = currentItem()
                            if (!it.shaDeclared || !it.shaComputed) return "#9ca3af"
                            return (it.shaDeclared.toLowerCase() === it.shaComputed.toLowerCase()) ? "#16a34a" : "#ef4444"
                        }
                    }
                }
            }

            // Compatibilidade
            GroupBox {
                title: qsTr("Compatibilidade declarada (PNs)")
                Layout.fillWidth: true
                Layout.fillHeight: true
                Rectangle { anchors.fill: parent; color: "transparent"; border.color: borderCol; border.width: 1 }
                ListView {
                    anchors.fill: parent; anchors.margins: 8; clip: true
                    model: currentItem()
                           ? (Array.isArray(currentItem().compatList)
                              ? currentItem().compatList
                              : (currentItem().compatList ? [currentItem().compatList] : []))
                           : []
                    delegate: Label { text: modelData; color: text }
                    ScrollBar.vertical: ScrollBar {}
                }
            }

            // Logs
            GroupBox {
                title: qsTr("Logs")
                Layout.fillWidth: true
                Layout.preferredHeight: 120
                Rectangle { anchors.fill: parent; color: "transparent"; border.color: borderCol; border.width: 1 }
                ScrollView {
                    anchors.fill: parent; anchors.margins: 6
                    ListView {
                        id: logsView
                        clip: true
                        model: ListModel { id: logsModel }
                        delegate: Label { text: model.text; color: text; font.family: "monospace" }
                        ScrollBar.vertical: ScrollBar { id: logsBar }
                    }
                }
            }
        }
    }
}
