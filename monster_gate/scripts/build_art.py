#!/usr/bin/env python3
"""Draw the top-down dungeon tiles public/art/manifest.json expects.

Run from the repo root (the workspace venv has Pillow):

    uv run --no-sync python monster_gate/scripts/build_art.py

The view is straight down on a square grid (src/ui/render/grid.ts), so tiles are
plain squares and there is no projection to match. They are drawn here rather
than cut from a pack because the six castles are the same shapes in different
palettes: one ramp per castle (luminance 0..1 -> colour) paints every tile, and
that is what makes a castle recognisable at a glance.

Sprites are exported at 2x the on-screen size so they stay crisp at
devicePixelRatio 2; the manifest halves them again with `scale`.
"""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "public/art")

TS = 48  # must match TS in src/ui/render/grid.ts
EXPORT = 2  # export at 2x for high-dpi displays
SS = 4  # supersample factor while drawing
N = TS * EXPORT * SS  # working canvas edge

Ramp = list[tuple[float, tuple[int, int, int]]]


def pick(ramp: Ramp, t: float) -> tuple[int, int, int]:
    """The colour this castle puts at luminance `t`."""
    t = max(0.0, min(1.0, t))
    lo = max((s for s in ramp if s[0] <= t), key=lambda s: s[0], default=ramp[0])
    hi = min((s for s in ramp if s[0] >= t), key=lambda s: s[0], default=ramp[-1])
    f = 0.0 if hi[0] == lo[0] else (t - lo[0]) / (hi[0] - lo[0])
    return tuple(round(lo[1][i] + (hi[1][i] - lo[1][i]) * f) for i in range(3))  # type: ignore[return-value]


class Theme:
    def __init__(self, ramp: Ramp, grout: tuple[int, int, int] | None = None, ice: Ramp | None = None) -> None:
        self.ramp = ramp
        # what shows between the stones; a colour here reads as something seeping up
        self.grout = grout
        self.ice = ice


THEMES: dict[str, Theme] = {
    # ゆかい: 古典的な石の地下城（灰×茶）
    "yukai": Theme([(0.0, (34, 30, 26)), (0.4, (104, 92, 74)), (0.72, (156, 140, 114)), (1.0, (206, 192, 162))]),
    # LIGHT: 白い大聖堂（白×金）
    "light": Theme([(0.0, (62, 55, 48)), (0.42, (172, 162, 146)), (0.74, (232, 226, 210)), (1.0, (255, 226, 158))]),
    # VAGUE: 苔むした霧の遺跡（緑×灰）
    "vague": Theme([(0.0, (22, 30, 25)), (0.4, (66, 84, 62)), (0.72, (118, 138, 110)), (1.0, (184, 196, 172))]),
    # COLD: 氷の洞窟（青×白）
    "cold": Theme(
        [(0.0, (14, 24, 44)), (0.42, (62, 96, 142)), (0.76, (134, 176, 214)), (1.0, (232, 248, 255))],
        ice=[(0.0, (12, 52, 82)), (0.45, (46, 148, 190)), (0.78, (126, 216, 240)), (1.0, (238, 254, 255))],
    ),
    # CRUEL: 腐食した工房（紫×黄緑）— 黄緑は目地から滲む酸として出す
    "cruel": Theme(
        [(0.0, (26, 15, 36)), (0.42, (80, 48, 104)), (0.72, (136, 92, 156)), (1.0, (196, 164, 206))],
        grout=(126, 176, 52),
    ),
    # TIGHT: 竜の巣（黒×赤）— 赤は割れ目から覗く溶岩
    "tight": Theme(
        [(0.0, (8, 7, 9)), (0.45, (40, 32, 34)), (0.75, (72, 58, 56)), (1.0, (104, 86, 82))],
        grout=(206, 62, 20),
    ),
}


def mix(a: tuple[int, int, int], b: tuple[int, int, int], f: float) -> tuple[int, int, int]:
    return tuple(round(a[i] + (b[i] - a[i]) * f) for i in range(3))  # type: ignore[return-value]


def canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def bevel(d: ImageDraw.ImageDraw, box: tuple[int, int, int, int], ramp: Ramp, mid: float, lip: int) -> None:
    """A slab: flat face, lit top-left edge, shaded bottom-right edge."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=pick(ramp, mid))
    d.rectangle((x0, y0, x1, y0 + lip), fill=pick(ramp, mid + 0.16))
    d.rectangle((x0, y0, x0 + lip, y1), fill=pick(ramp, mid + 0.11))
    d.rectangle((x0, y1 - lip, x1, y1), fill=pick(ramp, mid - 0.2))
    d.rectangle((x1 - lip, y0, x1, y1), fill=pick(ramp, mid - 0.14))


def floor_tile(th: Theme, accent: bool) -> Image.Image:
    """One flagstone per cell. Four smaller stones read as brickwork and then the
    floor and the walls turn into the same texture; one stone per cell also lets
    the player count tiles, which a roguelike needs."""
    im, d = canvas()
    dark = pick(th.ramp, 0.14)
    # a tinted castle only stains its mortar; the undiluted colour is saved for
    # the cracks below, or the floor turns into a neon grid
    d.rectangle((0, 0, N, N), fill=mix(dark, th.grout, 0.34) if th.grout else dark)
    g = round(N * 0.045)  # grout
    bevel(d, (g, g, N - g, N - g), th.ramp, 0.68, round(N * 0.022))
    if accent:
        crack = mix(pick(th.ramp, 0.5), th.grout, 0.8) if th.grout else pick(th.ramp, 0.34)
        d.line(
            [(N * 0.30, N * 0.20), (N * 0.40, N * 0.34), (N * 0.33, N * 0.48), (N * 0.44, N * 0.62)],
            fill=crack,
            width=round(N * 0.014),
        )
        for px_, py_, r in [(0.68, 0.30, 0.03), (0.74, 0.66, 0.024), (0.28, 0.74, 0.026)]:
            d.ellipse((N * (px_ - r), N * (py_ - r), N * (px_ + r), N * (py_ + r)), fill=pick(th.ramp, 0.5))
    return im


def wall_tile(th: Theme) -> Image.Image:
    """Offset brick courses. Much darker than the floor, with a lit top edge, so
    a wall reads as mass rather than as a differently coloured floor."""
    im, d = canvas()
    d.rectangle((0, 0, N, N), fill=pick(th.ramp, 0.03))
    rows = 4
    h = N / rows
    m = round(N * 0.022)  # mortar
    for r in range(rows):
        y0 = round(r * h) + m
        y1 = round((r + 1) * h) - m
        offset = (N / 4) if r % 2 else 0
        x = -N / 4 + offset
        while x < N:
            bevel(d, (round(x) + m, y0, round(x + N / 2) - m, y1), th.ramp, 0.23 + (r % 2) * 0.04, round(N * 0.012))
            x += N / 2
    d.rectangle((0, 0, N, round(N * 0.05)), fill=pick(th.ramp, 0.44))
    d.rectangle((0, N - round(N * 0.07), N, N), fill=pick(th.ramp, 0.02))
    return im


def ice_tile(th: Theme) -> Image.Image:
    ramp = th.ice or th.ramp
    im, d = canvas()
    d.rectangle((0, 0, N, N), fill=pick(ramp, 0.3))
    bevel(d, (round(N * 0.03), round(N * 0.03), round(N * 0.97), round(N * 0.97)), ramp, 0.72, round(N * 0.02))
    for x0, y0, w in [(0.16, 0.62, 0.09), (0.46, 0.3, 0.06)]:
        d.line([(N * x0, N * y0), (N * (x0 + 0.34), N * (y0 - 0.34))], fill=pick(ramp, 1.0), width=round(N * w * 0.5))
    return im


def stairs_tile(th: Theme) -> Image.Image:
    im, d = canvas()
    d.rectangle((0, 0, N, N), fill=pick(th.ramp, 0.14))
    for i in range(4):
        t = i / 4
        inset_ = N * (0.1 + t * 0.16)
        d.rectangle((inset_, N * (0.14 + t * 0.19), N - inset_, N * (0.32 + t * 0.19)), fill=pick(th.ramp, 0.62 - t * 0.16))
    d.rectangle((N * 0.26, N * 0.86, N * 0.74, N * 0.96), fill=(6, 8, 16))
    return im


def door_tile(th: Theme, ew: bool) -> Image.Image:
    """Floor with two posts across the passage, so a doorway reads as a doorway
    from straight above."""
    im = floor_tile(th, False)
    d = ImageDraw.Draw(im)
    t = round(N * 0.14)
    wood = (150, 96, 44)
    dark = (86, 52, 22)
    if ew:  # passage runs east-west: posts on the north and south edges
        for y0 in (0, N - t):
            d.rectangle((0, y0, N, y0 + t), fill=wood)
            d.rectangle((0, y0 + t - round(t * 0.3), N, y0 + t), fill=dark)
    else:
        for x0 in (0, N - t):
            d.rectangle((x0, 0, x0 + t, N), fill=wood)
            d.rectangle((x0 + t - round(t * 0.3), 0, x0 + t, N), fill=dark)
    return im


def export(im: Image.Image, rel: str) -> dict:
    """Downscale out of the supersample and write. Returns the manifest entry."""
    size = TS * EXPORT
    out = im.resize((size, size), Image.LANCZOS)
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out.save(path, optimize=True)
    return {"src": rel, "ax": size / 2, "ay": size / 2, "scale": round(1 / EXPORT, 4)}


def thumbnail(tiles: dict[str, Image.Image]) -> Image.Image:
    """A 5x4 patch of room and wall for the castle picker, built from the real
    tiles so the picture and the dungeon can never drift apart."""
    cols, rows = 5, 4
    size = TS * EXPORT
    small = {k: v.resize((size, size), Image.LANCZOS) for k, v in tiles.items()}
    sheet = Image.new("RGBA", (cols * size, rows * size), (0, 0, 0, 0))
    for y in range(rows):
        for x in range(cols):
            edge = x == 0 or y == 0 or x == cols - 1 or y == rows - 1
            key = "tile.wall" if edge else ("tile.floor.b" if (x + y) % 4 == 2 else "tile.floor")
            sheet.alpha_composite(small[key], (x * size, y * size))
    return sheet


def export_thumb(im: Image.Image, rel: str) -> dict:
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, optimize=True)
    return {"src": rel, "ax": im.width / 2, "ay": im.height / 2, "scale": round(1 / EXPORT, 4)}


def build_theme(name: str, th: Theme) -> dict:
    tiles = {
        "tile.floor": floor_tile(th, False),
        "tile.floor.b": floor_tile(th, True),
        "tile.wall": wall_tile(th),
        "tile.stairs": stairs_tile(th),
        "tile.door.ns": door_tile(th, False),
        "tile.door.ew": door_tile(th, True),
    }
    if th.ice or name == "cold":
        tiles["tile.ice"] = ice_tile(th)
    # ゆかいは既定セット（接頭辞なし）。他の城だけ id に城名を付ける
    prefix = "" if name == "yukai" else f"{name}."
    out = {f"{prefix}{id_}": export(im, f"{name}/{id_.removeprefix('tile.')}.png") for id_, im in tiles.items()}
    out[f"thumb.{name}"] = export_thumb(thumbnail(tiles), f"{name}/thumb.png")
    return out


def main() -> None:
    manifest_path = os.path.join(OUT, "manifest.json")
    manifest = {"version": 1, "sprites": {}}
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
    for name, th in THEMES.items():
        manifest["sprites"].update(build_theme(name, th))
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {len(manifest['sprites'])} sprites to {manifest_path}")


if __name__ == "__main__":
    main()
