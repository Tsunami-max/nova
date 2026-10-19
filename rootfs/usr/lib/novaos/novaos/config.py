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
    "refresh": None,                # None = highest available, else "144.00"
    "scale": None,                  # None = automatic, else 100/125/150/175/200
    "font_size": 10,
    "buttons": "right",             # right (Windows) | left (macOS)
    "desktop_icon_size": 56,
    "taskbar_position": "top",      # top | bottom
    "dock_apps": None,              # None = defaults
    "dock_position": "bottom",      # bottom | left | right
    "dock_icon_size": 48,
    "dock_autohide": "never",       # never | smart | always
}

DEFAULT_DOCK = ["thunar.desktop", "@browser", "xfce4-terminal.desktop", "novaos-notes.desktop",
                "org.gnome.Calculator.desktop", "novaos-settings.desktop", "xfce4-appfinder.desktop"]


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
    """Return {output: {"modes": [...], "rates": {mode: [rates]}, "current": "WxH",
    "rate": "60.00"}} for connected outputs."""
    r = run("xrandr", "--query")
    res, cur = {}, None
    if not r or r.returncode != 0:
        return res
    for line in r.stdout.splitlines():
        if " connected" in line:
            cur = line.split()[0]
            res[cur] = {"modes": [], "rates": {}, "current": None, "rate": None}
        elif cur and line.startswith("   "):
            parts = line.split()
            mode = parts[0]
            if mode not in res[cur]["modes"]:
                res[cur]["modes"].append(mode)
                res[cur]["rates"][mode] = []
            for tok in parts[1:]:
                rate = tok.rstrip("*+")
                try:
                    float(rate)
                except ValueError:
                    continue
                if rate not in res[cur]["rates"][mode]:
                    res[cur]["rates"][mode].append(rate)
                if "*" in tok:
                    res[cur]["current"] = mode
                    res[cur]["rate"] = rate
        elif not line.startswith(" "):
            cur = None
    return res


def primary_output():
    outs = outputs()
    for name, info in outs.items():
        return name, info
    return None, None


def apply_resolution(s):
    """Set resolution (or keep the current one) at the chosen or highest refresh rate."""
    name, info = primary_output()
    if not name:
        return False
    mode = s.get("resolution") or info["current"]
    if mode not in info["modes"]:
        return False
    rates = info["rates"].get(mode) or []
    want = s.get("refresh")
    if want not in rates:
        want = max(rates, key=float) if rates else None
    args = ["xrandr", "--output", name, "--mode", mode]
    if want:
        args += ["--rate", want]
    if mode == info["current"] and want == info["rate"]:
        return True
    r = run(*args)
    return bool(r and r.returncode == 0)


def auto_scale():
    """Pick a sensible UI scale from the screen width (high-DPI / Retina screens)."""
    name, info = primary_output()
    try:
        w = int((info or {}).get("current", "0x0").split("x")[0])
    except (ValueError, AttributeError):
        w = 0
    if w >= 3800:
        return 200
    if w >= 2500:
        return 150
    return 100


def apply_scale(s):
    scale = s.get("scale") or auto_scale()
    if scale >= 200:
        factor, dpi = 2, 96
    else:
        factor, dpi = 1, int(96 * scale / 100)
    xfconf_set("xsettings", "/Gdk/WindowScalingFactor", "int", factor)
    xfconf_set("xsettings", "/Xft/DPI", "int", dpi)
    xfconf_set("xsettings", "/Gtk/CursorThemeSize", "int", int(24 * scale / 100))
    return scale


# ---------------------------------------------------------------------------
# look & feel extras
# ---------------------------------------------------------------------------
def apply_extras(s):
    size = int(s.get("font_size", 10))
    xfconf_set("xsettings", "/Gtk/FontName", "string", "Inter %d" % size)
    xfconf_set("xsettings", "/Gtk/MonospaceFontName", "string", "JetBrains Mono %d" % size)
    xfconf_set("xfwm4", "/general/title_font", "string", "Inter Medium %d" % size)
    if s.get("buttons") == "left":
        xfconf_set("xfwm4", "/general/button_layout", "string", "CHM|O")
        xfconf_set("xsettings", "/Gtk/DecorationLayout", "string", "close,minimize,maximize:icon")
    else:
        xfconf_set("xfwm4", "/general/button_layout", "string", "O|HMC")
        xfconf_set("xsettings", "/Gtk/DecorationLayout", "string", "icon:minimize,maximize,close")
    xfconf_set("xfce4-desktop", "/desktop-icons/icon-size", "uint", int(s.get("desktop_icon_size", 56)))
    pos = {"top": "p=6;x=0;y=0", "bottom": "p=10;x=0;y=0"}.get(s.get("taskbar_position", "top"))
    if pos:
        xfconf_set("xfce4-panel", "/panels/panel-1/position", "string", pos)
    xfconf_set("xsettings", "/Gtk/EnableAnimations", "bool", s.get("effects") != "off")


# ---------------------------------------------------------------------------
# dock (panel-2)
# ---------------------------------------------------------------------------
APP_DIRS = [os.path.expanduser("~/.local/share/applications"), "/usr/local/share/applications",
            "/usr/share/applications"]


def find_desktop(app_id):
    for d in APP_DIRS:
        p = os.path.join(d, app_id)
        if os.path.exists(p):
            return p
    return None


def browser_desktop():
    for b in ("chromium.desktop", "chromium-browser.desktop", "org.gnome.Epiphany.desktop",
              "firefox.desktop", "firefox_firefox.desktop"):
        if find_desktop(b):
            return b
    return None


def dock_apps(s):
    apps = s.get("dock_apps") or DEFAULT_DOCK
    out = []
    for a in apps:
        if a == "@browser":
            a = browser_desktop()
        if a and find_desktop(a) and a not in out:
            out.append(a)
    return out


def apply_dock(s, restart=True):
    """Rebuild the dock (panel 2) from the saved app list and options."""
    apps = dock_apps(s)
    base = 200
    ids = []
    cfg = os.path.expanduser("~/.config/xfce4/panel")
    # drop launcher dirs of our previous dock
    for d in glob.glob(os.path.join(cfg, "launcher-2??")):
        shutil.rmtree(d, ignore_errors=True)
    for prop in xfconf_list("xfce4-panel"):
        m = prop.startswith("/plugins/plugin-2") and len(prop.split("/")[2]) == len("plugin-200")
        if m:
            run("xfconf-query", "-c", "xfce4-panel", "-p", prop, "-r", "-R")
    for i, app in enumerate(apps):
        pid = base + i
        d = os.path.join(cfg, "launcher-%d" % pid)
        os.makedirs(d, exist_ok=True)
        shutil.copy(find_desktop(app), os.path.join(d, app))
        xfconf_set("xfce4-panel", "/plugins/plugin-%d" % pid, "string", "launcher")
        xfconf_set_array("xfce4-panel", "/plugins/plugin-%d/items" % pid, "string", [app])
        ids.append(pid)
    sep = base + 90
    xfconf_set("xfce4-panel", "/plugins/plugin-%d" % sep, "string", "separator")
    xfconf_set("xfce4-panel", "/plugins/plugin-%d/style" % sep, "uint", 1)
    tasks = base + 91
    xfconf_set("xfce4-panel", "/plugins/plugin-%d" % tasks, "string", "tasklist")
    xfconf_set("xfce4-panel", "/plugins/plugin-%d/show-labels" % tasks, "bool", False)
    xfconf_set("xfce4-panel", "/plugins/plugin-%d/flat-buttons" % tasks, "bool", True)
    xfconf_set("xfce4-panel", "/plugins/plugin-%d/show-handle" % tasks, "bool", False)
    ids += [sep, tasks]
    pos = s.get("dock_position", "bottom")
    xfconf_set("xfce4-panel", "/panels/panel-2/position", "string",
               {"bottom": "p=10;x=0;y=0", "left": "p=7;x=0;y=0", "right": "p=3;x=0;y=0"}.get(pos, "p=10;x=0;y=0"))
    xfconf_set("xfce4-panel", "/panels/panel-2/mode", "uint", 0 if pos == "bottom" else 2)
    xfconf_set("xfce4-panel", "/panels/panel-2/size", "uint", int(s.get("dock_icon_size", 48)) + 8)
    xfconf_set("xfce4-panel", "/panels/panel-2/icon-size", "uint", int(s.get("dock_icon_size", 48)))
    xfconf_set("xfce4-panel", "/panels/panel-2/length", "uint", 1)
    xfconf_set("xfce4-panel", "/panels/panel-2/position-locked", "bool", True)
    xfconf_set("xfce4-panel", "/panels/panel-2/autohide-behavior", "uint",
               {"never": 0, "smart": 1, "always": 2}.get(s.get("dock_autohide", "never"), 0))
    xfconf_set_array("xfce4-panel", "/panels/panel-2/plugin-ids", "int", ids)
    r = run("xfconf-query", "-c", "xfce4-panel", "-p", "/panels")
    panels = [l.strip() for l in (r.stdout.splitlines() if r and r.returncode == 0 else []) if l.strip().isdigit()]
    if "2" not in panels:
        xfconf_set_array("xfce4-panel", "/panels", "int", [int(x) for x in panels] + [2])
    if restart:
        restart_panel()


def _panel_pids():
    r = subprocess.run(["pgrep", "-x", "xfce4-panel"], capture_output=True, text=True)
    return set(r.stdout.split())


def restart_panel():
    """Restart the panel so a new dock layout loads. Quit it, then start a fresh one
    unless the session manager already brought it back."""
    run("xfce4-panel", "--quit")
    for _ in range(20):
        if not _panel_pids():
            break
        time.sleep(0.25)
    time.sleep(1.5)
    if not _panel_pids():
        subprocess.Popen(["xfce4-panel"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         stdin=subprocess.DEVNULL, start_new_session=True)


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
    apply_resolution(s)
    apply_scale(s)
    apply_extras(s)
    apply_wallpaper(s)
    return apply_effects(s)
