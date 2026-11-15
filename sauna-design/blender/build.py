"""Build the sauna A-plan model and save the .blend.

blender -b --factory-startup --python build.py -- --data-root <fable-v3> --plan <plan_a.json> [--rooms main,water,rest,other]
"""

import argparse
import json
import os
import sys
import time

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sauna import furniture, geo, materials, shell
from sauna import scene as sc

argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--data-root", required=True)
ap.add_argument("--plan", required=True)
ap.add_argument("--rooms", default="main,water,rest,other")
ap.add_argument("--out", default="")
args = ap.parse_args(argv)
t0 = time.time()

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
plan = json.load(open(args.plan, encoding="utf-8"))
materials.ASSET_ROOT = os.path.join(args.data_root, "assets")
geo.reseed(20261114)
P = materials.palette()
LM = sc.light_materials()
furniture.load_rocks(materials.ASSET_ROOT)

root = geo.collection("SaunaA")
shell.build_structure(plan, P, geo.collection("Structure", root))
rooms = set(args.rooms.split(","))
by_id = {r["id"]: r for r in plan["rooms"]}
detailed = set()
if "main" in rooms:
    from sauna import room_main

    room_main.build(plan, P, LM, geo.collection("Main", root))
    detailed.add("main")
if "water" in rooms:
    from sauna import room_water

    room_water.build(plan, P, LM, geo.collection("Water", root))
    detailed |= {"water", "carbon", "wash"}
if "rest" in rooms:
    from sauna import room_rest

    room_rest.build(plan, P, LM, geo.collection("Rest", root))
    detailed |= {"rest", "restExt"}
if "other" in rooms:
    from sauna import room_other

    room_other.build(plan, P, LM, geo.collection("Other", root), skip=detailed)
    detailed |= {r["id"] for r in plan["rooms"]}
for r in plan["rooms"]:
    if r["id"] not in detailed:
        shell.plain_ceiling(r, P, root)
doors = geo.collection("Doors", root)
for d in plan["doors"]:
    shell.door(plan, d, P, doors)

cams = geo.collection("Cameras", root)
sc.add_camera(
    "Cam_main",
    (0.50, 9.37, 1.50),
    (0.50 + 6 * 0.682, 9.37 + 6 * 0.731),
    lens=24,
    shift_y=-0.085,
    coll=cams,
)["exposure"] = 2.45
sc.add_camera("Cam_water", (16.05, 9.90, 1.50), (9.0, 8.25), lens=24, shift_y=-0.08, coll=cams)[
    "exposure"
] = 3.0
sc.add_camera("Cam_rest", (0.42, 6.30, 1.50), (7.0, 6.22), lens=24, shift_y=-0.08, coll=cams)[
    "exposure"
] = 3.2
sc.add_overview_camera("Cam_overview", (10.0, -5.5, 30.0), (10.0, 6.6, 0.0), lens=41, coll=cams)[
    "exposure"
] = 1.6
sc.add_overview_camera("Cam_plan", (10.0, 7.0, 30.0), (10.0, 7.0, 0.0), ortho=21.5, coll=cams)[
    "exposure"
] = 1.6
scene.camera = bpy.data.objects["Cam_main"]
sc.configure_render(scene)

out = args.out or os.path.join(args.data_root, "model", "sauna_a_v3.blend")
os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=out, relative_remap=True)
try:
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile()
except Exception as e:
    print("relative path remap skipped:", e)
tris = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")
print(
    f"BUILD_OK objects={len(bpy.data.objects)} polys={tris} time={time.time() - t0:.1f}s -> {out}"
)
