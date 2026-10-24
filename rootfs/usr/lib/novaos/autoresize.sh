#!/bin/sh
# NovaOS: keep the desktop the same size as the UTM window, including full
# screen. When the VM window changes size, the virtual graphics card offers a
# new "preferred" resolution; switch to it right away. A resolution you pick
# yourself in Settings stays until the window size changes again.
last=""
while :; do
	out="$(xrandr --current 2>/dev/null)"
	name="$(printf '%s\n' "$out" | awk '/ connected/ {print $1; exit}')"
	if [ -n "$name" ]; then
		pref="$(printf '%s\n' "$out" | awk -v n="$name" '$1==n {f=1; next} f && /^[^ ]/ {exit} f && /\+/ {print $1; exit}')"
		cur="$(printf '%s\n' "$out" | awk -v n="$name" '$1==n {f=1; next} f && /^[^ ]/ {exit} f && /\*/ {print $1; exit}')"
		if [ -n "$pref" ] && [ "$pref" != "$last" ]; then
			[ "$pref" != "$cur" ] && xrandr --output "$name" --mode "$pref" 2>/dev/null
			last="$pref"
		fi
	fi
	sleep 1
done
