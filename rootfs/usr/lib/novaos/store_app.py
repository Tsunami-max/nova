#!/usr/bin/env python3
"""Nova Store - NovaOS's own App Store.

Browses the Flathub catalogue that flatpak keeps on disk (appstream), and
installs, opens, updates and removes apps with flatpak. Only apps that run on
this computer's processor are listed (Flathub's catalogue is per CPU type).
"""
import gzip
import os
import platform
import subprocess
import sys
import threading
import urllib.request
import xml.etree.ElementTree as ET

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, Gio, GLib, Gtk, Pango  # noqa: E402

GLib.set_prgname("novaos-store")

ARCH = {"aarch64": "aarch64", "arm64": "aarch64", "x86_64": "x86_64", "amd64": "x86_64"}.get(
    platform.machine(), platform.machine())
APPSTREAM_DIRS = ["/var/lib/flatpak/appstream/flathub/%s/active" % ARCH,
                  os.path.expanduser("~/.local/share/flatpak/appstream/flathub/%s/active" % ARCH)]

CATEGORIES = [  # (id, title, icon, freedesktop categories)
    ("home", "Discover", "novaos-store", None),
    ("games", "Games", "applications-games", {"Game"}),
    ("internet", "Internet", "applications-internet", {"Network", "WebBrowser", "Chat", "InstantMessaging",
                                                        "Email"}),
    ("office", "Office", "applications-office", {"Office", "WordProcessor", "Spreadsheet", "Presentation"}),
    ("graphics", "Graphics & Photos", "applications-graphics", {"Graphics", "Photography", "2DGraphics",
                                                                 "3DGraphics"}),
    ("video", "Music & Video", "applications-multimedia", {"AudioVideo", "Audio", "Video", "Music", "Player"}),
    ("dev", "Developer", "applications-development", {"Development", "IDE"}),
    ("edu", "Education", "applications-education", {"Education", "Science"}),
    ("utils", "Utilities", "applications-utilities", {"Utility", "System", "Settings"}),
    ("installed", "Installed", "emblem-ok-symbolic", None),
    ("updates", "Updates", "system-software-update", None),
]
# Shown first on the Discover page when they exist for this processor.
FEATURED = ["org.prismlauncher.PrismLauncher", "net.supertuxkart.SuperTuxKart", "com.github.Anuken.Mindustry",
            "org.chromium.Chromium", "com.brave.Browser", "com.obsproject.Studio", "com.visualstudio.code",
            "org.gimp.GIMP", "org.kde.krita", "org.inkscape.Inkscape", "org.videolan.VLC",
            "org.telegram.desktop", "com.spotify.Client", "com.discordapp.Discord", "org.libreoffice.LibreOffice",
            "org.openttd.OpenTTD", "net.minetest.Minetest", "io.mrarm.mcpelauncher", "org.kde.kdenlive",
            "com.github.tchx84.Flatseal", "org.audacityteam.Audacity", "io.github.shiftey.Desktop",
            "net.lutris.Lutris", "org.signal.Signal", "md.obsidian.Obsidian", "org.blender.Blender"]
GAME_PICKS = ["org.prismlauncher.PrismLauncher", "net.supertuxkart.SuperTuxKart", "com.github.Anuken.Mindustry",
              "net.minetest.Minetest", "org.openttd.OpenTTD", "io.mrarm.mcpelauncher", "org.zdoom.GZDoom",
              "com.play0ad.zeroad", "net.openra.OpenRA", "org.supertuxproject.SuperTux", "io.github.endless_sky.endless_sky",
              "org.freeciv.Freeciv", "net.wz2100.wz2100", "com.moonlight_stream.Moonlight", "org.libretro.RetroArch"]

CSS = b"""
.hero { background-image: linear-gradient(120deg, #3b2a8f, #6d4cff 45%, #1aa0d8); border-radius: 18px;
        padding: 26px 30px; color: white; }
.hero-title { font-size: 24pt; font-weight: 800; color: white; }
.hero-sub { color: alpha(white, 0.85); }
.ptitle { font-size: 17pt; font-weight: 800; }
.section { font-size: 12pt; font-weight: 700; margin-top: 8px; }
.sub { opacity: 0.65; }
.card { background-color: alpha(@theme_fg_color, 0.05); border-radius: 14px; padding: 12px; }
.card:hover { background-color: alpha(@theme_fg_color, 0.09); }
.appname { font-weight: 700; }
.bigname { font-size: 20pt; font-weight: 800; }
.pill { border-radius: 999px; padding: 4px 16px; }
.sidebar row { padding: 9px 12px; border-radius: 10px; margin: 2px 8px; }
.brand { font-size: 15pt; font-weight: 800; }
"""


def run(*cmd, timeout=3600):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None


class App:
    __slots__ = ("id", "name", "summary", "description", "icon", "categories", "developer",
                 "screenshot", "homepage", "license")

    def __init__(self):
        self.id = self.name = self.summary = self.description = self.icon = ""
        self.developer = self.screenshot = self.homepage = self.license = ""
        self.categories = set()


def text_of(el):
    return "".join(el.itertext()).strip() if el is not None else ""


def load_catalogue():
    """Parse Flathub's appstream file into {app id: App}."""
    for d in APPSTREAM_DIRS:
        for name in ("appstream.xml.gz", "appstream.xml"):
            path = os.path.join(d, name)
            if os.path.exists(path):
                return parse_appstream(path, d)
    return {}


def parse_appstream(path, base):
    apps = {}
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rb") as f:
        for _ev, el in ET.iterparse(f):
            if el.tag != "component":
                continue
            if el.get("type") not in ("desktop", "desktop-application", "console-application"):
                el.clear()
                continue
            a = App()
            bundle = el.find("bundle")
            if bundle is not None and bundle.text and bundle.text.startswith("app/"):
                a.id = bundle.text.split("/")[1]
            else:
                a.id = (el.findtext("id") or "").removesuffix(".desktop")
            for n in el.findall("name"):
                if not n.get("{http://www.w3.org/XML/1998/namespace}lang"):
                    a.name = text_of(n)
            for s in el.findall("summary"):
                if not s.get("{http://www.w3.org/XML/1998/namespace}lang"):
                    a.summary = text_of(s)
            desc = el.find("description")
            if desc is not None:
                parts = []
                for child in desc:
                    if child.get("{http://www.w3.org/XML/1998/namespace}lang"):
                        continue
                    if child.tag == "p":
                        parts.append(text_of(child))
                    elif child.tag in ("ul", "ol"):
                        parts.extend("• " + text_of(li) for li in child if not li.get(
                            "{http://www.w3.org/XML/1998/namespace}lang"))
                a.description = "\n\n".join(p for p in parts if p)
            best = 0
            for ic in el.findall("icon"):
                if ic.get("type") == "cached":
                    h = int(ic.get("height") or 64)
                    for size in ("%dx%d" % (h, h), "128x128", "64x64"):
                        p = os.path.join(base, "icons", size, ic.text or "")
                        if os.path.exists(p) and h > best:
                            a.icon, best = p, h
                            break
            a.categories = {c.text for c in el.iter("category") if c.text}
            lang = "{http://www.w3.org/XML/1998/namespace}lang"
            dev = el.find("developer")
            names = [n for n in (dev.findall("name") if dev is not None else el.findall("developer_name"))
                     if not n.get(lang)]
            a.developer = text_of(names[0]) if names else ""
            for u in el.findall("url"):
                if u.get("type") == "homepage":
                    a.homepage = (u.text or "").strip()
            a.license = el.findtext("project_license") or ""
            shots = el.find("screenshots")
            if shots is not None:
                for sh in shots.findall("screenshot"):
                    imgs = [i for i in sh.findall("image") if i.text]
                    if not imgs:
                        continue
                    # a medium-size thumbnail is enough
                    imgs.sort(key=lambda i: abs(int(i.get("width") or 1248) - 752))
                    a.screenshot = imgs[0].text.strip()
                    if sh.get("type") == "default":
                        break
            if a.id and a.name and "runtime" not in a.categories:
                apps[a.id] = a
            el.clear()
    return apps


def installed_apps():
    r = run("flatpak", "list", "--app", "--columns=application,name,version,origin")
    out = {}
    if r and r.returncode == 0:
        for line in r.stdout.splitlines():
            parts = line.split("\t")
            if parts and parts[0]:
                out[parts[0]] = parts[1] if len(parts) > 1 else parts[0]
    return out


def pixbuf(path, size):
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)
    except GLib.Error:
        return None


class StoreWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="App Store")
        self.set_default_size(1180, 820)
        self.set_icon_name("novaos-store")
        self.catalogue = {}
        self.installed = {}
        self.busy = {}  # app id -> "install" | "remove"
        self.current = "home"
        self.page_limit = 60

        hb = Gtk.HeaderBar(show_close_button=True, title="App Store")
        self.set_titlebar(hb)
        self.back = Gtk.Button.new_from_icon_name("go-previous-symbolic", Gtk.IconSize.BUTTON)
        self.back.connect("clicked", lambda _b: self.show_category(self.current))
        hb.pack_start(self.back)
        self.search = Gtk.SearchEntry(placeholder_text="Search apps and games")
        self.search.set_size_request(380, -1)
        self.search.connect("search-changed", self.on_search)
        hb.set_custom_title(self.search)
        self.spinner = Gtk.Spinner()
        hb.pack_end(self.spinner)

        outer = Gtk.Box()
        self.add(outer)
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        side.set_size_request(220, -1)
        brand = Gtk.Box(spacing=10)
        brand.set_margin_start(18)
        brand.set_margin_top(16)
        brand.set_margin_bottom(12)
        brand.pack_start(Gtk.Image.new_from_icon_name("novaos-store", Gtk.IconSize.DND), False, False, 0)
        bl = Gtk.Label(label="Nova Store", xalign=0)
        bl.get_style_context().add_class("brand")
        brand.pack_start(bl, False, False, 0)
        side.pack_start(brand, False, False, 0)
        self.nav = Gtk.ListBox()
        self.nav.get_style_context().add_class("sidebar")
        for cid, title, icon, _c in CATEGORIES:
            r = Gtk.ListBoxRow()
            r.cid = cid
            b = Gtk.Box(spacing=10)
            b.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU), False, False, 0)
            b.pack_start(Gtk.Label(label=title, xalign=0), True, True, 0)
            r.add(b)
            self.nav.add(r)
        self.nav.connect("row-selected", self.on_nav)
        side.pack_start(self.nav, True, True, 0)
        upd = Gtk.Button(label="Update NovaOS…")
        upd.set_margin_start(14)
        upd.set_margin_end(14)
        upd.set_margin_bottom(14)
        upd.connect("clicked", lambda _b: self.launch(["nova-update"]))
        side.pack_end(upd, False, False, 0)
        outer.pack_start(side, False, False, 0)
        outer.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)

        self.scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        outer.pack_start(self.scroll, True, True, 0)
        self.body = None
        self.set_body(self.message("Loading apps…", "The App Store is reading the app list."))
        self.load()

    # -- helpers --------------------------------------------------------------
    def launch(self, cmd):
        try:
            subprocess.Popen(cmd, start_new_session=True)
        except OSError:
            pass

    def set_body(self, widget):
        if self.body is not None:
            self.scroll.remove(self.body)
        self.body = widget
        self.scroll.add(widget)
        self.scroll.get_vadjustment().set_value(0)
        widget.show_all()
        self.back.set_visible(False)

    def message(self, title, sub, button=None):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        box.set_margin_top(120)
        img = Gtk.Image.new_from_icon_name("novaos-store", Gtk.IconSize.DIALOG)
        img.set_pixel_size(96)
        box.pack_start(img, False, False, 0)
        t = Gtk.Label(label=title)
        t.get_style_context().add_class("ptitle")
        box.pack_start(t, False, False, 0)
        s = Gtk.Label(label=sub)
        s.get_style_context().add_class("sub")
        s.set_line_wrap(True)
        s.set_max_width_chars(60)
        s.set_justify(Gtk.Justification.CENTER)
        box.pack_start(s, False, False, 0)
        if button:
            box.pack_start(button, False, False, 0)
        return box

    def page_box(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(24)
        return box

    def label(self, text, css=None, xalign=0):
        lb = Gtk.Label(label=text, xalign=xalign)
        lb.set_line_wrap(True)
        if css:
            lb.get_style_context().add_class(css)
        return lb

    # -- loading -------------------------------------------------------------
    def load(self, refresh=False):
        self.spinner.start()

        def work():
            if refresh or not any(os.path.exists(os.path.join(d, "appstream.xml.gz")) or
                                  os.path.exists(os.path.join(d, "appstream.xml")) for d in APPSTREAM_DIRS):
                run("flatpak", "update", "--appstream", "flathub", timeout=600)
            cat = load_catalogue()
            inst = installed_apps()
            GLib.idle_add(self.loaded, cat, inst)
        threading.Thread(target=work, daemon=True).start()

    def loaded(self, cat, inst):
        self.spinner.stop()
        self.catalogue, self.installed = cat, inst
        if not cat:
            retry = Gtk.Button(label="Try again")
            retry.get_style_context().add_class("suggested-action")
            retry.set_halign(Gtk.Align.CENTER)
            retry.connect("clicked", lambda _b: (self.set_body(self.message("Loading apps…", "Downloading the "
                                                                             "app list from Flathub.")),
                                                 self.load(True)))
            self.set_body(self.message("No app list yet", "NovaOS needs the internet once to download the list "
                                       "of apps. Check your connection and try again.", retry))
            return False
        row = self.nav.get_row_at_index(0)
        self.nav.select_row(row)
        self.show_category("home")
        # refresh the catalogue in the background once per start
        threading.Thread(target=self.background_refresh, daemon=True).start()
        return False

    def background_refresh(self):
        r = run("flatpak", "update", "--appstream", "flathub", timeout=600)
        if r and r.returncode == 0:
            cat = load_catalogue()
            if cat:
                GLib.idle_add(self._set_cat, cat)

    def _set_cat(self, cat):
        self.catalogue = cat
        return False

    def refresh_installed(self):
        self.installed = installed_apps()

    # -- navigation ----------------------------------------------------------
    def on_nav(self, _lb, row):
        if row is None:
            return
        self.search.set_text("")
        self.page_limit = 60
        self.show_category(row.cid)

    def show_category(self, cid):
        self.current = cid
        if not self.catalogue and cid not in ("installed", "updates"):
            return
        if cid == "home":
            self.show_home()
        elif cid == "installed":
            self.show_installed()
        elif cid == "updates":
            self.show_updates()
        else:
            _id, title, _icon, cats = next(c for c in CATEGORIES if c[0] == cid)
            apps = [a for a in self.catalogue.values() if a.categories & cats]
            if cid == "games":
                picks = [self.catalogue[i] for i in GAME_PICKS if i in self.catalogue]
                apps = picks + sorted((a for a in apps if a.id not in GAME_PICKS), key=lambda a: a.name.lower())
            else:
                apps.sort(key=lambda a: a.name.lower())
            self.show_list(title, "%d apps" % len(apps), apps)

    def on_search(self, entry):
        q = entry.get_text().strip().lower()
        if not q:
            self.show_category(self.current)
            return
        words = q.split()

        def score(a):
            n = a.name.lower()
            if n == q:
                return 0
            if n.startswith(q):
                return 1
            if q in n:
                return 2
            return 3
        hits = [a for a in self.catalogue.values()
                if all(w in (a.name + " " + a.summary + " " + a.id + " " + " ".join(a.categories)).lower()
                       for w in words)]
        hits.sort(key=lambda a: (score(a), a.name.lower()))
        self.page_limit = 60
        self.show_list('Results for "%s"' % entry.get_text().strip(), "%d apps" % len(hits), hits)

    # -- pages ---------------------------------------------------------------
    def show_home(self):
        box = self.page_box()
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        hero.get_style_context().add_class("hero")
        hero.pack_start(self.label("Nova Store", "hero-title"), False, False, 0)
        hero.pack_start(self.label("%d apps and games for NovaOS, free to install. One click — no Terminal."
                                   % len(self.catalogue), "hero-sub"), False, False, 0)
        box.pack_start(hero, False, False, 0)
        feat = [self.catalogue[i] for i in FEATURED if i in self.catalogue]
        if feat:
            box.pack_start(self.label("Editor's picks", "section"), False, False, 0)
            box.pack_start(self.grid(feat[:12]), False, False, 0)
        games = [self.catalogue[i] for i in GAME_PICKS if i in self.catalogue]
        if games:
            box.pack_start(self.label("Games", "section"), False, False, 0)
            box.pack_start(self.grid(games[:8]), False, False, 0)
        for cid, title in (("internet", "Internet"), ("graphics", "Create"), ("video", "Music & Video")):
            cats = next(c[3] for c in CATEGORIES if c[0] == cid)
            apps = [a for a in self.catalogue.values() if a.categories & cats and a.icon]
            apps.sort(key=lambda a: (a.id not in FEATURED, a.name.lower()))
            if apps:
                h = Gtk.Box()
                h.pack_start(self.label(title, "section"), True, True, 0)
                more = Gtk.Button(label="See all", relief=Gtk.ReliefStyle.NONE)
                more.connect("clicked", lambda _b, c=cid: self.select_nav(c))
                h.pack_end(more, False, False, 0)
                box.pack_start(h, False, False, 0)
                box.pack_start(self.grid(apps[:4]), False, False, 0)
        self.set_body(box)

    def select_nav(self, cid):
        for i, c in enumerate(CATEGORIES):
            if c[0] == cid:
                self.nav.select_row(self.nav.get_row_at_index(i))

    def show_list(self, title, sub, apps):
        box = self.page_box()
        box.pack_start(self.label(title, "ptitle"), False, False, 0)
        box.pack_start(self.label(sub, "sub"), False, False, 0)
        if not apps:
            box.pack_start(self.label("Nothing found. Try another word.", "sub"), False, False, 0)
        box.pack_start(self.grid(apps[:self.page_limit]), False, False, 0)
        if len(apps) > self.page_limit:
            more = Gtk.Button(label="Show more")
            more.set_halign(Gtk.Align.CENTER)

            def on_more(_b):
                self.page_limit += 60
                self.show_list(title, sub, apps)
            more.connect("clicked", on_more)
            box.pack_start(more, False, False, 0)
        self.set_body(box)

    def grid(self, apps):
        flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=4,
                           min_children_per_line=2, column_spacing=12, row_spacing=12, homogeneous=True)
        for a in apps:
            flow.add(self.card(a))
        return flow

    def card(self, a):
        ev = Gtk.EventBox()
        box = Gtk.Box(spacing=12)
        box.get_style_context().add_class("card")
        img = Gtk.Image()
        pb = pixbuf(a.icon, 56) if a.icon else None
        if pb:
            img.set_from_pixbuf(pb)
        else:
            img.set_from_icon_name("application-x-executable", Gtk.IconSize.DIALOG)
            img.set_pixel_size(56)
        box.pack_start(img, False, False, 0)
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        n = Gtk.Label(label=a.name, xalign=0)
        n.get_style_context().add_class("appname")
        n.set_ellipsize(Pango.EllipsizeMode.END)
        v.pack_start(n, False, False, 0)
        s = Gtk.Label(label=a.summary, xalign=0)
        s.get_style_context().add_class("sub")
        s.set_ellipsize(Pango.EllipsizeMode.END)
        s.set_max_width_chars(28)
        v.pack_start(s, False, False, 0)
        v.pack_start(self.action_button(a, small=True), False, False, 4)
        box.pack_start(v, True, True, 0)
        ev.add(box)
        ev.connect("button-release-event", lambda _w, e: self.show_app(a) if e.button == 1 else None)
        return ev

    def action_button(self, a, small=False):
        hb = Gtk.Box(spacing=6)
        hb.set_halign(Gtk.Align.START)
        state = self.busy.get(a.id)
        if state:
            sp = Gtk.Spinner(active=True)
            hb.pack_start(sp, False, False, 0)
            hb.pack_start(self.label("Installing…" if state == "install" else "Removing…", "sub"),
                          False, False, 0)
        elif a.id in self.installed:
            op = Gtk.Button(label="Open")
            op.get_style_context().add_class("pill")
            op.connect("clicked", lambda _b: self.launch(["flatpak", "run", a.id]))
            hb.pack_start(op, False, False, 0)
            if not small:
                rm = Gtk.Button(label="Remove")
                rm.get_style_context().add_class("destructive-action")
                rm.get_style_context().add_class("pill")
                rm.connect("clicked", lambda _b: self.remove(a))
                hb.pack_start(rm, False, False, 0)
        else:
            ins = Gtk.Button(label="Install" if not small else "Get")
            ins.get_style_context().add_class("suggested-action")
            ins.get_style_context().add_class("pill")
            ins.connect("clicked", lambda _b: self.install(a))
            hb.pack_start(ins, False, False, 0)
        return hb

    def show_app(self, a):
        box = self.page_box()
        top = Gtk.Box(spacing=18)
        img = Gtk.Image()
        pb = pixbuf(a.icon, 128) if a.icon else None
        if pb:
            img.set_from_pixbuf(pb)
        else:
            img.set_from_icon_name("application-x-executable", Gtk.IconSize.DIALOG)
            img.set_pixel_size(128)
        top.pack_start(img, False, False, 0)
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        v.set_valign(Gtk.Align.CENTER)
        v.pack_start(self.label(a.name, "bigname"), False, False, 0)
        v.pack_start(self.label(a.summary), False, False, 0)
        if a.developer:
            v.pack_start(self.label(a.developer, "sub"), False, False, 0)
        self.detail_action = Gtk.Box()
        self.detail_action.pack_start(self.action_button(a), False, False, 0)
        v.pack_start(self.detail_action, False, False, 6)
        top.pack_start(v, True, True, 0)
        box.pack_start(top, False, False, 0)
        if a.screenshot:
            shot = Gtk.Image()
            shot.set_halign(Gtk.Align.START)
            box.pack_start(shot, False, False, 0)
            threading.Thread(target=self.fetch_shot, args=(a.screenshot, shot), daemon=True).start()
        if a.description:
            box.pack_start(self.label("About", "section"), False, False, 0)
            d = self.label(a.description)
            d.set_selectable(True)
            d.set_max_width_chars(100)
            box.pack_start(d, False, False, 0)
        facts = []
        if a.license:
            facts.append("Licence: %s" % a.license)
        facts.append("App ID: %s" % a.id)
        box.pack_start(self.label("   ·   ".join(facts), "sub"), False, False, 0)
        if a.homepage:
            box.pack_start(Gtk.LinkButton(uri=a.homepage, label="Website", halign=Gtk.Align.START),
                           False, False, 0)
        self.detail_app = a
        self.set_body(box)
        self.back.set_visible(True)

    def fetch_shot(self, url, img):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NovaOS-Store"})
            data = urllib.request.urlopen(req, timeout=20).read()
            loader = GdkPixbuf.PixbufLoader()
            loader.write(data)
            loader.close()
            pb = loader.get_pixbuf()
            w = min(820, pb.get_width())
            pb = pb.scale_simple(w, int(pb.get_height() * w / pb.get_width()), GdkPixbuf.InterpType.BILINEAR)
            GLib.idle_add(img.set_from_pixbuf, pb)
        except Exception:  # noqa: BLE001 - screenshots are optional
            pass

    def show_installed(self):
        self.refresh_installed()
        box = self.page_box()
        box.pack_start(self.label("Installed", "ptitle"), False, False, 0)
        box.pack_start(self.label("Apps you got from the App Store. The apps that come with NovaOS "
                                  "(Firefox, Writer, Paint…) are updated by NovaOS Update.", "sub"), False, False, 0)
        lst = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        lst.get_style_context().add_class("card")
        for aid, name in sorted(self.installed.items(), key=lambda x: x[1].lower()):
            a = self.catalogue.get(aid)
            if a is None:
                a = App()
                a.id, a.name = aid, name
            row = Gtk.Box(spacing=12)
            row.set_border_width(8)
            img = Gtk.Image()
            pb = pixbuf(a.icon, 40) if a.icon else None
            if pb:
                img.set_from_pixbuf(pb)
            else:
                img.set_from_icon_name("application-x-executable", Gtk.IconSize.DND)
            row.pack_start(img, False, False, 0)
            row.pack_start(self.label(a.name, "appname"), True, True, 0)
            row.pack_end(self.action_button(a), False, False, 0)
            lst.add(row)
        if not self.installed:
            box.pack_start(self.message("Nothing installed yet", "Find something you like on the Discover page."),
                           False, False, 0)
        else:
            box.pack_start(lst, False, False, 0)
        self.set_body(box)

    def show_updates(self):
        box = self.page_box()
        box.pack_start(self.label("Updates", "ptitle"), False, False, 0)
        status = self.label("Checking for updates…", "sub")
        box.pack_start(status, False, False, 0)
        btn = Gtk.Button(label="Update all apps")
        btn.get_style_context().add_class("suggested-action")
        btn.set_halign(Gtk.Align.START)
        btn.set_sensitive(False)
        box.pack_start(btn, False, False, 0)
        nova = Gtk.Button(label="Update NovaOS itself…")
        nova.set_halign(Gtk.Align.START)
        nova.connect("clicked", lambda _b: self.launch(["nova-update"]))
        box.pack_start(nova, False, False, 0)
        self.set_body(box)

        def check():
            r = run("flatpak", "remote-ls", "--updates", "--app", "--columns=application", timeout=300)
            ids = [x for x in (r.stdout.split() if r and r.returncode == 0 else []) if x != "Application"]
            GLib.idle_add(done, ids)

        def done(ids):
            if ids:
                status.set_text("%d app update%s ready: %s" % (len(ids), "" if len(ids) == 1 else "s", ", ".join(
                    self.catalogue[i].name if i in self.catalogue else i for i in ids)))
                btn.set_sensitive(True)
            else:
                status.set_text("All your App Store apps are up to date.")
            return False

        def update(_b):
            btn.set_sensitive(False)
            status.set_text("Updating…")
            self.spinner.start()

            def work():
                r = run("flatpak", "update", "-y", "--noninteractive")
                GLib.idle_add(finish, r is not None and r.returncode == 0)
            threading.Thread(target=work, daemon=True).start()

        def finish(ok):
            self.spinner.stop()
            status.set_text("Everything is up to date." if ok else "Some updates did not work. Try again later.")
            return False
        btn.connect("clicked", update)
        threading.Thread(target=check, daemon=True).start()

    # -- install / remove -------------------------------------------------------
    def refresh_view(self):
        if self.current == "installed":
            self.show_installed()
        elif getattr(self, "detail_app", None) and self.back.get_visible():
            self.show_app(self.detail_app)
        elif self.search.get_text().strip():
            self.on_search(self.search)
        else:
            self.show_category(self.current)

    def install(self, a):
        self.busy[a.id] = "install"
        self.refresh_view()
        self.spinner.start()

        def work():
            r = run("flatpak", "install", "-y", "--noninteractive", "--system", "flathub", a.id)
            GLib.idle_add(self.finished, a, "install", r)
        threading.Thread(target=work, daemon=True).start()

    def remove(self, a):
        self.busy[a.id] = "remove"
        self.refresh_view()
        self.spinner.start()

        def work():
            r = run("flatpak", "uninstall", "-y", "--noninteractive", a.id)
            if r and r.returncode == 0:
                run("flatpak", "uninstall", "-y", "--noninteractive", "--unused")
            GLib.idle_add(self.finished, a, "remove", r)
        threading.Thread(target=work, daemon=True).start()

    def finished(self, a, what, r):
        self.busy.pop(a.id, None)
        if not self.busy:
            self.spinner.stop()
        self.refresh_installed()
        ok = r is not None and r.returncode == 0
        n = Gio.Notification.new("%s %s" % (a.name, ("is installed" if what == "install" else "was removed")
                                            if ok else ("could not be installed" if what == "install"
                                                        else "could not be removed")))
        if not ok and r is not None:
            lines = (r.stderr or r.stdout or "").strip().splitlines()
            if lines:
                n.set_body(lines[-1])
        self.get_application().send_notification(None, n)
        self.refresh_view()
        return False


class StoreApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="os.nova.Store")

    def do_activate(self):
        win = self.get_active_window()
        if not win:
            prov = Gtk.CssProvider()
            prov.load_from_data(CSS)
            Gtk.StyleContext.add_provider_for_screen(Gtk.Window().get_screen(), prov,
                                                     Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            dark = run("kreadconfig5", "--file", "kdeglobals", "--group", "General", "--key", "ColorScheme")
            if not dark or "Light" not in (dark.stdout or ""):
                s = Gtk.Settings.get_default()
                s.set_property("gtk-application-prefer-dark-theme", True)
                if os.path.isdir("/usr/share/themes/Breeze-Dark/gtk-3.0"):
                    s.set_property("gtk-theme-name", "Breeze-Dark")
            win = StoreWindow(self)
        win.show_all()
        win.back.set_visible(False)
        win.present()


if __name__ == "__main__":
    sys.exit(StoreApp().run(sys.argv))
