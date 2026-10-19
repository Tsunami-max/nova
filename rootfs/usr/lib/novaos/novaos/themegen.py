"""Generate the NovaOS GTK + xfwm4 themes.

The GTK part is derived from the Materia theme (GPL-2.0) by recolouring its
accent and surface colours and appending NovaOS-specific CSS for the panel,
Start menu and desktop.  The window decorations (xfwm4) are drawn from
scratch here.
"""
import os
import re
import shutil

from . import palette as P

BASES = {"dark": "Materia-dark-compact", "light": "Materia-light-compact"}
MATERIA_ACCENT = {"dark": ("#8ab4f8", (138, 180, 248)), "light": ("#1967d2", (25, 103, 210))}
THEME_NAMES = {"dark": "NovaOS-Dark", "light": "NovaOS-Light"}


def _recolor(text, mode, accent):
    acc = P.accent_for_mode(accent, mode)
    r, g, b = P.hex_to_rgb(acc)
    src_hex, (sr, sg, sb) = MATERIA_ACCENT[mode]
    text = re.sub(re.escape(src_hex), acc, text, flags=re.I)
    text = text.replace(f"rgba({sr}, {sg}, {sb},", f"rgba({r}, {g}, {b},")
    if mode == "light":
        # The light theme uses the dark accent in a few dark-on-light spots.
        text = re.sub("#8ab4f8", P.accent_for_mode(accent, "dark"), text, flags=re.I)
        text = text.replace("rgba(138, 180, 248,", "rgba(%d, %d, %d," % P.hex_to_rgb(
            P.accent_for_mode(accent, "dark")))
    surfaces = P.DARK_SURFACES if mode == "dark" else P.LIGHT_SURFACES
    for old, new in surfaces.items():
        text = re.sub(re.escape(old) + r"\b", new, text, flags=re.I)
    return text


def nova_css(mode, accent):
    c = P.CHROME[mode]
    acc = P.accent_for_mode(accent, mode)
    ar, ag, ab = P.hex_to_rgb(acc)
    return f"""
/* ==================== NovaOS desktop additions ==================== */
* {{ -gtk-outline-radius: 6px; }}

/* ---- Taskbar ---- */
.xfce4-panel {{ font-family: "Inter"; }}
.xfce4-panel button {{
	border-radius: 6px;
	border: none;
	box-shadow: none;
	background-image: none;
	min-height: 0;
	padding: 2px 6px;
	margin: 3px 1px;
	transition: background-color 120ms ease-out, box-shadow 160ms ease-out;
}}
.xfce4-panel button:hover {{ background-color: {c['hover']}; }}
.xfce4-panel button:active {{ background-color: rgba({ar}, {ag}, {ab}, 0.20); }}
.xfce4-panel button:checked {{
	background-color: rgba({ar}, {ag}, {ab}, 0.16);
	box-shadow: inset 0 -3px 0 0 {acc};
}}
.xfce4-panel button:checked:hover {{ background-color: rgba({ar}, {ag}, {ab}, 0.24); }}
.xfce4-panel label {{ color: {c['fg']}; }}
.xfce4-panel separator {{ background: transparent; }}

/* Start button */
#whiskermenu-button {{ padding: 2px 10px; margin: 3px 4px 3px 4px; }}
#whiskermenu-button:checked {{ box-shadow: none; background-color: rgba({ar}, {ag}, {ab}, 0.28); }}

/* Clock: two-line, Windows-style */
#clock-button label {{ font-size: 9.5pt; }}

/* ---- Start menu ---- */
#whiskermenu-window {{
	background-color: {c['menu_bg']};
	border: 1px solid {c['border']};
	border-radius: 12px;
	padding: 6px;
}}
#whiskermenu-window entry {{
	border-radius: 18px;
	min-height: 34px;
	padding-left: 12px;
	background-color: {c['card']};
	border: 1px solid {c['border']};
	box-shadow: none;
}}
#whiskermenu-window entry:focus {{ border-color: {acc}; }}
#whiskermenu-window button {{ border-radius: 8px; }}
#whiskermenu-window treeview, #whiskermenu-window iconview,
#whiskermenu-window scrolledwindow, #whiskermenu-window viewport {{ background-color: transparent; }}
#whiskermenu-window iconview:selected, #whiskermenu-window treeview:selected {{
	background-color: rgba({ar}, {ag}, {ab}, 0.22);
	color: {c['fg']};
	border-radius: 8px;
}}
#whiskermenu-window iconview {{ padding: 6px; }}
#whiskermenu-window .category-button {{ padding: 6px 10px; border-radius: 8px; }}
#whiskermenu-window .category-button:checked {{ background-color: rgba({ar}, {ag}, {ab}, 0.18); }}

/* ---- Desktop icons ---- */
XfdesktopIconView.view {{ background-color: transparent; color: {"#ffffff" if mode == "dark" else "#1d2333"}; }}
XfdesktopIconView.view.label {{ text-shadow: {"0 1px 3px rgba(0,0,0,0.85)" if mode == "dark" else "0 1px 2px rgba(255,255,255,0.9)"}; }}
XfdesktopIconView.view:active {{ background-color: rgba({ar}, {ag}, {ab}, 0.45); border-radius: 6px; }}
XfdesktopIconView.rubberband {{ background-color: rgba({ar}, {ag}, {ab}, 0.25); border: 1px solid {acc}; }}

/* ---- Notifications ---- */
#XfceNotifyWindow {{ border-radius: 12px; border: 1px solid {c['border']}; }}
#XfceNotifyWindow button {{ border-radius: 8px; }}

/* ---- Menus (including the desktop right-click menu) ---- */
menu, .menu, .context-menu {{ border-radius: 8px; padding: 4px; }}
menu menuitem, .menu menuitem {{ border-radius: 6px; padding: 6px 10px; }}
menu menuitem:hover {{ background-color: rgba({ar}, {ag}, {ab}, 0.20); }}
tooltip {{ border-radius: 6px; }}
"""


# ---------------------------------------------------------------------------
# xfwm4 window decorations: flat, Windows-10-like caption buttons
# ---------------------------------------------------------------------------
TB_H = 34
BTN_W = 46


_K = 1.0  # window-decoration scale (1 = normal, 2 = high-DPI)


def _svg(w, h, body):
    sw, sh = max(1, round(w * _K)), max(1, round(h * _K))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{sw}" height="{sh}" '
            f'viewBox="0 0 {w} {h}">{body}</svg>\n')


def _glyph(kind, color):
    cx, cy = BTN_W / 2, TB_H / 2
    s = f'stroke="{color}" stroke-width="1.2" fill="none" stroke-linecap="square"'
    if kind == "hide":
        return f'<path d="M{cx - 5} {cy + 0.5} H{cx + 5}" {s}/>'
    if kind == "maximize":
        return f'<rect x="{cx - 5}" y="{cy - 5}" width="10" height="10" {s}/>'
    if kind == "maximize-toggled":
        return (f'<rect x="{cx - 5}" y="{cy - 3}" width="8" height="8" {s}/>'
                f'<path d="M{cx - 3} {cy - 3} V{cy - 5} H{cx + 5} V{cy + 3} H{cx + 3}" {s}/>')
    if kind == "close":
        return f'<path d="M{cx - 5} {cy - 5} L{cx + 5} {cy + 5} M{cx + 5} {cy - 5} L{cx - 5} {cy + 5}" {s}/>'
    if kind == "menu":
        return f'<circle cx="{cx}" cy="{cy}" r="3" fill="{color}"/>'
    if kind in ("shade", "stick"):
        return f'<circle cx="{cx}" cy="{cy}" r="2.5" fill="{color}"/>'
    return f'<circle cx="{cx}" cy="{cy}" r="2.5" stroke="{color}" fill="none"/>'


def write_xfwm4_scaled(dest, mode, scale):
    """Window decorations drawn larger for high-DPI screens."""
    global _K
    _K = scale
    try:
        write_xfwm4(dest, mode)
    finally:
        _K = 1.0


def write_xfwm4(dest, mode):
    c = P.CHROME[mode]
    d = os.path.join(dest, "xfwm4")
    os.makedirs(d, exist_ok=True)
    hover = "#ffffff" if mode == "dark" else "#000000"
    for state in ("active", "inactive"):
        bg = c["title_active"] if state == "active" else c["title_inactive"]
        fg = c["title_text"] if state == "active" else c["title_text_inactive"]
        border = c["border"]
        files = {
            f"title-1-{state}": _svg(2, TB_H, f'<rect width="2" height="{TB_H}" fill="{bg}"/>'),
            f"top-left-{state}": _svg(1, TB_H, f'<rect width="1" height="{TB_H}" fill="{border}"/>'),
            f"top-right-{state}": _svg(1, TB_H, f'<rect width="1" height="{TB_H}" fill="{border}"/>'),
            f"left-{state}": _svg(1, 2, f'<rect width="1" height="2" fill="{border}"/>'),
            f"right-{state}": _svg(1, 2, f'<rect width="1" height="2" fill="{border}"/>'),
            f"bottom-{state}": _svg(2, 1, f'<rect width="2" height="1" fill="{border}"/>'),
            f"bottom-left-{state}": _svg(1, 1, f'<rect width="1" height="1" fill="{border}"/>'),
            f"bottom-right-{state}": _svg(1, 1, f'<rect width="1" height="1" fill="{border}"/>'),
        }
        for i in range(2, 6):
            files[f"title-{i}-{state}"] = files[f"title-1-{state}"]
        for k, v in files.items():
            with open(os.path.join(d, k + ".svg"), "w") as f:
                f.write(v)
        for kind in ("hide", "maximize", "maximize-toggled", "close", "menu", "shade",
                     "shade-toggled", "stick", "stick-toggled"):
            g = kind.replace("-toggled", "") if kind.startswith(("shade", "stick")) else kind
            variants = {state: (bg, fg)}
            if state == "active":
                if kind == "close":
                    variants["prelight"] = ("#e81123", "#ffffff")
                    variants["pressed"] = ("#b40f1c", "#ffffff")
                else:
                    variants["prelight"] = (None, c["title_text"])
                    variants["pressed"] = (None, c["title_text"])
            for vname, (vbg, vfg) in variants.items():
                bgrect = f'<rect width="{BTN_W}" height="{TB_H}" fill="{bg}"/>'
                if vbg:
                    bgrect += f'<rect width="{BTN_W}" height="{TB_H}" fill="{vbg}"/>'
                elif vname in ("prelight", "pressed"):
                    op = 0.08 if vname == "prelight" else 0.14
                    bgrect += f'<rect width="{BTN_W}" height="{TB_H}" fill="{hover}" fill-opacity="{op}"/>'
                with open(os.path.join(d, f"{kind}-{vname}.svg"), "w") as f:
                    f.write(_svg(BTN_W, TB_H, bgrect + _glyph(g, vfg)))
    with open(os.path.join(d, "themerc"), "w") as f:
        f.write(f"""# NovaOS window decorations
active_text_color={c['title_text']}
inactive_text_color={c['title_text_inactive']}
title_shadow_active=false
title_shadow_inactive=false
full_width_title=true
title_vertical_offset_active=0
title_vertical_offset_inactive=0
title_horizontal_offset=6
button_offset=0
button_spacing=0
show_app_icon=true
maximized_offset=0
shadow_delta_height=0
shadow_delta_width=0
shadow_delta_x=0
shadow_delta_y=-4
shadow_opacity=45
show_popup_shadow=true
""")


def generate(mode, accent, dest_root, name=None):
    """Create <dest_root>/<name> containing gtk-2.0/3.0/4.0 + xfwm4."""
    name = name or THEME_NAMES[mode]
    base = None
    for d in ("/usr/share/themes", os.path.expanduser("~/.local/share/themes")):
        if os.path.isdir(os.path.join(d, BASES[mode])):
            base = os.path.join(d, BASES[mode])
            break
    if base is None:
        raise RuntimeError("Base theme %s not found" % BASES[mode])
    dest = os.path.join(dest_root, name)
    tmp = dest + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    for sub in ("gtk-2.0", "gtk-3.0", "gtk-4.0"):
        src = os.path.join(base, sub)
        if not os.path.isdir(src):
            continue
        shutil.copytree(src, os.path.join(tmp, sub), symlinks=True)
        for root, _dirs, files in os.walk(os.path.join(tmp, sub)):
            for fn in files:
                if fn.endswith((".css", "gtkrc")):
                    p = os.path.join(root, fn)
                    if os.path.islink(p):
                        continue
                    with open(p) as f:
                        txt = _recolor(f.read(), mode, accent)
                    if fn == "gtk.css" and sub == "gtk-3.0":
                        txt += nova_css(mode, accent)
                    with open(p, "w") as f:
                        f.write(txt)
    write_xfwm4(tmp, mode)
    with open(os.path.join(tmp, "index.theme"), "w") as f:
        f.write(f"""[Desktop Entry]
Type=X-GNOME-Metatheme
Name={name}
Comment=NovaOS {mode} theme (accent {accent}); GTK styling derived from Materia
Encoding=UTF-8

[X-GNOME-Metatheme]
GtkTheme={name}
MetacityTheme={name}
IconTheme={"NovaOS-Dark" if mode == "dark" else "NovaOS"}
""")
    shutil.rmtree(dest, ignore_errors=True)
    os.rename(tmp, dest)
    return dest
