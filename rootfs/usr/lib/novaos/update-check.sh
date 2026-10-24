#!/bin/bash
# At login (installed system only): tell the user when a newer NovaOS exists.
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
