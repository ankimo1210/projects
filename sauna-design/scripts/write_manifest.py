#!/usr/bin/env python3
"""Write <data-root>/delivery_manifest.json: files, sizes, sha256 and the render settings used (stdlib only)."""

import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
DATA = (
    pathlib.Path(sys.argv[1])
    if len(sys.argv) > 1
    else HERE.parent / "_data" / "sauna-design" / "fable-v3"
)
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
        "lens_mm": 24,
        "sensor_mm": 36,
        "eye_height_m": 1.5,
        "pitch": "level, vertical lens shift",
    },
    "exposure_stops": {"main": 2.45, "water": 3.0, "rest": 3.2, "overview": 1.6, "plan": 1.6},
}
files = []
for sub in ("model", "renders", "viewer"):
    for p in sorted((DATA / sub).glob("*")):
        if p.is_file():
            files.append(
                {
                    "file": f"{sub}/{p.name}",
                    "bytes": p.stat().st_size,
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                }
            )
times = {}
for log in sorted((DATA / "logs").glob("render_*.log")):
    m = re.search(
        r"RENDER_OK view=(\w+) (\d+x\d+) samples<=(\d+) exposure=([\d.]+) time=([\d.]+)s",
        log.read_text(errors="replace"),
    )
    if m:
        times[m.group(1)] = {
            "resolution": m.group(2),
            "max_samples": int(m.group(3)),
            "exposure": float(m.group(4)),
            "seconds": float(m.group(5)),
        }
total = sum(p.stat().st_size for p in DATA.rglob("*") if p.is_file())
out = {
    "settings": SETTINGS,
    "render_log": times,
    "files": files,
    "total_bytes_before_manifest": total,
    "assets": "assets/polyhaven/manifest.json (CC0, URLs + md5)",
}
(DATA / "delivery_manifest.json").write_text(
    json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8"
)
print(
    json.dumps(
        {"files": len(files), "total_MB": round(total / 1e6, 1), "render_log": times},
        ensure_ascii=False,
    )
)
