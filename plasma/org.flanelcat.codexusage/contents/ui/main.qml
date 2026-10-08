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
    property bool fiveHourAvailable: false
    property bool weeklyAvailable: false
    property bool limitReached: false
    property string lastError: ""
    property var ordinaryUsageAllowed: null

    property real fiveHourRemaining: 100
    property real weeklyRemaining: 100
    property string fiveHourResetDisplay: ""
    property string fiveHourTimeRemaining: ""
    property string weeklyResetDisplay: ""
    property string weeklyTimeRemaining: ""

    preferredRepresentation: compactRepresentation

    function updateUsage() {
        executable.connectSource(
            "$HOME/.local/bin/codex-usage --json"
        )
    }

    function clearAllowance() {
        fiveHourUsed = 0
        weeklyUsed = 0
        fiveHourRemaining = 0
        weeklyRemaining = 0
        fiveHourFresh = false
        weeklyFresh = false
        fiveHourAvailable = false
        weeklyAvailable = false
        fiveHourResetDisplay = ""
        fiveHourTimeRemaining = ""
        weeklyReset = ""
        weeklyResetDisplay = ""
        weeklyTimeRemaining = ""
        limitReached = false
        ordinaryUsageAllowed = null
    }

    function parseUsage(output) {
        try {
            const data = JSON.parse(output)

        if (data.five_hour !== null) {
            fiveHourAvailable = true
            fiveHourUsed = data.five_hour.used_percent
            fiveHourRemaining = data.five_hour.remaining_percent
            fiveHourFresh = data.five_hour.fresh
            fiveHourResetDisplay = data.five_hour.reset_display || ""
            fiveHourTimeRemaining = data.five_hour.time_remaining || ""
        } else {
            fiveHourAvailable = false
            fiveHourUsed = 0
            fiveHourRemaining = 0
            fiveHourFresh = false
            fiveHourResetDisplay = ""
            fiveHourTimeRemaining = ""
        }

        if (data.weekly !== null) {
            weeklyAvailable = true
            weeklyUsed = data.weekly.used_percent
            weeklyRemaining = data.weekly.remaining_percent
            weeklyFresh = data.weekly.fresh
            weeklyReset = data.weekly.resets_at || ""
            weeklyResetDisplay = data.weekly.reset_display || ""
            weeklyTimeRemaining = data.weekly.time_remaining || ""
        } else {
            weeklyAvailable = false
            weeklyUsed = 0
            weeklyRemaining = 0
            weeklyFresh = false
            weeklyReset = ""
            weeklyResetDisplay = ""
            weeklyTimeRemaining = ""
        }

        limitReached = data.limit_reached
        ordinaryUsageAllowed = data.ordinaryUsageAllowed
        lastError = data.allowance_error || ""
        } catch (error) {
            clearAllowance()
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
                root.clearAllowance()
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
                "5h " + (root.fiveHourAvailable && root.fiveHourFresh
                    ? root.fiveHourUsed.toFixed(0) + "%"
                    : "?") +
                " | W " + (root.weeklyAvailable && root.weeklyFresh
                    ? root.weeklyUsed.toFixed(0) + "%"
                    : "?")

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
            visible: root.fiveHourAvailable && root.fiveHourFresh
            from: 0
            to: 100
            value: root.fiveHourUsed
        }

        PlasmaComponents3.Label {
            visible: root.fiveHourAvailable && root.fiveHourFresh
            text:
                root.fiveHourUsed.toFixed(0) +
                "% used — " +
                root.fiveHourRemaining.toFixed(0) +
                "% remaining"
        }

        PlasmaComponents3.Label {
            visible: root.fiveHourAvailable && root.fiveHourTimeRemaining !== ""
            text: "Resets in " + root.fiveHourTimeRemaining
        }

        PlasmaComponents3.Label {
            visible: root.fiveHourAvailable && root.fiveHourResetDisplay !== ""
            text: root.fiveHourResetDisplay
            opacity: 0.7
        }

        PlasmaComponents3.Label {
            visible: root.fiveHourAvailable && !root.fiveHourFresh
            text: "New window — awaiting fresh Codex activity"
            opacity: 0.7
        }

        PlasmaComponents3.Label {
            visible: !root.fiveHourAvailable
            text: "Allowance unavailable"
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
            visible: root.weeklyAvailable && root.weeklyFresh
            from: 0
            to: 100
            value: root.weeklyUsed
        }

        PlasmaComponents3.Label {
            visible: root.weeklyAvailable && root.weeklyFresh
            text:
                root.weeklyUsed.toFixed(0) +
                "% used — " +
                root.weeklyRemaining.toFixed(0) +
                "% remaining"
        }

        PlasmaComponents3.Label {
            visible: root.weeklyAvailable && root.weeklyTimeRemaining !== ""
            text: "Resets in " + root.weeklyTimeRemaining
        }

        PlasmaComponents3.Label {
            visible: root.weeklyAvailable && root.weeklyResetDisplay !== ""
            text: root.weeklyResetDisplay
            opacity: 0.7
        }

        PlasmaComponents3.Label {
            visible: root.weeklyAvailable && !root.weeklyFresh
            text: "New window — awaiting fresh Codex activity"
            opacity: 0.7
        }

        PlasmaComponents3.Label {
            visible: !root.weeklyAvailable
            text: "Allowance unavailable"
            opacity: 0.7
        }

        PlasmaComponents3.Label {
            visible: root.ordinaryUsageAllowed !== null
            text: root.ordinaryUsageAllowed
                ? "Ordinary usage allowed"
                : "Ordinary usage not allowed"
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
