#!/bin/sh
# Safety net: if the Plasma desktop/taskbar (plasmashell) ever crashes,
# start it again within a few seconds instead of leaving a bare screen.
sleep 60
miss=0
while :; do
	if pgrep -u "$(id -u)" -x plasmashell >/dev/null; then
		miss=0
	else
		miss=$((miss + 1))
		if [ "$miss" -ge 2 ]; then
			pkill -u "$(id -u)" -x drkonqi 2>/dev/null
			(setsid plasmashell >/dev/null 2>&1 &)
			miss=0
			sleep 20
		fi
	fi
	sleep 5
done
