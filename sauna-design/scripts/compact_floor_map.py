"""Number the compact model's actual plan render; no separate room geometry is drawn."""

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = Path("/home/kazumasa/projects/_data/sauna-design/fable-v10")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", required=True, type=Path)
    a = parser.parse_args()
    if a.render.resolve().parent != OUT / "renders":
        raise ValueError("Only the new V10 plan render is supported")
    plan = json.loads((ROOT / "plan/compact_v10.json").read_text())
    probe = json.loads((OUT / "verification/native_probe.json").read_text())
    camera = next(c for c in probe["cameras"] if c["name"].lower().endswith("plan"))
    raw = Image.open(a.render).convert("RGB")
    if raw.width < 2000:
        raise ValueError("A final, high resolution plan render is required")
    scale = raw.width / camera["ortho_scale_m"]
    cx, cy = camera["position_blender_m"][:2]
    font_path = next(
        p
        for p in [
            "/mnt/c/Windows/Fonts/YuGothM.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        ]
        if Path(p).is_file()
    )

    def font(n):
        return ImageFont.truetype(font_path, n)

    paper, ink, secondary = "#f4f0e8", "#302d28", "#746f66"
    colors = {
        "main": "#a16e45",
        "self": "#a16e45",
        "rest": "#587263",
        "pools": "#4d7c88",
        "bath_hall": "#4d7c88",
        "wash": "#4d7c88",
    }
    offset = (50, 245)
    legend_x = raw.width + 135
    height = max(raw.height + 490, 2050)
    im = Image.new("RGB", (raw.width + 930, height), paper)
    d = ImageDraw.Draw(im)
    im.paste(raw, offset)
    d.text((55, 35), "SAUNA / フロアマップ V10", font=font(62), fill=ink)
    d.text(
        (60, 125),
        "170㎡・24人の比較案  |  17 × 10m（壁芯）  |  男性専用・1系統",
        font=font(33),
        fill=secondary,
    )
    d.text(
        (60, 185),
        "同じ保存済み3Dモデルの真上画像に、区画番号を付記。元案V8/V9は保持。",
        font=font(27),
        fill=secondary,
    )
    for i, z in enumerate(plan["zones"]):
        x, y, w, h = z["rect"]
        color = colors.get(z["group"], "#787875")
        px = offset[0] + raw.width / 2 + (x + w / 2 - cx) * scale
        py = offset[1] + raw.height / 2 - (y + h / 2 - cy) * scale
        r = 25
        d.ellipse((px - r, py - r, px + r, py + r), fill=color, outline=paper, width=3)
        d.text((px, py - 1), str(z["no"]).zfill(2), font=font(25), fill=paper, anchor="mm")
        ly = 270 + i * 94
        d.ellipse((legend_x, ly, legend_x + 48, ly + 48), fill=color)
        d.text(
            (legend_x + 24, ly + 23), str(z["no"]).zfill(2), font=font(24), fill=paper, anchor="mm"
        )
        d.text((legend_x + 65, ly - 3), z["name"], font=font(29), fill=ink)
        d.text(
            (legend_x + 65, ly + 40),
            f"{w:.2f} × {h:.2f} m / 壁芯 {w * h:.2f}㎡",
            font=font(23),
            fill=secondary,
        )
    bottom = offset[1] + raw.height + 35
    d.text(
        (60, bottom),
        "休憩16席（室内14＋浴室2）＋予備腰掛け2。全員集中・機器交換には未解決条件。",
        font=font(28),
        fill=ink,
    )
    d.text(
        (60, bottom + 47),
        "物件未定。床下・構造・メーカー条件・法適合・費用成立は未確認。在館24人は運営目標。",
        font=font(26),
        fill=secondary,
    )
    (OUT / "diagrams").mkdir(exist_ok=True)
    path = OUT / "diagrams/sauna_floor_map_v10.png"
    im.save(path)
    report = {
        "source_render": a.render.name,
        "source_render_sha256": hashlib.sha256(a.render.read_bytes()).hexdigest(),
        "source_model_sha256": probe["model_sha256"],
        "native_camera": camera,
        "pixel_scale_per_m": scale,
        "output": path.name,
        "output_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "note": "annotation only; native render geometry unchanged",
    }
    (OUT / "verification/floor_map_provenance.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)
    )
    with (OUT / "diagrams/room_program.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "x_m", "y_m", "width_m", "height_m", "wall_center_area_m2"])
        for z in plan["zones"]:
            writer.writerow([z["id"], z["name"], *z["rect"], z["rect"][2] * z["rect"][3]])
    print(
        json.dumps(
            {
                "floor_map": path.name,
                "image_size": im.size,
                "source_model_sha256": probe["model_sha256"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
