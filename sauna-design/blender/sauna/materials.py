"""Cycles materials: photo-textured wood (Poly Haven CC0), procedural stone tile, water, glass, metal, fabric, light."""

import os

import bpy

ASSET_ROOT = ""  # set by build.py
_cache = {}


class NT:
    def __init__(self, name):
        self.mat = bpy.data.materials.new(name)
        self.mat.use_nodes = True
        self.nt = self.mat.node_tree
        self.nt.nodes.clear()
        self.out = self.nt.nodes.new("ShaderNodeOutputMaterial")

    def node(self, kind, **props):
        n = self.nt.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def link(self, a, b):
        self.nt.links.new(a, b)

    def set(self, sock, val):
        if isinstance(val, (int, float)):
            sock.default_value = val
        elif isinstance(val, (tuple, list)):
            sock.default_value = val
        else:
            self.link(val, sock)

    def math(self, op, a, b=None, clamp=False):
        n = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        self.set(n.inputs[0], a)
        if b is not None:
            self.set(n.inputs[1], b)
        return n.outputs[0]

    def maprange(self, v, a, b, c, d, smooth=False):
        n = self.node("ShaderNodeMapRange")
        if smooth:
            n.interpolation_type = "SMOOTHSTEP"
        self.set(n.inputs[0], v)
        for i, x in enumerate((a, b, c, d)):
            n.inputs[i + 1].default_value = x
        return n.outputs[0]

    def mixc(self, fac, a, b, blend="MIX"):
        n = self.node("ShaderNodeMix", data_type="RGBA", blend_type=blend)
        self.set(n.inputs[0], fac)
        self.set(n.inputs[6], a)
        self.set(n.inputs[7], b)
        return n.outputs[2]

    def mixv(self, fac, a, b):
        n = self.node("ShaderNodeMix", data_type="VECTOR")
        self.set(n.inputs[0], fac)
        self.set(n.inputs[4], a)
        self.set(n.inputs[5], b)
        return n.outputs[1]

    def mixf(self, fac, a, b):
        n = self.node("ShaderNodeMix", data_type="FLOAT")
        self.set(n.inputs[0], fac)
        self.set(n.inputs[2], a)
        self.set(n.inputs[3], b)
        return n.outputs[0]

    def principled(self, **inputs):
        p = self.node("ShaderNodeBsdfPrincipled")
        for k, v in inputs.items():
            self.set(p.inputs[k], v)
        self.link(p.outputs[0], self.out.inputs["Surface"])
        return p


def rgb(r, g, b):
    return (r, g, b, 1.0)


def _glb(mat, color, rough=0.6, metal=0.0, image="", emit=0.0, alpha=1.0):
    mat["glb_color"] = list(color[:3])
    mat["glb_rough"] = rough
    mat["glb_metal"] = metal
    mat["glb_image"] = image
    mat["glb_emit"] = emit
    mat["glb_alpha"] = alpha


def _image(path, colorspace="sRGB"):
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = colorspace
    return img


def wood(
    name,
    tint=(0.62, 0.50, 0.42),
    gamma=1.25,
    rough=0.72,
    size=1.2,
    variation=0.22,
    normal=0.5,
    coat=0.0,
):
    """Straight-grain timber. UV u runs along the fibre in metres; 'rand' vertex attribute varies each board."""
    if name in _cache:
        return _cache[name]
    t = NT(name)
    base = os.path.join(ASSET_ROOT, "polyhaven", "cherry_veneer")
    uv = t.node("ShaderNodeUVMap", uv_map="UVMap")
    mp = t.node("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0 / size, 1.0 / size, 1.0)
    t.link(uv.outputs[0], mp.inputs[0])
    diff = t.node(
        "ShaderNodeTexImage", image=_image(os.path.join(base, "cherry_veneer_diff_2k.jpg"))
    )
    rgh = t.node(
        "ShaderNodeTexImage",
        image=_image(os.path.join(base, "cherry_veneer_rough_2k.jpg"), "Non-Color"),
    )
    nor = t.node(
        "ShaderNodeTexImage",
        image=_image(os.path.join(base, "cherry_veneer_nor_gl_2k.jpg"), "Non-Color"),
    )
    for n in (diff, rgh, nor):
        t.link(mp.outputs[0], n.inputs[0])
    att = t.node("ShaderNodeAttribute", attribute_name="rand")
    r = att.outputs["Fac"]
    g = t.node("ShaderNodeGamma")
    t.link(diff.outputs[0], g.inputs[0])
    g.inputs[1].default_value = gamma
    hs = t.node("ShaderNodeHueSaturation")
    t.link(g.outputs[0], hs.inputs["Color"])
    t.set(hs.inputs["Hue"], t.maprange(r, 0, 1, 0.492, 0.508))
    t.set(
        hs.inputs["Saturation"],
        t.maprange(t.math("FRACT", t.math("MULTIPLY", r, 7.31)), 0, 1, 0.92, 1.08),
    )
    t.set(
        hs.inputs["Value"],
        t.maprange(
            t.math("FRACT", t.math("MULTIPLY", r, 3.17)), 0, 1, 1 - variation / 2, 1 + variation / 2
        ),
    )
    col = t.mixc(1.0, hs.outputs[0], rgb(*tint), "MULTIPLY")
    nm = t.node("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = normal
    t.link(nor.outputs[0], nm.inputs["Color"])
    ro = t.math("MULTIPLY", rgh.outputs[0], rough / 0.70, clamp=True)
    t.principled(
        **{
            "Base Color": col,
            "Roughness": ro,
            "Normal": nm.outputs[0],
            "Coat Weight": coat,
            "Coat Roughness": 0.25,
        }
    )
    _glb(
        t.mat, [c * 0.8 for c in tint], rough, 0.0, os.path.join(base, "cherry_veneer_diff_2k.jpg")
    )
    _cache[name] = t.mat
    return t.mat


def tile(
    name,
    color=(0.045, 0.043, 0.041),
    size=(0.6, 0.6),
    grout=(0.012, 0.012, 0.012),
    joint=0.003,
    rough=0.5,
    wet=0.0,
    offset=0.0,
    speckle=1.0,
    origin=(0.0, 0.0),
    bump=1.0,
    cloud=1.0,
):
    """Stone-look porcelain. Tri-planar tile grid in world metres; each tile gets its own mineral pattern."""
    if name in _cache:
        return _cache[name]
    t = NT(name)
    tc = t.node("ShaderNodeTexCoord")
    geo = t.node("ShaderNodeNewGeometry")
    p = t.node("ShaderNodeSeparateXYZ")
    t.link(tc.outputs["Object"], p.inputs[0])
    absn = t.node("ShaderNodeVectorMath", operation="ABSOLUTE")
    t.link(geo.outputs["True Normal"], absn.inputs[0])
    n = t.node("ShaderNodeSeparateXYZ")
    t.link(absn.outputs[0], n.inputs[0])
    sel_z = t.math("GREATER_THAN", n.outputs[2], 0.6)
    sel_x = t.math("GREATER_THAN", n.outputs[0], 0.6)

    def comb(a, b):
        c = t.node("ShaderNodeCombineXYZ")
        t.link(a, c.inputs[0])
        t.link(b, c.inputs[1])
        return c.outputs[0]

    v = t.mixv(
        sel_z,
        t.mixv(sel_x, comb(p.outputs[0], p.outputs[2]), comb(p.outputs[1], p.outputs[2])),
        comb(p.outputs[0], p.outputs[1]),
    )
    off = t.node("ShaderNodeVectorMath", operation="ADD")
    t.link(v, off.inputs[0])
    off.inputs[1].default_value = (-origin[0], -origin[1], 0)
    br = t.node("ShaderNodeTexBrick", offset=offset, offset_frequency=2, squash=1.0)
    t.link(off.outputs[0], br.inputs["Vector"])
    br.inputs["Color1"].default_value = rgb(0, 0, 0)
    br.inputs["Color2"].default_value = rgb(1, 1, 1)
    br.inputs["Mortar"].default_value = rgb(0.5, 0.5, 0.5)
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = joint
    br.inputs["Mortar Smooth"].default_value = 0.1
    br.inputs["Bias"].default_value = 0.0
    br.inputs["Brick Width"].default_value = size[0]
    br.inputs["Row Height"].default_value = size[1]
    tile_rand = t.node("ShaderNodeSeparateColor")
    t.link(br.outputs["Color"], tile_rand.inputs[0])
    tr = tile_rand.outputs[0]
    mortar = br.outputs["Fac"]
    # 3D pattern coordinate: in-plane position + per-tile jump along the third axis
    pc = t.node("ShaderNodeCombineXYZ")
    sv = t.node("ShaderNodeSeparateXYZ")
    t.link(v, sv.inputs[0])
    t.link(sv.outputs[0], pc.inputs[0])
    t.link(sv.outputs[1], pc.inputs[1])
    t.set(pc.inputs[2], t.math("MULTIPLY", tr, 53.0))
    cloud_n = t.node("ShaderNodeTexNoise")
    t.link(pc.outputs[0], cloud_n.inputs["Vector"])
    cloud_n.inputs["Scale"].default_value = 2.2
    cloud_n.inputs["Detail"].default_value = 7.0
    cloud_n.inputs["Roughness"].default_value = 0.62
    fine = t.node("ShaderNodeTexNoise")
    t.link(pc.outputs[0], fine.inputs["Vector"])
    fine.inputs["Scale"].default_value = 85.0
    fine.inputs["Detail"].default_value = 5.0
    fine.inputs["Roughness"].default_value = 0.7
    fleck = t.node("ShaderNodeTexVoronoi", feature="F1")
    t.link(pc.outputs[0], fleck.inputs["Vector"])
    fleck.inputs["Scale"].default_value = 260.0
    fleck_mask = t.maprange(fleck.outputs["Distance"], 0.0, 0.22, 1.0, 0.0)
    mid = t.node("ShaderNodeTexNoise")
    t.link(pc.outputs[0], mid.inputs["Vector"])
    mid.inputs["Scale"].default_value = 14.0
    mid.inputs["Detail"].default_value = 6.0
    mid.inputs["Roughness"].default_value = 0.65
    val = t.math(
        "ADD",
        t.maprange(cloud_n.outputs["Fac"], 0.25, 0.75, 1 - 0.42 * cloud, 1 + 0.42 * cloud),
        t.maprange(fine.outputs["Fac"], 0.3, 0.7, -0.28 * speckle, 0.28 * speckle),
    )
    val = t.math("ADD", val, t.maprange(mid.outputs["Fac"], 0.3, 0.7, -0.22 * cloud, 0.22 * cloud))
    val = t.math("ADD", val, t.math("MULTIPLY", t.math("POWER", fleck_mask, 3.0), 0.55 * speckle))
    val = t.math("MAXIMUM", t.math("MULTIPLY", val, t.maprange(tr, 0, 1, 0.88, 1.12)), 0.15)
    body = t.mixc(1.0, rgb(*color), val, "MULTIPLY")
    # warm/cool drift
    drift = t.mixc(
        t.maprange(cloud_n.outputs["Fac"], 0.3, 0.7, 0.0, 0.25),
        body,
        t.mixc(1.0, body, rgb(1.12, 1.0, 0.86), "MULTIPLY"),
    )
    col = t.mixc(mortar, drift, rgb(*grout))
    ro = t.math("ADD", rough, t.maprange(fine.outputs["Fac"], 0.3, 0.7, -0.07, 0.07))
    ro = t.math("ADD", ro, t.maprange(cloud_n.outputs["Fac"], 0.3, 0.7, -0.10, 0.10))
    ro = t.mixf(mortar, ro, 0.85)
    height = t.math(
        "ADD",
        t.math("MULTIPLY", mortar, -1.0),
        t.math("MULTIPLY", fine.outputs["Fac"], 0.10 * bump),
    )
    coat = 0.0
    if wet > 0:
        pud = t.node("ShaderNodeTexNoise")
        t.link(tc.outputs["Object"], pud.inputs["Vector"])
        pud.inputs["Scale"].default_value = 1.1
        pud.inputs["Detail"].default_value = 4.0
        pud.inputs["Roughness"].default_value = 0.5
        wetmask = t.maprange(pud.outputs["Fac"], 0.40, 0.66, 0.0, 1.0, smooth=True)
        wetmask = t.math("MULTIPLY", wetmask, sel_z)
        drop = t.node("ShaderNodeTexVoronoi", feature="F1")
        t.link(tc.outputs["Object"], drop.inputs["Vector"])
        drop.inputs["Scale"].default_value = 70.0
        drop.inputs["Randomness"].default_value = 1.0
        dn = t.node("ShaderNodeTexNoise")
        t.link(tc.outputs["Object"], dn.inputs["Vector"])
        dn.inputs["Scale"].default_value = 7.0
        dropmask = t.math(
            "MULTIPLY",
            t.maprange(drop.outputs["Distance"], 0.10, 0.20, 1.0, 0.0, smooth=True),
            t.maprange(dn.outputs["Fac"], 0.55, 0.66, 0.0, 1.0, smooth=True),
        )
        dropmask = t.math("MULTIPLY", dropmask, sel_z)
        # damp everywhere on horizontal faces; standing film where the mask is high
        damp_rough = t.math("MULTIPLY", ro, 1.0 - 0.55 * wet)
        ro = t.mixf(sel_z, ro, damp_rough)
        ro = t.mixf(t.math("MULTIPLY", wetmask, 0.85 * wet), ro, 0.05)
        ro = t.mixf(dropmask, ro, 0.03)
        col = t.mixc(t.math("MULTIPLY", sel_z, 0.18 * wet), col, rgb(0, 0, 0))
        col = t.mixc(t.math("MULTIPLY", wetmask, 0.20 * wet), col, rgb(0, 0, 0))
        height = t.math(
            "ADD",
            t.math(
                "MULTIPLY", height, t.math("SUBTRACT", 1.0, t.math("MULTIPLY", wetmask, 0.7 * wet))
            ),
            t.math("MULTIPLY", dropmask, 1.2),
        )
        coat = t.math(
            "MULTIPLY", t.math("MAXIMUM", t.math("MULTIPLY", wetmask, wet), dropmask), 0.8
        )
    bm = t.node("ShaderNodeBump")
    bm.inputs["Strength"].default_value = 0.6
    bm.inputs["Distance"].default_value = 0.0012
    t.link(height, bm.inputs["Height"])
    t.principled(
        **{
            "Base Color": col,
            "Roughness": ro,
            "Normal": bm.outputs[0],
            "Coat Weight": coat,
            "Coat Roughness": 0.03,
            "Specular IOR Level": 0.5,
        }
    )
    _glb(t.mat, color, rough)
    _cache[name] = t.mat
    return t.mat


def flat(name, color, rough=0.6, metal=0.0, aniso=0.0, coat=0.0):
    if name in _cache:
        return _cache[name]
    t = NT(name)
    nz = t.node("ShaderNodeTexNoise")
    tc = t.node("ShaderNodeTexCoord")
    t.link(tc.outputs["Object"], nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 30.0
    nz.inputs["Detail"].default_value = 4.0
    ro = t.math("ADD", rough, t.maprange(nz.outputs["Fac"], 0.3, 0.7, -0.05, 0.05))
    t.principled(
        **{
            "Base Color": rgb(*color),
            "Roughness": ro,
            "Metallic": metal,
            "Anisotropic": aniso,
            "Coat Weight": coat,
        }
    )
    _glb(t.mat, color, rough, metal)
    _cache[name] = t.mat
    return t.mat


def brushed(name, color=(0.30, 0.28, 0.26), rough=0.32):
    """Brushed dark stainless: streaky roughness along the tube (UV u = length)."""
    if name in _cache:
        return _cache[name]
    t = NT(name)
    uv = t.node("ShaderNodeUVMap", uv_map="UVMap")
    mp = t.node("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (3.0, 900.0, 1.0)
    t.link(uv.outputs[0], mp.inputs[0])
    nz = t.node("ShaderNodeTexNoise")
    t.link(mp.outputs[0], nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 1.0
    nz.inputs["Detail"].default_value = 3.0
    ro = t.math("ADD", rough, t.maprange(nz.outputs["Fac"], 0.3, 0.7, -0.10, 0.10))
    bm = t.node("ShaderNodeBump")
    bm.inputs["Strength"].default_value = 0.08
    bm.inputs["Distance"].default_value = 0.0005
    t.link(nz.outputs["Fac"], bm.inputs["Height"])
    t.principled(
        **{"Base Color": rgb(*color), "Roughness": ro, "Metallic": 1.0, "Normal": bm.outputs[0]}
    )
    _glb(t.mat, color, rough, 1.0)
    _cache[name] = t.mat
    return t.mat


def light(name, kelvin=2700.0, strength=10.0):
    key = (name, kelvin, strength)
    if key in _cache:
        return _cache[key]
    t = NT(name)
    bb = t.node("ShaderNodeBlackbody")
    bb.inputs[0].default_value = kelvin
    em = t.node("ShaderNodeEmission")
    t.link(bb.outputs[0], em.inputs["Color"])
    em.inputs["Strength"].default_value = strength
    # emit only from the front face so strips can sit against a surface
    geo = t.node("ShaderNodeNewGeometry")
    blk = t.node("ShaderNodeEmission")
    blk.inputs["Strength"].default_value = 0.0
    mix = t.node("ShaderNodeMixShader")
    t.link(geo.outputs["Backfacing"], mix.inputs[0])
    t.link(em.outputs[0], mix.inputs[1])
    t.link(blk.outputs[0], mix.inputs[2])
    t.link(mix.outputs[0], t.out.inputs["Surface"])
    _glb(t.mat, (1.0, 0.72, 0.42), 1.0, 0.0, emit=2.0)
    _cache[key] = t.mat
    return t.mat


def glass(name="glass", tint=(0.93, 0.90, 0.85), rough=0.015, frosted=0.0):
    if name in _cache:
        return _cache[name]
    t = NT(name)
    g = t.node("ShaderNodeBsdfGlass")
    g.inputs["Color"].default_value = rgb(*tint)
    g.inputs["Roughness"].default_value = max(rough, frosted)
    g.inputs["IOR"].default_value = 1.5
    tr = t.node("ShaderNodeBsdfTransparent")
    tr.inputs["Color"].default_value = rgb(*[c * 0.9 for c in tint])
    lp = t.node("ShaderNodeLightPath")
    mix = t.node("ShaderNodeMixShader")
    t.link(lp.outputs["Is Shadow Ray"], mix.inputs[0])
    t.link(g.outputs[0], mix.inputs[1])
    t.link(tr.outputs[0], mix.inputs[2])
    t.link(mix.outputs[0], t.out.inputs["Surface"])
    _glb(t.mat, tint, 0.05, 0.0, alpha=0.25)
    _cache[name] = t.mat
    return t.mat


def water(name="water", absorb=(0.42, 0.80, 0.88), density=0.55, shadow_transparent=False):
    if name in _cache:
        return _cache[name]
    t = NT(name)
    g = t.node("ShaderNodeBsdfGlass")
    g.inputs["Color"].default_value = rgb(1, 1, 1)
    g.inputs["Roughness"].default_value = 0.0
    g.inputs["IOR"].default_value = 1.333
    surf = g.outputs[0]
    if shadow_transparent:
        tr = t.node("ShaderNodeBsdfTransparent")
        tr.inputs["Color"].default_value = rgb(0.80, 0.88, 0.90)
        lp = t.node("ShaderNodeLightPath")
        mix = t.node("ShaderNodeMixShader")
        t.link(lp.outputs["Is Shadow Ray"], mix.inputs[0])
        t.link(g.outputs[0], mix.inputs[1])
        t.link(tr.outputs[0], mix.inputs[2])
        surf = mix.outputs[0]
    t.link(surf, t.out.inputs["Surface"])
    va = t.node("ShaderNodeVolumeAbsorption")
    va.inputs["Color"].default_value = rgb(*absorb)
    va.inputs["Density"].default_value = density
    t.link(va.outputs[0], t.out.inputs["Volume"])
    _glb(t.mat, (0.25, 0.42, 0.45), 0.05, 0.0, alpha=0.45)
    _cache[name] = t.mat
    return t.mat


def fabric(name="mat_fabric", color=(0.10, 0.092, 0.085), rib=260.0):
    """Woven rest-mat: ribbed weave bump in UV metres."""
    if name in _cache:
        return _cache[name]
    t = NT(name)
    uv = t.node("ShaderNodeUVMap", uv_map="UVMap")
    s = t.node("ShaderNodeSeparateXYZ")
    t.link(uv.outputs[0], s.inputs[0])
    wob = t.node("ShaderNodeTexNoise")
    t.link(uv.outputs[0], wob.inputs["Vector"])
    wob.inputs["Scale"].default_value = 40.0
    warp = t.math(
        "SINE",
        t.math(
            "ADD",
            t.math("MULTIPLY", s.outputs[1], rib),
            t.math("MULTIPLY", wob.outputs["Fac"], 1.2),
        ),
    )
    weft = t.math(
        "SINE",
        t.math(
            "ADD",
            t.math("MULTIPLY", s.outputs[0], rib * 2.4),
            t.math(
                "MULTIPLY",
                t.math("FLOOR", t.math("MULTIPLY", s.outputs[1], rib / 3.14159)),
                3.14159,
            ),
        ),
    )
    h = t.math("ADD", t.math("MULTIPLY", warp, 0.65), t.math("MULTIPLY", weft, 0.35))
    fuzz = t.node("ShaderNodeTexNoise")
    t.link(uv.outputs[0], fuzz.inputs["Vector"])
    fuzz.inputs["Scale"].default_value = 900.0
    h2 = t.math("ADD", h, t.math("MULTIPLY", fuzz.outputs["Fac"], 0.5))
    bm = t.node("ShaderNodeBump")
    bm.inputs["Strength"].default_value = 0.9
    bm.inputs["Distance"].default_value = 0.0018
    t.link(h2, bm.inputs["Height"])
    col = t.mixc(
        t.maprange(h, -1, 1, 0.0, 1.0),
        rgb(*[c * 0.55 for c in color]),
        rgb(*[c * 1.25 for c in color]),
    )
    blot = t.node("ShaderNodeTexNoise")
    t.link(uv.outputs[0], blot.inputs["Vector"])
    blot.inputs["Scale"].default_value = 3.0
    col = t.mixc(1.0, col, t.maprange(blot.outputs["Fac"], 0.3, 0.7, 0.88, 1.12), "MULTIPLY")
    t.principled(
        **{
            "Base Color": col,
            "Roughness": 0.92,
            "Normal": bm.outputs[0],
            "Sheen Weight": 0.5,
            "Sheen Roughness": 0.5,
        }
    )
    _glb(t.mat, color, 0.95)
    _cache[name] = t.mat
    return t.mat


# ---- shared palette -------------------------------------------------------
def palette():
    P = {}
    P["wood"] = wood("wood_sauna", tint=(0.56, 0.64, 0.50), gamma=1.15, rough=0.66)
    P["wood_bench"] = wood("wood_bench", tint=(0.60, 0.68, 0.54), gamma=1.12, rough=0.60)
    P["wood_dark"] = wood(
        "wood_ceiling_dark", tint=(0.20, 0.21, 0.18), gamma=1.3, rough=0.66, variation=0.3
    )
    P["wood_back"] = wood("wood_backing_dark", tint=(0.07, 0.065, 0.06), gamma=1.3, rough=0.85)
    P["wood_chair"] = wood(
        "wood_chair_charcoal", tint=(0.115, 0.12, 0.11), gamma=1.3, rough=0.50, variation=0.25
    )
    P["floor"] = tile(
        "tile_floor_charcoal", color=(0.095, 0.088, 0.080), size=(0.6, 0.6), rough=0.40
    )
    P["floor_wet"] = tile(
        "tile_floor_wet", color=(0.095, 0.088, 0.080), size=(0.6, 0.6), rough=0.42, wet=0.8
    )
    P["wall_stone"] = tile(
        "tile_wall_stone",
        color=(0.070, 0.062, 0.053),
        size=(1.2, 0.6),
        rough=0.55,
        offset=0.0,
        bump=1.6,
        cloud=0.55,
    )
    P["coping"] = tile(
        "tile_coping",
        color=(0.080, 0.074, 0.067),
        size=(2.0, 2.0),
        rough=0.40,
        wet=0.8,
        joint=0.0,
        cloud=0.7,
    )
    P["lining"] = tile(
        "tile_pool_lining",
        color=(0.050, 0.068, 0.074),
        size=(0.3, 0.3),
        rough=0.35,
        grout=(0.03, 0.04, 0.045),
        speckle=0.7,
        joint=0.0025,
        cloud=0.6,
    )
    P["plaster"] = flat("plaster_dark", (0.050, 0.047, 0.044), 0.9)
    P["struct"] = flat("structure_dark", (0.03, 0.03, 0.03), 0.9)
    P["black"] = flat("black_matte", (0.008, 0.008, 0.008), 0.85)
    P["steel"] = flat("steel_dark", (0.030, 0.027, 0.024), 0.42, metal=1.0)
    P["stainless"] = brushed("stainless_dark")
    P["glass"] = glass()
    P["water"] = water()
    P["water_warm"] = water("water_carbonated", absorb=(0.70, 0.84, 0.80), density=0.40)
    P["mirror"] = flat("mirror", (0.85, 0.85, 0.85), 0.03, metal=1.0)
    P["fabric"] = fabric()
    P["fabric_pillow"] = fabric("pillow_fabric", color=(0.115, 0.10, 0.09), rib=420.0)
    P["white"] = flat("ceramic_white", (0.75, 0.74, 0.72), 0.25)
    P["locker"] = wood("wood_locker", tint=(0.43, 0.50, 0.46), gamma=1.15, rough=0.6)
    return P
