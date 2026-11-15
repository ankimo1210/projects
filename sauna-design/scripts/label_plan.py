#!/usr/bin/env python3
"""Overlay room names from plan/plan_a.json on the rendered top view (sauna_plan_v6.png -> sauna_plan_v6_labeled.png).

The label image is an annotation of the Cycles render, not a separate drawing. Uses Pillow only.
"""

import sys

sys.dont_write_bytecode = True
import json  # noqa: E402
import pathlib  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

V = "v6"
HERE = pathlib.Path(__file__).resolve().parent.parent
DATA = (
    pathlib.Path(sys.argv[1])
    if len(sys.argv) > 1
    else pathlib.Path(f"/home/kazumasa/projects/_data/sauna-design/fable-{V}")
)
ORTHO_SCALE, CENTER = 21.5, (10.0, 7.0)  # must match Cam_plan in blender/build.py
FONTS = [
    "/mnt/c/Windows/Fonts/YuGothM.ttc",
    "/mnt/c/Windows/Fonts/meiryo.ttc",
    "/mnt/c/Windows/Fonts/msgothic.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]
# notes on the plan: (text, marked point x, y, label x, y) in plan metres
MARKS = [
    ("TV（東壁・ガラス越し）", 12.45, 12.75, 11.0, 13.62),
    ("造り付け席 2席", 16.72, 9.35, 15.45, 10.12),
    ("扉", 18.45, 7.0, 18.5, 7.42),
    ("扉", 18.45, 10.0, 18.5, 9.58),
    ("休憩 15席（寝台6・壁向き5・縦列4）", 3.0, 4.9, 3.0, 3.86),
    # v6: main sauna with the stove in the middle, spare perch seats in the bath, towel pegs in the rest area
    ("ストーブ（中央）と柵", 3.0, 10.95, 3.0, 9.55),
    ("上り口：中間段→足置き段", 4.75, 11.2, 4.85, 9.98),
    ("踊り場", 1.36, 12.74, 2.05, 12.2),
    ("予備の腰掛け 3席", 13.81, 10.6, 13.8, 9.98),
    ("席ごとのタオル掛け", 3.34, 5.94, 1.25, 6.92),
]
NAME_AT = {"main": (3.0, 13.55)}  # room name moved off the stove

plan = json.loads((HERE / "plan" / "plan_a.json").read_text(encoding="utf-8"))
im = Image.open(DATA / "renders" / f"sauna_plan_{V}.png").convert("RGB")
ppm = im.width / ORTHO_SCALE
font = None
for f in FONTS:
    if pathlib.Path(f).exists():
        font = ImageFont.truetype(f, 30)
        small = ImageFont.truetype(f, 22)
        tiny = ImageFont.truetype(f, 19)
        break
if font is None:
    sys.exit("no Japanese font found; labels skipped")


def px(x, y):
    return im.width / 2 + (x - CENTER[0]) * ppm, im.height / 2 - (y - CENTER[1]) * ppm


d = ImageDraw.Draw(im)
for r in plan["rooms"]:
    x, y, w, h = r["rect"]
    cx, cy = px(*NAME_AT.get(r["id"], (x + w / 2, y + h / 2)))
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
for text, mx, my, tx, ty in MARKS:
    (ax, ay), (bx, by) = px(mx, my), px(tx, ty)
    d.line([(ax, ay), (bx, by)], fill=(120, 226, 214), width=2)
    d.ellipse([ax - 6, ay - 6, ax + 6, ay + 6], fill=(120, 226, 214), outline=(20, 16, 12))
    box = d.textbbox((0, 0), text, font=tiny)
    tw, th = box[2] - box[0], box[3] - box[1]
    d.text(
        (bx - tw / 2, by - th / 2 - 4),
        text,
        font=tiny,
        fill=(170, 240, 230),
        stroke_width=4,
        stroke_fill=(20, 16, 12),
    )
out = DATA / "renders" / f"sauna_plan_{V}_labeled.png"
im.save(out)
print(out)
