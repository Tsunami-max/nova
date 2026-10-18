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

# wait for the desktop to be fully up
for _ in $(seq 1 120); do pgrep -x xfdesktop >/dev/null && pgrep -x xfce4-panel >/dev/null && break; sleep 1; done
sleep 25
say "BEGIN $(date +%T) kernel=$(uname -r)"
say "theme=$(xfconf-query -c xsettings -p /Net/ThemeName) icons=$(xfconf-query -c xsettings -p /Net/IconThemeName) wm=$(xfconf-query -c xfwm4 -p /general/theme)"
say "wallpaper=$(xfconf-query -c xfce4-desktop -l -v | grep last-image | head -1 | awk '{print $2}')"
say "picom=$(pgrep -x picom >/dev/null && echo running || echo stopped) resolution=$(xrandr | grep '\*' | awk '{print $1}' | head -1)"
say "SHOT desktop"
sleep 6

# name | command | window-class regex
APPS=(
	"files|thunar|thunar"
	"settings|nova-settings|settings_app|nova"
	"browser|exo-open --launch WebBrowser|browser"
	"notes|nova-notes|notes_app|nova"
	"calculator|gnome-calculator|calculator"
	"terminal|xfce4-terminal|xfce4-terminal"
	"imageviewer|ristretto /usr/share/backgrounds/novaos/nova-lakeside.jpg|ristretto"
	"texteditor|mousepad|mousepad"
	"launcher|xfce4-appfinder|appfinder"
	"taskmanager|xfce4-taskmanager|taskmanager"
	"volumemixer|pavucontrol|pavucontrol"
	"installer|novaos-install|calamares"
)
pass=0; fail=0
for entry in "${APPS[@]}"; do
	IFS='|' read -r name cmd cls _ <<<"$entry"
	before="$(xdotool search --onlyvisible --class "" 2>/dev/null | sort)"
	setsid bash -c "$cmd" >"/tmp/selftest-$name.log" 2>&1 &
	pid=$!
	win=""
	for _ in $(seq 1 120); do
		for w in $(comm -13 <(echo "$before") <(xdotool search --onlyvisible --class "" 2>/dev/null | sort)); do
			t="$(xdotool getwindowname "$w" 2>/dev/null)"
			case "$t" in ""|xfce4-panel|Desktop|xfdesktop|xfce4-notifyd|wrapper-2.0) continue ;; esac
			win="$w"; break
		done
		[ -n "$win" ] && break
		sleep 1
	done
	if [ -n "$win" ]; then
		sleep 8
		title="$(xdotool getwindowname "$win" 2>/dev/null)"
		if [ -z "$title" ] || ! xdotool getwindowgeometry "$win" >/dev/null 2>&1; then
			say "FAIL $name (window vanished or has no title) log: $(tail -3 /tmp/selftest-$name.log | tr '\n' ' ' | cut -c1-300)"
			fail=$((fail + 1))
			continue
		fi
		say "PASS $name window=\"$title\""
		say "SHOT app-$name"
		sleep 6
		pass=$((pass + 1))
		xdotool windowclose "$win" 2>/dev/null || xdotool windowkill "$win" 2>/dev/null
		sleep 3
		for w in $(comm -13 <(echo "$before") <(xdotool search --onlyvisible --class "" 2>/dev/null | sort)); do
			case "$(xdotool getwindowname "$w" 2>/dev/null)" in xfce4-panel|Desktop|xfdesktop|xfce4-notifyd|wrapper-2.0) continue ;; esac
			xdotool windowkill "$w" 2>/dev/null
		done
	else
		say "FAIL $name (no window after 120 s) log: $(tail -3 /tmp/selftest-$name.log | tr '\n' ' ' | cut -c1-300)"
		fail=$((fail + 1))
	fi
	pkill -f "$cmd" 2>/dev/null; sudo -n pkill -x calamares 2>/dev/null
	sleep 2
done
say "env GSK_RENDERER=${GSK_RENDERER:-unset} picom=$(pgrep -x picom >/dev/null && echo running || echo stopped)"
say "session-init: $(tr '\n' ' ' < ~/.cache/novaos-session-init.log | cut -c1-200)"
say "segfaults: $(sudo -n dmesg | grep -i segfault | tail -3 | tr '\n' ' ')"
say "desktop-alive: xfdesktop=$(pgrep -x xfdesktop >/dev/null && echo yes || echo no) panel=$(pgrep -x xfce4-panel >/dev/null && echo yes || echo no)"
say "RESULT pass=$pass fail=$fail"

case "$ACTION" in
	halt)   say "ACTION halt";   sleep 3; xfce4-session-logout --halt --fast ;;
	reboot) say "ACTION reboot"; sleep 3; xfce4-session-logout --reboot --fast ;;
esac
say "END"
