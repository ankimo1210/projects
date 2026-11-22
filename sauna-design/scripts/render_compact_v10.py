"""Parent-run sequential finals from one already saved model."""

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("--replace", action="store_true")
options = p.parse_args()
for view in [
    "main",
    "self",
    "bath",
    "rest",
    "rest_detail",
    "change",
    "overview",
    "plan",
    "section_pools",
]:
    args = [
        "bash",
        "scripts/blender_v10.sh",
        "render",
        "--view",
        view,
        "--res",
        "2400",
        "--samples",
        "1024",
        "--threshold",
        ".015",
    ]
    if options.replace:
        args += ["--replace"]
    if view in ("overview", "plan"):
        args += ["--world", ".3"]
    if view == "section_pools":
        args += ["--world", ".1"]
    subprocess.run(args, cwd=ROOT, check=True)
print("V10_FINAL_RENDER_BATCH_OK count=9")
