"""Read-only product dimensions and unrelated-geometry comparison to frozen v6."""

import hashlib
import json
import os
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sauna.products import FLOOR, ZL300

root = Path(sys.argv[sys.argv.index("--") + 1])
model = Path(bpy.data.filepath)


def digest(obj, uv=False):
    h = hashlib.sha256()
    for row in obj.matrix_world:
        h.update(struct.pack("4f", *row))
    for v in obj.data.vertices:
        h.update(struct.pack("3f", *v.co))
    for p in obj.data.polygons:
        h.update(struct.pack(f"{len(p.vertices)}I", *p.vertices))
    for m in obj.modifiers:
        h.update(str((m.type, getattr(m, "width", None), getattr(m, "segments", None))).encode())
    if uv and obj.data.uv_layers.active:
        for v in obj.data.uv_layers.active.data:
            h.update(struct.pack("2f", *v.uv))
    return h.hexdigest()


def snapshot():
    return {
        o.name: {"shape": digest(o), "uv": digest(o, True)}
        for o in bpy.context.scene.objects
        if o.type == "MESH"
        and not o.name.startswith("Main_ZL300_")
        and not (
            o.name.startswith("Main_heater_") and "guard" not in o.name and "hood" not in o.name
        )
    }


bpy.context.view_layer.update()
objects = [o for o in bpy.context.scene.objects if o.name.startswith("Main_ZL300_")]
deps = bpy.context.evaluated_depsgraph_get()
points = []
for obj in objects:
    evaluated = obj.evaluated_get(deps)
    mesh = evaluated.to_mesh()
    points.extend(evaluated.matrix_world @ v.co for v in mesh.vertices)
    evaluated.to_mesh_clear()
lo = [min(v[k] for v in points) for k in range(3)]
hi = [max(v[k] for v in points) for k in range(3)]
size = [hi[k] - lo[k] for k in range(3)]
assert all(abs(a - b) < 0.001 for a, b in zip(size, (0.880, 0.510, 0.710))), size
guard = bpy.data.objects["Main_heater_guard_rails"]
bvh = BVHTree.FromObject(guard, bpy.context.evaluated_depsgraph_get())
cx, cy = ZL300["centre"]
distances = []
for x in (cx - 0.440, cx + 0.440):
    for y in (cy - 0.255, cy + 0.255):
        p = Vector((x, y, 0.410))
        hit = bvh.find_nearest(p)
        distances.append(hit[3])
mat = bpy.data.objects["Floor_wet"].data.materials[0]
assert mat.name == "LIXIL_ST33N_bath_floor_APPROX"
mask = mat.node_tree.nodes["Product_grout_mask_3mm"]
assert mask.operation == "LESS_THAN" and abs(mask.inputs[1].default_value - 0.0015) < 1e-8
mods = [n for n in mat.node_tree.nodes if n.type == "MATH" and n.operation == "MODULO"]
assert len(mods) == 2 and all(abs(n.inputs[1].default_value - 0.300) < 1e-7 for n in mods)
assert bpy.data.objects["Floor_dry"].data.materials[0].name == "tile_floor_charcoal"
assert bpy.data.objects["Floor_damp"].data.materials[0].name == "tile_floor_charcoal"
actual_v7 = snapshot()
settings = {
    "lights": {o.name: o.data.energy for o in bpy.context.scene.objects if o.type == "LIGHT"},
    "cameras": {
        o.name: {
            "location": list(o.location),
            "rotation": list(o.rotation_euler),
            "lens": o.data.lens,
            "shift_y": o.data.shift_y,
            "exposure": o.get("exposure"),
        }
        for o in bpy.context.scene.objects
        if o.type == "CAMERA"
    },
}
report = {
    "version": "v7",
    "model_sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
    "heater_public_spec": ZL300,
    "heater_measured_bbox_m": {"min": lo, "max": hi, "size": size},
    "heater_model_objects": len(objects),
    "quantity": "one dimensional placeholder, operational quantity unselected",
    "guard_minimum_corner_to_wood_mesh_m": min(distances),
    "guard_note": "Geometric distance only; no manufacturer's required clearance was available. Not an installation approval.",
    "floor": FLOOR,
    "floor_shader_full_joint_m": 2 * mask.inputs[1].default_value,
    "floor_shader_module_m": [n.inputs[1].default_value for n in mods],
    "floor_scope": ["carbonated bath deck", "cold-pool circulation", "wash"],
    "floor_geometry": "Existing surface mesh; 9 mm product thickness is a specification, not a detailed floor assembly.",
    "not_selected": [
        "sauna-floor heat compatibility",
        "heater quantity / thermal load",
        "manufacturer clearances / guard / servicing specification",
        "price / construction / permissions",
    ],
    "appearance": "Exterior geometry and procedural slate/ceramic approximations; not certified manufacturer CAD or colour proof",
    "modified_model": False,
}
baseline = root.parent / "fable-v6/model/sauna_a_v6.blend"
bpy.ops.wm.open_mainfile(filepath=str(baseline))
actual_v6 = snapshot()
added = sorted(set(actual_v7) - set(actual_v6))
removed = sorted(set(actual_v6) - set(actual_v7))
shape = sorted(
    n for n in actual_v6.keys() & actual_v7.keys() if actual_v6[n]["shape"] != actual_v7[n]["shape"]
)
uv = sorted(
    n for n in actual_v6.keys() & actual_v7.keys() if actual_v6[n]["uv"] != actual_v7[n]["uv"]
)
old_lights = {o.name: o.data.energy for o in bpy.context.scene.objects if o.type == "LIGHT"}
changed_cameras = []
for o in bpy.context.scene.objects:
    if o.type != "CAMERA":
        continue
    cam = {
        "location": list(o.location),
        "rotation": list(o.rotation_euler),
        "lens": o.data.lens,
        "shift_y": o.data.shift_y,
        "exposure": o.get("exposure"),
    }
    if cam != settings["cameras"].get(o.name):
        changed_cameras.append(o.name)
report["baseline_comparison"] = {
    "compared_mesh_objects": len(actual_v6),
    "added_unrelated": added,
    "removed_unrelated": removed,
    "changed_unrelated_shape": shape,
    "changed_uv": uv,
    "all_light_energy_unchanged": old_lights == settings["lights"],
    "changed_existing_cameras": changed_cameras,
}
assert not added and not removed and not shape, report["baseline_comparison"]
assert uv == ["Floor_wet"] and not changed_cameras and old_lights == settings["lights"]
target = root / "verification/product_selection.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print("PRODUCT_OK dimensions, explicit grid, scoped materials and frozen unrelated geometry")
