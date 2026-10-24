#!/bin/bash
# autologin.sh on <user> | off   — start NovaOS straight to the desktop (no password).
# autologin.sh nopass-on|nopass-off <user> — no password on the login screen either.
set -e
CONF=/etc/sddm.conf.d/60-novaos-autologin.conf
case "${1:-}" in
on)
	u="${2:?user}"
	id "$u" >/dev/null 2>&1 || { echo "no such user: $u"; exit 1; }
	sess=plasma
	[ -f /usr/share/xsessions/plasma.desktop ] || sess="$(ls /usr/share/xsessions/ 2>/dev/null | head -1 | sed 's/\.desktop$//')"
	mkdir -p /etc/sddm.conf.d /etc/novaos
	printf '# NovaOS: log in automatically (NovaOS Style → Start-up)\n[Autologin]\nUser=%s\nSession=%s\nRelogin=false\n' \
		"$u" "${sess:-plasma}" > "$CONF"
	getent group autologin >/dev/null || groupadd -r autologin
	usermod -aG autologin "$u" || true
	rm -f /etc/novaos/no-autologin
	echo "Autologin on for $u" ;;
off)
	rm -f "$CONF"
	mkdir -p /etc/novaos; touch /etc/novaos/no-autologin
	# The installer may have written autologin into sddm.conf itself.
	[ -f /etc/sddm.conf ] && sed -i '/^\[Autologin\]/,/^\[/{/^User=/d}' /etc/sddm.conf
	echo "Autologin off" ;;
nopass-on)
	# Log in on the login screen (after logging out) without typing a password.
	u="${2:?user}"
	getent group nopasswdlogin >/dev/null || groupadd -r nopasswdlogin
	usermod -aG nopasswdlogin "$u"
	rm -f /etc/novaos/password-login
	echo "Password-free login on for $u" ;;
nopass-off)
	u="${2:?user}"
	gpasswd -d "$u" nopasswdlogin >/dev/null 2>&1 || true
	mkdir -p /etc/novaos; touch /etc/novaos/password-login
	echo "Password-free login off for $u" ;;
*) echo "usage: $0 on <user> | off | nopass-on <user> | nopass-off <user>"; exit 2 ;;
esac
