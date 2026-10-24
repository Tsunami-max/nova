#!/usr/bin/env python3
"""NovaOS Style - one window to make NovaOS look and work the way you want.

Pages: Look, Wallpaper, Taskbar, Windows & effects, Text & pointer,
Start-up & updates, Backup. Everything is applied with KDE Plasma's own
tools and config files, so System Settings shows the same choices afterwards.
"""
import glob
import os
import shutil
import subprocess
import sys
import tarfile
import threading
import time

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, GLib, Gtk  # noqa: E402

GLib.set_prgname("novaos-style")

STYLES = [
    ("org.novaos.desktop", "NovaOS", "Centred taskbar, dark (Windows 11 style)", "desktop"),
    ("org.novaos.light", "NovaOS Light", "Centred taskbar, light", "light"),
    ("org.novaos.mac", "NovaOS Mac", "Top menu bar + dock (macOS style)", "mac"),
    ("org.novaos.classic", "NovaOS Classic", "Full taskbar, Start on the left (Windows 10 style)", "classic"),
]
ACCENTS = [("Nova", "#7c88ff"), ("Blue", "#3b82f6"), ("Sky", "#0ea5e9"), ("Teal", "#14b8a6"),
           ("Green", "#22c55e"), ("Lime", "#84cc16"), ("Amber", "#f59e0b"), ("Orange", "#f97316"),
           ("Red", "#ef4444"), ("Rose", "#f43f5e"), ("Pink", "#ec4899"), ("Violet", "#a855f7"),
           ("Indigo", "#6366f1"), ("Brown", "#a16207"), ("Graphite", "#8a93a6")]
PREVIEWS = "/usr/share/novaos/styles"
CHANGEICONS = (glob.glob("/usr/lib/*/libexec/plasma-changeicons") + glob.glob("/usr/libexec/plasma-changeicons")
               + [""])[0]
WALLPAPERS = "/usr/share/wallpapers"
HOME = os.path.expanduser("~")
CFG = os.environ.get("XDG_CONFIG_HOME", os.path.join(HOME, ".config"))
LIVE = os.path.isdir("/run/casper") or "boot=casper" in open("/proc/cmdline").read()
AUTOLOGIN_CONF = "/etc/sddm.conf.d/60-novaos-autologin.conf"

# Settings that make up "your NovaOS" (for Backup / Restore).
BACKUP_CONFIG = ["kdeglobals", "kwinrc", "kwinrulesrc", "plasmarc", "plasmashellrc",
                 "plasma-org.kde.plasma.desktop-appletsrc", "kcminputrc", "kxkbrc", "breezerc",
                 "kscreenlockerrc", "ksplashrc", "kglobalshortcutsrc", "khotkeysrc", "dolphinrc",
                 "konsolerc", "katerc", "kwriterc", "gwenviewrc", "okularpartrc", "spectaclerc",
                 "powermanagementprofilesrc", "Kvantum", "gtk-3.0", "gtk-4.0", "gtkrc", "gtkrc-2.0",
                 "novaosrc", "kcmfonts", "kscreenrc", "mimeapps.list", "user-dirs.dirs",
                 "libreoffice", "vlc", "autostart"]
BACKUP_DATA = [".local/share/konsole", ".local/share/plasma", ".local/share/color-schemes",
               ".local/share/wallpapers", ".local/share/icons", ".local/share/kxmlgui5",
               ".local/share/Trash/../user-places.xbel", ".local/share/kwin", ".local/share/aurorae",
               ".local/share/applications"]
BACKUP_FIREFOX = [".mozilla"]

CSS = b"""
.title { font-size: 20pt; font-weight: 800; }
.ptitle { font-size: 16pt; font-weight: 800; }
.sub { opacity: 0.65; }
.section { font-weight: 700; font-size: 11pt; margin-top: 10px; }
.card { background-color: alpha(@theme_fg_color, 0.05); border-radius: 12px; padding: 12px 14px; }
.style-btn { padding: 6px; border-radius: 12px; }
.swatch { min-width: 30px; min-height: 30px; border-radius: 999px; padding: 0; }
.thumb { padding: 3px; border-radius: 8px; }
stacksidebar row { padding: 10px 14px; }
"""


def run(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.SubprocessError):
        return None


def kwrite(file, group, key, value):
    groups = group if isinstance(group, (list, tuple)) else [group]
    args = ["kwriteconfig5", "--file", file]
    for g in groups:
        args += ["--group", g]
    run(*args, "--key", key, str(value))


def kread(file, group, key, default=""):
    groups = group if isinstance(group, (list, tuple)) else [group]
    args = ["kreadconfig5", "--file", file]
    for g in groups:
        args += ["--group", g]
    r = run(*args, "--key", key, "--default", default)
    return r.stdout.strip() if r and r.returncode == 0 else default


def shell_script(js):
    r = run("qdbus", "org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.evaluateScript", js)
    return r.stdout.strip() if r else ""


def kwin_reconfigure():
    run("qdbus", "org.kde.KWin", "/KWin", "reconfigure")


def kwin_effect(names, on):
    for n in names:
        run("qdbus", "org.kde.KWin", "/Effects",
            "org.kde.kwin.Effects.%s" % ("loadEffect" if on else "unloadEffect"), n)


def notify_change(kind):
    # KGlobalSettings: 0 palette, 1 fonts, 2 style, 3 settings, 4 icons, 5 cursor
    run("dbus-send", "--session", "--type=signal", "/KGlobalSettings",
        "org.kde.KGlobalSettings.notifyChange", "int32:%d" % kind, "int32:0")


def restart_plasmashell():
    run("qdbus", "org.kde.plasmashell", "/MainApplication", "quit")
    for _ in range(40):
        r = run("pgrep", "-x", "plasmashell")
        if not r or r.returncode != 0:
            break
        time.sleep(0.25)
    else:
        run("pkill", "-x", "plasmashell")
        time.sleep(1)
    starter = ["kstart5", "plasmashell"] if shutil.which("kstart5") else ["plasmashell"]
    subprocess.Popen(starter, start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def label(text, css=None, wrap=True):
    lb = Gtk.Label(label=text, xalign=0)
    lb.set_line_wrap(wrap)
    if css:
        lb.get_style_context().add_class(css)
    return lb


def row(title, widget, sub=None):
    box = Gtk.Box(spacing=12)
    v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    v.pack_start(label(title), False, False, 0)
    if sub:
        v.pack_start(label(sub, "sub"), False, False, 0)
    box.pack_start(v, True, True, 0)
    widget.set_valign(Gtk.Align.CENTER)
    box.pack_end(widget, False, False, 0)
    return box


def card(*children):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    box.get_style_context().add_class("card")
    for c in children:
        box.pack_start(c, False, False, 0)
    return box


def combo(options, current, callback):
    c = Gtk.ComboBoxText()
    for k, t in options:
        c.append(k, t)
    if not c.set_active_id(current):
        c.set_active(0)
    c.connect("changed", callback)
    return c


def switch(active, callback):
    s = Gtk.Switch(active=active)
    s.connect("notify::active", lambda w, _p: callback(w.get_active()))
    return s


def button(text, cb):
    b = Gtk.Button(label=text)
    b.connect("clicked", lambda _b: cb())
    return b


def launch(*cmd):
    try:
        subprocess.Popen(cmd, start_new_session=True)
    except OSError:
        pass


def wallpapers():
    out = []
    try:
        names = sorted(os.listdir(WALLPAPERS))
    except OSError:
        return out
    for n in names:
        d = os.path.join(WALLPAPERS, n, "contents", "images")
        if not os.path.isdir(d):
            continue
        imgs = sorted(os.listdir(d), key=lambda f: os.path.getsize(os.path.join(d, f)))
        imgs = [i for i in imgs if not i.startswith(".")]
        if imgs:
            out.append((n, os.path.join(d, imgs[0]), os.path.join(WALLPAPERS, n)))
    return out


def font_families():
    r = run("fc-list", ":", "family")
    fams = set()
    if r:
        for line in r.stdout.splitlines():
            fams.add(line.split(",")[0].strip())
    wanted = ["Inter", "Noto Sans", "Ubuntu", "Cantarell", "Roboto", "DejaVu Sans", "Carlito",
              "JetBrains Mono"]
    return [f for f in wanted if f in fams] or ["Inter"]


def current_font():
    f = kread("kdeglobals", "General", "font", "Inter,10,-1,5,50,0,0,0,0,0").split(",")
    try:
        return f[0], str(int(float(f[1])))
    except (IndexError, ValueError):
        return "Inter", "10"


def autologin_user():
    for path in (AUTOLOGIN_CONF, "/etc/sddm.conf"):
        try:
            inside = False
            for line in open(path):
                line = line.strip()
                if line.startswith("["):
                    inside = line == "[Autologin]"
                elif inside and line.startswith("User=") and line[5:]:
                    return line[5:]
        except OSError:
            pass
    for path in glob.glob("/etc/sddm.conf.d/*.conf"):
        if "live" in path:
            continue
        try:
            txt = open(path).read()
            if "[Autologin]" in txt:
                for line in txt.splitlines():
                    if line.startswith("User=") and line[5:]:
                        return line[5:]
        except OSError:
            pass
    return ""


def build_info():
    info = {}
    try:
        for line in open("/etc/novaos/build"):
            if "=" in line:
                k, v = line.strip().split("=", 1)
                info[k] = v
    except OSError:
        pass
    return info


class StyleWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="NovaOS Style")
        self.set_default_size(1120, 800)
        dark = kread("kdeglobals", "General", "ColorScheme", "NovaOSDark") != "NovaOSLight"
        settings = Gtk.Settings.get_default()
        settings.set_property("gtk-application-prefer-dark-theme", dark)
        if dark and os.path.isdir("/usr/share/themes/Breeze-Dark/gtk-3.0"):
            settings.set_property("gtk-theme-name", "Breeze-Dark")
        self.set_icon_name("novaos-wallpapers")
        self.status = label("", "sub")

        outer = Gtk.Box()
        self.add(outer)
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        side = Gtk.StackSidebar(stack=self.stack)
        side.set_size_request(220, -1)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hdr = label("NovaOS Style", "title")
        hdr.set_margin_start(16)
        hdr.set_margin_top(18)
        hdr.set_margin_bottom(10)
        left.pack_start(hdr, False, False, 0)
        left.pack_start(side, True, True, 0)
        self.status.set_margin_start(16)
        self.status.set_margin_bottom(12)
        self.status.set_max_width_chars(24)
        left.pack_start(self.status, False, False, 0)
        outer.pack_start(left, False, False, 0)
        outer.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
        outer.pack_start(self.stack, True, True, 0)

        self.page_look()
        self.page_wallpaper()
        self.page_taskbar()
        self.page_windows()
        self.page_text()
        self.page_startup()
        self.page_backup()

    def page(self, name, title, intro):
        sc = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(24)
        sc.add(box)
        box.pack_start(label(title, "ptitle"), False, False, 0)
        box.pack_start(label(intro, "sub"), False, False, 0)
        self.stack.add_titled(sc, name, title)
        return box

    def section(self, box, title, *rows):
        box.pack_start(label(title, "section"), False, False, 0)
        box.pack_start(card(*rows), False, False, 0)

    # -- pages ------------------------------------------------------------------
    def page_look(self):
        box = self.page("look", "Look", "Pick a layout and colours. Changes apply right away.")
        flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=4,
                           column_spacing=10, row_spacing=10, homogeneous=True)
        current = kread("kdeglobals", "KDE", "LookAndFeelPackage", "org.novaos.desktop")
        for pid, name, desc, img in STYLES:
            b = Gtk.Button()
            b.get_style_context().add_class("style-btn")
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(os.path.join(PREVIEWS, img + ".jpg"),
                                                              200, 112, True)
                v.pack_start(Gtk.Image.new_from_pixbuf(pb), False, False, 0)
            except GLib.Error:
                pass
            t = label(("✓ " if pid == current else "") + name)
            t.set_xalign(0.5)
            v.pack_start(t, False, False, 0)
            d = label(desc, "sub")
            d.set_xalign(0.5)
            d.set_justify(Gtk.Justification.CENTER)
            d.set_max_width_chars(24)
            v.pack_start(d, False, False, 0)
            b.add(v)
            b.connect("clicked", self.on_style, pid, name)
            flow.add(b)
        self.section(box, "Layout", flow,
                     label("Changing the layout replaces the taskbar and its pinned apps.", "sub"))

        mode_now = kread("kdeglobals", "General", "ColorScheme", "NovaOSDark")
        mode = combo([("NovaOSDark", "Dark"), ("NovaOSLight", "Light"), ("BreezeDark", "Breeze Dark"),
                      ("BreezeLight", "Breeze Light"), ("BreezeClassic", "Breeze Classic")],
                     mode_now, self.on_mode)
        sw = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=15,
                         column_spacing=6, row_spacing=6)
        prov = Gtk.CssProvider()
        css = ""
        for i, (name, hexc) in enumerate(ACCENTS):
            b = Gtk.Button()
            b.set_name("acc%d" % i)
            b.set_tooltip_text(name)
            b.set_size_request(34, 34)
            b.get_style_context().add_class("swatch")
            b.get_style_context().add_provider(prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            css += "#acc%d { background: %s; } " % (i, hexc)
            b.connect("clicked", self.on_accent, hexc)
            sw.add(b)
        prov.load_from_data(css.encode())
        pick = Gtk.ColorButton(title="Any accent colour")
        pick.connect("color-set", lambda c: self.on_accent(None, "#%02x%02x%02x" % tuple(
            int(x * 255) for x in (c.get_rgba().red, c.get_rgba().green, c.get_rgba().blue))))
        wall_acc = switch(kread("kdeglobals", "General", "accentColorFromWallpaper", "false") == "true",
                          self.on_accent_wallpaper)
        icons = combo([("NovaOS-Dark", "NovaOS (Papirus, dark)"), ("NovaOS", "NovaOS (Papirus, light)"),
                       ("Papirus-Dark", "Papirus dark"), ("Papirus", "Papirus"),
                       ("breeze-dark", "Breeze dark"), ("breeze", "Breeze light")],
                      kread("kdeglobals", "Icons", "Theme", "NovaOS-Dark"), self.on_icons)
        ptheme = combo([("default", "Breeze (follows colours)"), ("breeze-dark", "Breeze dark"),
                        ("breeze-light", "Breeze light"), ("oxygen", "Oxygen")],
                       kread("plasmarc", "Theme", "name", "default"), self.on_plasma_theme)
        self.section(box, "Colours", row("Mode", mode), label("Accent colour"), sw,
                     row("Custom accent colour", pick),
                     row("Accent from wallpaper", wall_acc, "Picks the accent colour from your wallpaper."),
                     row("Icons", icons), row("Taskbar and menus style", ptheme))
        more = Gtk.Box(spacing=8)
        for text, cmd in (("All appearance settings", ["systemsettings", "kcm_lookandfeel"]),
                          ("Download themes", ["systemsettings", "kcm_lookandfeel"]),
                          ("Kvantum app styles", ["kvantummanager"])):
            more.pack_start(button(text, lambda c=cmd: launch(*c)), False, False, 0)
        self.section(box, "More", more)

    def page_wallpaper(self):
        box = self.page("wallpaper", "Wallpaper", "Click a picture to use it.")
        wf = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=6,
                         column_spacing=6, row_spacing=6, homogeneous=True)
        for name, thumb, folder in wallpapers():
            b = Gtk.Button()
            b.get_style_context().add_class("thumb")
            b.set_tooltip_text(name)
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(thumb, 136, 77, False)
                b.add(Gtk.Image.new_from_pixbuf(pb))
            except GLib.Error:
                b.set_label(name)
            b.connect("clicked", self.on_wallpaper, thumb)
            wf.add(b)
        hb = Gtk.Box(spacing=8)
        hb.pack_start(button("Use my own picture…", self.on_own_wallpaper), False, False, 0)
        hb.pack_start(button("Picture of the day…", lambda: launch("systemsettings", "kcm_wallpaper")),
                      False, False, 0)
        self.section(box, "Pictures", wf, hb)
        slide = combo([("off", "Off"), ("60", "Every minute"), ("600", "Every 10 minutes"),
                       ("3600", "Every hour"), ("86400", "Every day")], "off", self.on_slideshow)
        self.section(box, "Slideshow", row("Change wallpaper automatically", slide,
                                           "Cycles through all NovaOS wallpapers and your Pictures folder."))

    def page_taskbar(self):
        box = self.page("taskbar", "Taskbar", "Where the taskbar sits, how it looks and its clock.")
        pos = combo([("bottom", "Bottom"), ("top", "Top"), ("left", "Left"), ("right", "Right")],
                    "bottom", self.on_position)
        size = combo([("1.6", "Tiny"), ("2", "Small"), ("2.6", "Normal"), ("3.4", "Large"),
                      ("4.4", "Huge")], "2.6", self.on_size)
        hide = combo([("none", "Always visible"), ("autohide", "Auto-hide"),
                      ("dodgewindows", "Hide when a window covers it"),
                      ("windowsgobelow", "Windows can cover it")], "none", self.on_hiding)
        align = combo([("center", "Centre"), ("left", "Start"), ("right", "End")], "center", self.on_align)
        floating = switch(False, self.on_floating)
        opacity = combo([("0", "Adaptive"), ("1", "Solid"), ("2", "See-through")], "0", self.on_panel_opacity)
        edit = button("Edit taskbar…", lambda: run("qdbus", "org.kde.plasmashell", "/PlasmaShell",
                                                    "org.kde.PlasmaShell.toggleWidgetExplorer"))
        self.section(box, "Taskbar", row("Position", pos), row("Size", size), row("Visibility", hide),
                     row("Floating", floating, "A rounded taskbar that floats above the screen edge."),
                     row("Background", opacity),
                     row("Alignment", align, "For a short taskbar or dock."),
                     row("Add widgets, move or resize", edit,
                         "Drag things around; click Exit Edit Mode when done."))
        c24 = combo([("1", "Region default"), ("2", "24-hour"), ("0", "12-hour (AM/PM)")], "1",
                    lambda c: self.clock("use24hFormat", int(c.get_active_id())))
        secs = switch(False, lambda on: self.clock("showSeconds", "true" if on else "false"))
        date = switch(True, lambda on: self.clock("showDate", "true" if on else "false"))
        dfmt = combo([("shortDate", "Short (24/10/2026)"), ("longDate", "Long (Saturday 24 October)"),
                      ("isoDate", "ISO (2026-10-24)")], "shortDate",
                     lambda c: self.clock("dateFormat", c.get_active_id()))
        self.section(box, "Clock", row("Time format", c24), row("Show seconds", secs),
                     row("Show the date", date), row("Date style", dfmt))

    def page_windows(self):
        box = self.page("windows", "Windows & effects", "Window buttons, borders, animations and effects.")
        btns = combo([("right", "Right (Windows)"), ("left", "Left (macOS)")],
                     "left" if kread("kwinrc", "org.kde.kdecoration2", "ButtonsOnLeft", "M").startswith("X")
                     else "right", self.on_buttons)
        bsize = combo([("Small", "Small"), ("Default", "Normal"), ("Large", "Large"), ("VeryLarge", "Very large")],
                      kread("breezerc", "Common", "ButtonSize", "Default"),
                      lambda c: self.deco("breezerc", "Common", "ButtonSize", c.get_active_id()))
        talign = combo([("AlignCenterFullWidth", "Centre"), ("AlignLeft", "Left"), ("AlignRight", "Right")],
                       kread("breezerc", "Common", "TitleAlignment", "AlignCenterFullWidth"),
                       lambda c: self.deco("breezerc", "Common", "TitleAlignment", c.get_active_id()))
        border = combo([("None", "None"), ("NoSides", "Bottom only"), ("Tiny", "Thin"), ("Normal", "Normal"),
                        ("Large", "Thick")],
                       kread("kwinrc", "org.kde.kdecoration2", "BorderSize", "Normal"), self.on_border)
        self.section(box, "Windows", row("Window buttons", btns), row("Button size", bsize),
                     row("Title position", talign), row("Window borders", border))

        anim = combo([("0", "Off (instant)"), ("0.5", "Fast"), ("0.7", "Normal"), ("1.2", "Relaxed")],
                     kread("kdeglobals", "KDE", "AnimationDurationFactor", "0.7"), self.on_anim)
        openfx = combo([("scale", "Zoom"), ("glide", "Glide"), ("fade", "Fade"), ("off", "None")],
                       kread("novaosrc", "Effects", "Open", "scale"), self.on_open_effect)
        minfx = combo([("magiclamp", "Magic lamp"), ("squash", "Squash"), ("off", "None")],
                      kread("novaosrc", "Effects", "Minimize", "magiclamp"), self.on_min_effect)
        wobbly = switch(kread("kwinrc", "Plugins", "wobblywindowsEnabled", "false") == "true",
                        lambda on: self.effect_toggle("wobblywindows", on))
        dim = switch(kread("kwinrc", "Plugins", "diminactiveEnabled", "false") == "true",
                     lambda on: self.effect_toggle("diminactive", on))
        shake = switch(kread("kwinrc", "Plugins", "mousemarkEnabled", "false") == "true",
                       lambda on: self.effect_toggle("mousemark", on))
        self.section(box, "Animations", row("Speed", anim), row("Opening and closing", openfx),
                     row("Minimising", minfx), row("Wobbly windows", wobbly, "Windows wobble while you drag them."),
                     row("Dim windows in the background", dim),
                     row("Draw on screen", shake, "Hold Shift+⌘ and move the mouse to draw; Shift+⌘+F11 clears."))

        trans = combo([("off", "Off"), ("light", "Light"), ("medium", "Medium"), ("strong", "Strong")],
                      kread("kwinrc", "NovaOS", "Transparency", "off"), self.on_transparency)
        blur = combo([("off", "Off"), ("3", "Soft"), ("7", "Medium"), ("12", "Strong")],
                     kread("novaosrc", "Effects", "Blur", "7"), self.on_blur)
        hot = combo([("off", "Off"), ("7", "Top-left"), ("1", "Top-right"), ("5", "Bottom-left"),
                     ("3", "Bottom-right")], kread("novaosrc", "Effects", "HotCorner", "off"), self.on_hot_corner)
        night = combo([("off", "Off"), ("5500", "Slightly warm"), ("4500", "Warm"), ("3500", "Very warm")],
                      kread("novaosrc", "Effects", "Night", "off"), self.on_night)
        self.section(box, "Effects",
                     row("Transparent windows", trans,
                         "See-through windows and menus. Needs graphics acceleration "
                         "(UTM: GPU Supported display)."),
                     row("Blur behind see-through things", blur),
                     row("Hot corner", hot, "Move the mouse into this corner to see all windows."),
                     row("Night light", night, "Warmer colours, easier on the eyes in the evening."))

    def page_text(self):
        box = self.page("text", "Text & pointer", "Fonts, text size, mouse pointer and clicking.")
        fam, size = current_font()
        fonts = combo([(f, f) for f in font_families()], fam, self.on_font)
        self.font_combo = fonts
        fsize = combo([(s, s + " pt") for s in ("8", "9", "10", "11", "12", "13", "14", "16")], size,
                      self.on_font)
        self.size_combo = fsize
        aa = combo([("Slight", "Smooth (recommended)"), ("None", "Sharp"), ("Full", "Strong hinting")],
                   kread("kdeglobals", "General", "XftHintStyle", "hintslight").replace("hint", "").title(),
                   self.on_hinting)
        self.section(box, "Text", row("Font", fonts), row("Size", fsize), row("Text smoothing", aa),
                     row("Make everything bigger (scale)", button("Display settings…",
                                                                  lambda: launch("systemsettings", "kcm_kscreen"))))
        cur = combo([("breeze_cursors", "Breeze (dark)"), ("Breeze_Snow", "Breeze Snow (white)"),
                     ("DMZ-White", "DMZ white"), ("DMZ-Black", "DMZ black"), ("Adwaita", "Adwaita")],
                    kread("kcminputrc", "Mouse", "cursorTheme", "breeze_cursors"), self.on_cursor)
        self.cursor_combo = cur
        csize = combo([("24", "Normal"), ("32", "Large"), ("48", "Extra large"), ("64", "Huge")],
                      kread("kcminputrc", "Mouse", "cursorSize", "24"), self.on_cursor)
        self.csize_combo = csize
        click = combo([("false", "Double-click to open (Windows)"), ("true", "Single-click to open")],
                      kread("kdeglobals", "KDE", "SingleClick", "false"), self.on_click)
        speed = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, -1, 1, 0.1)
        speed.set_size_request(220, -1)
        speed.set_draw_value(False)
        try:
            speed.set_value(float(kread("kcminputrc", "Mouse", "XLbInptPointerAcceleration", "0")))
        except ValueError:
            pass
        speed.connect("value-changed", self.on_mouse_speed)
        self.section(box, "Pointer", row("Pointer style", cur), row("Pointer size", csize, "Fully applies after "
                                                                                            "signing out."),
                     row("Opening files and folders", click),
                     row("Mouse speed", speed, "Left slower, right faster."))

    def page_startup(self):
        box = self.page("startup", "Start-up & updates",
                        "How NovaOS starts, and getting new NovaOS versions without reinstalling.")
        info = build_info()
        ver = "NovaOS %s" % info.get("VERSION", "?")
        if info.get("COMMIT", "unknown") != "unknown":
            ver += "  ·  %s" % info["COMMIT"][:7]
        if info.get("DATE"):
            ver += "  ·  %s" % info["DATE"]
        upd = button("Update NovaOS now", lambda: launch("nova-update"))
        upd.get_style_context().add_class("suggested-action")
        check = switch(kread("novaosrc", "Update", "Check", "true") != "false",
                       lambda on: kwrite("novaosrc", "Update", "Check", "true" if on else "false"))
        if LIVE:
            upd.set_sensitive(False)
        self.section(box, "Updates", row("This computer", label(ver, "sub", False)),
                     row("Get the newest NovaOS", upd,
                         "Installs the newest NovaOS on top of this one. Your files, apps, settings and "
                         "website logins stay — no reinstall, no new account." if not LIVE else
                         "Install NovaOS first; updates work on the installed system."),
                     row("Tell me when there is a new version", check))

        user = os.environ.get("USER") or os.path.basename(HOME)
        auto = Gtk.Switch(active=bool(autologin_user()))
        auto.connect("notify::active", self.on_autologin)
        if LIVE:
            auto.set_active(True)
            auto.set_sensitive(False)
        lock = combo([("off", "Never"), ("5", "After 5 minutes"), ("15", "After 15 minutes"),
                      ("30", "After 30 minutes")],
                     kread("kscreenlockerrc", "Daemon", "Timeout", "off")
                     if kread("kscreenlockerrc", "Daemon", "Autolock", "false") == "true" else "off",
                     self.on_lock)
        splash = switch(kread("ksplashrc", "KSplash", "Engine", "KSplashQML") != "none", self.on_splash)
        self.section(box, "Start-up",
                     row("Log in automatically", auto,
                         "Start straight to the desktop as %s, without typing a password." % user),
                     row("Lock the screen", lock), row("Show the NovaOS splash while starting", splash),
                     row("Apps that start with NovaOS", button("Choose…",
                                                               lambda: launch("systemsettings", "kcm_autostart"))))

    def page_backup(self):
        box = self.page("backup", "Backup",
                        "Save your whole NovaOS setup to one file, and restore it on another NovaOS "
                        "(for example after reinstalling). Put the file in a shared folder or on a USB "
                        "stick to move it.")
        self.inc_firefox = Gtk.CheckButton(label="Include Firefox (bookmarks, passwords and website logins)")
        self.inc_firefox.set_active(True)
        hb = Gtk.Box(spacing=8)
        hb.pack_start(button("Save my setup…", self.on_backup), False, False, 0)
        hb.pack_start(button("Restore a setup…", self.on_restore), False, False, 0)
        self.section(box, "Your setup", label("Saves: layout, taskbar, colours, wallpaper, fonts, window "
                                              "settings, shortcuts, keyboard, app settings."),
                     self.inc_firefox, hb)
        self.section(box, "Start fresh", row("Reset the look to NovaOS defaults",
                                             button("Reset", lambda: self.on_style(None, "org.novaos.desktop",
                                                                                   "NovaOS"))))

    # -- actions --------------------------------------------------------------
    def work(self, msg, fn):
        self.status.set_text(msg)

        def t():
            res = fn()
            GLib.idle_add(self.status.set_text, res if isinstance(res, str) else "Done.")
        threading.Thread(target=t, daemon=True).start()

    def on_style(self, _b, pid, name):
        self.work("Applying %s…" % name,
                  lambda: run("plasma-apply-lookandfeel", "--apply", pid, "--resetLayout"))

    def on_mode(self, combo):
        scheme = combo.get_active_id()

        def f():
            run("plasma-apply-colorscheme", scheme)
            icons = "NovaOS" if "Light" in scheme or "Classic" in scheme else "NovaOS-Dark"
            if CHANGEICONS:
                run(CHANGEICONS, icons)
            else:
                kwrite("kdeglobals", "Icons", "Theme", icons)
        self.work("Switching colours…", f)

    def on_accent(self, _b, hexc):
        def f():
            kwrite("kdeglobals", "General", "accentColorFromWallpaper", "false")
            run("plasma-apply-colorscheme", "--accent-color", hexc)
        self.work("Changing accent colour…", f)

    def on_accent_wallpaper(self, on):
        def f():
            kwrite("kdeglobals", "General", "accentColorFromWallpaper", "true" if on else "false")
            restart_plasmashell()
        self.work("Changing accent colour…", f)

    def on_plasma_theme(self, combo):
        v = combo.get_active_id()
        self.work("Changing style…", lambda: run("plasma-apply-desktoptheme", v))

    def on_wallpaper(self, _b, path):
        self.work("Changing wallpaper…", lambda: run("plasma-apply-wallpaperimage", path))

    def on_own_wallpaper(self):
        dlg = Gtk.FileChooserNative(title="Choose a picture", transient_for=self,
                                    action=Gtk.FileChooserAction.OPEN)
        flt = Gtk.FileFilter()
        flt.set_name("Pictures")
        for m in ("image/jpeg", "image/png", "image/webp"):
            flt.add_mime_type(m)
        dlg.add_filter(flt)
        if dlg.run() == Gtk.ResponseType.ACCEPT:
            self.on_wallpaper(None, dlg.get_filename())
        dlg.destroy()

    def on_slideshow(self, combo):
        v = combo.get_active_id()
        pics = os.path.join(HOME, "Pictures")
        if v == "off":
            js = ("var ds = desktops(); for (var i = 0; i < ds.length; i++) {"
                  " ds[i].wallpaperPlugin = 'org.kde.image'; }")
        else:
            js = ("var ds = desktops(); for (var i = 0; i < ds.length; i++) { var d = ds[i];"
                  " d.wallpaperPlugin = 'org.kde.slideshow';"
                  " d.currentConfigGroup = ['Wallpaper', 'org.kde.slideshow', 'General'];"
                  " d.writeConfig('SlidePaths', ['%s/', '%s/']);"
                  " d.writeConfig('SlideInterval', %s); d.writeConfig('FillMode', 2); }"
                  % (WALLPAPERS, pics, v))
        self.work("Changing wallpaper…", lambda: shell_script(js))

    def main_panel_js(self, body):
        return ("var ps = panels(); var main = null;"
                "for (var i = 0; i < ps.length; i++) { var w = ps[i].widgetIds;"
                " for (var k = 0; k < w.length; k++) { var t = ps[i].widgetById(w[k]).type;"
                "  if (t == 'org.kde.plasma.icontasks' || t == 'org.kde.plasma.taskmanager') main = ps[i]; } }"
                "if (!main && ps.length) main = ps[0]; if (main) { %s }" % body)

    def on_position(self, combo):
        loc = combo.get_active_id()
        self.work("Moving the taskbar…", lambda: shell_script(self.main_panel_js("main.location = '%s';" % loc)))

    def on_size(self, combo):
        f = combo.get_active_id()
        self.work("Resizing the taskbar…",
                  lambda: shell_script(self.main_panel_js("main.height = Math.round(gridUnit * %s);" % f)))

    def on_hiding(self, combo):
        v = combo.get_active_id()
        self.work("Changing the taskbar…", lambda: shell_script(self.main_panel_js("main.hiding = '%s';" % v)))

    def on_align(self, combo):
        v = combo.get_active_id()
        self.work("Changing the taskbar…", lambda: shell_script(self.main_panel_js("main.alignment = '%s';" % v)))

    def panel_views(self, key, value):
        ids = shell_script("var ps = panels(); var s = ''; for (var i = 0; i < ps.length; i++)"
                           " s += ps[i].id + ' '; print(s);").split()
        for pid in ids:
            if pid.isdigit():
                kwrite("plasmashellrc", ["PlasmaViews", "Panel %s" % pid], key, value)
        restart_plasmashell()

    def on_floating(self, on):
        self.work("Changing the taskbar…", lambda: self.panel_views("floating", 1 if on else 0))

    def on_panel_opacity(self, combo):
        v = combo.get_active_id()
        self.work("Changing the taskbar…", lambda: self.panel_views("panelOpacity", v))

    def clock(self, key, value):
        js = ("var ps = panels(); for (var i = 0; i < ps.length; i++) { var w = ps[i].widgets();"
              " for (var k = 0; k < w.length; k++) { if (w[k].type == 'org.kde.plasma.digitalclock') {"
              " w[k].currentConfigGroup = ['Appearance']; w[k].writeConfig('%s', %s); } } }"
              % (key, value if isinstance(value, int) or value in ("true", "false") else "'%s'" % value))
        self.work("Changing the clock…", lambda: shell_script(js))

    def on_buttons(self, combo):
        left = combo.get_active_id() == "left"

        def f():
            kwrite("kwinrc", "org.kde.kdecoration2", "ButtonsOnLeft", "XIA" if left else "M")
            kwrite("kwinrc", "org.kde.kdecoration2", "ButtonsOnRight", "" if left else "IAX")
            kwin_reconfigure()
        self.work("Moving window buttons…", f)

    def deco(self, file, group, key, value):
        def f():
            kwrite(file, group, key, value)
            kwin_reconfigure()
        self.work("Changing windows…", f)

    def on_border(self, combo):
        v = combo.get_active_id()

        def f():
            kwrite("kwinrc", "org.kde.kdecoration2", "BorderSize", v)
            kwrite("kwinrc", "org.kde.kdecoration2", "BorderSizeAuto", "false")
            kwin_reconfigure()
        self.work("Changing window borders…", f)

    def on_anim(self, combo):
        v = combo.get_active_id()

        def f():
            kwrite("kdeglobals", "KDE", "AnimationDurationFactor", v)
            notify_change(3)
            kwin_reconfigure()
        self.work("Changing animation speed…", f)

    def effect_toggle(self, name, on, reconfigure=True):
        kwrite("kwinrc", "Plugins", name + "Enabled", "true" if on else "false")
        if reconfigure:
            def f():
                kwin_reconfigure()
                kwin_effect([name], on)
            self.work("Changing effects…", f)

    def on_open_effect(self, combo):
        v = combo.get_active_id()

        def f():
            kwrite("novaosrc", "Effects", "Open", v)
            for name, key in (("scale", "kwin4_effect_scale"), ("glide", "glide"), ("fade", "kwin4_effect_fade")):
                kwrite("kwinrc", "Plugins", key + "Enabled", "true" if v == name else "false")
                kwin_effect([key], v == name)
            kwin_reconfigure()
        self.work("Changing animations…", f)

    def on_min_effect(self, combo):
        v = combo.get_active_id()

        def f():
            kwrite("novaosrc", "Effects", "Minimize", v)
            for name, key in (("magiclamp", "magiclamp"), ("squash", "kwin4_effect_squash")):
                kwrite("kwinrc", "Plugins", key + "Enabled", "true" if v == name else "false")
                kwin_effect([key], v == name)
            kwin_reconfigure()
        self.work("Changing animations…", f)

    TRANSPARENCY = {  # level: (inactive windows, menus, dialogs, moving/resizing)
        "off": None,
        "light": (88, 92, 96, 85),
        "medium": (78, 86, 92, 75),
        "strong": (65, 78, 85, 60),
    }

    def on_transparency(self, combo):
        level = combo.get_active_id()
        vals = self.TRANSPARENCY.get(level)

        def f():
            kwrite("kwinrc", "NovaOS", "Transparency", level)
            if vals:
                g = "Effect-translucency"
                for key, v in zip(("Inactive", "Menus", "Dialogs", "MoveResize"), vals):
                    kwrite("kwinrc", g, key, v)
                for key in ("DropdownMenus", "PopupMenus", "ComboboxPopups"):
                    kwrite("kwinrc", g, key, vals[1])
                kwrite("kwinrc", "Plugins", "translucencyEnabled", "true")
                kwrite("kwinrc", "Plugins", "blurEnabled", "true")
                kwrite("kwinrc", "Compositing", "Enabled", "true")
                run("qdbus", "org.kde.KWin", "/Compositor", "org.kde.kwin.Compositing.resume")
                kwin_reconfigure()
                kwin_effect(["translucency", "kwin4_effect_translucency", "blur"], True)
            else:
                kwrite("kwinrc", "Plugins", "translucencyEnabled", "false")
                kwin_effect(["translucency", "kwin4_effect_translucency"], False)
                kwin_reconfigure()
        self.work("Changing transparency…", f)

    def on_blur(self, combo):
        v = combo.get_active_id()

        def f():
            kwrite("novaosrc", "Effects", "Blur", v)
            if v == "off":
                kwrite("kwinrc", "Plugins", "blurEnabled", "false")
                kwin_effect(["blur"], False)
            else:
                kwrite("kwinrc", "Plugins", "blurEnabled", "true")
                kwrite("kwinrc", "Effect-blur", "BlurStrength", v)
                kwrite("kwinrc", "Effect-blur", "NoiseStrength", "2")
                kwin_effect(["blur"], True)
            kwin_reconfigure()
        self.work("Changing blur…", f)

    def on_hot_corner(self, combo):
        v = combo.get_active_id()

        def f():
            kwrite("novaosrc", "Effects", "HotCorner", v)
            kwrite("kwinrc", "Effect-overview", "BorderActivate", "9" if v == "off" else v)
            kwrite("kwinrc", "Effect-windowview", "BorderActivateAll", "9")
            kwin_reconfigure()
        self.work("Changing hot corner…", f)

    def on_night(self, combo):
        v = combo.get_active_id()

        def f():
            kwrite("novaosrc", "Effects", "Night", v)
            if v == "off":
                kwrite("kwinrc", "NightColor", "Active", "false")
            else:
                kwrite("kwinrc", "NightColor", "Active", "true")
                kwrite("kwinrc", "NightColor", "Mode", "Constant")
                kwrite("kwinrc", "NightColor", "NightTemperature", v)
            kwin_reconfigure()
        self.work("Changing night light…", f)

    def on_icons(self, combo):
        v = combo.get_active_id()

        def f():
            if CHANGEICONS:
                run(CHANGEICONS, v)
            else:
                kwrite("kdeglobals", "Icons", "Theme", v)
        self.work("Changing icons…", f)

    def on_font(self, _combo):
        fam = self.font_combo.get_active_id()
        size = int(self.size_combo.get_active_id())

        def f():
            spec = "%s,%d,-1,5,50,0,0,0,0,0"
            for key, sz in (("font", size), ("menuFont", size), ("toolBarFont", size),
                            ("smallestReadableFont", max(size - 2, 7))):
                kwrite("kdeglobals", "General", key, spec % (fam, sz))
            kwrite("kdeglobals", "WM", "activeFont", "%s,%d,-1,5,63,0,0,0,0,0" % (fam, size))
            notify_change(1)
            kwin_reconfigure()
            return "Done. Some apps update after they restart."
        self.work("Changing font…", f)

    def on_hinting(self, combo):
        v = combo.get_active_id()

        def f():
            kwrite("kdeglobals", "General", "XftAntialias", "true")
            kwrite("kdeglobals", "General", "XftHintStyle", "hint" + v.lower())
            notify_change(1)
            return "Done. Apps update after they restart."
        self.work("Changing text smoothing…", f)

    def on_cursor(self, _combo):
        theme = self.cursor_combo.get_active_id()
        size = self.csize_combo.get_active_id()

        def f():
            kwrite("kcminputrc", "Mouse", "cursorSize", size)
            kwrite("kcminputrc", "Mouse", "cursorTheme", theme)
            run("plasma-apply-cursortheme", theme)
            notify_change(5)
            return "Done. The size fully applies after signing out."
        self.work("Changing the pointer…", f)

    def on_click(self, combo):
        v = combo.get_active_id()

        def f():
            kwrite("kdeglobals", "KDE", "SingleClick", v)
            notify_change(3)
        self.work("Changing clicking…", f)

    def on_mouse_speed(self, scale):
        v = round(scale.get_value(), 1)
        GLib.timeout_add(400, self._apply_speed, v, scale)

    def _apply_speed(self, v, scale):
        if round(scale.get_value(), 1) != v:
            return False
        kwrite("kcminputrc", "Mouse", "XLbInptPointerAcceleration", v)
        kwrite("kcminputrc", "Mouse", "XLbInptAccelProfileFlat", "true")
        out = run("xinput", "list", "--id-only")
        for dev in (out.stdout.split() if out else []):
            run("xinput", "set-prop", dev, "libinput Accel Speed", str(v))
        self.status.set_text("Mouse speed changed.")
        return False

    def on_autologin(self, sw, _p):
        on = sw.get_active()
        if on == bool(autologin_user()):
            return
        user = os.environ.get("USER") or os.path.basename(HOME)

        def f():
            r = run("pkexec", "/usr/lib/novaos/autologin.sh", "on" if on else "off", user)
            ok = r is not None and r.returncode == 0
            if not ok:
                GLib.idle_add(sw.set_active, not on)
                return "Could not change it (no permission)."
            return "NovaOS will log you in automatically." if on else "NovaOS will ask for your password."
        self.work("Changing start-up…", f)

    def on_lock(self, combo):
        v = combo.get_active_id()

        def f():
            if v == "off":
                kwrite("kscreenlockerrc", "Daemon", "Autolock", "false")
                kwrite("kscreenlockerrc", "Daemon", "LockOnResume", "false")
            else:
                kwrite("kscreenlockerrc", "Daemon", "Autolock", "true")
                kwrite("kscreenlockerrc", "Daemon", "Timeout", v)
                kwrite("kscreenlockerrc", "Daemon", "LockOnResume", "true")
            run("qdbus", "org.freedesktop.ScreenSaver", "/ScreenSaver", "configure")
        self.work("Changing screen lock…", f)

    def on_splash(self, on):
        def f():
            kwrite("ksplashrc", "KSplash", "Engine", "KSplashQML" if on else "none")
            kwrite("ksplashrc", "KSplash", "Theme", "org.novaos.desktop" if on else "None")
        self.work("Changing start-up…", f)

    # -- backup ----------------------------------------------------------------
    def on_backup(self):
        dlg = Gtk.FileChooserNative(title="Save my NovaOS setup", transient_for=self,
                                    action=Gtk.FileChooserAction.SAVE)
        dlg.set_do_overwrite_confirmation(True)
        dlg.set_current_name("NovaOS-setup-%s.tar.gz" % time.strftime("%Y-%m-%d"))
        if dlg.run() != Gtk.ResponseType.ACCEPT:
            dlg.destroy()
            return
        dest = dlg.get_filename()
        dlg.destroy()
        firefox = self.inc_firefox.get_active()

        def f():
            items = [os.path.relpath(os.path.join(CFG, c), HOME) for c in BACKUP_CONFIG] + BACKUP_DATA
            if firefox:
                items += BACKUP_FIREFOX
            try:
                with tarfile.open(dest, "w:gz") as tar:
                    for it in items:
                        p = os.path.normpath(os.path.join(HOME, it))
                        if os.path.exists(p) and p.startswith(HOME):
                            tar.add(p, arcname=os.path.relpath(p, HOME),
                                    filter=lambda ti: None if ti.name.endswith((".lock", "lock",
                                                                                "/cache2")) else ti)
            except (OSError, tarfile.TarError) as e:
                return "Could not save: %s" % e
            return "Saved to %s" % dest
        self.work("Saving your setup…", f)

    def on_restore(self):
        dlg = Gtk.FileChooserNative(title="Restore a NovaOS setup", transient_for=self,
                                    action=Gtk.FileChooserAction.OPEN)
        flt = Gtk.FileFilter()
        flt.set_name("NovaOS setup")
        flt.add_pattern("*.tar.gz")
        dlg.add_filter(flt)
        if dlg.run() != Gtk.ResponseType.ACCEPT:
            dlg.destroy()
            return
        src = dlg.get_filename()
        dlg.destroy()
        ask = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                                buttons=Gtk.ButtonsType.OK_CANCEL,
                                text="Restore this setup?")
        ask.format_secondary_text("Your current look and settings are replaced. Close Firefox first. "
                                  "NovaOS signs you out at the end so everything loads.")
        resp = ask.run()
        ask.destroy()
        if resp != Gtk.ResponseType.OK:
            return

        def f():
            try:
                with tarfile.open(src, "r:gz") as tar:
                    safe = [m for m in tar.getmembers()
                            if not m.name.startswith(("/", "..")) and ".." not in m.name.split("/")
                            and not m.issym() and not m.islnk() and not m.isdev()]
                    tar.extractall(HOME, members=safe)
            except (OSError, tarfile.TarError) as e:
                return "Could not restore: %s" % e
            GLib.timeout_add(1500, lambda: launch("qdbus", "org.kde.ksmserver", "/KSMServer", "logout",
                                                  "0", "0", "0") or False)
            return "Restored. Signing out…"
        self.work("Restoring your setup…", f)


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="os.nova.Style")

    def do_activate(self):
        win = self.get_active_window()
        if not win:
            prov = Gtk.CssProvider()
            prov.load_from_data(CSS)
            Gtk.StyleContext.add_provider_for_screen(Gtk.Window().get_screen(), prov,
                                                     Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            win = StyleWindow(self)
        win.show_all()
        win.present()


if __name__ == "__main__":
    sys.exit(App().run(sys.argv))
