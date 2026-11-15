"""Export an interchange .glb of the saved model (simplified PBR materials; procedural shaders are flattened).

blender -b <model.blend> --python export_glb.py -- --out <glb> [--draco]
"""

import argparse
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--draco", action="store_true")
args = ap.parse_args(argv)

# tag ceiling objects so a viewer can hide them
for col in bpy.data.collections:
    if col.name.startswith("Ceilings"):
        for ob in col.objects:
            ob.name = "CEIL_" + ob.name

for mat in bpy.data.materials:
    if "glb_color" not in mat.keys() or mat.name.startswith("moon_rock"):
        continue
    nt = mat.node_tree
    img_path = mat.get("glb_image", "")
    image = None
    scale = None
    if img_path:
        for n in nt.nodes:
            if n.type == "TEX_IMAGE" and n.image and "diff" in n.image.name:
                image = n.image
            if n.type == "MAPPING":
                scale = tuple(n.inputs["Scale"].default_value)
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    col = list(mat["glb_color"]) + [1.0]
    bsdf.inputs["Roughness"].default_value = mat["glb_rough"]
    bsdf.inputs["Metallic"].default_value = mat["glb_metal"]
    if image:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = image
        uv = nt.nodes.new("ShaderNodeUVMap")
        mp = nt.nodes.new("ShaderNodeMapping")
        if scale:
            mp.inputs["Scale"].default_value = scale
        nt.links.new(uv.outputs[0], mp.inputs[0])
        nt.links.new(mp.outputs[0], tex.inputs[0])
        mx = nt.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = "MULTIPLY"
        mx.inputs[0].default_value = 1.0
        nt.links.new(tex.outputs[0], mx.inputs[6])
        mx.inputs[7].default_value = col
        nt.links.new(mx.outputs[2], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = col
    if mat["glb_emit"] > 0:
        bsdf.inputs["Emission Color"].default_value = col
        bsdf.inputs["Emission Strength"].default_value = mat["glb_emit"]
    if mat["glb_alpha"] < 1.0:
        bsdf.inputs["Alpha"].default_value = mat["glb_alpha"]
        try:
            mat.surface_render_method = "BLENDED"
        except Exception:
            mat.blend_method = "BLEND"

kw = dict(
    filepath=args.out,
    export_format="GLB",
    export_apply=True,
    export_cameras=True,
    export_lights=False,
    export_yup=True,
    export_image_format="JPEG",
    export_texcoords=True,
    export_normals=True,
)
if args.draco:
    kw.update(export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
bpy.ops.export_scene.gltf(**kw)
print(f"GLB_OK {os.path.getsize(args.out) / 1e6:.1f} MB -> {args.out}")
