"""Mesh-building helpers. All geometry is authored in world metres (x east, y north, z up)."""

import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

_rng = random.Random(20261114)


def reseed(seed):
    global _rng
    _rng = random.Random(seed)


def rnd():
    return _rng.random()


def jump(n, seed=20261114):
    """Put the shared stream where it stands after n draws from the seed (positions measured by blender/rng_probe.py).
    Used before a build stage that did not change, so its boards keep the variation of the previous model version."""
    reseed(seed)
    for _ in range(n):
        _rng.random()


def collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    return col


class MB:
    """Accumulates boards/boxes/tubes into one mesh object with per-part random attribute + UVs in metres."""

    def __init__(self, name, mat, coll, bevel=0.002, segments=2, smooth=True):
        self.name, self.mat, self.coll = name, mat, coll
        self.bevel, self.segments, self.smooth = bevel, segments, smooth
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.rl = self.bm.verts.layers.float.new("rand")
        self.flat_faces = []

    # -- primitives -------------------------------------------------
    def box_m(self, size, M, grain=0, rand=None):
        """Box of local size centred on origin, transformed by M. grain = local axis of the wood fibre."""
        sx, sy, sz = (s / 2 for s in size)
        r = rnd() if rand is None else rand
        ou, ov = rnd() * 7.0, rnd() * 7.0
        loc = [Vector((x, y, z)) for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
        vs = []
        for p in loc:
            v = self.bm.verts.new(M @ p)
            v[self.rl] = r
            vs.append(v)
        # faces (outward), index = x*4+y*2+z
        quads = [
            ((0, 1, 3, 2), 0),
            ((4, 6, 7, 5), 0),
            ((0, 4, 5, 1), 1),
            ((2, 3, 7, 6), 1),
            ((0, 2, 6, 4), 2),
            ((1, 5, 7, 3), 2),
        ]
        for idx, n in quads:
            f = self.bm.faces.new([vs[i] for i in idx])
            if n == grain:
                a, b = [k for k in range(3) if k != n]
            else:
                a = grain
                b = [k for k in range(3) if k not in (n, grain)][0]
            for loop, i in zip(f.loops, idx):
                p = loc[i]
                loop[self.uv].uv = (p[a] + ou, p[b] + ov)
        return self

    def box(self, x0, y0, z0, x1, y1, z1, grain=None, rand=None):
        """Axis-aligned box from two corners. grain defaults to the longest axis."""
        size = (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
        if grain is None:
            grain = max(range(3), key=lambda k: size[k])
        elif isinstance(grain, str):
            grain = "xyz".index(grain)
        M = Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
        return self.box_m(size, M, grain, rand)

    def quad(self, pts, uv_scale=1.0):
        vs = [self.bm.verts.new(p) for p in pts]
        r = rnd()
        for v in vs:
            v[self.rl] = r
        f = self.bm.faces.new(vs)
        uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
        for loop, uv in zip(f.loops, uvs):
            loop[self.uv].uv = (uv[0] * uv_scale, uv[1] * uv_scale)
        return f

    def tube(self, pts, radius, seg=14, cap=True, rand=None):
        """Round tube along a polyline (pts already filleted)."""
        pts = [Vector(p) for p in pts]
        r = rnd() if rand is None else rand
        rings = []
        t0 = (pts[1] - pts[0]).normalized()
        up = Vector((0, 0, 1)) if abs(t0.z) < 0.9 else Vector((1, 0, 0))
        n = t0.cross(up).normalized()
        length = 0.0
        for i, p in enumerate(pts):
            if i == 0:
                t = t0
            elif i == len(pts) - 1:
                t = (pts[i] - pts[i - 1]).normalized()
            else:
                t = (
                    (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
                ).normalized()
            n = (n - t * n.dot(t)).normalized()
            b = t.cross(n)
            if i:
                length += (pts[i] - pts[i - 1]).length
            ring = []
            for k in range(seg):
                a = 2 * math.pi * k / seg
                v = self.bm.verts.new(p + radius * (math.cos(a) * n + math.sin(a) * b))
                v[self.rl] = r
                ring.append(v)
            rings.append((ring, length))
        for (ra, la), (rb, lb) in zip(rings, rings[1:]):
            for k in range(seg):
                k2 = (k + 1) % seg
                f = self.bm.faces.new([ra[k], ra[k2], rb[k2], rb[k]])
                us = [k / seg, (k + 1) / seg, (k + 1) / seg, k / seg]
                ls = [la, la, lb, lb]
                for loop, u, l in zip(f.loops, us, ls):
                    loop[self.uv].uv = (l, u * 2 * math.pi * radius)
        if cap:
            self.bm.faces.new(list(reversed(rings[0][0])))
            self.bm.faces.new(rings[-1][0])
        return self

    def lathe(self, profile, center, seg=48, rand=None, cap_top=True, cap_bottom=True):
        """Solid of revolution around +Z. profile = [(radius, z), ...] bottom to top."""
        r = rnd() if rand is None else rand
        cx, cy, cz = center
        rings = []
        for rad, z in profile:
            ring = []
            for k in range(seg):
                a = 2 * math.pi * k / seg
                v = self.bm.verts.new((cx + rad * math.cos(a), cy + rad * math.sin(a), cz + z))
                v[self.rl] = r
                ring.append(v)
            rings.append(ring)
        for ra, rb in zip(rings, rings[1:]):
            for k in range(seg):
                k2 = (k + 1) % seg
                f = self.bm.faces.new([ra[k], ra[k2], rb[k2], rb[k]])
                for loop in f.loops:
                    co = loop.vert.co
                    loop[self.uv].uv = (math.atan2(co.y - cy, co.x - cx) * 0.3, co.z)
        if cap_bottom:
            self.bm.faces.new(list(reversed(rings[0])))
        if cap_top:
            self.bm.faces.new(rings[-1])
        return self

    def prism(self, poly, M, length, grain_along=True, rand=None):
        """Extrude a 2D polygon (local X,Z; counter-clockwise) along local Y by length (centred), transform by M."""
        r = rnd() if rand is None else rand
        ou, ov = rnd() * 7, rnd() * 7
        a = [self.bm.verts.new(M @ Vector((x, -length / 2, z))) for x, z in poly]
        b = [self.bm.verts.new(M @ Vector((x, length / 2, z))) for x, z in poly]
        for v in a + b:
            v[self.rl] = r
        n = len(poly)
        per = 0.0
        for i in range(n):
            j = (i + 1) % n
            seg_len = (Vector(poly[j]) - Vector(poly[i])).length
            f = self.bm.faces.new([a[j], a[i], b[i], b[j]])
            uvs = [
                (-length / 2, per + seg_len),
                (-length / 2, per),
                (length / 2, per),
                (length / 2, per + seg_len),
            ]
            for loop, uv in zip(f.loops, uvs):
                loop[self.uv].uv = (
                    (uv[0] + ou, uv[1] + ov) if grain_along else (uv[1] + ou, uv[0] + ov)
                )
            per += seg_len
        fa = self.bm.faces.new(a)
        fb = self.bm.faces.new(list(reversed(b)))
        for f, vs in ((fa, poly), (fb, list(reversed(poly)))):
            for loop, p in zip(f.loops, vs):
                loop[self.uv].uv = (p[0] + ou, p[1] + ov)
        return self

    def sweep_rect(self, path, normals, lateral, w, t, rand=None):
        """Sweep a w (lateral) x t (along normal) rectangle along a 3D path; grain follows the path."""
        r = rnd() if rand is None else rand
        ou, ov = rnd() * 7, rnd() * 7
        lat = Vector(lateral).normalized()
        rings, length = [], 0.0
        for i, (p, n) in enumerate(zip(path, normals)):
            p, n = Vector(p), Vector(n).normalized()
            if i:
                length += (p - Vector(path[i - 1])).length
            ring = []
            for dl, dn in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                v = self.bm.verts.new(p + lat * (dl * w / 2) + n * (dn * t / 2))
                v[self.rl] = r
                ring.append(v)
            rings.append((ring, length))
        offs = [0, w, w + t, 2 * w + t, 2 * w + 2 * t]
        for (ra, la), (rb, lb) in zip(rings, rings[1:]):
            for k in range(4):
                k2 = (k + 1) % 4
                f = self.bm.faces.new([ra[k], ra[k2], rb[k2], rb[k]])
                uvs = [(la, offs[k]), (la, offs[k + 1]), (lb, offs[k + 1]), (lb, offs[k])]
                for loop, uv in zip(f.loops, uvs):
                    loop[self.uv].uv = (uv[0] + ou, uv[1] + ov)
        self.bm.faces.new(list(reversed(rings[0][0])))
        self.bm.faces.new(rings[-1][0])
        return self

    # -- finish -------------------------------------------------------
    def finish(self, weighted=True, bevel_angle=40.0):
        if not self.bm.verts:
            self.bm.free()
            return None
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        if self.smooth:
            me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        me.materials.append(self.mat)
        ob = bpy.data.objects.new(self.name, me)
        self.coll.objects.link(ob)
        if self.bevel and self.bevel > 0:
            m = ob.modifiers.new("Bevel", "BEVEL")
            m.width = self.bevel
            m.segments = self.segments
            m.limit_method = "ANGLE"
            m.angle_limit = math.radians(bevel_angle)
            m.use_clamp_overlap = True
            m.miter_outer = "MITER_ARC"
        if weighted and self.smooth:
            w = ob.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
            w.keep_sharp = False
            w.weight = 60
        return ob


def fillet(pts, radius, n=6):
    """Round the interior corners of a 3D polyline."""
    pts = [Vector(p) for p in pts]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]
        d0, d1 = (p0 - p1), (p2 - p1)
        l0, l1 = d0.length, d1.length
        d0.normalize()
        d1.normalize()
        ang = d0.angle(d1)
        if ang > math.pi - 1e-3:
            out.append(p1)
            continue
        dist = min(radius / math.tan(ang / 2), l0 * 0.49, l1 * 0.49)
        rr = dist * math.tan(ang / 2)
        a, b = p1 + d0 * dist, p1 + d1 * dist
        centre = p1 + (d0 + d1).normalized() * (rr / math.sin(ang / 2))
        va, vb = a - centre, b - centre
        sweep = va.angle(vb)
        axis = va.cross(vb).normalized()
        for k in range(n + 1):
            out.append(centre + Matrix.Rotation(sweep * k / n, 3, axis) @ va)
    out.append(pts[-1])
    return out


def smooth_curve(ctrl, samples=10):
    """Catmull-Rom through 2D control points -> list of 2D points."""
    pts = [Vector(c) for c in ctrl]
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(samples):
            t = k / samples
            out.append(
                0.5
                * (
                    (2 * p1)
                    + (-p0 + p2) * t
                    + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t**3
                )
            )
    out.append(pts[-1])
    return out


def basis(origin, x, y, z):
    M = Matrix.Identity(4)
    for i, v in enumerate((x, y, z)):
        v = Vector(v)
        M[0][i], M[1][i], M[2][i] = v.x, v.y, v.z
    M[0][3], M[1][3], M[2][3] = origin[0], origin[1], origin[2]
    return M


def emitter(name, coll, mat, pts):
    """Single-quad light emitter; emits from the side its normal points to (counter-clockwise pts)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in pts], [], [(0, 1, 2, 3)])
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob
