#!/bin/sh
# NovaOS session helper (autostart): live-session installer shortcut, and a
# one-time hint when the virtual machine has no graphics acceleration.
DESK="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
mkdir -p "$DESK"
if grep -q "boot=casper" /proc/cmdline && [ -x /usr/bin/calamares ]; then
	cp /usr/share/applications/novaos-install.desktop "$DESK/"
	chmod +x "$DESK/novaos-install.desktop"
fi
sleep 8
if [ "$(/usr/lib/novaos/gl-check.sh)" != yes ] && systemd-detect-virt -q --vm; then
	STAMP="${XDG_RUNTIME_DIR:-/tmp}/novaos-gpu-hint"
	[ -e "$STAMP" ] && exit 0
	touch "$STAMP"
	kdialog --title "NovaOS runs without graphics acceleration" --passivepopup \
"Everything is drawn by the processor, so NovaOS and the browser will feel slow.

Fix in UTM (takes 1 minute):
1. Shut down NovaOS.
2. In UTM, select the VM → Edit (sliders icon) → Display.
3. Emulated Display Card: choose “virtio-gpu-gl-pci (GPU Supported)”.
4. Save and start NovaOS again.

Check later in Start → Info Center → Graphics." 60
fi
