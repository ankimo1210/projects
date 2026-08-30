#!/usr/bin/env python3
"""Draw the monsters into public/art/chars/. The three playable classes have
their own facings and poses and live in build_heroes.py.

Run from the repo root (the workspace venv has Pillow):

    uv run --no-sync python monster_gate/scripts/build_chars.py

These are drawn, not generated: flat fills, one shadow step lit from the upper
right, and a thick dark rim — the look docs/style-guide.md asks for. Each sprite
is an independent manifest entry, so any one of them can later be replaced by a
hand-made or AI-generated PNG without touching the others or the code.

Authoring space is the style guide's 512x512 canvas with the feet at (256, 440)
and the character facing screen-left; the renderer flips it when walking right.
"""

from __future__ import annotations

import os

from paint import (
    BONE,
    DRAGON,
    EYE,
    GREEN,
    LEATHER,
    PURPLE,
    SKIN_G,
    STEEL,
    WHITE,
    WOOD,
    YELLOW,
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
SCALE = 0.15  # canvas px -> on-screen px; ~57px tall on a 48px tile


# ---- the cast --------------------------------------------------------------
# Each builder paints back to front. Coordinates are the 512 canvas; the figure
# faces screen-left, so faces and held items sit on the left half.


def eyes(p, cx, cy, r=15, gap=44, pupil=EYE):
    for dx in (-gap // 2, gap // 2):
        p.flat(ell(cx + dx - r, cy - r, cx + dx + r, cy + r), WHITE)
        p.flat(ell(cx + dx - r + 3, cy - r + 4, cx + dx + r - 6, cy + r - 2), pupil)








def slime(p, body, big=False, angry=False):
    t = -26 if big else 0
    p.part(ell(96, 210 + t, 416, 442), body)  # blob
    p.flat(ell(150, 250 + t, 230, 300 + t), lighter(body))  # sheen
    eyes(p, 214, 320 + t, r=30, gap=104)
    if angry:
        for x0, x1 in ((150, 216), (232, 298)):
            p.flat(poly((x0, 262 + t), (x1, 286 + t), (x1, 300 + t), (x0, 276 + t)), EYE)
    p.flat(rr(196, 372 + t, 258, 386 + t, 7), EYE)  # mouth


def killerbee(p):
    p.part(poly((252, 230), (334, 138), (372, 186), (290, 256)), (214, 226, 242))  # wings
    p.part(poly((224, 244), (288, 134), (332, 174), (258, 266)), (236, 243, 251))
    p.part(ell(150, 236, 400, 420), YELLOW)  # abdomen
    p.flat(ell(238, 256, 278, 400), EYE)  # stripes, kept inside the body
    p.flat(ell(306, 262, 346, 394), EYE)
    p.part(poly((396, 306), (466, 328), (396, 350)), EYE)  # stinger
    p.part(ell(110, 210, 268, 368), YELLOW)  # head
    for dx in (0, 62):  # compound eyes
        p.flat(ell(134 + dx, 250, 186 + dx, 314), EYE)
        p.flat(ell(144 + dx, 258, 162 + dx, 278), WHITE)
    p.part(rr(128, 130, 142, 214, 7), EYE)  # antennae
    p.part(rr(196, 122, 210, 206, 7), EYE)


def skeleton(p):
    p.part(rr(214, 348, 250, 442, 15), BONE)  # legs
    p.part(rr(266, 348, 302, 442, 15), BONE)
    p.part(rr(196, 246, 320, 366, 40), BONE)  # ribcage
    for y in (272, 302, 332):
        p.flat(rr(206, y, 310, y + 12, 6), (176, 172, 158))
    p.part(rr(310, 250, 346, 330, 16), BONE)  # far arm
    p.part(poly((332, 258), (392, 140), (410, 152), (350, 270)), STEEL)  # sword
    p.part(ell(160, 92, 352, 274), BONE)  # skull
    p.flat(ell(190, 168, 244, 226), EYE)  # sockets
    p.flat(ell(258, 168, 312, 226), EYE)
    p.flat(poly((240, 232), (274, 232), (257, 258)), EYE)  # nose
    for x in (196, 224, 252, 280):
        p.flat(rr(x, 262, x + 18, 278, 4), (176, 172, 158))
    p.part(rr(166, 254, 202, 340, 16), BONE)  # near arm


def kemunpa(p):
    for i, x in enumerate((330, 268, 206)):  # body segments, back to front
        r = 62 + i * 4
        p.part(ell(x - r, 300 - r, x + r, 300 + r), darker(GREEN, 0.86 + i * 0.05))
    p.part(ell(52, 194, 264, 406), GREEN)  # head
    eyes(p, 138, 268, r=28, gap=96)
    p.flat(poly((84, 330), (206, 330), (196, 372), (94, 372)), EYE)  # wide mouth
    p.flat(poly((100, 330), (124, 356), (148, 330)), WHITE)  # fang
    p.flat(poly((160, 330), (184, 356), (208, 330)), WHITE)
    for x in (218, 288, 350):  # legs
        p.part(rr(x, 372, x + 22, 434, 10), darker(GREEN, 0.7))
    p.part(rr(96, 148, 110, 204, 7), EYE)  # antennae
    p.part(rr(168, 140, 182, 200, 7), EYE)


def goblin(p):
    p.part(rr(212, 356, 252, 442, 17), LEATHER)  # feet
    p.part(rr(268, 356, 308, 442, 17), LEATHER)
    p.part(rr(190, 250, 324, 376, 44), LEATHER)  # vest
    p.flat(rr(190, 296, 324, 312, 6), darker(LEATHER, 0.7))
    p.part(rr(302, 246, 348, 340, 20), SKIN_G)  # far arm
    p.part(rr(330, 116, 356, 264, 12), WOOD)  # club
    p.part(ell(316, 84, 396, 158), WOOD)
    p.part(ell(160, 96, 348, 272), SKIN_G)  # head
    p.part(poly((172, 150), (96, 92), (128, 194)), SKIN_G)  # ears
    p.part(poly((334, 150), (410, 96), (378, 194)), SKIN_G)
    eyes(p, 226, 176, r=17, pupil=(180, 40, 30))
    p.flat(poly((186, 226), (300, 226), (290, 254), (196, 254)), EYE)  # grin
    p.flat(poly((196, 226), (216, 250), (236, 226)), WHITE)
    p.flat(poly((252, 226), (272, 250), (292, 226)), WHITE)
    p.part(rr(166, 252, 210, 344, 20), SKIN_G)  # near arm


def darkmage(p):
    p.part(poly((168, 262), (344, 262), (376, 442), (136, 442)), (58, 44, 96))  # robe
    p.flat(poly((150, 420), (362, 420), (368, 442), (144, 442)), PURPLE)
    p.part(poly((256, 44), (368, 210), (340, 300), (172, 300), (144, 210)), (72, 54, 118))  # hood
    p.flat(ell(178, 150, 334, 300), (16, 12, 26))  # shadowed face
    for dx in (-38, 26):
        p.flat(ell(238 + dx, 208, 268 + dx, 238), (196, 120, 255))  # glowing eyes
    p.part(rr(160, 300, 206, 380, 20), (72, 54, 118))  # sleeve
    p.part(ell(88, 300, 188, 400), (170, 96, 240))  # orb
    p.flat(ell(110, 320, 146, 350), (226, 190, 255))


def dragon(p):
    p.part(poly((300, 250), (452, 96), (470, 210), (352, 300)), darker(DRAGON, 0.62))  # wings
    p.part(poly((262, 262), (400, 78), (424, 196), (312, 300)), darker(DRAGON, 0.78))
    p.part(poly((340, 380), (486, 336), (492, 372), (360, 424)), DRAGON)  # tail
    p.part(ell(150, 236, 402, 442), DRAGON)  # body
    p.flat(ell(196, 320, 336, 430), (240, 176, 132))  # belly
    p.part(rr(196, 384, 244, 442, 20), darker(DRAGON, 0.8))  # legs
    p.part(rr(282, 384, 330, 442, 20), darker(DRAGON, 0.8))
    p.part(rr(196, 168, 292, 300, 42), DRAGON)  # neck
    p.part(ell(96, 76, 314, 268), DRAGON)  # head
    p.part(ell(44, 150, 176, 252), DRAGON)  # snout
    p.flat(ell(66, 178, 92, 200), EYE)  # nostril
    eyes(p, 190, 148, r=22, gap=76, pupil=(232, 196, 60))
    for dx in (0, 58):  # horns
        p.part(poly((214 + dx, 92), (250 + dx, 8), (262 + dx, 96)), BONE)
    p.flat(poly((54, 224), (150, 224), (140, 252), (64, 252)), EYE)  # mouth
    p.flat(poly((62, 224), (78, 248), (94, 224)), WHITE)
    p.flat(poly((108, 224), (124, 248), (140, 224)), WHITE)


CAST = {
    "enemy.puunya_g": lambda p: slime(p, GREEN),
    "enemy.puunya_y": lambda p: slime(p, YELLOW, big=True, angry=True),
    "enemy.killerbee": killerbee,
    "enemy.skeleton": skeleton,
    "enemy.kemunpa": kemunpa,
    "enemy.goblin": goblin,
    "enemy.mage": darkmage,
    "enemy.dragon": dragon,
}


def main() -> None:
    entries = {}
    for id_, build in CAST.items():
        p = Painter(CANVAS)
        build(p)
        entries[id_] = export(p.finish(), OUT, f"chars/{id_.replace('.', '-')}.png", ANCHOR, SCALE)
    total = merge_manifest(OUT, entries)
    print(f"drew {len(entries)} characters; manifest now has {total} sprites")


if __name__ == "__main__":
    main()
