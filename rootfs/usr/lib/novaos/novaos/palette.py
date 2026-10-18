"""NovaOS colour system."""

DEFAULT_ACCENT = "#6c7bff"

ACCENTS = [
    ("Nova", "#6c7bff"),
    ("Blue", "#3b82f6"),
    ("Sky", "#0ea5e9"),
    ("Teal", "#14b8a6"),
    ("Green", "#22c55e"),
    ("Amber", "#f59e0b"),
    ("Orange", "#f97316"),
    ("Red", "#ef4444"),
    ("Pink", "#ec4899"),
    ("Violet", "#a855f7"),
    ("Graphite", "#8a93a6"),
]

# Surface colours that replace the neutral greys of the Materia base theme.
DARK_SURFACES = {
    "#050505": "#04060b",
    "#121212": "#0e1118",
    "#1e1e1e": "#161a24",
    "#212121": "#191d28",
    "#252525": "#1c2130",
    "#272727": "#1e2331",
    "#2e2e2e": "#242a3a",
    "#363636": "#2c3244",
    "#3f3f3f": "#343b4f",
}
LIGHT_SURFACES = {
    "#f9f9f9": "#f7f8fc",
    "#f0f0f0": "#eef0f6",
    "#ebebeb": "#e9ecf4",
    "#e0e0e0": "#dde1ec",
}

# Desktop chrome (panel, title bars) per mode.
CHROME = {
    "dark": {
        "panel_rgb": (0.075, 0.086, 0.122),
        "title_active": "#1e2331",
        "title_inactive": "#191d28",
        "title_text": "#e6e9f2",
        "title_text_inactive": "#7f879d",
        "border": "#2c3244",
        "fg": "#e6e9f2",
        "fg_dim": "#9aa3bb",
        "hover": "rgba(255,255,255,0.08)",
        "menu_bg": "rgba(22,26,36,0.94)",
        "card": "rgba(255,255,255,0.05)",
    },
    "light": {
        "panel_rgb": (0.957, 0.965, 0.984),
        "title_active": "#eceff6",
        "title_inactive": "#f5f6fa",
        "title_text": "#1d2333",
        "title_text_inactive": "#8a90a2",
        "border": "#d3d8e4",
        "fg": "#1d2333",
        "fg_dim": "#5b6378",
        "hover": "rgba(0,0,0,0.06)",
        "menu_bg": "rgba(247,248,252,0.95)",
        "card": "rgba(0,0,0,0.04)",
    },
}


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(c)))) for c in rgb)


def mix(a, b, t):
    ra, rb = hex_to_rgb(a), hex_to_rgb(b)
    return rgb_to_hex(tuple(x + (y - x) * t for x, y in zip(ra, rb)))


def accent_for_mode(accent, mode):
    """Dark backgrounds need a lighter accent, light ones a deeper accent."""
    return mix(accent, "#ffffff", 0.18) if mode == "dark" else mix(accent, "#000000", 0.08)
