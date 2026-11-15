"""Reusable furniture: sauna benches, backrests, stone heater with guard, loungers, lying platforms."""

import math
import os

import bpy
from mathutils import Matrix, Vector

from . import geo, shell
from .geo import MB

AX = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}


class Frame:
    """Axis-aligned local frame: u along a run, v from front to back, z up."""

    def __init__(self, ox, oy, u="+x", v="+y"):
        self.o = (ox, oy)
        self.u, self.v = AX[u], AX[v]
        self.un, self.vn = u, v

    def xy(self, u, v):
        return (
            self.o[0] + self.u[0] * u + self.v[0] * v,
            self.o[1] + self.u[1] * u + self.v[1] * v,
        )

    def pt(self, u, v, z):
        x, y = self.xy(u, v)
        return (x, y, z)

    def box(self, mb, u0, u1, v0, v1, z0, z1, grain="u", rand=None):
        xa, ya = self.xy(u0, v0)
        xb, yb = self.xy(u1, v1)
        g = {"u": self.un[1], "v": self.vn[1], "z": "z"}[grain]
        mb.box(min(xa, xb), min(ya, yb), z0, max(xa, xb), max(ya, yb), z1, g, rand)

    def wall(self, v):
        """(axis, fixed, sign) of a plane at depth v facing the front (-v)."""
        x, y = self.xy(0, v)
        if self.vn[1] == "y":
            return "x", y, -self.v[1]
        return "y", x, -self.v[0]

    def run(self, u0, u1):
        a = self.xy(u0, 0)
        b = self.xy(u1, 0)
        i = 0 if self.un[1] == "x" else 1
        return min(a[i], b[i]), max(a[i], b[i])


BOARD_T = 0.028
APRON_H = 0.11


def bench_tier(
    F,
    L,
    depth,
    top,
    base,
    mbs,
    coll,
    light_mat,
    name,
    riser_v=0.10,
    riser_run=None,
    legs=None,
    joints=(),
    cheeks=(False, False),
    led=True,
    bw=0.092,
    gap=0.008,
):
    """One bench tier. F origin = front edge start. mbs: boards, frame, slat, back MeshBuilders."""
    n = max(1, round((depth + gap) / (bw + gap)))
    w = (depth - (n - 1) * gap) / n
    cuts = [0.0] + sorted(j for j in joints if 0.05 < j < L - 0.05) + [L]
    zb = top - BOARD_T
    for i in range(n):
        v0 = i * (w + gap)
        for u0, u1 in zip(cuts, cuts[1:]):
            F.box(mbs["boards"], u0 + 0.0015, u1 - 0.0015, v0, v0 + w, zb, top, "u")
    for u0, u1 in zip(cuts, cuts[1:]):
        F.box(mbs["frame"], u0 + 0.001, u1 - 0.001, 0.03, 0.058, zb - APRON_H, zb, "u")
    # bearers
    nb = max(2, int(L / 0.55) + 1)
    for k in range(nb):
        u = 0.04 + (L - 0.08) * k / (nb - 1)
        F.box(mbs["frame"], u - 0.022, u + 0.022, 0.10, depth - 0.005, zb - 0.07, zb, "v")
    for u in legs if legs is not None else [0.06, L - 0.06]:
        F.box(mbs["frame"], u - 0.045, u + 0.045, 0.03, 0.12, base, zb - APRON_H, "z")
    if riser_v is not None:
        r0, r1 = riser_run if riser_run else (0.0, L)
        axis, fixed, sign = F.wall(riser_v + shell.T_BACK + shell.T_SLAT)
        a0, a1 = F.run(r0, r1)
        shell.slat_wall(mbs["slat"], mbs["back"], axis, fixed, sign, a0, a1, base, zb - 0.002)
    for flag, u in zip(cheeks, (0.0, L)):
        if flag:
            s = 1 if u == 0.0 else -1
            F.box(mbs["frame"], u + s * 0.004, u + s * 0.032, 0.058, depth, zb - APRON_H, zb, "v")
            if riser_v is not None:
                F.box(
                    mbs["back"],
                    u + s * 0.004,
                    u + s * 0.016,
                    riser_v,
                    depth,
                    base,
                    zb - APRON_H,
                    "v",
                )
    if led:
        a = F.xy(0.06, 0.066)
        b = F.xy(L - 0.06, 0.090)
        shell.strip_down(
            coll,
            light_mat,
            f"LED_{name}",
            min(a[0], b[0]),
            min(a[1], b[1]),
            max(a[0], b[0]),
            max(a[1], b[1]),
            zb - 0.012,
        )


def backrest(F, L, z0, mbs, joints=(), n=3, bw=0.09, gap=0.015, standoff=0.018, t=0.022):
    """Horizontal backrest boards on battens. F origin on the finished wall face, v pointing into the room."""
    cuts = [0.0] + sorted(j for j in joints if 0.05 < j < L - 0.05) + [L]
    for i in range(n):
        z = z0 + i * (bw + gap)
        for u0, u1 in zip(cuts, cuts[1:]):
            F.box(mbs["boards"], u0 + 0.0015, u1 - 0.0015, standoff, standoff + t, z, z + bw, "u")
    nb = max(2, int(L / 0.6) + 1)
    for k in range(nb):
        u = 0.08 + (L - 0.16) * k / (nb - 1)
        F.box(
            mbs["frame"],
            u - 0.015,
            u + 0.015,
            0.0,
            standoff,
            z0 + 0.006,
            z0 + n * (bw + gap) - gap - 0.006,
            "z",
        )


# ---- rocks -----------------------------------------------------------------
_rocks = []


def load_rocks(
    asset_root,
    ids=("moon_rock_02", "moon_rock_03", "moon_rock_04", "moon_rock_06"),
    darken=(0.42, 0.36, 0.30),
):
    if _rocks:
        return _rocks
    for rid in ids:
        path = os.path.join(asset_root, "polyhaven", rid, f"{rid}_1k.gltf")
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=path)
        new = [o for o in bpy.data.objects if o not in before]
        for o in new:
            if o.type == "MESH":
                me = o.data
                me.transform(o.matrix_world)
                vs = [v.co.copy() for v in me.vertices]
                lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
                hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
                size = max(hi - lo)
                me.transform(Matrix.Scale(1.0 / size, 4) @ Matrix.Translation(-(lo + hi) / 2))
                me.name = f"rock_{rid}"
                for m in me.materials:
                    nt = m.node_tree
                    bsdf = next((nd for nd in nt.nodes if nd.type == "BSDF_PRINCIPLED"), None)
                    if bsdf and bsdf.inputs["Base Color"].links:
                        src = bsdf.inputs["Base Color"].links[0].from_socket
                        mx = nt.nodes.new("ShaderNodeMix")
                        mx.data_type = "RGBA"
                        mx.blend_type = "MULTIPLY"
                        mx.inputs[0].default_value = 1.0
                        nt.links.new(src, mx.inputs[6])
                        mx.inputs[7].default_value = (*darken, 1.0)
                        nt.links.new(mx.outputs[2], bsdf.inputs["Base Color"])
                    m["glb_color"] = [0.12, 0.115, 0.11]
                    m["glb_rough"] = 0.9
                    m["glb_metal"] = 0.0
                    m["glb_image"] = ""
                    m["glb_emit"] = 0.0
                    m["glb_alpha"] = 1.0
                _rocks.append(me)
            bpy.data.objects.remove(o, do_unlink=True)
    return _rocks


def rock_pile(coll, name, cx, cy, z0, z1, r_in, r_out, size=(0.10, 0.155), heap=0.07):
    """Instanced stones filling a cylindrical basket shell (outer layers + heaped top)."""
    rocks = _rocks
    count = 0

    def put(x, y, z, s):
        nonlocal count
        me = rocks[int(geo.rnd() * len(rocks)) % len(rocks)]
        ob = bpy.data.objects.new(f"{name}_{count:03d}", me)
        rot = (
            Matrix.Rotation(geo.rnd() * 6.283, 4, "Z")
            @ Matrix.Rotation(geo.rnd() * 6.283, 4, "X")
            @ Matrix.Rotation(geo.rnd() * 6.283, 4, "Y")
        )
        sc = Matrix.Diagonal(
            (
                s * (0.85 + 0.3 * geo.rnd()),
                s * (0.85 + 0.3 * geo.rnd()),
                s * (0.8 + 0.3 * geo.rnd()),
                1.0,
            )
        )
        ob.matrix_world = Matrix.Translation((x, y, z)) @ rot @ sc
        coll.objects.link(ob)
        count += 1

    z = z0 + 0.05
    while z < z1:
        for rr in (r_out - 0.065, r_out - 0.16):
            if rr < r_in + 0.03:
                continue
            n = int(2 * math.pi * rr / 0.098)
            ph = geo.rnd() * 6.283
            for k in range(n):
                a = ph + 2 * math.pi * (k + 0.5 * geo.rnd()) / n
                r = rr + (geo.rnd() - 0.5) * 0.03
                put(
                    cx + r * math.cos(a),
                    cy + r * math.sin(a),
                    z + (geo.rnd() - 0.5) * 0.03,
                    size[0] + geo.rnd() * (size[1] - size[0]),
                )
        z += 0.078
    # heaped top
    for rr in (0.0, 0.10, 0.20, 0.29):
        n = max(1, int(2 * math.pi * rr / 0.10))
        ph = geo.rnd() * 6.283
        for k in range(n):
            a = ph + 2 * math.pi * k / n
            zz = z1 + heap * (1 - (rr / 0.33) ** 2) + (geo.rnd() - 0.3) * 0.03
            put(
                cx + rr * math.cos(a),
                cy + rr * math.sin(a),
                zz,
                size[0] + geo.rnd() * (size[1] - size[0]),
            )
    return count


def heater(P, coll, name, cx, cy, r=0.42, h=1.05, guard_r=0.74, guard_h=0.82, guard_skip=()):
    """Cylindrical stone heater: plinth, core, bar cage, stones, and a timber/steel guard rail."""
    st = MB(f"{name}_steel", P["steel"], coll, bevel=0.0015, segments=1)
    st.lathe([(r + 0.05, 0.0), (r + 0.05, 0.10), (r + 0.03, 0.12)], (cx, cy, 0), seg=64)
    st.lathe([(r - 0.17, 0.12), (r - 0.17, h - 0.06)], (cx, cy, 0), seg=32)
    for zc in (0.13, 0.13 + (h - 0.13) * 0.5, h):
        st.lathe(
            [
                (r + 0.022, zc - 0.018),
                (r + 0.034, zc - 0.018),
                (r + 0.034, zc + 0.018),
                (r + 0.022, zc + 0.018),
                (r + 0.022, zc - 0.018),
            ],
            (cx, cy, 0),
            seg=64,
            cap_top=False,
            cap_bottom=False,
        )
    nb = 30
    for k in range(nb):
        a = 2 * math.pi * k / nb
        M = Matrix.Translation(
            (cx + (r + 0.016) * math.cos(a), cy + (r + 0.016) * math.sin(a), (0.12 + h + 0.02) / 2)
        ) @ Matrix.Rotation(a, 4, "Z")
        st.box_m((0.012, 0.028, h + 0.02 - 0.12), M, grain=2)
    st.finish()
    rock_pile(
        geo.collection(f"{name}_stones", coll),
        f"{name}_stone",
        cx,
        cy,
        0.12,
        h - 0.03,
        r - 0.17,
        r + 0.01,
    )
    # guard: octagon of timber rails on steel posts
    gp = MB(f"{name}_guard_posts", P["steel"], coll, bevel=0.002, segments=1)
    gr = MB(f"{name}_guard_rails", P["wood_bench"], coll, bevel=0.005, segments=3)
    n = 8
    verts = [
        (
            cx + guard_r * math.cos(math.pi / 8 + 2 * math.pi * k / n),
            cy + guard_r * math.sin(math.pi / 8 + 2 * math.pi * k / n),
        )
        for k in range(n)
    ]
    for k in range(n):
        a, b = Vector(verts[k]), Vector(verts[(k + 1) % n])
        if k not in guard_skip:
            mid = (a + b) / 2
            ang = math.atan2(b.y - a.y, b.x - a.x)
            for z in (guard_h - 0.035, guard_h * 0.5):
                M = Matrix.Translation((mid.x, mid.y, z)) @ Matrix.Rotation(ang, 4, "Z")
                gr.box_m(((b - a).length - 0.012, 0.042, 0.07), M, grain=0)
        if k not in guard_skip or (k - 1) % n not in guard_skip:
            gp.box(a.x - 0.02, a.y - 0.02, 0, a.x + 0.02, a.y + 0.02, guard_h + 0.0, "z")
            gp.lathe([(0.05, 0.0), (0.05, 0.006)], (a.x, a.y, 0), seg=16)
    gp.finish()
    gr.finish()


def floor_drain(P, coll, name, x, y, s=0.15):
    mb = MB(name, P["stainless"], coll, bevel=0.0008, segments=1)
    mb.box(x - s / 2, y - s / 2, -0.002, x + s / 2, y - s / 2 + 0.012, 0.0025)
    mb.box(x - s / 2, y + s / 2 - 0.012, -0.002, x + s / 2, y + s / 2, 0.0025)
    mb.box(x - s / 2, y - s / 2, -0.002, x - s / 2 + 0.012, y + s / 2, 0.0025)
    mb.box(x + s / 2 - 0.012, y - s / 2, -0.002, x + s / 2, y + s / 2, 0.0025)
    nb = 7
    for k in range(nb):
        yy = y - s / 2 + 0.012 + (s - 0.024) * (k + 0.5) / nb
        mb.box(x - s / 2 + 0.012, yy - 0.004, -0.002, x + s / 2 - 0.012, yy + 0.004, 0.0015)
    mb.finish()
    pit = MB(name + "_pit", P["black"], coll, bevel=0)
    pit.box(
        x - s / 2 + 0.002, y - s / 2 + 0.002, -0.004, x + s / 2 - 0.002, y + s / 2 - 0.002, 0.0003
    )
    pit.finish(weighted=False)


def grille(
    P, coll, name, axis, fixed, sign, a0, a1, z0, z1, depth=0.035, blades=5, mat="wood_dark"
):
    """Louvred vent grille on a wall: black recess + inclined blades."""
    bk = MB(name + "_recess", P["black"], coll, bevel=0)
    shell.wall_box(bk, axis, fixed, sign, 0.0, depth - 0.02, a0, a1, z0, z1)
    bk.finish(weighted=False)
    mb = MB(name, P[mat], coll, bevel=0.0015, segments=1)
    shell.wall_box(mb, axis, fixed, sign, 0.0, depth, a0 - 0.02, a0, z0 - 0.02, z1 + 0.02, "z")
    shell.wall_box(mb, axis, fixed, sign, 0.0, depth, a1, a1 + 0.02, z0 - 0.02, z1 + 0.02, "z")
    shell.wall_box(mb, axis, fixed, sign, 0.0, depth, a0, a1, z0 - 0.02, z0)
    shell.wall_box(mb, axis, fixed, sign, 0.0, depth, a0, a1, z1, z1 + 0.02)
    for k in range(blades):
        z = z0 + (z1 - z0) * (k + 0.5) / blades
        shell.wall_box(
            mb, axis, fixed, sign, depth - 0.022, depth - 0.004, a0, a1, z - 0.012, z + 0.012
        )
    mb.finish()


# ---- rest furniture ----------------------------------------------------------
LOUNGER_PROFILE = [
    (0.00, 0.285),
    (0.22, 0.335),
    (0.50, 0.395),
    (0.76, 0.355),
    (0.95, 0.300),
    (1.16, 0.385),
    (1.42, 0.590),
    (1.66, 0.790),
    (1.80, 0.885),
]
CHAIR_PROFILE = [
    (0.00, 0.395),
    (0.18, 0.415),
    (0.40, 0.375),
    (0.50, 0.365),
    (0.60, 0.50),
    (0.69, 0.72),
    (0.76, 0.96),
]


def slat_seat(
    mbs,
    ox,
    oy,
    heading,
    profile=LOUNGER_PROFILE,
    width=0.62,
    legs=((0.20, 0.0), (1.02, 0.0)),
    slat=0.046,
    gap=0.017,
    rail=(0.032, 0.058),
):
    """Curved slatted lounger/chair. Origin = foot end centre on the floor; heading = unit (dx, dy) from foot to head."""
    hx, hy = heading
    lat = Vector((hy, -hx, 0.0))
    fwd = Vector((hx, hy, 0.0))
    up = Vector((0, 0, 1))
    pts2 = geo.smooth_curve(profile, 10)

    def P(l, s, z):
        return Vector((ox, oy, 0.0)) + lat * l + fwd * s + up * z

    tang, norm = [], []
    for i, p in enumerate(pts2):
        a = pts2[max(0, i - 1)]
        b = pts2[min(len(pts2) - 1, i + 1)]
        t = (b - a).normalized()
        tang.append(t)
        norm.append(Vector((-t.y, t.x)))
    # side rails
    for side in (-1, 1):
        l = side * (width / 2 - 0.05)
        path = [P(l, p.x, p.y - rail[1] / 2 - 0.004) for p in pts2]
        nrm = [fwd * n.x + up * n.y for n in norm]
        mbs["frame"].sweep_rect(path, nrm, lat, rail[0], rail[1])
    # slats along the arc
    acc, last = 0.0, pts2[0]
    next_at = slat / 2 + 0.004
    for i, p in enumerate(pts2[1:], 1):
        seg = (p - last).length
        while acc + seg >= next_at:
            u = (next_at - acc) / seg
            q = last + (p - last) * u
            t = (tang[i - 1] + (tang[i] - tang[i - 1]) * u).normalized()
            n = Vector((-t.y, t.x))
            c = P(0, q.x, q.y) + (fwd * n.x + up * n.y) * 0.009
            M = geo.basis(c, lat, fwd * t.x + up * t.y, fwd * n.x + up * n.y)
            mbs["slats"].box_m((width, slat, 0.018), M, grain=0)
            next_at += slat + gap
        acc += seg
        last = p
    # legs + stretchers
    for s_leg, splay in legs:
        zc = _profile_z(pts2, s_leg) - rail[1] - 0.004
        for side in (-1, 1):
            l = side * (width / 2 - 0.05)
            top = P(l, s_leg, zc + 0.02)
            bot = P(l + side * 0.015, s_leg + splay, 0.0)
            mid = (top + bot) / 2
            zdir = (top - bot).normalized()
            ydir = (fwd - zdir * fwd.dot(zdir)).normalized()
            xdir = ydir.cross(zdir)
            mbs["frame"].box_m(
                (0.034, 0.055, (top - bot).length), geo.basis(mid, xdir, ydir, zdir), grain=2
            )
        a = P(-(width / 2 - 0.05), s_leg + splay * 0.5, zc * 0.45)
        b = P((width / 2 - 0.05), s_leg + splay * 0.5, zc * 0.45)
        mbs["frame"].box_m(
            ((b - a).length, 0.03, 0.045), geo.basis((a + b) / 2, lat, fwd, up), grain=0
        )


def _profile_z(pts2, s):
    for a, b in zip(pts2, pts2[1:]):
        if a.x <= s <= b.x:
            return a.y + (b.y - a.y) * (s - a.x) / max(1e-9, b.x - a.x)
    return pts2[-1].y


def fin_screen(mb, axis, a, b0, b1, z1, n=None, fin=(0.035, 0.11), pitch=0.125):
    """Floor-to-ceiling privacy fins in a row along axis ('x' or 'y') at cross coordinate a."""
    n = n or max(2, int((b1 - b0) / pitch) + 1)
    for k in range(n):
        c = b0 + (b1 - b0) * k / (n - 1)
        if axis == "y":
            mb.box(a - fin[1] / 2, c - fin[0] / 2, 0.0, a + fin[1] / 2, c + fin[0] / 2, z1, "z")
        else:
            mb.box(c - fin[0] / 2, a - fin[1] / 2, 0.0, c + fin[0] / 2, a + fin[1] / 2, z1, "z")
    if axis == "y":
        mb.box(a - fin[1] / 2 - 0.005, b0 - 0.02, 0.0, a + fin[1] / 2 + 0.005, b1 + 0.02, 0.04, "y")
    else:
        mb.box(b0 - 0.02, a - fin[1] / 2 - 0.005, 0.0, b1 + 0.02, a + fin[1] / 2 + 0.005, 0.04, "x")


def lying_platform(
    P, coll, lights, light_mat, name, x0, x1, y_front, y_wall, n=6, top=0.40, mats=True
):
    """Row of timber lying trays on a recessed plinth with a concealed light under the front edge; heads at the wall."""
    body = MB(f"{name}_trays", P["wood_bench"], coll, bevel=0.004, segments=3)
    plinth = MB(f"{name}_plinth", P["wood_back"], coll, bevel=0)
    mat = MB(f"{name}_mats", P["fabric"], coll, bevel=0.012, segments=4)
    pil = MB(f"{name}_bolsters", P["fabric_pillow"], coll, bevel=0.0)
    plinth.box(x0 + 0.10, y_front + 0.14, 0.0, x1 - 0.10, y_wall, 0.10)
    pitch = (x1 - x0) / n
    for k in range(n):
        a, b = x0 + k * pitch + 0.006, x0 + (k + 1) * pitch - 0.006
        body.box(a, y_front, 0.10, b, y_wall, top, "y")
        if mats:
            mat.box(
                a + 0.035, y_front + 0.05, top - 0.004, b - 0.035, y_wall - 0.30, top + 0.034, "y"
            )
            cx = (a + b) / 2
            prof = [
                (0.085 * math.cos(math.pi * i / 14), 0.075 * math.sin(math.pi * i / 14))
                for i in range(15)
            ]
            M = geo.basis((cx, y_wall - 0.16, top + 0.001), (0, 1, 0), (1, 0, 0), (0, 0, 1))
            pil.prism(prof, M, 0.46)
    body.finish()
    plinth.finish(weighted=False)
    mat.finish()
    ob = pil.finish(weighted=False)
    if ob:
        m = ob.modifiers.new("Bevel", "BEVEL")
        m.width = 0.01
        m.segments = 3
        m.limit_method = "ANGLE"
        m.angle_limit = math.radians(60)
    shell.strip_down(
        lights,
        light_mat,
        f"LED_{name}",
        x0 + 0.12,
        y_front + 0.06,
        x1 - 0.12,
        y_front + 0.09,
        0.094,
    )
