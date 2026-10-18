#!/usr/bin/env python3
"""Render NovaOS boot artwork: GRUB theme, Plymouth splash, logo PNGs."""
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJ, "rootfs")
LOGO_SVG = os.path.join(ROOT, "usr/share/novaos/logo/novaos-logo.svg")
INTER = "/usr/share/fonts/opentype/inter"

GRUB_THEME = os.path.join(ROOT, "usr/share/grub/themes/novaos")
ISO_GRUB_THEME = os.path.join(PROJ, "boot/grub/themes/novaos")
PLY = os.path.join(ROOT, "usr/share/plymouth/themes/novaos")
LOGO_DIR = os.path.join(ROOT, "usr/share/novaos/logo")


def rsvg(svg_path, out, size):
    subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), svg_path, "-o", out], check=True)


def wordmark(out, height, color="#ffffff"):
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="560" height="140" viewBox="0 0 560 140">
<text x="280" y="104" text-anchor="middle" font-family="Inter" font-size="112" fill="{color}" letter-spacing="-2">
<tspan font-weight="700">Nova</tspan><tspan font-weight="300" fill-opacity="0.75">OS</tspan></text></svg>"""
    tmp = out + ".svg"
    with open(tmp, "w") as f:
        f.write(svg)
    subprocess.run(["rsvg-convert", "-h", str(height), tmp, "-o", out], check=True)
    os.remove(tmp)
    # trim transparent borders
    im = Image.open(out)
    im.crop(im.getbbox()).save(out)


def boot_background(path, w=1920, h=1080, with_logo=True):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    x /= w; y /= h
    top, bot = np.array([5, 7, 15]) / 255, np.array([11, 8, 30]) / 255
    rgb = top + (bot - top) * y[..., None]
    def blob(cx, cy, r, col, k):
        a = k * np.exp(-(((x - cx) / r) ** 2 + ((y - cy) / (r * 0.8)) ** 2))
        return np.array(col) / 255 * a[..., None]
    rgb = 1 - (1 - rgb) * (1 - blob(0.5, 0.35, 0.35, (70, 80, 220), 0.35))
    rgb = 1 - (1 - rgb) * (1 - blob(0.5, 1.05, 0.5, (120, 40, 200), 0.3))
    rgb += np.random.default_rng(1).normal(0, 0.006, rgb.shape)
    img = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    if with_logo:
        tmp = path + ".logo.png"
        rsvg(LOGO_SVG, tmp, 150)
        logo = Image.open(tmp).convert("RGBA")
        glow = logo.filter(ImageFilter.GaussianBlur(18))
        lx, ly = (w - 150) // 2, int(h * 0.20)
        img.alpha_composite(glow, (lx, ly))
        img.alpha_composite(logo, (lx, ly))
        wm = path + ".wm.png"
        wordmark(wm, 56)
        wmi = Image.open(wm).convert("RGBA")
        img.alpha_composite(wmi, ((w - wmi.width) // 2, ly + 170))
        os.remove(tmp); os.remove(wm)
    img.convert("RGB").save(path)


def nine_slice(dirpath, prefix, fill, r=10, outline=None):
    size = r * 2 + 4
    S = 4
    im = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, size * S - 1, size * S - 1], radius=r * S, fill=fill,
                        outline=outline, width=S * 2 if outline else 0)
    im = im.resize((size, size), Image.LANCZOS)
    c = r + 2
    parts = {"nw": (0, 0, r, r), "n": (r, 0, c, r), "ne": (c, 0, size, r),
             "w": (0, r, r, c), "c": (r, r, c, c), "e": (c, r, size, c),
             "sw": (0, c, r, size), "s": (r, c, c, size), "se": (c, c, size, size)}
    for k, box in parts.items():
        im.crop(box).save(os.path.join(dirpath, f"{prefix}_{k}.png"))


def grub_theme():
    for d in (GRUB_THEME, ISO_GRUB_THEME):
        os.makedirs(d, exist_ok=True)
        boot_background(os.path.join(d, "background.png"))
        nine_slice(d, "select", (109, 123, 255, 90), outline=(150, 160, 255, 200))
        for size, weight in ((16, "Regular"), (20, "Regular"), (14, "Regular")):
            subprocess.run(["grub-mkfont", "-s", str(size), "-n", f"Inter {weight}",
                            "-o", os.path.join(d, f"inter-{weight.lower()}-{size}.pf2"),
                            os.path.join(INTER, f"Inter-{weight}.otf")], check=True)
        with open(os.path.join(d, "theme.txt"), "w") as f:
            f.write("""# NovaOS GRUB theme
title-text: ""
desktop-image: "background.png"
desktop-image-scale-method: "crop"
desktop-color: "#07090f"
terminal-font: "Inter Regular 16"
terminal-box: "select_*.png"

+ boot_menu {
	left = 50%-300
	top = 56%
	width = 600
	height = 250
	item_font = "Inter Regular 20"
	item_color = "#9aa3c7"
	selected_item_color = "#ffffff"
	selected_item_font = "Inter Regular 20"
	item_height = 44
	item_padding = 18
	item_spacing = 6
	icon_width = 0
	icon_height = 0
	item_icon_space = 0
	selected_item_pixmap_style = "select_*.png"
	scrollbar = false
}

+ label {
	left = 0
	top = 100%-56
	width = 100%
	align = "center"
	id = "__timeout__"
	text = "Starting NovaOS in %d seconds"
	color = "#6b7399"
	font = "Inter Regular 16"
}

+ label {
	left = 0
	top = 100%-32
	width = 100%
	align = "center"
	text = "Use the arrow keys to choose, Enter to boot, E to edit"
	color = "#444b6b"
	font = "Inter Regular 14"
}
""")


def plymouth():
    os.makedirs(PLY, exist_ok=True)
    rsvg(LOGO_SVG, os.path.join(PLY, "logo.png"), 128)
    wordmark(os.path.join(PLY, "wordmark.png"), 40)
    dot = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    ImageDraw.Draw(dot).ellipse([2, 2, 37, 37], fill=(160, 170, 255, 255))
    dot.resize((10, 10), Image.LANCZOS).save(os.path.join(PLY, "dot.png"))
    with open(os.path.join(PLY, "novaos.plymouth"), "w") as f:
        f.write("""[Plymouth Theme]
Name=NovaOS
Description=NovaOS boot splash
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/novaos
ScriptFile=/usr/share/plymouth/themes/novaos/novaos.script
""")
    with open(os.path.join(PLY, "novaos.script"), "w") as f:
        f.write("""// NovaOS boot splash
Window.SetBackgroundTopColor(0.020, 0.027, 0.060);
Window.SetBackgroundBottomColor(0.045, 0.031, 0.118);

logo.image = Image("logo.png");
logo.sprite = Sprite(logo.image);
cx = Window.GetX() + Window.GetWidth() / 2;
cy = Window.GetY() + Window.GetHeight() / 2;
logo.sprite.SetPosition(cx - logo.image.GetWidth() / 2, cy - logo.image.GetHeight() / 2 - 60, 1);

word.image = Image("wordmark.png");
word.sprite = Sprite(word.image);
word.sprite.SetPosition(cx - word.image.GetWidth() / 2, cy + 30, 1);

dot_image = Image("dot.png");
for (i = 0; i < 3; i++) {
	dots[i] = Sprite(dot_image);
	dots[i].SetPosition(cx - 25 + i * 20, cy + 110, 1);
	dots[i].SetOpacity(0.2);
}

t = 0;
fun refresh_callback() {
	t++;
	for (i = 0; i < 3; i++) {
		phase = Math.Sin((t / 9) - i * 0.9);
		if (phase < 0) phase = 0;
		dots[i].SetOpacity(0.2 + 0.8 * phase);
	}
	logo.sprite.SetOpacity(0.85 + 0.15 * Math.Sin(t / 25));
}
Plymouth.SetRefreshFunction(refresh_callback);

// --- password prompt (only used for encrypted disks) ---
prompt.sprite = Sprite();
fun display_password_callback(prompt_text, bullets) {
	s = prompt_text + "  ";
	for (i = 0; i < bullets; i++) s += "*";
	prompt.sprite.SetImage(Image.Text(s, 0.85, 0.87, 1.0));
	prompt.sprite.SetPosition(cx - prompt.sprite.GetImage().GetWidth() / 2, cy + 160, 2);
}
fun display_normal_callback() { prompt.sprite.SetImage(Image.Text("", 1, 1, 1)); }
Plymouth.SetDisplayPasswordFunction(display_password_callback);
Plymouth.SetDisplayNormalFunction(display_normal_callback);

// --- messages from the boot process ---
msg.sprite = Sprite();
fun message_callback(text) {
	msg.sprite.SetImage(Image.Text(text, 0.55, 0.58, 0.75));
	msg.sprite.SetPosition(cx - msg.sprite.GetImage().GetWidth() / 2, Window.GetHeight() - 60, 2);
}
Plymouth.SetMessageFunction(message_callback);
""")


def logos():
    os.makedirs(LOGO_DIR, exist_ok=True)
    for s in (64, 128, 256, 512):
        rsvg(LOGO_SVG, os.path.join(LOGO_DIR, f"novaos-logo-{s}.png"), s)
    wordmark(os.path.join(LOGO_DIR, "novaos-wordmark-white.png"), 96)
    wordmark(os.path.join(LOGO_DIR, "novaos-wordmark-dark.png"), 96, "#151935")
    # LightDM / installer backdrop (no logo, the greeter draws its own UI)
    boot_background(os.path.join(ROOT, "usr/share/backgrounds/novaos/nova-login.jpg"), 2560, 1600, False)


if __name__ == "__main__":
    logos()
    grub_theme()
    plymouth()
    print("boot artwork written")
