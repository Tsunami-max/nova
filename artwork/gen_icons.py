#!/usr/bin/env python3
"""Generate the original NovaOS logo and icon theme as SVG files.

Output:
  <out>/usr/share/icons/NovaOS/scalable/{apps,places}/*.svg
  <out>/usr/share/icons/NovaOS-Dark  (same art, inherits Papirus-Dark)
  <out>/usr/share/novaos/logo/*.svg
"""
import math
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "rootfs"
ICON_ROOT = os.path.join(OUT, "usr/share/icons")
LOGO_DIR = os.path.join(OUT, "usr/share/novaos/logo")

# ---------------------------------------------------------------------------
# Logo
# ---------------------------------------------------------------------------
STAR = ("M64 6 C67.5 44 76 56.5 112 64 C76 71.5 67.5 84 64 122 "
        "C60.5 84 52 71.5 16 64 C52 56.5 60.5 44 64 6 Z")
TWINKLE = ("M100 14 C101 23 103 25 112 26 C103 27 101 29 100 38 "
           "C99 29 97 27 88 26 C97 25 99 23 100 14 Z")

GRAD_DEFS = """
  <linearGradient id="novaStar" x1="20" y1="10" x2="108" y2="118" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#5ee7ff"/>
    <stop offset="0.45" stop-color="#6d7bff"/>
    <stop offset="1" stop-color="#b44dff"/>
  </linearGradient>
  <linearGradient id="novaOrbit" x1="10" y1="64" x2="118" y2="64" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#7ee8ff"/>
    <stop offset="1" stop-color="#d07bff"/>
  </linearGradient>"""


def logo_mark(defs_prefix=""):
    """Star + orbit, sized for a 128x128 canvas."""
    orbit = 'transform="rotate(-24 64 64)"'
    return f"""
  <g {orbit}>
    <path d="M10 64 A54 17 0 0 1 118 64" fill="none" stroke="url(#novaOrbit)" stroke-width="4.5" stroke-linecap="round" opacity="0.55"/>
  </g>
  <path d="{STAR}" fill="url(#novaStar)"/>
  <path d="{STAR}" fill="#fff" opacity="0.18" transform="translate(64 64) scale(0.42) translate(-64 -64)"/>
  <g {orbit}>
    <path d="M118 64 A54 17 0 0 1 10 64" fill="none" stroke="url(#novaOrbit)" stroke-width="4.5" stroke-linecap="round"/>
  </g>
  <path d="{TWINKLE}" fill="#ffffff" opacity="0.9"/>"""


def svg(body, defs="", size=128):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 128 128">\n<defs>{defs}\n</defs>{body}\n</svg>\n')


# ---------------------------------------------------------------------------
# App tile template (rounded "squircle" tile + white glyph)
# ---------------------------------------------------------------------------
TILE = ("M64 8 C104 8 120 24 120 64 C120 104 104 120 64 120 "
        "C24 120 8 104 8 64 C8 24 24 8 64 8 Z")


def tile(name, c1, c2, glyph, extra_defs=""):
    defs = f"""
  <linearGradient id="bg" x1="64" y1="8" x2="64" y2="120" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/>
  </linearGradient>
  <linearGradient id="gloss" x1="64" y1="8" x2="64" y2="70" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#fff" stop-opacity="0.28"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </linearGradient>{extra_defs}"""
    body = f"""
  <path d="{TILE}" fill="#000" opacity="0.22" transform="translate(0 3)"/>
  <path d="{TILE}" fill="url(#bg)"/>
  <path d="{TILE}" fill="url(#gloss)"/>
  <path d="{TILE}" fill="none" stroke="#fff" stroke-opacity="0.18" stroke-width="1.5"/>
{glyph}"""
    return name, svg(body, defs)


def gear_path(cx, cy, r_out, r_in, teeth, hole):
    pts = []
    n = teeth * 4
    for i in range(n):
        a = 2 * math.pi * i / n - math.pi / 2
        r = r_out if (i % 4) in (0, 1) else r_in
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d = "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in pts) + " Z"
    d += (f" M{cx + hole} {cy} A{hole} {hole} 0 1 0 {cx - hole} {cy} "
          f"A{hole} {hole} 0 1 0 {cx + hole} {cy} Z")
    return d


W = 'fill="#ffffff"'
SH = '<g transform="translate(0 2)" opacity="0.18">{}</g>'  # glyph shadow helper


def with_shadow(g):
    return SH.format(g.replace('fill="#ffffff"', 'fill="#000"')) + g


GLYPHS = {}

GLYPHS["files"] = with_shadow(f"""
  <path {W} opacity="0.75" d="M34 38 h22 l7 8 h31 a6 6 0 0 1 6 6 v6 H28 v-14 a6 6 0 0 1 6 -6z"/>
  <rect {W} x="28" y="52" width="72" height="42" rx="7"/>""")

GLYPHS["settings"] = with_shadow(
    f'<path {W} fill-rule="evenodd" d="{gear_path(64, 64, 36, 28, 8, 12)}"/>')

GLYPHS["toggles"] = with_shadow(f"""
  <rect {W} x="30" y="40" width="68" height="20" rx="10" opacity="0.65"/>
  <circle {W} cx="86" cy="50" r="13"/>
  <rect {W} x="30" y="70" width="68" height="20" rx="10" opacity="0.65"/>
  <circle {W} cx="42" cy="80" r="13"/>""")

GLYPHS["browser"] = with_shadow(f"""
  <circle cx="64" cy="64" r="33" fill="none" stroke="#ffffff" stroke-width="6"/>
  <path {W} d="M80 48 L69 69 L48 80 L59 59 Z"/>
  <circle cx="64" cy="64" r="4.5" fill="#000" opacity="0.25"/>""")

GLYPHS["notes"] = with_shadow(f"""
  <rect {W} x="34" y="28" width="56" height="72" rx="8"/>
  <rect x="43" y="44" width="38" height="5" rx="2.5" fill="#c97a00"/>
  <rect x="43" y="57" width="38" height="5" rx="2.5" fill="#c97a00" opacity="0.7"/>
  <rect x="43" y="70" width="26" height="5" rx="2.5" fill="#c97a00" opacity="0.7"/>
  <path {W} d="M96 52 l8 8 l-26 26 l-11 3 l3 -11 z" stroke="#c97a00" stroke-width="3" stroke-linejoin="round"/>""")

GLYPHS["calculator"] = with_shadow(f"""
  <rect {W} x="36" y="26" width="56" height="76" rx="9"/>
  <rect x="43" y="33" width="42" height="17" rx="4" fill="#9a3412" opacity="0.85"/>
  """ + "".join(
    f'<rect x="{43 + c * 15}" y="{57 + r * 14}" width="11" height="10" rx="3" '
    f'fill="{"#ea580c" if c == 2 else "#64748b"}"/>'
    for r in range(3) for c in range(3)))

GLYPHS["terminal"] = with_shadow(f"""
  <path d="M38 48 L56 64 L38 80" fill="none" stroke="#ffffff" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
  <rect x="62" y="76" width="30" height="8" rx="4" fill="#5eead4"/>""")

GLYPHS["images"] = with_shadow(f"""
  <rect {W} x="26" y="34" width="76" height="60" rx="9"/>
  <path d="M32 88 L54 62 L68 78 L78 68 L96 88 Z" fill="#db2777"/>
  <circle cx="82" cy="50" r="7" fill="#f59e0b"/>""")

GLYPHS["wallpapers"] = with_shadow(f"""
  <rect {W} opacity="0.55" x="32" y="30" width="62" height="48" rx="8" transform="rotate(-10 63 54)"/>
  <rect {W} x="34" y="46" width="64" height="50" rx="8"/>
  <path d="M40 90 L58 68 L70 80 L78 72 L92 90 Z" fill="#7c3aed"/>
  <circle cx="82" cy="60" r="6" fill="#38bdf8"/>""")

GLYPHS["launcher"] = with_shadow("".join(
    f'<rect {W} x="{32 + c * 23}" y="{32 + r * 23}" width="18" height="18" rx="6" '
    f'opacity="{1 if (r + c) % 2 == 0 else 0.7}"/>' for r in range(3) for c in range(3)))

GLYPHS["search"] = with_shadow(f"""
  <circle cx="58" cy="58" r="22" fill="none" stroke="#ffffff" stroke-width="8"/>
  <path d="M74 74 L94 94" stroke="#ffffff" stroke-width="10" stroke-linecap="round"/>""")

GLYPHS["installer"] = with_shadow(f"""
  <path d="M64 28 V70" stroke="#ffffff" stroke-width="9" stroke-linecap="round"/>
  <path d="M46 54 L64 72 L82 54" fill="none" stroke="#ffffff" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>
  <rect {W} x="30" y="80" width="68" height="20" rx="7"/>
  <circle cx="86" cy="90" r="3.5" fill="#047857"/>""")

GLYPHS["texteditor"] = with_shadow(f"""
  <path {W} d="M38 26 h36 l18 18 v50 a8 8 0 0 1 -8 8 h-46 a8 8 0 0 1 -8 -8 v-60 a8 8 0 0 1 8 -8z"/>
  <path d="M74 26 v14 a4 4 0 0 0 4 4 h14" fill="#cbd5e1"/>
  <rect x="42" y="56" width="40" height="5" rx="2.5" fill="#475569"/>
  <rect x="42" y="68" width="40" height="5" rx="2.5" fill="#475569" opacity="0.7"/>
  <rect x="42" y="80" width="26" height="5" rx="2.5" fill="#475569" opacity="0.7"/>""")

GLYPHS["taskmanager"] = with_shadow(f"""
  <path d="M24 68 H44 L52 48 L64 86 L74 58 L80 68 H104" fill="none" stroke="#ffffff" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>""")

GLYPHS["screenshot"] = with_shadow(f"""
  <path d="M32 50 V38 a6 6 0 0 1 6 -6 h12 M78 32 h12 a6 6 0 0 1 6 6 v12 M96 78 v12 a6 6 0 0 1 -6 6 h-12 M50 96 h-12 a6 6 0 0 1 -6 -6 v-12"
        fill="none" stroke="#ffffff" stroke-width="7" stroke-linecap="round"/>
  <circle {W} cx="64" cy="64" r="12"/>""")

GLYPHS["sound"] = with_shadow(f"""
  <path {W} d="M30 54 h14 l20 -16 v52 l-20 -16 h-14 z"/>
  <path d="M74 50 a18 18 0 0 1 0 28" fill="none" stroke="#ffffff" stroke-width="7" stroke-linecap="round"/>
  <path d="M84 40 a32 32 0 0 1 0 48" fill="none" stroke="#ffffff" stroke-width="7" stroke-linecap="round" opacity="0.7"/>""")

GLYPHS["network"] = with_shadow(f"""
  <path d="M28 54 a52 52 0 0 1 72 0" fill="none" stroke="#ffffff" stroke-width="8" stroke-linecap="round" opacity="0.6"/>
  <path d="M40 67 a35 35 0 0 1 48 0" fill="none" stroke="#ffffff" stroke-width="8" stroke-linecap="round" opacity="0.8"/>
  <path d="M52 80 a17 17 0 0 1 24 0" fill="none" stroke="#ffffff" stroke-width="8" stroke-linecap="round"/>
  <circle {W} cx="64" cy="92" r="6"/>""")

GLYPHS["about"] = with_shadow(f"""
  <circle {W} cx="64" cy="40" r="8"/>
  <rect {W} x="56" y="56" width="16" height="42" rx="8"/>""")

GLYPHS["keyboard"] = with_shadow(f"""
  <rect {W} x="22" y="40" width="84" height="50" rx="9"/>
  """ + "".join(f'<rect x="{30 + c * 12}" y="{48 + r * 12}" width="8" height="8" rx="2" fill="#334155"/>'
                for r in range(2) for c in range(6)) +
    '<rect x="42" y="74" width="44" height="8" rx="3" fill="#334155"/>')

GLYPHS["display"] = with_shadow(f"""
  <rect {W} x="24" y="30" width="80" height="54" rx="8"/>
  <rect x="30" y="36" width="68" height="42" rx="4" fill="#0e7490" opacity="0.85"/>
  <rect {W} x="56" y="84" width="16" height="10"/>
  <rect {W} x="44" y="92" width="40" height="6" rx="3"/>""")

# app id -> (gradient top, gradient bottom, glyph)
APPS = {
    "novaos-files":       ("#4f9dff", "#2457e6", "files"),
    "novaos-settings":    ("#7b8798", "#3a4354", "settings"),
    "novaos-allsettings": ("#8b95a7", "#4b5567", "toggles"),
    "novaos-browser":     ("#36d1c4", "#1e6fd9", "browser"),
    "novaos-notes":       ("#ffd45c", "#f59e0b", "notes"),
    "novaos-calculator":  ("#fb9a4b", "#e2541b", "calculator"),
    "novaos-terminal":    ("#2b3448", "#0b1020", "terminal"),
    "novaos-images":      ("#ff6fb5", "#9b4dff", "images"),
    "novaos-wallpapers":  ("#a78bfa", "#5b4cf0", "wallpapers"),
    "novaos-launcher":    ("#6d7bff", "#4338ca", "launcher"),
    "novaos-search":      ("#60a5fa", "#4f46e5", "search"),
    "novaos-installer":   ("#34d399", "#0f9f7a", "installer"),
    "novaos-texteditor":  ("#94a3b8", "#475569", "texteditor"),
    "novaos-taskmanager": ("#fb7185", "#e11d48", "taskmanager"),
    "novaos-screenshot":  ("#22d3ee", "#0e7490", "screenshot"),
    "novaos-sound":       ("#c084fc", "#7e22ce", "sound"),
    "novaos-network":     ("#38bdf8", "#1d4ed8", "network"),
    "novaos-about":       ("#6d7bff", "#3b2fc9", "about"),
    "novaos-keyboard":    ("#94a3b8", "#334155", "keyboard"),
    "novaos-display":     ("#22d3ee", "#155e75", "display"),
}

# Icon names used by the stock applications -> our artwork.
ALIASES = {
    "novaos-files": ["org.xfce.filemanager", "org.xfce.thunar", "thunar", "system-file-manager", "file-manager"],
    "novaos-settings": ["preferences-system", "preferences-desktop"],
    "novaos-allsettings": ["org.xfce.settings.manager", "org.xfce.settings.appearance", "xfce4-settings-manager"],
    "novaos-browser": ["org.xfce.webbrowser", "org.gnome.Epiphany", "web-browser", "internet-web-browser", "epiphany"],
    "novaos-notes": ["accessories-notes"],
    "novaos-calculator": ["org.gnome.Calculator", "accessories-calculator", "gnome-calculator"],
    "novaos-terminal": ["org.xfce.terminalemulator", "org.xfce.terminal", "utilities-terminal", "xfce4-terminal", "terminal"],
    "novaos-images": ["org.xfce.ristretto", "ristretto", "image-viewer", "eog"],
    "novaos-launcher": ["org.xfce.appfinder", "xfce4-appfinder", "application-launcher"],
    "novaos-installer": ["calamares", "system-software-install", "ubiquity"],
    "novaos-texteditor": ["org.xfce.mousepad", "mousepad", "accessories-text-editor", "text-editor"],
    "novaos-taskmanager": ["org.xfce.taskmanager", "xfce4-taskmanager", "utilities-system-monitor"],
    "novaos-screenshot": ["org.xfce.screenshooter", "applets-screenshooter", "accessories-screenshot"],
    "novaos-sound": ["multimedia-volume-control", "pavucontrol", "org.pulseaudio.pavucontrol"],
    "novaos-network": ["nm-device-wired", "preferences-system-network"],
    "novaos-keyboard": ["org.xfce.settings.keyboard", "preferences-desktop-keyboard"],
    "novaos-display": ["org.xfce.settings.display", "preferences-desktop-display"],
}

# ---------------------------------------------------------------------------
# Folder / place icons
# ---------------------------------------------------------------------------
FOLDER_DEFS = """
  <linearGradient id="fback" x1="64" y1="20" x2="64" y2="60" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#5a62e8"/><stop offset="1" stop-color="#3f45c9"/>
  </linearGradient>
  <linearGradient id="ffront" x1="64" y1="40" x2="64" y2="112" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#8fa0ff"/><stop offset="1" stop-color="#5d63f0"/>
  </linearGradient>"""


def folder(emblem="", open_=False):
    front = ("M10 52 a8 8 0 0 1 8 -8 h92 a8 8 0 0 1 8 8 l-4 50 a8 8 0 0 1 -8 7 h-84 a8 8 0 0 1 -8 -7 z"
             if not open_ else
             "M18 54 a8 8 0 0 1 8 -7 h90 a6 6 0 0 1 6 7 l-8 48 a8 8 0 0 1 -8 7 h-84 a8 8 0 0 1 -8 -7 z")
    body = f"""
  <path d="M14 30 a8 8 0 0 1 8 -8 h28 l10 10 h46 a8 8 0 0 1 8 8 v60 H14 z" fill="url(#fback)"/>
  <rect x="20" y="36" width="88" height="40" rx="4" fill="#fff" opacity="0.9"/>
  <path d="{front}" fill="#000" opacity="0.15" transform="translate(0 2)"/>
  <path d="{front}" fill="url(#ffront)"/>
  <path d="M14 47 h100" stroke="#fff" stroke-opacity="0.35" stroke-width="1.5" transform="translate(0 {0 if not open_ else 2})"/>
  <g fill="#ffffff" opacity="0.92">{emblem}</g>"""
    return svg(body, FOLDER_DEFS)


EMBLEMS = {
    "folder": "",
    "folder-documents": '<rect x="54" y="62" width="20" height="26" rx="3"/><rect x="58" y="68" width="12" height="2.5" fill="#5d63f0"/><rect x="58" y="74" width="12" height="2.5" fill="#5d63f0"/>',
    "folder-download": '<path d="M64 60 v20" stroke="#fff" stroke-width="6" stroke-linecap="round"/><path d="M55 74 l9 9 l9 -9" fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/><rect x="50" y="88" width="28" height="4" rx="2"/>',
    "folder-pictures": '<rect x="50" y="62" width="28" height="24" rx="4"/><path d="M53 83 l8 -9 l5 5 l4 -4 l6 8 z" fill="#5d63f0"/>',
    "folder-music": '<path d="M58 66 l18 -4 v20" fill="none" stroke="#fff" stroke-width="4"/><circle cx="56" cy="84" r="5"/><circle cx="73" cy="82" r="5"/>',
    "folder-videos": '<path d="M58 62 l18 12 l-18 12 z"/>',
    "folder-desktop": '<rect x="48" y="62" width="32" height="20" rx="3"/><rect x="58" y="84" width="12" height="4" rx="2"/>',
    "folder-templates": '<rect x="54" y="62" width="20" height="26" rx="3" fill="none" stroke="#fff" stroke-width="3" stroke-dasharray="4 3"/>',
    "folder-publicshare": '<circle cx="64" cy="68" r="6"/><path d="M52 88 a12 10 0 0 1 24 0 z"/>',
    "user-home": '<path d="M64 60 l16 13 h-5 v15 h-8 v-9 h-6 v9 h-8 v-15 h-5 z"/>',
    "folder-remote": '<circle cx="64" cy="74" r="12" fill="none" stroke="#fff" stroke-width="3"/><path d="M52 74 h24 M64 62 v24" stroke="#fff" stroke-width="2.5"/>',
}
PLACE_ALIASES = {
    "folder": ["inode-directory", "folder-new", "gtk-directory", "stock_folder"],
    "folder-documents": ["folder-document"],
    "folder-download": ["folder-downloads"],
    "folder-pictures": ["folder-images"],
    "user-home": ["folder-home", "gnome-fs-home"],
    "folder-desktop": ["user-desktop"],
    "folder-remote": ["folder-network", "network-workgroup"],
}


def trash(full=False):
    defs = """
  <linearGradient id="tb" x1="64" y1="30" x2="64" y2="116" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#cfd7e6"/><stop offset="1" stop-color="#8592aa"/>
  </linearGradient>"""
    paper = ('<path d="M44 32 l14 -14 l18 6 l-6 18 z" fill="#ffffff"/>'
             '<path d="M66 30 l18 -10 l10 16 l-16 8 z" fill="#fde68a"/>') if full else ""
    body = f"""
  <path d="M30 40 h68 l-6 68 a8 8 0 0 1 -8 7 h-40 a8 8 0 0 1 -8 -7 z" fill="#000" opacity="0.18" transform="translate(0 3)"/>
  {paper}
  <path d="M30 40 h68 l-6 68 a8 8 0 0 1 -8 7 h-40 a8 8 0 0 1 -8 -7 z" fill="url(#tb)"/>
  <path d="M48 54 l2 48 M64 54 v48 M80 54 l-2 48" stroke="#5b6680" stroke-width="4" stroke-linecap="round" opacity="0.6"/>
  <rect x="24" y="30" width="80" height="12" rx="6" fill="#e5eaf3"/>
  <rect x="52" y="22" width="24" height="10" rx="4" fill="#e5eaf3"/>"""
    return svg(body, defs)


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def link(target, path):
    if os.path.lexists(path):
        os.remove(path)
    os.symlink(target, path)


def main():
    base = os.path.join(ICON_ROOT, "NovaOS", "scalable")
    apps_dir, places_dir = os.path.join(base, "apps"), os.path.join(base, "places")

    # Logo + start button
    logo = svg(logo_mark(), GRAD_DEFS)
    badge = svg(f"""
  <path d="{TILE}" fill="#000" opacity="0.25" transform="translate(0 3)"/>
  <path d="{TILE}" fill="#10142a"/>
  <g transform="translate(64 64) scale(0.78) translate(-64 -64)">{logo_mark()}</g>""", GRAD_DEFS)
    write(os.path.join(LOGO_DIR, "novaos-logo.svg"), logo)
    write(os.path.join(LOGO_DIR, "novaos-badge.svg"), badge)
    for n in ("novaos", "novaos-logo", "distributor-logo", "start-here", "novaos-start",
              "distributor-logo-novaos", "org.xfce.panel.whiskermenu", "xfce4-whiskermenu"):
        write(os.path.join(apps_dir, n + ".svg"), logo)
    write(os.path.join(apps_dir, "novaos-badge.svg"), badge)
    # Symbolic-ish monochrome start glyph (used in light panel mode)
    write(os.path.join(apps_dir, "novaos-start-mono.svg"),
          svg(f'<path d="{STAR}" fill="#4338ca"/><path d="{TWINKLE}" fill="#6d7bff"/>'))

    for app, (c1, c2, g) in APPS.items():
        _, content = tile(app, c1, c2, GLYPHS[g])
        write(os.path.join(apps_dir, app + ".svg"), content)
        for alias in ALIASES.get(app, []):
            link(app + ".svg", os.path.join(apps_dir, alias + ".svg"))

    for name, emb in EMBLEMS.items():
        write(os.path.join(places_dir, name + ".svg"), folder(emb))
        for alias in PLACE_ALIASES.get(name, []):
            link(name + ".svg", os.path.join(places_dir, alias + ".svg"))
    write(os.path.join(places_dir, "folder-open.svg"), folder("", open_=True))
    link("folder-open.svg", os.path.join(places_dir, "folder-drag-accept.svg"))
    write(os.path.join(places_dir, "user-trash.svg"), trash(False))
    write(os.path.join(places_dir, "user-trash-full.svg"), trash(True))
    link("user-trash.svg", os.path.join(places_dir, "trashcan_empty.svg"))
    link("user-trash-full.svg", os.path.join(places_dir, "trashcan_full.svg"))

    for theme, inherits in (("NovaOS", "Papirus,Adwaita,hicolor"),
                            ("NovaOS-Dark", "Papirus-Dark,Adwaita,hicolor")):
        tdir = os.path.join(ICON_ROOT, theme)
        os.makedirs(tdir, exist_ok=True)
        if theme != "NovaOS":
            link("../NovaOS/scalable", os.path.join(tdir, "scalable"))
        write(os.path.join(tdir, "index.theme"), f"""[Icon Theme]
Name={theme}
Comment=Original NovaOS icons (apps, places); everything else from Papirus
Inherits={inherits}
Example=folder
Directories=scalable/apps,scalable/places

[scalable/apps]
Size=128
MinSize=8
MaxSize=512
Context=Applications
Type=Scalable

[scalable/places]
Size=128
MinSize=8
MaxSize=512
Context=Places
Type=Scalable
""")
    print("icons written to", ICON_ROOT)


if __name__ == "__main__":
    main()
