#!/usr/bin/env python3
"""Write <data-root>/delivery_manifest.json: files, sizes, sha256, render settings, and v7/v8 image brightness.

Also writes <data-root>/verification/image_luminance.json (mean Rec.709 luma of the final PNGs; needs Pillow + numpy).
The previous version's folder is only read.
"""

import sys

sys.dont_write_bytecode = True
import hashlib  # noqa: E402
import json  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402

V, PREV_V = "v8", "v7"
HERE = pathlib.Path(__file__).resolve().parent.parent
DATA = (
    pathlib.Path(sys.argv[1])
    if len(sys.argv) > 1
    else pathlib.Path(f"/home/kazumasa/projects/_data/sauna-design/fable-{V}")
)
PREV = DATA.parent / f"fable-{PREV_V}"
lighting = {}
lp = DATA / "verification" / f"lighting_{V}.json"
if lp.exists():
    lighting = json.loads(lp.read_text(encoding="utf-8"))
SETTINGS = {
    "renderer": "Blender 5.2.1 LTS Cycles, OptiX GPU (RTX 5080)",
    "seed": 20261114,
    "geometry_seed": 20261114,
    "interior_views": {
        "resolution": [2400, 1600],
        "max_samples": 1500,
        "adaptive_threshold": 0.01,
        "adaptive_min_samples": 64,
    },
    "overview_views": {
        "resolution": [2400, 1600],
        "max_samples": 400,
        "hidden_collections": ["Ceilings"],
        "world_ambient": 0.35,
    },
    "denoiser": "OpenImageDenoise (albedo+normal, accurate prefilter)",
    "bounces": {"max": 12, "diffuse": 6, "glossy": 6, "transmission": 12, "transparent": 12},
    "clamp_indirect": 8.0,
    "filter_glossy": 0.5,
    "refractive_caustics": True,
    "shadow_caustics_mnee": "pool spot lights",
    "color": {
        "view_transform": "AgX",
        "look": "AgX - Medium High Contrast",
        "white_balance_K": 4300,
        "tint": 10,
        "led_blackbody_K": 2700,
    },
    "camera": {
        "sensor_mm": 36,
        "pitch": "level, vertical lens shift",
        "definitions": "blender/build.py",
    },
    "exposure_stops": lighting.get("exposure_stops", {}),
    "lighting_record": f"verification/lighting_{V}.json (v4-v7 strengths and keys; strips of the two small saunas, the split south reveal of the bath and the pool spots follow the new geometry)",
    "check_bodies": "hidden in all renders except sauna_dry_people (collection Check_people shown, objects Body_DT* hidden)",
}
times = {}
for log in sorted((DATA / "logs").glob("render_sauna_*.log")):
    m = re.search(
        r"RENDER_OK view=(\w+) (\d+x\d+) samples<=(\d+) exposure=([\d.]+) time=([\d.]+)s",
        log.read_text(errors="replace"),
    )
    if m:
        times[log.stem[len("render_") :]] = {
            "camera": "Cam_" + m.group(1),
            "resolution": m.group(2),
            "max_samples": int(m.group(3)),
            "exposure": float(m.group(4)),
            "seconds": float(m.group(5)),
        }
luma = {}
try:
    import numpy as np
    from PIL import Image

    def mean_luma(path):
        a = np.asarray(Image.open(path).convert("RGB")).astype(float) / 255.0
        y = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
        return {
            "mean": round(float(y.mean()), 4),
            "median": round(float(np.median(y)), 4),
            "p95": round(float(np.percentile(y, 95)), 4),
            "share_above_0.5": round(float((y > 0.5).mean()), 4),
        }

    for tag, root in ((PREV_V, PREV), (V, DATA)):
        for p in sorted((root / "renders").glob("sauna_*.png")):
            if "labeled" not in p.name:
                luma.setdefault(tag, {})[p.name] = mean_luma(p)
    luma["note"] = (
        "Display-referred (sRGB PNG after AgX) Rec.709 luma, 0-1. v8 keeps the emitter strengths, exposure, look and white balance of v7. "
        "Only sauna_water uses the same camera in both versions, and what it sees changed (smaller pools, splash wall, annex), so the "
        "numbers describe the pictures, not a like-for-like brightness comparison. The other v8 views are new cameras."
    )
    (DATA / "verification" / "image_luminance.json").write_text(
        json.dumps(luma, indent=1, ensure_ascii=False), encoding="utf-8"
    )
except ImportError as e:
    luma = {"skipped": str(e)}
files = []  # hashed after image_luminance.json is written
for sub in ("model", "renders", "diagrams", "verification", "viewer", "assets/product_floor"):
    for p in sorted((DATA / sub).glob("*")):
        if p.is_file():
            files.append(
                {
                    "file": f"{sub}/{p.name}",
                    "bytes": p.stat().st_size,
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                }
            )
total = sum(p.stat().st_size for p in DATA.rglob("*") if p.is_file())
out = {
    "version": V,
    "settings": SETTINGS,
    "render_log": times,
    "files": files,
    "total_bytes_before_manifest": total,
    "image_luminance": "verification/image_luminance.json",
    "assets": "assets/polyhaven/manifest.json (CC0, URLs + md5)",
}
(DATA / "delivery_manifest.json").write_text(
    json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8"
)
print(
    json.dumps(
        {
            "files": len(files),
            "total_MB": round(total / 1e6, 1),
            "render_log": times,
            "luma_mean": {
                t: {k: v["mean"] for k, v in d.items()}
                for t, d in luma.items()
                if isinstance(d, dict)
            },
        },
        ensure_ascii=False,
    )
)
