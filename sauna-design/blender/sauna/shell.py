"""Building shell from the plan JSON plus reusable finish builders (slat walls, coves, ceilings, doors)."""

import math

from . import geo
from .geo import MB

T_BACK = 0.012  # backing panel behind slats
T_SLAT = 0.020
SLOT_W = 0.14  # cove slot width
SLOT_H = 0.14  # cove slot height above ceiling line


def split_openings(a0, a1, z0, z1, openings):
    """Rectangles of (run, z) covering [a0,a1]x[z0,z1] minus openings [(s0,s1,zlo,zhi)]."""
    cuts = sorted({a0, a1} | {max(a0, min(a1, v)) for o in openings for v in o[:2]})
    out = []
    for s0, s1 in zip(cuts, cuts[1:]):
        if s1 - s0 < 1e-6:
            continue
        mid = (s0 + s1) / 2
        hit = [o for o in openings if o[0] < mid < o[1]]
        if not hit:
            out.append((s0, s1, z0, z1))
            continue
        o = hit[0]
        if o[2] - z0 > 0.01:
            out.append((s0, s1, z0, o[2]))
        if z1 - o[3] > 0.01:
            out.append((s0, s1, o[3], z1))
    return out


def wall_box(mb, axis, fixed, sign, depth0, depth1, a0, a1, z0, z1, grain=None, rand=None):
    """Box on a wall: runs along axis at plane 'fixed', occupying depth0..depth1 measured into the room (sign)."""
    d0, d1 = fixed + sign * depth0, fixed + sign * depth1
    if axis == "x":
        mb.box(a0, d0, z0, a1, d1, z1, grain, rand)
    else:
        mb.box(d0, a0, z0, d1, a1, z1, grain, rand)


def slat_wall(
    mb,
    mb_back,
    axis,
    fixed,
    sign,
    a0,
    a1,
    z0,
    z1,
    openings=(),
    w=0.042,
    gap=0.008,
    t=T_SLAT,
    tb=T_BACK,
):
    """Vertical timber slats on a dark backing. Returns the finished face offset from the structural face."""
    for s0, s1, lo, hi in split_openings(a0, a1, z0, z1, openings):
        wall_box(mb_back, axis, fixed, sign, 0.0, tb, s0, s1, lo, hi)
    n = max(1, int((a1 - a0 + gap) / (w + gap)))
    pitch = (a1 - a0) / n
    for i in range(n):
        s0 = a0 + i * pitch + (pitch - w) / 2
        s1 = s0 + w
        for p0, p1, lo, hi in split_openings(
            s0, s1, z0, z1, [o for o in openings if o[0] < s1 and o[1] > s0]
        ):
            if p1 - p0 < w * 0.6:
                continue
            wall_box(mb, axis, fixed, sign, tb, tb + t, p0, p1, lo, hi, grain="z")
    return tb + t


def panel_wall(mb, axis, fixed, sign, a0, a1, z0, z1, openings=(), t=0.012):
    for s0, s1, lo, hi in split_openings(a0, a1, z0, z1, openings):
        wall_box(mb, axis, fixed, sign, 0.0, t, s0, s1, lo, hi)
    return t


def slat_ceiling(mb, mb_back, x0, y0, x1, y1, z, along="x", w=0.07, gap=0.022, t=0.018):
    """Dark timber ceiling slats (underside at z) below a black backing."""
    mb_back.box(x0, y0, z + t + 0.012, x1, y1, z + t + 0.03)
    if along == "x":
        n = max(1, int((y1 - y0 + gap) / (w + gap)))
        pitch = (y1 - y0) / n
        for i in range(n):
            c = y0 + (i + 0.5) * pitch
            mb.box(x0, c - w / 2, z, x1, c + w / 2, z + t, grain="x")
    else:
        n = max(1, int((x1 - x0 + gap) / (w + gap)))
        pitch = (x1 - x0) / n
        for i in range(n):
            c = x0 + (i + 0.5) * pitch
            mb.box(c - w / 2, y0, z, c + w / 2, y1, z + t, grain="y")


def cove(
    coll,
    mb_black,
    light_mat,
    axis,
    face,
    sign,
    a0,
    a1,
    z,
    name,
    width=0.05,
    inset=0.075,
    mode="down",
    slot=SLOT_W,
):
    """Ceiling reveal with a hidden LED strip along a wall. face = finished wall face coordinate.
    mode "down": strip at the slot top shining down the wall (visible only from directly below).
    mode "wall": strip on the ceiling-edge upstand facing the wall (never visible from the room)."""
    zt = z + SLOT_H
    if mode == "down":
        c = face + sign * inset
        e0, e1 = c - width / 2, c + width / 2
        quad = [(e0, zt - 0.012), (e1, zt - 0.012)]
    else:
        e = face + sign * (slot - 0.004)
        quad = [(e, z + 0.06), (e, z + 0.06 + width)]
    (d0, z0), (d1, z1) = quad
    if axis == "x":
        pts = [(a0, d0, z0), (a0, d1, z1), (a1, d1, z1), (a1, d0, z0)]
        mb_black.box(a0, face, zt, a1, face + sign * slot, zt + 0.02)
        mb_black.box(a0, face + sign * slot, z + 0.0, a1, face + sign * (slot + 0.018), zt + 0.02)
        for a in (a0, a1):
            mb_black.box(a - 0.004, face, z + 0.001, a + 0.004, face + sign * slot, zt)
        want = (0.0, -sign, 0.0) if mode == "wall" else (0.0, 0.0, -1.0)
    else:
        pts = [(d0, a0, z0), (d1, a0, z1), (d1, a1, z1), (d0, a1, z0)]
        mb_black.box(face, a0, zt, face + sign * slot, a1, zt + 0.02)
        mb_black.box(face + sign * slot, a0, z + 0.0, face + sign * (slot + 0.018), a1, zt + 0.02)
        for a in (a0, a1):
            mb_black.box(face, a - 0.004, z + 0.001, face + sign * slot, a + 0.004, zt)
        want = (-sign, 0.0, 0.0) if mode == "wall" else (0.0, 0.0, -1.0)
    ob = geo.emitter(name, coll, light_mat, pts)
    me = ob.data
    me.update()
    n = me.polygons[0].normal
    if n.x * want[0] + n.y * want[1] + n.z * want[2] < 0:
        me.flip_normals()
    return ob


def strip_down(coll, light_mat, name, x0, y0, x1, y1, z):
    """Horizontal down-facing emitter rectangle."""
    ob = geo.emitter(name, coll, light_mat, [(x0, y0, z), (x0, y1, z), (x1, y1, z), (x1, y0, z)])
    ob.data.update()
    if ob.data.polygons[0].normal.z > 0:
        ob.data.flip_normals()
    return ob


def downlight(mb_trim, coll, light_mat, name, x, y, z, r=0.038, drop=0.045):
    """Small surface downlight below the ceiling plane z: dark cylinder with a recessed emitter disc."""
    import bpy

    mb_trim.lathe(
        [(r, -0.014), (r, -drop), (r + 0.012, -drop), (r + 0.012, 0.0)],
        (x, y, z),
        seg=24,
        cap_top=False,
        cap_bottom=False,
    )
    n = 16
    me = bpy.data.meshes.new(name)
    verts = [
        (
            x + r * 0.96 * math.cos(2 * math.pi * k / n),
            y + r * 0.96 * math.sin(2 * math.pi * k / n),
            z - 0.016,
        )
        for k in range(n)
    ]
    me.from_pydata(verts, [], [tuple(range(n))])
    me.materials.append(light_mat)
    me.update()
    if me.polygons[0].normal.z > 0:
        me.flip_normals()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


# ---------------------------------------------------------------------------
def build_structure(plan, P, coll, rng_before_roof=None):
    """Structural walls with door openings, floors (with pool cut-outs), roof slab.
    rng_before_roof: stream position for the roof / base slabs (the floor pieces before them depend on the pool rectangles)."""
    th = plan["wallThickness"]
    H = plan["structureHeight"]
    dh = plan["doorHeight"]
    mb = MB("Structure_Walls", P["plaster"], coll, bevel=0)
    segs = list(plan["walls"]) + [w["seg"] for w in plan.get("addedWalls", [])]
    for x0, y0, x1, y1 in segs:
        horiz = abs(y1 - y0) < 1e-9
        a0, a1 = (min(x0, x1), max(x0, x1)) if horiz else (min(y0, y1), max(y0, y1))
        fixed = y0 if horiz else x0
        ops = []
        for d in plan["doors"]:
            dx0, dy0, dx1, dy1 = d["seg"]
            dh_horiz = abs(dy1 - dy0) < 1e-9
            if dh_horiz != horiz:
                continue
            if abs((dy0 if horiz else dx0) - fixed) > 1e-6:
                continue
            s0, s1 = (min(dx0, dx1), max(dx0, dx1)) if horiz else (min(dy0, dy1), max(dy0, dy1))
            if s0 >= a0 - 1e-6 and s1 <= a1 + 1e-6:
                ops.append((s0, s1, 0.0, dh))
        for o in plan.get(
            "openings", []
        ):  # non-door wall openings (e.g. the glazed TV recess), with a sill
            ox0, oy0, ox1, oy1 = o["seg"]
            if (abs(oy1 - oy0) < 1e-9) != horiz or abs((oy0 if horiz else ox0) - fixed) > 1e-6:
                continue
            s0, s1 = (min(ox0, ox1), max(ox0, ox1)) if horiz else (min(oy0, oy1), max(oy0, oy1))
            if s0 >= a0 - 1e-6 and s1 <= a1 + 1e-6:
                ops.append((s0, s1, o["z"][0], o["z"][1]))
        for s0, s1, lo, hi in split_openings(a0 - th / 2, a1 + th / 2, 0.0, H, ops):
            if horiz:
                mb.box(s0, fixed - th / 2, lo, s1, fixed + th / 2, hi)
            else:
                mb.box(fixed - th / 2, s0, lo, fixed + th / 2, s1, hi)
    mb.finish(weighted=False)

    # floors
    floor_mat = {"dry": P["floor"], "damp": P["floor"], "wet": P["floor_wet"]}
    builders = {}
    for room in plan["rooms"]:
        x, y, w, d = room["rect"]
        key = room["floor"]
        fb = builders.setdefault(
            key, MB(f"Floor_{key}", floor_mat[key], coll, bevel=0, smooth=False)
        )
        holes = [p["rect"] for p in plan["pools"] if p["room"] == room["id"]]
        xs = sorted({x, x + w} | {v for h in holes for v in (h[0], h[0] + h[2])})
        ys = sorted({y, y + d} | {v for h in holes for v in (h[1], h[1] + h[3])})
        for xa, xb in zip(xs, xs[1:]):
            for ya, yb in zip(ys, ys[1:]):
                cx, cy = (xa + xb) / 2, (ya + yb) / 2
                if any(h[0] < cx < h[0] + h[2] and h[1] < cy < h[1] + h[3] for h in holes):
                    continue
                fb.quad([(xa, ya, 0), (xb, ya, 0), (xb, yb, 0), (xa, yb, 0)])
    for fb in builders.values():
        fb.finish(weighted=False)

    if rng_before_roof is not None:
        geo.jump(rng_before_roof)
    roof = MB("Structure_Roof", P["struct"], geo.collection("Ceilings", coll), bevel=0)
    roof.box(-0.1, -0.1, H, plan["width"] + 0.1, plan["height"] + 0.1, H + 0.15)
    roof.finish(weighted=False)
    ground = MB("Structure_Base", P["struct"], coll, bevel=0)
    ground.box(-0.1, -0.1, -1.75, plan["width"] + 0.1, plan["height"] + 0.1, -1.6)
    ground.finish(weighted=False)


def plain_ceiling(room, P, coll, inset=0.08):
    x, y, w, d = room["rect"]
    mb = MB(f"Ceiling_{room['id']}", P["plaster"], geo.collection("Ceilings", coll), bevel=0)
    mb.box(
        x + inset, y + inset, room["ceiling"], x + w - inset, y + d - inset, room["ceiling"] + 0.03
    )
    mb.finish(weighted=False)


def door(plan, d, P, coll, frame_depth=0.26):
    """Door set in a wall opening. kinds: sauna/glass/entry = glazed leaf with timber frame; timber = solid leaf."""
    x0, y0, x1, y1 = d["seg"]
    horiz = abs(y1 - y0) < 1e-9
    a0, a1 = (min(x0, x1), max(x0, x1)) if horiz else (min(y0, y1), max(y0, y1))
    fixed = y0 if horiz else x0
    axis = "x" if horiz else "y"
    dh = plan["doorHeight"]
    name = d.get("id", f"{x0}_{y0}")
    fr = MB(f"Door_{name}_frame", P["wood"], coll, bevel=0.003)
    jw = 0.05
    fd = frame_depth / 2

    def wb(mb, s0, s1, dep0, dep1, z0, z1, grain=None):
        wall_box(mb, axis, fixed, 1, dep0, dep1, s0, s1, z0, z1, grain)

    wb(fr, a0, a0 + jw, -fd, fd, 0, dh, "z")
    wb(fr, a1 - jw, a1, -fd, fd, 0, dh, "z")
    wb(fr, a0 + jw, a1 - jw, -fd, fd, dh - jw, dh)
    fr.finish()
    l0, l1 = a0 + jw + 0.004, a1 - jw - 0.004
    zt = dh - jw - 0.004
    if d["kind"] == "timber":
        leaf = MB(f"Door_{name}_leaf", P["wood_dark"], coll, bevel=0.003)
        wb(leaf, l0, l1, -0.02, 0.02, 0.008, zt, "z")
        leaf.finish()
    else:
        gl = MB(f"Door_{name}_glass", P["glass"], coll, bevel=0.0015, segments=1)
        wb(gl, l0, l1, -0.005, 0.005, 0.012, zt)
        gl.finish()
        hd = MB(f"Door_{name}_handle", P["wood_bench"], coll, bevel=0.006, segments=3)
        st = MB(f"Door_{name}_standoff", P["stainless"], coll, bevel=0)
        hs = l1 - 0.11
        for side in (-1, 1):
            wb(hd, hs - 0.02, hs + 0.02, side * 0.045, side * 0.075, 0.82, 1.32, "z")
            for hz in (0.90, 1.24):
                c = (hs, fixed + side * 0.025, hz) if horiz else (fixed + side * 0.025, hs, hz)
                e = (hs, fixed + side * 0.047, hz) if horiz else (fixed + side * 0.047, hs, hz)
                st.tube([c, e], 0.008, seg=10)
        hd.finish()
        st.finish(weighted=False)
        # hinges / patch fittings
        hg = MB(f"Door_{name}_fittings", P["stainless"], coll, bevel=0.001, segments=1)
        for hz in (0.22, zt - 0.22):
            wb(hg, l0 - 0.004, l0 + 0.05, -0.012, 0.012, hz - 0.045, hz + 0.045)
        hg.finish()
