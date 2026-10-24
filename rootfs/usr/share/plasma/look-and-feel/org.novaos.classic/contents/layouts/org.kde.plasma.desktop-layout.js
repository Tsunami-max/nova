// NovaOS Classic: full-width bottom taskbar, Start on the left, app names on buttons.
var desktopsArray = desktopsForActivity(currentActivity());
for (var j = 0; j < desktopsArray.length; j++) {
    desktopsArray[j].wallpaperPlugin = "org.kde.image";
    desktopsArray[j].currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    desktopsArray[j].writeConfig("Image", "file:///usr/share/wallpapers/Altai/");
}
var panel = new Panel;
panel.location = "bottom";
panel.height = 2 * Math.floor(gridUnit * 2.3 / 2);
var kickoff = panel.addWidget("org.kde.plasma.kickoff");
kickoff.currentConfigGroup = ["Shortcuts"];
kickoff.writeConfig("global", "Alt+F1");
kickoff.currentConfigGroup = ["General"];
kickoff.writeConfig("icon", "novaos-start");
kickoff.writeConfig("favorites", [
    "preferred://browser",
    "libreoffice-writer.desktop",
    "libreoffice-impress.desktop",
    "libreoffice-calc.desktop",
    "org.kde.kolourpaint.desktop",
    "org.kde.discover.desktop",
    "org.kde.dolphin.desktop",
    "org.kde.gwenview.desktop",
    "vlc.desktop",
    "novaos-notes.desktop",
    "org.kde.kcalc.desktop",
    "org.kde.kpat.desktop",
    "org.kde.konsole.desktop",
    "novaos-style.desktop",
    "systemsettings.desktop"
]);
var tasks = panel.addWidget("org.kde.plasma.taskmanager");
tasks.currentConfigGroup = ["General"];
tasks.writeConfig("launchers", [
    "applications:org.kde.dolphin.desktop",
    "applications:PLACEHOLDER_BROWSER",
    "applications:org.kde.discover.desktop"
]);
panel.addWidget("org.kde.plasma.systemtray");
var clock = panel.addWidget("org.kde.plasma.digitalclock");
clock.currentConfigGroup = ["Appearance"];
clock.writeConfig("showDate", "true");
// NovaOS: one-click Log out and Power buttons.
var leave = panel.addWidget("org.kde.plasma.lock_logout");
leave.currentConfigGroup = ["General"];
leave.writeConfig("show_lockScreen", "false");
leave.writeConfig("show_switchUser", "false");
leave.writeConfig("show_suspendToDisk", "false");
leave.writeConfig("show_suspendToRam", "false");
leave.writeConfig("show_requestReboot", "false");
leave.writeConfig("show_requestLogout", "true");
leave.writeConfig("show_requestShutDown", "true");
panel.addWidget("org.kde.plasma.showdesktop");
