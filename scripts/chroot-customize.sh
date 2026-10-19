#!/bin/bash
# Runs INSIDE the image (chroot) after the NovaOS overlay has been copied in.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
NOVA_VERSION="${NOVA_VERSION:-1.0}"
echo "== NovaOS customisation ($NOVA_VERSION, ${NOVA_ARCH:-?})"

# --- locale -------------------------------------------------------------------
sed -i 's/^# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen 2>/dev/null || echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
locale-gen en_US.UTF-8
update-locale LANG=en_US.UTF-8

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
echo "novaos" > /etc/hostname

# --- themes, icons, fonts -----------------------------------------------------
python3 - <<'EOF'
import sys
sys.path.insert(0, "/usr/lib/novaos")
from novaos import themegen, palette
for mode in ("dark", "light"):
    print("theme:", themegen.generate(mode, palette.DEFAULT_ACCENT, "/usr/share/themes"))
EOF
for t in NovaOS NovaOS-Dark; do gtk-update-icon-cache -f -t "/usr/share/icons/$t" || true; done
gtk-update-icon-cache -f -t /usr/share/icons/Papirus || true
gtk-update-icon-cache -f -t /usr/share/icons/Papirus-Dark || true
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
	local src="/usr/share/applications/$1"
	[ -f "$src" ] || return 0
	sed "0,/^Name=.*/s//Name=$2/" "$src" | sed '/^Name\[/d' > "/usr/local/share/applications/$1"
}
rename_app thunar.desktop "Files"
# Main browser: Chromium when installed, otherwise GNOME Web.
BROWSER_DESKTOP=""
for b in chromium.desktop chromium-browser.desktop org.gnome.Epiphany.desktop; do
	if [ -f "/usr/share/applications/$b" ]; then BROWSER_DESKTOP="$b"; break; fi
done
[ -n "$BROWSER_DESKTOP" ] && rename_app "$BROWSER_DESKTOP" "Web Browser"
rename_app xfce4-terminal.desktop "Terminal"
rename_app org.xfce.ristretto.desktop "Image Viewer"
rename_app org.xfce.mousepad.desktop "Text Editor"
rename_app xfce4-taskmanager.desktop "Task Manager"
rename_app xfce4-screenshooter.desktop "Screenshot"
rename_app xfce4-appfinder.desktop "App Launcher"
rename_app xfce-settings-manager.desktop "Advanced Settings"
rename_app pavucontrol.desktop "Volume Mixer"
hide_app() {
	local src="/usr/share/applications/$1"
	[ -f "$src" ] || return 0
	{ grep -v '^NoDisplay=' "$src"; } > "/usr/local/share/applications/$1"
	sed -i '0,/^\[Desktop Entry\]/s//[Desktop Entry]\nNoDisplay=true/' "/usr/local/share/applications/$1"
}
for a in calamares.desktop picom.desktop xfce4-mail-reader.desktop \
	vim.desktop python3.12.desktop \
	htop.desktop org.kde.kded5.desktop org.kde.kwalletd5.desktop kcm_trash.desktop \
	ktelnetservice5.desktop xfce4-about.desktop; do
	hide_app "$a"
done
update-desktop-database /usr/local/share/applications || true

# Desktop shortcuts copied into each user's Desktop at first login.
mkdir -p /usr/share/novaos/desktop
for a in novaos-settings.desktop novaos-notes.desktop; do
	cp "/usr/share/applications/$a" /usr/share/novaos/desktop/
done
for a in $BROWSER_DESKTOP xfce4-terminal.desktop; do
	[ -f "/usr/local/share/applications/$a" ] && cp "/usr/local/share/applications/$a" /usr/share/novaos/desktop/
done
# Make it the default browser everywhere (panel launcher, links, xdg-open).
# A NovaOS-specific helper so "Web Browser" never asks which app to use.
BROWSER_BIN="$(command -v chromium || command -v chromium-browser || command -v epiphany || true)"
mkdir -p /etc/xdg/xfce4 /usr/share/xfce4/helpers
if [ -n "$BROWSER_BIN" ]; then
	cat > /usr/share/xfce4/helpers/novaos-browser.desktop <<EOH
[Desktop Entry]
NoDisplay=true
Version=1.0
Encoding=UTF-8
Type=X-XFCE-Helper
X-XFCE-Category=WebBrowser
X-XFCE-CommandsWithParameter=$BROWSER_BIN "%s"
Icon=novaos-browser
Name=NovaOS Web Browser
X-XFCE-Commands=$BROWSER_BIN
X-XFCE-Binaries=$(basename "$BROWSER_BIN");
EOH
	printf 'WebBrowser=novaos-browser\n' > /etc/xdg/xfce4/helpers.rc
fi
if [ -n "$BROWSER_DESKTOP" ]; then
	cat > /etc/xdg/mimeapps.list <<EOM
[Default Applications]
text/html=$BROWSER_DESKTOP
x-scheme-handler/http=$BROWSER_DESKTOP
x-scheme-handler/https=$BROWSER_DESKTOP
x-scheme-handler/about=$BROWSER_DESKTOP
EOM
fi
# Chromium settings for VMs: NovaOS welcome page, no GPU (software rendering
# is more stable without 3D acceleration), no sign-in nag.
for d in /etc/chromium/policies/managed /etc/chromium-browser/policies/managed; do
	mkdir -p "$d"
	cat > "$d/novaos.json" <<'EOP'
{
  "HomepageLocation": "file:///usr/share/novaos/welcome/index.html",
  "HomepageIsNewTabPage": false,
  "ShowHomeButton": true,
  "RestoreOnStartup": 4,
  "RestoreOnStartupURLs": ["file:///usr/share/novaos/welcome/index.html"],
  "HardwareAccelerationModeEnabled": false,
  "DefaultBrowserSettingEnabled": false,
  "MetricsReportingEnabled": false,
  "PromotionalTabsEnabled": false
}
EOP
done

# picom is started by NovaOS settings, not by its own autostart entry.
if ! grep -q '^Hidden=true' /etc/xdg/autostart/picom.desktop 2>/dev/null; then
	echo "Hidden=true" >> /etc/xdg/autostart/picom.desktop
fi
# The MATE polkit agent excludes nothing relevant; keep only our XFCE entry.
rm -f /etc/xdg/autostart/polkit-mate-authentication-agent-1.desktop

# --- keyboard shortcuts --------------------------------------------------------------
python3 - <<'EOF'
import xml.etree.ElementTree as ET
p = "/etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-keyboard-shortcuts.xml"
tree = ET.parse(p)
root = tree.getroot()
default = root.find("./property[@name='commands']/property[@name='default']")
extra = {"<Super>i": "nova-settings", "<Super>n": "nova-notes", "<Super>t": "xfce4-terminal"}
for key, cmd in extra.items():
    for old in default.findall("property"):
        if old.get("name") == key:
            default.remove(old)
    ET.SubElement(default, "property", {"name": key, "type": "string", "value": cmd})
wm = root.find("./property[@name='xfwm4']/property[@name='default']")
for old in wm.findall("property"):
    if old.get("name") == "<Super>d":
        wm.remove(old)
ET.SubElement(wm, "property", {"name": "<Super>d", "type": "string", "value": "show_desktop_key"})
tree.write(p, encoding="UTF-8", xml_declaration=True)
EOF

# --- session ------------------------------------------------------------------------------
S=/etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-session.xml
python3 - "$S" <<'EOF'
import sys, xml.etree.ElementTree as ET
p = sys.argv[1]
tree = ET.parse(p); root = tree.getroot()
def ensure(parent, name, typ=None, value=None):
    for c in parent.findall("property"):
        if c.get("name") == name:
            if value is not None:
                c.set("type", typ); c.set("value", value)
            return c
    attrs = {"name": name, "type": typ or "empty"}
    if value is not None:
        attrs["value"] = value
    return ET.SubElement(parent, "property", attrs)
general = ensure(root, "general")
ensure(general, "SaveOnExit", "bool", "false")
shutdown = ensure(root, "shutdown")
for k in ("ShowSuspend", "ShowHibernate", "ShowHybridSleep", "LockScreen"):
    ensure(shutdown, k, "bool", "false")
tree.write(p, encoding="UTF-8", xml_declaration=True)
EOF

# --- services -------------------------------------------------------------------------------
echo /usr/sbin/lightdm > /etc/X11/default-display-manager
systemctl enable lightdm.service || true
systemctl set-default graphical.target
systemctl enable NetworkManager.service || true
systemctl enable systemd-resolved.service || true
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


# --- slimming (keeps the ISO small enough to download as one file) -----------
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
apt-get -y purge fonts-noto-core fonts-noto-color-emoji 2>/dev/null || true
rm -rf /usr/share/icons/Papirus-Light /usr/share/icons/ePapirus /usr/share/icons/ePapirus-Dark \
	/usr/share/icons/Humanity /usr/share/icons/Humanity-Dark \
	/usr/share/icons/ubuntu-mono-dark /usr/share/icons/ubuntu-mono-light
# Papirus: keep only the 24 px set plus symbolic icons. They are SVGs, so GTK
# renders them sharply at every other size; this saves well over 100 MB.
python3 - <<'PY'
import os, re, shutil
KEEP = ("24x24", "24x24@2x", "symbolic")
for theme in ("Papirus", "Papirus-Dark"):
    root = f"/usr/share/icons/{theme}"
    idx = os.path.join(root, "index.theme")
    if not os.path.exists(idx):
        continue
    for d in os.listdir(root):
        p = os.path.join(root, d)
        if (os.path.isdir(p) or os.path.islink(p)) and d not in KEEP and re.match(r"^\d+x\d+", d):
            if os.path.islink(p):
                os.remove(p)
            else:
                shutil.rmtree(p)
    text = open(idx).read()
    m = re.search(r"^Directories=(.*)$", text, re.M)
    dirs = [d for d in m.group(1).split(",") if d.split("/")[0] in KEEP]
    text = text.replace(m.group(0), "Directories=" + ",".join(dirs))
    m = re.search(r"^ScaledDirectories=(.*)$", text, re.M)
    if m:
        sd = [d for d in m.group(1).split(",") if d.split("/")[0] in KEEP]
        text = text.replace(m.group(0), "ScaledDirectories=" + ",".join(sd))
    open(idx, "w").write(text)
    print(theme, "icon dirs kept:", len(dirs))
PY
gtk-update-icon-cache -f -t /usr/share/icons/Papirus || true
gtk-update-icon-cache -f -t /usr/share/icons/Papirus-Dark || true
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
