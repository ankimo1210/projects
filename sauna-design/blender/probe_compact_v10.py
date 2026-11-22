"""Parent-owned, read-only inspection of the saved compact model's evaluated meshes."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.dont_write_bytecode = True


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", required=True)
    a = parser.parse_args(args)
    model, out = Path(a.model), Path(a.out)
    if model.parent.parent.name != "fable-v10" or out.parent.parent != model.parent.parent:
        raise ValueError("Probe is restricted to the named V10 model/output root")
    with model.open("rb") as f:
        before = hashlib.file_digest(f, "sha256").hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(model))
    scene = bpy.context.scene
    deps = bpy.context.evaluated_depsgraph_get()
    meshes, cameras, textures = [], [], []
    vertices = polygons = 0
    for ob in sorted(scene.objects, key=lambda x: x.name):
        if ob.type == "MESH":
            eo = ob.evaluated_get(deps)
            points = [ob.matrix_world @ Vector(v) for v in eo.bound_box]
            low = [min(p[i] for p in points) for i in range(3)]
            high = [max(p[i] for p in points) for i in range(3)]
            mesh = eo.to_mesh()
            nv, np = len(mesh.vertices), len(mesh.polygons)
            vertices += nv
            polygons += np
            eo.to_mesh_clear()
            meshes.append(
                {
                    "name": ob.name,
                    "collections": [c.name for c in ob.users_collection],
                    "bbox_min_m": low,
                    "bbox_max_m": high,
                    "extent_m": [high[i] - low[i] for i in range(3)],
                    "evaluated_vertices": nv,
                    "evaluated_polygons": np,
                    "hide_render": bool(ob.hide_render),
                    "hide_viewport": bool(ob.hide_viewport),
                    "materials": [
                        s.material.name if s.material else None for s in ob.material_slots
                    ],
                }
            )
        elif ob.type == "CAMERA":
            direction = ob.matrix_world.to_quaternion() @ Vector((0, 0, -1))
            position = ob.matrix_world.translation
            cameras.append(
                {
                    "name": ob.name,
                    "position_blender_m": list(position),
                    "target_blender_m": list(position + direction * 3),
                    "direction_blender": list(direction),
                    "type": ob.data.type,
                    "ortho_scale_m": ob.data.ortho_scale,
                    "lens_mm": ob.data.lens,
                    "fov_radians": ob.data.angle,
                    "shift_y": ob.data.shift_y,
                }
            )
    for im in bpy.data.images:
        if im.source != "FILE":
            continue
        resolved = bpy.path.abspath(im.filepath)
        textures.append(
            {
                "image": im.name,
                "stored_path": im.filepath,
                "resolved_path": resolved,
                "packed": bool(im.packed_file),
                "exists": bool(im.packed_file) or os.path.isfile(resolved),
            }
        )
    missing = [r["image"] for r in textures if not r["exists"]]
    with model.open("rb") as f:
        after = hashlib.file_digest(f, "sha256").hexdigest()
    assert before == after, "Probe modified the saved model"
    report = {
        "scope": "saved model reloaded; evaluated world bounding boxes, not a code/safety approval",
        "blender": bpy.app.version_string,
        "model_sha256": before,
        "model_unchanged": True,
        "engine": scene.render.engine,
        "units": {"system": scene.unit_settings.system, "scale": scene.unit_settings.scale_length},
        "mesh_count": len(meshes),
        "evaluated_vertices": vertices,
        "evaluated_polygons": polygons,
        "light_count": sum(o.type == "LIGHT" for o in scene.objects),
        "material_count": len(bpy.data.materials),
        "camera_count": len(cameras),
        "missing_texture_files": missing,
        "textures": textures,
        "cameras": cameras,
        "meshes": meshes,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "V10_PARENT_PROBE "
        + json.dumps(
            {
                k: report[k]
                for k in (
                    "model_sha256",
                    "model_unchanged",
                    "mesh_count",
                    "evaluated_vertices",
                    "camera_count",
                    "material_count",
                    "missing_texture_files",
                )
            }
        )
    )
    if missing:
        raise RuntimeError("Missing model textures")


if __name__ == "__main__":
    main()
