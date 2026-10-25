/* NovaOS Live wallpaper settings. SPDX-License-Identifier: MIT */
import QtQuick 2.15
import QtQuick.Controls 2.15 as QQC2
import QtQuick.Layouts 1.15
import QtQuick.Dialogs 1.3 as QtDialogs
import org.kde.kirigami 2.5 as Kirigami

Kirigami.FormLayout {
    id: root
    twinFormLayouts: parentLayout
    property alias formLayout: root

    property string cfg_Mode
    property string cfg_Effect
    property string cfg_Palette
    property string cfg_Image
    property bool cfg_SlowZoom
    property real cfg_Speed
    property int cfg_Fps
    property real cfg_Quality
    property bool cfg_PauseWhenCovered
    property int cfg_MaxCpu

    function indexOf(model, value) {
        for (var i = 0; i < model.length; i++)
            if (model[i].value == value) return i;
        return 0;
    }

    readonly property var modes: [
        { text: "Aurora (northern lights)", value: "aurora" },
        { text: "Nebula (space, shooting stars)", value: "nebula" },
        { text: "Waves", value: "waves" },
        { text: "Lava lamp", value: "lava" },
        { text: "Colour flow", value: "flow" },
        { text: "My picture + effect", value: "picture" }
    ]
    readonly property var effectList: [
        { text: "None", value: "none" },
        { text: "Snow", value: "snow" },
        { text: "Rain", value: "rain" },
        { text: "Fireflies", value: "fireflies" },
        { text: "Twinkling stars", value: "stars" },
        { text: "Light rays", value: "rays" }
    ]
    readonly property var paletteList: [
        { text: "NovaOS", value: "nova" }, { text: "Aurora", value: "aurora" },
        { text: "Ocean", value: "ocean" }, { text: "Sunset", value: "sunset" },
        { text: "Forest", value: "forest" }, { text: "Silver", value: "mono" }
    ]
    readonly property var fpsList: [
        { text: "10 – lightest", value: 10 }, { text: "15 – recommended", value: 15 },
        { text: "24 – smoother", value: 24 }, { text: "30 – smoothest", value: 30 }
    ]
    readonly property var qualityList: [
        { text: "Light (fastest)", value: 0.2 }, { text: "Balanced", value: 0.3 },
        { text: "Sharp", value: 0.45 }, { text: "Very sharp (needs graphics acceleration)", value: 0.7 }
    ]
    readonly property var cpuList: [
        { text: "10 % – lightest", value: 10 }, { text: "15 % – recommended", value: 15 },
        { text: "20 %", value: 20 }
    ]
    readonly property var speedList: [
        { text: "Slow", value: 0.5 }, { text: "Normal", value: 1.0 }, { text: "Fast", value: 1.8 }
    ]

    QQC2.ComboBox {
        Kirigami.FormData.label: "Wallpaper:"
        textRole: "text"
        model: root.modes
        currentIndex: root.indexOf(root.modes, root.cfg_Mode)
        onActivated: root.cfg_Mode = root.modes[index].value
    }
    RowLayout {
        Kirigami.FormData.label: "Picture:"
        visible: root.cfg_Mode === "picture"
        QQC2.TextField {
            Layout.preferredWidth: Kirigami.Units.gridUnit * 16
            text: root.cfg_Image.replace("file://", "")
            placeholderText: "NovaOS picture"
            readOnly: true
        }
        QQC2.Button {
            text: "Choose…"
            icon.name: "document-open"
            onClicked: fileDialog.open()
        }
        QQC2.Button {
            icon.name: "edit-clear"
            visible: root.cfg_Image !== ""
            onClicked: root.cfg_Image = ""
        }
    }
    QQC2.CheckBox {
        visible: root.cfg_Mode === "picture"
        text: "Slow zoom (gentle movement)"
        checked: root.cfg_SlowZoom
        onToggled: root.cfg_SlowZoom = checked
    }
    QQC2.ComboBox {
        Kirigami.FormData.label: "Effect on top:"
        textRole: "text"
        model: root.effectList
        currentIndex: root.indexOf(root.effectList, root.cfg_Effect)
        onActivated: root.cfg_Effect = root.effectList[index].value
    }
    QQC2.ComboBox {
        Kirigami.FormData.label: "Colours:"
        visible: root.cfg_Mode !== "picture"
        textRole: "text"
        model: root.paletteList
        currentIndex: root.indexOf(root.paletteList, root.cfg_Palette)
        onActivated: root.cfg_Palette = root.paletteList[index].value
    }
    QQC2.ComboBox {
        Kirigami.FormData.label: "Speed:"
        textRole: "text"
        model: root.speedList
        currentIndex: root.indexOf(root.speedList, root.cfg_Speed)
        onActivated: root.cfg_Speed = root.speedList[index].value
    }
    QQC2.ComboBox {
        Kirigami.FormData.label: "Frames per second:"
        textRole: "text"
        model: root.fpsList
        currentIndex: root.indexOf(root.fpsList, root.cfg_Fps)
        onActivated: root.cfg_Fps = root.fpsList[index].value
    }
    QQC2.ComboBox {
        Kirigami.FormData.label: "Detail:"
        textRole: "text"
        model: root.qualityList
        currentIndex: root.indexOf(root.qualityList, root.cfg_Quality)
        onActivated: root.cfg_Quality = root.qualityList[index].value
    }
    QQC2.ComboBox {
        Kirigami.FormData.label: "Max. processor use:"
        textRole: "text"
        model: root.cpuList
        currentIndex: root.indexOf(root.cpuList, root.cfg_MaxCpu)
        onActivated: root.cfg_MaxCpu = root.cpuList[index].value
    }
    QQC2.CheckBox {
        text: "Pause while a window fills the screen (saves processor)"
        checked: root.cfg_PauseWhenCovered
        onToggled: root.cfg_PauseWhenCovered = checked
    }
    QQC2.Label {
        Layout.maximumWidth: Kirigami.Units.gridUnit * 24
        wrapMode: Text.WordWrap
        opacity: 0.7
        text: "The wallpaper never uses more than the processor limit: when drawing costs more (for example on a big screen without graphics acceleration), it automatically shows fewer frames per second."
    }

    QtDialogs.FileDialog {
        id: fileDialog
        title: "Choose a picture"
        folder: shortcuts.pictures
        nameFilters: ["Pictures (*.jpg *.jpeg *.png *.webp)"]
        onAccepted: root.cfg_Image = fileDialog.fileUrl.toString()
    }
}
