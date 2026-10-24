#!/usr/bin/env python3
"""NovaOS Style - one window to make NovaOS look the way you want.

Layout (Windows 11 / macOS / Windows 10 style), dark or light, accent colour,
wallpaper, taskbar position, window buttons, animation speed and icons.
Everything is applied with KDE Plasma's own tools, so System Settings shows
the same choices afterwards.
"""
import glob
import os
import subprocess
import sys
import threading

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
           ("Green", "#22c55e"), ("Amber", "#f59e0b"), ("Orange", "#f97316"), ("Red", "#ef4444"),
           ("Pink", "#ec4899"), ("Violet", "#a855f7"), ("Graphite", "#8a93a6")]
PREVIEWS = "/usr/share/novaos/styles"
CHANGEICONS = (glob.glob("/usr/lib/*/libexec/plasma-changeicons") + glob.glob("/usr/libexec/plasma-changeicons")
               + [""])[0]
WALLPAPERS = "/usr/share/wallpapers"

CSS = b"""
.title { font-size: 20pt; font-weight: 800; }
.sub { opacity: 0.65; }
.section { font-weight: 700; font-size: 11pt; margin-top: 10px; }
.card { background-color: alpha(@theme_fg_color, 0.05); border-radius: 12px; padding: 12px 14px; }
.style-btn { padding: 6px; border-radius: 12px; }
.swatch { min-width: 30px; min-height: 30px; border-radius: 999px; padding: 0; }
.thumb { padding: 3px; border-radius: 8px; }
"""


def run(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None


def kwrite(file, group, key, value):
    run("kwriteconfig5", "--file", file, "--group", group, "--key", key, str(value))


def kread(file, group, key, default=""):
    r = run("kreadconfig5", "--file", file, "--group", group, "--key", key, "--default", default)
    return r.stdout.strip() if r and r.returncode == 0 else default


def shell_script(js):
    run("qdbus", "org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.evaluateScript", js)


def kwin_reconfigure():
    run("qdbus", "org.kde.KWin", "/KWin", "reconfigure")


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
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.get_style_context().add_class("card")
    for c in children:
        box.pack_start(c, False, False, 0)
    return box


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
            # small file for the thumbnail, the folder itself for applying
            out.append((n, os.path.join(d, imgs[0]), os.path.join(WALLPAPERS, n)))
    return out


class StyleWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="NovaOS Style")
        self.set_default_size(1060, 780)
        dark = kread("kdeglobals", "General", "ColorScheme", "NovaOSDark") != "NovaOSLight"
        settings = Gtk.Settings.get_default()
        settings.set_property("gtk-application-prefer-dark-theme", dark)
        if dark and os.path.isdir("/usr/share/themes/Breeze-Dark/gtk-3.0"):
            settings.set_property("gtk-theme-name", "Breeze-Dark")
        self.set_icon_name("novaos-wallpapers")
        sc = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.add(sc)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(24)
        sc.add(box)
        box.pack_start(label("Make NovaOS yours", "title"), False, False, 0)
        box.pack_start(label("Pick a layout, colours and wallpaper. Changes apply right away. "
                             "For even more, open Settings → Appearance.", "sub"), False, False, 0)
        self.status = label("", "sub")

        # Layout
        box.pack_start(label("Layout", "section"), False, False, 0)
        flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=4,
                           column_spacing=10, row_spacing=10, homogeneous=True)
        current = kread("kdeglobals", "KDE", "LookAndFeelPackage", "org.novaos.desktop")
        for pid, name, desc, img in STYLES:
            b = Gtk.Button()
            b.get_style_context().add_class("style-btn")
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(os.path.join(PREVIEWS, img + ".jpg"),
                                                              210, 118, True)
                v.pack_start(Gtk.Image.new_from_pixbuf(pb), False, False, 0)
            except GLib.Error:
                pass
            t = label(("✓ " if pid == current else "") + name)
            t.set_xalign(0.5)
            v.pack_start(t, False, False, 0)
            d = label(desc, "sub")
            d.set_xalign(0.5)
            d.set_justify(Gtk.Justification.CENTER)
            d.set_max_width_chars(26)
            v.pack_start(d, False, False, 0)
            b.add(v)
            b.connect("clicked", self.on_style, pid, name)
            flow.add(b)
        box.pack_start(card(flow, label("Changing the layout replaces the taskbar and its pinned apps.",
                                        "sub")), False, False, 0)

        # Colours
        box.pack_start(label("Colours", "section"), False, False, 0)
        mode = Gtk.ComboBoxText()
        mode.append("NovaOSDark", "Dark")
        mode.append("NovaOSLight", "Light")
        mode.set_active_id(kread("kdeglobals", "General", "ColorScheme", "NovaOSDark")
                           if kread("kdeglobals", "General", "ColorScheme", "") in ("NovaOSDark", "NovaOSLight")
                           else "NovaOSDark")
        mode.connect("changed", self.on_mode)
        sw = Gtk.Box(spacing=8)
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
            sw.pack_start(b, False, False, 0)
        prov.load_from_data(css.encode())
        box.pack_start(card(row("Mode", mode), label("Accent colour"), sw), False, False, 0)

        # Wallpaper
        box.pack_start(label("Wallpaper", "section"), False, False, 0)
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
        own = Gtk.Button(label="Use my own picture…")
        own.connect("clicked", self.on_own_wallpaper)
        daily = Gtk.Button(label="New picture every day…")
        daily.connect("clicked", lambda _b: subprocess.Popen(
            ["systemsettings", "kcm_wallpaper"], start_new_session=True))
        hb = Gtk.Box(spacing=8)
        hb.pack_start(own, False, False, 0)
        hb.pack_start(daily, False, False, 0)
        box.pack_start(card(wf, hb), False, False, 0)

        # Taskbar & windows
        box.pack_start(label("Taskbar and windows", "section"), False, False, 0)
        pos = Gtk.ComboBoxText()
        for k, t in (("bottom", "Bottom"), ("top", "Top"), ("left", "Left"), ("right", "Right")):
            pos.append(k, t)
        pos.set_active_id("bottom")
        pos.connect("changed", self.on_position)
        size = Gtk.ComboBoxText()
        for k, t in (("1.8", "Small"), ("2.6", "Normal"), ("3.4", "Large")):
            size.append(k, t)
        size.set_active_id("2.6")
        size.connect("changed", self.on_size)
        btns = Gtk.ComboBoxText()
        btns.append("right", "Right (Windows)")
        btns.append("left", "Left (macOS)")
        btns.set_active_id("left" if kread("kwinrc", "org.kde.kdecoration2", "ButtonsOnLeft", "M").startswith("X")
                           else "right")
        btns.connect("changed", self.on_buttons)
        anim = Gtk.ComboBoxText()
        for k, t in (("0", "Off (instant)"), ("0.5", "Fast"), ("0.7", "Normal"), ("1.2", "Relaxed")):
            anim.append(k, t)
        anim.set_active_id(kread("kdeglobals", "KDE", "AnimationDurationFactor", "0.7"))
        anim.connect("changed", self.on_anim)
        icons = Gtk.ComboBoxText()
        for k, t in (("NovaOS-Dark", "NovaOS (Papirus, dark)"), ("NovaOS", "NovaOS (Papirus, light)"),
                     ("breeze-dark", "Breeze dark"), ("breeze", "Breeze light")):
            icons.append(k, t)
        icons.set_active_id(kread("kdeglobals", "Icons", "Theme", "NovaOS-Dark"))
        icons.connect("changed", self.on_icons)
        edit = Gtk.Button(label="Edit taskbar…")
        edit.connect("clicked", lambda _b: run("qdbus", "org.kde.plasmashell", "/PlasmaShell",
                                                "org.kde.PlasmaShell.toggleWidgetExplorer"))
        box.pack_start(card(row("Taskbar position", pos), row("Taskbar size", size),
                            row("Window buttons", btns), row("Animations", anim),
                            row("Icons", icons),
                            row("Transparent windows", self.make_transparency(),
                                "See-through windows and menus with blur. Needs graphics "
                                "acceleration (UTM: GPU Supported display)."),
                            row("Add widgets, move or resize the taskbar", edit,
                                "Drag things around; click Exit Edit Mode when done.")), False, False, 0)

        # More
        box.pack_start(label("More", "section"), False, False, 0)
        more = Gtk.Box(spacing=8)
        for text, cmd in (("All appearance settings", ["systemsettings", "kcm_lookandfeel"]),
                          ("Download themes", ["systemsettings", "kcm_lookandfeel"]),
                          ("Kvantum app styles", ["kvantummanager"]),
                          ("Display and scale", ["systemsettings", "kcm_kscreen"])):
            b = Gtk.Button(label=text)
            b.connect("clicked", lambda _b, c=cmd: subprocess.Popen(c, start_new_session=True))
            more.pack_start(b, False, False, 0)
        box.pack_start(card(more), False, False, 0)
        box.pack_start(self.status, False, False, 0)

    # -- actions --------------------------------------------------------------
    def work(self, msg, fn):
        self.status.set_text(msg)

        def t():
            fn()
            GLib.idle_add(self.status.set_text, "Done.")
        threading.Thread(target=t, daemon=True).start()

    def on_style(self, _b, pid, name):
        self.work("Applying %s…" % name,
                  lambda: run("plasma-apply-lookandfeel", "--apply", pid, "--resetLayout"))

    def on_mode(self, combo):
        scheme = combo.get_active_id()

        def f():
            run("plasma-apply-colorscheme", scheme)
            icons = "NovaOS-Dark" if scheme == "NovaOSDark" else "NovaOS"
            if CHANGEICONS:
                run(CHANGEICONS, icons)
            else:
                kwrite("kdeglobals", "Icons", "Theme", icons)
        self.work("Switching colours…", f)

    def on_accent(self, _b, hexc):
        def f():
            run("plasma-apply-colorscheme", "--accent-color", hexc)
            kwrite("kdeglobals", "General", "AccentColor", hexc)
        self.work("Changing accent colour…", f)

    def on_wallpaper(self, _b, path):
        self.work("Changing wallpaper…", lambda: run("plasma-apply-wallpaperimage", path))

    def on_own_wallpaper(self, _b):
        dlg = Gtk.FileChooserNative(title="Choose a picture", transient_for=self,
                                    action=Gtk.FileChooserAction.OPEN)
        flt = Gtk.FileFilter()
        flt.set_name("Pictures")
        for m in ("image/jpeg", "image/png", "image/webp"):
            flt.add_mime_type(m)
        dlg.add_filter(flt)
        if dlg.run() == Gtk.ResponseType.ACCEPT:
            p = dlg.get_filename()
            self.on_wallpaper(None, p)
        dlg.destroy()

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

    def on_buttons(self, combo):
        left = combo.get_active_id() == "left"

        def f():
            kwrite("kwinrc", "org.kde.kdecoration2", "ButtonsOnLeft", "XIA" if left else "M")
            kwrite("kwinrc", "org.kde.kdecoration2", "ButtonsOnRight", "" if left else "IAX")
            kwin_reconfigure()
        self.work("Moving window buttons…", f)

    def on_anim(self, combo):
        v = combo.get_active_id()

        def f():
            kwrite("kdeglobals", "KDE", "AnimationDurationFactor", v)
            kwin_reconfigure()
        self.work("Changing animation speed…", f)

    TRANSPARENCY = {  # level: (inactive windows, menus, dialogs, moving/resizing)
        "off": None,
        "light": (88, 92, 96, 85),
        "medium": (78, 86, 92, 75),
        "strong": (65, 78, 85, 60),
    }

    def make_transparency(self):
        combo = Gtk.ComboBoxText()
        for k, t in (("off", "Off"), ("light", "Light"), ("medium", "Medium"), ("strong", "Strong")):
            combo.append(k, t)
        combo.set_active_id(kread("kwinrc", "NovaOS", "Transparency", "off"))
        combo.connect("changed", self.on_transparency)
        return combo

    def on_transparency(self, combo):
        level = combo.get_active_id()
        vals = self.TRANSPARENCY.get(level)

        def f():
            kwrite("kwinrc", "NovaOS", "Transparency", level)
            if vals:
                g = "Effect-translucency"
                for key, v in zip(("Inactive", "Menus", "Dialogs", "MoveResize"), vals):
                    kwrite("kwinrc", g, key, v)
                kwrite("kwinrc", g, "DropdownMenus", vals[1])
                kwrite("kwinrc", g, "PopupMenus", vals[1])
                kwrite("kwinrc", g, "ComboboxPopups", vals[1])
                kwrite("kwinrc", "Plugins", "translucencyEnabled", "true")
                kwrite("kwinrc", "Plugins", "blurEnabled", "true")
                kwrite("kwinrc", "Compositing", "Enabled", "true")
                run("qdbus", "org.kde.KWin", "/Compositor", "org.kde.kwin.Compositing.resume")
                kwin_reconfigure()
                for name in ("translucency", "kwin4_effect_translucency"):
                    run("qdbus", "org.kde.KWin", "/Effects", "org.kde.kwin.Effects.loadEffect", name)
            else:
                kwrite("kwinrc", "Plugins", "translucencyEnabled", "false")
                for name in ("translucency", "kwin4_effect_translucency"):
                    run("qdbus", "org.kde.KWin", "/Effects", "org.kde.kwin.Effects.unloadEffect", name)
                kwin_reconfigure()
        self.work("Changing transparency…", f)

    def on_icons(self, combo):
        v = combo.get_active_id()

        def f():
            if CHANGEICONS:
                run(CHANGEICONS, v)
            else:
                kwrite("kdeglobals", "Icons", "Theme", v)
        self.work("Changing icons…", f)


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
