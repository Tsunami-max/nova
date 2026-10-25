// NovaOS Mac: top bar (Start, app menu, tray, clock) + centred dock at the bottom.
var desktopsArray = desktopsForActivity(currentActivity());
for (var j = 0; j < desktopsArray.length; j++) {
    desktopsArray[j].wallpaperPlugin = "org.kde.image";
    desktopsArray[j].currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    desktopsArray[j].writeConfig("Image", "file:///usr/share/wallpapers/Next/");
}

var top = new Panel;
top.location = "top";
top.height = Math.round(gridUnit * 1.6);
var kickoff = top.addWidget("org.kde.plasma.kickoff");
kickoff.currentConfigGroup = ["Shortcuts"];
kickoff.writeConfig("global", "Alt+F1");
kickoff.currentConfigGroup = ["General"];
kickoff.writeConfig("icon", "/usr/share/icons/NovaOS/scalable/apps/novaos-start.svg");
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
top.addWidget("org.kde.plasma.appmenu");
top.addWidget("org.kde.plasma.panelspacer");
top.addWidget("org.kde.plasma.systemtray");
var clock = top.addWidget("org.kde.plasma.digitalclock");
clock.currentConfigGroup = ["Appearance"];
clock.writeConfig("showDate", "true");
// NovaOS: one-click Log out and Power buttons.
var leave = top.addWidget("org.kde.plasma.lock_logout");
leave.currentConfigGroup = ["General"];
leave.writeConfig("show_lockScreen", "false");
leave.writeConfig("show_switchUser", "false");
leave.writeConfig("show_suspendToDisk", "false");
leave.writeConfig("show_suspendToRam", "false");
leave.writeConfig("show_requestReboot", "false");
leave.writeConfig("show_requestLogout", "true");
leave.writeConfig("show_requestShutDown", "true");

var dock = new Panel;
dock.location = "bottom";
dock.height = Math.round(gridUnit * 3.2);
dock.alignment = "center";
var geo = screenGeometry(dock.screen);
dock.minimumLength = Math.round(gridUnit * 27);
dock.maximumLength = Math.round(gridUnit * 27);
var tasks = dock.addWidget("org.kde.plasma.icontasks");
tasks.currentConfigGroup = ["General"];
tasks.writeConfig("launchers", [
    "applications:org.kde.dolphin.desktop",
    "applications:PLACEHOLDER_BROWSER",
    "applications:org.kde.discover.desktop",
    "applications:libreoffice-writer.desktop",
    "applications:org.kde.kolourpaint.desktop",
    "applications:org.kde.konsole.desktop",
    "applications:systemsettings.desktop"
]);
tasks.writeConfig("iconSpacing", "2");
dock.addWidget("org.kde.plasma.marginsseparator");
dock.addWidget("org.kde.plasma.trash");
