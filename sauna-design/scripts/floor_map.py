#!/usr/bin/env python3
"""Publish a numbered floor map from the saved v8 model's orthographic render.

No room or furniture geometry is drawn independently of the native model.
The scale and centre must match Cam_plan in blender/build.py.
"""

import hashlib
import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent.parent
DATA = (
    pathlib.Path(sys.argv[1])
    if len(sys.argv) > 1
    else pathlib.Path("/home/kazumasa/projects/_data/sauna-design/fable-v8")
)
if DATA.name != "fable-v8":
    raise SystemExit("Only the current v8 output root is supported")
PLAN = json.loads((HERE / "plan/plan_a.json").read_text(encoding="utf-8"))
assert (PLAN["width"], PLAN["height"]) == (20, 14)
font_path = next(
    p
    for p in (
        "/mnt/c/Windows/Fonts/YuGothM.ttc",
        "/mnt/c/Windows/Fonts/meiryo.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    )
    if pathlib.Path(p).exists()
)
font = lambda size: ImageFont.truetype(font_path, size)
BG, INK, MUTED = "#f4f0e8", "#302d28", "#746f66"
GROUP = {
    "front": "#716c60",
    "rest": "#587263",
    "sauna": "#a16e45",
    "water": "#4d7c88",
    "back": "#787875",
}
im = Image.new("RGB", (3300, 2050), BG)
draw = ImageDraw.Draw(im)
raw = Image.open(DATA / "renders/sauna_plan_v8.png").convert("RGB")
assert raw.size == (2400, 1600), raw.size
offset = (65, 250)
im.paste(raw, offset)
draw.text((70, 38), "SAUNA  /  フロアマップ V8", font=font(64), fill=INK)
draw.text((75, 130), "男性専用・1系統  |  20 × 14 m / 約280㎡の概念配置", font=font(34), fill=MUTED)
draw.text(
    (75, 190), "同じ3Dモデルを真上から表示。番号は右の凡例に対応します。", font=font(28), fill=MUTED
)


def xy(x, y):
    return offset[0] + raw.width / 2 + (x - 10) * raw.width / 21.5, offset[1] + raw.height / 2 - (
        y - 7
    ) * raw.width / 21.5


def badge(number, position, group, radius=30):
    x, y = position
    draw.ellipse(
        (x - radius, y - radius, x + radius, y + radius), fill=GROUP[group], outline=BG, width=4
    )
    draw.text(
        (x, y - 2), str(number).zfill(2), font=font(29), fill="white", anchor="mm", stroke_width=0
    )


items = [
    (1, (2.0, 1.75), "front", "受付・下足・待合", "着衣の待合は小さく"),
    (2, (7.75, 1.75), "front", "更衣室", "ロッカー・身支度"),
    (3, (12.9, 1.75), "front", "洗面・WC", ""),
    (4, (15.65, 1.75), "back", "スタッフ・事務", ""),
    (5, (3.0, 6.3), "rest", "休憩室・延長区画", "寝台・椅子 計15席"),
    (6, (3.0, 12.0), "sauna", "メインサウナ", "中央ストーブ / 約20位置"),
    (7, (7.75, 12.25), "sauna", "セルフロウリュ", "高さが変わる6席"),
    (8, (11.0, 12.25), "sauna", "高温ドライ・TV", "腰掛け2＋脚を伸ばす2"),
    (9, (14.75, 12.25), "water", "炭酸泉", "1槽"),
    (10, (8.85, 7.78), "rest", "増設休憩「離れ」", "寝椅子4席 / 今回追加"),
    (11, (11.72, 7.75), "water", "深い水風呂", "1.78 × 1.90 m / 深さ1.20 m"),
    (12, (13.70, 7.75), "water", "座る水風呂", "1.60 × 1.90 m / 深さ0.60 m"),
    (13, (13.7, 5.0), "water", "洗い場・浴室導入", ""),
    (14, (18.5, 3.5), "back", "機械室・設備領域", ""),
    (15, (18.5, 8.5), "back", "リネン・清掃庫", ""),
    (16, (18.5, 12.0), "back", "保守・搬入領域", ""),
    (17, (13.8, 10.65), "rest", "予備の腰掛け", "短時間用3席"),
    (18, (16.65, 9.35), "rest", "浴室の造り付け席", "2席"),
]
draw.line((2515, 250, 2515, 1850), fill="#c8c1b5", width=2)
for index, (number, position, group, title, detail) in enumerate(items):
    badge(number, xy(*position), group)
    y = 275 + index * 86
    badge(number, (2585, y + 22), group, 28)
    draw.text((2630, y - 9), title, font=font(33), fill=INK)
    if detail:
        draw.text((2630, y + 34), detail, font=font(25), fill=MUTED)
# Same rest-room programme continues into its eastern extension.
badge(5, xy(8.1, 5.1), "rest", 25)

# The scale is derived from the fixed orthographic camera, not the page width.
x0, x1 = xy(0, 14)[0], xy(20, 14)[0]
dimension_y = 239
draw.line((x0, dimension_y, x1, dimension_y), fill=INK, width=2)
for x in [x0, x1]:
    draw.line((x, dimension_y - 10, x, dimension_y + 10), fill=INK, width=2)
draw.rectangle((1170, dimension_y - 23, 1360, dimension_y + 23), fill=BG)
draw.text((1265, dimension_y - 2), "20.0 m", font=font(30), fill=INK, anchor="mm")
draw.text((10, 1048), "14.0 m", font=font(25), fill=INK, anchor="lm")
draw.text((2390, 285), "N ↑", font=font(34), fill=INK)
entry = xy(2, 0)
draw.line((entry[0], 1870, entry[0], entry[1] + 13), fill=INK, width=4)
draw.polygon(
    [(entry[0], entry[1] + 13), (entry[0] - 10, entry[1] + 32), (entry[0] + 10, entry[1] + 32)],
    fill=INK,
)
draw.text((entry[0], 1900), "入口", font=font(30), fill=INK, anchor="mm")
sx, sy = 1675, 1900
unit = raw.width / 21.5
for i in range(5):
    draw.rectangle(
        (sx + i * unit, sy, sx + (i + 1) * unit, sy + 13), fill=INK if i % 2 == 0 else "#b8ad9b"
    )
for i in [0, 1, 5]:
    draw.text(
        (sx + i * unit, sy + 22),
        f"{i} m" if i == 5 else str(i),
        font=font(24),
        fill=MUTED,
        anchor="mt",
    )
draw.text(
    (75, 1950),
    "休憩は計24か所（15＋離れ4＋予備3＋造り付け2）。人数は概念検討上の位置数で、営業定員ではありません。",
    font=font(28),
    fill=INK,
)
draw.text(
    (75, 2000),
    "物件未定・寸法は仮。構造・設備能力・メーカー離隔・法適合・施工費は未検証。",
    font=font(25),
    fill=MUTED,
)
out = DATA / "diagrams/sauna_floor_map_v8.png"
out.parent.mkdir(exist_ok=True)
im.save(out)
print(
    json.dumps(
        {
            "map": out.name,
            "size": im.size,
            "numbered_items": len(items),
            "raw_render_sha256": hashlib.sha256(
                (DATA / "renders/sauna_plan_v8.png").read_bytes()
            ).hexdigest(),
        },
        ensure_ascii=False,
    )
)
