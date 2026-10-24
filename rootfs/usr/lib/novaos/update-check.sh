#!/bin/bash
# At login (installed system only): tell the user when a newer NovaOS exists.
# One-time: add the Log out / Power buttons to taskbars made before NovaOS had them.
if [ "$(kreadconfig5 --file novaosrc --group Migrations --key LeaveButtons)" != done ]; then
	sleep 15
	qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript "
var ps = panels(); var n = 0; var main = null;
for (var i = 0; i < ps.length; i++) { n += ps[i].widgets('org.kde.plasma.lock_logout').length;
  if (ps[i].widgets('org.kde.plasma.digitalclock').length) main = ps[i]; }
if (!n && main) { var w = main.addWidget('org.kde.plasma.lock_logout'); w.currentConfigGroup = ['General'];
  w.writeConfig('show_requestLogout', true); w.writeConfig('show_requestShutDown', true);
  w.writeConfig('show_lockScreen', false); w.writeConfig('show_switchUser', false);
  w.writeConfig('show_suspendToDisk', false); w.writeConfig('show_suspendToRam', false);
  w.writeConfig('show_requestReboot', false); print('added'); }" 2>/dev/null | grep -q added && {
		qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript "var ps = panels(); for (var i = 0; i < ps.length; i++) { var p = ps[i]; var l = p.widgets('org.kde.plasma.lock_logout'); var c = p.widgets('org.kde.plasma.digitalclock'); if (!l.length || !c.length) continue; p.currentConfigGroup = ['General']; var o = String(p.readConfig('AppletOrder', '')).split(';'); var lid = String(l[0].id), cid = String(c[0].id); o = o.filter(function (x) { return x != lid && x != ''; }); o.splice(o.indexOf(cid) + 1, 0, lid); p.writeConfig('AppletOrder', o.join(';')); }" >/dev/null 2>&1
		qdbus org.kde.plasmashell /MainApplication quit >/dev/null 2>&1
		sleep 3
		pgrep -x plasmashell >/dev/null || (setsid kstart5 plasmashell >/dev/null 2>&1 &)
	}
	kwriteconfig5 --file novaosrc --group Migrations --key LeaveButtons done
fi
[ -d /run/casper ] && exit 0
grep -qw boot=casper /proc/cmdline && exit 0
[ "$(kreadconfig5 --file novaosrc --group Update --key Check --default true)" = false ] && exit 0
sleep 90
. /etc/novaos/build 2>/dev/null
latest="$(curl -fsS --max-time 20 https://api.github.com/repos/Tsunami-max/nova/commits/main 2>/dev/null \
	| sed -n 's/^  "sha": "\([0-9a-f]*\)".*/\1/p' | head -1)"
[ -n "$latest" ] && [ "$latest" != "${COMMIT:-}" ] || exit 0
[ "$(kreadconfig5 --file novaosrc --group Update --key Skipped)" = "$latest" ] && exit 0
a="$(notify-send -a "NovaOS" -i system-software-update -t 0 -A update="Update now" -A later="Later" \
	"A new NovaOS is ready" "Update in place — your files, apps and logins stay." 2>/dev/null)"
case "$a" in
	update) exec nova-update ;;
	later) kwriteconfig5 --file novaosrc --group Update --key Skipped "$latest" ;;
esac
