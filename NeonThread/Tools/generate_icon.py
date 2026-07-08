#!/usr/bin/env python3
"""Generate NeonThread app icons (light / dark / tinted) with PIL.

Draws a glowing neon comet weaving a trailing thread through the dark,
matching the game's aesthetic. Writes 1024x1024 PNGs (opaque, no rounded
corners — iOS masks them) into the AppIcon.appiconset.
"""

import math
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter

S = 1024
OUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "NeonThread",
    "Assets.xcassets",
    "AppIcon.appiconset",
)

CYAN = (60, 240, 255)
MAGENTA = (255, 45, 190)
WHITE = (235, 255, 255)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def thread_points(n=260):
    """Comet path: weaves left->right, head on the right."""
    margin = 165
    amp = 232
    pts = []
    for i in range(n + 1):
        t = i / n
        x = margin + t * (S - 2 * margin)
        y = S / 2 + amp * math.sin(t * math.pi * 2.05 - 0.5) * (0.35 + 0.65 * t)
        pts.append((x, y, t))
    return pts


def draw_thread(draw, pts, width, color_fn):
    for i in range(len(pts) - 1):
        x0, y0, t0 = pts[i]
        x1, y1, _ = pts[i + 1]
        draw.line([(x0, y0), (x1, y1)], fill=color_fn(t0), width=width)
        # round joints so the thick stroke stays smooth
        r = width / 2
        draw.ellipse([x0 - r, y0 - r, x0 + r, y0 + r], fill=color_fn(t0))


def radial_background(center_rgb, edge_rgb):
    bg = Image.new("RGB", (S, S), edge_rgb)
    px = bg.load()
    cx = cy = S / 2
    maxd = math.hypot(cx, cy)
    for y in range(S):
        for x in range(S):
            d = math.hypot(x - cx, y - cy) / maxd
            d = min(1.0, d * 1.15)
            px[x, y] = lerp(center_rgb, edge_rgb, d)
    return bg


def comet_head(size, color, glow=True):
    layer = Image.new("RGB", (S, S), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    hx, hy, _ = thread_points()[-1]
    r = size
    d.ellipse([hx - r, hy - r, hx + r, hy + r], fill=color)
    if glow:
        layer = layer.filter(ImageFilter.GaussianBlur(size * 0.9))
    core = Image.new("RGB", (S, S), (0, 0, 0))
    dc = ImageDraw.Draw(core)
    dc.ellipse([hx - r * 0.55, hy - r * 0.55, hx + r * 0.55, hy + r * 0.55], fill=WHITE)
    return ImageChops.add(layer, core)


def sparks(color, count=26, seed=7):
    import random

    rng = random.Random(seed)
    layer = Image.new("RGB", (S, S), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    hx, hy, _ = thread_points()[-1]
    for _ in range(count):
        a = rng.uniform(0, 2 * math.pi)
        dist = rng.uniform(40, 210)
        x = hx + math.cos(a) * dist
        y = hy + math.sin(a) * dist * 0.8
        r = rng.uniform(3, 11)
        fade = max(0.15, 1 - dist / 240)
        d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(c * fade) for c in color))
    return layer.filter(ImageFilter.GaussianBlur(4))


def color_fn(t):
    return lerp(MAGENTA, CYAN, min(1.0, t * 1.15))


def build(background, thread_color_fn, head_color, mono=False):
    pts = thread_points()
    img = background.copy()

    # Wide + medium glow passes composited additively.
    for width, blur in [(70, 46), (40, 22), (24, 10)]:
        glow = Image.new("RGB", (S, S), (0, 0, 0))
        gd = ImageDraw.Draw(glow)
        draw_thread(gd, pts, width, thread_color_fn)
        glow = glow.filter(ImageFilter.GaussianBlur(blur))
        img = ImageChops.add(img, glow)

    img = ImageChops.add(img, sparks(head_color))
    img = ImageChops.add(img, comet_head(58, head_color, glow=True))

    # Sharp bright core on top.
    core = Image.new("RGB", (S, S), (0, 0, 0))
    cd = ImageDraw.Draw(core)
    core_color = (255, 255, 255) if mono else WHITE
    draw_thread(cd, pts, 9, lambda t: core_color)
    img = ImageChops.add(img, core)
    return img


def main():
    # Light / default: deep navy radial background.
    light = build(
        radial_background((16, 18, 46), (4, 4, 12)),
        color_fn,
        CYAN,
    )
    light.save(os.path.join(OUT, "icon-light.png"))

    # Dark: near-black background, same neon.
    dark = build(
        radial_background((10, 10, 28), (2, 2, 6)),
        color_fn,
        CYAN,
    )
    dark.save(os.path.join(OUT, "icon-dark.png"))

    # Tinted: grayscale thread on black; iOS applies the user's tint.
    gray = lambda t: (200, 200, 200)
    tinted = build(Image.new("RGB", (S, S), (0, 0, 0)), gray, (240, 240, 240), mono=True)
    tinted.save(os.path.join(OUT, "icon-tinted.png"))

    print("wrote icon-light.png, icon-dark.png, icon-tinted.png to", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
