"""Shared flat-art painter for the sprite build scripts.

The look docs/style-guide.md asks for — flat fills, one shadow step lit from the
upper right, a thick dark rim — is drawable, so build_chars.py and build_cards.py
compose it out of primitives instead of shipping bitmaps from elsewhere.
"""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFilter

SS = 2  # supersample, then downscale for clean edges
INK = (26, 20, 32, 255)

# ---- palette ---------------------------------------------------------------
SKIN = (247, 201, 155)
SKIN_G = (122, 186, 96)
STEEL = (185, 194, 204)
RED = (216, 67, 58)
LEATHER = (124, 84, 52)
WOOD = (146, 102, 62)
PURPLE = (107, 75, 181)
GOLD = (255, 216, 90)
BLACK = (43, 43, 58)
BONE = (232, 230, 218)
GREEN = (86, 194, 74)
YELLOW = (232, 197, 58)
DRAGON = (198, 64, 52)
EYE = (30, 26, 40)
WHITE = (250, 250, 252)
BLUE = (59, 125, 221)
ORANGE = (224, 138, 52)


def darker(c, f=0.74):
    return (round(c[0] * f), round(c[1] * f), round(c[2] * f))


def lighter(c, k=45):
    return tuple(min(255, v + k) for v in c)


# ---- shape DSL -------------------------------------------------------------
# Shapes are data so the painter can rasterise them at the supersampled size.
def ell(x0, y0, x1, y1):
    return ("ell", (x0, y0, x1, y1))


def rr(x0, y0, x1, y1, r):
    return ("rr", (x0, y0, x1, y1), r)


def poly(*pts):
    return ("poly", pts)


class Painter:
    """Paints into a square canvas in its own coordinate space."""

    def __init__(self, canvas: int, rim: int = 5, light=(11, -11)):
        self.canvas = canvas
        self.rim = rim
        self.light = light
        self.im = Image.new("RGBA", (canvas * SS, canvas * SS), (0, 0, 0, 0))

    def _mask(self, shape):
        m = Image.new("L", self.im.size, 0)
        d = ImageDraw.Draw(m)
        kind = shape[0]
        if kind == "ell":
            d.ellipse([v * SS for v in shape[1]], fill=255)
        elif kind == "rr":
            d.rounded_rectangle([v * SS for v in shape[1]], shape[2] * SS, fill=255)
        else:
            d.polygon([(x * SS, y * SS) for x, y in shape[1]], fill=255)
        return m

    def part(self, shape, fill, rim=True, shade=True):
        """One flat shape: dark rim, flat fill, one shadow step on the dark side."""
        mask = self._mask(shape)
        bb = mask.getbbox()
        if bb is None:
            return
        if rim:
            pad = self.rim * SS + 2
            box = (max(0, bb[0] - pad), max(0, bb[1] - pad), min(mask.width, bb[2] + pad), min(mask.height, bb[3] + pad))
            sub = mask.crop(box)
            grown = sub.filter(ImageFilter.MaxFilter(self.rim * SS * 2 + 1))
            ring = Image.new("L", mask.size, 0)
            ring.paste(grown, box)
            self.im.paste(INK, (0, 0), ring)
        self.im.paste(fill + (255,), (0, 0), mask)
        if shade:
            lit = Image.new("L", mask.size, 0)
            lit.paste(mask, (self.light[0] * SS, self.light[1] * SS))
            # everything in the shape that the shifted copy does not cover
            shadow = Image.composite(mask, Image.new("L", mask.size, 0), Image.eval(lit, lambda v: 255 - v))
            self.im.paste(darker(fill) + (255,), (0, 0), shadow)

    def flat(self, shape, fill):
        """Detail with no rim and no shading (eyes, stripes, trim)."""
        self.part(shape, fill, rim=False, shade=False)

    def finish(self):
        return self.im.resize((self.canvas, self.canvas), Image.LANCZOS)


def eyes(p, cx, cy, r=15, gap=44, pupil=EYE):
    for dx in (-gap // 2, gap // 2):
        p.flat(ell(cx + dx - r, cy - r, cx + dx + r, cy + r), WHITE)
        p.flat(ell(cx + dx - r + 3, cy - r + 4, cx + dx + r - 6, cy + r - 2), pupil)


# ---- output ----------------------------------------------------------------
def export(im: Image.Image, out_dir: str, rel: str, anchor, scale: float) -> dict:
    """Crop to the ink and write; the anchor moves with the crop."""
    bbox = im.getchannel("A").getbbox()
    if bbox is None:
        raise SystemExit(f"{rel}: fully transparent")
    path = os.path.join(out_dir, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.crop(bbox).save(path, optimize=True)
    return {"src": rel, "ax": anchor[0] - bbox[0], "ay": anchor[1] - bbox[1], "scale": scale}


def merge_manifest(out_dir: str, entries: dict) -> int:
    path = os.path.join(out_dir, "manifest.json")
    manifest = {"version": 1, "sprites": {}}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            manifest = json.load(fh)
    manifest["sprites"].update(entries)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return len(manifest["sprites"])
