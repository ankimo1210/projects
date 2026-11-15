"""Bake only the selected bath floor for the portable GLB; no scene save."""

import json
from pathlib import Path

import bpy
import numpy as np


def bake_floor(material, output_root):
    root = Path(output_root)
    folder = root / "assets" / "product_floor"
    folder.mkdir(parents=True, exist_ok=True)
    span = float(material["product_texture_span"])
    mesh = bpy.data.meshes.new("Product_floor_bake_plane")
    mesh.from_pydata([(0, 0, 0), (span, 0, 0), (span, span, 0), (0, span, 0)], [], [(0, 1, 2, 3)])
    uv = mesh.uv_layers.new(name="UVMap")
    for p, v in zip(uv.data, ((0, 0), (1, 0), (1, 1), (0, 1))):
        p.uv = v
    obj = bpy.data.objects.new("Product_floor_bake_plane", mesh)
    bpy.context.scene.collection.objects.link(obj)
    copy = material.copy()
    mesh.materials.append(copy)
    nt = copy.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    src_color = bsdf.inputs["Base Color"].links[0].from_socket
    src_rough = bsdf.inputs["Roughness"].links[0].from_socket
    src_mask = nt.nodes["Product_grout_mask_3mm"].outputs[0]
    emit = nt.nodes.new("ShaderNodeEmission")
    tex = nt.nodes.new("ShaderNodeTexImage")
    for n in nt.nodes:
        n.select = False
    tex.select = True
    nt.nodes.active = tex
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 1
    scene.render.bake.use_selected_to_active = False
    scene.render.bake.margin = 0
    images = {}
    mask_pixels = None
    for kind, socket in (
        ("basecolor", src_color),
        ("roughness", src_rough),
        ("normal", None),
        ("joint_mask", src_mask),
    ):
        im = bpy.data.images.new(
            "ST33N_" + kind, width=2048, height=2048, alpha=False, is_data=kind != "basecolor"
        )
        im.colorspace_settings.name = "sRGB" if kind == "basecolor" else "Non-Color"
        tex.image = im
        if socket is None:
            nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
            bpy.ops.object.bake(type="NORMAL")
        else:
            nt.links.new(socket, emit.inputs["Color"])
            nt.links.new(emit.outputs[0], out.inputs["Surface"])
            bpy.ops.object.bake(type="EMIT")
        im.filepath_raw = str(folder / ("ST33N_" + kind + ".png"))
        im.file_format = "PNG"
        im.save()
        im.pack()
        images[kind] = im
        if kind == "joint_mask":
            pixels = np.empty(2048 * 2048 * 4, dtype=np.float32)
            im.pixels.foreach_get(pixels)
            mask_pixels = pixels.reshape(2048, 2048, 4)[256, :, 0]
    # A row at y=150 mm crosses vertical joints, not a horizontal one.
    selected = np.flatnonzero(mask_pixels > 0.5)
    groups = np.split(selected, np.flatnonzero(np.diff(selected) > 1) + 1)
    groups = [g for g in groups if len(g) and g[0] > 0 and g[-1] < 2047]
    widths = [round(len(g) * span / 2048 * 1000, 4) for g in groups]
    report = {
        "source": "native Cycles product floor shader, unlit surface bake",
        "resolution": [2048, 2048],
        "span_m": span,
        "tiles_per_side": 4,
        "intended_full_joint_mm": 3.0,
        "pixel_size_mm": span / 2048 * 1000,
        "measured_interior_joint_mm": widths,
        "max_joint_quantization_error_mm": max(abs(w - 3) for w in widths),
        "maps": {
            k: str(Path("assets/product_floor") / Path(v.filepath_raw).name)
            for k, v in images.items()
        },
        "appearance": "procedural approximation; not manufacturer texture or colour proof",
        "portable_difference": "four-tile texture repeats; native large-scale wet variation is approximated",
    }
    assert len(groups) == 3 and report["max_joint_quantization_error_mm"] < 0.9, report
    (root / "verification").mkdir(parents=True, exist_ok=True)
    (root / "verification/product_floor_bake.json").write_text(json.dumps(report, indent=2) + "\n")
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.materials.remove(copy)
    return images, span


def portable_floor(material, images, span):
    nt = material.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / span, 1 / span, 1)
    nt.links.new(uv.outputs[0], mp.inputs[0])
    for kind, socket in (
        ("basecolor", "Base Color"),
        ("roughness", "Roughness"),
        ("normal", "Normal"),
    ):
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = images[kind]
        tex.extension = "REPEAT"
        nt.links.new(mp.outputs[0], tex.inputs[0])
        if kind == "normal":
            n = nt.nodes.new("ShaderNodeNormalMap")
            nt.links.new(tex.outputs["Color"], n.inputs["Color"])
            nt.links.new(n.outputs[0], p.inputs[socket])
        else:
            nt.links.new(tex.outputs["Color"], p.inputs[socket])
