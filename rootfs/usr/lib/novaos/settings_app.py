#!/usr/bin/env python3
"""NovaOS Settings - personalisation, display, keyboard, time, sound, about."""
import argparse
import configparser
import os
import platform
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi  # noqa: E402
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

from novaos import config as C  # noqa: E402
from novaos import palette as P  # noqa: E402

VERSION = "1.0"

CSS = b"""
.nova-sidebar { background-color: alpha(@theme_fg_color, 0.03); }
.nova-sidebar row { padding: 9px 14px; border-radius: 8px; margin: 2px 8px; }
.nova-sidebar row:selected { background-color: alpha(@theme_selected_bg_color, 0.22); color: @theme_fg_color; }
.nova-title { font-size: 20pt; font-weight: 700; }
.nova-subtitle { opacity: 0.65; }
.nova-section { font-weight: 700; font-size: 11pt; margin-top: 14px; }
.nova-card { background-color: alpha(@theme_fg_color, 0.045); border-radius: 12px; padding: 14px 16px; }
.nova-swatch { min-width: 30px; min-height: 30px; border-radius: 999px; padding: 0; margin: 0; border: 3px solid transparent; }
.nova-swatch:checked { border-color: @theme_fg_color; }
.nova-thumb { padding: 4px; border-radius: 10px; border: 2px solid transparent; background: none; }
.nova-thumb:checked { border-color: @theme_selected_bg_color; }
.nova-mode { padding: 8px; border-radius: 12px; border: 2px solid transparent; }
.nova-mode:checked { border-color: @theme_selected_bg_color; }
.nova-preview-dark { background: linear-gradient(160deg, #20253a, #0e1118); border-radius: 8px; }
.nova-preview-light { background: linear-gradient(160deg, #ffffff, #e3e7f2); border-radius: 8px; }
.nova-preview-bar-dark { background: #161a24; border-radius: 0 0 8px 8px; }
.nova-preview-bar-light { background: #f4f6fb; border-radius: 0 0 8px 8px; border-top: 1px solid #d3d8e4; }
.nova-big { font-size: 30pt; font-weight: 800; }
"""

LAYOUTS = [("us", "English (US)"), ("gb", "English (UK)"), ("be", "Belgian"),
           ("fr", "French"), ("de", "German"), ("nl", "Dutch"), ("es", "Spanish"),
           ("it", "Italian"), ("pt", "Portuguese"), ("br", "Portuguese (Brazil)"),
           ("ch", "Swiss"), ("se", "Swedish"), ("no", "Norwegian"), ("dk", "Danish"),
           ("fi", "Finnish"), ("pl", "Polish"), ("ro", "Romanian"), ("tr", "Turkish"),
           ("ru", "Russian"), ("jp", "Japanese"), ("latam", "Spanish (Latin America)")]

PAGES = [
    ("personalization", "Personalization", "novaos-wallpapers"),
    ("taskbar", "Taskbar", "novaos-launcher"),
    ("dock", "Dock", "novaos-start"),
    ("display", "Display", "novaos-display"),
    ("apps", "Apps", "novaos-files"),
    ("keyboard", "Keyboard", "novaos-keyboard"),
    ("time", "Date & time", "novaos-calculator"),
    ("sound", "Sound", "novaos-sound"),
    ("network", "Network", "novaos-network"),
    ("specs", "System specs", "novaos-taskmanager"),
    ("about", "About NovaOS", "novaos-about"),
]


def label(text, css=None, xalign=0.0, wrap=False):
    lb = Gtk.Label(label=text, xalign=xalign)
    lb.set_line_wrap(wrap)
    if css:
        lb.get_style_context().add_class(css)
    return lb


def card(*rows):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    box.get_style_context().add_class("nova-card")
    for r in rows:
        box.pack_start(r, False, False, 0)
    return box


def row(title, widget, subtitle=None):
    box = Gtk.Box(spacing=12)
    tbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    tbox.pack_start(label(title), False, False, 0)
    if subtitle:
        tbox.pack_start(label(subtitle, "nova-subtitle", wrap=True), False, False, 0)
    box.pack_start(tbox, True, True, 0)
    widget.set_valign(Gtk.Align.CENTER)
    box.pack_end(widget, False, False, 0)
    return box


def launch(*cmd):
    try:
        subprocess.Popen(cmd, start_new_session=True)
    except OSError as e:
        print("could not launch", cmd, e, file=sys.stderr)


POPULAR = [("VLC media player", "vlc"), ("GIMP image editor", "gimp"),
           ("LibreOffice", "libreoffice-writer libreoffice-calc libreoffice-impress libreoffice-gtk3"),
           ("Chromium browser", "chromium"), ("Thunderbird mail", "thunderbird"),
           ("SuperTux (game)", "supertux")]

# packages whose apps make up NovaOS itself and must not be removed from here
PROTECTED = {"novaos", "thunar", "xfce4-terminal", "xfce4-panel", "xfce4-appfinder", "xfce4-settings",
             "xfdesktop4", "xfwm4", "xfce4-session", "network-manager-gnome", "lightdm",
             "xfce4-taskmanager", "pavucontrol", "calamares", "python3", "exo-utils"}


def installed_apps():
    seen, out = set(), []
    for d in C.APP_DIRS:
        try:
            names = sorted(os.listdir(d))
        except OSError:
            continue
        for n in names:
            if not n.endswith(".desktop") or n in seen:
                continue
            seen.add(n)
            cp = configparser.ConfigParser(interpolation=None, strict=False)
            try:
                cp.read(os.path.join(d, n), encoding="utf-8")
                e = cp["Desktop Entry"]
            except (configparser.Error, KeyError, UnicodeDecodeError):
                continue
            if e.get("NoDisplay", "false").lower() == "true" or e.get("Type", "Application") != "Application":
                continue
            if e.get("OnlyShowIn") and "XFCE" not in e.get("OnlyShowIn"):
                continue
            if "X-XFCE-SettingsDialog" in e.get("Categories", "") or "X-XFCE-SystemSettings" in e.get("Categories", ""):
                continue
            out.append({"id": n, "name": e.get("Name", n), "icon": e.get("Icon", "application-x-executable"),
                        "path": os.path.join(d, n)})
    out.sort(key=lambda a: a["name"].lower())
    return out


def package_of(path):
    """Debian package that owns a .desktop file (NovaOS renames live in /usr/local)."""
    cands = [path]
    if not path.startswith("/usr/share/"):
        cands.append(os.path.join("/usr/share/applications", os.path.basename(path)))
    for p in cands:
        if not os.path.exists(p):
            continue
        r = C.run("dpkg", "-S", p)
        if r and r.returncode == 0:
            return r.stdout.split(":")[0].strip()
    if path.startswith("/usr/lib/novaos") or "novaos" in os.path.basename(path):
        return "novaos"
    return None


def package_desktops(pkgs):
    out = []
    for pkg in pkgs.split():
        r = C.run("dpkg", "-L", pkg)
        for line in (r.stdout.splitlines() if r and r.returncode == 0 else []):
            if line.endswith(".desktop") and "/applications/" in line:
                out.append(line)
    return out


class SettingsWindow(Gtk.ApplicationWindow):
    def __init__(self, app, page):
        super().__init__(application=app, title="Settings")
        self.set_default_size(1000, 680)
        self.set_icon_name("novaos-settings")
        self.s = C.load()
        self._busy = False

        hb = Gtk.HeaderBar(show_close_button=True, title="Settings")
        self.set_titlebar(hb)

        paned = Gtk.Box()
        self.add(paned)
        self.sidebar = Gtk.ListBox()
        self.sidebar.get_style_context().add_class("nova-sidebar")
        self.sidebar.set_size_request(230, -1)
        side_scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        side_scroll.add(self.sidebar)
        side_scroll.get_style_context().add_class("nova-sidebar")
        paned.pack_start(side_scroll, False, False, 0)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE,
                               transition_duration=160)
        paned.pack_start(self.stack, True, True, 0)

        for pid, title, icon in PAGES:
            r = Gtk.ListBoxRow()
            hb_ = Gtk.Box(spacing=12)
            hb_.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR), False, False, 0)
            hb_.pack_start(label(title), False, False, 0)
            r.add(hb_)
            r.page_id = pid
            self.sidebar.add(r)
            builder = getattr(self, "page_" + pid)
            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            content.set_border_width(28)
            content.pack_start(label(title, "nova-title"), False, False, 4)
            builder(content)
            sc = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
            clamp = Gtk.Box()
            content.set_size_request(640, -1)
            clamp.set_center_widget(content)
            sc.add(clamp)
            self.stack.add_named(sc, pid)

        self.sidebar.connect("row-selected", self.on_page)
        for r in self.sidebar.get_children():
            if r.page_id == page:
                self.sidebar.select_row(r)
                break
        else:
            self.sidebar.select_row(self.sidebar.get_row_at_index(0))

    def _goto(self, pid):
        for r in self.sidebar.get_children():
            if r.page_id == pid:
                self.sidebar.select_row(r)

    def on_page(self, _lb, r):
        if r:
            self.stack.set_visible_child_name(r.page_id)

    # -- helpers ----------------------------------------------------------
    def commit(self, what):
        """Save settings and apply them in a worker thread (keeps UI fluid)."""
        C.save(self.s)
        s = dict(self.s)

        def work():
            if what == "theme":
                C.apply_theme(s, force_reload=True)
            elif what == "panel":
                C.apply_panel(s)
            elif what == "wallpaper":
                C.apply_wallpaper(s)
            elif what == "effects":
                C.apply_effects(s)
                C.apply_panel(s)
                C.apply_extras(s)
            elif what == "extras":
                C.apply_extras(s)
            elif what == "dock":
                C.apply_dock(s)
        threading.Thread(target=work, daemon=True).start()

    # -- pages ------------------------------------------------------------
    def page_personalization(self, box):
        box.pack_start(label("Make NovaOS yours: colours, wallpaper and effects.", "nova-subtitle"),
                       False, False, 0)
        # Mode
        box.pack_start(label("Mode", "nova-section"), False, False, 0)
        modes = Gtk.Box(spacing=14)
        self.mode_buttons = {}
        for mode, title in (("dark", "Dark"), ("light", "Light")):
            b = Gtk.ToggleButton()
            b.get_style_context().add_class("nova-mode")
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            prev = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            prev.set_size_request(200, 112)
            prev.get_style_context().add_class("nova-preview-" + mode)
            prev.pack_end(self._bar(mode), False, False, 0)
            v.pack_start(prev, False, False, 0)
            v.pack_start(label(title, xalign=0.5), False, False, 0)
            b.add(v)
            b.set_active(self.s["mode"] == mode)
            b.connect("toggled", self.on_mode, mode)
            self.mode_buttons[mode] = b
            modes.pack_start(b, False, False, 0)
        box.pack_start(card(modes), False, False, 0)

        # Accent
        box.pack_start(label("Accent colour", "nova-section"), False, False, 0)
        flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=12,
                           column_spacing=8, row_spacing=8)
        self.accent_buttons = []
        prov = Gtk.CssProvider()
        css = ""
        for i, (name, hexc) in enumerate(P.ACCENTS):
            b = Gtk.ToggleButton()
            b.set_name("accent%d" % i)
            b.set_tooltip_text(name)
            b.set_size_request(36, 36)
            b.set_halign(Gtk.Align.CENTER)
            b.set_valign(Gtk.Align.CENTER)
            b.get_style_context().add_class("nova-swatch")
            b.get_style_context().add_provider(prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            css += "#accent%d { background: %s; } " % (i, hexc)
            b.set_active(self.s["accent"].lower() == hexc)
            b.connect("toggled", self.on_accent, hexc)
            self.accent_buttons.append((hexc, b))
            flow.add(b)
        prov.load_from_data(css.encode())
        box.pack_start(card(flow), False, False, 0)

        # Wallpaper
        box.pack_start(label("Wallpaper", "nova-section"), False, False, 0)
        self.wall_flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=3,
                                     column_spacing=10, row_spacing=10, homogeneous=True)
        self.wall_buttons = []
        for path in sorted(os.listdir(C.WALLPAPER_DIR)):
            full = os.path.join(C.WALLPAPER_DIR, path)
            if not path.endswith(".jpg") or path == "nova-login.jpg":
                continue
            self._add_wall(full)
        browse = Gtk.Button(label="Browse for a picture…")
        browse.connect("clicked", self.on_browse)
        wall_card = card(self.wall_flow, row("Use your own picture", browse))
        box.pack_start(wall_card, False, False, 0)

        # Effects
        box.pack_start(label("Effects", "nova-section"), False, False, 0)
        eff = Gtk.ComboBoxText()
        for k, t in (("off", "Off (fastest)"), ("balanced", "Balanced: shadows and fades"),
                     ("full", "Full: blur and rounded corners (needs GPU)")):
            eff.append(k, t)
        eff.set_active_id(self.s.get("effects", "balanced"))
        eff.connect("changed", lambda w: self._set("effects", w.get_active_id(), "effects"))
        tr = Gtk.Switch(active=bool(self.s.get("transparency", True)))
        tr.connect("notify::active", lambda w, _p: self._set("transparency", w.get_active(), "panel"))
        box.pack_start(card(
            row("Window effects", eff, "Off is smoothest in a virtual machine (UTM). Balanced adds "
                "shadows and fades; Full needs a real graphics card."),
            row("Transparent taskbar and Start menu", tr)), False, False, 0)

        # Look & feel
        box.pack_start(label("Look and feel", "nova-section"), False, False, 0)
        font = Gtk.ComboBoxText()
        for v, t in ((9, "Small"), (10, "Normal"), (11, "Large"), (12, "Larger"), (14, "Huge")):
            font.append(str(v), t)
        font.set_active_id(str(self.s.get("font_size", 10)))
        font.connect("changed", lambda w: self._set("font_size", int(w.get_active_id()), "extras"))
        btns = Gtk.ComboBoxText()
        btns.append("right", "Right (like Windows)")
        btns.append("left", "Left (like macOS)")
        btns.set_active_id(self.s.get("buttons", "right"))
        btns.connect("changed", lambda w: self._set("buttons", w.get_active_id(), "extras"))
        icons = Gtk.ComboBoxText()
        for v, t in ((40, "Small"), (56, "Normal"), (72, "Large"), (96, "Huge")):
            icons.append(str(v), t)
        icons.set_active_id(str(self.s.get("desktop_icon_size", 56)))
        icons.connect("changed", lambda w: self._set("desktop_icon_size", int(w.get_active_id()), "extras"))
        box.pack_start(card(row("Text size", font),
                            row("Window buttons (close, minimise, maximise)", btns),
                            row("Desktop icon size", icons)), False, False, 0)

    def _bar(self, mode):
        bar = Gtk.Box()
        bar.set_size_request(-1, 16)
        bar.get_style_context().add_class("nova-preview-bar-" + mode)
        return bar

    def _add_wall(self, full):
        thumb = os.path.join(C.WALLPAPER_DIR, "thumbs", os.path.basename(full))
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(thumb if os.path.exists(thumb) else full,
                                                          192, 120, False)
        except GLib.Error:
            return
        b = Gtk.ToggleButton()
        b.get_style_context().add_class("nova-thumb")
        b.add(Gtk.Image.new_from_pixbuf(pb))
        name = os.path.splitext(os.path.basename(full))[0].replace("nova-", "").replace("-", " ").title()
        b.set_tooltip_text(name)
        b.set_active(self.s["wallpaper"] == full)
        b.connect("toggled", self.on_wallpaper, full)
        self.wall_buttons.append((full, b))
        self.wall_flow.add(b)
        b.show_all()

    def on_mode(self, btn, mode):
        if self._busy:
            return
        self._busy = True
        for m, b in self.mode_buttons.items():
            b.set_active(m == mode)
        self._busy = False
        if self.s["mode"] != mode:
            self.s["mode"] = mode
            if mode == "light" and self.s["wallpaper"].endswith("nova-aurora.jpg"):
                self.s["wallpaper"] = os.path.join(C.WALLPAPER_DIR, "nova-daylight.jpg")
                self._sync_walls()
                self.commit("wallpaper")
            elif mode == "dark" and self.s["wallpaper"].endswith("nova-daylight.jpg"):
                self.s["wallpaper"] = os.path.join(C.WALLPAPER_DIR, "nova-aurora.jpg")
                self._sync_walls()
                self.commit("wallpaper")
            self.commit("theme")

    def on_accent(self, btn, hexc):
        if self._busy:
            return
        self._busy = True
        for h, b in self.accent_buttons:
            b.set_active(h == hexc)
        self._busy = False
        if self.s["accent"].lower() != hexc:
            self.s["accent"] = hexc
            self.commit("theme")

    def _sync_walls(self):
        self._busy = True
        for p, b in self.wall_buttons:
            b.set_active(p == self.s["wallpaper"])
        self._busy = False

    def on_wallpaper(self, btn, path):
        if self._busy:
            return
        self.s["wallpaper"] = path
        self._sync_walls()
        self.commit("wallpaper")

    def on_browse(self, _b):
        dlg = Gtk.FileChooserNative(title="Choose a wallpaper", transient_for=self,
                                    action=Gtk.FileChooserAction.OPEN)
        flt = Gtk.FileFilter()
        flt.set_name("Images")
        for m in ("image/jpeg", "image/png", "image/webp", "image/svg+xml"):
            flt.add_mime_type(m)
        dlg.add_filter(flt)
        dlg.set_current_folder(os.path.expanduser("~/Pictures"))
        if dlg.run() == Gtk.ResponseType.ACCEPT:
            path = dlg.get_filename()
            self.s["wallpaper"] = path
            self._sync_walls()
            self.commit("wallpaper")
        dlg.destroy()

    def _set(self, key, value, what):
        self.s[key] = value
        self.commit(what)

    def page_taskbar(self, box):
        labels = Gtk.Switch(active=bool(self.s.get("taskbar_labels")))
        labels.connect("notify::active", lambda w, _p: self._set("taskbar_labels", w.get_active(), "panel"))
        size = Gtk.ComboBoxText()
        for v, t in ((36, "Small"), (44, "Normal"), (52, "Large")):
            size.append(str(v), t)
        size.set_active_id(str(self.s.get("taskbar_size", 36)))
        size.connect("changed", lambda w: self._set("taskbar_size", int(w.get_active_id()), "panel"))
        tpos = Gtk.ComboBoxText()
        tpos.append("top", "Top of the screen")
        tpos.append("bottom", "Bottom of the screen")
        tpos.set_active_id(self.s.get("taskbar_position", "top"))
        tpos.connect("changed", lambda w: self._set("taskbar_position", w.get_active_id(), "extras"))
        box.pack_start(card(row("Show app names on taskbar buttons", labels),
                            row("Taskbar size", size),
                            row("Taskbar position", tpos,
                                "Tip: if you move the taskbar to the bottom, put the dock on the left or right.")),
                       False, False, 0)
        adv = Gtk.Button(label="Panel preferences…")
        adv.connect("clicked", lambda _b: launch("xfce4-panel", "--preferences"))
        box.pack_start(card(
            row("Panel layout, items and position", adv,
                "Add or remove items such as the Whisker Menu, clock or launchers.")), False, False, 0)

    def page_display(self, box):
        self.outs = C.outputs()
        name, info = C.primary_output()
        info = info or {"modes": [], "rates": {}, "current": None, "rate": None}
        self.res_combo = Gtk.ComboBoxText()
        self.res_combo.append("auto", "Keep current (%s)" % (info["current"] or "unknown"))
        for m in info["modes"]:
            self.res_combo.append(m, m.replace("x", " × "))
        if not self.res_combo.set_active_id(self.s.get("resolution") or "auto"):
            self.res_combo.set_active_id("auto")
        self.rate_combo = Gtk.ComboBoxText()
        self.res_combo.connect("changed", lambda _w: self._fill_rates())
        self._fill_rates()
        self.scale_combo = Gtk.ComboBoxText()
        self.scale_combo.append("0", "Automatic (%d %%)" % C.auto_scale())
        for v in (100, 125, 150, 175, 200):
            self.scale_combo.append(str(v), "%d %%%s" % (v, " (recommended for 4K)" if v == 200 else ""))
        self.scale_combo.set_active_id(str(self.s.get("scale") or 0))
        apply_b = Gtk.Button(label="Apply")
        apply_b.get_style_context().add_class("suggested-action")
        apply_b.connect("clicked", self.on_resolution)
        cur = info["current"] or "unknown"
        if info["rate"] and float(info["rate"]) > 0:
            cur += " at %s Hz" % info["rate"]
        box.pack_start(label("Screen: %s · currently %s" % (name or "none detected", cur),
                             "nova-subtitle", wrap=True), False, False, 0)
        box.pack_start(card(
            row("Resolution", self.res_combo),
            row("Refresh rate", self.rate_combo, "NovaOS picks the highest rate your screen supports."),
            row("Scale (size of everything)", self.scale_combo,
                "Use 150–200 % on high-resolution screens (1440p, 4K, Retina) so text is not tiny."),
            row("", apply_b)), False, False, 0)
        box.pack_start(label("Tip for UTM on a Mac: a smaller resolution such as 1920 × 1080 is much smoother, "
                             "because a virtual machine has no graphics card. Raise the scale instead of the "
                             "resolution if things look small.", "nova-subtitle", wrap=True), False, False, 0)
        adv = Gtk.Button(label="Advanced display settings…")
        adv.connect("clicked", lambda _b: launch("xfce4-display-settings"))
        box.pack_start(card(row("Rotation and multiple monitors", adv)), False, False, 0)

    def _fill_rates(self):
        _n, info = C.primary_output()
        info = info or {"rates": {}, "current": None, "rate": None}
        mode = self.res_combo.get_active_id()
        if mode in (None, "auto"):
            mode = info["current"]
        rates = sorted((r for r in info["rates"].get(mode) or [] if float(r) > 0), key=float, reverse=True)
        self.rate_combo.remove_all()
        self.rate_combo.append("max", "Highest available" + (" (%s Hz)" % rates[0] if rates else ""))
        for r in rates:
            self.rate_combo.append(r, "%s Hz" % r)
        if not self.rate_combo.set_active_id(self.s.get("refresh") or "max"):
            self.rate_combo.set_active_id("max")

    def on_resolution(self, _b):
        mode = self.res_combo.get_active_id()
        rate = self.rate_combo.get_active_id()
        scale = int(self.scale_combo.get_active_id() or 0)
        self.s["resolution"] = None if mode == "auto" else mode
        self.s["refresh"] = None if rate == "max" else rate
        self.s["scale"] = scale or None
        C.save(self.s)
        ok = C.apply_resolution(self.s)
        C.apply_scale(self.s)
        if not ok and mode != "auto":
            self._error("Could not switch to %s." % mode)

    # -- dock ---------------------------------------------------------------
    def page_dock(self, box):
        box.pack_start(label("Choose which apps sit in the dock, where it goes and how big it is.",
                             "nova-subtitle", wrap=True), False, False, 0)
        pos = Gtk.ComboBoxText()
        for k, t in (("bottom", "Bottom"), ("left", "Left"), ("right", "Right")):
            pos.append(k, t)
        pos.set_active_id(self.s.get("dock_position", "bottom"))
        pos.connect("changed", lambda w: self._set("dock_position", w.get_active_id(), "dock"))
        size = Gtk.ComboBoxText()
        for v, t in ((32, "Small"), (40, "Medium"), (48, "Normal"), (56, "Large"), (64, "Huge")):
            size.append(str(v), t)
        size.set_active_id(str(self.s.get("dock_icon_size", 48)))
        size.connect("changed", lambda w: self._set("dock_icon_size", int(w.get_active_id()), "dock"))
        hide = Gtk.ComboBoxText()
        for k, t in (("never", "Always show"), ("smart", "Hide when a window covers it"),
                     ("always", "Always auto-hide")):
            hide.append(k, t)
        hide.set_active_id(self.s.get("dock_autohide", "never"))
        hide.connect("changed", lambda w: self._set("dock_autohide", w.get_active_id(), "dock"))
        box.pack_start(card(row("Position", pos), row("Icon size", size), row("Auto-hide", hide)),
                       False, False, 0)

        box.pack_start(label("Pinned apps", "nova-section"), False, False, 0)
        self.dock_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.dock_list.get_style_context().add_class("nova-card")
        box.pack_start(self.dock_list, False, False, 0)
        hb = Gtk.Box(spacing=8)
        self.dock_add = Gtk.ComboBoxText()
        self.dock_add.set_size_request(300, -1)
        add_b = Gtk.Button(label="Add to dock")
        add_b.connect("clicked", self.on_dock_add)
        reset = Gtk.Button(label="Reset to default")
        reset.connect("clicked", self.on_dock_reset)
        hb.pack_start(self.dock_add, False, False, 0)
        hb.pack_start(add_b, False, False, 0)
        hb.pack_end(reset, False, False, 0)
        box.pack_start(card(hb), False, False, 0)
        self._fill_dock()

    def _fill_dock(self):
        for ch in self.dock_list.get_children():
            self.dock_list.remove(ch)
        apps = C.dock_apps(self.s)
        all_apps = installed_apps()
        names = {a["id"]: a for a in all_apps}
        for i, app in enumerate(apps):
            info = names.get(app) or {"name": app, "icon": "application-x-executable"}
            hb = Gtk.Box(spacing=10)
            hb.set_border_width(4)
            hb.pack_start(Gtk.Image.new_from_icon_name(info["icon"], Gtk.IconSize.LARGE_TOOLBAR), False, False, 0)
            hb.pack_start(label(info["name"]), True, True, 0)
            for icon, tip, delta in (("go-up-symbolic", "Move up", -1), ("go-down-symbolic", "Move down", 1)):
                b = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
                b.set_tooltip_text(tip)
                b.set_sensitive(0 <= i + delta < len(apps))
                b.connect("clicked", self.on_dock_move, i, delta)
                hb.pack_start(b, False, False, 0)
            rm = Gtk.Button.new_from_icon_name("list-remove-symbolic", Gtk.IconSize.BUTTON)
            rm.set_tooltip_text("Remove from dock")
            rm.connect("clicked", self.on_dock_remove, i)
            hb.pack_start(rm, False, False, 0)
            self.dock_list.add(hb)
        self.dock_add.remove_all()
        for a in all_apps:
            if a["id"] not in apps:
                self.dock_add.append(a["id"], a["name"])
        self.dock_add.set_active(0)
        self.dock_list.show_all()

    def _save_dock(self, apps):
        self.s["dock_apps"] = apps
        self.commit("dock")
        self._fill_dock()

    def on_dock_move(self, _b, i, delta):
        apps = C.dock_apps(self.s)
        apps[i], apps[i + delta] = apps[i + delta], apps[i]
        self._save_dock(apps)

    def on_dock_remove(self, _b, i):
        apps = C.dock_apps(self.s)
        del apps[i]
        self._save_dock(apps)

    def on_dock_add(self, _b):
        app = self.dock_add.get_active_id()
        if app:
            self._save_dock(C.dock_apps(self.s) + [app])

    def on_dock_reset(self, _b):
        self.s["dock_apps"] = None
        self.commit("dock")
        self._fill_dock()

    # -- apps (install / uninstall) -----------------------------------------
    def page_apps(self, box):
        box.pack_start(label("Remove apps you don't need, or install new ones from the internet. "
                             "A small window opens to do the work; it may ask for your password.",
                             "nova-subtitle", wrap=True), False, False, 0)
        box.pack_start(label("Get new apps", "nova-section"), False, False, 0)
        quick = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=3,
                            column_spacing=8, row_spacing=8, homogeneous=True)
        for title, pkg in POPULAR:
            b = Gtk.Button(label=title)
            b.connect("clicked", lambda _b, p=pkg, t=title: self.run_apt("install", p, t))
            quick.add(b)
        self.search = Gtk.SearchEntry(placeholder_text="Search all apps (e.g. gimp, vlc, game)…")
        self.search.connect("activate", self.on_search)
        self.results = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        box.pack_start(card(quick, self.search, self.results), False, False, 0)

        box.pack_start(label("Installed apps", "nova-section"), False, False, 0)
        self.app_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.app_list.get_style_context().add_class("nova-card")
        box.pack_start(self.app_list, False, False, 0)
        self._fill_apps()

    def _fill_apps(self):
        for ch in self.app_list.get_children():
            self.app_list.remove(ch)
        for a in installed_apps():
            hb = Gtk.Box(spacing=10)
            hb.set_border_width(4)
            hb.pack_start(Gtk.Image.new_from_icon_name(a["icon"], Gtk.IconSize.LARGE_TOOLBAR), False, False, 0)
            hb.pack_start(label(a["name"]), True, True, 0)
            pkg = package_of(a["path"])
            if pkg and pkg not in PROTECTED:
                b = Gtk.Button(label="Uninstall")
                b.get_style_context().add_class("destructive-action")
                b.connect("clicked", lambda _b, p=pkg, n=a["name"]: self.run_apt("remove", p, n))
                hb.pack_start(b, False, False, 0)
            else:
                hb.pack_start(label("Part of NovaOS", "nova-subtitle"), False, False, 0)
            self.app_list.add(hb)
        self.app_list.show_all()

    def on_search(self, entry):
        q = entry.get_text().strip()
        for ch in self.results.get_children():
            self.results.remove(ch)
        if not q:
            return
        r = C.run("apt-cache", "search", "--names-only", q)
        lines = (r.stdout.splitlines() if r and r.returncode == 0 else [])[:25]
        if not lines:
            self.results.add(label("Nothing found. If you have never installed anything, "
                                   "first click “Refresh app list” below.", "nova-subtitle", wrap=True))
            rb = Gtk.Button(label="Refresh app list")
            rb.connect("clicked", lambda _b: self.run_apt("update", "", "app list"))
            self.results.add(rb)
        for line in lines:
            pkg, _sep, desc = line.partition(" - ")
            hb = Gtk.Box(spacing=10)
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            v.pack_start(label(pkg), False, False, 0)
            v.pack_start(label(desc, "nova-subtitle", wrap=True), False, False, 0)
            hb.pack_start(v, True, True, 0)
            b = Gtk.Button(label="Install")
            b.connect("clicked", lambda _b, p=pkg: self.run_apt("install", p, p))
            b.set_valign(Gtk.Align.CENTER)
            hb.pack_start(b, False, False, 0)
            self.results.add(hb)
        self.results.show_all()

    def run_apt(self, action, pkg, title):
        if action == "install":
            cmd = "sudo apt-get update -q && sudo apt-get install -y %s" % pkg
            head = "Installing %s" % title
        elif action == "remove":
            cmd = "sudo apt-get remove -y %s && sudo rm -f %s" % (
                pkg, " ".join("/usr/local/share/applications/" + os.path.basename(f)
                              for f in package_desktops(pkg)) or "/dev/null/none")
            head = "Removing %s" % title
        else:
            cmd = "sudo apt-get update"
            head = "Refreshing the app list"
        script = ("echo '%s…'; echo; if %s; then echo; echo 'Done! You can close this window.'; "
                  "else echo; echo 'Something went wrong (see above). Check your internet connection.'; fi; "
                  "sleep 3" % (head, cmd))

        def work():
            subprocess.run(["xfce4-terminal", "--disable-server", "-T", head, "--hold",
                            "-x", "bash", "-c", script])
            GLib.idle_add(self._after_apt)
        threading.Thread(target=work, daemon=True).start()

    def _after_apt(self):
        self._fill_apps()
        self._fill_dock()
        C.apply_dock(dict(self.s))
        return False

    def page_keyboard(self, box):
        combo = Gtk.ComboBoxText()
        for code, name in LAYOUTS:
            combo.append(code, name)
        if not combo.set_active_id(C.current_layout()):
            combo.append(C.current_layout(), C.current_layout())
            combo.set_active_id(C.current_layout())
        combo.connect("changed", lambda w: C.set_layout(w.get_active_id()))
        test = Gtk.Entry(placeholder_text="Type here to test your layout")
        box.pack_start(card(row("Keyboard layout", combo), test), False, False, 0)
        adv = Gtk.Button(label="Shortcuts and more…")
        adv.connect("clicked", lambda _b: launch("xfce4-keyboard-settings"))
        box.pack_start(card(row("Keyboard shortcuts", adv,
                                "Alt+F3 app search · Super+E Files · Ctrl+Alt+T Terminal · Super+I Settings")),
                       False, False, 0)

    def page_time(self, box):
        clock = Gtk.Switch(active=bool(self.s.get("clock_24h", True)))
        clock.connect("notify::active", lambda w, _p: self._set("clock_24h", w.get_active(), "panel"))
        tzs = []
        r = C.run("timedatectl", "list-timezones")
        if r and r.returncode == 0:
            tzs = r.stdout.split()
        cur = ""
        r = C.run("timedatectl", "show", "-p", "Timezone", "--value")
        if r and r.returncode == 0:
            cur = r.stdout.strip()
        self.tz_entry = Gtk.Entry(text=cur, width_chars=26)
        store = Gtk.ListStore(str)
        for t in tzs:
            store.append([t])
        comp = Gtk.EntryCompletion(model=store, text_column=0, minimum_key_length=1)
        comp.set_match_func(lambda c, key, it: key.lower() in store[it][0].lower())
        self.tz_entry.set_completion(comp)
        set_b = Gtk.Button(label="Set")
        set_b.connect("clicked", self.on_timezone, set(tzs))
        hb = Gtk.Box(spacing=8)
        hb.pack_start(self.tz_entry, False, False, 0)
        hb.pack_start(set_b, False, False, 0)
        box.pack_start(card(row("Time zone", hb, "Start typing a city, e.g. Europe/Brussels"),
                            row("24-hour clock", clock)), False, False, 0)

    def on_timezone(self, _b, valid):
        tz = self.tz_entry.get_text().strip()
        if tz not in valid:
            self._error("Unknown time zone: %s" % tz)
            return
        r = C.run("timedatectl", "set-timezone", tz)
        if not r or r.returncode != 0:
            self._error("Could not set the time zone.\n%s" % (r.stderr if r else ""))

    def page_sound(self, box):
        vol = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        vol.set_size_request(280, -1)
        r = C.run("pactl", "get-sink-volume", "@DEFAULT_SINK@")
        try:
            vol.set_value(int(r.stdout.split("/")[1].strip().rstrip("%")))
        except (AttributeError, IndexError, ValueError):
            vol.set_value(50)
        vol.connect("value-changed", lambda w: C.run("pactl", "set-sink-volume", "@DEFAULT_SINK@",
                                                      "%d%%" % int(w.get_value())))
        mute = Gtk.Switch()
        r = C.run("pactl", "get-sink-mute", "@DEFAULT_SINK@")
        mute.set_active(bool(r and "yes" in r.stdout))
        mute.connect("notify::active", lambda w, _p: C.run("pactl", "set-sink-mute", "@DEFAULT_SINK@",
                                                            "1" if w.get_active() else "0"))
        adv = Gtk.Button(label="Open volume mixer…")
        adv.connect("clicked", lambda _b: launch("pavucontrol"))
        box.pack_start(card(row("Volume", vol), row("Mute", mute), row("Devices and apps", adv)),
                       False, False, 0)

    def page_network(self, box):
        r = C.run("nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active")
        lines = [l for l in (r.stdout.splitlines() if r and r.returncode == 0 else []) if l]
        status = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        if lines:
            for l in lines:
                name, typ, dev = (l.split(":") + ["", "", ""])[:3]
                if typ == "loopback":
                    continue
                status.pack_start(label("● Connected: %s (%s)" % (name, dev)), False, False, 0)
        if not status.get_children():
            status.pack_start(label("Not connected. NovaOS works fully offline."), False, False, 0)
        edit = Gtk.Button(label="Network connections…")
        edit.connect("clicked", lambda _b: launch("nm-connection-editor"))
        box.pack_start(card(status, row("Configure connections", edit)), False, False, 0)

    # -- system specs (live) ----------------------------------------------
    def page_specs(self, box):
        box.pack_start(label("What this computer (or virtual machine) has, updated every 2 seconds.",
                             "nova-subtitle", wrap=True), False, False, 0)
        self.spec_labels = {}
        hw_rows, live_rows = [], []
        for key, title in (("cpu", "Processor"), ("cores", "CPU cores"), ("arch", "Architecture"),
                           ("virt", "Running on"), ("gpu", "Graphics"), ("display", "Display"),
                           ("os", "Operating system"), ("kernel", "Kernel")):
            lb = label("…", xalign=1.0, wrap=True)
            lb.set_max_width_chars(48)
            self.spec_labels[key] = lb
            hw_rows.append(row(title, lb))
        box.pack_start(label("Hardware", "nova-section"), False, False, 0)
        box.pack_start(card(*hw_rows), False, False, 0)
        for key, title in (("cpuuse", "CPU usage"), ("mem", "Memory"), ("disk", "Disk (system)"),
                           ("uptime", "Uptime")):
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            lb = label("…", xalign=1.0)
            bar = Gtk.LevelBar(min_value=0, max_value=1)
            bar.set_size_request(260, 6)
            v.pack_start(lb, False, False, 0)
            if key != "uptime":
                v.pack_start(bar, False, False, 0)
            self.spec_labels[key] = (lb, bar)
            live_rows.append(row(title, v))
        box.pack_start(label("Usage", "nova-section"), False, False, 0)
        box.pack_start(card(*live_rows), False, False, 0)
        copy = Gtk.Button(label="Copy specs to clipboard")
        copy.connect("clicked", self.on_copy_specs)
        box.pack_start(card(row("Share these details", copy)), False, False, 0)
        self._cpu_prev = None
        self._fill_static_specs()
        self._update_specs()
        GLib.timeout_add_seconds(2, self._update_specs)

    def _fill_static_specs(self):
        cpu, cores = "", 0
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    k = line.split(":", 1)[0].strip().lower()
                    if k in ("model name", "hardware", "cpu model") and not cpu:
                        cpu = line.split(":", 1)[1].strip()
                    if k == "processor":
                        cores += 1
        except OSError:
            pass
        if cpu in ("", "-"):
            cpu = ""
            r = C.run("lscpu")
            for line in (r.stdout.splitlines() if r else []):
                if line.startswith(("Model name", "Vendor ID")) and line.split(":", 1)[1].strip() not in ("", "-"):
                    cpu = line.split(":", 1)[1].strip()
                    if line.startswith("Model name"):
                        break
        virt = C.run("systemd-detect-virt")
        virt = virt.stdout.strip() if virt and virt.returncode == 0 else "none"
        virt_name = {"none": "Real hardware", "qemu": "Virtual machine (QEMU / UTM)",
                     "kvm": "Virtual machine (KVM)", "apple": "Virtual machine (Apple Virtualization)",
                     "vmware": "Virtual machine (VMware)", "oracle": "Virtual machine (VirtualBox)",
                     "microsoft": "Virtual machine (Hyper-V)"}.get(virt, "Virtual machine (%s)" % virt)
        gpu = "unknown"
        r = C.run("lspci")
        if r and r.returncode == 0:
            for line in r.stdout.splitlines():
                if any(t in line for t in ("VGA", "Display", "3D controller")):
                    gpu = line.split(":", 2)[-1].strip()
                    break
        outs = C.outputs()
        disp = ", ".join("%s (%s)" % (o, i["current"] or "?") for o, i in outs.items()) or "unknown"
        osname = "NovaOS %s" % VERSION
        try:
            for line in open("/etc/os-release"):
                if line.startswith("PRETTY_NAME="):
                    osname = line.split("=", 1)[1].strip().strip('"') + " (Ubuntu 24.04 base)"
        except OSError:
            pass
        if not cpu:
            cpu = "%s processor" % ("Apple silicon / ARM" if platform.machine() == "aarch64" else platform.machine())
        vals = {"cpu": cpu, "cores": str(cores or os.cpu_count() or "?"),
                "arch": platform.machine(), "virt": virt_name, "gpu": gpu, "display": disp,
                "os": osname, "kernel": platform.release()}
        for k, v in vals.items():
            self.spec_labels[k].set_text(v)

    @staticmethod
    def _fmt_bytes(n):
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024 or unit == "TB":
                return "%.1f %s" % (n, unit) if unit != "B" else "%d B" % n
            n /= 1024.0

    def _update_specs(self):
        if not self.get_visible():
            return False
        try:
            with open("/proc/stat") as f:
                parts = [int(x) for x in f.readline().split()[1:]]
            idle, total = parts[3] + parts[4], sum(parts)
            if self._cpu_prev:
                di, dt = idle - self._cpu_prev[0], total - self._cpu_prev[1]
                use = 1 - di / dt if dt else 0
                lb, bar = self.spec_labels["cpuuse"]
                lb.set_text("%d %%" % round(use * 100))
                bar.set_value(max(0, min(1, use)))
            self._cpu_prev = (idle, total)
            mem = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    k, v = line.split(":", 1)
                    mem[k] = int(v.split()[0]) * 1024
            used = mem["MemTotal"] - mem.get("MemAvailable", mem.get("MemFree", 0))
            lb, bar = self.spec_labels["mem"]
            lb.set_text("%s used of %s" % (self._fmt_bytes(used), self._fmt_bytes(mem["MemTotal"])))
            bar.set_value(used / mem["MemTotal"])
            st = os.statvfs("/")
            tot, free = st.f_blocks * st.f_frsize, st.f_bavail * st.f_frsize
            lb, bar = self.spec_labels["disk"]
            lb.set_text("%s free of %s" % (self._fmt_bytes(free), self._fmt_bytes(tot)))
            bar.set_value((tot - free) / tot if tot else 0)
            with open("/proc/uptime") as f:
                up = int(float(f.read().split()[0]))
            self.spec_labels["uptime"][0].set_text("%dh %02dm" % (up // 3600, up % 3600 // 60))
        except (OSError, ValueError, KeyError, ZeroDivisionError):
            pass
        return True

    def on_copy_specs(self, _b):
        lines = []
        for k, v in self.spec_labels.items():
            text = v.get_text() if isinstance(v, Gtk.Label) else v[0].get_text()
            lines.append("%s: %s" % (k, text))
        cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        cb.set_text("\n".join(lines), -1)

    def page_about(self, box):
        top = Gtk.Box(spacing=18)
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_size("/usr/share/novaos/logo/novaos-logo.svg", 96, 96)
            top.pack_start(Gtk.Image.new_from_pixbuf(pb), False, False, 0)
        except GLib.Error:
            pass
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        v.set_valign(Gtk.Align.CENTER)
        v.pack_start(label("NovaOS", "nova-big"), False, False, 0)
        v.pack_start(label("Version %s · based on Ubuntu 24.04 LTS" % VERSION, "nova-subtitle"), False, False, 0)
        top.pack_start(v, False, False, 0)
        box.pack_start(top, False, False, 6)

        cpu = "unknown"
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        cpu = line.split(":", 1)[1].strip()
                        break
            if cpu == "unknown":
                cpu = "%d-core %s" % (os.cpu_count() or 1, platform.machine())
            with open("/proc/meminfo") as f:
                mem_kb = int(f.readline().split()[1])
        except (OSError, ValueError, IndexError):
            mem_kb = 0
        live = "boot=casper" in open("/proc/cmdline").read()
        info = [("Device name", platform.node()), ("Processor", cpu),
                ("Memory", "%.1f GB" % (mem_kb / 1048576)), ("Architecture", platform.machine()),
                ("Kernel", platform.release()), ("Desktop", "NovaOS Shell (XFCE 4.18, customised)"),
                ("Session", "Live session" if live else "Installed")]
        rows = []
        for k, val in info:
            rows.append(row(k, label(val, xalign=1.0)))
        box.pack_start(card(*rows), False, False, 0)
        specs = Gtk.Button(label="Full system specs…")
        specs.connect("clicked", lambda _b: self._goto("specs"))
        box.pack_start(card(row("Detailed hardware and live usage", specs)), False, False, 0)
        lic = Gtk.Button(label="Open-source licences…")
        lic.connect("clicked", lambda _b: launch("mousepad", "/usr/share/doc/novaos/LICENSES.md"))
        allset = Gtk.Button(label="All system settings…")
        allset.connect("clicked", lambda _b: launch("xfce4-settings-manager"))
        box.pack_start(card(row("Licences and notices", lic), row("Advanced (XFCE) settings", allset)),
                       False, False, 0)

    def _error(self, msg):
        d = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.ERROR,
                              buttons=Gtk.ButtonsType.CLOSE, text=msg)
        d.run()
        d.destroy()


class App(Gtk.Application):
    def __init__(self, page):
        super().__init__(application_id="os.nova.Settings")
        self.page = page

    def do_activate(self):
        win = self.get_active_window()
        if not win:
            prov = Gtk.CssProvider()
            prov.load_from_data(CSS)
            Gtk.StyleContext.add_provider_for_screen(
                Gtk.Window().get_screen(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            win = SettingsWindow(self, self.page)
        win.show_all()
        win.present()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default="personalization", choices=[p[0] for p in PAGES])
    args = ap.parse_args()
    App(args.page).run([sys.argv[0]])


if __name__ == "__main__":
    main()
