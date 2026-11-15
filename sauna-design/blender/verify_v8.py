"""v8 check on the built mesh (read-only; the model is not saved): the two small saunas, the two cold pools and the rest annex.

blender -b <sauna_a_v8.blend> --python verify_v8.py -- <fable-v8>

Measures seat / foot / step heights, fronts, aisles, pool floors and treads, screen heights and walking widths on the
evaluated geometry (check bodies and water hidden), compares them with sub_layout.py / water_layout.py, tests every
assumed body box against the mesh, and compares the stages that v8 did not touch (main sauna, rest room, doors, product
stage, service rooms, structure walls) with the frozen v7 model. Writes <fable-v8>/verification/v8_design_check.json.

A concept check with assumed adult sizes. Not verified: code compliance, heater type and maker clearances, how heat and
steam move, pool plant and water quality, slip resistance, structure, ventilation, cost.
"""

import hashlib
import json
import os
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sauna import bath_layout as BL  # noqa: E402
from sauna import main_layout as ML
from sauna import sub_layout as SL
from sauna import water_layout as WL
from sauna.products import FLOOR, ZL300  # noqa: E402

root = Path(sys.argv[sys.argv.index("--") + 1])
model = Path(bpy.data.filepath)
scene = bpy.context.scene

# ---- digests of the untouched stages (taken before anything is hidden) ---------------------------------------------
KEEP = ("Main", "Rest", "Doors", "Product_study_v7")


def digest(o, uv=False):
    h = hashlib.sha256()
    for row in o.matrix_world:
        h.update(struct.pack("4f", *row))
    for v in o.data.vertices:
        h.update(struct.pack("3f", *v.co))
    for p in o.data.polygons:
        h.update(struct.pack(f"{len(p.vertices)}I", *p.vertices))
    for m in o.modifiers:
        h.update(str((m.type, getattr(m, "width", None), getattr(m, "segments", None))).encode())
    if uv and o.data.uv_layers.active:
        for v in o.data.uv_layers.active.data:
            h.update(struct.pack("2f", *v.uv))
    return h.hexdigest()


def snapshot():
    out = {}
    for c in KEEP:
        col = bpy.data.collections.get(c)
        out[c] = (
            {o.name: (digest(o), digest(o, True)) for o in col.all_objects if o.type == "MESH"}
            if col
            else {}
        )
    out["Service"] = {
        o.name: (digest(o), digest(o, True))
        for o in bpy.data.objects
        if o.type == "MESH"
        and (
            o.name.startswith("Service_")
            or o.name.startswith("Ceiling_")
            or o.name in ("Structure_Walls", "Structure_Roof", "Structure_Base")
        )
    }
    out["lights"] = {
        o.name: (round(o.data.energy, 4), [round(v, 4) for v in o.location])
        for o in bpy.data.objects
        if o.type == "LIGHT"
    }
    out["cameras"] = {
        o.name: [
            [round(v, 5) for v in o.location],
            [round(v, 5) for v in o.rotation_euler],
            o.data.lens,
            round(o.data.shift_y, 4),
            o.get("exposure"),
        ]
        for o in bpy.data.objects
        if o.type == "CAMERA"
    }
    out["emitters"] = {}
    for o in bpy.data.objects:
        if (
            o.type == "MESH"
            and o.data.materials
            and o.data.materials[0]
            and o.data.materials[0].name.startswith("light_")
        ):
            e = out["emitters"].setdefault(o.data.materials[0].name[6:], [0, 0.0])
            e[0] += 1
            e[1] += sum(p.area for p in o.data.polygons)
    return out


snap8 = snapshot()

# ---- rays ----------------------------------------------------------------------------------------------------------
people = [c for c in bpy.data.collections if c.name.startswith("Check_people")]
body_bbox = {}
for c in people:
    for ob in c.objects:
        pts = [ob.matrix_world @ Vector(v) for v in ob.bound_box]
        body_bbox[ob.name[len("Body_") :]] = [min(p[i] for p in pts) for i in range(3)] + [
            max(p[i] for p in pts) for i in range(3)
        ]
    c.hide_viewport = True
for ob in bpy.data.objects:  # people stand in the water: the water volumes must not stop the rays
    if ob.name.endswith("_water"):
        ob.hide_viewport = True
bpy.context.view_layer.update()
deps = bpy.context.evaluated_depsgraph_get()


def ray(o, d, dist=10.0):
    ok, loc, _n, _i, ob, _m = scene.ray_cast(deps, Vector(o), Vector(d).normalized(), distance=dist)
    return (loc, ob.name) if ok else (None, None)


OFF = (
    -0.03,
    0.0,
    0.03,
)  # boards and slats have 8 mm gaps: every probe is a 3 x 3 bundle and the nearest hit counts


def _bundle(o, d, pick):
    d = Vector(d).normalized()
    a = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(a).normalized()
    v = d.cross(u)
    best = None
    for du in OFF:
        for dv in OFF:
            loc, name = ray(Vector(o) + u * du + v * dv, d)
            if loc is not None:
                t = (loc - Vector(o)).dot(d)
                if best is None or t < best[0]:
                    best = (t, loc, name)
    return (round(pick(best[1]), 4), best[2]) if best else (None, None)


def down(x, y, z=2.0):
    return _bundle((x, y, z), (0, 0, -1), lambda p: p.z)


def up(x, y, z):
    return _bundle((x, y, z), (0, 0, 1), lambda p: p.z)


def reach(o, d, axis):
    return _bundle(o, d, lambda p: p[axis])


def verts(name):
    ob = bpy.data.objects[name].evaluated_get(deps)
    me = ob.to_mesh()
    out = [ob.matrix_world @ v.co for v in me.vertices]
    ob.to_mesh_clear()
    return out


rows = []


def rec(group, what, measured, planned, name=""):
    rows.append(
        {
            "group": group,
            "what": what,
            "measured": None if measured is None else round(measured, 4),
            "planned": None if planned is None else round(planned, 4),
            "diff_mm": None
            if planned is None or measured is None
            else round((measured - planned) * 1000, 1),
            "object": name or "",
        }
    )


# ---- self-loyly room -----------------------------------------------------------------------------------------------
s, sd = SL.SELF, SL.self_dims()
rec("self", "west wall face x", reach((7.5, 11.2, 1.7), (-1, 0, 0), 0)[0], s["xw"])
rec("self", "east wall face x", reach((7.5, 11.2, 1.7), (1, 0, 0), 0)[0], s["xe"])
rec("self", "north wall face y", reach((8.4, 12.0, 1.9), (0, 1, 0), 1)[0], SL.Y1)
rec("self", "south wall face y", reach((6.6, 11.2, 1.7), (0, -1, 0), 1)[0], SL.Y0)
rec("self", "ceiling underside z", up(7.6, 11.6, 1.0)[0], SL.H)
for kind, label, x0, y0, x1, y1, z in SL.self_levels():
    cy = min((y0 + y1) / 2, 13.25) if kind == "corner" else (y0 + y1) / 2
    rec("self", f"{label} 上面 z", down((x0 + x1) / 2, cy, z + 0.4)[0], z)
rec("self", "west seat front x", reach((7.4, 12.0, 0.45 - 0.012), (-1, 0, 0), 0)[0], sd["w_front"])
rec(
    "self",
    "north seat front y (0.675)",
    reach((7.4, 12.3, 0.675 - 0.012), (0, 1, 0), 1)[0],
    sd["n_front"],
)
rec(
    "self",
    "north seat front y (0.90)",
    reach((8.7, 12.3, 0.90 - 0.012), (0, 1, 0), 1)[0],
    sd["n_front"],
)
rec(
    "self",
    "foot level front y (0.225)",
    reach((7.4, 12.3, 0.225 - 0.012), (0, 1, 0), 1)[0],
    sd["ledge_front"],
)
rec(
    "self",
    "half step front y",
    reach((8.7, 12.2, 0.225 - 0.012), (0, 1, 0), 1)[0],
    sd["step_front"],
)
rec("self", "west seat south end y", reach((6.4, 10.9, 0.45 - 0.012), (0, 1, 0), 1)[0], s["w_end"])
hx, hy = s["heater"]["c"]
g = reach((hx, sd["step_front"] - 0.02, 0.39), (0, -1, 0), 1)[0]
rec(
    "self",
    "aisle: half step to guard rail",
    None if g is None else sd["step_front"] - g,
    sd["aisle_step_to_guard"],
)
g = reach((sd["w_front"] + 0.02, hy, 0.39), (1, 0, 0), 0)[0]
rec(
    "self",
    "floor: west seat nose to guard rail",
    None if g is None else g - sd["w_front"],
    sd["floor_w_bench_to_guard"],
)
ja, jb = ray((7.6, 10.5, 1.0), (-1, 0, 0))[0], ray((7.6, 10.5, 1.0), (1, 0, 0))[0]
rec("self", "door clear width between jambs", None if not (ja and jb) else jb.x - ja.x, None)
# rounded corner: the lining stands on the planned radius
R = s["corner_r"]
cxr, cyr = s["xw"] + R, SL.Y1 - R
import math  # noqa: E402

for deg in (112, 135, 158):  # the slats have 8 mm gaps: nearest of five rays 1.2 degrees apart
    hits = []
    for k in range(-2, 3):
        a = math.radians(deg + 1.2 * k)
        loc, name = ray((cxr, cyr, 1.5), (math.cos(a), math.sin(a), 0), 2.0)
        if loc is not None:
            hits.append((math.hypot(loc.x - cxr, loc.y - cyr), name))
    rec(
        "self",
        f"rounded corner radius at {deg} deg",
        min(hits)[0] if hits else None,
        R,
        min(hits)[1] if hits else "",
    )

# ---- dry room ------------------------------------------------------------------------------------------------------
d, dd = SL.DRY, SL.dry_dims()
rec("dry", "west wall face x", reach((11.6, 13.2, 1.9), (-1, 0, 0), 0)[0], d["xw"])
rec("dry", "east wall face x", reach((11.6, 13.6, 1.0), (1, 0, 0), 0)[0], d["xe"])
rec("dry", "north wall face y", reach((11.8, 13.0, 1.0), (0, 1, 0), 1)[0], SL.Y1)
rec("dry", "ceiling underside z", up(11.6, 12.4, 1.0)[0], SL.H)
for kind, label, x0, y0, x1, y1, z in SL.dry_levels():
    xq = x0 + 0.75 * (x1 - x0) if kind == "deck" else (x0 + x1) / 2
    rec("dry", f"{label} 上面 z", down(xq, (y0 + y1) / 2, z + 0.4)[0], z)
tri = SL.dry_diag()
rec(
    "dry",
    "diagonal tread top z",
    down(sum(p[0] for p in tri) / 3, sum(p[1] for p in tri) / 3, 0.6)[0],
    d["step_top"],
)
rec("dry", "high bench front x", reach((11.8, 12.0, 0.90 - 0.012), (-1, 0, 0), 0)[0], dd["u_nose"])
rec(
    "dry",
    "foot deck front x",
    reach((11.8, 12.0, 0.45 - 0.012), (-1, 0, 0), 0)[0],
    dd["u_foot_front"],
)
rec(
    "dry",
    "half step front x (high bench)",
    reach((11.8, 12.0, 0.225 - 0.012), (-1, 0, 0), 0)[0],
    dd["u_step_front"],
)
rec("dry", "low deck front x", reach((11.9, 13.3, 0.45 - 0.012), (-1, 0, 0), 0)[0], dd["d_front"])
rec(
    "dry",
    "half step front x (deck)",
    reach((11.9, 13.3, 0.225 - 0.012), (-1, 0, 0), 0)[0],
    dd["d_step_front"],
)
rec(
    "dry",
    "aisle: deck half step to TV wall",
    (reach((11.9, 13.6, 0.21), (1, 0, 0), 0)[0] or 0)
    - (reach((11.9, 13.6, 0.225 - 0.012), (-1, 0, 0), 0)[0] or 0),
    dd["aisle_east_of_d_step"],
)
rec("dry", "high bench south end y", reach((9.9, 10.9, 0.90 - 0.012), (0, 1, 0), 1)[0], d["u_y"][0])
bk = d["back"]
for hz in (
    0.149,
    0.360,
    0.570,
):  # raked back: face of the boards at three board centres (single rays: the face is inclined)
    want = d["xw"] + bk["base"] - (bk["base"] - bk["top_in"]) * hz / bk["h"]
    loc, name = ray((10.6, 13.28, d["deck_top"] + hz), (-1, 0, 0))
    rec("dry", f"raked back face x at deck+{hz:.2f}", None if loc is None else loc.x, want, name)
wing_top = down(d["xw"] + 0.15, sum(d["wing"]["y"]) / 2, 2.0)[0]
rec("dry", "wing top z (wall end)", wing_top, d["wing"]["top"])
tvp = bpy.data.objects.get("Dry_TV_picture")
tvb = [tvp.matrix_world @ Vector(v) for v in tvp.bound_box]
rec(
    "dry",
    "TV picture centre y",
    (min(p.y for p in tvb) + max(p.y for p in tvb)) / 2,
    d["tv"]["c"][0],
    "Dry_TV_picture",
)
rec(
    "dry",
    "TV picture centre z",
    (min(p.z for p in tvb) + max(p.z for p in tvb)) / 2,
    d["tv"]["c"][1],
    "Dry_TV_picture",
)

# every seat of both rooms
seat_rows = []
for st in SL.all_seats():
    bx, by = st["b"]
    fx, fy = st["f"]
    q = 0.45 if st["posture"] == "legs_out" else 0.25
    seat_z, seat_ob = down(bx + fx * q, by + fy * q, st["seat_z"] + 0.5)
    feet = [p for p in SL.boxes(st) if p[0] == "feet"][0]
    foot_z, _ = down((feet[1] + feet[3]) / 2, (feet[2] + feet[4]) / 2, feet[5] + 0.4)
    head = [p for p in SL.boxes(st) if p[0] == "head"][0]
    c_z, _ = up((head[1] + head[3]) / 2, (head[2] + head[4]) / 2, head[6] + 0.02)
    seat_rows.append(
        {
            "id": st["id"],
            "posture": st["posture"],
            "seat_z": seat_z,
            "seat_planned": st["seat_z"],
            "seat_object": seat_ob,
            "foot_z": foot_z,
            "foot_planned": st["foot_z"],
            "head_top_to_ceiling": round(c_z - head[6], 3),
        }
    )

# ---- cold pools ----------------------------------------------------------------------------------------------------
pool_rows = {}
for pid in ("deep", "seated"):
    pl = WL.pool(pid)
    x0, y0, x1, y1 = pl["rect"]
    wv = verts(f"Pool_{pid}_water")
    lv = verts(f"Pool_{pid}_lining")
    zx0, zy0, zx1, zy1 = pl["zone"]
    fz = down((zx0 + zx1) / 2, (zy0 + zy1) / 2, 0.5)[0]
    treads = [round(down((t[0] + t[2]) / 2, (t[1] + t[3]) / 2, 0.5)[0], 4) for t in pl["treads"]]
    sf = pl["step_foot"]
    pool_rows[pid] = {
        "basin_inner_x": [round(min(v.x for v in lv), 4), round(max(v.x for v in lv), 4)],
        "basin_inner_y": [round(min(v.y for v in lv), 4), round(max(v.y for v in lv), 4)],
        "planned_rect": [x0, y0, x1, y1],
        "water_surface_z_mean": round(
            sum(v.z for v in wv if v.z > -0.2) / max(1, sum(1 for v in wv if v.z > -0.2)), 4
        ),
        "planned_surface_z": -WL.WATER_DROP,
        "floor_z": fz,
        "planned_floor_z": pl["floor_z"],
        "tread_top_z": treads,
        "planned_tread_z": [round(t[4], 4) for t in pl["treads"]],
        "floor_below_last_tread_z": down((sf[0] + sf[2]) / 2, (sf[1] + sf[3]) / 2, 0.5)[0],
        "surface_m2": pl["surface_m2"],
        "tread_area_m2": pl["step_area_m2"],
        "free_floor_m2": pl["free_floor_m2"],
    }
    rec("pool", f"{pid} floor z", fz, pl["floor_z"])
    for k, (got, t) in enumerate(zip(treads, pl["treads"])):
        rec("pool", f"{pid} tread {k + 1} top z", got, t[4])
cop = verts("Pool_cold_coping")
rec("pool", "coping outer edge north y", max(v.y for v in cop), WL.COPING_N)
rec("pool", "coping outer edge east x", max(v.x for v in cop), WL.EAST_COPING[1])
rec("pool", "coping west end x (at the splash wall)", min(v.x for v in cop), WL.SCREEN["x1"])
rec("pool", "coping top z", down(13.0, WL.COPING_N - 0.12, 0.5)[0], 0.012)
rail = verts("Pool_cold_rails")
rec(
    "pool",
    "rails: lowest point z (deep rail foot on tread 3)",
    min(v.z for v in rail),
    WL.pool("deep")["treads"][2][4] - 0.005,
)
rec("pool", "rails: top z", max(v.z for v in rail), 0.90 + 0.019)
sc = WL.SCREEN
rec("pool", "splash wall top z (middle)", down((sc["x0"] + sc["x1"]) / 2, 7.6, 2.6)[0], sc["h"])
rec(
    "pool",
    "splash wall top z (0.02 from the walkway end)",
    down((sc["x0"] + sc["x1"]) / 2 - 0.03, sc["y1"] - 0.02, 2.6)[0],
    None,
)
rec("pool", "splash wall west face x", reach((9.6, 7.756, 1.6), (1, 0, 0), 0)[0], sc["x0"])
rec("pool", "splash wall east face x", reach((11.5, 7.6, 1.0), (-1, 0, 0), 0)[0], sc["x1"])
north_face = reach((13.0, 9.6, 1.5), (0, 1, 0), 1)[0]
n2 = reach((9.0, 9.6, 1.5), (0, 1, 0), 1)[0]
rec(
    "walk",
    "walkway: coping edge to north wall (x=11.5, between the dry door and the perch)",
    reach((11.6, 9.6, 1.5), (0, 1, 0), 1)[0] - max(v.y for v in cop),
    WL.clearances()["walkway_north_of_pools"],
)
toes = min(q[2] for st in BL.perch_seats() for q in ML.body_boxes(st) if q[0] == "feet")
rec(
    "walk",
    "walkway: coping edge to the toes of a seated person on the spare perch",
    toes - max(v.y for v in cop),
    WL.clearances().get("walkway_between_coping_and_perch_toes"),
)
rec(
    "walk",
    "east zone: coping edge to east wall face",
    reach((15.5, 7.45, 1.4), (1, 0, 0), 0)[0] - max(v.x for v in cop),
    WL.clearances()["east_zone_from_coping_to_east_wall"],
)

# ---- rest annex ----------------------------------------------------------------------------------------------------
a = WL.ANNEX
pan = verts("Annex_partition_panels")
ya = (a["row_s"] + a["row_n"]) / 2
west_scr = [v for v in pan if v.x < a["x0"] + 0.06 and v.z > 0.3]
rec(
    "annex",
    "aisle mouth between the foot-screen ends",
    min(v.y for v in west_scr if v.y > ya) - max(v.y for v in west_scr if v.y < ya),
    a["mouth"][1] - a["mouth"][0],
)
walk_scr = [v for v in pan if a["x0"] + 0.2 < v.x < a["x1"] - 0.3 and v.y > a["y1"] - 0.08]
rec("annex", "walkway screen top z", max(v.z for v in walk_scr), a["panel_h"])
rec(
    "walk",
    "walkway: annex screen to north wall",
    n2 - max(v.y for v in walk_scr),
    WL.clearances()["walkway_north_of_annex_screen"],
)
wface = reach((6.5, 8.45, 1.0), (-1, 0, 0), 0)[0]
rec(
    "walk",
    "rest-door path: west wall to the annex foot screen",
    min(v.x for v in west_scr) - wface,
    WL.clearances()["rest_door_path_width"],
)
ch = verts("Annex_chair_slats") + verts("Annex_chair_frames")
for tag, xa, xb in (
    ("west pair", a["foot_w"] + 0.3, a["foot_w"] + 1.5),
    ("east pair", a["foot_e"] + 0.3, a["foot_e"] + 1.5),
):
    vs = [v for v in ch if xa < v.x < xb]
    rec(
        "annex",
        f"aisle between the loungers ({tag})",
        min(v.y for v in vs if v.y > ya) - max(v.y for v in vs if v.y < ya),
        WL.clearances()["annex_aisle_between_loungers"],
    )
rec(
    "annex",
    "lounger mesh length (west row, x extent; profile 1.80 + slat edge)",
    max(v.x for v in ch if v.x < a["divider"][0]) - min(v.x for v in ch if v.x < a["divider"][0]),
    None,
)
rec("annex", "lounger head end to splash wall (mesh)", sc["x0"] - max(v.x for v in ch), None)
rec(
    "annex",
    "west lounger head end to the divider (mesh)",
    a["divider"][0] - max(v.x for v in ch if v.x < a["divider"][0]),
    None,
)
rec(
    "annex",
    "lounger foot end to its foot screen (mesh, west row)",
    min(v.x for v in ch) - (a["x0"] + a["screen_t"]),
    None,
)
rec("annex", "south wall face y (timber)", reach((8.0, 7.2, 1.7), (0, -1, 0), 1)[0], WL.YS_TIMBER)
fin = verts("Annex_partition_fins")
rec("annex", "fins above the walkway screen: top z", max(v.z for v in fin), 2.72)

# ---- bodies against the mesh ----------------------------------------------------------------------------------------
everybody = (
    [(st["id"], SL.boxes(st)) for st in SL.all_seats()]
    + [(t["id"], ML.standing_boxes(t)) for t in SL.all_standing()]
    + [(t["id"] + "_tall", ML.standing_boxes(t, tall=True)) for t in SL.all_standing()]
    + [(bid, bx) for bid, kind, label, bx in WL.bodies()]
)
cuts = []
for bid, boxes in everybody:
    for part, x0, y0, x1, y1, z0, z1 in boxes:
        c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
        for cx in (x0 + 0.01, x1 - 0.01):
            for cy in (y0 + 0.01, y1 - 0.01):
                for cz in (z0 + 0.01, z1 - 0.01):
                    v = Vector((cx, cy, cz)) - c
                    loc, name = ray(c, v, v.length)
                    if loc:
                        cuts.append(
                            {
                                "body": bid,
                                "part": part,
                                "object": name,
                                "at": [round(q, 3) for q in loc],
                            }
                        )
layer = []
for bid, bb in everybody:
    if bid.endswith("_tall"):
        continue
    want = [
        min(b[1] for b in bb),
        min(b[2] for b in bb),
        min(b[5] for b in bb),
        max(b[3] for b in bb),
        max(b[4] for b in bb),
        max(b[6] for b in bb),
    ]
    got = body_bbox.get(bid)
    layer.append(
        {
            "id": bid,
            "max_diff_mm": None
            if got is None
            else round(max(abs(p - q) for p, q in zip(got, want)) * 1000, 1),
        }
    )

# ---- products kept from v7 -------------------------------------------------------------------------------------------
zl = [p for o in bpy.data.objects if o.name.startswith("Main_ZL300_") for p in verts(o.name)]
zl_size = [round(max(p[k] for p in zl) - min(p[k] for p in zl), 4) for k in range(3)]
fmat = bpy.data.objects["Floor_wet"].data.materials[0]
mask = fmat.node_tree.nodes.get("Product_grout_mask_3mm")
mods = [n for n in fmat.node_tree.nodes if n.type == "MATH" and n.operation == "MODULO"]
products = {
    "ZL300_bbox_size_m": zl_size,
    "ZL300_public_size_m": [ZL300["width"], ZL300["depth"], ZL300["height"]],
    "ZL300_objects": len([o for o in bpy.data.objects if o.name.startswith("Main_ZL300_")]),
    "bath_floor_material": fmat.name,
    "bath_floor_joint_m": None if mask is None else round(2 * mask.inputs[1].default_value, 5),
    "bath_floor_module_m": [round(n.inputs[1].default_value, 4) for n in mods],
    "bath_floor_spec": FLOOR["code"],
    "dry_floor_material": bpy.data.objects["Floor_dry"].data.materials[0].name,
    "note": "v7の製品反映をそのまま保持。色・台数・メーカー離隔は未選定（docs/PRODUCT_SELECTION.md）。浴室の床は新しい浴槽の穴に合わせて面が切り直されている。",
}

dev = [r for r in rows if r["diff_mm"] is not None and abs(r["diff_mm"]) > 5.0]
dev += [
    {
        "what": f"seat {r['id']} height",
        "diff_mm": round((r["seat_z"] - r["seat_planned"]) * 1000, 1),
    }
    for r in seat_rows
    if r["seat_z"] is None or abs(r["seat_z"] - r["seat_planned"]) > 0.005
]
dev += [
    {
        "what": f"seat {r['id']} foot level",
        "diff_mm": round((r["foot_z"] - r["foot_planned"]) * 1000, 1),
    }
    for r in seat_rows
    if r["foot_z"] is None or abs(r["foot_z"] - r["foot_planned"]) > 0.005
]

sub = SL.checks()
wat = WL.checks()
out = {
    "version": "v8",
    "model": model.name,
    "input_sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
    "method": "scene.ray_cast and vertex extents on the evaluated mesh (check bodies and water volumes hidden); metres",
    "limits": (
        "成人の仮寸法（main_layout.BODY）による概念検討。人体は直方体の集まり。熱・蒸気の流れ、ストーブ機種とメーカー離隔、換気、"
        "浴槽の設備・水質・滑り、監視の見通し、構造、法適合、費用は未検証。席数・同時に入れる人数は定員ではない。"
    ),
    "sub_saunas": {
        "options_compared": SL.options(),
        "self": {
            k: sub["self"][k]
            for k in (
                "seats",
                "by_height",
                "dims",
                "access",
                "stove",
                "seats_reached_without_passing_anyone",
            )
        },
        "dry": {
            k: sub["dry"][k]
            for k in (
                "seats",
                "by_posture",
                "dims",
                "access",
                "tv_view",
                "seats_reached_without_passing_anyone",
            )
        },
        "shoulder_gap_between_neighbours": sub["shoulder_gap_between_neighbours"],
        "body_clashes": sub["body_clashes"],
        "standing": sub["standing"],
        "v7_reference": sub["v7_reference"],
        "seats_on_mesh": seat_rows,
        "heat_and_steam": "形から温度や蒸気の当たり方は主張しない。高さとストーブからの距離が席ごとに違う、という配置の事実だけを記録した。",
    },
    "cold_pools": {
        "options_compared": WL.options(),
        "areas": wat["areas"],
        "on_mesh": pool_rows,
        "in_water_positions": wat["in_water_positions"],
        "head_above_water": wat["head_above_water"],
        "body_clashes": wat["body_clashes"],
        "seated_bodies_on_steps": wat["seated_bodies_on_steps"],
        "nearest_other_body_m": wat["nearest_other_body_m"],
        "clearances": wat["clearances"],
        "rails": WL.RAILS,
        "demand": WL.demand(),
        "volume_note": "水量は水面×水深で、階段（とv7の腰掛け段）の体積を引いていない。",
    },
    "rest_annex": {
        "count": WL.rest_count(),
        "loungers": WL.loungers(),
        "routes": [{k: v for k, v in r.items() if k != "path"} for r in WL.routes()],
        "screens": [
            {"name": p[0], "x": [p[1], p[3]], "y": [p[2], p[4]], "h": p[5], "fins_above": p[6]}
            for p in WL.partitions()
        ],
    },
    "mesh_measurements": rows,
    "deviations_over_5mm": dev,
    "body_boxes_cut_by_mesh": cuts,
    "body_layer_vs_data": layer,
    "products_kept": products,
}

# ---- unchanged stages against the frozen v7 model (opened read-only, nothing saved) --------------------------------
base = root.parent / "fable-v7" / "model" / "sauna_a_v7.blend"
bpy.ops.wm.open_mainfile(filepath=str(base))
snap7 = snapshot()
cmp = {}
for c in KEEP + ("Service",):
    a7, a8 = snap7[c], snap8[c]
    cmp[c] = {
        "objects_v7": len(a7),
        "objects_v8": len(a8),
        "added": sorted(set(a8) - set(a7)),
        "removed": sorted(set(a7) - set(a8)),
        "shape_changed": sorted(n for n in a7.keys() & a8.keys() if a7[n][0] != a8[n][0]),
        "uv_or_variation_changed": sorted(
            n for n in a7.keys() & a8.keys() if a7[n][0] == a8[n][0] and a7[n][1] != a8[n][1]
        ),
    }
cams = {
    "changed": sorted(
        n
        for n in snap7["cameras"].keys() & snap8["cameras"].keys()
        if snap7["cameras"][n] != snap8["cameras"][n]
    ),
    "added": sorted(set(snap8["cameras"]) - set(snap7["cameras"])),
    "removed": sorted(set(snap7["cameras"]) - set(snap8["cameras"])),
}
lights = {
    "spots_v7": len(snap7["lights"]),
    "spots_v8": len(snap8["lights"]),
    "energy_changed": sorted(
        n
        for n in snap7["lights"].keys() & snap8["lights"].keys()
        if snap7["lights"][n][0] != snap8["lights"][n][0]
    ),
    "moved": sorted(
        n
        for n in snap7["lights"].keys() & snap8["lights"].keys()
        if snap7["lights"][n][1] != snap8["lights"][n][1]
    ),
    "removed": sorted(set(snap7["lights"]) - set(snap8["lights"])),
    "added": sorted(set(snap8["lights"]) - set(snap7["lights"])),
}
emit = {
    k: {
        "v7": [snap7["emitters"].get(k, [0, 0])[0], round(snap7["emitters"].get(k, [0, 0])[1], 4)],
        "v8": [snap8["emitters"].get(k, [0, 0])[0], round(snap8["emitters"].get(k, [0, 0])[1], 4)],
    }
    for k in sorted(set(snap7["emitters"]) | set(snap8["emitters"]))
}
out["unchanged_against_v7"] = {
    "baseline": str(base.name),
    "baseline_sha256": hashlib.sha256(base.read_bytes()).hexdigest(),
    "collections": cmp,
    "cameras": cams,
    "pool_spot_lights": lights,
    "emitters_count_and_area_m2": emit,
    "note": "Main・Rest・Doors・製品段階・裏方は形もUV（板ごとの色むら）もv7と同じであることを確認する。浴室とサブ2室は作り直したので比較しない。",
}
ver = root / "verification"
ver.mkdir(parents=True, exist_ok=True)
(ver / "v8_design_check.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
)
bad = {
    c: {
        k: v
        for k, v in r.items()
        if k in ("added", "removed", "shape_changed", "uv_or_variation_changed") and v
    }
    for c, r in cmp.items()
}
print(
    "V8_OK",
    json.dumps(
        {
            "measured": len(rows),
            "deviations_over_5mm": dev,
            "cuts": len(cuts),
            "cut_list": cuts[:25],
            "layer_max_diff_mm": max((r["max_diff_mm"] or 0) for r in layer),
            "missing_bodies": [r["id"] for r in layer if r["max_diff_mm"] is None],
            "unchanged_diffs": {c: v for c, v in bad.items() if v},
            "cameras": cams,
            "lights": lights,
            "emitters": emit,
            "products": products,
            "seat_head_clear_min": min(r["head_top_to_ceiling"] for r in seat_rows),
        },
        ensure_ascii=False,
    ),
)
if (
    dev
    or cuts
    or any(bad.values())
    or any(r["max_diff_mm"] is None or r["max_diff_mm"] > 1.0 for r in layer)
):
    raise SystemExit(
        "V8_CHECK_FAILED: deviations, body cuts, missing bodies or a changed v7 stage (see verification/v8_design_check.json)"
    )
