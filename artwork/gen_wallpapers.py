#!/usr/bin/env python3
"""Procedurally generate the original NovaOS wallpapers (2560x1600).

All artwork is generated from code (numpy + Pillow), so there are no
external image sources and no licensing questions.
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = sys.argv[1] if len(sys.argv) > 1 else "rootfs"
DEST = os.path.join(OUT, "usr/share/backgrounds/novaos")
W, H = 3840, 2160
rng = np.random.default_rng(7)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def grid(w=W, h=H):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    return x / w, y / h


def noise(w, h, cells, seed):
    """Smooth value noise via bicubic upsampling of a random grid."""
    r = np.random.default_rng(seed)
    small = (r.random((cells[1] + 3, cells[0] + 3)) * 255).astype(np.uint8)
    img = Image.fromarray(small, "L").resize((w + w // cells[0] * 3, h + h // cells[1] * 3),
                                             Image.BICUBIC)
    arr = np.asarray(img, np.float32)[:h, :w] / 255.0
    return arr


def fbm(w, h, base=4, octaves=5, seed=0):
    total = np.zeros((h, w), np.float32)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        c = base * 2 ** o
        total += amp * noise(w, h, (c, max(1, int(c * h / w))), seed + o)
        norm += amp
        amp *= 0.5
    return total / norm


def blob(x, y, cx, cy, rx, ry=None):
    ry = ry or rx
    return np.exp(-(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2))


def finish(rgb, name, grain=0.012, vignette=0.35):
    x, y = grid(rgb.shape[1], rgb.shape[0])
    if vignette:
        v = 1 - vignette * (((x - 0.5) * 1.1) ** 2 + ((y - 0.5) * 1.3) ** 2)
        rgb = rgb * np.clip(v, 0, 1)[..., None]
    rgb = rgb + rng.normal(0, grain, rgb.shape).astype(np.float32)  # dithering grain
    img = Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")
    os.makedirs(os.path.join(DEST, "thumbs"), exist_ok=True)
    img.save(os.path.join(DEST, name + ".jpg"), quality=92, subsampling=0, optimize=True)
    img.resize((320, 180), Image.LANCZOS).save(os.path.join(DEST, "thumbs", name + ".jpg"), quality=88)
    print("wrote", name)
    return img


def screen(a, b):
    return 1 - (1 - a) * (1 - b)


# ---------------------------------------------------------------------------
# 1. Aurora - blue & purple abstract gradient
# ---------------------------------------------------------------------------
def aurora():
    x, y = grid()
    top, bot = hexrgb("#03050f"), hexrgb("#0c0626")
    rgb = top + (bot - top) * y[..., None]
    for cx, cy, r, col, k in [(0.12, 0.30, 0.42, "#1d4ed8", 0.45), (0.88, 0.22, 0.45, "#6d28d9", 0.45),
                              (0.6, 0.95, 0.5, "#4c1d95", 0.55), (0.3, 0.8, 0.3, "#0e7490", 0.25),
                              (0.97, 0.75, 0.3, "#a21caf", 0.3)]:
        rgb = screen(rgb, hexrgb(col) * (k * blob(x, y, cx, cy, r, r * 1.1))[..., None])
    warp = fbm(W, H, 3, 4, 11)
    for i, (c1, c2, yc, amp, wid, inten) in enumerate([
            ("#38bdf8", "#a855f7", 0.42, 0.10, 0.045, 0.85),
            ("#22d3ee", "#6366f1", 0.55, 0.08, 0.03, 0.6),
            ("#818cf8", "#e879f9", 0.33, 0.07, 0.022, 0.45)]):
        center = yc + amp * np.sin(x * 2 * math.pi * (0.8 + 0.3 * i) + i * 1.7) + 0.08 * (warp - 0.5)
        width = wid * (0.7 + 0.8 * fbm(W, H, 2, 3, 30 + i))
        band = np.exp(-((y - center) / width) ** 2)
        # soft curtain streaks above the band
        streak = np.clip(1 - (center - y) / 0.22, 0, 1) ** 2 * (y < center) * 0.22
        streak *= 0.4 + 0.6 * noise(W, H, (60, 3), 50 + i) ** 2
        a = (band + streak * band.max()) * inten
        col = hexrgb(c1) * (1 - x[..., None]) + hexrgb(c2) * x[..., None]
        rgb = screen(rgb, col * a[..., None])
    # tiny stars in the dark top region
    stars = (rng.random((H, W)) > 0.99965) * rng.random((H, W)) * (1 - y) ** 2
    rgb = screen(rgb, np.repeat(stars[..., None], 3, 2) * 0.9)
    return finish(rgb, "nova-aurora")


# ---------------------------------------------------------------------------
# 2. Midnight Peaks - minimalist dark geometric landscape (low-poly)
# ---------------------------------------------------------------------------
def midnight_peaks():
    S = 2  # supersampling for anti-aliased polygons
    w, h = W * S, H * S
    x, y = grid(W, H)
    sky_top, sky_hz = hexrgb("#070a18"), hexrgb("#27305e")
    sky = sky_top + (sky_hz - sky_top) * (y ** 1.6)[..., None]
    sky = screen(sky, hexrgb("#6d5dfc") * (0.35 * blob(x, y, 0.68, 0.62, 0.45, 0.25))[..., None])
    stars = (rng.random((H, W)) > 0.9993) * (0.3 + 0.7 * rng.random((H, W))) * (1 - y) ** 1.5
    sky = screen(sky, np.repeat(stars[..., None], 3, 2))
    img = Image.fromarray((np.clip(sky, 0, 1) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    d = ImageDraw.Draw(img)
    # crescent moon
    mx, my, mr = int(0.72 * w), int(0.22 * h), int(0.045 * h)
    glow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(glow).ellipse([mx - mr * 4, my - mr * 4, mx + mr * 4, my + mr * 4], fill=60)
    glow = glow.filter(ImageFilter.GaussianBlur(mr * 2))
    img = Image.composite(Image.new("RGB", (w, h), (160, 170, 255)), img, glow)
    d = ImageDraw.Draw(img)
    moon = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(moon)
    md.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=255)
    off = int(mr * 0.55)
    md.ellipse([mx - mr + off, my - mr - off // 3, mx + mr + off, my + mr - off // 3], fill=0)
    img = Image.composite(Image.new("RGB", (w, h), (236, 238, 255)), img, moon)
    d = ImageDraw.Draw(img)
    # re-draw sky under the "bite" so it blends: sample sky colour there
    layers = [  # (valley y, amplitude, peaks, lit colour, shade colour, seed)
        (0.56, 0.20, 5, "#4a4fa8", "#2c2f78", 1),
        (0.66, 0.17, 6, "#363a8a", "#212461", 2),
        (0.75, 0.14, 8, "#262a6a", "#18194a", 3),
        (0.84, 0.11, 9, "#1a1c4c", "#101233", 4),
        (0.93, 0.08, 11, "#101130", "#08091c", 5),
    ]
    for valley, amp, npk, cl, cd, seed in layers:
        r = np.random.default_rng(seed)
        cl, cd = hexrgb(cl), hexrgb(cd)
        base_col = cd * 0.85
        # zig-zag ridge: valley points m_i and peaks p_i between them
        mx = np.linspace(-0.08, 1.08, npk + 1)
        mx[1:-1] += (r.random(npk - 1) - 0.5) * (mx[1] - mx[0]) * 0.5
        my = valley - amp * 0.25 * r.random(len(mx))
        px = (mx[:-1] + mx[1:]) / 2 + (r.random(npk) - 0.5) * 0.04
        py = valley - amp * (0.45 + 0.55 * r.random(npk))
        py[r.integers(0, npk)] = valley - amp * 1.12
        # keep slopes plausible: cap each peak's height by its base width
        half = (mx[1:] - mx[:-1]) / 2
        py = np.maximum(py, valley - half * (W / H) * 0.75)
        ridge = []
        for i in range(npk):
            ridge += [(mx[i], my[i]), (px[i], py[i])]
        ridge.append((mx[-1], my[-1]))
        outline = [(qx * w, qy * h) for qx, qy in ridge] + [(w * 1.1, h * 1.1), (-w * 0.1, h * 1.1)]
        d.polygon(outline, fill=tuple(int(c * 255) for c in base_col))
        depth = valley + amp * 0.35
        for i in range(npk):
            bx = px[i] + (r.random() - 0.5) * (mx[i + 1] - mx[i]) * 0.4
            by = depth + r.random() * amp * 0.15
            lit = np.clip(cl * (0.95 + 0.12 * r.random()), 0, 1)
            shd = np.clip(cd * (0.95 + 0.1 * r.random()), 0, 1)
            mid = (lit + shd) / 2 * 0.9
            tri = [
                ([(mx[i], my[i]), (px[i], py[i]), (bx, by)], lit),
                ([(px[i], py[i]), (mx[i + 1], my[i + 1]), (bx, by)], shd),
                ([(mx[i], my[i]), (bx, by), (mx[i], depth + amp * 0.25)], lit * 0.82),
                ([(bx, by), (mx[i + 1], my[i + 1]), (mx[i + 1], depth + amp * 0.25)], shd * 0.85),
                ([(mx[i], depth + amp * 0.25), (bx, by), (mx[i + 1], depth + amp * 0.25)], mid),
            ]
            for poly, col in tri:
                d.polygon([(qx * w, qy * h) for qx, qy in poly],
                          fill=tuple(int(c * 255) for c in np.clip(col, 0, 1)))
    img = img.resize((W, H), Image.LANCZOS)
    rgb = np.asarray(img, np.float32) / 255
    # low mist between layers
    mist = 0.18 * np.exp(-((y - 0.78) / 0.06) ** 2) * (0.6 + 0.4 * fbm(W, H, 4, 3, 9))
    rgb = screen(rgb, hexrgb("#7f7ff5") * mist[..., None])
    return finish(rgb, "nova-midnight-peaks", vignette=0.25)


# ---------------------------------------------------------------------------
# 3. Crystal - glass and crystal-inspired artwork
# ---------------------------------------------------------------------------
def crystal():
    x, y = grid()
    rgb = hexrgb("#04050f") + (hexrgb("#12093a") - hexrgb("#04050f")) * (1 - y)[..., None] * 0.9
    rgb = screen(rgb, hexrgb("#3b1d8f") * (0.7 * blob(x, y, 0.5, 0.75, 0.5, 0.35))[..., None])
    rgb = screen(rgb, hexrgb("#0b5d8a") * (0.5 * blob(x, y, 0.2, 0.4, 0.35))[..., None])
    base = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).convert("RGBA")

    S = 2
    w, h = W * S, H * S
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    edges = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    de = ImageDraw.Draw(edges)
    r = np.random.default_rng(3)
    shards = [  # base x, base y, angle (deg from vertical), length, width, palette
        (0.50, 0.92, 0, 0.70, 0.085, ("#7dd3fc", "#6366f1")),
        (0.43, 0.94, -18, 0.55, 0.07, ("#c4b5fd", "#7c3aed")),
        (0.58, 0.95, 16, 0.58, 0.075, ("#a5f3fc", "#3b82f6")),
        (0.36, 0.97, -34, 0.40, 0.06, ("#f0abfc", "#a21caf")),
        (0.65, 0.97, 33, 0.42, 0.06, ("#93c5fd", "#4f46e5")),
        (0.29, 1.00, -52, 0.30, 0.05, ("#e9d5ff", "#6d28d9")),
        (0.72, 1.00, 50, 0.32, 0.05, ("#bae6fd", "#0284c7")),
        (0.47, 0.99, -6, 0.30, 0.05, ("#ffffff", "#818cf8")),
    ]
    for bx, by, ang, length, wid, (c1, c2) in shards:
        a = math.radians(ang)
        ux, uy = math.sin(a), -math.cos(a)          # axis direction (towards tip)
        px, py = -uy, ux                            # perpendicular
        aspect = W / H
        def P(t, s):  # t along axis (0..1), s across (-1..1) -> image coords
            X = bx + (ux * t * length) / aspect + px * s * wid / aspect
            Y = by + uy * t * length + py * s * wid
            return (X * w, Y * h)
        body = 0.78
        pts = {"bl": P(0, -1), "br": P(0, 1), "ml": P(body, -1), "mr": P(body, 1),
               "mc": P(body + 0.05, 0), "tip": P(1, 0.0), "bc": P(0, 0.05)}
        facets = [  # polygon, brightness, alpha
            ([pts["bl"], pts["ml"], pts["mc"], pts["bc"]], 1.00, 150),
            ([pts["bc"], pts["mc"], pts["mr"], pts["br"]], 0.55, 165),
            ([pts["ml"], pts["tip"], pts["mc"]], 1.25, 185),
            ([pts["mc"], pts["tip"], pts["mr"]], 0.70, 190),
        ]
        col1, col2 = hexrgb(c1), hexrgb(c2)
        for poly, bright, alpha in facets:
            mask = Image.new("L", (w, h), 0)
            ImageDraw.Draw(mask).polygon(poly, fill=alpha)
            xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
            x0, x1, y0, y1 = int(min(xs)), int(max(xs)) + 1, int(min(ys)), int(max(ys)) + 1
            x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, w), min(y1, h)
            if x1 <= x0 or y1 <= y0:
                continue
            gy = np.linspace(0, 1, y1 - y0, dtype=np.float32)[:, None, None]
            gx = np.linspace(0, 1, x1 - x0, dtype=np.float32)[None, :, None]
            t = np.clip(0.65 * gy + 0.35 * gx, 0, 1)
            grad = (col1 * (1 - t) + col2 * t) * bright
            grad = np.clip(grad, 0, 1)
            patch = Image.fromarray((grad * 255).astype(np.uint8), "RGB").convert("RGBA")
            patch.putalpha(mask.crop((x0, y0, x1, y1)))
            layer.alpha_composite(patch, (x0, y0))
            de.line(poly + [poly[0]], fill=(255, 255, 255, 120), width=3)
        de.line([pts["bc"], pts["mc"], pts["tip"]], fill=(255, 255, 255, 200), width=4)
    glow = edges.filter(ImageFilter.GaussianBlur(10))
    layer.alpha_composite(glow)
    layer.alpha_composite(edges)
    layer = layer.resize((W, H), Image.LANCZOS)
    # soft bloom of the whole crystal cluster
    bloom = layer.filter(ImageFilter.GaussianBlur(60))
    out = base.copy()
    out.alpha_composite(bloom)
    out.alpha_composite(layer)
    rgb = np.asarray(out.convert("RGB"), np.float32) / 255
    # light beams and sparkles
    beam = 0.10 * np.exp(-((x - 0.5 - (0.6 - y) * 0.35) / 0.03) ** 2) * (y < 0.7)
    beam += 0.07 * np.exp(-((x - 0.5 + (0.6 - y) * 0.45) / 0.02) ** 2) * (y < 0.7)
    rgb = screen(rgb, hexrgb("#a5b4fc") * beam[..., None])
    for _ in range(140):
        sx, sy = r.random(), r.random() * 0.9
        rr = 0.002 + 0.006 * r.random() ** 3
        rgb = screen(rgb, hexrgb("#c7d2fe") * (0.6 * r.random() * blob(x, y, sx, sy, rr, rr * 1.6))[..., None]) \
            if rr > 0.006 else rgb
        if rr <= 0.006:
            iy, ix = int(sy * H), int(sx * W)
            rgb[iy:iy + 2, ix:ix + 2] = np.maximum(rgb[iy:iy + 2, ix:ix + 2], 0.6 + 0.4 * r.random())
    return finish(rgb, "nova-crystal", vignette=0.3)


# ---------------------------------------------------------------------------
# 4. Prism - colourful modern abstract (domain-warped flow)
# ---------------------------------------------------------------------------
def prism():
    x, y = grid()
    rgb = (hexrgb("#0b1033") + (hexrgb("#1b1060") - hexrgb("#0b1033")) * y[..., None]).astype(np.float32)
    palette = [("#2563eb", "#7c3aed"), ("#6d28d9", "#db2777"), ("#c026d3", "#f43f5e"),
               ("#f43f5e", "#fb923c"), ("#fb923c", "#facc15"), ("#14b8a6", "#3b82f6"),
               ("#3b82f6", "#8b5cf6")]
    r = np.random.default_rng(9)
    xs = x[0]
    for k, (c1, c2) in enumerate(palette):
        base = 0.18 + k * 0.115
        ph = r.random() * 6.28
        curve = (base + 0.085 * np.sin(xs * (2.2 + 0.25 * k) * math.pi + ph)
                 + 0.03 * np.sin(xs * (5.1 + 0.4 * k) * math.pi + ph * 1.7)
                 - 0.10 * (xs - 0.5))
        cy = curve[None, :]
        inside = 1 / (1 + np.exp(-(y - cy) * H / 1.6))           # anti-aliased edge
        t = np.clip(0.75 * x + 0.25 * (y - cy) * 3, 0, 1)
        col = hexrgb(c1) * (1 - t[..., None]) + hexrgb(c2) * t[..., None]
        # shading inside the band: light near the crest, darker further down
        shade = 0.82 + 0.25 * np.exp(-np.clip(y - cy, 0, None) / 0.035)
        col = col * shade[..., None]
        # soft shadow cast onto the layer above
        above = np.clip(cy - y, 0, None)
        shadow = 1 - 0.45 * np.exp(-above / 0.025) * (y < cy)
        rgb = rgb * shadow[..., None]
        rgb = rgb * (1 - inside[..., None]) + col * inside[..., None]
        # thin specular line along the crest
        crest = np.exp(-((y - cy - 0.002) / 0.0015) ** 2) * 0.35
        rgb = screen(rgb, np.ones(3, np.float32) * crest[..., None])
    return finish(rgb, "nova-prism", vignette=0.2)


# ---------------------------------------------------------------------------
# 5. Lakeside Dawn - clean nature-inspired wallpaper
# ---------------------------------------------------------------------------
def lakeside():
    S = 2
    w, h = W * S, H * S
    x, y = grid()
    horizon = 0.64
    sky_t, sky_m, sky_h = hexrgb("#24427a"), hexrgb("#7d8fc6"), hexrgb("#ffd2a8")
    ty = np.clip(y / horizon, 0, 1)
    sky = np.where((ty < 0.6)[..., None],
                   sky_t + (sky_m - sky_t) * (ty / 0.6)[..., None],
                   sky_m + (sky_h - sky_m) * ((ty - 0.6) / 0.4)[..., None])
    sky = screen(sky, hexrgb("#ffb27a") * (0.85 * blob(x, y, 0.62, horizon - 0.02, 0.22, 0.12))[..., None])
    sky = screen(sky, hexrgb("#fff3d6") * np.clip(blob(x, y, 0.62, horizon - 0.055, 0.022, 0.035) * 1.6, 0, 1)[..., None])
    clouds = np.clip((fbm(W, H, 3, 5, 77) - 0.55) * 4, 0, 1) * (y < horizon * 0.7)
    sky = sky * (1 - 0.3 * clouds[..., None]) + hexrgb("#ffc4c8") * (0.3 * clouds)[..., None]
    img = Image.fromarray((np.clip(sky, 0, 1) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    d = ImageDraw.Draw(img)
    hills = [  # base height, amplitude, colour, seed, trees
        (horizon - 0.10, 0.07, "#8c86b8", 1, False),
        (horizon - 0.06, 0.06, "#6b6aa0", 2, False),
        (horizon - 0.03, 0.05, "#4a4f82", 3, True),
        (horizon - 0.005, 0.035, "#1f2448", 4, True),
    ]
    r = np.random.default_rng(12)
    for base, amp, col, seed, trees in hills:
        prof = fbm(512, 1, 3, 4, 100 + seed)[0]
        xs = np.linspace(0, 1, 512)
        ys = base - amp * (prof - prof.min()) / (prof.max() - prof.min() + 1e-6)
        pts = [(px * w, py * h) for px, py in zip(xs, ys)] + [(w, horizon * h), (0, horizon * h)]
        c = tuple(int(v * 255) for v in hexrgb(col))
        d.polygon(pts, fill=c)
        if trees:
            n = 220 if seed == 4 else 160
            for _ in range(n):
                tx = r.random()
                ty0 = np.interp(tx, xs, ys)
                th = (0.018 + 0.03 * r.random()) * (1.3 if seed == 4 else 0.9)
                tw = th * 0.32 * h / w
                tyb = min(ty0 + 0.012, horizon)
                d.polygon([(tx * w, (tyb - th) * h), ((tx - tw) * w, tyb * h), ((tx + tw) * w, tyb * h)], fill=c)
    img = img.resize((W, H), Image.LANCZOS)
    rgb = np.asarray(img, np.float32) / 255
    # haze bands for depth
    haze = np.exp(-((y - (horizon - 0.04)) / 0.05) ** 2) * 0.25
    rgb = screen(rgb, hexrgb("#ffd9c2") * haze[..., None])
    # lake: mirror the scene above the horizon, darken, add ripples
    hz = int(horizon * H)
    above = rgb[:hz][::-1]
    n = H - hz
    ripple = (noise(W, n, (6, 90), 5) - 0.5) * 18
    rows = np.clip(np.arange(n)[:, None] + ripple.astype(int), 0, hz - 1)
    cols = np.arange(W)[None, :]
    refl = above[rows, cols]
    depth = np.linspace(0, 1, n, dtype=np.float32)[:, None, None]
    water = hexrgb("#1c2a52")
    refl = refl * (0.75 - 0.35 * depth) + water * (0.25 + 0.35 * depth)
    shine = (np.abs(np.sin(np.arange(n)[:, None] * 0.9 + noise(W, n, (40, 30), 8) * 12)) > 0.985)
    shine = shine * blob(x[hz:], y[hz:], 0.62, horizon + 0.05, 0.08, 0.25)
    refl = screen(refl, hexrgb("#ffe0b8") * (0.6 * shine)[..., None])
    rgb = rgb.copy()
    rgb[hz:] = refl
    rgb[hz:hz + 2] = rgb[hz:hz + 2] * 0.9 + 0.1
    return finish(rgb, "nova-lakeside", vignette=0.2)


# ---------------------------------------------------------------------------
# 6. Daylight - soft pastel abstract (pairs well with light mode)
# ---------------------------------------------------------------------------
def daylight():
    x, y = grid()
    rgb = hexrgb("#f4f6ff") + (hexrgb("#e9e6ff") - hexrgb("#f4f6ff")) * y[..., None]
    for cx, cy, rr, col, k in [(0.1, 0.1, 0.5, "#a5c8ff", 0.55), (0.9, 0.3, 0.45, "#d6b8ff", 0.55),
                               (0.55, 0.95, 0.55, "#ffc8e6", 0.45), (0.3, 0.7, 0.3, "#b8f0ff", 0.4)]:
        c = hexrgb(col)
        a = (k * blob(x, y, cx, cy, rr))[..., None]
        rgb = rgb * (1 - a) + c * a
    warp = fbm(W, H, 2, 3, 41)
    for i in range(7):
        yc = 0.25 + i * 0.09 + 0.12 * np.sin(x * 4.2 + i * 0.6) + 0.05 * (warp - 0.5)
        line = np.exp(-((y - yc) / 0.0018) ** 2) * 0.35 + np.exp(-((y - yc) / 0.02) ** 2) * 0.05
        rgb = rgb * (1 - line[..., None]) + np.ones(3) * line[..., None]
    return finish(rgb, "nova-daylight", grain=0.008, vignette=0)


# ---------------------------------------------------------------------------
# 7. Neon Horizon - synthwave sun over a glowing grid
# ---------------------------------------------------------------------------
def neon_horizon():
    x, y = grid()
    hz = 0.58
    sky = hexrgb("#07021a") + (hexrgb("#3b0a5e") - hexrgb("#07021a")) * np.clip(y / hz, 0, 1)[..., None] ** 1.4
    sky = screen(sky, hexrgb("#ff3d9a") * (0.55 * blob(x, y, 0.5, hz, 0.45, 0.12))[..., None])
    stars = (rng.random((H, W)) > 0.9994) * rng.random((H, W)) * (y < hz * 0.8)
    sky = screen(sky, np.repeat(stars[..., None], 3, 2))
    # sun with horizontal cut-outs
    sx, sy, sr = 0.5, hz - 0.17, 0.2
    aspect = W / H
    d = np.sqrt(((x - sx) * aspect) ** 2 + (y - sy) ** 2)
    sun = (d < sr).astype(np.float32)
    t = np.clip((y - (sy - sr)) / (2 * sr), 0, 1)
    sun_col = hexrgb("#ffe066") * (1 - t[..., None]) + hexrgb("#ff2d7a") * t[..., None]
    for i in range(7):
        yc = sy + 0.02 + i * 0.03
        sun *= 1 - ((y > yc) & (y < yc + 0.004 + i * 0.0018)).astype(np.float32)
    glow = np.exp(-np.clip(d - sr, 0, None) / 0.05) * 0.5
    rgb = sky * (1 - sun[..., None]) + sun_col * sun[..., None]
    rgb = screen(rgb, hexrgb("#ff5fa2") * glow[..., None])
    # ground with perspective grid
    gy = np.clip((y - hz) / (1 - hz), 1e-4, 1)
    ground = (y > hz)
    base = hexrgb("#12002a") * (1 - gy[..., None]) + hexrgb("#05010f") * gy[..., None]
    z = 1 / gy
    hlines = np.abs(((z * 0.9) % 1) - 0.5) > (0.5 - 0.03 * gy * 3)
    xv = (x - 0.5) * z
    vlines = np.abs(((xv * 6) % 1) - 0.5) > (0.5 - 0.02 * gy * 3)
    lines = (hlines | vlines).astype(np.float32) * np.clip(gy * 2.5, 0, 1)
    gcol = hexrgb("#ff3df0") * (1 - gy[..., None]) + hexrgb("#3df0ff") * gy[..., None]
    g = base + gcol * (lines * 0.9)[..., None]
    rgb = np.where(ground[..., None], g, rgb)
    rgb = screen(rgb, hexrgb("#ff7ad9") * (0.6 * np.exp(-((y - hz) / 0.006) ** 2))[..., None])
    img = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    return finish(np.asarray(img, np.float32) / 255, "nova-neon-horizon", vignette=0.3)


# ---------------------------------------------------------------------------
# 8. Nebula - deep space clouds and stars
# ---------------------------------------------------------------------------
def nebula():
    w, h = W // 2, H // 2
    x, y = grid(w, h)
    f1 = fbm(w, h, 2, 6, 61)
    f2 = fbm(w, h, 3, 6, 62)
    f3 = fbm(w, h, 2, 5, 63)
    rgb = hexrgb("#020309") * np.ones((h, w, 3), np.float32)
    c1 = np.clip((f1 - 0.45) * 2.6, 0, 1) ** 1.6
    c2 = np.clip((f2 - 0.5) * 3.0, 0, 1) ** 1.8
    c3 = np.clip((f3 - 0.55) * 4.0, 0, 1) ** 2
    band = np.exp(-((y - 0.55 - 0.25 * (x - 0.5)) / 0.28) ** 2)
    rgb = screen(rgb, hexrgb("#7b3bf0") * (c1 * band * 1.4)[..., None])
    rgb = screen(rgb, hexrgb("#ff4f9a") * (c2 * band * 1.2)[..., None])
    rgb = screen(rgb, hexrgb("#38d1ff") * (c3 * band * 1.3)[..., None])
    rgb = screen(rgb, hexrgb("#ffd7f0") * (0.25 * blob(x, y, 0.62, 0.48, 0.08))[..., None])
    img = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
    rgb = np.asarray(img, np.float32) / 255
    r = np.random.default_rng(5)
    stars = (r.random((H, W)) > 0.9985) * (0.3 + 0.7 * r.random((H, W)))
    rgb = screen(rgb, np.repeat(stars[..., None], 3, 2))
    big = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(big)
    for _ in range(60):
        sx, sy, rr = r.random() * W, r.random() * H, 1 + r.random() * 3
        d.ellipse([sx - rr, sy - rr, sx + rr, sy + rr], fill=(255, 255, 255))
    big = np.asarray(big.filter(ImageFilter.GaussianBlur(2.5)), np.float32) / 255
    rgb = screen(rgb, big * 1.6)
    return finish(rgb, "nova-nebula", vignette=0.4)


# ---------------------------------------------------------------------------
# 9. Golden Dunes - sunset desert
# ---------------------------------------------------------------------------
def dunes():
    x, y = grid()
    sky = hexrgb("#2b1b5e") + (hexrgb("#ff9a62") - hexrgb("#2b1b5e")) * np.clip(y / 0.55, 0, 1)[..., None] ** 1.3
    sky = screen(sky, hexrgb("#ffd27a") * (0.9 * blob(x, y, 0.3, 0.5, 0.18, 0.12))[..., None])
    sky = screen(sky, hexrgb("#fff2c9") * np.clip(blob(x, y, 0.3, 0.47, 0.03, 0.05) * 1.8, 0, 1)[..., None])
    rgb = sky
    layers = [(0.52, "#c96a4a", "#7a3a3a", 11), (0.62, "#e08a55", "#8a4636", 12),
              (0.74, "#f0a35e", "#9a5238", 13), (0.88, "#f7b86a", "#a65a3a", 14)]
    for base, lit, shade, seed in layers:
        prof = fbm(W, 1, 2, 3, seed)[0]
        prof = (prof - prof.min()) / (np.ptp(prof) + 1e-6)
        crest = base - 0.09 * prof
        grad = np.gradient(crest)
        inside = y > crest[None, :]
        side = (grad[None, :] > 0).astype(np.float32)
        depth = np.clip((y - crest[None, :]) / 0.15, 0, 1)
        col = hexrgb(lit) * (1 - side[..., None] * 0.55) + hexrgb(shade) * (side[..., None] * 0.55)
        col = col * (1 - 0.25 * depth[..., None])
        ripple = 0.015 * np.sin((y - crest[None, :]) * 300 + np.sin(x * 25) * 3) * depth
        col = np.clip(col + ripple[..., None], 0, 1)
        rgb = np.where(inside[..., None], col, rgb)
        rim = np.exp(-((y - crest[None, :]) / 0.002) ** 2) * 0.5
        rgb = screen(rgb, hexrgb("#ffe0a0") * rim[..., None])
    return finish(rgb, "nova-dunes", vignette=0.25)


# ---------------------------------------------------------------------------
# 10. Ocean Dusk - calm sea under a pastel sky
# ---------------------------------------------------------------------------
def ocean_dusk():
    x, y = grid()
    hz = 0.6
    sky = hexrgb("#1a2a6c") + (hexrgb("#f7a8b8") - hexrgb("#1a2a6c")) * np.clip(y / hz, 0, 1)[..., None] ** 1.5
    clouds = np.clip((fbm(W, H, 2, 5, 81) - 0.52) * 3, 0, 1) * (y < hz)
    sky = sky * (1 - 0.35 * clouds[..., None]) + hexrgb("#ffd1dc") * (0.35 * clouds)[..., None]
    sky = screen(sky, hexrgb("#fff0d0") * np.clip(blob(x, y, 0.7, hz - 0.02, 0.03, 0.05) * 1.5, 0, 1)[..., None])
    hzi = int(hz * H)
    n = H - hzi
    depth = np.linspace(0, 1, n, dtype=np.float32)[:, None]
    waves = noise(W, n, (24, 60), 9) - 0.5
    sea = hexrgb("#24346e") * (1 - depth[..., None]) + hexrgb("#0b1230") * depth[..., None]
    refl = sky[:hzi][::-1][np.clip((np.arange(n)[:, None] * 0.8 + waves * 30).astype(int), 0, hzi - 1), np.arange(W)[None, :]]
    sea = sea * 0.6 + refl * 0.4 * (1 - depth[..., None] * 0.7)
    glitter = (np.abs(np.sin(np.arange(n)[:, None] * 0.7 + waves * 40)) > 0.97) * \
        np.exp(-((x[hzi:] - 0.7) / (0.02 + 0.15 * depth)) ** 2)
    sea = screen(sea, hexrgb("#ffe8c0") * (0.8 * glitter)[..., None])
    rgb = sky.copy()
    rgb[hzi:] = sea
    return finish(rgb, "nova-ocean-dusk", vignette=0.25)


# ---------------------------------------------------------------------------
# 11. Liquid Glass - soft gradient blobs (great for light mode)
# ---------------------------------------------------------------------------
def liquid_glass():
    w, h = W // 4, H // 4
    x, y = grid(w, h)
    rgb = np.ones((h, w, 3), np.float32) * hexrgb("#0d0f2b")
    r = np.random.default_rng(23)
    cols = ["#6c7bff", "#ff6fb5", "#38d1ff", "#a855f7", "#22c55e", "#f59e0b"]
    for i, c in enumerate(cols):
        cx, cy = r.random(), r.random()
        rr = 0.18 + 0.2 * r.random()
        a = blob(x, y, cx, cy, rr * 0.9, rr)
        rgb = rgb * (1 - 0.85 * a[..., None]) + hexrgb(c) * (0.85 * a)[..., None]
    img = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
    img = img.filter(ImageFilter.GaussianBlur(40))
    rgb = np.asarray(img, np.float32) / 255
    return finish(rgb, "nova-liquid-glass", vignette=0.15)


if __name__ == "__main__":
    os.makedirs(DEST, exist_ok=True)
    which = sys.argv[2:] or ["aurora", "midnight_peaks", "crystal", "prism", "lakeside", "daylight",
                             "neon_horizon", "nebula", "dunes", "ocean_dusk", "liquid_glass"]
    for name in which:
        globals()[name]()
