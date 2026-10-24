#!/bin/bash
# Runs INSIDE the image (chroot) after the NovaOS overlay has been copied in.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
NOVA_VERSION="${NOVA_VERSION:-1.0}"
echo "== NovaOS customisation ($NOVA_VERSION, ${NOVA_ARCH:-?})"
# NOVA_UPDATE=1: run by NovaOS Update on an installed system, so skip the
# image-only steps (locale, slimming, kernel driver pruning, initramfs).
UPDATE="${NOVA_UPDATE:-}"
mkdir -p /etc/novaos
cat > /etc/novaos/build <<EOB
VERSION=$NOVA_VERSION
COMMIT=${NOVA_COMMIT:-unknown}
BUILD=${NOVA_BUILD:-local}
DATE=$(date -u +%Y-%m-%d)
EOB

# --- locale -------------------------------------------------------------------
if [ -z "$UPDATE" ]; then
	sed -i 's/^# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen 2>/dev/null || echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
	locale-gen en_US.UTF-8
	update-locale LANG=en_US.UTF-8
fi

# --- branding -------------------------------------------------------------------
if ! dpkg-divert --list /usr/lib/os-release | grep -q novaos; then
	dpkg-divert --package novaos --rename --divert /usr/lib/os-release.ubuntu /usr/lib/os-release
fi
rm -f /usr/lib/os-release /etc/os-release
cat > /usr/lib/os-release <<EOF
PRETTY_NAME="NovaOS $NOVA_VERSION"
NAME="NovaOS"
VERSION_ID="$NOVA_VERSION"
VERSION="$NOVA_VERSION (based on Ubuntu 24.04 LTS)"
VERSION_CODENAME=noble
ID=novaos
ID_LIKE="ubuntu debian"
UBUNTU_CODENAME=noble
LOGO=novaos
EOF
ln -sf ../usr/lib/os-release /etc/os-release
echo "NovaOS $NOVA_VERSION \\n \\l" > /etc/issue
echo "NovaOS $NOVA_VERSION" > /etc/issue.net
if [ -z "$UPDATE" ]; then echo "novaos" > /etc/hostname; fi

# --- look & feel (KDE Plasma) ---------------------------------------------------
# NovaOS colour schemes: Breeze with NovaOS's deep blue-black surfaces and
# violet accent.
nova_colors() {  # nova_colors <source scheme> <dest file> <name>
	sed -e 's/61,174,233/124,136,255/g' -e 's/30,87,116/58,64,140/g' -e 's/29,153,243/140,155,255/g' \
	    -e 's/^Name=.*/Name='"$3"'/' "$1" > "$2"
}
nova_colors /usr/share/color-schemes/BreezeDark.colors /usr/share/color-schemes/NovaOSDark.colors "NovaOS Dark"
sed -i -e 's/=49,54,59/=32,35,48/g' -e 's/=42,46,50/=26,29,40/g' -e 's/=35,38,41/=22,25,34/g' \
	-e 's/=27,30,32/=18,20,28/g' /usr/share/color-schemes/NovaOSDark.colors
nova_colors /usr/share/color-schemes/BreezeLight.colors /usr/share/color-schemes/NovaOSLight.colors "NovaOS Light"
sed -i 's/^LookAndFeelPackage=.*/LookAndFeelPackage=org.novaos.desktop/' /etc/xdg/kdeglobals
# Full colour definitions as system defaults, so every app is dark from the
# very first login (not only after the look-and-feel is applied).
awk '/^\[/{keep = ($0 !~ /^\[(General|KDE)\]/)} keep' /usr/share/color-schemes/NovaOSDark.colors >> /etc/xdg/kdeglobals
cat >> /etc/xdg/kdeglobals <<'EOK'

[General]
ColorScheme=NovaOSDark
AccentColor=124,136,255
BrowserApplication=PLACEHOLDER_BROWSER

[Icons]
Theme=NovaOS-Dark
EOK
# Login screen: Breeze with the NovaOS wallpaper.
SHELLWP="$(ls -S /usr/share/wallpapers/Shell/contents/images/* 2>/dev/null | head -1)"
if [ -d /usr/share/sddm/themes/breeze ]; then
	cat > /usr/share/sddm/themes/breeze/theme.conf.user <<EOT
[General]
background=${SHELLWP:-/usr/share/novaos/login-background.jpg}
type=image
EOT
fi
# Look-and-feel preview picture.
[ -n "$SHELLWP" ] && command -v convert >/dev/null && \
	convert "$SHELLWP" -resize 600x338^ -gravity center -extent 600x338 \
	/usr/share/plasma/look-and-feel/org.novaos.desktop/contents/previews/preview.png 2>/dev/null || true
for t in NovaOS NovaOS-Dark Papirus Papirus-Dark; do gtk-update-icon-cache -f -t "/usr/share/icons/$t" || true; done
glib-compile-schemas /usr/share/glib-2.0/schemas
fc-cache -f >/dev/null

# --- boot splash ------------------------------------------------------------------
update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth \
	/usr/share/plymouth/themes/novaos/novaos.plymouth 300
update-alternatives --set default.plymouth /usr/share/plymouth/themes/novaos/novaos.plymouth

# --- GRUB defaults for the installed system --------------------------------------
if [ -f /etc/default/grub ]; then G=/etc/default/grub; else G=/etc/default/grub; touch $G; fi
sed -i '/^GRUB_DISTRIBUTOR=/d;/^GRUB_THEME=/d;/^GRUB_CMDLINE_LINUX_DEFAULT=/d;/^GRUB_TIMEOUT=/d;/^GRUB_TIMEOUT_STYLE=/d;/^GRUB_GFXMODE=/d' $G
cat >> $G <<'EOF'
GRUB_DISTRIBUTOR="NovaOS"
GRUB_TIMEOUT_STYLE=menu
GRUB_TIMEOUT=3
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
GRUB_GFXMODE=1920x1080,1280x800,auto
GRUB_THEME=/usr/share/grub/themes/novaos/theme.txt
EOF

# --- application menu polish -----------------------------------------------------------
mkdir -p /usr/local/share/applications
rename_app() {  # rename_app <desktop file> <new name>
	local src="/usr/share/applications/$1" dst="/usr/local/share/applications/$1" bin
	[ -f "$src" ] || return 0
	sed "0,/^Name=.*/s//Name=$2/" "$src" | sed '/^Name\[/d' > "$dst"
	# Hide the renamed copy automatically once its app is uninstalled.
	if ! grep -q '^TryExec=' "$dst"; then
		bin="$(sed -n 's/^Exec=//p' "$src" | head -1 | awk '{print $1}')"
		[ -n "$bin" ] && sed -i "0,/^\[Desktop Entry\]/s##[Desktop Entry]\nTryExec=$bin#" "$dst"
	fi
}
# Main browser: Chromium when installed, otherwise GNOME Web.
BROWSER_DESKTOP=""
for b in firefox.desktop chromium.desktop chromium-browser.desktop org.gnome.Epiphany.desktop; do
	if [ -f "/usr/share/applications/$b" ]; then BROWSER_DESKTOP="$b"; break; fi
done
if [ -n "$BROWSER_DESKTOP" ] && [ "$BROWSER_DESKTOP" != firefox.desktop ]; then
	rename_app "$BROWSER_DESKTOP" "Web Browser"
	# Start it through nova-browser (GPU-aware flags, works after reinstalls).
	sed -i -E 's#^Exec=[^ ]*(chromium|chromium-browser|epiphany)( |$)#Exec=nova-browser\2#' \
		"/usr/local/share/applications/$BROWSER_DESKTOP"
fi
rename_app org.kde.discover.desktop "App Store"
rename_app libreoffice-writer.desktop "Writer (Word documents)"
rename_app libreoffice-impress.desktop "Impress (PowerPoint slides)"
rename_app libreoffice-calc.desktop "Calc (Excel spreadsheets)"
rename_app org.kde.kolourpaint.desktop "Paint"
rename_app org.kde.dolphin.desktop "Files"
rename_app org.kde.konsole.desktop "Terminal"
rename_app org.kde.kwrite.desktop "Text Editor"
rename_app org.kde.kcalc.desktop "Calculator"
rename_app org.kde.gwenview.desktop "Photos"
rename_app org.kde.kinfocenter.desktop "System Info"
rename_app org.kde.spectacle.desktop "Screenshot"
rename_app org.kde.plasma-systemmonitor.desktop "Task Manager"
rename_app systemsettings.desktop "Settings"
rename_app vlc.desktop "Video Player"
hide_app() {
	local src="/usr/share/applications/$1"
	[ -f "$src" ] || return 0
	{ grep -v '^NoDisplay=' "$src"; } > "/usr/local/share/applications/$1"
	sed -i '0,/^\[Desktop Entry\]/s//[Desktop Entry]\nNoDisplay=true/' "/usr/local/share/applications/$1"
}
for a in calamares.desktop vim.desktop python3.12.desktop htop.desktop org.kde.kded5.desktop \
	org.kde.kwalletd5.desktop kcm_trash.desktop ktelnetservice5.desktop \
	org.gnome.Epiphany.desktop org.kde.kmenuedit.desktop libreoffice-startcenter.desktop \
	libreoffice-xsltfilter.desktop org.kde.gwenview_importer.desktop; do
	[ "$a" = "$BROWSER_DESKTOP" ] && continue
	hide_app "$a"
done
update-desktop-database /usr/local/share/applications || true

if [ -n "$BROWSER_DESKTOP" ]; then
	cat > /etc/xdg/mimeapps.list <<EOM
[Default Applications]
text/html=$BROWSER_DESKTOP
x-scheme-handler/http=$BROWSER_DESKTOP
x-scheme-handler/https=$BROWSER_DESKTOP
x-scheme-handler/about=$BROWSER_DESKTOP
EOM
fi
# Chromium settings: NovaOS welcome page, no default-browser nag. (GPU or
# software rendering is chosen per machine by /usr/bin/nova-browser.)
# Firefox: NovaOS start page, KDE file dialogs, no first-run/default-browser
# nagging, smooth scrolling; updates come with system updates.
mkdir -p /etc/firefox/policies
cat > /etc/firefox/policies/policies.json <<'EOP'
{
  "policies": {
    "DisableAppUpdate": true,
    "DontCheckDefaultBrowser": true,
    "DisableTelemetry": true,
    "OverrideFirstRunPage": "",
    "OverridePostUpdatePage": "",
    "Homepage": {
      "URL": "file:///usr/share/novaos/welcome/index.html",
      "StartPage": "homepage"
    },
    "Preferences": {
      "widget.use-xdg-desktop-portal.file-picker": { "Value": 1, "Status": "default" },
      "general.smoothScroll": { "Value": true, "Status": "default" },
      "browser.tabs.inTitlebar": { "Value": 1, "Status": "default" }
    }
  }
}
EOP
# Firefox draws pages with WebRender. On UTM's virtual GPU (virgl) the
# hardware path loses all text, so use WebRender's fast software renderer.
if [ -d /usr/lib/firefox/defaults/pref ]; then
	cat > /usr/lib/firefox/defaults/pref/novaos.js <<'EOJ'
// NovaOS defaults
pref("gfx.webrender.software", true);
pref("gfx.webrender.software.opengl", false);
pref("layers.acceleration.disabled", false);
pref("widget.use-xdg-desktop-portal.file-picker", 1);
EOJ
fi
for d in /etc/chromium/policies/managed /etc/chromium-browser/policies/managed; do
	mkdir -p "$d"
	cat > "$d/novaos.json" <<'EOP'
{
  "HomepageLocation": "file:///usr/share/novaos/welcome/index.html",
  "HomepageIsNewTabPage": false,
  "ShowHomeButton": true,
  "RestoreOnStartup": 4,
  "RestoreOnStartupURLs": ["file:///usr/share/novaos/welcome/index.html"],
  "DefaultBrowserSettingEnabled": false,
  "MetricsReportingEnabled": false,
  "PromotionalTabsEnabled": false
}
EOP
done

# Taskbar pin + default browser point at the real browser entry.
sed -i "s#PLACEHOLDER_BROWSER#${BROWSER_DESKTOP:-org.gnome.Epiphany.desktop}#g" \
	/etc/xdg/kdeglobals \
	/usr/share/plasma/look-and-feel/org.novaos.*/contents/layouts/org.kde.plasma.desktop-layout.js

# --- App Store: Flathub ------------------------------------------------------------------
if command -v flatpak >/dev/null 2>&1; then
	if curl -fsSL --max-time 60 https://dl.flathub.org/repo/flathub.flatpakrepo -o /tmp/flathub.flatpakrepo; then
		flatpak remote-add --system --if-not-exists flathub /tmp/flathub.flatpakrepo || true
		mkdir -p /etc/flatpak/remotes.d
		cp /tmp/flathub.flatpakrepo /etc/flatpak/remotes.d/flathub.flatpakrepo
	else
		echo "WARNING: could not download the Flathub description (offline build)"
	fi
fi

# --- services -------------------------------------------------------------------------------
echo /usr/bin/sddm > /etc/X11/default-display-manager
systemctl enable sddm.service || true
systemctl set-default graphical.target
systemctl enable NetworkManager.service || true
systemctl enable systemd-resolved.service || true
systemctl enable spice-vdagentd.socket 2>/dev/null || systemctl enable spice-vdagentd.service 2>/dev/null || true
for u in apt-daily.timer apt-daily-upgrade.timer motd-news.timer e2scrub_all.timer \
	man-db.timer fstrim.timer; do
	systemctl disable "$u" 2>/dev/null || true
done
systemctl mask systemd-networkd-wait-online.service || true

# --- licence notices ---------------------------------------------------------------------
python3 - <<'EOF'
import os, re, subprocess
rows = []
out = subprocess.run(["dpkg-query", "-W", "-f=${Package}\t${Version}\n"], capture_output=True, text=True).stdout
for line in out.splitlines():
    pkg, ver = line.split("\t")
    lic = set()
    cp = f"/usr/share/doc/{pkg}/copyright"
    try:
        for m in re.finditer(r"^License:\s*(.+)$", open(cp, errors="replace").read(), re.M):
            lic.add(m.group(1).strip())
    except OSError:
        pass
    rows.append((pkg, ver, ", ".join(sorted(lic))[:120] or "see /usr/share/doc/%s" % pkg))
with open("/usr/share/doc/novaos/package-licenses.tsv", "w") as f:
    f.write("package\tversion\tdeclared licences (from Debian copyright files)\n")
    for r in rows:
        f.write("\t".join(r) + "\n")
print("licence table:", len(rows), "packages")
EOF


if [ -n "$UPDATE" ]; then
	update-grub 2>/dev/null || true
	echo "== NovaOS update customisation complete"
	exit 0
fi

# --- slimming: docs, man pages, rare translations, unused font weights -------
cat > /etc/dpkg/dpkg.cfg.d/01-novaos-slim <<'EOF2'
# Keep licence files, drop the rest of the docs, man pages and rare translations.
path-exclude=/usr/share/doc/*
path-include=/usr/share/doc/*/copyright
path-include=/usr/share/doc/novaos/*
path-exclude=/usr/share/man/*
path-exclude=/usr/share/help/*
path-exclude=/usr/share/locale/*
path-include=/usr/share/locale/locale.alias
path-include=/usr/share/locale/en*
path-include=/usr/share/locale/fr/*
path-include=/usr/share/locale/de/*
path-include=/usr/share/locale/es/*
path-include=/usr/share/locale/it/*
path-include=/usr/share/locale/nl/*
path-include=/usr/share/locale/pt*
path-include=/usr/share/locale/ro/*
EOF2
find /usr/share/doc -mindepth 1 ! -name copyright ! -path '/usr/share/doc/novaos*' -type f -delete
find /usr/share/doc -mindepth 1 -type d -empty -delete
rm -rf /usr/share/man/* /usr/share/help/*
find /usr/share/locale -mindepth 1 -maxdepth 1 -type d \
	! -name 'en*' ! -name fr ! -name de ! -name es ! -name it ! -name nl ! -name 'pt*' ! -name ro \
	-exec rm -rf {} +
rm -rf /usr/share/icons/ePapirus /usr/share/icons/ePapirus-Dark \
	/usr/share/icons/Humanity /usr/share/icons/Humanity-Dark \
	/usr/share/icons/ubuntu-mono-dark /usr/share/icons/ubuntu-mono-light
rm -f /var/cache/apt/*.bin
# Fonts: keep the everyday weights only.
find /usr/share/fonts/opentype/inter -name 'InterDisplay-*' -delete
for w in Black BlackItalic ExtraBold ExtraBoldItalic ExtraLight ExtraLightItalic Thin ThinItalic \
	LightItalic MediumItalic SemiBoldItalic; do
	rm -f "/usr/share/fonts/opentype/inter/Inter-$w.otf"
done
find /usr/share/fonts/truetype/jetbrains-mono -type f ! -name 'JetBrainsMono-Regular.ttf' \
	! -name 'JetBrainsMono-Bold.ttf' ! -name 'JetBrainsMono-Italic.ttf' -delete
# Character maps: UTF-8 is all NovaOS uses.
find /usr/share/i18n/charmaps -type f ! -name 'UTF-8.gz' -delete
fc-cache -f >/dev/null

# NovaOS targets virtual machines: drop kernel drivers for Wi-Fi, TV/webcam
# capture, InfiniBand, embedded audio, sensors and discrete GPUs. (A kernel
# update through apt brings the full set back.)
KVER="$(ls /lib/modules | sort -V | tail -1)"
K="/lib/modules/$KVER/kernel"
rm -rf "$K/drivers/net/wireless" "$K/drivers/media" "$K/drivers/infiniband" "$K/drivers/staging" \
	"$K/sound/soc" "$K/drivers/iio" "$K/drivers/gpu/drm/amd" "$K/drivers/gpu/drm/nouveau" \
	"$K/drivers/gpu/drm/i915" "$K/drivers/gpu/drm/radeon" "$K/drivers/gpu/drm/xe" \
	"$K/drivers/comedi" "$K/drivers/mtd" "$K/drivers/input/touchscreen" "$K/net/mac80211" \
	"$K/net/wireless" "$K/net/bluetooth" "$K/drivers/bluetooth" "$K/fs/bcachefs" "$K/fs/ocfs2" \
	"$K/drivers/scsi/lpfc" "$K/drivers/scsi/qla2xxx" "$K/drivers/scsi/qla4xxx" "$K/drivers/scsi/bfa" \
	"$K/drivers/scsi/mpt3sas" "$K/drivers/scsi/megaraid" "$K/drivers/scsi/be2iscsi" "$K/drivers/scsi/smartpqi" \
	"$K/drivers/scsi/aacraid" "$K/drivers/scsi/fnic" "$K/drivers/scsi/csiostor" "$K/drivers/scsi/qedi" \
	"$K/drivers/scsi/qedf" "$K/drivers/scsi/mpi3mr" "$K/drivers/scsi/pm8001" "$K/drivers/scsi/hisi_sas"
# Ethernet: keep Intel (e1000/e1000e) and Realtek (rtl8139/r8169), the NICs VMs emulate.
find "$K/drivers/net/ethernet" -mindepth 1 -maxdepth 1 -type d ! -name intel ! -name realtek -exec rm -rf {} +
depmod -a "$KVER"

# --- initramfs (includes casper live-boot hooks) -----------------------------------------
KVER="$(ls /lib/modules | sort -V | tail -1)"
update-initramfs -c -k "$KVER" 2>/dev/null || update-initramfs -u -k "$KVER"

apt-get clean
echo "== NovaOS customisation complete"
