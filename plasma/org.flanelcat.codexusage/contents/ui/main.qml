import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.plasma5support as Plasma5Support

PlasmoidItem {
    id: root

    property real fiveHourUsed: 0
    property real weeklyUsed: 0
    property string weeklyReset: ""
    property bool fiveHourFresh: false
    property bool weeklyFresh: false
    property bool limitReached: false
    property string lastError: ""

    property real fiveHourRemaining: 100
    property real weeklyRemaining: 100
    property string weeklyResetDisplay: ""
    property string weeklyTimeRemaining: ""

    preferredRepresentation: compactRepresentation

    function updateUsage() {
        executable.connectSource(
            "$HOME/.local/bin/codex-usage --json"
        )
    }

    function parseUsage(output) {
        try {
            const data = JSON.parse(output)

        if (data.five_hour) {
            fiveHourUsed = data.five_hour.used_percent
            fiveHourRemaining = data.five_hour.remaining_percent
            fiveHourFresh = data.five_hour.fresh
        }

        if (data.weekly) {
            weeklyUsed = data.weekly.used_percent
            weeklyRemaining = data.weekly.remaining_percent
            weeklyFresh = data.weekly.fresh
            weeklyReset = data.weekly.resets_at || ""
            weeklyResetDisplay = data.weekly.reset_display || ""
            weeklyTimeRemaining = data.weekly.time_remaining || ""
        }
            limitReached = data.limit_reached
            lastError = ""
        } catch (error) {
            lastError = "Could not parse codex-usage output"
            console.log("Codex Usage:", error)
        }
    }

    Plasma5Support.DataSource {
        id: executable

        engine: "executable"

        onNewData: function(sourceName, data) {
            disconnectSource(sourceName)

            if (data["exit code"] !== 0) {
                root.lastError =
                    "codex-usage exited with code " +
                    data["exit code"]
                return
            }

            root.parseUsage(data.stdout)
        }
    }

    Timer {
        interval: 30000
        running: true
        repeat: true

        onTriggered: root.updateUsage()
    }

    Component.onCompleted: updateUsage()

    compactRepresentation: MouseArea {
        implicitWidth: compactLabel.implicitWidth + 20
        implicitHeight: compactLabel.implicitHeight + 8

        Layout.minimumWidth: implicitWidth
        Layout.preferredWidth: implicitWidth

        onClicked: root.expanded = !root.expanded

        PlasmaComponents3.Label {
            id: compactLabel

            anchors.centerIn: parent

            text:
                "5h " + root.fiveHourUsed.toFixed(0) +
                "% | W " + root.weeklyUsed.toFixed(0) + "%"

            textFormat: Text.PlainText
            elide: Text.ElideNone

            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }
    fullRepresentation: ColumnLayout {
        implicitWidth: 380
        implicitHeight: 300
        spacing: 8

        PlasmaComponents3.Label {
            text: "Codex Usage"
            font.bold: true
            font.pointSize: 14
        }

        Item {
            Layout.preferredHeight: 4
    	}

    	PlasmaComponents3.Label {
       	    text: "5-hour allowance"
            font.bold: true
        }

        PlasmaComponents3.ProgressBar {
            Layout.fillWidth: true
            from: 0
            to: 100
            value: root.fiveHourUsed
        }

        PlasmaComponents3.Label {
            text:
                root.fiveHourUsed.toFixed(0) +
                "% used — " +
                root.fiveHourRemaining.toFixed(0) +
                "% remaining"
        }

        PlasmaComponents3.Label {
            visible: !root.fiveHourFresh
            text: "New window — awaiting fresh Codex activity"
            opacity: 0.7
        }

        Item {
            Layout.preferredHeight: 8
        }

        PlasmaComponents3.Label {
            text: "Weekly allowance"
            font.bold: true
        }

        PlasmaComponents3.ProgressBar {
            Layout.fillWidth: true
            from: 0
            to: 100
            value: root.weeklyUsed
        }

        PlasmaComponents3.Label {
            text:
                root.weeklyUsed.toFixed(0) +
                "% used — " +
                root.weeklyRemaining.toFixed(0) +
                "% remaining"
        }

        PlasmaComponents3.Label {
            visible: root.weeklyTimeRemaining !== ""
            text: "Resets in " + root.weeklyTimeRemaining
        }

        PlasmaComponents3.Label {
            visible: root.weeklyResetDisplay !== ""
            text: root.weeklyResetDisplay
            opacity: 0.7
        }

        Item {
            Layout.preferredHeight: 8
        }

        PlasmaComponents3.Label {
            visible: root.limitReached
            text: "LIMIT REACHED"
            font.bold: true
        }

        PlasmaComponents3.Label {
            visible: root.lastError !== ""
            text: root.lastError
        }
    }
}
