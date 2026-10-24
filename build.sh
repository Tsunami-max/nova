#!/usr/bin/env bash
# =============================================================================
#  NovaOS build script
#  Builds a bootable live/installer ISO based on Ubuntu 24.04 LTS ("noble").
#
#  Usage (run as root on an Ubuntu 24.04 machine of the SAME architecture
#  you want to build for):
#      sudo ./build.sh            # full build -> out/NovaOS.iso
#      sudo ./build.sh <stage>    # run one stage: bootstrap | packages |
#                                 #   customize | image | clean
#  Environment overrides:
#      ARCH=amd64|arm64   (default: this machine's architecture)
#      MIRROR=<url>       (default: official Ubuntu mirror for ARCH)
#      WORK=<dir>         (default: ./work)
#      OUT=<dir>          (default: ./out)
#      EXTRA_CA_CERT=<f>  (optional: extra CA cert for HTTPS proxies)
# =============================================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCH="${ARCH:-$(dpkg --print-architecture)}"
SUITE="noble"
VERSION="2.0"
WORK="${WORK:-$HERE/work}"
OUT="${OUT:-$HERE/out}"
CHROOT="$WORK/chroot"
ISODIR="$WORK/iso"

case "$ARCH" in
	amd64) MIRROR="${MIRROR:-http://archive.ubuntu.com/ubuntu}"
	       SEC_MIRROR="${SEC_MIRROR:-http://security.ubuntu.com/ubuntu}"
	       ISO_NAME="NovaOS.iso" ;;
	arm64) MIRROR="${MIRROR:-http://ports.ubuntu.com/ubuntu-ports}"
	       SEC_MIRROR="${SEC_MIRROR:-$MIRROR}"
	       ISO_NAME="NovaOS-arm64.iso" ;;
	*) echo "Unsupported ARCH: $ARCH" >&2; exit 1 ;;
esac

if [ "$(dpkg --print-architecture)" != "$ARCH" ]; then
	echo "Cross-building is not supported: run this on an $ARCH machine." >&2
	exit 1
fi
[ "$(id -u)" -eq 0 ] || { echo "Run as root (sudo ./build.sh)" >&2; exit 1; }

HOST_DEPS="debootstrap squashfs-tools xorriso mtools grub-common rsync dosfstools"
[ "$ARCH" = amd64 ] && HOST_DEPS="$HOST_DEPS grub-pc-bin grub-efi-amd64-bin"
[ "$ARCH" = arm64 ] && HOST_DEPS="$HOST_DEPS grub-efi-arm64-bin"
missing=""
for p in $HOST_DEPS; do dpkg -s "$p" >/dev/null 2>&1 || missing="$missing $p"; done
if [ -n "$missing" ]; then
	echo "Installing build tools:$missing"
	apt-get update && apt-get install -y $missing
fi

log() { printf '\n\033[1;35m==> %s\033[0m\n' "$*"; }

# ---------------------------------------------------------------------------
# chroot helpers
# ---------------------------------------------------------------------------
mount_chroot() {
	for d in dev dev/pts proc sys run; do
		mkdir -p "$CHROOT/$d"
		mountpoint -q "$CHROOT/$d" || mount --bind "/$d" "$CHROOT/$d"
	done
}
umount_chroot() {
	for d in run sys proc dev/pts dev; do
		mountpoint -q "$CHROOT/$d" 2>/dev/null && umount -l "$CHROOT/$d" || true
	done
}
trap umount_chroot EXIT

in_chroot() {
	chroot "$CHROOT" /usr/bin/env -i \
		HOME=/root PATH=/usr/sbin:/usr/bin:/sbin:/bin LANG=C.UTF-8 \
		DEBIAN_FRONTEND=noninteractive \
		https_proxy="${HTTPS_PROXY:-${https_proxy:-}}" \
		"$@"
}

# ---------------------------------------------------------------------------
# Stage 1: minimal Ubuntu base system
# ---------------------------------------------------------------------------
stage_bootstrap() {
	log "Bootstrapping Ubuntu $SUITE ($ARCH) into $CHROOT"
	umount_chroot
	rm -rf "$CHROOT"
	mkdir -p "$CHROOT"
	debootstrap --arch="$ARCH" --variant=minbase \
		--include=ca-certificates,gnupg,apt-utils \
		"$SUITE" "$CHROOT" "$MIRROR"
}

# ---------------------------------------------------------------------------
# Stage 2: kernel, desktop and applications
# ---------------------------------------------------------------------------
PKGS_COMMON=(
	# --- live boot + system ---
	ubuntu-minimal systemd-sysv systemd-timesyncd sudo locales tzdata
	keyboard-configuration console-setup kbd casper discover laptop-detect
	initramfs-tools zstd squashfs-tools dosfstools e2fsprogs parted
	network-manager systemd-resolved iputils-ping curl nano less htop bash-completion pciutils
	ethtool dbus-x11 dbus-user-session policykit-1 udisks2 acpid
	spice-vdagent qemu-guest-agent
	# --- graphics stack ---
	xserver-xorg-core xserver-xorg-input-libinput xserver-xorg-video-fbdev
	xinit xauth x11-xserver-utils x11-utils x11-xkb-utils xdotool
	mesa-utils libgl1-mesa-dri mesa-vulkan-drivers
	# --- boot splash + login ---
	plymouth plymouth-label sddm sddm-theme-breeze kde-config-sddm
	# --- KDE Plasma desktop, styled as NovaOS ---
	plasma-desktop plasma-workspace kwin-x11 breeze breeze-gtk-theme breeze-cursor-theme
	kde-config-gtk-style plasma-nm plasma-pa powerdevil kscreen systemsettings
	kinfocenter plasma-systemmonitor kde-cli-tools libkf5config-bin kmenuedit
	polkit-kde-agent-1 xdg-desktop-portal-kde kdialog khotkeys
	plasma-widgets-addons plasma-wallpapers-addons plasma-workspace-wallpapers
	kio-extras ffmpegthumbs kdegraphics-thumbnailers
	pipewire pipewire-pulse wireplumber alsa-utils
	dconf-cli dconf-gsettings-backend gsettings-desktop-schemas
	xdg-user-dirs xdg-utils desktop-file-utils shared-mime-info
	# --- App Store: Discover with Ubuntu packages and Flathub ---
	plasma-discover plasma-discover-backend-flatpak packagekit flatpak
	qt5-style-kvantum qt5-style-kvantum-themes dmz-cursor-theme
	# --- built-in applications ---
	dolphin konsole kwrite kcalc gwenview okular ark kde-spectacle kolourpaint vlc
	libreoffice-writer libreoffice-calc libreoffice-impress libreoffice-kf5
	libreoffice-style-breeze fonts-crosextra-carlito fonts-crosextra-caladea
	kpat kmines kblocks kmahjongg
	epiphany-browser
	gstreamer1.0-libav gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly
	python3 python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-cairo
	# --- look & feel ---
	papirus-icon-theme librsvg2-common adwaita-icon-theme
	fonts-inter fonts-jetbrains-mono fonts-noto-color-emoji
	fonts-dejavu-core
	# --- installer ---
	calamares rsync efibootmgr grub2-common
)
PKGS_amd64=(xserver-xorg-video-vesa xserver-xorg-video-qxl
	grub-efi-amd64-bin grub-pc-bin)
PKGS_arm64=(grub-efi-arm64-bin)

install_firefox() {
	log "Installing Firefox (Mozilla's official APT repository)"
	mkdir -p "$CHROOT/etc/apt/keyrings"
	curl -fsSL https://packages.mozilla.org/apt/repo-signing-key.gpg \
		-o "$CHROOT/etc/apt/keyrings/packages.mozilla.org.asc" || return 1
	echo "deb [signed-by=/etc/apt/keyrings/packages.mozilla.org.asc] https://packages.mozilla.org/apt mozilla main" \
		> "$CHROOT/etc/apt/sources.list.d/mozilla.list"
	# Mozilla's real Firefox, not Ubuntu's snap transition package.
	cat > "$CHROOT/etc/apt/preferences.d/mozilla" <<'PIN'
Package: *
Pin: origin packages.mozilla.org
Pin-Priority: 1000
PIN
	in_chroot apt-get update || return 1
	in_chroot apt-get -y install firefox || return 1
	[ -x "$CHROOT/usr/lib/firefox/firefox" ] || [ -x "$CHROOT/usr/lib/firefox/firefox-bin" ] || return 1
	in_chroot apt-get -y purge epiphany-browser epiphany-browser-data || true
	return 0
}

install_chromium() {
	log "Installing Chromium (xtradeb PPA)"
	in_chroot apt-get -y install software-properties-common gpg-agent dirmngr || return 1
	in_chroot add-apt-repository -y ppa:xtradeb/apps || return 1
	# Only take Chromium from this PPA, everything else from Ubuntu.
	cat > "$CHROOT/etc/apt/preferences.d/xtradeb" <<'PIN'
Package: *
Pin: release o=LP-PPA-xtradeb-apps
Pin-Priority: 100

Package: chromium*
Pin: release o=LP-PPA-xtradeb-apps
Pin-Priority: 700
PIN
	in_chroot apt-get update || return 1
	in_chroot apt-get -y install chromium || return 1
	in_chroot apt-get -y purge epiphany-browser epiphany-browser-data software-properties-common || true
	return 0
}

stage_packages() {
	log "Configuring APT sources"
	cat > "$CHROOT/etc/apt/sources.list" <<EOF
deb $MIRROR $SUITE main restricted universe multiverse
deb $MIRROR $SUITE-updates main restricted universe multiverse
deb $SEC_MIRROR $SUITE-security main restricted universe multiverse
EOF
	cat > "$CHROOT/etc/apt/apt.conf.d/99novaos-build" <<'EOF'
APT::Install-Recommends "false";
APT::Install-Suggests "false";
Acquire::Retries "5";
EOF
	if [ -n "${EXTRA_CA_CERT:-}" ]; then
		cp "$EXTRA_CA_CERT" "$CHROOT/usr/local/share/ca-certificates/build-extra.crt"
	fi
	# Never start services inside the build chroot.
	printf '#!/bin/sh\nexit 101\n' > "$CHROOT/usr/sbin/policy-rc.d"
	chmod +x "$CHROOT/usr/sbin/policy-rc.d"
	echo "novaos" > "$CHROOT/etc/hostname"

	mount_chroot
	in_chroot update-ca-certificates >/dev/null 2>&1 || true
	in_chroot apt-get update
	in_chroot apt-get -y dist-upgrade

	log "Installing kernel"
	in_chroot apt-get -y install linux-image-virtual
	local kver
	kver="$(ls "$CHROOT/lib/modules" | sort -V | tail -1)"
	in_chroot apt-get -y install "linux-modules-extra-$kver"

	log "Installing NovaOS packages"
	local arch_pkgs="PKGS_${ARCH}[@]"
	# shellcheck disable=SC2086
	in_chroot apt-get -y install "${PKGS_COMMON[@]}" "${!arch_pkgs}"

	# Optional: Chromium as the main browser (needs a machine with full internet,
	# e.g. the GitHub Actions build). Ubuntu only ships Chromium as a snap, so the
	# deb comes from the xtradeb PPA. Skipped silently if unreachable.
	if [ "${NOVA_FIREFOX:-0}" = 1 ]; then
		install_firefox || { echo "WARNING: Firefox not installed, trying Chromium"; NOVA_CHROMIUM=1; }
	fi
	if [ "${NOVA_CHROMIUM:-0}" = 1 ]; then
		install_chromium || echo "WARNING: Chromium not installed, keeping GNOME Web"
	fi

	# Make sure no snap tooling sneaks in.
	in_chroot apt-get -y purge snapd 2>/dev/null || true
	in_chroot apt-get -y autoremove --purge
	in_chroot apt-get clean
	umount_chroot
}

# ---------------------------------------------------------------------------
# Stage 3: NovaOS customisation (overlay files + configuration script)
# ---------------------------------------------------------------------------
stage_customize() {
	mount_chroot
	log "Making sure all packages are present"
	local arch_pkgs="PKGS_${ARCH}[@]"
	[ -n "$(ls -A "$CHROOT/var/lib/apt/lists" 2>/dev/null | grep -v lock)" ] || in_chroot apt-get update
	local pkgs=("${PKGS_COMMON[@]}" "${!arch_pkgs}")
	if [ -x "$CHROOT/usr/bin/chromium" ] || [ -e "$CHROOT/usr/lib/firefox/firefox" ]; then
		local filtered=()
		for p in "${pkgs[@]}"; do [ "$p" = epiphany-browser ] || filtered+=("$p"); done
		pkgs=("${filtered[@]}")
	fi
	in_chroot apt-get -y install "${pkgs[@]}"

	log "Copying NovaOS overlay into the image"
	rsync -a --chown=root:root "$HERE/rootfs/" "$CHROOT/"
	mkdir -p "$CHROOT/usr/share/doc/novaos"
	cp "$HERE/licenses/LICENSES.md" "$CHROOT/usr/share/doc/novaos/LICENSES.md"
	install -m 0755 "$HERE/scripts/chroot-customize.sh" "$CHROOT/tmp/chroot-customize.sh"
	in_chroot env NOVA_ARCH="$ARCH" NOVA_VERSION="$VERSION" /tmp/chroot-customize.sh
	rm -f "$CHROOT/tmp/chroot-customize.sh"
	umount_chroot
}

# ---------------------------------------------------------------------------
# Stage 4: squashfs + bootable ISO
# ---------------------------------------------------------------------------
stage_image() {
	log "Preparing ISO tree"
	rm -rf "$ISODIR"
	mkdir -p "$ISODIR"/{casper,boot/grub,.disk} "$OUT"

	# Live-only clean up before squashing.
	rm -f "$CHROOT/usr/sbin/policy-rc.d" "$CHROOT/etc/apt/apt.conf.d/99novaos-build"
	rm -f "$CHROOT/usr/local/share/ca-certificates/build-extra.crt"
	rm -rf "$CHROOT"/tmp/* "$CHROOT"/var/tmp/* "$CHROOT"/var/lib/apt/lists/*
	rm -f "$CHROOT"/var/log/*.log "$CHROOT/etc/machine-id" "$CHROOT/var/lib/dbus/machine-id"
	# DNS: never ship the build machine's resolv.conf; use systemd-resolved.
	rm -f "$CHROOT/etc/resolv.conf"
	ln -s ../run/systemd/resolve/stub-resolv.conf "$CHROOT/etc/resolv.conf"
	touch "$CHROOT/etc/machine-id"

	local kver
	kver="$(ls "$CHROOT/lib/modules" | sort -V | tail -1)"
	cp "$CHROOT/boot/vmlinuz-$kver" "$ISODIR/casper/vmlinuz"
	cp "$CHROOT/boot/initrd.img-$kver" "$ISODIR/casper/initrd"

	chroot "$CHROOT" dpkg-query -W --showformat='${Package} ${Version}\n' \
		> "$ISODIR/casper/filesystem.manifest"
	cp "$ISODIR/casper/filesystem.manifest" "$OUT/packages.manifest"

	log "Compressing root filesystem (this takes a while)"
	local DEFAULT_SQUASH_OPTS="-Xdict-size 100%"
	[ "$ARCH" = amd64 ] && DEFAULT_SQUASH_OPTS="-Xbcj x86 -Xdict-size 100%"
	rm -f "$ISODIR/casper/filesystem.squashfs"
	mksquashfs "$CHROOT" "$ISODIR/casper/filesystem.squashfs" \
		-comp "${SQUASH_COMP:-xz}" ${SQUASH_OPTS-$DEFAULT_SQUASH_OPTS} -b 1M -noappend \
		-wildcards -e boot/efi -e 'proc/*' -e 'sys/*' -e 'dev/*' -e 'run/*' \
		-e 'boot/initrd.img-*' -e 'boot/System.map-*'
	du -sx --block-size=1 "$CHROOT" | cut -f1 > "$ISODIR/casper/filesystem.size"

	echo "NovaOS $VERSION \"Nova\" - $ARCH ($(date -u +%Y%m%d))" > "$ISODIR/.disk/info"
	touch "$ISODIR/.disk/base_installable"
	echo "full_cd/single" > "$ISODIR/.disk/cd_type"

	log "Installing GRUB boot menu and theme"
	cp -r "$HERE/boot/grub/." "$ISODIR/boot/grub/"
	sed -i "s/@VERSION@/$VERSION/g" "$ISODIR/boot/grub/grub.cfg"
	mkdir -p "$ISODIR/boot/grub/fonts"
	cp /usr/share/grub/unicode.pf2 "$ISODIR/boot/grub/fonts/" 2>/dev/null || true
	# Licences on the medium itself.
	cp -r "$HERE/licenses" "$ISODIR/licenses"

	log "Building $ISO_NAME"
	rm -f "$OUT/$ISO_NAME"
	grub-mkrescue -o "$OUT/$ISO_NAME" "$ISODIR" -- -volid "NOVAOS" \
		2> "$WORK/grub-mkrescue.log" || { cat "$WORK/grub-mkrescue.log"; exit 1; }
	(cd "$OUT" && sha256sum "$ISO_NAME" > "$ISO_NAME.sha256")
	log "Done: $OUT/$ISO_NAME"
	ls -lh "$OUT/$ISO_NAME"
	cat "$OUT/$ISO_NAME.sha256"
}

stage_clean() { umount_chroot; rm -rf "$WORK"; }

case "${1:-all}" in
	bootstrap) stage_bootstrap ;;
	packages)  stage_packages ;;
	customize) stage_customize ;;
	image)     stage_image ;;
	clean)     stage_clean ;;
	all)       stage_bootstrap; stage_packages; stage_customize; stage_image ;;
	*) echo "Unknown stage: $1" >&2; exit 1 ;;
esac
