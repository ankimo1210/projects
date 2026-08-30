#!/usr/bin/env python3
"""Draw the three playable classes for the top-down view.

Run from the repo root (the workspace venv has Pillow):

    uv run --no-sync python monster_gate/scripts/build_heroes.py

Seen from above the camera can look at a character's back, so one side-on pose
is no longer enough. Each class is drawn in three facings — front (walking
toward the camera), back (away) and side (mirrored for the other side) — and
three poses: standing, mid-step, and swinging. That is the Mystery Dungeon
convention the original followed, and 3 x 3 is the smallest set that still
reads: eight facings would only add angles the eye cannot tell apart at 48px.

Authoring space is the style guide's 512x512 canvas with the feet at (256, 440).
Side poses face screen-left; the renderer flips them when walking right.
"""

from __future__ import annotations

import os

from paint import (
    BLACK,
    BONE,
    EYE,
    GOLD,
    LEATHER,
    PURPLE,
    RED,
    SKIN,
    STEEL,
    WOOD,
    Painter,
    darker,
    ell,
    export,
    lighter,
    merge_manifest,
    poly,
    rr,
)

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public/art")

CANVAS = 512
ANCHOR = (256, 440)
SCALE = 0.175  # canvas px -> on-screen px; ~66px tall on a 48px tile

FACINGS = ("f", "b", "s")
POSES = ("", "w", "a")  # stand, step, swing


class Pose:
    """Where the limbs go for one facing/pose pair. Coordinates are canvas px."""

    def __init__(self, facing: str, pose: str) -> None:
        self.facing = facing
        self.pose = pose
        self.step = pose == "w"
        self.swing = pose == "a"
        # a step lifts the whole figure a little; a swing leans into the blow
        self.bob = -12 if self.step else 0
        self.lean = 18 if self.swing else 0


def boots(p, ps: Pose, color=LEATHER) -> None:
    """Legs are short on a chibi, so the step has to be wide to read at 48px."""
    y = 440 + ps.bob
    if ps.facing == "s":
        lead = -40 if ps.step else (-26 if ps.swing else -14)
        back = 30 if ps.step else 18
        p.part(rr(238 + back, y - 92, 288 + back, y, 20), darker(color, 0.78))
        p.part(rr(212 + lead, y - 92 - (10 if ps.step else 0), 262 + lead, y - (10 if ps.step else 0), 20), color)
        return
    if ps.step:
        # one leg planted forward (down the screen), the other lifted behind:
        # a straddle just reads as standing wider
        p.part(rr(268, y - 74 - 22, 310, y - 22, 18), darker(color, 0.8))
        p.part(rr(202, y - 100 + 8, 248, y + 8, 20), color)
    else:
        p.part(rr(206, y - 96, 248, y, 18), color)
        p.part(rr(264, y - 96, 306, y, 18), color)


def torso(p, ps: Pose, cloth, trim=None) -> None:
    """Stops well above the feet: a tunic down to the ankles hides the walk."""
    y = ps.bob
    bottom = 356 + y
    if ps.facing == "s":
        p.part(rr(208 + ps.lean, 250 + y, 312 + ps.lean, bottom, 40), cloth)
        if trim:
            p.flat(rr(208 + ps.lean, bottom - 30, 312 + ps.lean, bottom - 12, 8), trim)
        return
    p.part(rr(194, 250 + y, 318, bottom, 42), cloth)
    if trim:
        p.flat(rr(194, bottom - 30, 318, bottom - 12, 8), trim)


def head(p, ps: Pose, skin=SKIN) -> tuple[int, int]:
    """Returns the head centre so hats and helms can sit on it."""
    y = ps.bob
    cx = 256 + (ps.lean // 2)
    cy = 172 + y
    if ps.facing == "s":
        p.part(ell(cx - 86, cy - 86, cx + 78, cy + 82), skin)
        p.part(poly((cx - 84, cy - 4), (cx - 116, cy + 16), (cx - 82, cy + 34)), skin)  # nose
    else:
        p.part(ell(cx - 86, cy - 88, cx + 86, cy + 86), skin)
    return cx, cy


def face(p, ps: Pose, cx: int, cy: int) -> None:
    """Only the front and the side have one; the back of a head is a back."""
    if ps.facing == "b":
        return
    if ps.facing == "s":
        p.flat(ell(cx - 58, cy - 6, cx - 26, cy + 32), EYE)
        p.flat(ell(cx - 50, cy + 2, cx - 38, cy + 14), (255, 255, 255))
        return
    for dx in (-32, 30):
        p.flat(ell(cx + dx - 15, cy - 6, cx + dx + 15, cy + 30), EYE)
        p.flat(ell(cx + dx - 5, cy, cx + dx + 5, cy + 12), (255, 255, 255))


def sword(p, x0: int, y0: int, horizontal: bool, flip: bool = False) -> None:
    """Blade, crossguard, grip. Upright when resting, level when swinging —
    a blade foreshortened straight at the camera just reads as a grey slab."""
    if horizontal:
        d = -1 if flip else 1
        tip = x0 + d * 150
        p.part(poly((x0 + d * 26, y0 - 17), (tip, y0 - 9), (tip, y0 + 9), (x0 + d * 26, y0 + 17)), STEEL)
        p.flat(poly((x0 + d * 26, y0 - 17), (tip, y0 - 9), (tip, y0 - 2), (x0 + d * 26, y0 - 6)), lighter(STEEL, 22))
        p.part(rr(x0 + d * 14, y0 - 34, x0 + d * 26, y0 + 34, 5) if d > 0 else rr(x0 + d * 26, y0 - 34, x0 + d * 14, y0 + 34, 5), GOLD)
        p.part(rr(x0 - 12, y0 - 11, x0 + 12, y0 + 11, 6), LEATHER)
        return
    p.part(poly((x0 - 17, y0 - 26), (x0 + 17, y0 - 26), (x0 + 9, y0 - 176), (x0 - 9, y0 - 176)), STEEL)
    p.flat(poly((x0 - 17, y0 - 26), (x0 - 6, y0 - 26), (x0 - 4, y0 - 172), (x0 - 9, y0 - 172)), lighter(STEEL, 22))
    p.part(rr(x0 - 34, y0 - 26, x0 + 34, y0 - 14, 5), GOLD)  # crossguard
    p.part(rr(x0 - 11, y0 - 14, x0 + 11, y0 + 26, 6), LEATHER)  # grip


def staff(p, x0: int, y0: int, horizontal: bool, flip: bool = False) -> None:
    if horizontal:
        d = -1 if flip else 1
        tip = x0 + d * 140
        p.part(rr(min(x0, tip), y0 - 10, max(x0, tip), y0 + 10, 8), WOOD)
        p.part(ell(tip - d * 4 - 40, y0 - 40, tip - d * 4 + 40, y0 + 40), GOLD)
        return
    p.part(rr(x0 - 11, y0 - 186, x0 + 11, y0 + 30, 9), WOOD)
    p.part(ell(x0 - 40, y0 - 226, x0 + 40, y0 - 146), GOLD)


def dagger(p, x0: int, y0: int, horizontal: bool, flip: bool = False) -> None:
    if horizontal:
        d = -1 if flip else 1
        tip = x0 + d * 108
        p.part(poly((x0 + d * 18, y0 - 14), (tip, y0 - 6), (tip, y0 + 6), (x0 + d * 18, y0 + 14)), BONE)
        p.part(rr(x0 - 11, y0 - 10, x0 + 11, y0 + 10, 5), GOLD)
        return
    p.part(poly((x0 - 14, y0 - 20), (x0 + 14, y0 - 20), (x0 + 7, y0 - 128), (x0 - 7, y0 - 128)), BONE)
    p.part(rr(x0 - 24, y0 - 22, x0 + 24, y0 - 10, 5), GOLD)
    p.part(rr(x0 - 10, y0 - 10, x0 + 10, y0 + 22, 5), BLACK)


def weapon_arm(p, ps: Pose, sleeve, blade) -> None:
    """`blade(x, y, horizontal, flip)` paints whatever this class swings."""
    y = ps.bob
    if ps.facing == "s":
        if ps.swing:
            p.part(rr(150, 272 + y, 236, 316 + y, 22), sleeve)
            blade(150, 294 + y, True, True)
        else:
            p.part(rr(178, 264 + y, 222, 344 + y, 20), sleeve)
            blade(200, 300 + y, False, False)
        return
    side = 1 if ps.facing == "f" else -1
    hx = 256 + side * 100
    if ps.swing:
        p.part(rr(min(hx, hx + side * 60) - 26, 288 + y, max(hx, hx + side * 60) + 26, 332 + y, 22), sleeve)
        blade(hx + side * 60, 310 + y, True, side < 0)
    else:
        p.part(rr(hx - 26, 264 + y, hx + 26, 348 + y, 22), sleeve)
        blade(hx, 320 + y, False, False)


def off_arm(p, ps: Pose, sleeve, shield=None) -> None:
    y = ps.bob
    if ps.facing == "s":
        if shield:
            p.part(ell(292, 254 + y, 396, 358 + y), shield)  # slung on the far side
            p.flat(ell(330, 292 + y, 362, 322 + y), RED)
        return
    side = -1 if ps.facing == "f" else 1
    hx = 256 + side * 100
    p.part(rr(hx - 26, 264 + y, hx + 26, 348 + y, 22), sleeve)
    if shield:
        p.part(ell(hx - 60, 248 + y, hx + 60, 366 + y), shield)
        p.flat(ell(hx - 21, 288 + y, hx + 21, 330 + y), RED)


# ---- the three classes -----------------------------------------------------


def warrior(p, ps: Pose) -> None:
    """Plate helm with a red plume, red surcoat, broadsword and round shield —
    the original's starter knight."""
    boots(p, ps)
    torso(p, ps, RED, LEATHER)
    off_arm(p, ps, RED, STEEL)
    weapon_arm(p, ps, RED, lambda x, y, h, fl: sword(p, x, y, h, fl))
    cx, cy = head(p, ps, STEEL if ps.facing == "b" else SKIN)
    face(p, ps, cx, cy)
    # helm: a brow band across the head, open at the face on the front
    if ps.facing == "b":
        p.flat(rr(cx - 84, cy - 26, cx + 84, cy - 8, 6), darker(STEEL, 0.82))  # helm seam
    elif ps.facing == "s":
        p.part(poly((cx - 96, cy - 14), (cx + 86, cy - 14), (cx + 76, cy - 70), (cx - 6, cy - 106), (cx - 88, cy - 62)), STEEL)
    else:
        p.part(poly((cx - 92, cy - 18), (cx + 92, cy - 18), (cx + 82, cy - 72), (cx, cy - 108), (cx - 82, cy - 72)), STEEL)
    p.part(poly((cx - 12, cy - 100), (cx + 14, cy - 100), (cx + 26, cy - 168), (cx - 24, cy - 156)), RED)  # plume
    p.part(rr(cx - 96, cy + 78, cx + 96, cy + 104, 12), STEEL)  # gorget


def mage(p, ps: Pose) -> None:
    boots(p, ps, BLACK)
    torso(p, ps, PURPLE, GOLD)
    off_arm(p, ps, PURPLE)
    weapon_arm(p, ps, PURPLE, lambda x, y, h, fl: staff(p, x, y, h, fl))
    cx, cy = head(p, ps)
    face(p, ps, cx, cy)
    if ps.facing != "b":
        p.part(ell(cx - 66, cy + 40, cx + 66, cy + 112), BONE)  # beard
    p.part(poly((cx - 104, cy - 30), (cx + 104, cy - 30), (cx - 10, cy - 190)), PURPLE)  # hat
    p.flat(poly((cx - 104, cy - 30), (cx + 104, cy - 30), (cx + 96, cy - 56), (cx - 96, cy - 56)), GOLD)


def gambler(p, ps: Pose) -> None:
    boots(p, ps, BLACK)
    torso(p, ps, BLACK, GOLD)
    off_arm(p, ps, BLACK)
    weapon_arm(p, ps, BLACK, lambda x, y, h, fl: dagger(p, x, y, h, fl))
    cx, cy = head(p, ps)
    face(p, ps, cx, cy)
    p.part(ell(cx - 130, cy - 62, cx + 130, cy - 6), BLACK)  # brim
    p.part(rr(cx - 62, cy - 132, cx + 62, cy - 40, 16), BLACK)  # crown
    p.flat(rr(cx - 62, cy - 62, cx + 62, cy - 42, 6), GOLD)


CLASSES = {"class.warrior": warrior, "class.mage": mage, "class.gambler": gambler}


def main() -> None:
    entries = {}
    for id_, build in CLASSES.items():
        for facing in FACINGS:
            for pose in POSES:
                p = Painter(CANVAS)
                build(p, Pose(facing, pose))
                sid = f"{id_}.{facing}" + (f".{pose}" if pose else "")
                rel = f"chars/{id_.replace('.', '-')}-{facing}{pose}.png"
                entries[sid] = export(p.finish(), OUT, rel, ANCHOR, SCALE)
    total = merge_manifest(OUT, entries)
    print(f"drew {len(entries)} hero sprites; manifest now has {total} sprites")


if __name__ == "__main__":
    main()
