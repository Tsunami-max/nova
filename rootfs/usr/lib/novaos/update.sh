#!/bin/bash
# NovaOS Update: brings an installed NovaOS up to the newest version in place.
# Your files, apps, settings and browser logins stay; nothing is reinstalled.
#
#   sudo /usr/lib/novaos/update.sh            (or Start → NovaOS Update)
# From an older NovaOS that does not have this tool yet:
#   curl -fsSL https://raw.githubusercontent.com/Tsunami-max/nova/main/rootfs/usr/lib/novaos/update.sh | sudo bash
set -uo pipefail
REPO="${NOVA_REPO:-Tsunami-max/nova}"
BRANCH="${NOVA_BRANCH:-main}"
export DEBIAN_FRONTEND=noninteractive

if [ "$(id -u)" != 0 ]; then
	exec pkexec "$0" "$@"
fi
say() { printf '\n\033[1;35m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mNovaOS Update failed: %s\033[0m\n' "$*"; exit 1; }

if [ -d /run/casper ] || grep -qw boot=casper /proc/cmdline; then
	die "this is the live CD. Install NovaOS first (Install NovaOS on the desktop); updates work on the installed system."
fi

# The person who asked for the update (for autologin and their settings).
TARGET_USER="${NOVA_USER:-}"
[ -z "$TARGET_USER" ] && [ -n "${PKEXEC_UID:-}" ] && TARGET_USER="$(getent passwd "$PKEXEC_UID" | cut -d: -f1)"
[ -z "$TARGET_USER" ] && [ -n "${SUDO_USER:-}" ] && TARGET_USER="$SUDO_USER"
[ -z "$TARGET_USER" ] && TARGET_USER="$(getent passwd | awk -F: '$3 >= 1000 && $3 < 60000 {print $1; exit}')"

say "Downloading the newest NovaOS from GitHub ($REPO)"
WORK="$(mktemp -d /tmp/novaos-update.XXXXXX)"
trap 'rm -rf "$WORK"' EXIT
curl -fL --retry 3 --max-time 600 -o "$WORK/nova.tar.gz" \
	"https://codeload.github.com/$REPO/tar.gz/refs/heads/$BRANCH" || die "no internet connection to GitHub"
mkdir "$WORK/src"
tar -xzf "$WORK/nova.tar.gz" -C "$WORK/src" --strip-components=1 || die "download was damaged, try again"
SRC="$WORK/src"
COMMIT="$(curl -fsS --max-time 30 "https://api.github.com/repos/$REPO/commits/$BRANCH" 2>/dev/null \
	| sed -n 's/^  "sha": "\([0-9a-f]*\)".*/\1/p' | head -1)"
VERSION="$(sed -n 's/^VERSION="\(.*\)"/\1/p' "$SRC/build.sh" | head -1)"
[ -n "$VERSION" ] || VERSION="2"

say "Installing new NovaOS apps and system updates (this can take a while)"
apt-get update || true
dpkg --configure -a || true
if [ -f "$SRC/packages.list" ]; then
	# Live-CD-only packages are not wanted on an installed system.
	mapfile -t WANT < <(sed 's/#.*//' "$SRC/packages.list" | tr ' \t' '\n\n' | grep -v '^$' \
		| grep -Ev '^(casper|calamares.*|ubiquity.*|lupin-casper)$')
	MISSING=()
	for p in "${WANT[@]}"; do
		dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q "ok installed" || MISSING+=("$p")
	done
	if [ ${#MISSING[@]} -gt 0 ]; then
		echo "New packages: ${MISSING[*]}"
		apt-get -y install "${MISSING[@]}" || for p in "${MISSING[@]}"; do apt-get -y install "$p" || true; done
	fi
fi
apt-get -y -o Dpkg::Options::=--force-confold full-upgrade || true
command -v flatpak >/dev/null && flatpak update -y --noninteractive || true

say "Updating NovaOS's look, apps and settings"
# Copy the NovaOS files, except the ones that only belong on the live CD.
tar -C "$SRC/rootfs" \
	--exclude='./etc/sddm.conf.d/50-novaos-live.conf' \
	--exclude='./etc/polkit-1/rules.d/49-novaos-live.rules' \
	--exclude='./etc/calamares' --exclude='./etc/casper.conf' --exclude='./etc/initramfs-tools' \
	--exclude='./usr/bin/novaos-install' \
	--exclude='./etc/hostname' --exclude='./etc/hosts' \
	-cf - . | tar -C / --no-same-owner --keep-directory-symlink -xf -
cp "$SRC/scripts/chroot-customize.sh" "$WORK/customize.sh"
NOVA_UPDATE=1 NOVA_VERSION="$VERSION" NOVA_COMMIT="${COMMIT:-unknown}" NOVA_BUILD=update \
	NOVA_ARCH="$(dpkg --print-architecture)" bash "$WORK/customize.sh" || echo "WARNING: some settings were not updated"

# Log in automatically (no password at start-up) unless switched off in NovaOS Style.
if [ -n "$TARGET_USER" ] && [ ! -e /etc/novaos/no-autologin ] && [ "$TARGET_USER" != root ]; then
	/usr/lib/novaos/autologin.sh on "$TARGET_USER" || true
fi

# Refresh the person's desktop with the new NovaOS defaults (keeps their own changes).
if [ -n "$TARGET_USER" ]; then
	H="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
	if [ -d "$H/.config" ]; then
		su - "$TARGET_USER" -c "kbuildsycoca5 >/dev/null 2>&1" 2>/dev/null || true
	fi
fi

say "NovaOS is now version $VERSION${COMMIT:+ (${COMMIT:0:7})}"
echo "Log out and in again (or restart) to see everything new."
