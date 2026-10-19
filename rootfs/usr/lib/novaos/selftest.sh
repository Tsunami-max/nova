#!/bin/bash
# NovaOS automated self-test. Runs only when the kernel command line contains
# "novaos.selftest" (used by the build's QEMU test harness, never in normal use).
#   novaos.selftest          launch every built-in app and report
#   novaos.selftest=halt     ... then shut down
#   novaos.selftest=reboot   ... then restart
grep -q "novaos.selftest" /proc/cmdline || exit 0
ACTION="$(sed -n 's/.*novaos\.selftest=\([a-z]*\).*/\1/p' /proc/cmdline)"
LOG="$HOME/novaos-selftest.log"

say() {
	echo "SELFTEST: $*" >> "$LOG"
	for t in /dev/ttyS0 /dev/ttyAMA0; do
		[ -e "$t" ] && echo "SELFTEST: $*" | sudo -n tee "$t" >/dev/null 2>&1
	done
	true
}

for _ in $(seq 1 300); do pgrep -x plasmashell >/dev/null && pgrep -x kwin_x11 >/dev/null && break; sleep 1; done
sleep 40
say "BEGIN $(date +%T) kernel=$(uname -r) desktop=$XDG_CURRENT_DESKTOP session=$DESKTOP_SESSION"
say "plasmashell=$(pgrep -x plasmashell >/dev/null && echo running || echo MISSING) kwin=$(pgrep -x kwin_x11 >/dev/null && echo running || echo MISSING)"
say "lnf=$(kreadconfig5 --file kdeglobals --group KDE --key LookAndFeelPackage) colors=$(kreadconfig5 --file kdeglobals --group General --key ColorScheme) icons=$(kreadconfig5 --file kdeglobals --group Icons --key Theme)"
say "compositing=$(kreadconfig5 --file kwinrc --group Compositing --key Enabled) scale=$(kreadconfig5 --file kdeglobals --group KScreen --key ScaleFactor) resolution=$(xrandr | grep '\*' | awk '{print $1}' | head -1)"
say "gl=$(/usr/lib/novaos/gl-check.sh) renderer=$(cat "${XDG_RUNTIME_DIR:-/tmp}/novaos-gl-renderer" 2>/dev/null)"
say "dns: resolv.conf=$(readlink /etc/resolv.conf) resolved=$(systemctl is-active systemd-resolved) servers=$(resolvectl dns 2>/dev/null | tr '\n' ' ' | cut -c1-160)"
say "net: mtu=$(cat /sys/class/net/*/mtu 2>/dev/null | tr '\n' ' ') mtu_probing=$(sysctl -n net.ipv4.tcp_mtu_probing) flathub=$(flatpak remotes --system 2>/dev/null | grep -c flathub)"
say "taskbar launchers: $(grep -h '^launchers=' ~/.config/plasma-org.kde.plasma.desktop-appletsrc 2>/dev/null | head -1 | cut -c1-200)"
say "SHOT desktop"
sleep 8

WP="$(ls /usr/share/wallpapers/Shell/contents/images/* | head -1)"
APPS=(
	"files|dolphin"
	"settings|systemsettings"
	"browser|nova-browser"
	"appstore|plasma-discover"
	"writer|libreoffice --writer"
	"impress|libreoffice --impress"
	"paint|kolourpaint"
	"notes|nova-notes"
	"calculator|kcalc"
	"terminal|konsole"
	"photos|gwenview $WP"
	"texteditor|kwrite"
	"systeminfo|kinfocenter"
	"solitaire|kpat"
	"installer|novaos-install"
)
ignore='^(plasmashell|Desktop.*|Plasma|kwin.*|)$'
pass=0; fail=0
for entry in "${APPS[@]}"; do
	IFS='|' read -r name cmd <<<"$entry"
	before="$(xdotool search --onlyvisible --name "" 2>/dev/null | sort)"
	setsid bash -c "$cmd" >"/tmp/selftest-$name.log" 2>&1 &
	win=""
	for _ in $(seq 1 180); do
		for w in $(comm -13 <(echo "$before") <(xdotool search --onlyvisible --name "" 2>/dev/null | sort)); do
			t="$(xdotool getwindowname "$w" 2>/dev/null)"
			[[ "$t" =~ $ignore ]] && continue
			win="$w"; break
		done
		[ -n "$win" ] && break
		sleep 1
	done
	if [ -n "$win" ]; then
		sleep 10
		title="$(xdotool getwindowname "$win" 2>/dev/null)"
		if [ -z "$title" ]; then
			say "FAIL $name (window vanished) log: $(tail -3 /tmp/selftest-$name.log | tr '\n' ' ' | cut -c1-300)"
			fail=$((fail + 1))
		else
			say "PASS $name window=\"$title\""
			say "SHOT app-$name"
			sleep 6
			pass=$((pass + 1))
		fi
		for w in $(comm -13 <(echo "$before") <(xdotool search --onlyvisible --name "" 2>/dev/null | sort)); do
			[[ "$(xdotool getwindowname "$w" 2>/dev/null)" =~ $ignore ]] && continue
			xdotool windowclose "$w" 2>/dev/null
		done
	else
		say "FAIL $name (no window after 180 s) log: $(tail -3 /tmp/selftest-$name.log | tr '\n' ' ' | cut -c1-300)"
		fail=$((fail + 1))
	fi
	sleep 3
	pkill -f "^${cmd%% *}" 2>/dev/null; pkill -x soffice.bin 2>/dev/null; sudo -n pkill -x calamares 2>/dev/null
	sleep 2
done
say "segfaults: $(sudo -n dmesg | grep -i segfault | tail -3 | tr '\n' ' ')"
say "desktop-alive: plasmashell=$(pgrep -x plasmashell >/dev/null && echo yes || echo no) kwin=$(pgrep -x kwin_x11 >/dev/null && echo yes || echo no)"
say "RESULT pass=$pass fail=$fail"
case "$ACTION" in
	halt)   say "ACTION halt";   sleep 3; qdbus org.kde.ksmserver /KSMServer logout 0 2 2 || systemctl poweroff ;;
	reboot) say "ACTION reboot"; sleep 3; qdbus org.kde.ksmserver /KSMServer logout 0 1 2 || systemctl reboot ;;
esac
say "END"
