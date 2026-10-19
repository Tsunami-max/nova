#!/usr/bin/env python3
"""Runs at every login: applies NovaOS settings and prepares the desktop."""
import glob
import hashlib
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from novaos import config as C  # noqa: E402

LIVE = "boot=casper" in open("/proc/cmdline").read()


def desktop_dir():
    r = C.run("xdg-user-dir", "DESKTOP")
    return r.stdout.strip() if r and r.returncode == 0 and r.stdout.strip() else os.path.expanduser("~/Desktop")


def trust_launchers(ddir):
    """Mark .desktop shortcuts as trusted so xfdesktop runs them without a warning."""
    for f in glob.glob(os.path.join(ddir, "*.desktop")):
        os.chmod(f, 0o755)
        with open(f, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        C.run("gio", "set", "-t", "string", f, "metadata::xfce-exe-checksum", digest)
        C.run("gio", "set", "-t", "string", f, "metadata::trusted", "true")


def main():
    ddir = desktop_dir()
    os.makedirs(ddir, exist_ok=True)
    first = not os.path.exists(C.CONFIG_FILE)

    # Desktop shortcuts (copied once per user; the user may delete them).
    marker = os.path.expanduser("~/.config/novaos/.shortcuts-done")
    if not os.path.exists(marker):
        for f in glob.glob("/usr/share/novaos/desktop/*.desktop"):
            shutil.copy(f, ddir)
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        open(marker, "w").close()
    installer = os.path.join(ddir, "novaos-install.desktop")
    if LIVE and os.path.exists("/usr/bin/calamares"):
        shutil.copy("/usr/share/applications/novaos-install.desktop", installer)
    elif os.path.exists(installer):
        os.remove(installer)
    trust_launchers(ddir)

    s = C.load()
    in_vm = False
    r = C.run("systemd-detect-virt", "-q", "--vm")
    if r and r.returncode == 0:
        in_vm = True
    if first and in_vm:
        # VMs have no 3D acceleration: start with effects off for smoothness.
        s["effects"] = "off"
        s["transparency"] = False
    if first:
        C.save(s)
    # Wait for xfconfd / xfsettingsd to be up before applying settings.
    for _ in range(20):
        if C.xfconf_get("xsettings", "/Net/ThemeName") is not None:
            break
        time.sleep(0.5)
    # Screen blanking just looks like a frozen VM window, so turn it off in VMs.
    r = C.run("systemd-detect-virt", "-q", "--vm")
    if r and r.returncode == 0:
        C.run("xset", "s", "off")
        C.run("xset", "-dpms")
    used = C.apply_all(s)
    print("novaos-session-init: effects =", used)
    # Panel layout may still be initialising; re-apply panel colours once more.
    time.sleep(3)
    C.apply_panel(s)
    C.apply_wallpaper(s)
    # Build the dock from the saved app list (the first time, or after an upgrade).
    dock_marker = os.path.expanduser("~/.config/novaos/.dock-v1")
    if not os.path.exists(dock_marker):
        for _ in range(30):
            if subprocess.run(["pgrep", "-x", "xfce4-panel"], capture_output=True).returncode == 0:
                break
            time.sleep(0.5)
        C.apply_dock(s)
        open(dock_marker, "w").close()


if __name__ == "__main__":
    main()
