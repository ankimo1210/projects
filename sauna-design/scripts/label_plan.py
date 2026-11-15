#!/usr/bin/env python3
"""Overlay room names from plan/plan_a.json on the rendered top view (sauna_plan_v3.png -> sauna_plan_v3_labeled.png).

The label image is an annotation of the Cycles render, not a separate drawing. Uses Pillow only.
"""

import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent.parent
DATA = (
    pathlib.Path(sys.argv[1])
    if len(sys.argv) > 1
    else HERE.parent / "_data" / "sauna-design" / "fable-v3"
)
ORTHO_SCALE, CENTER = 21.5, (10.0, 7.0)  # must match Cam_plan in blender/build.py
FONTS = [
    "/mnt/c/Windows/Fonts/YuGothM.ttc",
    "/mnt/c/Windows/Fonts/meiryo.ttc",
    "/mnt/c/Windows/Fonts/msgothic.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

plan = json.loads((HERE / "plan" / "plan_a.json").read_text(encoding="utf-8"))
im = Image.open(DATA / "renders" / "sauna_plan_v3.png").convert("RGB")
ppm = im.width / ORTHO_SCALE
font = None
for f in FONTS:
    if pathlib.Path(f).exists():
        font = ImageFont.truetype(f, 30)
        small = ImageFont.truetype(f, 22)
        break
if font is None:
    sys.exit("no Japanese font found; labels skipped")
d = ImageDraw.Draw(im)
for r in plan["rooms"]:
    x, y, w, h = r["rect"]
    cx = im.width / 2 + (x + w / 2 - CENTER[0]) * ppm
    cy = im.height / 2 - (y + h / 2 - CENTER[1]) * ppm
    for text, fnt, dy in (
        (r["name"], font, -18),
        (f"{w:g}×{h:g} m・天井{r['ceiling']:g} m（仮）", small, 20),
    ):
        box = d.textbbox((0, 0), text, font=fnt)
        tw, th = box[2] - box[0], box[3] - box[1]
        if tw > w * ppm - 10:  # narrow rooms: keep the name only, wrapped
            if fnt is small:
                continue
            text = text.replace("・", "\n")
            box = d.multiline_textbbox((0, 0), text, font=fnt)
            tw, th = box[2] - box[0], box[3] - box[1]
        d.multiline_text(
            (cx - tw / 2, cy + dy - th / 2),
            text,
            font=fnt,
            fill=(255, 244, 226),
            stroke_width=4,
            stroke_fill=(20, 16, 12),
            align="center",
        )
out = DATA / "renders" / "sauna_plan_v3_labeled.png"
im.save(out)
print(out)
