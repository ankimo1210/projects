"""Measure the main sauna and the spare perch seats on the built mesh (read-only; the model is not saved).

blender -b <model.blend> --python verify_main.py

Ray casts against the evaluated geometry (check bodies hidden) give seat / foot / step heights, bench fronts, aisle and
door widths, headroom and heater distances. Each value is compared with main_layout.py / bath_layout.py, which the check
figures read. The 20 assumed seated bodies and four standing ones (also at 1.85 m) are then tested against the mesh
(does any surface cut through a body box?) and against each other, and the body layer in the file is compared with the data.
A concept check with assumed adult sizes: no code compliance, heater-maker clearance, structure, ventilation / heat load,
slip or performer review.
"""

import hashlib
import json
import os
import sys

import bpy
from mathutils import Vector

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sauna import bath_layout as BL  # noqa: E402
from sauna import main_layout as ML

scene = bpy.context.scene
people = [c for c in bpy.data.collections if c.name.startswith("Check_people")]
body_bbox = {}
for c in people:
    for ob in c.objects:
        pts = [ob.matrix_world @ Vector(v) for v in ob.bound_box]
        body_bbox[ob.name[len("Body_") :]] = [min(p[i] for p in pts) for i in range(3)] + [
            max(p[i] for p in pts) for i in range(3)
        ]
    c.hide_viewport = True  # rays must not hit the check bodies
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


D = ML.dims()
hx, hy = ML.HEATER["c"]
rows = []  # (what, measured, planned, object)


def rec(what, *a):
    """rec(what, measured, planned[, object]) or rec(what, measured, object, planned) as returned by reach() / down()."""
    if len(a) == 2:
        measured, planned, name = a[0], a[1], ""
    elif isinstance(a[2], str):
        measured, planned, name = a
    else:
        measured, name, planned = a
    rows.append(
        {
            "what": what,
            "measured": measured,
            "planned": None if planned is None else round(planned, 4),
            "diff_mm": None
            if planned is None or measured is None
            else round((measured - planned) * 1000, 1),
            "object": name or "",
        }
    )


# room shell
rec("west wall face x", *reach((1.0, 12.0, 1.6), (-1, 0, 0), 0)[:1], ML.XW)
rec("east wall face x", *reach((5.0, 12.0, 1.6), (1, 0, 0), 0)[:1], ML.XE)
rec("north wall face y", *reach((3.0, 13.0, 1.6), (0, 1, 0), 1)[:1], ML.YN)
rec("south wall face y", *reach((3.0, 9.6, 1.6), (0, -1, 0), 1)[:1], ML.YS)
ceil_z, ceil_name = up(3.0, 9.6, 1.0)
rec("ceiling underside z", ceil_z, ML.H, ceil_name)
# bench fronts (ray at the board edge of each level)
rec("north upper front y", *reach((2.2, 12.9, ML.TOP_UP - 0.012), (0, 1, 0), 1), D["n_upper_front"])
rec(
    "north lower front y", *reach((2.2, 12.2, ML.TOP_LOW - 0.012), (0, 1, 0), 1), D["n_lower_front"]
)
for side, sg, xs in (("west", -1, 2.0), ("east", 1, 4.0)):
    k = side[0]
    rec(
        f"{side} upper front x",
        *reach((xs, 11.6, ML.TOP_UP - 0.012), (sg, 0, 0), 0),
        D[f"{k}_upper_front"],
    )
    rec(
        f"{side} foot bench front x",
        *reach((xs, 11.6, ML.TOP_LOW - 0.012), (sg, 0, 0), 0),
        D[f"{k}_foot_front"],
    )
    rec(
        f"{side} half step front x",
        *reach((xs, 11.6, ML.TOP_STEP - 0.012), (sg, 0, 0), 0),
        D[f"{k}_step_front"],
    )
    rec(
        f"{side} bench south end y",
        *reach((D[f"{k}_upper_front"] + sg * 0.3, 10.0, ML.TOP_UP - 0.012), (0, 1, 0), 1),
        ML.Y_END,
    )
    xm = (D[f"{k}_step_front"] + D[f"{k}_foot_front"]) / 2
    xf = (D[f"{k}_foot_front"] + D[f"{k}_upper_front"]) / 2
    xu = D[f"{k}_upper_front"] + sg * 0.3
    rec(f"{side} half step top z", *down(xm, 11.6, 0.6), ML.TOP_STEP)
    rec(f"{side} foot bench top z", *down(xf, 11.6, 0.8), ML.TOP_LOW)
    rec(f"{side} seat top z", *down(xu, 11.6, 1.1), ML.TOP_UP)
    # guard rail (mid rail at 0.41 m) as seen from the half step
    g, gname = reach(
        (D[f"{k}_step_front"] - sg * 0.02, hy, ML.HEATER["guard_h"] * 0.5), (-sg, 0, 0), 0
    )
    rec(
        f"{side} aisle: half step to guard rail",
        round(abs(D[f"{k}_step_front"] - g), 4),
        D[f"aisle_{side}"],
        gname,
    )
g, gname = reach((hx, D["n_lower_front"] - 0.02, ML.HEATER["guard_h"] * 0.5), (0, -1, 0), 1)
rec(
    "north aisle: front row nose to guard rail",
    round(D["n_lower_front"] - g, 4),
    D["aisle_north"],
    gname,
)
g, gname = reach((hx, ML.YS + 0.05, ML.HEATER["guard_h"] * 0.5), (0, 1, 0), 1)
rec("south floor: south wall to guard rail", round(g - ML.YS, 4), D["floor_south"], gname)
rec("guard rail top z", *down(hx + D["guard_apothem"] - 0.021, hy, 1.6), ML.HEATER["guard_h"])
stone_z, stone_name = down(hx, hy, 2.0)
rec("stone heap top z (centre)", stone_z, None, stone_name)
# door: clear width between the jambs, bench end to the jamb
ja = ray((5.885, 9.75, 1.0), (0, -1, 0))[
    0
].y  # single rays inside the frame depth, clear of the leaf and its handle
jb = ray((5.885, 9.75, 1.0), (0, 1, 0))[0].y
rec("door clear width between jambs", round(jb - ja, 4), None)
rec(
    "east bench end to door opening (north jamb line)",
    round(reach((5.6, 10.0, ML.TOP_UP - 0.012), (0, 1, 0), 1)[0] - ML.DOOR[1], 4),
    D["bench_end_to_door_jamb"],
)
# north landings, corner squares, diagonal treads
nl = [s for s in ML.seats() if s["id"].startswith("NL")]
for name, x in (
    ("north-west landing", (D["w_foot_front"] + nl[0]["b"][0] - nl[0]["pitch"] / 2) / 2),
    ("north-east landing", (D["e_foot_front"] + nl[-1]["b"][0] + nl[-1]["pitch"] / 2) / 2),
):
    rec(f"{name} top z", *down(x, D["n_lower_front"] + 0.25, 0.8), ML.TOP_LOW)
for name, tri in zip(("west", "east"), ML.diag_treads()):
    cx, cy = sum(p[0] for p in tri) / 3, sum(p[1] for p in tri) / 3
    rec(f"{name} diagonal turning tread top z", *down(cx, cy, 0.6), ML.TOP_STEP)

# every seat: seat height, foot level, ceiling above the head
seat_rows = []
for s in ML.seats():
    bx, by = s["b"]
    fx, fy = s["f"]
    sx, sy = (bx, by) if s["posture"] == "feet_up" else (bx + fx * 0.25, by + fy * 0.25)
    seat_z, seat_ob = down(sx, sy, s["seat_z"] + 0.5)
    feet = [p for p in ML.body_boxes(s) if p[0] == "feet"]
    foot_z = None
    if feet:
        _, x0, y0, x1, y1, z0, z1 = feet[0]
        foot_z, _ = down((x0 + x1) / 2, (y0 + y1) / 2, z0 + 0.4)
    head = [p for p in ML.body_boxes(s) if p[0] == "head"][0]
    c_z, _ = up((head[1] + head[3]) / 2, (head[2] + head[4]) / 2, s["seat_z"] + 0.1)
    seat_rows.append(
        {
            "id": s["id"],
            "seat_z": seat_z,
            "seat_planned": s["seat_z"],
            "seat_object": seat_ob,
            "foot_z": foot_z,
            "foot_planned": s["foot_z"],
            "seat_to_ceiling": round(c_z - seat_z, 3),
            "head_to_ceiling": round(c_z - seat_z - ML.BODY["sit_h"], 3),
            "head_to_ceiling_tall": round(c_z - seat_z - ML.BODY["sit_h_tall"], 3),
        }
    )

# bodies against the mesh: from the centre of each body box to its 8 corners (10 mm inside); a hit = a surface inside the box
cuts = []
everybody = (
    [(s, ML.body_boxes(s)) for s in ML.seats()]
    + [(t, ML.standing_boxes(t)) for t in ML.standing()]
    + [({"id": t["id"] + "_tall"}, ML.standing_boxes(t, tall=True)) for t in ML.standing()]
)
for s, boxes in everybody:
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
                                "seat": s["id"],
                                "part": part,
                                "object": name,
                                "at": [round(q, 3) for q in loc],
                            }
                        )
# body layer in the file == data
layer = []
for s, bb in everybody[: len(ML.seats()) + len(ML.standing())]:
    want = [
        min(b[1] for b in bb),
        min(b[2] for b in bb),
        min(b[5] for b in bb),
        max(b[3] for b in bb),
        max(b[4] for b in bb),
        max(b[6] for b in bb),
    ]
    got = body_bbox.get(s["id"])
    layer.append(
        {
            "id": s["id"],
            "max_diff_mm": None
            if got is None
            else round(max(abs(a - b) for a, b in zip(got, want)) * 1000, 1),
        }
    )

# spare perch seats in the bath
P = BL.PERCH
perch = []
for s in BL.perch_seats():
    x = s["b"][0]
    top, top_ob = down(x, P["y_front"] + 0.18, 1.0)
    nose, _ = reach((x, 9.8, P["seat_top"] - 0.03), (0, 1, 0), 1)
    cop = round(
        ray((x, 9.8, 0.006), (0, -1, 0))[0].y, 4
    )  # single ray 6 mm above the deck: the raised coping edge
    backf, _ = reach((x, P["y_front"] + 0.1, 0.8), (0, 1, 0), 1)
    toes = [q for q in ML.body_boxes(s) if q[0] == "feet"][0][2]
    perch.append(
        {
            "id": s["id"],
            "seat_top_z": top,
            "object": top_ob,
            "seat_nose_y": nose,
            "coping_edge_y": cop,
            "back_pad_face_y": backf,
            "walkway_empty": round(nose - cop, 3),
            "walkway_with_legs": round(toes - cop, 3),
            "seat_depth": round(backf - nose, 3),
        }
    )
wing_w, _ = reach((P["x0"] + 0.5, P["y_front"] + 0.2, 1.0), (-1, 0, 0), 0)
wing_e, _ = reach((P["x1"] - 0.5, P["y_front"] + 0.2, 1.0), (1, 0, 0), 0)

dev = [r for r in rows if r["diff_mm"] is not None and abs(r["diff_mm"]) > 5.0]
dev += [
    {
        "what": f"seat {r['id']} height",
        "diff_mm": round((r["seat_z"] - r["seat_planned"]) * 1000, 1),
    }
    for r in seat_rows
    if abs(r["seat_z"] - r["seat_planned"]) > 0.005
]
dev += [
    {
        "what": f"seat {r['id']} foot level",
        "diff_mm": round((r["foot_z"] - r["foot_planned"]) * 1000, 1),
    }
    for r in seat_rows
    if r["foot_z"] is not None and abs(r["foot_z"] - r["foot_planned"]) > 0.005
]
chk = ML.checks()
out = {
    "model": os.path.basename(bpy.data.filepath),
    "method": "scene.ray_cast on the evaluated mesh with the check bodies hidden; values in metres",
    "limits": (
        "成人の仮寸法による概念検討。法適合、ストーブ機種と離隔、構造、換気・熱負荷、滑り、演者の確認は別途。"
        "人体は直方体の集まりで、姿勢の崩れ・体格差・立ち上がる動作は扱わない。"
    ),
    "main_measurements": rows,
    "seats": seat_rows,
    "deviations_over_5mm": dev,
    "body_boxes_cut_by_mesh": cuts,
    "body_layer_vs_data": layer,
    "body_clashes": chk["body_clashes"],
    "feet_on_another_seat": chk["feet_on_another_seat"],
    "feet_on_step_or_landing": chk["feet_on_step_or_landing"],
    "zone_overlaps": chk["zone_overlaps"],
    "seat_count": {k: chk[k] for k in ("seats", "legs_down", "feet_up_corner", "by_row")},
    "standing_bodies": chk["standing"],
    "north_landing_size": chk["north_landing_size"],
    "seats_needing_cooperation": chk["seats_needing_cooperation"],
    "perch": {
        "seats": perch,
        "clear_between_wings": round(wing_e - wing_w, 3),
        "planned": BL.clearances(),
    },
}
with open(bpy.data.filepath, "rb") as fh:
    out["input_sha256"] = hashlib.file_digest(fh, "sha256").hexdigest()
ver = os.path.join(os.path.dirname(os.path.dirname(bpy.data.filepath)), "verification")
os.makedirs(ver, exist_ok=True)
with open(os.path.join(ver, "main_mesh_check.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print(
    "MAIN_OK",
    json.dumps(
        {
            "measured": len(rows),
            "deviations_over_5mm": dev,
            "seats": chk["seats"],
            "body_cut_by_mesh": len(cuts),
            "cut_list": cuts[:12],
            "body_clashes": len(chk["body_clashes"]),
            "layer_max_diff_mm": max((r["max_diff_mm"] or 0) for r in layer),
            "missing_bodies": [r["id"] for r in layer if r["max_diff_mm"] is None],
            "headroom_min": min(r["head_to_ceiling"] for r in seat_rows),
            "perch": perch[:1],
            "aisles": {
                r["what"]: r["measured"]
                for r in rows
                if "aisle" in r["what"] or "south floor" in r["what"] or "door" in r["what"]
            },
        },
        ensure_ascii=False,
    ),
)
