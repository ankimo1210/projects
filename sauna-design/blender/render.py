"""Render one camera of the saved model.

blender -b <model.blend> --python render.py -- --view main --out <png> [--res 2400] [--samples 1024] [--exposure 0]
"""

import argparse
import os
import sys
import time

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sauna import scene as sc

argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--view", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--res", type=int, default=2400)
ap.add_argument("--aspect", type=float, default=1.5)
ap.add_argument("--samples", type=int, default=1024)
ap.add_argument("--threshold", type=float, default=0.015)
ap.add_argument("--exposure", type=float, default=None)
ap.add_argument("--wb", type=float, default=None, help="camera white balance in kelvin")
ap.add_argument("--look", default=None)
ap.add_argument("--world", type=float, default=0.0, help="ambient world light (overview only)")
ap.add_argument(
    "--hide", default="", help="comma separated collection names to hide (e.g. Ceilings)"
)
args = ap.parse_args(argv)

scene = bpy.context.scene
cam = bpy.data.objects[f"Cam_{args.view}"]
scene.camera = cam
exposure = args.exposure if args.exposure is not None else cam.get("exposure", 0.0)
sc.configure_render(
    scene,
    args.res,
    int(round(args.res / args.aspect)),
    args.samples,
    args.threshold,
    exposure,
    ambient=args.world,
    **({"white_balance": args.wb} if args.wb else {}),
    **({"look": args.look} if args.look else {}),
)
for name in [n for n in args.hide.split(",") if n]:
    for col in bpy.data.collections:
        if col.name == name or col.name.startswith(name + "."):
            col.hide_render = True
scene.render.filepath = args.out
t0 = time.time()
bpy.ops.render.render(write_still=True)
print(
    f"RENDER_OK view={args.view} {scene.render.resolution_x}x{scene.render.resolution_y} samples<={args.samples} exposure={exposure} time={time.time() - t0:.1f}s -> {args.out}"
)
