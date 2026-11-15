"""Run inside Blender to inspect the saved model without modifying it."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import bpy


def main() -> None:
    target = Path(sys.argv[sys.argv.index("--") + 1])
    scene = bpy.context.scene
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    missing = []
    reference_textures = []
    for image in bpy.data.images:
        if image.source != "FILE" or image.packed_file or not image.filepath:
            continue
        if not os.path.isfile(bpy.path.abspath(image.filepath)):
            missing.append(image.name)
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image and "sauna-interior-" in node.image.name:
                reference_textures.append({"material": mat.name, "image": node.image.name})
    report = {
        "blender": bpy.app.version_string,
        "opened_model": bpy.data.filepath,
        "engine": scene.render.engine,
        "cycles_device": scene.cycles.device,
        "units": {"system": scene.unit_settings.system, "scale": scene.unit_settings.scale_length},
        "mesh_objects": len(meshes),
        "mesh_vertices": sum(len(obj.data.vertices) for obj in meshes),
        "materials": len(bpy.data.materials),
        "cameras": [obj.name for obj in scene.objects if obj.type == "CAMERA"],
        "lights": len([obj for obj in scene.objects if obj.type == "LIGHT"]),
        "missing_texture_files": missing,
        "reference_image_texture_nodes": reference_textures,
        "modified_model": False,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PARENT_MODEL_VERIFICATION_OK")


if __name__ == "__main__":
    main()
