import QtQuick 2.15
import QtQuick.Controls 2.15

Button {
    id: btnLeftMenu
    text: qsTr("Left Menu Text")

    // CUSTOM PROPERTIES
    property url   btnIconSource: "../../images/svg_images/menu_icon.svg"
    property color btnColorDefault:  "#0167b2"
    property color btnColorMouseOver:"#017cd4"
    property color btnColorClicked:  "#00a1f1"
    property int   iconWidth: 18
    property int   iconHeight: 18
    property color activeMenuColor: "#017cd4"
    property color activeMenuColorRight: "#e5e8ea"
    property bool isActiveMenu: false

    QtObject{
            id: internal

            // MOUSE OVER AND CLICK CHANGE COLOR
            property var dynamicColor: if(btnLeftMenu.down){
                                           btnLeftMenu.down ? btnColorClicked : btnColorDefault
                                       } else {
                                           btnLeftMenu.hovered ? btnColorMouseOver : btnColorDefault
                                       }

        }

    implicitWidth: 250
    implicitHeight: 60
    flat: true

    background: Rectangle{
        id: bgBtn
        color: internal.dynamicColor

        Rectangle{
            anchors{
                top: parent.top
                left: parent.left
                bottom: parent.bottom
            }
            color: activeMenuColor
            width: 3
            visible: isActiveMenu
        }

        Rectangle{
            anchors{
                top: parent.top
                right: parent.right
                bottom: parent.bottom
            }
            color: activeMenuColorRight
            width: 5
            visible: false // isActiveMenu
        }

    }

    contentItem: Item{
        anchors.fill: parent
        id: content
        Image {
            id: iconBtn
            source: btnIconSource
            anchors.leftMargin: 26
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            sourceSize.width: iconWidth
            sourceSize.height: iconHeight
            width: iconWidth
            height: iconHeight
            fillMode: Image.PreserveAspectFit
            visible: true
            antialiasing: true
        }

        Text{
            color: "#ffffff"
            text: btnLeftMenu.text
            font: btnLeftMenu.font
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 75
        }
    }
}
