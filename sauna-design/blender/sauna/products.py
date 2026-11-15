"""V7 product study applied after the accepted layout is built.

The baseline builder runs unchanged first, retaining every unrelated mesh and
random wood/stone variation. Only the generic main heater is replaced. This is
an exterior study, not manufacturer CAD or an approved heating installation.
"""

import math
import random

import bmesh
import bpy

from . import geo, materials
from .geo import MB

ZL300 = {
    "width": 0.880,
    "depth": 0.510,
    "height": 0.710,
    "power_kw": 24.8,
    "mass_with_stones_kg": 161,
    "centre": (3.0, 10.95),
    "source": "https://metos.co.jp/products/ziel",
}
FLOOR = {
    "code": "IFT-300/ST-33N",
    "module": 0.300,
    "tile": 0.297,
    "joint": 0.003,
    "thickness": 0.009,
    "texture_span": 1.200,
    "source": "https://iinavi.inax.lixil.co.jp/search_sp/index.php?keyword=IFT-300%2FST-33N",
}


def bath_floor():
    """Slate approximation with an explicit full-width 3 mm joint (metres)."""
    t = materials.NT("LIXIL_ST33N_bath_floor_APPROX")
    tc = t.node("ShaderNodeTexCoord")
    xyz = t.node("ShaderNodeSeparateXYZ")
    t.link(tc.outputs["Object"], xyz.inputs[0])
    edges = []
    for k in (0, 1):
        mod = t.math("MODULO", xyz.outputs[k], FLOOR["module"])
        edges.append(t.math("MINIMUM", mod, t.math("SUBTRACT", FLOOR["module"], mod)))
    grout = t.math("LESS_THAN", t.math("MINIMUM", *edges), FLOOR["joint"] / 2)
    # Unlike the generic Brick node, this threshold is explicitly half the
    # full joint. The mask is also baked and measured during export.
    grout.node.name = "Product_grout_mask_3mm"
    cloud = t.node("ShaderNodeTexNoise")
    t.link(tc.outputs["Object"], cloud.inputs["Vector"])
    cloud.inputs["Scale"].default_value = 17
    cloud.inputs["Detail"].default_value = 5
    fine = t.node("ShaderNodeTexNoise")
    t.link(tc.outputs["Object"], fine.inputs["Vector"])
    fine.inputs["Scale"].default_value = 280
    fine.inputs["Detail"].default_value = 3
    # Fine broken slate relief; warm colour comes from the existing lighting.
    strata = t.node("ShaderNodeTexWave", wave_type="BANDS", bands_direction="X")
    t.link(tc.outputs["Object"], strata.inputs["Vector"])
    strata.inputs["Scale"].default_value = 44
    strata.inputs["Distortion"].default_value = 8
    strata.inputs["Detail"].default_value = 4
    shade = t.maprange(cloud.outputs["Fac"], 0.2, 0.8, 0.80, 1.18)
    body = t.mixc(1.0, materials.rgb(0.080, 0.084, 0.087), shade, "MULTIPLY")
    color = t.mixc(grout, body, materials.rgb(0.021, 0.023, 0.024))
    damp = t.node("ShaderNodeTexNoise")
    t.link(tc.outputs["Object"], damp.inputs["Vector"])
    damp.inputs["Scale"].default_value = 1.4
    damp.inputs["Detail"].default_value = 3
    wet = t.maprange(damp.outputs["Fac"], 0.43, 0.72, 0, 1, smooth=True)
    rough = t.mixf(wet, 0.70, 0.34)
    rough = t.mixf(grout, rough, 0.88)
    color = t.mixc(t.math("MULTIPLY", wet, 0.13), color, materials.rgb(0, 0, 0))
    relief = t.math(
        "ADD",
        t.math("MULTIPLY", fine.outputs["Fac"], 0.09),
        t.math("MULTIPLY", strata.outputs["Fac"], 0.08),
    )
    relief = t.math("SUBTRACT", relief, t.math("MULTIPLY", grout, 0.60))
    bump = t.node("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.5
    bump.inputs["Distance"].default_value = 0.001
    t.link(relief, bump.inputs["Height"])
    t.principled(**{"Base Color": color, "Roughness": rough, "Normal": bump.outputs[0]})
    materials._glb(t.mat, (0.080, 0.084, 0.087), 0.60)
    for k, v in FLOOR.items():
        t.mat["product_" + k] = v
    t.mat["product_status"] = (
        "Series selected; dark colour provisional; procedural appearance approximation"
    )
    t.mat["glb_product_floor"] = True
    return t.mat


def ceramic():
    t = materials.NT("ZIEL_ceramic_stone_APPROX")
    tc = t.node("ShaderNodeTexCoord")
    n = t.node("ShaderNodeTexNoise")
    t.link(tc.outputs["Object"], n.inputs["Vector"])
    n.inputs["Scale"].default_value = 240
    n.inputs["Detail"].default_value = 3
    b = t.node("ShaderNodeBump")
    b.inputs["Distance"].default_value = 0.002
    b.inputs["Strength"].default_value = 0.45
    t.link(n.outputs["Fac"], b.inputs["Height"])
    col = t.mixc(
        n.outputs["Fac"], materials.rgb(0.21, 0.215, 0.215), materials.rgb(0.36, 0.37, 0.37)
    )
    t.principled(**{"Base Color": col, "Roughness": 0.89, "Normal": b.outputs[0]})
    materials._glb(t.mat, (0.29, 0.30, 0.30), 0.89)
    return t.mat


def stone_mesh():
    """Reusable oval ceramic study with shallow triangular dimples."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1)
    tmp = bpy.context.object
    vertices = [v.co.copy() for v in tmp.data.vertices]
    faces = [tuple(p.vertices) for p in tmp.data.polygons]
    bpy.data.objects.remove(tmp, do_unlink=True)
    out_v, out_f = [], []
    for face in faces:
        a, b, c = [vertices[i] for i in face]
        centre = (a + b + c) / 3
        inner = [centre + (v - centre) * 0.52 - centre.normalized() * 0.055 for v in (a, b, c)]
        start = len(out_v)
        out_v += [a, b, c] + inner
        out_f += [
            (start + i, start + (i + 1) % 3, start + 3 + (i + 1) % 3, start + 3 + i)
            for i in range(3)
        ]
        out_f.append((start + 3, start + 4, start + 5))
    mesh = bpy.data.meshes.new("ZIEL_ceramic_dimpled_APPROX")
    mesh.from_pydata(out_v, [], out_f)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.000001)
    bm.to_mesh(mesh)
    bm.free()
    for p in mesh.polygons:
        p.use_smooth = True
    mesh.update()
    return mesh


def apply(P, root):
    # Do not change the baseline RNG stream for any accepted room geometry.
    state = geo._rng.getstate()
    coll = geo.collection("Product_study_v7", root)
    for obj in list(bpy.data.objects):
        if (
            obj.name.startswith("Main_heater_")
            and "guard" not in obj.name
            and "hood" not in obj.name
        ):
            bpy.data.objects.remove(obj, do_unlink=True)
    cx, cy = ZL300["centre"]
    w, d, h = ZL300["width"], ZL300["depth"], ZL300["height"]
    metal = materials.brushed("ZIEL_stainless_APPROX", color=(0.52, 0.54, 0.56), rough=0.36)
    body = MB("Main_ZL300_casing_APPROX", metal, coll, bevel=0.0015, segments=2)
    body.box(cx - w / 2, cy - d / 2, 0.075, cx + w / 2, cy + d / 2, 0.595)
    body.finish()
    details = MB("Main_ZL300_rim_and_legs_APPROX", metal, coll, bevel=0.001, segments=1)
    for x in (cx - w / 2 + 0.055, cx + w / 2 - 0.055):
        for y in (cy - d / 2 + 0.055, cy + d / 2 - 0.055):
            details.box(x - 0.018, y - 0.018, 0, x + 0.018, y + 0.018, 0.075)
    for y in (cy - d / 2 + 0.008, cy + d / 2 - 0.008):
        details.box(cx - w / 2, y - 0.008, 0.580, cx + w / 2, y + 0.008, 0.607)
    for x in (cx - w / 2 + 0.008, cx + w / 2 - 0.008):
        details.box(x - 0.008, cy - d / 2, 0.580, x + 0.008, cy + d / 2, 0.607)
    for i in range(12):
        x = cx - w / 2 + 0.035 + i * (w - 0.070) / 11
        details.box(x - 0.003, cy - d / 2 + 0.015, 0.588, x + 0.003, cy + d / 2 - 0.015, 0.597)
    details.finish()
    stone = stone_mesh()
    stone.materials.append(ceramic())
    rng = random.Random(300)
    for row in range(3):
        for col in range(6):
            ob = bpy.data.objects.new(f"Main_ZL300_stone_APPROX_{row}_{col}", stone)
            coll.objects.link(ob)
            ob.location = (
                cx - 0.350 + col * 0.140 + rng.uniform(-0.006, 0.006),
                cy - 0.160 + row * 0.160 + rng.uniform(-0.006, 0.006),
                0.640 + rng.uniform(-0.003, 0.003),
            )
            ob.scale = (0.065, 0.065, 0.055 + rng.uniform(-0.004, 0.004))
            ob.rotation_euler = (
                rng.uniform(-0.25, 0.25),
                rng.uniform(-0.25, 0.25),
                rng.uniform(0, math.tau),
            )
    # One high central stone fixes the external study envelope at the published H710.
    top = bpy.data.objects.new("Main_ZL300_stone_APPROX_top", stone)
    coll.objects.link(top)
    top.location = (cx, cy, 0.660)
    top.scale = (0.065, 0.062, 0.050)
    bpy.context.view_layer.update()
    highest = max((top.matrix_world @ v.co).z for v in stone.vertices)
    top.location.z += h - highest
    for ob in coll.objects:
        ob["product"] = "METOS ZIEL ZL-300 exterior approximation"
        ob["quantity_status"] = "1 dimensional placeholder; heating quantity unselected"
    mat = bath_floor()
    floor = bpy.data.objects["Floor_wet"]
    floor.data.materials.clear()
    floor.data.materials.append(mat)
    # Metre UVs align the baked 1.2 m square with the native world-coordinate grid.
    uv = floor.data.uv_layers.active
    for poly in floor.data.polygons:
        for loop_index in poly.loop_indices:
            p = floor.data.vertices[floor.data.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv = (p.x, p.y)
    floor["product"] = "LIXIL IFT-300/ST-33N bathroom-floor type; colour provisional"
    floor["scope"] = (
        "carbonated-bath deck / cold-pool circulation / wash; not sauna floors or pool lining"
    )
    geo._rng.setstate(state)
