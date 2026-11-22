"""V10 compact comparison model (170 m2 / 24 people in house / 2 saunas / cold + carbonated pool / 16 rest places).

NOT EXECUTED BY THE AUTHOR. The parent audits this file and compact_v10_rooms.py, then runs the steps.
The original design (V8 model, V9 study) is not opened, changed or replaced by anything here.

Source of every placement: plan/compact_v10.json. Geometry: compact_v10_rooms.py with the V8 kit (sauna.*).
Reads : the plan JSON, the V8 texture/rock assets (read only, default <out-root>/assets or ../fable-v8/assets),
        and this script's own outputs.
Writes: only under <out-root> = .../sauna-design/fable-v10, only names starting with "v10_" or "sauna_compact_v10"
        (plus assets/product_floor/* and verification/product_floor_bake.json written by the V8 floor bake in the glb step).
        Nothing is overwritten unless --replace is given.

Steps (one Blender 5.2 process each; paths are Windows / UNC paths when the Windows Blender is used)
  estimate  disk estimate against the 1 GiB budget and plan arithmetic (no model)
  build     new scene -> rooms from the plan -> images packed into the file -> save -> measurements
  verify    open the saved model -> measure real meshes -> failures / open_issues / not_measured (exit 1 on failures)
  render    open the saved model -> one camera -> PNG   (first: --tests --res 600 --samples 48)
  glb       open the saved model -> simplified materials in memory -> .glb (the .blend is not saved again)

  blender -b --python-exit-code 1 --python compact_v10.py -- --step build --out-root <...\\sauna-design\\fable-v10>
  blender -b --python-exit-code 1 --python compact_v10.py -- --step render --out-root <...> --view main --res 2400 --samples 1024

verify measures the built meshes (triangles in world coordinates), not the plan constants: floor coverage and overlap,
net room sizes between wall faces, counted objects, pool water / bottom / support levels, door and passage widths, the
performer floor and towel circle against benches, guard, walls and the check bodies. A design target that is not met, or a
thing that was not measured, goes to open_issues / not_measured, separate from failures (model and plan disagree).
Law, equipment selection and cost are never certified here.
"""

import argparse
import hashlib
import itertools
import json
import math
import os
import sys
import time

import bpy

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MODEL_NAME = "sauna_compact_v10.blend"
GLB_NAME = "sauna_compact_v10.glb"
BUDGET_MB = 1024.0
SEED = 20261116
ROLES = {
    "main_seat": "main.seats",
    "self_seat": "self.seats",
    "rest_chair": "rest.chairs",
    "rest_lounger": "rest.loungers",
    "rest_builtin": "rest.builtin.seats",
    "perch": "hall.perch.seats",
    "waiting": "hall.waiting_standing",
}


# ---------------------------------------------------------------------------------------------- paths, records
def norm(p):
    return os.path.normcase(os.path.normpath(os.path.abspath(p)))


def inside(root, p):
    return norm(p).startswith(norm(root) + os.sep)


def check_root(p):
    q = os.path.normpath(os.path.abspath(p))
    if (
        os.path.basename(q).lower() != "fable-v10"
        or os.path.basename(os.path.dirname(q)).lower() != "sauna-design"
    ):
        raise RuntimeError(f"out-root must be the canonical .../sauna-design/fable-v10, got {q}")
    if not os.path.isdir(q):
        raise RuntimeError(f"out-root does not exist: {q}")
    return q


def out_path(root, sub, name, replace=False, append=False):
    if not (name.startswith("v10_") or name.startswith("sauna_compact_v10")):
        raise RuntimeError(f"output name must start with v10_ or sauna_compact_v10: {name}")
    path = os.path.join(root, sub, name)
    if not inside(root, path):
        raise RuntimeError(f"refusing to write outside the V10 root: {path}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path) and not (replace or append):
        raise RuntimeError(f"refusing to overwrite {path} (pass --replace)")
    return path


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def file_state(path):
    return {"path": path, "bytes": os.path.getsize(path), "sha256": sha256_file(path)}


def dir_bytes(root):
    total = 0
    for base, _dirs, files in os.walk(root):
        for n in files:
            try:
                total += os.path.getsize(os.path.join(base, n))
            except OSError:
                pass
    return total


def load_plan(args):
    path = args.plan or os.path.join(HERE, "..", "plan", "compact_v10.json")
    path = os.path.normpath(os.path.abspath(path))
    with open(path, encoding="utf-8") as f:
        return json.load(f), path


def assets_root(args, root):
    cands = (
        [args.assets]
        if args.assets
        else [
            os.path.join(root, "assets"),
            os.path.join(os.path.dirname(root), "fable-v8", "assets"),
        ]
    )
    for c in cands:
        if c and os.path.isdir(os.path.join(c, "polyhaven")):
            return os.path.normpath(os.path.abspath(c))
    raise RuntimeError(
        f"texture assets not found (looked in {cands}); pass --assets <dir containing polyhaven>"
    )


# ---------------------------------------------------------------------------------------------- plan arithmetic
def plan_checks(plan):
    """Zones as a partition of the footprint, from the plan rectangles only (the model is measured separately)."""
    plan_width, plan_depth = plan["width"], plan["height"]
    zones = plan["zones"]
    fail, rows, groups = [], [], {}
    for z in zones:
        x, y, w, d = z["rect"]
        if x < -1e-9 or y < -1e-9 or x + w > plan_width + 1e-9 or y + d > plan_depth + 1e-9:
            fail.append(f"zone {z['id']} leaves the footprint")
        rows.append(
            {
                "id": z["id"],
                "no": z["no"],
                "name": z["name"],
                "group": z["group"],
                "rect": z["rect"],
                "gross_m2": round(w * d, 3),
            }
        )
        groups[z["group"]] = groups.get(z["group"], 0.0) + w * d
    overlaps = []
    for i in range(len(zones)):
        for j in range(i + 1, len(zones)):
            a, b = zones[i]["rect"], zones[j]["rect"]
            ox = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
            oy = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
            if ox > 1e-9 and oy > 1e-9:
                overlaps.append(
                    {"zones": [zones[i]["id"], zones[j]["id"]], "m2": round(ox * oy, 4)}
                )
    total = sum(r["gross_m2"] for r in rows)
    if overlaps:
        fail.append(f"zone rectangles overlap: {overlaps}")
    if abs(total - plan_width * plan_depth) > 1e-3:
        fail.append(f"zone areas sum to {total:.3f}, footprint is {plan_width * plan_depth:.3f}")
    declared = {c["group"]: c["delta"] for c in plan.get("area_changes", [])}
    table = []
    for g, target in plan["targets_m2"].items():
        got = groups.get(g, 0.0)
        delta = got - target
        table.append(
            {
                "group": g,
                "target_m2": target,
                "plan_gross_m2": round(got, 3),
                "delta_m2": round(delta, 3),
                "declared_delta_m2": declared.get(g),
                "reason": next(
                    (c["reason"] for c in plan.get("area_changes", []) if c["group"] == g), None
                ),
            }
        )
        if abs(delta) > 0.004 and abs(delta - declared.get(g, 1e9)) > 0.006:
            fail.append(
                f"area change of group {g} ({delta:+.3f} m2) is not recorded in area_changes"
            )
    return {
        "footprint_m2": plan_width * plan_depth,
        "zones": rows,
        "sum_gross_m2": round(total, 3),
        "overlaps": overlaps,
        "groups": table,
        "failures": fail,
    }


def estimate(root, assets):
    existing = dir_bytes(root)
    a = dir_bytes(assets) if assets else 0
    items = {
        "model_blend_upper": 120e6,
        "glb_upper": 40e6,
        "asset_copy_if_made_upper": max(25e6, a),
        "final_renders_upper": 12 * 11.6e6,
        "test_renders_upper": 30 * 1.1e6,
        "product_floor_bake": 20e6,
        "records_logs_diagrams_upper": 40e6,
    }
    upper = existing + sum(items.values())
    return {
        "budget_mb": BUDGET_MB,
        "existing_in_root_mb": round(existing / 1e6, 2),
        "assets_source_mb": round(a / 1e6, 2),
        "items_mb": {k: round(v / 1e6, 1) for k, v in items.items()},
        "upper_total_mb": round(upper / 1e6, 1),
        "within_budget": upper / 1e6 <= BUDGET_MB,
        "note": "upper bounds; the conversation backup of the parent is not part of this script and is not counted",
    }


# ---------------------------------------------------------------------------------------------- mesh measurement kit
def part_labels(idx, nv):
    """Loose part of every triangle (min-label propagation with pointer jumping)."""
    import numpy as np

    lab = np.arange(nv, dtype=np.int64)
    flat = idx.ravel()
    for _ in range(400):
        m = lab[idx].min(axis=1)
        new = lab.copy()
        np.minimum.at(new, flat, np.repeat(m, 3))
        new = new[new]
        if np.array_equal(new, lab):
            break
        lab = new
    return lab[idx[:, 0]]


class Geo:
    """Base-mesh triangles in world coordinates, with the z-range of the loose part each triangle belongs to."""

    def __init__(self):
        self.c, self.v, self.b = {}, {}, {}

    def verts(self, ob):
        import numpy as np

        if ob.name not in self.v:
            me = ob.data
            co = np.empty(len(me.vertices) * 3, np.float32)
            me.vertices.foreach_get("co", co)
            m = np.array(ob.matrix_world, dtype=np.float64)
            self.v[ob.name] = co.reshape(-1, 3).astype(np.float64) @ m[:3, :3].T + m[:3, 3]
        return self.v[ob.name]

    def get(self, ob):
        import numpy as np

        if ob.name in self.c:
            return self.c[ob.name]
        me = ob.data
        me.calc_loop_triangles()
        n, out = len(me.loop_triangles), None
        if n:
            idx = np.empty(n * 3, np.int32)
            me.loop_triangles.foreach_get("vertices", idx)
            idx = idx.reshape(-1, 3).astype(np.int64)
            w = self.verts(ob)
            tri = w[idx]
            lab = part_labels(idx, len(me.vertices))
            _u, inv = np.unique(lab, return_inverse=True)
            zmin = np.full(inv.max() + 1, np.inf)
            zmax = np.full(inv.max() + 1, -np.inf)
            np.minimum.at(zmin, inv, tri[:, :, 2].min(axis=1))
            np.maximum.at(zmax, inv, tri[:, :, 2].max(axis=1))
            out = {"tri": tri, "pzmin": zmin[inv], "pzmax": zmax[inv]}
        self.c[ob.name] = out
        return out

    def bbox(self, ob):
        if ob.name not in self.b:
            v = self.verts(ob)
            self.b[ob.name] = (v.min(axis=0), v.max(axis=0)) if len(v) else None
        return self.b[ob.name]

    def boxes(self, ob):
        """Axis-aligned boxes of a mesh built only from MB.box (8 vertices each), else None."""
        import numpy as np

        v = self.verts(ob)
        if not len(v) or len(v) % 8:
            return None
        v = v.reshape(-1, 8, 3)
        return np.concatenate([v.min(axis=1), v.max(axis=1)], axis=1)


def _seg(query_points, segment_start, segment_end):
    import numpy as np

    ab, ap = segment_end - segment_start, query_points - segment_start
    t = np.clip((ap * ab).sum(-1) / np.maximum((ab * ab).sum(-1), 1e-18), 0.0, 1.0)
    q = ap - ab * t[..., None]
    return np.sqrt((q * q).sum(-1))


def _cr(left_vectors, right_vectors):
    return (
        left_vectors[..., 0] * right_vectors[..., 1] - left_vectors[..., 1] * right_vectors[..., 0]
    )


class Slab:
    """Plan projection of every loose part that crosses the height band zlo..zhi. dist() = plan distance to the nearest
    part (0 inside a part). extra = named plan rectangles treated as obstacles (pool water)."""

    def __init__(self, scene_geo, objs, zlo, zhi, region, extra=()):
        import numpy as np

        projected_faces, owner, self.names = [], [], []
        x0, y0, x1, y1 = region
        for ob in objs:
            g = scene_geo.get(ob)
            if g is None:
                continue
            t = g["tri"]
            keep = (
                (g["pzmax"] > zlo)
                & (g["pzmin"] < zhi)
                & (t[:, :, 0].max(1) >= x0)
                & (t[:, :, 0].min(1) <= x1)
                & (t[:, :, 1].max(1) >= y0)
                & (t[:, :, 1].min(1) <= y1)
            )
            if keep.any():
                projected_faces.append(t[keep][:, :, :2])
                owner += [len(self.names)] * int(keep.sum())
                self.names.append(ob.name)
        for name, (rx0, ry0, rx1, ry1) in extra:
            projected_faces.append(
                np.array(
                    [[[rx0, ry0], [rx1, ry0], [rx1, ry1]], [[rx0, ry0], [rx1, ry1], [rx0, ry1]]],
                    dtype=np.float64,
                )
            )
            owner += [len(self.names)] * 2
            self.names.append(name)
        self.t = np.concatenate(projected_faces) if projected_faces else np.zeros((0, 3, 2))
        self.owner = np.array(owner, dtype=np.int64)

    def dist(self, pts):
        import numpy as np

        pts = np.asarray(pts, dtype=np.float64).reshape(-1, 2)
        k, m = len(pts), len(self.t)
        d, who = np.full(k, np.inf), np.full(k, -1, dtype=np.int64)
        if m == 0 or k == 0:
            return d, who
        vertices_a, vertices_b, vertices_c = (
            self.t[:, 0][None],
            self.t[:, 1][None],
            self.t[:, 2][None],
        )
        solid = np.abs(_cr(vertices_b - vertices_a, vertices_c - vertices_a)) > 1e-12
        step = max(1, 300_000 // m)
        for s in range(0, k, step):
            query_points = pts[s : s + step][:, None, :]
            dd = np.minimum(
                np.minimum(
                    _seg(query_points, vertices_a, vertices_b),
                    _seg(query_points, vertices_b, vertices_c),
                ),
                _seg(query_points, vertices_c, vertices_a),
            )
            c1, c2, c3 = (
                _cr(vertices_b - vertices_a, query_points - vertices_a),
                _cr(vertices_c - vertices_b, query_points - vertices_b),
                _cr(vertices_a - vertices_c, query_points - vertices_c),
            )
            ins = (
                ((c1 >= 0) & (c2 >= 0) & (c3 >= 0)) | ((c1 <= 0) & (c2 <= 0) & (c3 <= 0))
            ) & solid
            dd[ins] = 0.0
            j = dd.argmin(axis=1)
            d[s : s + step] = dd[np.arange(len(j)), j]
            who[s : s + step] = self.owner[j]
        return d, who

    def name(self, i):
        return self.names[int(i)] if int(i) >= 0 else None


def sample_line(line, step=0.05):
    import numpy as np

    pts = []
    for (xa, ya), (xb, yb) in itertools.pairwise(line):
        n = max(1, math.ceil(math.hypot(xb - xa, yb - ya) / step))
        pts += [(xa + (xb - xa) * i / n, ya + (yb - ya) * i / n) for i in range(n)]
    pts.append((line[-1][0], line[-1][1]))
    return np.array(pts, dtype=np.float64)


def grid_pts(rect, step):
    import numpy as np

    xs = np.arange(rect[0], rect[2] + 1e-9, step)
    ys = np.arange(rect[1], rect[3] + 1e-9, step)
    return np.array([(x, y) for x in xs for y in ys], dtype=np.float64)


def best_point(pts, value):
    i = int(value.argmax())
    return float(value[i]), [round(float(pts[i][0]), 3), round(float(pts[i][1]), 3)], i


def surface_z(scene_geo, objs, x, y, zlo, zhi):
    """Highest surface between zlo and zhi under (x, y) and four points 50 mm around it (board and slat gaps)."""
    import numpy as np

    best, who = None, None
    for px, py in ((x, y), (x + 0.05, y), (x - 0.05, y), (x, y + 0.05), (x, y - 0.05)):
        for ob in objs:
            g = scene_geo.get(ob)
            if g is None:
                continue
            t = g["tri"]
            sel = (
                (t[:, :, 0].min(1) <= px)
                & (t[:, :, 0].max(1) >= px)
                & (t[:, :, 1].min(1) <= py)
                & (t[:, :, 1].max(1) >= py)
            )
            if not sel.any():
                continue
            q = t[sel]
            vertices_a, vertices_b, vertices_c = q[:, 0], q[:, 1], q[:, 2]
            den = (vertices_b[:, 1] - vertices_c[:, 1]) * (vertices_a[:, 0] - vertices_c[:, 0]) + (
                vertices_c[:, 0] - vertices_b[:, 0]
            ) * (vertices_a[:, 1] - vertices_c[:, 1])
            ok = np.abs(den) > 1e-12
            den = np.where(ok, den, 1.0)
            l1 = (
                (vertices_b[:, 1] - vertices_c[:, 1]) * (px - vertices_c[:, 0])
                + (vertices_c[:, 0] - vertices_b[:, 0]) * (py - vertices_c[:, 1])
            ) / den
            l2 = (
                (vertices_c[:, 1] - vertices_a[:, 1]) * (px - vertices_c[:, 0])
                + (vertices_a[:, 0] - vertices_c[:, 0]) * (py - vertices_c[:, 1])
            ) / den
            l3 = 1.0 - l1 - l2
            z = l1 * vertices_a[:, 2] + l2 * vertices_b[:, 2] + l3 * vertices_c[:, 2]
            z = z[ok & (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9) & (z >= zlo) & (z <= zhi)]
            if len(z) and (best is None or z.max() > best):
                best, who = float(z.max()), ob.name
    return best, who


def is_solid(ob, bodies=False):
    """Things a person cannot walk through. Door leaves are left out (a passage is measured with the door open)."""
    n = ob.name
    if ob.type != "MESH" or n.startswith(("CEIL_", "STUDY_", "Floor_")):
        return False
    if n.startswith("CHECK_"):
        return bodies
    if n.startswith(("Main_ZL300_stone", "Self_heater_stone")) or n.endswith("_water"):
        return False
    if n == "Plant_pipes":  # overhead runs at 2.3 m and risers standing on the equipment
        return False
    if (n.startswith("Door_") and not n.endswith("_frame")) or n.startswith("WC_door"):
        return False
    mats = ob.data.materials
    return not (len(mats) and mats[0] is not None and mats[0].name.startswith("light_"))


def get_path(plan, dotted):
    v = plan
    for k in dotted.split("."):
        v = v[k]
    return v


# ---------------------------------------------------------------------------------------------- measurements
def measure(plan):
    import numpy as np

    bpy.context.view_layer.update()
    scene_geo = Geo()
    fail, issues, unmeasured = [], [], []
    res = {"failures": fail, "open_issues": issues, "not_measured": unmeasured}
    a = plan["assumptions"]
    plan_width, plan_depth = plan["width"], plan["height"]
    footprint = (0.0, 0.0, plan_width, plan_depth)
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    solids = [o for o in objs if is_solid(o)]
    bodies = [o for o in objs if o.name.startswith("CHECK_")]
    by_name = {o.name: o for o in objs}
    zone_rect = {z["id"]: z["rect"] for z in plan["zones"]}

    def issue(i, what, measured=None, target=None, status="not_achieved"):
        issues.append(
            {"id": i, "what": what, "measured": measured, "target": target, "status": status}
        )

    # --- 1. floors: every point of the footprint is covered by exactly one zone floor or one pool
    pts = grid_pts((0.0125, 0.0125, plan_width, plan_depth), 0.05)
    cover = np.zeros(len(pts), dtype=np.int32)
    zone_rows = []
    pool_rect = {}
    for p in plan["pools"]:
        lin = by_name.get(f"Pool_{p['id']}_lining")
        if lin is None:
            fail.append(f"pool lining missing: {p['id']}")
            continue
        lo, hi = scene_geo.bbox(lin)
        pool_rect[p["id"]] = (float(lo[0]), float(lo[1]), float(hi[0]), float(hi[1]))
        d, _ = Slab(scene_geo, [], -1, 1, footprint, extra=[("pool", pool_rect[p["id"]])]).dist(pts)
        cover += d == 0.0
    for z in plan["zones"]:
        ob = by_name.get("Floor_" + z["id"])
        if ob is None:
            fail.append(f"floor mesh missing: {z['id']}")
            continue
        d, _ = Slab(scene_geo, [ob], -1.0, 1.0, footprint).dist(pts)
        inz = d == 0.0
        cover += inz
        area = float(sum(p.area for p in ob.data.polygons))
        holes = sum(
            (r[2] - r[0]) * (r[3] - r[1])
            for p in plan["pools"]
            if p["zone"] == z["id"]
            for r in [pool_rect.get(p["id"], (0, 0, 0, 0))]
        )
        gross = z["rect"][2] * z["rect"][3]
        zone_rows.append(
            {
                "id": z["id"],
                "no": z["no"],
                "group": z["group"],
                "plan_gross_m2": round(gross, 3),
                "floor_mesh_m2": round(area, 3),
                "pool_openings_m2": round(holes, 3),
                "floor_plus_pools_m2": round(area + holes, 3),
            }
        )
        if abs(area + holes - gross) > 0.01:
            fail.append(
                f"floor mesh of {z['id']} is {area + holes:.3f} m2, plan rectangle {gross:.3f} m2"
            )
    res["floor_coverage"] = {
        "sample_step_m": 0.05,
        "points": len(pts),
        "uncovered": int((cover == 0).sum()),
        "double_covered": int((cover > 1).sum()),
        "covered_once_m2": round(float((cover == 1).sum()) * 0.0025, 2),
        "footprint_m2": plan_width * plan_depth,
    }
    if (cover != 1).any():
        fail.append(f"floor meshes leave gaps or overlap: {res['floor_coverage']}")

    # --- 2. net room size between wall faces (cross scan from the zone centre through the wall boxes at z = 1.0)
    walls = by_name.get("Structure_Walls")
    wb = scene_geo.boxes(walls) if walls is not None else None
    if wb is None:
        unmeasured.append("net room sizes: Structure_Walls is not a pure box mesh")
    else:
        wb = wb[(wb[:, 2] < 1.0) & (wb[:, 5] > 1.0)]
        for row in zone_rows:
            x, y, w, d = zone_rect[row["id"]]
            cx, cy = x + w / 2, y + d / 2
            inx, iny = (wb[:, 1] < cy) & (wb[:, 4] > cy), (wb[:, 0] < cx) & (wb[:, 3] > cx)
            xw = max([x] + [float(v) for v in wb[inx & (wb[:, 3] <= cx), 3]])
            xe = min([x + w] + [float(v) for v in wb[inx & (wb[:, 0] >= cx), 0]])
            ys = max([y] + [float(v) for v in wb[iny & (wb[:, 4] <= cy), 4]])
            yn = min([y + d] + [float(v) for v in wb[iny & (wb[:, 1] >= cy), 1]])
            row["net_between_walls"] = [round(xe - xw, 3), round(yn - ys, 3)]
            row["net_m2"] = round((xe - xw) * (yn - ys), 3)
    groups = {}
    for row in zone_rows:
        g = groups.setdefault(row["group"], {"gross_m2": 0.0, "net_m2": 0.0})
        g["gross_m2"] = round(g["gross_m2"] + row["floor_plus_pools_m2"], 3)
        g["net_m2"] = round(g["net_m2"] + row.get("net_m2", 0.0), 3)
    for gname, target in plan["targets_m2"].items():
        g = groups.setdefault(gname, {"gross_m2": 0.0, "net_m2": 0.0})
        g["target_m2"] = target
        g["gross_minus_target"] = round(g["gross_m2"] - target, 3)
    res["zones"] = zone_rows
    res["area_groups"] = groups
    res["area_note"] = (
        "gross = floor mesh + pool openings (wall centre to wall centre, walls counted once inside the rooms); "
        "net = clear size between the wall faces met from the zone centre, clipped to the zone"
    )
    for gname in ("main", "self", "rest", "changing", "wash"):
        g = groups.get(gname, {})
        if g.get("net_m2") and g["net_m2"] < g["target_m2"] - 0.5:
            issue(
                f"net_area_{gname}",
                "内法面積が目安より小さい（壁を区画に含めたため）",
                g["net_m2"],
                g["target_m2"],
            )

    # --- 3. counted objects
    items, where_bad = {}, []
    zone_of = {z["id"]: z["rect"] for z in plan["zones"]}

    def in_zone(ob, zid):
        lo, hi = scene_geo.bbox(ob)
        cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
        rects = [
            zone_of[k]
            for k in (("plantArm", "plantMain") if zid == "plant" else (zid,))
            if k in zone_of
        ]
        return any(r[0] <= cx <= r[0] + r[2] and r[1] <= cy <= r[1] + r[3] for r in rects)

    for ob in objs:
        if "v10_item" in ob.keys():
            items[ob["v10_item"]] = items.get(ob["v10_item"], 0) + 1
            if ob.get("v10_zone") and not in_zone(ob, ob["v10_zone"]):
                where_bad.append(ob.name)
    roles = {}
    for ob in bodies:
        roles[ob.get("v10_role", "?")] = roles.get(ob.get("v10_role", "?"), 0) + 1
    lk, sl = plan["changing"]["lockers"], plan["reception"]["shoe_lockers"]
    want_items = {
        "rest_chair": len(plan["rest"]["chairs"]),
        "rest_lounger": len(plan["rest"]["loungers"]),
        "shower": len(plan["wash"]["showers"]),
        "locker": lk["cols"] * lk["tiers"],
        "shoe_locker": sl["cols"] * sl["tiers"],
        "wc": len(plan["wc"]["cubicles"]),
        "basin": len(plan["changing"]["vanity"]["basins"]) + 1,
        "equipment": len(plan["plant"]["equipment"]),
    }
    want_roles = {r: len(get_path(plan, p)) for r, p in ROLES.items()}
    for p in plan["pools"]:
        want_roles[f"pool_{p['id']}"] = len(p["positions"])
    want_roles.update(performer=1, showering=len(plan["wash"]["showers"]))
    res["counts"] = {
        "objects": items,
        "plan": want_items,
        "check_bodies": roles,
        "plan_positions": want_roles,
    }
    for k, v in want_items.items():
        if items.get(k, 0) != v:
            fail.append(f"count of {k}: model {items.get(k, 0)}, plan {v}")
    for k, v in want_roles.items():
        if roles.get(k, 0) != v:
            fail.append(f"check bodies {k}: model {roles.get(k, 0)}, plan {v}")
    if where_bad:
        fail.append(f"objects outside their zone: {where_bad[:10]}")

    # --- 4. every seated body has a real surface under it
    seats, missing = [], []
    for ob in bodies:
        if "v10_support" not in ob.keys():
            continue
        sx, sy = list(ob["v10_support"])
        zz = float(ob["v10_seat_z"])
        near = [
            o
            for o in solids
            if (
                lambda b: (
                    b is not None
                    and b[0][0] - 0.1 <= sx <= b[1][0] + 0.1
                    and b[0][1] - 0.1 <= sy <= b[1][1] + 0.1
                )
            )(scene_geo.bbox(o))
        ]
        z, who = surface_z(scene_geo, near, sx, sy, zz - 0.10, zz + 0.06)
        seats.append(
            {
                "body": ob.name,
                "role": ob.get("v10_role"),
                "expected_seat_z": zz,
                "surface_z": None if z is None else round(z, 3),
                "on": who,
            }
        )
        if z is None:
            missing.append(ob.name)
    res["seat_support"] = seats
    supported = {}
    for s in seats:
        if s["surface_z"] is not None:
            supported[s["role"]] = supported.get(s["role"], 0) + 1
    res["seats_with_measured_support"] = supported
    res["rest_places_measured"] = sum(
        supported.get(k, 0) for k in ("rest_chair", "rest_lounger", "rest_builtin")
    )
    if missing:
        fail.append(f"no seat surface under: {missing[:12]}")

    # --- 5. check bodies do not overlap each other
    bb, owner = [], []
    for ob in bodies:
        b = scene_geo.boxes(ob)
        if b is None:
            unmeasured.append(f"body overlap: {ob.name} is not a box mesh")
            continue
        bb.append(b)
        owner += [ob.name] * len(b)
    clashes = []
    if bb:
        bb = np.concatenate(bb)
        ov = np.ones((len(bb), len(bb)), dtype=bool)
        for k in range(3):
            ov &= (
                np.minimum(bb[:, None, 3 + k], bb[None, :, 3 + k])
                - np.maximum(bb[:, None, k], bb[None, :, k])
            ) > 0.005
        for i, j in zip(*np.nonzero(np.triu(ov, 1)), strict=False):
            if owner[i] != owner[j] and (owner[i], owner[j]) not in clashes:
                clashes.append((owner[i], owner[j]))
    res["body_overlaps"] = [list(c) for c in clashes]
    if clashes:
        fail.append(f"check bodies overlap: {clashes[:8]}")
    unmeasured.append(
        "check bodies against furniture (legs under tables, shoulders against screens) are not tested; only body against body"
    )

    # --- 6. pools: water surface, bottom, steps, support underside and the assumed slab
    plate = by_name.get("STUDY_slab_top_plate")
    plate_boxes = scene_geo.boxes(plate) if plate is not None else None
    slab_top = float(scene_geo.bbox(plate)[1][2]) if plate is not None else None
    pools = []
    for p in plan["pools"]:
        pid = p["id"]
        wat, lin, stp, env = (
            by_name.get(f"Pool_{pid}_water"),
            by_name.get(f"Pool_{pid}_lining"),
            by_name.get(f"Pool_{pid}_steps"),
            by_name.get(f"STUDY_pool_{pid}_envelope"),
        )
        if wat is None or lin is None or env is None:
            fail.append(f"pool {pid}: water, lining or study envelope missing")
            continue
        r = pool_rect[pid]
        wv = scene_geo.verts(wat)
        top = wv[wv[:, 2] > wv[:, 2].max() - 0.05][:, 2]
        llo, lhi = scene_geo.bbox(lin)
        elo, _ehi = scene_geo.bbox(env)
        bottom, under = float(llo[2]), float(elo[2])
        inner = [round(float(lhi[0] - llo[0]), 3), round(float(lhi[1] - llo[1]), 3)]
        step_m2 = 0.0
        if stp is not None:
            slo, shi = scene_geo.bbox(stp)
            step_m2 = float((shi[0] - slo[0]) * (shi[1] - slo[1]))
        row = {
            "id": pid,
            "water_surface_mean": round(float(top.mean()), 4),
            "water_surface_range": [round(float(top.min()), 4), round(float(top.max()), 4)],
            "inner_size": inner,
            "water_m2": round(inner[0] * inner[1], 3),
            "bottom": round(bottom, 4),
            "water_depth": round(float(top.mean()) - bottom, 3),
            "steps_plan_m2": round(step_m2, 3),
            "landing_kept_clear_m2": round(
                (p["landing"][2] - p["landing"][0]) * (p["landing"][3] - p["landing"][1]), 3
            ),
            "support_underside": round(under, 4),
            "envelope_below_bottom": round(bottom - under, 4),
            "assumed_slab_top": None if slab_top is None else round(slab_top, 4),
            "space_needed_below_slab_top": None if slab_top is None else round(slab_top - under, 3),
            "below_fl": round(a["fl"] - under, 3),
            "positions_in_water": roles.get(f"pool_{pid}", 0),
        }
        want_bottom = a["fl"] - a["water_drop"] - p["depth"]
        if abs(row["water_surface_mean"] - (a["fl"] - a["water_drop"])) > 0.006:
            fail.append(
                f"pool {pid}: water surface {row['water_surface_mean']} differs from FL - {a['water_drop']}"
            )
        if (
            abs(bottom - want_bottom) > 0.002
            or abs(inner[0] - p["rect"][2]) > 0.002
            or abs(inner[1] - p["rect"][3]) > 0.002
        ):
            fail.append(
                f"pool {pid}: basin {inner} / bottom {bottom:.3f} differ from the plan {p['rect'][2:]} / {want_bottom:.3f}"
            )
        if abs((bottom - under) - a["envelope_below"]) > 0.003:
            fail.append(
                f"pool {pid}: support underside {under:.3f} is not {a['envelope_below']} below the measured bottom {bottom:.3f}"
            )
        if plate_boxes is not None:
            hit = (
                (plate_boxes[:, 0] < r[2] - 0.01)
                & (plate_boxes[:, 3] > r[0] + 0.01)
                & (plate_boxes[:, 1] < r[3] - 0.01)
                & (plate_boxes[:, 4] > r[1] + 0.01)
            )
            row["assumed_slab_plate_over_the_basin"] = bool(hit.any())
            if hit.any():
                fail.append(f"pool {pid}: the assumed slab plate is not opened over the basin")
        lx0, ly0, lx1, ly1 = p["landing"]
        for ob in bodies:
            if ob.get("v10_role") == f"pool_{pid}":
                blo, bhi = scene_geo.bbox(ob)
                if (
                    blo[0] < lx1 - 0.005
                    and bhi[0] > lx0 + 0.005
                    and blo[1] < ly1 - 0.005
                    and bhi[1] > ly0 + 0.005
                ):
                    fail.append(
                        f"pool {pid}: {ob.name} sits on the stair landing that must stay clear"
                    )
                if (
                    blo[0] < r[0] - 0.01
                    or bhi[0] > r[2] + 0.01
                    or blo[1] < r[1] - 0.01
                    or bhi[1] > r[3] + 0.01
                ):
                    fail.append(f"pool {pid}: {ob.name} is not inside the basin")
        pools.append(row)
        if slab_top is not None and under < slab_top:
            issue(
                f"pool_{pid}_below_slab",
                "浴槽の支持下端が仮スラブ上端より下。床下空間が必要で、掘削・切断の可否は物件未定のため未確認",
                {
                    "support_underside": row["support_underside"],
                    "below_assumed_slab_top": row["space_needed_below_slab_top"],
                },
                "物件の床下・構造で確認",
                "unverified",
            )
    res["pools"] = pools
    res["pool_water_total_m2"] = round(sum(r["water_m2"] for r in pools), 3)

    # --- 7. doors: clear width between the built wall ends and frame jambs (leaf open)
    doors = []
    for d in plan["doors"]:
        fr = by_name.get(f"Door_{d['id']}_frame")
        if walls is None or fr is None:
            unmeasured.append(f"door {d['id']}: wall or frame mesh missing")
            continue
        x0, y0, x1, y1 = d["seg"]
        door_length = math.hypot(x1 - x0, y1 - y0)
        ux, uy = (x1 - x0) / door_length, (y1 - y0) / door_length
        line = np.array(
            [(x0 + ux * s, y0 + uy * s) for s in np.arange(-0.15, door_length + 0.15, 0.002)]
        )
        dd, _ = Slab(
            scene_geo,
            [walls, fr],
            0.30,
            1.80,
            (min(x0, x1) - 1, min(y0, y1) - 1, max(x0, x1) + 1, max(y0, y1) + 1),
        ).dist(line)
        clear = float((dd > 1e-5).sum()) * 0.002
        doors.append(
            {
                "id": d["id"],
                "kind": d["kind"],
                "opening": round(door_length, 3),
                "clear_width": round(clear, 3),
            }
        )
        if clear < plan["door_clear_target"] - 1e-6:
            issue(
                f"door_{d['id']}",
                "扉の有効幅が検討目安より狭い",
                round(clear, 3),
                plan["door_clear_target"],
            )
    res["doors"] = doors
    res["door_note"] = "枠の内法（扉を開けた状態）。開いた扉の厚み・把手は引いていない。"

    # --- 8. passages: largest circle that travels along the drawn centre line (2 x smallest clearance)
    water = [(f"pool:{k}", r) for k, r in pool_rect.items()]
    passages = []
    for p in plan["passages"]:
        ln = sample_line(p["line"])
        reg = (
            ln[:, 0].min() - 2.5,
            ln[:, 1].min() - 2.5,
            ln[:, 0].max() + 2.5,
            ln[:, 1].max() + 2.5,
        )
        use = solids + (bodies if p.get("with_bodies") else [])
        s = Slab(scene_geo, use, 0.05, 1.90, reg, extra=water)
        dd, who = s.dist(ln)
        i = int(dd.argmin())
        row = {
            "id": p["id"],
            "name": p["name"],
            "with_check_bodies": bool(p.get("with_bodies")),
            "width_on_centre_line": round(float(2 * dd[i]), 3),
            "target": p["target"],
            "narrowest_at": [round(float(ln[i][0]), 2), round(float(ln[i][1]), 2)],
            "limited_by": s.name(who[i]),
        }
        passages.append(row)
        if row["width_on_centre_line"] < p["target"] - 1e-6:
            issue(
                f"passage_{p['id']}",
                f"通路幅が検討目安より狭い: {p['name']}",
                row["width_on_centre_line"],
                p["target"],
            )
    res["passages"] = passages
    res["passage_note"] = (
        "中心線上を通れる最大の円の直径（高さ0.05〜1.90 mの物体と浴槽の水面を障害とする）。中心線が偏っていれば実幅より小さく出る。"
        "目安は検討用の値で、法定幅ではない。"
    )

    # --- 9. main sauna: performer floor and towel circle against the built benches, guard, walls and bodies
    m = plan["main"]
    pf = m["performer"]
    zx, zy, zw, zd = zone_of["main"]
    reg = (zx - 0.3, zy - 0.3, zx + zw + 0.3, zy + zd + 0.3)
    main_bodies = [
        o for o in bodies if o.get("v10_zone") == "main" and o.get("v10_role") != "performer"
    ]
    cand = grid_pts(pf["search_rect"], 0.05)
    floor = Slab(scene_geo, solids, 0.05, 1.90, reg)
    d_floor, _w_floor = floor.dist(cand)
    _r0, c0, _i0 = best_point(cand, d_floor)
    fine = grid_pts((c0[0] - 0.05, c0[1] - 0.05, c0[0] + 0.05, c0[1] + 0.05), 0.01)
    d_fine, w_fine = floor.dist(fine)
    r1, c1, i1 = best_point(fine, d_fine)
    hx = m["heater"]["centre"][0]
    axis = np.array(
        [(hx, y) for y in np.arange(pf["search_rect"][1], pf["search_rect"][3] + 1e-9, 0.01)]
    )
    d_axis, _ = floor.dist(axis)
    ra, ca, _ia = best_point(axis, d_axis)
    d_decl, w_decl = floor.dist([pf["centre"]])
    air = Slab(scene_geo, solids, 1.00, 2.30, reg)
    air_b = Slab(scene_geo, main_bodies, 1.00, 2.30, reg)
    full = Slab(scene_geo, solids, 0.05, 2.30, reg)
    full_b = Slab(scene_geo, main_bodies, 0.05, 2.30, reg)
    mp = pf["margin_people"]

    def towel(pp, over):
        ds, ws = (air if over else full).dist(pp)
        db, _ = (air_b if over else full_b).dist(pp)
        return np.minimum(ds, db - mp), ds, db, ws

    can_stand = d_floor >= pf["stand_radius"]
    t_over, _, _, _ = towel(cand, True)
    t_clear, _, _, _ = towel(cand, False)
    vo, co, _ = best_point(cand, np.where(can_stand, t_over, 0.0))
    vc, cc, _ = best_point(cand, np.where(can_stand, t_clear, 0.0))
    td, tds, tdb, tws = towel([pf["centre"]], True)
    lane = sample_line(
        next(p["line"] for p in plan["passages"] if p["id"] == "main_entry_lane"), 0.02
    )
    gap = (
        np.hypot(lane[:, 0] - pf["centre"][0], lane[:, 1] - pf["centre"][1])
        - pf["towel_radius_ref"]
    )
    ref = pf["towel_radius_ref"]
    res["main_performer"] = {
        "reference": {
            "towel_radius": ref,
            "stand_radius": pf["stand_radius"],
            "margin_people": mp,
            "note": pf["note"],
        },
        "largest_free_floor_circle": {
            "radius": round(r1, 3),
            "centre": c1,
            "limited_by": floor.name(w_fine[i1]),
        },
        "largest_free_floor_circle_on_stove_axis": {"radius": round(ra, 3), "centre": ca},
        "declared_centre": {
            "centre": pf["centre"],
            "floor_clearance": round(float(d_decl[0]), 3),
            "limited_by": floor.name(w_decl[0]),
            "towel_radius_over_stove": round(float(td[0]), 3),
            "to_walls_and_benches_above_1m": round(float(tds[0]), 3),
            "to_seated_bodies_above_1m": round(float(tdb[0]), 3),
            "limited_by_solid": air.name(tws[0]),
        },
        "best_towel_radius_over_stove": {"radius": round(vo, 3), "stand_at": co},
        "best_towel_radius_clear_of_stove_and_guard": {"radius": round(vc, 3), "stand_at": cc},
        "entry_lane_centre_line_outside_towel_circle_by": round(float(gap.min()), 3),
        "method": "床の円は高さ0.05〜1.90 mの全物体（ベンチ・ガード・壁・扉枠・桶）への平面距離。タオルは高さ1.00〜2.30 mの物体と、着座した検査用人体から0.25 m離した距離。",
    }
    if r1 < ref:
        issue("main_floor_circle", "演者の床に基準円R1.30が入らない", round(r1, 3), ref)
    if float(td[0]) < ref:
        issue(
            "main_towel_declared",
            "指定した立ち位置でタオルR1.30が人・壁に届く",
            round(float(td[0]), 3),
            ref,
        )
    if vc < ref:
        issue(
            "main_towel_clear_of_stove",
            "ストーブとガードの上を通さない水平一周はR1.30に足りない（ストーブ上を通す前提）",
            round(vc, 3),
            ref,
        )
    if float(gap.min()) < 0.30:
        issue(
            "main_entry_lane_vs_performer",
            "入口からの通りの中心線が基準円から0.30 m離れていない",
            round(float(gap.min()), 3),
            0.30,
        )
    issue(
        "main_west_seats_access",
        "西の3席と北の西側へは演者の床を横切って入る（開始前後のみ）。通りは東側だけが演者の床と分かれている",
        None,
        None,
        "by_design",
    )
    issue(
        "main_performer_real_test",
        "演者による動作確認、ヒーター機種・離隔・ガード形状の再選定は未実施",
        None,
        None,
        "unverified",
    )

    # --- 10. plant equipment against the doors on the way in
    eq = []
    for ob in objs:
        if ob.get("v10_item") == "equipment":
            lo, hi = scene_geo.bbox(ob)
            eq.append(
                {
                    "id": ob.get("v10_id"),
                    "label": ob.get("v10_label"),
                    "plan_size": [round(float(hi[0] - lo[0]), 3), round(float(hi[1] - lo[1]), 3)],
                    "height": round(float(hi[2] - lo[2]), 3),
                    "narrow_side": round(float(min(hi[0] - lo[0], hi[1] - lo[1])), 3),
                }
            )
    route = [d for d in doors if d["id"] in plan["plant"]["route_doors"]]
    if eq and route:
        narrow = min(route, key=lambda d: d["clear_width"])
        stuck = [
            e["id"]
            for e in eq
            if e["narrow_side"] > narrow["clear_width"] - 0.02
            or e["height"] > plan["doorHeight"] - 0.07
        ]
        res["plant"] = {
            "equipment": eq,
            "route_doors": route,
            "narrowest_door": narrow,
            "do_not_pass_in_one_piece": stuck,
            "note": "外形の短辺と高さを扉の有効寸法と比べただけ。回転・傾け・分割・外部搬入口は未検討。",
        }
        if stuck:
            issue(
                "plant_carry_in",
                "客用扉を通る交換経路では一体で通らない機器がある（外部搬入口は物件未定）",
                stuck,
                f"扉の有効幅 {narrow['clear_width']} m",
            )
    else:
        unmeasured.append("plant carry-in: equipment or route doors missing")
    issue(
        "plant_capacity",
        "機器の能力・台数・熱源方式・屋外放熱の位置と権利・点検寸法はメーカー未照合",
        None,
        None,
        "unverified",
    )

    # --- 11. waiting and rest capacity from the measured counts
    op = plan["operations"]
    rest_n = res["rest_places_measured"]
    cold_n = roles.get("pool_cold", 0)
    spare = supported.get("perch", 0) + roles.get("waiting", 0)
    rounds = math.ceil(op["event_people"] / max(cold_n, 1))
    res["capacity"] = {
        "in_house_target": op["in_house_target"],
        "rest_places": rest_n,
        "short_if_everyone_rests": op["in_house_target"] - rest_n,
        "cold_positions": cold_n,
        "event_people": op["event_people"],
        "waiting_after_first_group": max(0, op["event_people"] - cold_n),
        "rounds": rounds,
        "longest_wait_s": (rounds - 1) * op["cold_turn_s"],
        "waiting_places_outside_the_lane": spare,
        "perch_seats": supported.get("perch", 0),
        "standing_places": roles.get("waiting", 0),
        "note": op["note"],
    }
    if rest_n != op["rest_seats"]:
        fail.append(f"rest places with a measured seat surface: {rest_n}, plan {op['rest_seats']}")
    # Parent: count the shared Hall seats per operating state, never twice.
    scenarios = []
    room_rest = roles.get("rest_chair", 0) + roles.get("rest_lounger", 0)
    hall_rest = supported.get("rest_builtin", 0)
    for state in op.get("scenarios", []):
        total = (
            state["in_room_rest"]
            + state["hall_official_rest"]
            + state["cold"]
            + state.get("queue_on_hall_official", 0)
            + state["queue_on_spare_perch"]
            + state["queue_standing"]
        )
        valid = (
            total == state["total"] == op["in_house_target"]
            and state["in_room_rest"] <= room_rest
            and state["hall_official_rest"] + state.get("queue_on_hall_official", 0) <= hall_rest
            and state["cold"] <= cold_n
            and state["queue_on_spare_perch"] <= supported.get("perch", 0)
            and state["queue_standing"] <= roles.get("waiting", 0)
        )
        scenarios.append(dict(state, arithmetic_and_place_counts_ok=bool(valid)))
        if not valid:
            fail.append(
                "operating scenario exceeds measured places or duplicates shared seats: "
                + state["name"]
            )
    res["capacity"]["operating_scenarios"] = scenarios
    res["capacity"]["scenario_note"] = (
        "10人イベント時は室内休憩14人、空く浴室正式2席も待機へ。休憩16人時は8人イベント。静的な人数配分で時系列・救助・需要は未検証。"
    )
    if spare < max(0, op["event_people"] - cold_n):
        issue(
            "cold_waiting_places",
            "専用待機だけでは不足。10人イベントは空く浴室正式2席を共用し、他の休憩は室内14人までとする運用条件",
            {"dedicated_places": spare, "shared_hall_seats": hall_rest},
            op["event_people"] - cold_n,
            "conditional",
        )
    if op["in_house_target"] - rest_n > supported.get("perch", 0):
        issue(
            "rest_overflow",
            "全員が同時に休むと休憩席が足りず、休憩外の腰掛け（冷槽待ちと共用）でも受けきれない",
            {"short": op["in_house_target"] - rest_n, "perch": supported.get("perch", 0)},
            "不足0",
        )

    # --- 12. ceilings against the assumed service band; screens against a standing eye
    band_u = a["beam_soffit"] - a["service_band"]
    ceil_rows, top_of_reveal = [], None
    for ob in objs:
        if ob.name.startswith("CEIL_") and ("ceiling" in ob.name.lower()):
            lo, hi = scene_geo.bbox(ob)
            ceil_rows.append({"object": ob.name, "underside": round(float(lo[2]), 3)})
        if ob.name.startswith("CEIL_") and ob.name.endswith("_cove_black"):
            hi = scene_geo.bbox(ob)[1]
            top_of_reveal = max(top_of_reveal or -1e9, float(hi[2]))
    res["ceilings"] = {
        "band_underside_assumed": band_u,
        "ceilings": ceil_rows,
        "highest_light_reveal": None if top_of_reveal is None else round(top_of_reveal, 3),
    }
    if any(r["underside"] > band_u + 1e-6 for r in ceil_rows):
        issue(
            "ceiling_in_band",
            "天井の下端が仮の設備帯の内側にある",
            max(r["underside"] for r in ceil_rows),
            band_u,
        )
    if top_of_reveal is not None and top_of_reveal > band_u + 1e-6:
        issue(
            "reveal_in_band",
            "間接光のスリット上端が仮の設備帯（+2.65〜+3.00）に入る。ダクトとの取り合いは未設計",
            round(top_of_reveal, 3),
            band_u,
        )
    scr = by_name.get("Rest_screens")
    if scr is not None:
        res["rest_screen_top"] = round(float(scene_geo.bbox(scr)[1][2]), 3)
        res["rest_screen_note"] = (
            "板高1.30 m。着席者間の視線を抑える意図の配置。監視・救助の視認性と全席の可視性は未検証。"
        )

    # --- 13. lights, images, cameras, layers, size
    em = {}
    for ob in objs:
        mats = ob.data.materials
        if len(mats) and mats[0] is not None and mats[0].name.startswith("light_"):
            e = em.setdefault(mats[0].name[len("light_") :], {"objects": 0, "area_m2": 0.0})
            e["objects"] += 1
            e["area_m2"] = round(e["area_m2"] + sum(p.area for p in ob.data.polygons), 4)
    res["lighting"] = {
        "emitters": em,
        "spot_lights": len([o for o in bpy.context.scene.objects if o.type == "LIGHT"]),
        "note": "光源の強さ・色・露出は元案（V4〜V8）の値をそのまま使う。照度計算ではない。",
    }
    ext = [i.name for i in bpy.data.images if i.source == "FILE" and i.packed_file is None]
    res["images"] = {
        "total": len(bpy.data.images),
        "packed": len([i for i in bpy.data.images if i.packed_file is not None]),
        "external_files": ext,
    }
    if ext:
        fail.append(f"the model depends on external image files: {ext[:6]}")
    cams = sorted(o.name for o in bpy.context.scene.objects if o.type == "CAMERA")
    lost = [c["name"] for c in plan["cameras"] if "Cam_" + c["name"] not in cams]
    res["cameras"] = cams
    if lost:
        fail.append(f"cameras missing: {lost}")
    layers = {}
    for cname, prefix in (
        ("CEIL_ceilings", "CEIL_"),
        ("CHECK_people", "CHECK_"),
        ("STUDY_architecture", "STUDY_"),
    ):
        col = bpy.data.collections.get(cname)
        if col is None:
            fail.append(f"collection missing: {cname}")
            continue
        bad = [o.name for o in col.objects if not o.name.startswith(prefix)]
        layers[cname] = {
            "objects": len(col.objects),
            "hide_render": col.hide_render,
            "wrong_prefix": bad[:5],
        }
        if bad or (cname != "CEIL_ceilings" and not col.hide_render):
            fail.append(f"layer {cname}: wrong object names or not render-hidden")
    res["layers"] = layers
    res["model"] = {
        "objects": len(bpy.context.scene.objects),
        "mesh_objects": len(objs),
        "base_polygons": int(sum(len(o.data.polygons) for o in objs)),
        "blender": bpy.app.version_string,
    }
    for text in plan["unverified"]:
        issues.append(
            {
                "id": "unverified",
                "what": text,
                "measured": None,
                "target": None,
                "status": "unverified",
            }
        )
    res["ok"] = not fail
    return res


def summary(m):
    p = m.get("main_performer", {})
    return (
        f"failures={len(m['failures'])} open_issues={len(m['open_issues'])} not_measured={len(m['not_measured'])} "
        f"rest={m.get('rest_places_measured')} floor_circle_R={p.get('largest_free_floor_circle', {}).get('radius')} "
        f"water={m.get('pool_water_total_m2')} m2"
    )


# ---------------------------------------------------------------------------------------------- steps
def step_estimate(args, root):
    plan, plan_path = load_plan(args)
    try:
        assets = assets_root(args, root)
    except RuntimeError:
        assets = None
    rec = {
        "disk": estimate(root, assets),
        "plan": plan_checks(plan),
        "plan_file": plan_path,
        "assets": assets,
    }
    write_json(out_path(root, "verification", "v10_estimate.json", replace=True), rec)
    print(
        f"V10_ESTIMATE upper {rec['disk']['upper_total_mb']} MB of {BUDGET_MB} MB, within_budget={rec['disk']['within_budget']}, "
        f"zones sum {rec['plan']['sum_gross_m2']} m2, plan failures={len(rec['plan']['failures'])}"
    )
    if not rec["disk"]["within_budget"] or rec["plan"]["failures"]:
        raise RuntimeError(f"estimate failed: {rec['plan']['failures']}")
    return rec


def step_build(args, root):
    model = out_path(root, "model", MODEL_NAME, args.replace)
    rec_path = out_path(root, "verification", "v10_build.json", args.replace)
    plan, plan_path = load_plan(args)
    pc = plan_checks(plan)
    if pc["failures"]:
        raise RuntimeError(f"plan is not a clean partition: {pc['failures']}")
    assets = assets_root(args, root)
    est = estimate(root, assets)
    if not est["within_budget"]:
        raise RuntimeError("disk estimate exceeds the budget")
    t0 = time.time()
    import compact_v10_rooms as rooms
    from sauna import furniture, geo, materials
    from sauna import scene as sc

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    materials.ASSET_ROOT = assets
    geo.reseed(SEED)
    surface_palette = materials.palette(tv_level=sc.TV_LEVEL)
    fixture_materials = sc.light_materials()
    furniture.load_rocks(assets)
    warnings = rooms.build_all(
        plan, surface_palette, fixture_materials, geo.collection("CompactV10")
    )
    scene.camera = bpy.data.objects["Cam_main"]
    sc.configure_render(scene)
    scene["v10_plan_sha256"] = sha256_file(plan_path)
    scene["v10_note"] = (
        "V10 compact comparison candidate. The original V8/V9 design is not replaced. Structure, law, equipment and cost are not verified."
    )
    bpy.ops.file.pack_all()  # textures travel inside the file: no dependency on the V8 asset folder after the build
    if not inside(root, model):
        raise RuntimeError("refusing to save outside the V10 root")
    bpy.ops.wm.save_as_mainfile(filepath=model, check_existing=False, compress=True)
    m = measure(plan)
    total = dir_bytes(root)
    rec = {
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "seconds": round(time.time() - t0, 1),
        "model": file_state(model),
        "plan_file": plan_path,
        "plan_sha256": scene["v10_plan_sha256"],
        "assets_read_from": assets,
        "seed": SEED,
        "build_warnings": warnings,
        "plan_checks": pc,
        "measurements": m,
        "disk_estimate": est,
        "root_total_mb": round(total / 1e6, 2),
    }
    write_json(rec_path, rec)
    print(
        f"V10_BUILD_MODEL {rec['model']['bytes'] / 1e6:.1f} MB sha256={rec['model']['sha256']} -> {model}"
    )
    print(f"V10_BUILD_MEASURE {summary(m)} warnings={len(warnings)}")
    for f in m["failures"]:
        print("V10_FAILURE", f)
    if total / 1e6 > BUDGET_MB:
        raise RuntimeError(f"V10 root is {total / 1e6:.0f} MB, over the budget")
    print("V10_BUILD_OK (run --step verify on the saved file next)")


def open_model(root):
    model = os.path.join(root, "model", MODEL_NAME)
    if not os.path.isfile(model):
        raise RuntimeError(f"model not found: {model} (run --step build first)")
    state = file_state(model)
    bpy.ops.wm.open_mainfile(filepath=model)
    if norm(bpy.data.filepath) != norm(model):
        raise RuntimeError(f"opened {bpy.data.filepath}, expected {model}")
    return model, state


def step_verify(args, root):
    rec_path = out_path(root, "verification", "v10_verification.json", replace=True)
    plan, plan_path = load_plan(args)
    model, before = open_model(root)
    pc = plan_checks(plan)
    m = measure(plan)
    m["failures"] = pc["failures"] + m["failures"]
    if bpy.context.scene.get("v10_plan_sha256") != sha256_file(plan_path):
        m["failures"].append("the plan file changed after the model was built (rebuild)")
    after = file_state(model)
    if before["sha256"] != after["sha256"]:
        m["failures"].append("the model file changed while it was verified")
    m["ok"] = not m["failures"]
    rec = {
        "checked": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "model_file": after,
        "model_unchanged_by_verify": before["sha256"] == after["sha256"],
        "plan_file": plan_path,
        "plan_sha256": sha256_file(plan_path),
        "plan_checks": pc,
        "root_total_mb": round(dir_bytes(root) / 1e6, 2),
        **m,
    }
    write_json(rec_path, rec)
    print(f"V10_VERIFY {summary(m)} model_sha256={after['sha256']}")
    for f in m["failures"]:
        print("V10_FAILURE", f)
    for i in m["open_issues"]:
        if i["status"] == "not_achieved":
            print("V10_OPEN_ISSUE", i["id"], i["measured"], "target", i["target"])
    if m["failures"]:
        raise RuntimeError(f"V10 verification failed ({len(m['failures'])} failures)")
    print("V10_VERIFY_OK (open issues and unverified items remain; see v10_verification.json)")


def named(group, name):
    return [b for b in group if b.name == name or b.name.startswith(name + ".")]


def step_render(args, root):
    from sauna import scene as sc

    if not args.view:
        raise RuntimeError("--view is required")
    stem = "v10_" + args.view + (f"_{args.tag}" if args.tag else "")
    png = out_path(root, "tests" if args.tests else "renders", stem + ".png", args.replace)
    log = out_path(root, "verification", "v10_render_log.jsonl", append=True)
    model, before = open_model(root)
    scene = bpy.context.scene
    cam = bpy.data.objects.get("Cam_" + args.view)
    if cam is None or cam.type != "CAMERA":
        raise RuntimeError(
            f"camera Cam_{args.view} not found; have {sorted(o.name for o in bpy.data.objects if o.type == 'CAMERA')}"
        )
    scene.camera = cam
    exposure = args.exposure if args.exposure is not None else float(cam.get("exposure", 0.0))
    ambient = args.world if args.world is not None else float(cam.get("v10_ambient", 0.0))
    aspect = args.aspect if args.aspect is not None else float(cam.get("v10_aspect", 1.5))
    sc.configure_render(
        scene,
        args.res,
        round(args.res / aspect),
        args.samples,
        args.threshold,
        exposure,
        ambient=ambient,
    )
    if args.device == "CPU":
        scene.cycles.device = "CPU"
    scene.cycles.adaptive_min_samples = min(64, args.samples)
    devices = (
        [d.name for d in bpy.context.preferences.addons["cycles"].preferences.devices if d.use]
        if args.device != "CPU"
        else ["CPU"]
    )
    if not devices:
        raise RuntimeError(
            "no OptiX device is enabled (nothing rendered); pass --device CPU to render without it"
        )
    hide = [
        n for n in (args.hide if args.hide is not None else cam.get("v10_hide", "")).split(",") if n
    ]
    show = [
        n for n in (args.show if args.show is not None else cam.get("v10_show", "")).split(",") if n
    ]
    for n in hide:
        for col in named(bpy.data.collections, n):
            col.hide_render = True
    for n in show:
        for col in named(bpy.data.collections, n):
            col.hide_render = False
    study_on = any(n.startswith("STUDY") for n in show)
    if study_on:
        gain = args.study_gain * 2.0 ** (
            -exposure
        )  # study colours read the same at any camera exposure
        for mat in bpy.data.materials:
            if (
                "v10_emit_base" in mat.keys()
                and mat.node_tree
                and mat.node_tree.nodes.get("STUDY_EMIT")
            ):
                mat.node_tree.nodes["STUDY_EMIT"].inputs["Strength"].default_value = (
                    float(mat["v10_emit_base"]) * gain
                )
        bg = (
            scene.world.node_tree.nodes.get("Background")
            if scene.world and scene.world.node_tree
            else None
        )
        if bg and ambient > 0:
            bg.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
        try:
            scene.world.cycles_visibility.camera = False
        except Exception:
            pass
    for prefix in [n for n in (args.hide_objects or "").split(",") if n]:
        for ob in bpy.data.objects:
            if ob.name.startswith(prefix):
                ob.hide_render = True
    scene.render.filepath = png
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t0
    if not os.path.isfile(png):
        raise RuntimeError(f"render produced no file: {png}")
    after = file_state(model)
    rec = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "view": args.view,
        "file": png,
        "bytes": os.path.getsize(png),
        "sha256": sha256_file(png),
        "model_used": bpy.data.filepath,
        "model_sha256": after["sha256"],
        "model_unchanged_by_render": before["sha256"] == after["sha256"],
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "max_samples": args.samples,
        "threshold": args.threshold,
        "exposure": exposure,
        "ambient": ambient,
        "collections_hidden": hide,
        "collections_shown": show,
        "devices": devices,
        "seconds": round(dt, 1),
        "blender": bpy.app.version_string,
        "test": bool(args.tests),
        "note": "visibility and study brightness are changed in memory for this render only; the model file is not saved",
    }
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if not rec["model_unchanged_by_render"]:
        raise RuntimeError("the model file changed during the render")
    print(
        f"V10_RENDER_OK view={args.view} {rec['resolution'][0]}x{rec['resolution'][1]} samples<={args.samples} exposure={exposure} "
        f"time={dt:.1f}s {rec['bytes'] / 1e6:.2f} MB -> {png}"
    )
    print(f"V10_RENDER_MODEL {bpy.data.filepath} sha256={after['sha256']}")


def step_glb(args, root):
    """Interchange file for the viewer. Materials are simplified in memory (the .blend is not saved)."""
    glb = out_path(root, "model", GLB_NAME, args.replace)
    rec_path = out_path(root, "verification", "v10_glb.json", replace=True)
    bake_files = [
        os.path.join(root, "assets", "product_floor", f"ST33N_{k}.png")
        for k in ("basecolor", "roughness", "normal", "joint_mask")
    ] + [os.path.join(root, "verification", "product_floor_bake.json")]
    if not args.no_floor_bake and not args.replace and any(os.path.exists(p) for p in bake_files):
        raise RuntimeError(
            "the floor bake outputs already exist; pass --replace or --no-floor-bake"
        )
    model, before = open_model(root)
    bakes = {}
    if not args.no_floor_bake:
        from sauna.product_bake import bake_floor, portable_floor

        for mat in list(bpy.data.materials):
            if mat.get("glb_product_floor"):
                bakes[mat.name] = bake_floor(mat, root)
    flat, textured, left = [], [], []
    for mat in bpy.data.materials:
        nt = mat.node_tree
        if nt is None:
            continue
        if mat.name in bakes:
            portable_floor(mat, *bakes[mat.name])
            textured.append(mat.name)
            continue
        if "glb_color" not in mat.keys() or mat.name.startswith("moon_rock"):
            left.append(mat.name)
            continue
        image, scale = None, None
        if mat.get("glb_image", ""):
            for n in nt.nodes:
                if n.type == "TEX_IMAGE" and n.image and "diff" in n.image.name:
                    image = n.image
                if n.type == "MAPPING":
                    scale = tuple(n.inputs["Scale"].default_value)
        rgba = [*list(mat["glb_color"]), 1.0]
        rough, metal, emit, alpha = (
            float(mat["glb_rough"]),
            float(mat["glb_metal"]),
            float(mat["glb_emit"]),
            float(mat["glb_alpha"]),
        )
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
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
            mx.inputs[7].default_value = rgba
            nt.links.new(mx.outputs[2], bsdf.inputs["Base Color"])
            textured.append(mat.name)
        else:
            bsdf.inputs["Base Color"].default_value = rgba
            flat.append(mat.name)
        if emit > 0:
            bsdf.inputs["Emission Color"].default_value = rgba
            bsdf.inputs["Emission Strength"].default_value = emit
        if alpha < 1.0:
            bsdf.inputs["Alpha"].default_value = alpha
            try:
                mat.surface_render_method = "BLENDED"
            except Exception:
                mat.blend_method = "BLEND"
    kw = dict(
        filepath=glb,
        export_format="GLB",
        export_apply=True,
        export_cameras=True,
        export_lights=False,
        export_yup=True,
        export_image_format="AUTO",
        export_texcoords=True,
        export_normals=True,
    )
    if args.draco:
        kw.update(export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
    bpy.ops.export_scene.gltf(**kw)
    after = file_state(model)
    prefixes = {
        p: len([o for o in bpy.data.objects if o.name.startswith(p)])
        for p in ("CEIL_", "CHECK_", "STUDY_")
    }
    rec = {
        "file": file_state(glb),
        "source_model": bpy.data.filepath,
        "source_model_sha256": after["sha256"],
        "source_model_unchanged": before["sha256"] == after["sha256"],
        "draco": bool(args.draco),
        "floor_baked": bool(bakes),
        "materials_flat_colour": len(flat),
        "materials_with_texture": textured,
        "materials_left_as_is": left,
        "switchable_by_name": {
            "prefix_counts": prefixes,
            "note": "天井 CEIL_、検査用人体 CHECK_、検討表示 STUDY_ はオブジェクト名の接頭辞で表示切替できる（すべて書き出す）。",
        },
        "differs_from_cycles": [
            "手続き型の石・タイル・目地は単色に置換（浴室床だけ1.2 m角のベイク画像）",
            "水は半透明の単色。屈折・吸収・コースティクスなし",
            "光源は発光色の面のみ。Cyclesの間接光・暗さ・露出・ホワイトバランスは再現されない",
            "ガラスは半透明の単色",
            "面取りは書き出し時に適用（メッシュは重くなる）",
        ],
        "root_total_mb": round(dir_bytes(root) / 1e6, 2),
    }
    write_json(rec_path, rec)
    if not rec["source_model_unchanged"]:
        raise RuntimeError("the model file changed during the export")
    print(f"V10_GLB_OK {rec['file']['bytes'] / 1e6:.1f} MB from {bpy.data.filepath} -> {glb}")


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--step", required=True, choices=["estimate", "build", "verify", "render", "glb"]
    )
    ap.add_argument(
        "--out-root", required=True, help="canonical .../sauna-design/fable-v10 (must exist)"
    )
    ap.add_argument(
        "--plan", default=None, help="default: ../plan/compact_v10.json next to this script"
    )
    ap.add_argument(
        "--assets",
        default=None,
        help="folder with polyhaven/ (default: <out-root>/assets, else ../fable-v8/assets, read only)",
    )
    ap.add_argument(
        "--replace", action="store_true", help="allow replacing this script's own earlier outputs"
    )
    ap.add_argument(
        "--view", default=None, help="camera name without Cam_ (see cameras in the plan)"
    )
    ap.add_argument("--res", type=int, default=2400)
    ap.add_argument("--aspect", type=float, default=None)
    ap.add_argument("--samples", type=int, default=1024)
    ap.add_argument("--threshold", type=float, default=0.015)
    ap.add_argument("--exposure", type=float, default=None)
    ap.add_argument("--world", type=float, default=None, help="ambient world light")
    ap.add_argument(
        "--hide",
        default=None,
        help="comma separated collections to hide (default: the camera's own list)",
    )
    ap.add_argument(
        "--show",
        default=None,
        help="comma separated collections to show, e.g. CHECK_people,STUDY_architecture",
    )
    ap.add_argument(
        "--hide-objects", default=None, help="comma separated object-name prefixes to hide"
    )
    ap.add_argument("--study-gain", type=float, default=1.0)
    ap.add_argument("--tests", action="store_true", help="write to tests/ instead of renders/")
    ap.add_argument("--tag", default="")
    ap.add_argument("--device", default="OPTIX", choices=["OPTIX", "CPU"])
    ap.add_argument("--draco", action="store_true")
    ap.add_argument("--no-floor-bake", action="store_true")
    args = ap.parse_args(argv)
    root = check_root(args.out_root)
    {
        "estimate": step_estimate,
        "build": step_build,
        "verify": step_verify,
        "render": step_render,
        "glb": step_glb,
    }[args.step](args, root)


main()
