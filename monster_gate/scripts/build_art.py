#!/usr/bin/env python3
"""Turn the Kenney dungeon pack into the sprites public/art/manifest.json expects.

Run from the repo root (the workspace venv has Pillow):

    uv run --no-sync python monster_gate/scripts/build_art.py

The pack draws every tile on a shared 256x512 canvas in true 2:1 dimetric, with
the ground diamond 256 wide and 128 tall and its centre at (128, 448) — the same
projection the renderer uses, so tiles need no reprojection, only scaling.

Sprites are exported at 2x the on-screen size so they stay crisp at
devicePixelRatio 2; the manifest halves them again with `scale`.
"""

from __future__ import annotations

import json
import os
import sys

from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "assets/src/kenney/miniature-dungeon/Isometric")
OUT = os.path.join(ROOT, "public/art")

TILE_W = 96  # must match TW in src/ui/render/iso.ts
EXPORT = 2  # export at 2x for high-dpi displays
SRC_TILE_W = 256
SRC_ANCHOR = (128, 448)  # ground centre of the pack's shared canvas
K = TILE_W * EXPORT / SRC_TILE_W  # source -> exported pixels
WALL_CAP_DY = 92  # source px to raise a floor tile by, to cap the hollow wall box


def raw(name: str, orient: str = "N") -> Image.Image:
    return Image.open(os.path.join(SRC, f"{name}_{orient}.png")).convert("RGBA")


def over(base: str, top: str) -> Image.Image:
    """Accent floors like planksBroken have holes punched through them; without a
    plain tile underneath those holes show the black background as a pit."""
    im = raw(base).copy()
    im.alpha_composite(raw(top))
    return im


def wall_block(cap: str = "stone") -> Image.Image:
    """The pack has no full-cell wall: its walls sit on tile edges. Two opposite
    corner pieces close all four sides, and a floor tile roofs the hollow top."""
    im = raw("stoneWallCorner", "E").copy()
    im.alpha_composite(raw("stoneWallCorner", "W"))
    im.alpha_composite(raw(cap), (0, -WALL_CAP_DY))
    return im


# ---- castle palettes -------------------------------------------------------
# The pack is one grey-brown stone set, so the five other castles are the same
# geometry run through a gradient map: source luminance picks a colour off the
# castle's ramp. That keeps Kenney's shading and the 2:1 silhouette while giving
# each castle the palette in docs/plan-design.md 7.1.

Ramp = list[tuple[float, tuple[int, int, int]]]


def ramp_luts(ramp: Ramp) -> list[list[int]]:
    """One 256-entry lookup per channel, linearly interpolated between stops."""
    luts = [[0] * 256 for _ in range(3)]
    for v in range(256):
        t = v / 255
        lo = max((s for s in ramp if s[0] <= t), key=lambda s: s[0], default=ramp[0])
        hi = min((s for s in ramp if s[0] >= t), key=lambda s: s[0], default=ramp[-1])
        f = 0.0 if hi[0] == lo[0] else (t - lo[0]) / (hi[0] - lo[0])
        for ch in range(3):
            luts[ch][v] = round(lo[1][ch] + (hi[1][ch] - lo[1][ch]) * f)
    return luts


def grade(im: Image.Image, ramp: Ramp) -> Image.Image:
    lum = im.convert("L")
    luts = ramp_luts(ramp)
    r, g, b = (lum.point(luts[ch]) for ch in range(3))
    return Image.merge("RGBA", (r, g, b, im.getchannel("A")))


def tint(im: Image.Image, rgb: tuple[int, int, int], a: float) -> Image.Image:
    """Wash a flat colour over the sprite's own pixels only."""
    wash = Image.new("RGBA", im.size, (*rgb, round(255 * a)))
    wash.putalpha(Image.eval(im.getchannel("A"), lambda v: round(v * a)))
    out = im.copy()
    out.alpha_composite(wash)
    return out


def glow_in_cracks(im: Image.Image, src: Image.Image, rgb: tuple[int, int, int], cutoff: int, strength: float) -> Image.Image:
    """Light the source's deepest shadows from below — its crevices are exactly
    where a lava floor would show through."""
    lum = src.convert("L")
    mask = lum.point(lambda v: 0 if v >= cutoff else round(255 * strength * (cutoff - v) / cutoff))
    mask = ImageChops.multiply(mask, src.getchannel("A"))
    glow = Image.new("RGBA", im.size, (*rgb, 0))
    glow.putalpha(mask)
    out = im.copy()
    out.alpha_composite(glow)
    return out


class Theme:
    def __init__(
        self,
        ramp: Ramp,
        floor: str,
        floor_b: str,
        cap: str | None = None,
        crack: tuple[tuple[int, int, int], int, float] | None = None,
        ice: Ramp | None = None,
    ) -> None:
        self.ramp = ramp
        self.floor = floor
        self.floor_b = floor_b
        self.cap = cap or floor  # what roofs the hollow wall box
        self.crack = crack  # (rgb, cutoff, strength) lit into the floor's gaps
        self.ice = ice  # a separate ramp, so ice never reads as "just the floor"


THEMES = {
    # 白×金の大聖堂: 磨いた石畳、ハイライトだけ金に振る
    "light": Theme(
        [(0.0, (62, 55, 48)), (0.42, (188, 178, 160)), (0.74, (240, 234, 220)), (1.0, (255, 224, 152))],
        "stoneTile",
        "stoneUneven",
    ),
    # 緑×灰の苔むした遺跡: 素は平らな石、欠けた床材はアクセント側に置く
    # （全マスが欠けていると床全体が穴だらけに見える）
    "vague": Theme(
        [(0.0, (24, 32, 27)), (0.4, (72, 90, 70)), (0.72, (124, 142, 116)), (1.0, (186, 196, 176))],
        "stoneUneven",
        "stoneMissingTiles",
    ),
    # 青×白の氷の洞窟: 床を落として壁との明暗差を稼ぐ。氷は滑るという
    # ルールがあるので、床の色違いでは足りない — 彩度の高いシアンで分ける
    "cold": Theme(
        [(0.0, (14, 24, 44)), (0.42, (64, 100, 148)), (0.76, (136, 178, 216)), (1.0, (232, 248, 255))],
        "stone",
        "stoneUneven",
        ice=[(0.0, (12, 52, 82)), (0.45, (46, 148, 190)), (0.78, (126, 216, 240)), (1.0, (238, 254, 255))],
    ),
    # 紫×黄緑の腐食した工房: 板張りの床、壁は石のまま。黄緑はランプに入れず
    # 板の隙間から滲む酸として足す（ランプに入れると壁の天面まで緑一色になる）
    "cruel": Theme(
        [(0.0, (26, 15, 36)), (0.42, (84, 50, 108)), (0.72, (140, 96, 160)), (1.0, (198, 166, 208))],
        "planks",
        "planksBroken",
        cap="stone",
        crack=((150, 202, 62), 104, 0.8),
    ),
    # 黒×赤の竜の巣: ほぼ無彩色の黒岩に、割れ目の赤を後から足す
    "tight": Theme(
        [(0.0, (8, 7, 9)), (0.45, (34, 28, 30)), (0.75, (62, 50, 50)), (1.0, (94, 77, 74))],
        "stoneUneven",
        "stoneMissingTiles",
        crack=((222, 62, 18), 118, 1.0),
    ),
}


def build_theme(name: str, th: Theme) -> dict:
    src = {
        "tile.floor": raw(th.floor),
        "tile.floor.b": over(th.floor, th.floor_b),
        "tile.wall": wall_block(th.cap),
        "tile.stairs": raw("stairsSpiral"),
        "tile.door.ns": raw("stoneWallArchway", "N"),
        "tile.door.ew": raw("stoneWallArchway", "E"),
    }
    sprites = {id_: grade(im, th.ramp) for id_, im in src.items()}
    if th.ice:
        # a polished slab: its own colder ramp plus a white sheen
        sprites["tile.ice"] = tint(grade(raw("stone"), th.ice), (232, 252, 255), 0.18)
    if th.crack:
        rgb, cutoff, strength = th.crack
        for id_ in ("tile.floor", "tile.floor.b"):
            sprites[id_] = glow_in_cracks(sprites[id_], src[id_], rgb, cutoff, strength)
    out = {f"{name}.{id_}": export(im, f"{name}/{id_.removeprefix('tile.')}.png") for id_, im in sprites.items()}
    thumb = thumbnail(sprites["tile.floor"], sprites["tile.floor.b"], sprites["tile.wall"])
    out[f"thumb.{name}"] = export_centered(thumb, f"{name}/thumb.png", THUMB_W)
    return out


THUMB_W = 200  # on-screen width of a castle thumbnail


def export_centered(im: Image.Image, rel: str, width: int) -> dict:
    """For sprites the UI positions by their middle rather than a foot point."""
    bbox = im.getchannel("A").getbbox()
    if bbox is None:
        raise SystemExit(f"{rel}: fully transparent")
    cropped = im.crop(bbox)
    k = width * EXPORT / cropped.width
    out = cropped.resize((round(cropped.width * k), round(cropped.height * k)), Image.LANCZOS)
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out.save(path, optimize=True)
    return {"src": rel, "ax": round(out.width / 2, 1), "ay": round(out.height / 2, 1), "scale": round(1 / EXPORT, 4)}


def thumbnail(floor: Image.Image, floor_b: Image.Image, wall: Image.Image) -> Image.Image:
    """A 3x3 room corner, so the castle picker shows the palette rather than a
    colour swatch. Painter's order is row-major, the same as the renderer's."""
    canvas = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    cells = [(x, y) for y in range(-1, 3) for x in range(-1, 3) if x >= 0 or y >= 0 or (x, y) == (-1, -1)]
    for x, y in cells:
        edge = x < 0 or y < 0
        im = wall if edge else (floor_b if (x + y) % 3 == 1 else floor)
        dx = (x - y) * 128
        dy = (x + y) * 64
        canvas.alpha_composite(im, (512 + dx - 128, 512 + dy - 448))
    return canvas


def export(im: Image.Image, rel: str) -> dict:
    """Scale, crop to the ink, and write. Returns the manifest entry."""
    scaled = im.resize((round(im.width * K), round(im.height * K)), Image.LANCZOS)
    ax, ay = SRC_ANCHOR[0] * K, SRC_ANCHOR[1] * K
    bbox = scaled.getchannel("A").getbbox()
    if bbox is None:
        raise SystemExit(f"{rel}: fully transparent")
    cropped = scaled.crop(bbox)
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cropped.save(path, optimize=True)
    return {"src": rel, "ax": round(ax - bbox[0], 1), "ay": round(ay - bbox[1], 1), "scale": round(1 / EXPORT, 4)}


# id -> image. Kept flat so the manifest stays readable.
def build() -> dict:
    sprites = {
        "tile.floor": raw("stone"),
        "tile.floor.b": over("stone", "dirt"),
        "tile.wall": wall_block(),
        "tile.stairs": raw("stairsSpiral"),
        # archways face the two grid axes; the renderer picks by neighbouring walls
        "tile.door.ns": raw("stoneWallArchway", "N"),
        "tile.door.ew": raw("stoneWallArchway", "E"),
    }
    out = {id_: export(im, f"yukai/{id_.removeprefix('tile.')}.png") for id_, im in sprites.items()}
    thumb = thumbnail(sprites["tile.floor"], sprites["tile.floor.b"], sprites["tile.wall"])
    out["thumb.yukai"] = export_centered(thumb, "yukai/thumb.png", THUMB_W)
    return out


def main() -> None:
    if not os.path.isdir(SRC):
        sys.exit(f"missing pack: {SRC}\nsee assets/SOURCES.md for where it comes from")
    manifest_path = os.path.join(OUT, "manifest.json")
    manifest = {"version": 1, "sprites": {}}
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
    manifest["sprites"].update(build())
    for name, th in THEMES.items():
        manifest["sprites"].update(build_theme(name, th))
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {len(manifest['sprites'])} sprites to {manifest_path}")


if __name__ == "__main__":
    main()
