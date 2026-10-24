#!/bin/sh
# Runs in the X server just before Plasma starts (from /etc/X11/Xsession.d).
#  1. Window effects follow the graphics hardware: with 3D acceleration KWin
#     uses OpenGL (smooth animations, blur); without it compositing is turned
#     off, which keeps windows and menus snappy on a CPU-drawn screen.
#  2. High-resolution screens (2K/4K/Retina) get a matching scale so text
#     and buttons are not tiny (see below).
CFG="${XDG_CONFIG_HOME:-$HOME/.config}"
mkdir -p "$CFG"
KW=kwriteconfig5
command -v "$KW" >/dev/null 2>&1 || exit 0

GPU="$(/usr/lib/novaos/gl-check.sh)"
if [ "$GPU" = yes ]; then
	$KW --file kwinrc --group Compositing --key Enabled true
	$KW --file kwinrc --group Compositing --key Backend OpenGL
	$KW --file kwinrc --group Compositing --key GLCore true
elif [ "$(kreadconfig5 --file kwinrc --group NovaOS --key Transparency --default off)" = off ]; then
	# (kept on when the user turned on transparent windows in NovaOS Style)
	$KW --file kwinrc --group Compositing --key Enabled false
fi

# Automatic scale for big screens, decided at every login from the current
# screen width (UTM full screen with Retina gives the Mac's full resolution).
# As soon as you pick a scale yourself in Settings, NovaOS leaves it alone.
KR=kreadconfig5
CUR="$($KR --file kdeglobals --group KScreen --key ScaleFactor)"
AUTO="$($KR --file kdeglobals --group NovaOS --key AutoScale)"
if [ -z "$CUR" ] || [ "$CUR" = "$AUTO" ]; then
	W="$(xrandr --current 2>/dev/null | sed -n 's/.* connected[^0-9]*\([0-9][0-9]*\)x[0-9].*/\1/p' | head -1)"
	S=1; DPI=96
	if [ "${W:-0}" -ge 3000 ]; then S=2; DPI=192
	elif [ "${W:-0}" -ge 2400 ]; then S=1.25; DPI=120
	fi
	SSF="$(xrandr --current | awk -v s="$S" '/ connected/ {printf "%s=%s;", $1, s}')"
	$KW --file kdeglobals --group KScreen --key ScaleFactor "$S"
	$KW --file kdeglobals --group KScreen --key ScreenScaleFactors "$SSF"
	$KW --file kdeglobals --group NovaOS --key AutoScale "$S"
	if [ "$S" = 1 ]; then
		$KW --file kcmfonts --group General --key forceFontDPI --delete
	else
		$KW --file kcmfonts --group General --key forceFontDPI "$DPI"
	fi
fi
exit 0
