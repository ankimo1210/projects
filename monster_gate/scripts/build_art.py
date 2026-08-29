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

from PIL import Image

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


def wall_block() -> Image.Image:
    """The pack has no full-cell wall: its walls sit on tile edges. Two opposite
    corner pieces close all four sides, and a floor tile roofs the hollow top."""
    im = raw("stoneWallCorner", "E").copy()
    im.alpha_composite(raw("stoneWallCorner", "W"))
    im.alpha_composite(raw("stone"), (0, -WALL_CAP_DY))
    return im


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
        "tile.floor.b": raw("dirt"),
        "tile.wall": wall_block(),
        "tile.stairs": raw("stairsSpiral"),
        # archways face the two grid axes; the renderer picks by neighbouring walls
        "tile.door.ns": raw("stoneWallArchway", "N"),
        "tile.door.ew": raw("stoneWallArchway", "E"),
    }
    return {id_: export(im, f"yukai/{id_.removeprefix('tile.')}.png") for id_, im in sprites.items()}


def main() -> None:
    if not os.path.isdir(SRC):
        sys.exit(f"missing pack: {SRC}\nsee assets/SOURCES.md for where it comes from")
    manifest_path = os.path.join(OUT, "manifest.json")
    manifest = {"version": 1, "sprites": {}}
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
    manifest["sprites"].update(build())
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {len(manifest['sprites'])} sprites to {manifest_path}")


if __name__ == "__main__":
    main()
