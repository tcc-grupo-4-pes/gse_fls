import QtQuick
import QtQuick.Window
import QtQuick.Controls 2.15
import "qml/controls"
import QtQuick.Layouts 2.15
import Qt5Compat.GraphicalEffects

Window {
    id: mainWindow
    width: 1000
    height: 580
    minimumWidth: 800
    minimumHeight: 500
    visible: true
    color: "#00ffffff"
    title: qsTr("GSE")

    // Remove title bar
    flags: Qt.Window | Qt.FramelessWindowHint

    // Properties
    property int windowStatus: 0

    // Internal functions
    QtObject{
        id: internal

        function maximizeRestore(){
            if(windowStatus === 0){
                windowStatus = 1
                mainWindow.showMaximized()
                btnMaximizeRestore.btnIconSource = "../../images/svg_images/restore_icon.svg"
                // Resize visibility
                resizeLeft.visible = false
                resizeRight.visible = false
                resizeBottom.visible = false
                resizeTop.visible = false
                resizeBottomRight.visible = false
            }
            else{
                windowStatus = 0
                mainWindow.showNormal()
                btnMaximizeRestore.btnIconSource = "../../images/svg_images/maximize_icon.svg"
                // Resize visibility
                resizeLeft.visible = true
                resizeRight.visible = true
                resizeBottom.visible = true
                resizeTop.visible = true
                resizeBottomRight.visible = true
            }
        }

        function setSection(section) {
            switch (section) {
            case "login":
                labelRightInfo.text = qsTr("| ENTRAR")
                labelTopInfo.text   = qsTr("Acesse o GSE com suas credenciais.")
                labelTopInfo1.text  = qsTr("Autenticação de usuário")
                break
            case "upload":
                labelRightInfo.text = qsTr("| UPLOAD")
                labelTopInfo.text   = qsTr("Gerencie imagens FLS para transferência.")
                labelTopInfo1.text  = qsTr("Seleção e verificação de imagens")
                break
            default:
                // fallback
                labelRightInfo.text = qsTr("| GSE")
                labelTopInfo.text   = qsTr("Application description")
                labelTopInfo1.text  = qsTr("Application description")
            }
        }

    }

    Rectangle {
        id: bg
        color: "#e5e8ea"
        border.color: "#d9e4ec"
        border.width: 1
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.leftMargin: 0
        anchors.rightMargin: 0
        anchors.topMargin: 0
        anchors.bottomMargin: 0

        Rectangle {
            id: appContainer
            color: "#00ffffff"
            anchors.fill: parent
            anchors.leftMargin: 0
            anchors.rightMargin: 0
            anchors.topMargin: 0
            anchors.bottomMargin: 0

            Rectangle {
                id: topBar
                height: 60
                color: "#0164ac"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.leftMargin: 0
                anchors.rightMargin: 0
                anchors.topMargin: 0

                ToggleButton{
                    btnColorDefault: "#0164ac"
                    onClicked: animationMenu.running = true
                }

                Rectangle {
                    id: topBarDescription
                    height: 25
                    color: "#017cd4"
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: 70
                    anchors.rightMargin: 0
                    anchors.bottomMargin: 0

                    Label {
                        id: labelTopInfo
                        color: "#f9f9f9"
                        text: qsTr("Application description")
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 300
                        verticalAlignment: Text.AlignVCenter
                    }

                    Label {
                        id: labelRightInfo
                        color: "#ffffff"
                        text: qsTr("| ENTRAR")
                        anchors.left: labelTopInfo.right
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.leftMargin: 0
                        anchors.rightMargin: 10
                        anchors.topMargin: 0
                        anchors.bottomMargin: 0
                        horizontalAlignment: Text.AlignRight
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                Rectangle {
                    id: titleBar
                    height: 35
                    color: "#00ffffff"
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.leftMargin: 70
                    anchors.rightMargin: 105
                    anchors.topMargin: 0

                    DragHandler {
                        onActiveChanged: if(active){
                                             mainWindow.startSystemMove()
                                         }
                    }

                    Image {
                        id: iconApp
                        width: 33
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.leftMargin: 5
                        anchors.topMargin: 8
                        anchors.bottomMargin: 8
                        source: "images/svg_images/ERJ.D.svg"
                        mipmap: true
                        focus: false
                        antialiasing: true
                        fillMode: Image.PreserveAspectFit
                    }

                    Label {
                        id: label
                        color: "#ffffff"
                        text: qsTr("GSE - FLS")
                        anchors.left: iconApp.right
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.leftMargin: 5
                        verticalAlignment: Text.AlignVCenter
                        font.pointSize: 10
                        font.bold: true
                    }
                }

                Row {
                    id: rowBtns
                    width: 105
                    height: 35
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.rightMargin: 0
                    anchors.topMargin: 0

                    TopBarButton{
                        id: btnMinimize
                        btnColorDefault: "#0164ac"
                        onClicked: mainWindow.showMinimized()
                    }

                    TopBarButton {
                        id: btnMaximizeRestore
                        btnColorDefault: "#0164ac"
                        btnIconSource: "../../images/svg_images/maximize_icon.svg"
                        onClicked: internal.maximizeRestore()
                    }

                    TopBarButton {
                        id: btnClose
                        btnColorDefault: "#0164ac"
                        btnColorClicked: "#f05252"
                        btnColorMouseOver: "#f5033a"
                        btnIconSource: "../../images/svg_images/close_icon.svg"
                        onClicked: mainWindow.close()
                    }
                }
            }

            Rectangle {
                id: content
                color: "#00ffffff"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: topBar.bottom
                anchors.bottom: parent.bottom
                anchors.topMargin: 0

                Rectangle {
                    id: leftMenu
                    width: 70
                    color: "#0164ac"
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: 0
                    anchors.topMargin: 0
                    anchors.bottomMargin: 0

                    PropertyAnimation{
                        id: animationMenu
                        target: leftMenu
                        property: "width"
                        to: if(leftMenu.width === 70) return 175; else return 70
                        duration: 500
                        easing.type: Easing.InOutQuint
                    }

                    Column {
                        id: columnMenus
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.leftMargin: 0
                        anchors.rightMargin: 0
                        anchors.topMargin: 0
                        anchors.bottomMargin: 90

                        LeftMenuBtn {
                            id: btnLogin
                            text: qsTr("Entrar")
                            anchors.left: parent.left
                            anchors.leftMargin: 0
                            isActiveMenu: true
                            width: leftMenu.width
                            btnIconSource: "../../images/svg_images/home_icon.svg"
                            btnColorDefault: "#0164ac"
                            onClicked: {
                                btnLogin.isActiveMenu = true
                                btnUpload.isActiveMenu = false
                                stackView.push(Qt.resolvedUrl("qml/pages/loginPage.qml"))
                                internal.setSection("login")
                            }
                        }

                        LeftMenuBtn {
                            id: btnUpload
                            y: 60
                            width: leftMenu.width
                            text: qsTr("Upload")
                            anchors.left: parent.left
                            anchors.leftMargin: 0
                            btnIconSource: "../../images/png_images/upload_icon.png"
                            btnColorDefault: "#0164ac"
                            onClicked: {
                                btnLogin.isActiveMenu = false
                                btnUpload.isActiveMenu = true
                                stackView.push(Qt.resolvedUrl("qml/pages/uploadPage.qml"))
                                internal.setSection("upload")
                            }
                        }
                    }
                }

                Rectangle {
                    id: contentPage
                    color: "#e5e8ea"
                    anchors.left: leftMenu.right
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: 0
                    anchors.bottomMargin: 25
                    clip: true

                    StackView {
                    id: stackView
                    anchors.fill: parent
                    Component.onCompleted:{
                        stackView.push("qml/pages/loginPage.qml")
                        internal.setSection("login")
                        }
                    }
                    // Loader{
                    //     id: pagesView
                    //     anchors.fill: parent
                    //     source: Qt.resolvedUrl("qml/pages/loginPage.qml")
                    // }
                }

                Rectangle {
                    id: rectangle
                    y: 280
                    color: "#017cd4"
                    anchors.left: leftMenu.right
                    anchors.right: parent.right
                    anchors.top: contentPage.bottom
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: 0
                    anchors.rightMargin: 0
                    anchors.topMargin: 0
                    anchors.bottomMargin: 0

                    Label {
                        id: labelTopInfo1
                        x: -60
                        y: -473
                        color: "#f9f9f9"
                        text: qsTr("Application description")
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.leftMargin: 10
                        anchors.rightMargin: 845
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }

    DropShadow{
        anchors.fill: bg
        horizontalOffset: 0
        verticalOffset: 0
        radius: 10
        samples: 16
        color: "#80000000"
        source: bg
        z: 0
    }

    MouseArea {
        id: resizeLeft
        width: 10
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.leftMargin: 0
        anchors.topMargin: 10
        anchors.bottomMargin: 10
        cursorShape: Qt.SizeHorCursor

        DragHandler{
            target: null
            onActiveChanged: if(active) { mainWindow.startSystemResize(Qt.LeftEdge) }
        }
    }

    MouseArea {
        id: resizeRight
        width: 10
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.rightMargin: 0
        anchors.topMargin: 10
        anchors.bottomMargin: 10
        cursorShape: Qt.SizeHorCursor

        DragHandler{
            target: null
            onActiveChanged: if(active) { mainWindow.startSystemResize(Qt.RightEdge) }
        }
    }

    MouseArea {
        id: resizeBottom
        height: 10
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        anchors.bottomMargin: 0
        cursorShape: Qt.SizeVerCursor

        DragHandler{
            target: null
            onActiveChanged: if(active) { mainWindow.startSystemResize(Qt.BottomEdge) }
        }
    }

    MouseArea {
        id: resizeTop
        height: 10
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        anchors.topMargin: 0
        cursorShape: Qt.SizeVerCursor

        DragHandler{
            target: null
            onActiveChanged: if(active) { mainWindow.startSystemResize(Qt.TopEdge) }
        }
    }

    MouseArea {
        id: resizeBottomRight
        width: 25
        height: 25
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 0
        anchors.bottomMargin: 0
        cursorShape: Qt.SizeFDiagCursor

        DragHandler{
            target: null
            onActiveChanged: if(active){
                                 mainWindow.startSystemResize(Qt.RightEdge | Qt.BottomEdge)
                             }
        }

        Image {
            id: resizeImage
            opacity: 1.00
            anchors.fill: parent
            anchors.leftMargin: 5
            anchors.topMargin: 5
            source: "images/svg_images/resize_icon.svg"
            sourceSize.height: 16
            sourceSize.width: 16
            fillMode: Image.PreserveAspectFit
            antialiasing: false
        }
    }
}
