#!/bin/sh
# NovaOS: make common big-screen resolutions selectable in Settings > Display
# even when the virtual screen does not list them (2K, 4K, 1440p, 1080p).
OUT="$(xrandr --current 2>/dev/null | awk '/ connected/ {print $1; exit}')"
[ -n "$OUT" ] || exit 0
add() {  # add <w> <h>
	NAME="${1}x${2}_60.00"
	xrandr --current | grep -q "^   ${1}x${2}[ _]" && return
	ML="$(cvt "$1" "$2" 60 | sed -n 's/^Modeline "[^"]*" *//p')"
	[ -n "$ML" ] || return
	xrandr --newmode "$NAME" $ML 2>/dev/null
	xrandr --addmode "$OUT" "$NAME" 2>/dev/null
}
add 1920 1080
add 2560 1440
add 2560 1600
add 3840 2160
exit 0
