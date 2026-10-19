#!/bin/sh
# Runs in the X server just before Plasma starts (from /etc/X11/Xsession.d).
#  1. Window effects follow the graphics hardware: with 3D acceleration KWin
#     uses OpenGL (smooth animations, blur); without it compositing is turned
#     off, which keeps windows and menus snappy on a CPU-drawn screen.
#  2. On the first login, high-resolution screens (2K/4K/Retina) get a matching
#     scale so text and buttons are not tiny. Change it later in
#     System Settings > Display and Monitor.
CFG="${XDG_CONFIG_HOME:-$HOME/.config}"
mkdir -p "$CFG"
KW=kwriteconfig5
command -v "$KW" >/dev/null 2>&1 || exit 0

GPU="$(/usr/lib/novaos/gl-check.sh)"
if [ "$GPU" = yes ]; then
	$KW --file kwinrc --group Compositing --key Enabled true
	$KW --file kwinrc --group Compositing --key Backend OpenGL
	$KW --file kwinrc --group Compositing --key GLCore true
else
	$KW --file kwinrc --group Compositing --key Enabled false
fi

if [ ! -e "$CFG/.novaos-scale-done" ]; then
	W="$(xrandr --current 2>/dev/null | sed -n 's/.* connected[^0-9]*\([0-9][0-9]*\)x[0-9].*/\1/p' | head -1)"
	S=1; DPI=96
	if [ "${W:-0}" -ge 3000 ]; then S=2; DPI=192
	elif [ "${W:-0}" -ge 2400 ]; then S=1.5; DPI=144
	fi
	if [ "$S" != 1 ]; then
		SSF="$(xrandr --current | awk -v s="$S" '/ connected/ {printf "%s=%s;", $1, s}')"
		$KW --file kdeglobals --group KScreen --key ScaleFactor "$S"
		$KW --file kdeglobals --group KScreen --key ScreenScaleFactors "$SSF"
		$KW --file kcmfonts --group General --key forceFontDPI "$DPI"
	fi
	touch "$CFG/.novaos-scale-done"
fi
exit 0
