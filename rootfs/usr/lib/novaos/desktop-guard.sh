#!/bin/sh
# Safety net: if the desktop (wallpaper/icons) or the panel ever crashes,
# bring it back within a few seconds instead of leaving a black screen.
sleep 30
while :; do
	pgrep -u "$(id -u)" -x xfdesktop >/dev/null || (xfdesktop >/dev/null 2>&1 &)
	pgrep -u "$(id -u)" -x xfce4-panel >/dev/null || (xfce4-panel >/dev/null 2>&1 &)
	sleep 10
done
