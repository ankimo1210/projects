"""Count how many random numbers each build stage draws (read-only probe, saves nothing).

blender -b --factory-startup --python rng_probe.py -- --data-root <fable-vN> --plan <plan_a.json>

The builders share one random stream (geo.rnd) for per-board colour variation and UV offsets. When a later version changes
one room, the rooms built after it would otherwise get a different (equally random) variation. build.py therefore jumps the
stream to the recorded position before every unchanged stage; the positions were measured with this probe on the v7 source
(sessions/source-v7.zip) before v8 changed the water room and the two small saunas.
"""

import argparse
import json
import os
import random
import sys

import bpy

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sauna import furniture, geo, materials, shell  # noqa: E402
from sauna import scene as sc

argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--data-root", required=True)
ap.add_argument("--plan", required=True)
args = ap.parse_args(argv)


class Counting(random.Random):
    n = 0

    def random(self):
        self.n += 1
        return super().random()


bpy.ops.wm.read_factory_settings(use_empty=True)
plan = json.load(open(args.plan, encoding="utf-8"))
materials.ASSET_ROOT = os.path.join(args.data_root, "assets")
geo._rng = Counting(20261114)
P = materials.palette(tv_level=sc.TV_LEVEL)
LM = sc.light_materials()
furniture.load_rocks(materials.ASSET_ROOT)
pos = {"start": geo._rng.n}
root = geo.collection("SaunaA")
shell.build_structure(plan, P, geo.collection("Structure", root))
pos["after_structure"] = geo._rng.n
from sauna import room_main, room_other, room_rest, room_water  # noqa: E402

room_main.build(plan, P, LM, geo.collection("Main", root))
pos["after_main"] = geo._rng.n
room_water.build(plan, P, LM, geo.collection("Water", root))
pos["after_water"] = geo._rng.n
room_rest.build(plan, P, LM, geo.collection("Rest", root))
pos["after_rest"] = geo._rng.n
other = geo.collection("Other", root)
if hasattr(
    room_other, "small_sauna"
):  # v7 layout of room_other.build: the two small saunas come first
    room_other.small_sauna(plan, P, LM, other, "Self", 6.08, 9.42, (7.1, 8.1), (8.78, 11.25), 0.30)
    room_other.bucket(P, other, "Self_loyly_bucket", 6.45, 12.25)
    room_other.dry_tv_sauna(plan, P, LM, other)
    pos["after_small_saunas"] = geo._rng.n
print("RNG_POSITIONS " + json.dumps(pos))
