"""Supplementary sight-line check against the built mesh (read-only; the model is not saved).

blender -b <model.blend> --python verify_sight.py

Repeats rest_layout.study() with a ray cast through the real geometry instead of the analytic partition outlines, and
lists every line the analytic model calls blocked but the mesh lets through (a gap the simplified model would hide).
Rays start and end 0.12 m short of each eye point so a person's own head position is not counted as an obstacle.
People are still points: body width, posture and standing up are not modelled. Not a privacy guarantee.
Transparent materials are conservatively treated as open; refraction and reflections are not simulated.
"""

import hashlib
import json
import math
import os
import sys

import bpy
from mathutils import Vector

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sauna import rest_layout as RL  # noqa: E402

scene = bpy.context.scene
deps = bpy.context.evaluated_depsgraph_get()
CLEAR = 0.12
hits = {}
ignored_hits = {}


def transparent_surface(ob, face_index):
    """Treat transmissive glazing as open, as the analytic study does; do not let a clear pane hide a sight-line leak."""
    if ob.type != "MESH" or not ob.data.materials:
        return False
    slot = (
        ob.data.polygons[face_index].material_index
        if 0 <= face_index < len(ob.data.polygons)
        else 0
    )
    mat = ob.data.materials[slot] if slot < len(ob.data.materials) else None
    if not mat or not mat.use_nodes:
        return False
    for node in mat.node_tree.nodes:
        if node.type in {"BSDF_GLASS", "BSDF_REFRACTION", "BSDF_TRANSPARENT"}:
            return True
        if node.type == "BSDF_PRINCIPLED":
            transmission = node.inputs.get("Transmission Weight")
            alpha = node.inputs.get("Alpha")
            if transmission and transmission.default_value > 0.1:
                return True
            if alpha and alpha.default_value < 0.99:
                return True
    return False


def mesh_state(lay, a, b):
    a, b = Vector(a), Vector(b)
    d = b - a
    dist = d.length - 2 * CLEAR
    if dist <= 0:
        return "open"
    d.normalize()
    origin = a + d * CLEAR
    for _ in range(128):
        if dist <= 0.0001:
            return "open"
        ok, loc, _nrm, face_index, ob, _matrix = scene.ray_cast(deps, origin, d, distance=dist)
        if not ok:
            return "open"
        if not transparent_surface(ob, face_index):
            hits[ob.name] = hits.get(ob.name, 0) + 1
            return "blocked"
        ignored_hits[ob.name] = ignored_hits.get(ob.name, 0) + 1
        step = max((loc - origin).dot(d) + 0.0001, 0.0001)
        origin += d * step
        dist -= step
    raise RuntimeError("Too many transparent surface crossings; sight line was not classified.")


lay = (
    RL.layout_v5()
)  # v6 keeps the v5 rest layout and partitions (towel pegs added, no screen changed)
analytic = RL.study(lay)
mesh = RL.study(lay, state=mesh_state)

# pairwise comparison of every eye-to-eye and aisle-to-eye line, also 0.11 m above the eye (top of the head)
seats = lay["seats"]
lines = []
for i, s in enumerate(seats):
    for t in seats[i + 1 :]:
        if math.hypot(s["eye"][0] - t["eye"][0], s["eye"][1] - t["eye"][1]) <= RL.RANGE:
            lines.append((s["id"], t["id"], s["eye"], t["eye"]))
    for k, (wx, wy) in enumerate(lay["walk"]):
        if math.hypot(wx - s["eye"][0], wy - s["eye"][1]) <= RL.RANGE:
            lines.append((f"walk{k}", s["id"], (wx, wy, RL.EYE["walk"]), s["eye"]))
count = {
    "lines": 0,
    "both_blocked": 0,
    "both_open": 0,
    "analytic_open_mesh_blocked": 0,
    "analytic_blocked_mesh_open": 0,
}
leaks, head_leaks = [], []
for na, nb, a, b in lines:
    an = RL.line_state(lay, a, b) == "blocked"
    me = mesh_state(lay, a, b) == "blocked"
    count["lines"] += 1
    if an and me:
        count["both_blocked"] += 1
    elif not an and not me:
        count["both_open"] += 1
    elif me:
        count["analytic_open_mesh_blocked"] += 1
    else:
        count["analytic_blocked_mesh_open"] += 1
        leaks.append([na, nb])
    top = (b[0], b[1], b[2] + 0.11)
    if an and mesh_state(lay, a, top) == "open":
        head_leaks.append([na, nb])

keys = (
    "seats",
    "mutual_gaze_pairs",
    "face_sightlines_open",
    "face_sightlines_filtered",
    "aisle_exposure_seated_mean",
    "aisle_exposure_seated_max",
    "aisle_exposure_lying_mean",
    "aisle_exposure_lying_max",
    "aisle_exposure_pct",
)
out = {
    "model": os.path.basename(bpy.data.filepath),
    "method": "scene.ray_cast on the evaluated mesh; transparent surfaces skipped; eye point to eye point, 0.12 m clear at both ends",
    "limits": "点としての目の位置だけを結ぶ補助確認。透過材は遮蔽せず、屈折による経路・体の幅・姿勢・立ち上がり・映り込みは扱わない。実空間のプライバシーを保証しない。",
    "analytic": {k: analytic[k] for k in keys},
    "mesh": {k: mesh[k] for k in keys},
    "line_comparison": count,
    "analytic_blocked_but_mesh_open": leaks,
    "blocked_at_eye_but_open_11cm_above": head_leaks,
    "objects_hit": dict(sorted(hits.items(), key=lambda kv: -kv[1])[:25]),
    "ignored_transparent_hits": dict(sorted(ignored_hits.items(), key=lambda kv: -kv[1])[:25]),
}
with open(bpy.data.filepath, "rb") as model_file:
    out["input_sha256"] = hashlib.file_digest(model_file, "sha256").hexdigest()
ver = os.path.join(os.path.dirname(os.path.dirname(bpy.data.filepath)), "verification")
os.makedirs(ver, exist_ok=True)
with open(os.path.join(ver, "rest_sight_raycast.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print(
    "SIGHT_OK",
    json.dumps(
        {
            "analytic": {k: analytic[k] for k in keys[:8]},
            "mesh": {k: mesh[k] for k in keys[:8]},
            "lines": count,
            "leaks": leaks[:20],
            "head_leaks": len(head_leaks),
        },
        ensure_ascii=False,
    ),
)
