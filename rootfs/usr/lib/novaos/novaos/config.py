"""NovaOS user settings: storage and application to the running desktop."""
import glob
import json
import os
import shutil
import subprocess
import time

from . import palette as P
from . import themegen

CONFIG_DIR = os.path.expanduser("~/.config/novaos")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")
USER_THEMES = os.path.expanduser("~/.local/share/themes")
WALLPAPER_DIR = "/usr/share/backgrounds/novaos"
PICOM_TEMPLATES = "/usr/share/novaos/picom"

DEFAULTS = {
    "mode": "dark",
    "accent": P.DEFAULT_ACCENT,
    "wallpaper": os.path.join(WALLPAPER_DIR, "nova-aurora.jpg"),
    "effects": "balanced",          # off | balanced | full
    "transparency": True,
    "taskbar_labels": False,
    "taskbar_size": 36,
    "clock_24h": True,
    "resolution": None,             # None = automatic, else "1920x1080"
}


def load():
    s = dict(DEFAULTS)
    try:
        with open(CONFIG_FILE) as f:
            s.update(json.load(f))
    except (OSError, ValueError):
        pass
    return s


def save(s):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(s, f, indent=2)
    os.replace(tmp, CONFIG_FILE)


# ---------------------------------------------------------------------------
# low-level helpers
# ---------------------------------------------------------------------------
def run(*cmd, check=False):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None


def xfconf_get(channel, prop):
    r = run("xfconf-query", "-c", channel, "-p", prop)
    return r.stdout.strip() if r and r.returncode == 0 else None


def xfconf_set(channel, prop, typ, value):
    if typ == "bool":
        value = "true" if value else "false"
    run("xfconf-query", "-c", channel, "-p", prop, "-n", "-t", typ, "-s", str(value))


def xfconf_set_array(channel, prop, typ, values):
    args = ["xfconf-query", "-c", channel, "-p", prop, "-n", "--force-array"]
    for v in values:
        args += ["-t", typ, "-s", str(v)]
    run(*args)


def xfconf_list(channel):
    r = run("xfconf-query", "-c", channel, "-l")
    return r.stdout.split() if r and r.returncode == 0 else []


def panel_plugin_ids(kind):
    ids = []
    for prop in xfconf_list("xfce4-panel"):
        if prop.count("/") == 2 and prop.startswith("/plugins/plugin-"):
            if xfconf_get("xfce4-panel", prop) == kind:
                ids.append(prop)
    return ids


def gsettings(schema, key, value):
    run("gsettings", "set", schema, key, value)


# ---------------------------------------------------------------------------
# appearance
# ---------------------------------------------------------------------------
def theme_name(mode):
    return themegen.THEME_NAMES[mode]


def ensure_theme(mode, accent):
    """System themes ship the default accent; custom accents live in ~/.local."""
    name = theme_name(mode)
    user_copy = os.path.join(USER_THEMES, name)
    if accent.lower() == P.DEFAULT_ACCENT:
        shutil.rmtree(user_copy, ignore_errors=True)
        return
    stamp = os.path.join(user_copy, ".nova-accent")
    try:
        with open(stamp) as f:
            if f.read().strip() == accent.lower():
                return
    except OSError:
        pass
    os.makedirs(USER_THEMES, exist_ok=True)
    themegen.generate(mode, accent, USER_THEMES)
    with open(stamp, "w") as f:
        f.write(accent.lower())


def _reload_named(channel, prop, name, placeholder):
    """Force running apps to re-read a theme whose files changed in place."""
    if xfconf_get(channel, prop) == name:
        xfconf_set(channel, prop, "string", placeholder)
        time.sleep(0.4)
    xfconf_set(channel, prop, "string", name)


def apply_theme(s, force_reload=False):
    mode, accent = s["mode"], s["accent"]
    ensure_theme(mode, accent)
    name = theme_name(mode)
    icons = "NovaOS-Dark" if mode == "dark" else "NovaOS"
    if force_reload:
        _reload_named("xsettings", "/Net/ThemeName", name, "Materia-compact")
        _reload_named("xfwm4", "/general/theme", name, "Default")
    else:
        xfconf_set("xsettings", "/Net/ThemeName", "string", name)
        xfconf_set("xfwm4", "/general/theme", "string", name)
    xfconf_set("xsettings", "/Net/IconThemeName", "string", icons)
    # GTK4 / libadwaita applications follow the GNOME colour-scheme key.
    gsettings("org.gnome.desktop.interface", "color-scheme",
              "prefer-dark" if mode == "dark" else "default")
    gsettings("org.gnome.desktop.interface", "gtk-theme", name)
    gsettings("org.gnome.desktop.interface", "icon-theme", icons)
    apply_panel(s)


def apply_panel(s):
    mode = s["mode"]
    r, g, b = P.CHROME[mode]["panel_rgb"]
    alpha = 0.82 if (s.get("transparency") and s.get("effects") != "off") else 1.0
    xfconf_set("xfce4-panel", "/panels/dark-mode", "bool", mode == "dark")
    xfconf_set("xfce4-panel", "/panels/panel-1/background-style", "uint", 1)
    xfconf_set_array("xfce4-panel", "/panels/panel-1/background-rgba", "double", [r, g, b, alpha])
    xfconf_set("xfce4-panel", "/panels/panel-1/size", "uint", int(s.get("taskbar_size", 36)))
    for p in panel_plugin_ids("tasklist"):
        xfconf_set("xfce4-panel", p + "/show-labels", "bool", bool(s.get("taskbar_labels")))
    for p in panel_plugin_ids("clock"):
        fmt = "%H:%M" if s.get("clock_24h", True) else "%I:%M %p"
        xfconf_set("xfce4-panel", p + "/digital-time-format", "string", fmt)
    for p in panel_plugin_ids("whiskermenu"):
        xfconf_set("xfce4-panel", p + "/menu-opacity", "int",
                   92 if (s.get("transparency") and s.get("effects") != "off") else 100)


def apply_wallpaper(s):
    path = s["wallpaper"]
    props = [p for p in xfconf_list("xfce4-desktop") if p.endswith("/last-image")]
    # Also cover monitors that have never had a wallpaper set yet.
    r = run("xrandr", "--query")
    if r and r.returncode == 0:
        for line in r.stdout.splitlines():
            if " connected" in line:
                out = line.split()[0]
                p = f"/backdrop/screen0/monitor{out}/workspace0/last-image"
                if p not in props:
                    props.append(p)
    for p in props:
        base = p.rsplit("/", 1)[0]
        xfconf_set("xfce4-desktop", base + "/image-style", "int", 5)  # zoomed
        xfconf_set("xfce4-desktop", base + "/last-image", "string", path)


def picom_running():
    r = run("pgrep", "-u", str(os.getuid()), "-x", "picom")
    return bool(r and r.returncode == 0)


def apply_effects(s):
    run("pkill", "-u", str(os.getuid()), "-x", "picom")
    level = s.get("effects", "balanced")
    if level == "off":
        xfconf_set("xfwm4", "/general/use_compositing", "bool", False)
        return "off"
    xfconf_set("xfwm4", "/general/use_compositing", "bool", False)
    for attempt in ([level, "balanced"] if level == "full" else [level]):
        conf = os.path.join(PICOM_TEMPLATES, attempt + ".conf")
        time.sleep(0.3)
        subprocess.Popen(["picom", "--config", conf], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        for _ in range(10):
            time.sleep(0.3)
            if picom_running():
                return attempt
    # picom could not start: fall back to xfwm4's built-in compositor.
    xfconf_set("xfwm4", "/general/use_compositing", "bool", True)
    return "xfwm4"


# ---------------------------------------------------------------------------
# display
# ---------------------------------------------------------------------------
def outputs():
    """Return {output: {"modes": [...], "current": "WxH"}} for connected outputs."""
    r = run("xrandr", "--query")
    res, cur = {}, None
    if not r or r.returncode != 0:
        return res
    for line in r.stdout.splitlines():
        if " connected" in line:
            cur = line.split()[0]
            res[cur] = {"modes": [], "current": None}
        elif cur and line.startswith("   "):
            parts = line.split()
            mode = parts[0]
            if mode not in res[cur]["modes"]:
                res[cur]["modes"].append(mode)
            if "*" in line:
                res[cur]["current"] = mode
        elif not line.startswith(" "):
            cur = None
    return res


def apply_resolution(s):
    mode = s.get("resolution")
    if not mode:
        return True
    outs = outputs()
    ok = True
    for name, info in outs.items():
        if mode in info["modes"]:
            r = run("xrandr", "--output", name, "--mode", mode)
            ok = ok and bool(r and r.returncode == 0)
            break
    else:
        ok = False
    return ok


# ---------------------------------------------------------------------------
# keyboard
# ---------------------------------------------------------------------------
def current_layout():
    return xfconf_get("keyboard-layout", "/Default/XkbLayout") or "us"


def set_layout(layout):
    xfconf_set("keyboard-layout", "/Default/XkbDisable", "bool", False)
    xfconf_set("keyboard-layout", "/Default/XkbLayout", "string", layout)
    xfconf_set("keyboard-layout", "/Default/XkbVariant", "string", "")
    run("setxkbmap", layout)


def apply_all(s, force_reload=False):
    apply_theme(s, force_reload)
    apply_wallpaper(s)
    apply_resolution(s)
    return apply_effects(s)
