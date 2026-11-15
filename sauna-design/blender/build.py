"""Build the sauna A-plan model (v8) and save the .blend.

blender -b --factory-startup --python build.py -- --data-root <fable-v8> --plan <plan_a.json> [--rooms main,water,rest,other]

v8 changes the bath strip (two smaller cold pools, rest annex) and the two small saunas. The stages that did not change
(main sauna, rest room, service rooms, doors) are built from the same position of the shared random stream as in v7, so
their boards and stones keep the same variation (positions measured by blender/rng_probe.py on the v7 source).
"""

import argparse
import json
import os
import sys
import time

import bpy

sys.dont_write_bytecode = True  # keep generated files out of the source tree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sauna import furniture, geo, materials, shell  # noqa: E402
from sauna import scene as sc

VERSION = "v8"
# shared random stream after each v7 stage (rng_probe.py); the roof / base slabs start 6 draws before the end of the structure
RNG_V7 = {
    "before_roof": 184,
    "after_structure": 190,
    "after_main": 6700,
    "after_water": 10361,
    "after_rest": 13493,
    "after_small_saunas": 19963,
}
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
P = materials.palette(tv_level=sc.TV_LEVEL)
LM = sc.light_materials()
furniture.load_rocks(materials.ASSET_ROOT)

root = geo.collection("SaunaA")
shell.build_structure(
    plan, P, geo.collection("Structure", root), rng_before_roof=RNG_V7["before_roof"]
)
rooms = set(args.rooms.split(","))
detailed = set()
if "main" in rooms:
    from sauna import room_main

    geo.jump(RNG_V7["after_structure"])
    room_main.build(plan, P, LM, geo.collection("Main", root))
    detailed.add("main")
if "water" in rooms:
    from sauna import room_water

    geo.jump(RNG_V7["after_main"])
    room_water.build(plan, P, LM, geo.collection("Water", root))
    detailed |= {"water", "carbon", "wash"}
if "rest" in rooms:
    from sauna import room_rest

    geo.jump(RNG_V7["after_water"])
    room_rest.build(plan, P, LM, geo.collection("Rest", root))
    detailed |= {"rest", "restExt"}
if "other" in rooms:
    from sauna import room_other

    geo.jump(RNG_V7["after_rest"])
    room_other.build(
        plan,
        P,
        LM,
        geo.collection("Other", root),
        skip=detailed,
        rng_after_saunas=RNG_V7["after_small_saunas"],
    )
    detailed |= {r["id"] for r in plan["rooms"]}
for r in plan["rooms"]:
    if r["id"] not in detailed:
        shell.plain_ceiling(r, P, root)
doors = geo.collection("Doors", root)
for d in plan["doors"]:
    shell.door(plan, d, P, doors)

from sauna import products

products.apply(P, root)  # local product stage; keeps all accepted layout meshes and RNG variation

if "main" in rooms:
    room_main.check_layer(
        root
    )  # last geometry step: assumed bodies for the seat / headroom check (hidden in renders)
if {"water", "other"} <= rooms:
    from sauna import room_sub

    room_sub.check_layer(root)  # v8: bodies in the small saunas, the cold pools and the rest annex

cams = geo.collection("Cameras", root)
E = {k: v[0] for k, v in sc.EXPOSURE.items()}
sc.add_camera(
    "Cam_main",
    (0.50, 9.37, 1.50),
    (0.50 + 6 * 0.682, 9.37 + 6 * 0.731),
    lens=24,
    shift_y=-0.085,
    coll=cams,
)["exposure"] = E["main"]
# v6: from the door towards the north-west — half step, foot bench and seats of the east side, stove, north landing
sc.add_camera(
    "Cam_main_entry", (4.16, 9.24, 1.55), (4.42, 13.0), lens=17, shift_y=-0.11, coll=cams
)["exposure"] = E["main"]
sc.add_overview_camera("Cam_main_plan", (3.0, 11.5, 30.0), (3.0, 11.5, 0.0), ortho=7.6, coll=cams)[
    "exposure"
] = E["overview"]  # base of the seat figure
# v6: from the walkway beside the seated pool towards the spare perch seats in the former fin-screen recess
sc.add_camera(
    "Cam_overflow", (12.30, 9.02, 1.50), (14.25, 10.75), lens=20, shift_y=-0.09, coll=cams
)["exposure"] = E["bath"]
sc.add_camera("Cam_water", (16.05, 9.90, 1.50), (9.0, 8.25), lens=24, shift_y=-0.08, coll=cams)[
    "exposure"
] = E["water"]
sc.add_camera("Cam_rest", (0.30, 6.43, 1.50), (7.0, 6.40), lens=24, shift_y=-0.08, coll=cams)[
    "exposure"
] = E["rest"]  # along the aisle
sc.add_camera("Cam_rest_seat", (2.63, 3.93, 1.55), (2.78, 6.40), lens=16, shift_y=-0.12, coll=cams)[
    "exposure"
] = E["rest"]  # standing at the wall end of a pair's entry, looking back to the aisle
sc.add_overview_camera("Cam_rest_plan", (5.25, 6.3, 30.0), (5.25, 6.3, 0.0), ortho=11.4, coll=cams)[
    "exposure"
] = E["overview"]  # base of the sight-line figure
sc.add_camera("Cam_bath", (12.25, 10.10, 1.50), (17.0, 8.55), lens=24, shift_y=-0.09, coll=cams)[
    "exposure"
] = E["bath"]
sc.add_overview_camera(
    "Cam_floor_detail", (15.75, 9.80, 1.30), (14.45, 9.30, 0.12), lens=35, coll=cams
)["exposure"] = E["bath"]
sc.add_overview_camera(
    "Cam_heater_detail", (3.90, 9.32, 1.28), (3.0, 10.95, 0.52), lens=32, coll=cams
)["exposure"] = E["main"]
# v8 small saunas: from each door, and from a seat
sc.add_camera("Cam_self", (7.80, 10.80, 1.55), (6.70, 13.55), lens=16, shift_y=-0.10, coll=cams)[
    "exposure"
] = E["self"]  # door -> rounded corner, three heights
sc.add_camera(
    "Cam_self_seat", (6.45, 11.50, 1.27), (9.25, 13.35), lens=17, shift_y=-0.06, coll=cams
)["exposure"] = E["self"]  # eye of the low west seat -> stove and the high seats
sc.add_camera("Cam_dry", (11.22, 10.80, 1.60), (11.02, 13.9), lens=15, shift_y=-0.10, coll=cams)[
    "exposure"
] = E["dry"]  # inside the door, looking north: high bench left, deck beyond, TV right
sc.add_camera(
    "Cam_dry_seats", (12.25, 12.05, 1.55), (9.60, 12.62), lens=15, shift_y=-0.10, coll=cams
)["exposure"] = E["dry"]  # from the TV wall -> high bench, wing, leg-stretch deck
sc.add_camera("Cam_dry_tv", (9.80, 13.52, 1.25), (12.39, 12.40), lens=16, shift_y=-0.15, coll=cams)[
    "exposure"
] = E["dry"]  # eye of the deck seat -> legs out, TV and stove
# v8 bath: the rest annex seen from the rest-door path, the annex / pool relation from the walkway, top view of the changed part
sc.add_camera("Cam_annex", (6.42, 7.776, 1.50), (10.7, 7.776), lens=18, shift_y=-0.09, coll=cams)[
    "exposure"
] = E["bath"]
sc.add_camera(
    "Cam_annex_pool", (9.05, 10.22, 1.55), (12.35, 7.35), lens=17, shift_y=-0.09, coll=cams
)["exposure"] = E["bath"]
sc.add_overview_camera(
    "Cam_bath_top", (11.5, 10.25, 30.0), (11.5, 10.25, 0.0), ortho=11.5, coll=cams
)["exposure"] = E["overview"]
sc.add_overview_camera("Cam_overview", (10.0, -5.5, 30.0), (10.0, 6.6, 0.0), lens=41, coll=cams)[
    "exposure"
] = E["overview"]
sc.add_overview_camera("Cam_plan", (10.0, 7.0, 30.0), (10.0, 7.0, 0.0), ortho=21.5, coll=cams)[
    "exposure"
] = E["plan"]
scene.camera = bpy.data.objects["Cam_main"]
sc.configure_render(scene)

out = args.out or os.path.join(args.data_root, "model", f"sauna_a_{VERSION}.blend")
os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=out, relative_remap=True)
try:
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile()
except Exception as e:
    print("relative path remap skipped:", e)

# lighting record: declared strengths plus what was actually built (emitter count, area, area x strength)
built = {}
for ob in bpy.data.objects:
    if ob.type != "MESH" or not ob.data.materials or not ob.data.materials[0]:
        continue
    name = ob.data.materials[0].name
    if not name.startswith("light_"):
        continue
    b = built.setdefault(name[len("light_") :], {"objects": 0, "area_m2": 0.0})
    b["objects"] += 1
    b["area_m2"] += sum(p.area for p in ob.data.polygons)
rec = sc.lighting_record()
for e in rec["emitters"]:
    b = built.get(e["key"], {"objects": 0, "area_m2": 0.0})
    e.update(
        objects=b["objects"],
        area_m2=round(b["area_m2"], 4),
        area_x_strength=round(b["area_m2"] * e["v4"], 3),
    )
rec["spot_lights"] = len([o for o in bpy.data.objects if o.type == "LIGHT"])
ver = os.path.join(args.data_root, "verification")
os.makedirs(ver, exist_ok=True)
rec["model_version"] = VERSION
rec["note"] = (
    "v8 keeps the v4-v7 emitter strengths, colours and exposure; the 'v4' column is the value in use. No new light key. "
    "What changed with the geometry: the two small saunas have new benches, so their under-bench strips (key sauna_bench) "
    "follow the new tiers (foot levels and half steps 12 mm wide, seats 24 mm); the bath's south ceiling reveal is split at "
    "the splash wall and its part over the rest annex uses the dimmer rest-room key rest_cove_s instead of bath_cove; one "
    "floor-facing strip under the annex walkway screen (key rest_toe); the two cold pools have one caustic spot each "
    "instead of two (spot_lights counts all pool spots). Areas below are measured from the built model."
)
rec["emitter_objects"] = sorted(
    [
        {
            "name": ob.name,
            "key": ob.data.materials[0].name[len("light_") :],
            "area_m2": round(sum(p.area for p in ob.data.polygons), 4),
        }
        for ob in bpy.data.objects
        if ob.type == "MESH"
        and ob.data.materials
        and ob.data.materials[0]
        and ob.data.materials[0].name.startswith("light_")
    ],
    key=lambda e: e["name"],
)
with open(os.path.join(ver, f"lighting_{VERSION}.json"), "w", encoding="utf-8") as fh:
    json.dump(rec, fh, ensure_ascii=False, indent=1)

polys = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")
print(
    f"BUILD_OK objects={len(bpy.data.objects)} polys={polys} time={time.time() - t0:.1f}s -> {out}"
)
