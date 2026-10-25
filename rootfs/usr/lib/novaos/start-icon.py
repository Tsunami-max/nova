#!/usr/bin/env python3
"""Before Plasma starts: give every Start menu button the NovaOS logo.

Runs at each login unless switched off in NovaOS Style (novaosrc [Start]
NovaIcon=false), so the logo comes back even after applying another theme or
layout. Works on the saved panel config, so nothing flickers.
"""
import os
import re
import subprocess

ICON = "/usr/share/icons/NovaOS/scalable/apps/novaos-start.svg"
MENUS = {"org.kde.plasma.kickoff", "org.kde.plasma.kicker", "org.kde.plasma.kickerdash",
         "org.kde.plasma.simplemenu", "org.kde.plasma.applicationlauncher"}
cfg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
path = os.path.join(cfg, "plasma-org.kde.plasma.desktop-appletsrc")


def setting():
    try:
        r = subprocess.run(["kreadconfig5", "--file", "novaosrc", "--group", "Start", "--key", "NovaIcon",
                            "--default", "true"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() != "false"
    except (OSError, subprocess.SubprocessError):
        return True


if os.path.exists(ICON) and os.path.exists(path) and setting():
    lines = open(path, encoding="utf-8").read().split("\n")
    head = re.compile(r"^\[Containments\]\[(\d+)\]\[Applets\]\[(\d+)\]$")
    menus = []
    cur = None
    for line in lines:
        m = head.match(line)
        if m:
            cur = m.groups()
        elif line.startswith("["):
            cur = None
        elif cur and line.startswith("plugin=") and line[7:].strip() in MENUS:
            menus.append(cur)
    changed = False
    for c, a in menus:
        sec = "[Containments][%s][Applets][%s][Configuration][General]" % (c, a)
        if sec in lines:
            i = lines.index(sec) + 1
            j = i
            while j < len(lines) and not lines[j].startswith("["):
                j += 1
            keys = [k for k in range(i, j) if lines[k].startswith("icon=")]
            if keys:
                if lines[keys[0]] != "icon=" + ICON:
                    lines[keys[0]] = "icon=" + ICON
                    changed = True
            else:
                lines.insert(i, "icon=" + ICON)
                changed = True
        else:
            while lines and lines[-1] == "":
                lines.pop()
            lines += ["", sec, "icon=" + ICON, ""]
            changed = True
    if changed:
        tmp = path + ".novaos"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        os.replace(tmp, path)
