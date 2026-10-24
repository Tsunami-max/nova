// NovaOS login splash: logo, wordmark and a soft progress bar on a
// deep blue gradient. Based on the structure of Plasma's Breeze splash.
import QtQuick 2.15
import org.kde.plasma.core 2.0 as PlasmaCore

Rectangle {
    id: root
    property int stage
    gradient: Gradient {
        GradientStop { position: 0.0; color: "#0b0f24" }
        GradientStop { position: 1.0; color: "#1b1046" }
    }

    onStageChanged: {
        if (stage == 2) {
            introAnimation.running = true;
        }
        progress.width = Math.min(1, stage / 6) * track.width;
    }

    Item {
        id: content
        anchors.fill: parent
        opacity: 0

        Image {
            id: glow
            anchors.centerIn: logo
            width: logo.width * 2.2
            height: width
            source: "images/logo.svg"
            sourceSize.width: width
            sourceSize.height: height
            opacity: 0.12
        }
        Image {
            id: logo
            readonly property real size: PlasmaCore.Units.gridUnit * 7
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            anchors.verticalCenterOffset: -PlasmaCore.Units.gridUnit * 2
            source: "images/logo.svg"
            sourceSize.width: size
            sourceSize.height: size
        }
        Image {
            id: word
            anchors.top: logo.bottom
            anchors.topMargin: PlasmaCore.Units.gridUnit * 1.5
            anchors.horizontalCenter: parent.horizontalCenter
            source: "images/wordmark.png"
            height: PlasmaCore.Units.gridUnit * 2.2
            fillMode: Image.PreserveAspectFit
            smooth: true
        }
        Rectangle {
            id: track
            anchors.top: word.bottom
            anchors.topMargin: PlasmaCore.Units.gridUnit * 2.5
            anchors.horizontalCenter: parent.horizontalCenter
            width: PlasmaCore.Units.gridUnit * 12
            height: 4
            radius: 2
            color: "#26ffffff"
            Rectangle {
                id: progress
                height: parent.height
                radius: 2
                width: 0
                color: "#8b96ff"
                Behavior on width { NumberAnimation { duration: 400; easing.type: Easing.OutCubic } }
            }
        }
    }

    OpacityAnimator {
        id: introAnimation
        running: false
        target: content
        from: 0
        to: 1
        duration: 600
        easing.type: Easing.InOutQuad
    }
}
