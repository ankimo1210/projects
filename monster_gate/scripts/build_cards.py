#!/usr/bin/env python3
"""Draw the card illustrations into public/art/cards/.

    uv run --no-sync python monster_gate/scripts/build_cards.py

One icon per card, centred in a 256x256 canvas (anchor at the centre, not the
feet — these are emblems on a card face, not figures standing on the ground).
The frame, name, cost and range marks are drawn by src/ui/render/card-face.ts;
this only supplies the picture.
"""

from __future__ import annotations

import math
import os

from paint import (
    BLUE,
    BONE,
    DRAGON,
    EYE,
    GOLD,
    GREEN,
    LEATHER,
    PURPLE,
    RED,
    SKIN_G,
    STEEL,
    WHITE,
    WOOD,
    YELLOW,
    Painter,
    darker,
    ell,
    export,
    merge_manifest,
    poly,
    rr,
)

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public/art")

CANVAS = 256
ANCHOR = (128, 128)
SCALE = 1.0  # the card face scales it to whatever box it has
RIM = 4

FLAME = (250, 140, 40)


def flame(p, cx, cy, w, h, color=FLAME):
    p.part(poly((cx, cy - h), (cx + w, cy + h // 3), (cx + w // 2, cy + h), (cx - w // 2, cy + h), (cx - w, cy + h // 3)), color)
    p.flat(poly((cx, cy - h // 3), (cx + w // 3, cy + h // 2), (cx - w // 3, cy + h // 2)), GOLD)


def bolt(p, cx, cy, s, color=YELLOW):
    p.part(
        poly(
            (cx + s // 3, cy - s),
            (cx - s // 2, cy + s // 6),
            (cx, cy + s // 6),
            (cx - s // 3, cy + s),
            (cx + s // 2, cy - s // 5),
            (cx, cy - s // 5),
        ),
        color,
    )


def swirl(p, cx, cy, r, color=PURPLE):
    """A hypnotic spiral ribbon — confusion, and clearly not the warp portal."""
    turns, width, steps = 2.4, max(8, r * 0.26), 96
    outer, inner = [], []
    for i in range(steps + 1):
        t = i / steps * turns * 2 * math.pi
        rad = r * (i / steps)
        outer.append((cx + math.cos(t) * (rad + width / 2), cy + math.sin(t) * (rad + width / 2)))
        inner.append((cx + math.cos(t) * max(0.0, rad - width / 2), cy + math.sin(t) * max(0.0, rad - width / 2)))
    p.part(poly(*outer, *inner[::-1]), color)


def zed(p, x, y, s, color=WHITE):
    """A block letter Z, for the sleep icon."""
    t = s * 0.3
    p.part(poly((x, y), (x + s, y), (x + s, y + t), (x + t, y + s - t), (x + s, y + s - t), (x + s, y + s), (x, y + s), (x, y + s - t), (x + s - t, y + t), (x, y + t)), color)


def blade(p, tip_y, hilt_y, w, color=STEEL):
    cx = 128
    p.part(poly((cx, tip_y), (cx + w, tip_y + 34), (cx + w, hilt_y), (cx - w, hilt_y), (cx - w, tip_y + 34)), color)
    p.part(rr(cx - 52, hilt_y, cx + 52, hilt_y + 20, 9), GOLD)  # guard
    p.part(rr(cx - 13, hilt_y + 18, cx + 13, hilt_y + 66, 11), LEATHER)  # grip
    p.part(ell(cx - 20, hilt_y + 58, cx + 20, hilt_y + 96), GOLD)  # pommel


# ---- the icons -------------------------------------------------------------
def potion(p):
    p.part(rr(96, 44, 160, 76, 10), STEEL)  # cork
    p.part(poly((104, 74), (152, 74), (196, 150), (196, 208), (60, 208), (60, 150)), (214, 232, 240))  # glass
    p.flat(poly((70, 150), (186, 150), (186, 200), (70, 200)), GREEN)  # liquid
    p.flat(ell(84, 96, 108, 140), WHITE)  # highlight


def regen(p):
    p.part(poly((128, 210), (36, 118), (36, 84), (72, 52), (128, 84), (184, 52), (220, 84), (220, 118)), (86, 200, 110))
    for x, y, r in ((60, 70, 12), (200, 74, 10), (128, 34, 9)):
        p.flat(ell(x - r, y - r, x + r, y + r), WHITE)


def fire(p):
    flame(p, 128, 130, 74, 92)


def multi_fire(p):
    flame(p, 62, 156, 44, 56)
    flame(p, 196, 156, 44, 56)
    flame(p, 128, 116, 56, 74)


def meteor(p):
    p.part(poly((196, 32), (236, 76), (150, 150), (108, 108)), FLAME)  # trail
    p.part(ell(46, 110, 178, 236), (110, 96, 96))  # rock
    for x, y, r in ((84, 150, 14), (128, 190, 11), (132, 142, 9)):
        p.flat(ell(x - r, y - r, x + r, y + r), (78, 68, 70))


def thunder(p):
    bolt(p, 128, 128, 96)


def multi_thunder(p):
    p.part(ell(40, 40, 216, 128), (206, 214, 228))  # cloud
    p.part(ell(24, 62, 128, 130), (222, 228, 240))
    bolt(p, 84, 176, 52)
    bolt(p, 176, 176, 52)


def sleep(p):
    p.part(poly((10, 168), (118, 100), (226, 168), (118, 236)), (240, 236, 226))  # eye
    p.flat(poly((26, 168), (210, 168), (118, 216)), (150, 146, 160))  # lowered lid
    p.flat(rr(26, 162, 210, 174, 6), EYE)  # lash line
    zed(p, 132, 46, 44)  # Zzz
    zed(p, 190, 8, 32)


def panic(p):
    swirl(p, 128, 128, 88)


def multi_panic(p):
    swirl(p, 66, 168, 50)
    swirl(p, 190, 168, 50)
    swirl(p, 128, 78, 56)


def bright(p):
    p.part(rr(112, 20, 144, 46, 8), STEEL)  # handle
    p.part(poly((72, 60), (184, 60), (206, 200), (50, 200)), GOLD)  # lantern body
    p.flat(poly((92, 78), (164, 78), (180, 182), (76, 182)), WHITE)
    p.part(rr(44, 196, 212, 222, 10), STEEL)


def search(p):
    p.part(poly((16, 128), (128, 44), (240, 128), (128, 212)), WHITE)  # eye
    p.part(ell(84, 84, 172, 172), BLUE)  # iris
    p.flat(ell(106, 106, 150, 150), EYE)
    p.flat(ell(112, 108, 130, 126), WHITE)


def cardmap(p):
    p.part(rr(30, 52, 226, 204, 14), (238, 226, 190))  # parchment
    for y in (88, 122, 156):
        p.flat(rr(56, y, 200, y + 10, 5), (176, 158, 124))
    p.part(ell(150, 140, 190, 180), RED)  # marker
    p.flat(poly((60, 70), (110, 106), (86, 140), (52, 108)), (170, 196, 150))


def warp(p):
    """A flat oval portal — reads as a hole in space, unlike the panic spiral."""
    for i, (r, col) in enumerate(((110, (36, 58, 140)), (84, BLUE), (56, (120, 190, 255)), (26, WHITE))):
        p.part(ell(128 - r, 128 - r * 0.7, 128 + r, 128 + r * 0.7), col, rim=(i == 0), shade=(i == 0))


def escape(p):
    p.part(rr(58, 30, 198, 216, 14), WOOD)  # door
    p.flat(rr(78, 50, 178, 196, 8), darker(WOOD, 0.8))
    p.part(ell(150, 118, 174, 142), GOLD)  # knob
    p.part(poly((196, 128), (250, 100), (250, 156)), GREEN)  # exit arrow


def haste(p):
    p.part(poly((70, 196), (70, 96), (128, 96), (156, 140), (206, 158), (206, 196)), LEATHER)  # boot
    p.flat(rr(70, 176, 206, 196, 8), darker(LEATHER, 0.7))
    p.part(poly((66, 92), (10, 40), (36, 106), (0, 96)), WHITE)  # wing
    p.part(poly((132, 84), (100, 22), (166, 62), (172, 30)), WHITE)


def bronze_sword(p):
    blade(p, 40, 150, 26, (198, 142, 74))


def long_sword(p):
    blade(p, 14, 176, 24, STEEL)


def power_shield(p):
    p.part(poly((128, 26), (222, 66), (222, 140), (128, 230), (34, 140), (34, 66)), STEEL)
    p.flat(poly((128, 58), (192, 84), (192, 136), (128, 196), (64, 136), (64, 84)), BLUE)
    p.flat(poly((128, 84), (166, 100), (166, 132), (128, 168), (90, 132), (90, 100)), WHITE)


def power_up(p):
    p.part(poly((128, 18), (222, 122), (172, 122), (172, 214), (84, 214), (84, 122), (34, 122)), (255, 176, 60))
    p.flat(poly((128, 60), (176, 112), (152, 112), (152, 190), (104, 190), (104, 112), (80, 112)), GOLD)


def pocket(p):
    p.part(poly((60, 96), (196, 96), (222, 196), (196, 226), (60, 226), (34, 196)), LEATHER)  # pouch
    p.part(rr(74, 74, 182, 104, 14), (168, 122, 76))  # neck
    p.flat(rr(50, 150, 206, 168, 8), darker(LEATHER, 0.66))  # cord
    p.part(rr(116, 34, 140, 92, 11), GOLD)  # a "+2" of coins peeking out
    p.part(ell(150, 40, 200, 90), GOLD)


def revive_ring(p):
    p.part(ell(44, 78, 212, 230), GOLD)
    p.flat(ell(80, 112, 176, 200), (44, 36, 56))
    p.part(poly((128, 20), (166, 66), (128, 106), (90, 66)), (120, 220, 255))  # gem


def summon_goblin(p):
    p.part(ell(52, 56, 204, 208), SKIN_G)  # head
    p.part(poly((64, 108), (0, 58), (26, 148)), SKIN_G)  # ears
    p.part(poly((192, 108), (256, 58), (230, 148)), SKIN_G)
    for dx in (0, 62):
        p.flat(ell(76 + dx, 108, 112 + dx, 144), WHITE)
        p.flat(ell(84 + dx, 116, 106 + dx, 138), (180, 40, 30))
    p.flat(poly((74, 156), (182, 156), (172, 186), (84, 186)), EYE)  # grin
    p.flat(poly((84, 156), (102, 180), (120, 156)), WHITE)
    p.flat(poly((136, 156), (154, 180), (172, 156)), WHITE)


def summon_dragon(p):
    p.part(poly((60, 60), (96, 0), (110, 66)), BONE)  # horns
    p.part(poly((146, 62), (182, 4), (196, 68)), BONE)
    p.part(ell(40, 40, 216, 200), DRAGON)  # head
    p.part(ell(6, 108, 130, 208), DRAGON)  # snout
    p.flat(ell(28, 132, 52, 154), EYE)  # nostril
    for dx in (0, 66):
        p.flat(ell(86 + dx, 88, 122 + dx, 128), WHITE)
        p.flat(ell(94 + dx, 96, 116 + dx, 122), (232, 196, 60))
    p.flat(poly((16, 176), (110, 176), (100, 202), (26, 202)), EYE)  # mouth
    p.flat(poly((24, 176), (40, 198), (56, 176)), WHITE)
    p.flat(poly((68, 176), (84, 198), (100, 176)), WHITE)


ICONS = {
    "potion20": potion,
    "potion40": potion,
    "potion80": potion,
    "regen": regen,
    "fire": fire,
    "multiFire": multi_fire,
    "meteor": meteor,
    "thunder": thunder,
    "multiThunder": multi_thunder,
    "sleep": sleep,
    "panic": panic,
    "multiPanic": multi_panic,
    "bright": bright,
    "search": search,
    "map": cardmap,
    "warp": warp,
    "escape": escape,
    "haste": haste,
    "bronzeSword": bronze_sword,
    "longSword": long_sword,
    "powerShield": power_shield,
    "powerUp": power_up,
    "pocket2": pocket,
    "reviveRing": revive_ring,
    "summonGoblin": summon_goblin,
    "summonDragon": summon_dragon,
}


def main() -> None:
    entries = {}
    drawn: dict[str, str] = {}  # builder name -> file already written, so potions share one picture
    for card, build in ICONS.items():
        key = build.__name__
        if key not in drawn:
            p = Painter(CANVAS, rim=RIM)
            build(p)
            drawn[key] = f"cards/{key}.png"
            entries[f"card.{card}"] = export(p.finish(), OUT, drawn[key], ANCHOR, SCALE)
        else:
            entries[f"card.{card}"] = dict(entries[f"card.{next(c for c, b in ICONS.items() if b.__name__ == key)}"])
    total = merge_manifest(OUT, entries)
    print(f"drew {len(set(b.__name__ for b in ICONS.values()))} icons for {len(ICONS)} cards; manifest now has {total} sprites")


if __name__ == "__main__":
    main()
