"""v8 small saunas as plain data (no bpy): the self-loyly room and the dry room with the TV.

Shared by room_sub.py (model), blender/verify_v8.py (mesh check) and scripts/v8_diagram.py (figure).
Metres, x east, y north, z up. Body sizes are the assumed adult study values of main_layout.BODY.

Self-loyly: one row of seats that climbs round the room in three heights (0.45 west, 0.675 north-west, 0.90 north-east),
each height with its own foot level 0.45 m below, and a rounded timber corner. People choose how high and how near the
stove they sit. Dry room: two postures facing the glazed TV in the east wall — a high bench for two and a low deck for two
where the legs lie out flat against a raked back.

Heater type, output, maker clearances, how heat and steam actually move, ventilation, structure and code compliance are not
selected or verified; nothing here claims a temperature or steam effect from the shape.
"""

import math

from . import main_layout as ML

B = ML.BODY
H = 2.4  # ceiling of both rooms: v8 raises it from 2.30 (provisional; see ceiling_options())
H_V7 = 2.3
Y0, Y1 = 10.612, 13.888  # finished south / north faces of both rooms
SEAT_D = 0.60

# ---- self-loyly room (plan rect 6..9.5 x 10.5..14) --------------------------------------------------------------
SELF = {
    "xw": 6.112,
    "xe": 9.388,
    "door": (7.1, 8.1),
    "heater": {
        "c": (8.78, 11.25),
        "r": 0.30,
        "guard_r": 0.57,
    },  # same heater, guard and position as v7
    "levels": (0.45, 0.675, 0.90),
    "w_end": Y0 + 0.80,
    "w_top": Y0 + 2.10,  # west run (0.45): y range of the two seats
    "n_split": 8.05,  # north run: 0.675 west of this x, 0.90 east of it
    "ledge_d": 0.38,
    "step_d": 0.28,
    "corner_r": 0.90,  # plan radius of the rounded timber lining in the north-west corner
    "bucket": (9.22, 11.93),
    "ladle": (-0.25, 0.06),  # in the corner between the guard and the east wall, out of the aisle
}
# ---- dry room with the TV (plan rect 9.5..12.5 x 10.5..14) -------------------------------------------------------
DRY = {
    "xw": 9.612,
    "xe": 12.388,
    "door": (10.2, 11.2),
    "heater": {
        "c": (11.90, 11.10),
        "r": 0.24,
        "guard_r": 0.50,
    },  # same heater, guard and position as v7
    "tv": {"x": 12.388, "c": (12.75, 1.495), "picture": (0.94, 0.529)},  # east wall, unchanged
    "u_y": (Y0 + 0.83, Y0 + 2.03),
    "u_top": 0.90,
    "u_foot_d": 0.42,  # high bench for two: y range, seat height, foot deck depth
    "split": Y0
    + 2.06,  # the low deck starts here; a 30 mm timber wing stands between the two postures
    "wing": {"y": (Y0 + 2.03, Y0 + 2.06), "top": 1.30, "ease": (0.25, 0.25)},
    "deck_y0": Y0 + 0.94,  # south edge of the foot deck (keeps the 0.94 m door landing of v7)
    "deck_top": 0.45,
    "d_depth": 1.50,  # low deck for two: depth from the west wall
    "back": {
        "base": 0.30,
        "top_in": 0.06,
        "h": 0.72,
    },  # raked back on the deck: 0.30 out at the deck, 0.06 at the top, 0.72 high
    "step_d": 0.28,
    "step_top": 0.225,
    "diag": 0.48,
}


def self_dims():
    s = SELF
    yn_front = Y1 - SEAT_D
    ledge_front = yn_front - s["ledge_d"]
    step_front = ledge_front - s["step_d"]
    hx, hy = s["heater"]["c"]
    ap = s["heater"]["guard_r"] * math.cos(math.pi / 8) + ML.GUARD_RAIL_T / 2
    return {
        "room_inner": (round(s["xe"] - s["xw"], 3), round(Y1 - Y0, 3)),
        "ceiling": H,
        "w_front": s["xw"] + SEAT_D,
        "n_front": yn_front,
        "ledge_front": ledge_front,
        "step_front": step_front,
        "guard_apothem": round(ap, 3),
        "aisle_step_to_guard": round(step_front - (hy + ap), 3),
        "floor_w_bench_to_guard": round((hx - ap) - (s["xw"] + SEAT_D), 3),
        "w_bench_end_to_door_jamb": round(s["door"][0] - (s["xw"] + SEAT_D), 3),
        "w_bench_end_from_south_wall": round(s["w_end"] - Y0, 3),
        "guard_to_door_jamb": round((hx - ap) - s["door"][1], 3),
        "headroom_top_seat": round(H - s["levels"][2], 3),
        "head_clear_top_seat": round(H - s["levels"][2] - B["sit_h"], 3),
        "head_clear_top_seat_tall": round(H - s["levels"][2] - B["sit_h_tall"], 3),
        "standing_on_0.45_ledge": round(H - 0.45, 3),
        "standing_on_0.225_ledge": round(H - 0.225, 3),
    }


def self_seats():
    s = SELF
    g = B["back_gap"]
    out = []

    def add(sid, b, f, seat_z, pitch):
        out.append(
            {
                "id": sid,
                "tier": "self",
                "b": (round(b[0], 4), round(b[1], 4)),
                "f": f,
                "pitch": round(pitch, 4),
                "seat_z": seat_z,
                "foot_z": round(seat_z - 0.45, 3),
                "posture": "legs_down",
                "backrest": True,
            }
        )

    pw = (s["w_top"] - s["w_end"]) / 2
    for k in range(2):
        add(f"SW{k + 1}", (s["xw"] + g, s["w_end"] + (k + 0.5) * pw), (1, 0), s["levels"][0], pw)
    x0 = s["xw"] + SEAT_D
    pn = (s["xe"] - x0) / 4
    for k in range(4):
        add(
            f"SN{k + 1}",
            (x0 + (k + 0.5) * pn, Y1 - g),
            (0, -1),
            s["levels"][1] if k < 2 else s["levels"][2],
            pn,
        )
    return out


def self_levels():
    """Plan rectangles by use and height: (kind, label, x0, y0, x1, y1, z)."""
    s = SELF
    d = self_dims()
    xs = s["n_split"]
    return [
        ("seat", "西 0.45（2席）", s["xw"], s["w_end"], d["w_front"], s["w_top"], 0.45),
        (
            "corner",
            "丸い入隅の台 0.675（席に数えない）",
            s["xw"],
            s["w_top"],
            d["w_front"],
            Y1,
            0.675,
        ),
        ("seat", "北西 0.675（2席）", d["w_front"], d["n_front"], xs, Y1, 0.675),
        ("seat", "北東 0.90（2席）", xs, d["n_front"], s["xe"], Y1, 0.90),
        ("foot", "足置き 0.225", d["w_front"], d["ledge_front"], xs, d["n_front"], 0.225),
        ("foot", "足置き 0.45", xs, d["ledge_front"], s["xe"], d["n_front"], 0.45),
        ("step", "中間段 0.225", xs, d["step_front"], s["xe"], d["ledge_front"], 0.225),
    ]


def self_access():
    return {
        "SW1": {"route": "床からそのまま座る", "rises": [], "pass": 0},
        "SW2": {"route": "床からそのまま座る", "rises": [], "pass": 0},
        "SN1": {"route": "床 → 目の前の足置き0.225 → 座る", "rises": [0.225], "pass": 0},
        "SN2": {"route": "床 → 目の前の足置き0.225 → 座る", "rises": [0.225], "pass": 0},
        "SN3": {
            "route": "床 → 中間段0.225 → 足置き0.45 → 座る",
            "rises": [0.225, 0.225],
            "pass": 0,
        },
        "SN4": {
            "route": "床 → 中間段0.225 → 足置き0.45 → 座る",
            "rises": [0.225, 0.225],
            "pass": 0,
        },
    }


def self_stove_distance():
    """Plan distance from each seated head to the heater centre and the seat height: what differs between the seats."""
    hx, hy = SELF["heater"]["c"]
    out = {}
    for s in self_seats():
        head = [p for p in ML.body_boxes(s) if p[0] == "head"][0]
        cx, cy = (head[1] + head[3]) / 2, (head[2] + head[4]) / 2
        out[s["id"]] = {
            "seat_z": s["seat_z"],
            "head_z": round(s["seat_z"] + B["sit_h"], 2),
            "plan_distance_to_stove_centre": round(math.hypot(cx - hx, cy - hy), 2),
        }
    return out


def self_standing():
    d = self_dims()
    s = SELF
    xm = (s["n_split"] + s["xe"]) / 2
    return [
        {
            "id": "ST1",
            "label": "セルフ：中間段0.225に立つ（SN3の前）",
            "c": (xm - 0.33, (d["step_front"] + d["ledge_front"]) / 2),
            "z": 0.225,
            "wide": "x",
        },
        {
            "id": "ST2",
            "label": "セルフ：ストーブの前で水をかける",
            "c": (8.05, 12.05),
            "z": 0.0,
            "wide": "x",
        },
    ]


# ---- dry room ----------------------------------------------------------------------------------------------------
def dry_dims():
    d = DRY
    xu = d["xw"] + SEAT_D  # nose of the high bench
    xf = xu + d["u_foot_d"]  # front of its foot deck
    xs = xf + d["step_d"]  # front of the half step in front of it
    xd = d["xw"] + d["d_depth"]  # front of the low deck
    xds = xd + d["step_d"]
    hx, hy = d["heater"]["c"]
    ap = d["heater"]["guard_r"] * math.cos(math.pi / 8) + ML.GUARD_RAIL_T / 2
    return {
        "room_inner": (round(d["xe"] - d["xw"], 3), round(Y1 - Y0, 3)),
        "ceiling": H,
        "u_nose": xu,
        "u_foot_front": xf,
        "u_step_front": xs,
        "d_front": xd,
        "d_step_front": xds,
        "zone_split_y": d["split"],
        "guard_apothem": round(ap, 3),
        "door_landing_depth": round(d["deck_y0"] - Y0, 3),
        "aisle_east_of_u_step": round(d["xe"] - xs, 3),
        "aisle_east_of_d_step": round(d["xe"] - xds, 3),
        "u_step_corner_to_guard": round(
            math.hypot((hx - ap) - xs, max(0.0, d["deck_y0"] - (hy + ap * math.tan(math.pi / 8)))),
            3,
        ),
        "headroom_high_seat": round(H - d["u_top"], 3),
        "head_clear_high_seat": round(H - d["u_top"] - B["sit_h"], 3),
        "head_clear_high_seat_tall": round(H - d["u_top"] - B["sit_h_tall"], 3),
        "standing_on_deck": round(H - d["deck_top"], 3),
        "back_rake_deg": round(
            math.degrees(math.atan2(d["back"]["base"] - d["back"]["top_in"], d["back"]["h"])), 1
        ),
    }


def dry_seats():
    d = DRY
    g = B["back_gap"]
    pu = (d["u_y"][1] - d["u_y"][0]) / 2
    out = [
        {
            "id": f"DU{k + 1}",
            "tier": "dry_high",
            "b": (round(d["xw"] + g, 4), round(d["u_y"][0] + (k + 0.5) * pu, 4)),
            "f": (1, 0),
            "pitch": round(pu, 4),
            "seat_z": d["u_top"],
            "foot_z": d["deck_top"],
            "posture": "legs_down",
            "backrest": True,
        }
        for k in range(2)
    ]
    pd = (Y1 - d["split"]) / 2
    out += [
        {
            "id": f"DD{k + 1}",
            "tier": "dry_deck",
            "b": (round(d["xw"] + d["back"]["base"], 4), round(d["split"] + (k + 0.5) * pd, 4)),
            "f": (1, 0),
            "pitch": round(pd, 4),
            "seat_z": d["deck_top"],
            "foot_z": d["deck_top"],
            "posture": "legs_out",
            "backrest": True,
        }
        for k in range(2)
    ]
    return out


def leg_stretch_boxes(s):
    """Sitting on the deck against the raked back with the legs lying out towards the TV (stepped boxes follow the rake)."""
    x, y = s["b"]  # foot of the raked back on the deck
    z = s["seat_z"]
    hw = B["shoulder"] / 2
    return [
        ("hips", x + 0.02, y - hw, x + 0.27, y + hw, z, z + 0.30),
        ("torso", x - 0.08, y - hw, x + 0.17, y + hw, z + 0.30, z + B["shoulder_h"] - 0.03),
        (
            "head",
            x - 0.16,
            y - 0.09,
            x + 0.04,
            y + 0.09,
            z + B["shoulder_h"] - 0.03,
            z + B["sit_h"] - 0.07,
        ),
        (
            "legs",
            x + 0.27,
            y - B["thigh_w"] / 2,
            x + 1.07,
            y + B["thigh_w"] / 2,
            z,
            z + B["thigh_t"],
        ),
        ("feet", x + 1.07, y - B["feet_w"] / 2, x + 1.15, y + B["feet_w"] / 2, z, z + 0.26),
    ]


def boxes(s):
    return leg_stretch_boxes(s) if s["posture"] == "legs_out" else ML.body_boxes(s)


def eye(s):
    if s["posture"] == "legs_out":
        return (s["b"][0] - 0.02, s["b"][1], s["seat_z"] + B["sit_h"] - 0.19)
    return (
        s["b"][0] + s["f"][0] * 0.13,
        s["b"][1] + s["f"][1] * 0.13,
        s["seat_z"] + B["sit_h"] - 0.12,
    )


def dry_tv_view():
    """Distance and angles from each eye to the centre of the picture, and whether another seated body is on the line."""
    tv = DRY["tv"]
    tx, (ty, tz) = tv["x"], tv["c"]
    seats = dry_seats()
    out = {}
    for s in seats:
        ex, ey, ez = eye(s)
        dx, dy, dz = tx - ex, ty - ey, tz - ez
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        blocked = []
        for o in seats:
            if o["id"] == s["id"]:
                continue
            for part, x0, y0, x1, y1, z0, z1 in boxes(o):
                for k in range(1, 40):
                    t = k / 40
                    px, py, pz = ex + dx * t, ey + dy * t, ez + dz * t
                    if x0 <= px <= x1 and y0 <= py <= y1 and z0 <= pz <= z1:
                        blocked.append(o["id"])
                        break
        out[s["id"]] = {
            "eye": [round(ex, 2), round(ey, 2), round(ez, 2)],
            "distance_m": round(dist, 2),
            "turn_from_straight_ahead_deg": round(math.degrees(math.atan2(abs(dy), dx)), 1),
            "look_up_deg": round(math.degrees(math.atan2(dz, math.hypot(dx, dy))), 1),
            "picture_width_deg": round(math.degrees(2 * math.atan2(tv["picture"][0] / 2, dist)), 1),
            "blocked_by": sorted(set(blocked)),
        }
    return out


def dry_levels():
    d = DRY
    m = dry_dims()
    ys = d["split"]
    return [
        ("seat", "高い腰掛け 0.90（2席）", d["xw"], d["u_y"][0], m["u_nose"], d["u_y"][1], 0.90),
        ("foot", "足置き 0.45", m["u_nose"], d["deck_y0"], m["u_foot_front"], ys, 0.45),
        ("step", "中間段 0.225", m["u_foot_front"], d["deck_y0"], m["u_step_front"], ys, 0.225),
        ("deck", "脚を伸ばす寝座 0.45（2席）", d["xw"], ys, m["d_front"], Y1, 0.45),
        ("step", "中間段 0.225", m["d_front"], ys, m["d_step_front"], Y1, 0.225),
    ]


def dry_diag():
    """Diagonal tread at 0.225 joining the two half steps where the fronts jog (plan triangle)."""
    m = dry_dims()
    ys = DRY["split"]
    return [(m["u_step_front"], ys - DRY["diag"]), (m["d_step_front"], ys), (m["u_step_front"], ys)]


def dry_access():
    return {
        "DU1": {
            "route": "床 → 目の前の中間段0.225 → 足置き0.45 → 座る",
            "rises": [0.225, 0.225],
            "pass": 0,
        },
        "DU2": {
            "route": "床 → 目の前の中間段0.225 → 足置き0.45 → 座る",
            "rises": [0.225, 0.225],
            "pass": 0,
        },
        "DD1": {
            "route": "床 → 目の前の中間段0.225 → 寝座0.45へ上がり、背にもたれて脚を伸ばす",
            "rises": [0.225, 0.225],
            "pass": 0,
        },
        "DD2": {
            "route": "床 → 目の前の中間段0.225 → 寝座0.45へ上がり、背にもたれて脚を伸ばす",
            "rises": [0.225, 0.225],
            "pass": 0,
        },
    }


def dry_standing():
    m = dry_dims()
    d = DRY
    return [
        {
            "id": "DT1",
            "label": "ドライ：中間段0.225に立つ（DU2の前）",
            "c": ((m["u_foot_front"] + m["u_step_front"]) / 2, d["u_y"][1] - 0.30),
            "z": 0.225,
            "wide": "y",
        },
        {
            "id": "DT2",
            "label": "ドライ：TVの壁の前を通る",
            "c": ((m["d_step_front"] + d["xe"]) / 2, 13.0),
            "z": 0.0,
            "wide": "x",
        },
    ]


# ---- checks, options ---------------------------------------------------------------------------------------------
def _overlap(a, b, eps=1e-6):
    return (
        min(a[3], b[3]) - max(a[1], b[1]) > eps
        and min(a[4], b[4]) - max(a[2], b[2]) > eps
        and min(a[6], b[6]) - max(a[5], b[5]) > eps
    )


def all_seats():
    return self_seats() + dry_seats()


def all_standing():
    return self_standing() + dry_standing()


def checks():
    seats = all_seats()
    body = {s["id"]: boxes(s) for s in seats}
    ids = [s["id"] for s in seats]
    clashes = [
        [a, pa[0], b, pb[0]]
        for i, a in enumerate(ids)
        for b in ids[i + 1 :]
        for pa in body[a]
        for pb in body[b]
        if _overlap(pa, pb)
    ]
    stand = []
    for t in all_standing():
        tb = ML.standing_boxes(t)
        hit = sorted(
            {f"{sid}:{pb[0]}" for sid in ids for pb in body[sid] for pa in tb if _overlap(pa, pb)}
        )
        gaps = [
            max(max(tb[0][1] - pb[3], pb[1] - tb[0][3]), max(tb[0][2] - pb[4], pb[2] - tb[0][4]))
            for sid in ids
            for pb in body[sid]
            if min(tb[0][6], pb[6]) - max(tb[0][5], pb[5]) > 0
        ]
        stand.append(
            {
                "id": t["id"],
                "label": t["label"],
                "at": [round(v, 3) for v in t["c"]],
                "level": t["z"],
                "head_to_ceiling": round(H - t["z"] - B["stature"], 3),
                "head_to_ceiling_tall": round(H - t["z"] - B["stature_tall"], 3),
                "overlaps_seated_body": hit,
                "nearest_seated_body_m": round(min(gaps), 3) if gaps else None,
            }
        )
    gap = {}
    for grp in ("SW", "SN", "DU", "DD"):
        row = [s for s in seats if s["id"].startswith(grp)]
        gap[grp] = round(row[0]["pitch"] - B["shoulder"], 3)
    return {
        "self": {
            "seats": len(self_seats()),
            "by_height": {"0.45": 2, "0.675": 2, "0.90": 2},
            "dims": self_dims(),
            "access": self_access(),
            "stove": self_stove_distance(),
            "seats_reached_without_passing_anyone": sum(
                1 for a in self_access().values() if a["pass"] == 0
            ),
        },
        "dry": {
            "seats": len(dry_seats()),
            "by_posture": {"高い腰掛け（脚を下ろす）": 2, "寝座（脚を伸ばす）": 2},
            "dims": dry_dims(),
            "access": dry_access(),
            "tv_view": dry_tv_view(),
            "seats_reached_without_passing_anyone": sum(
                1 for a in dry_access().values() if a["pass"] == 0
            ),
        },
        "shoulder_gap_between_neighbours": gap,
        "body_clashes": clashes,
        "standing": stand,
        "v7_reference": {
            "self": "北壁に2段（0.90／0.45）×長さ3.28 m。人体を置いた席数の確認は無し（幅0.6 mで割ると上5・下5）",
            "dry": "西壁に2段（0.90／0.45）×長さ2.34 m。同じく上3・下3の割り算だけ",
        },
    }


def ceiling_options():
    """Headroom when a 1.85 m person stands on the 0.45 m foot level / deck (the way to the high seats and onto the deck)."""
    vol = lambda h: {
        "self_m3": round((SELF["xe"] - SELF["xw"]) * (Y1 - Y0) * h, 1),
        "dry_m3": round((DRY["xe"] - DRY["xw"]) * (Y1 - Y0) * h, 1),
    }  # noqa: E731
    return [
        {
            "name": "A: 天井2.30のまま（v7）",
            "adopted": False,
            "standing_on_0.45": round(H_V7 - 0.45, 2),
            "head_1.72": round(H_V7 - 0.45 - 1.72, 2),
            "head_1.85": round(H_V7 - 0.45 - 1.85, 2),
            "air_volume_wall_to_wall": vol(H_V7),
            "why_not": "0.45の段に立つと身長1.85 mの人は頭が天井に触れる。上がるたびに屈む出入りになる。",
        },
        {
            "name": "B: 天井2.30のまま座面と足置きを0.10下げる（席0.80／足置き0.35）",
            "adopted": False,
            "standing_on_0.35": round(H_V7 - 0.35, 2),
            "head_1.85": round(H_V7 - 0.35 - 1.85, 2),
            "why_not": "頭上は0.10 m取れるが、いちばん高い席が0.80になり、セルフの3つの高さの差（0.225ずつ）が0.175へ縮む。ドライの寝座も0.35で、TVの見上げが増える。",
        },
        {
            "name": "C: 天井を2.40へ（採用）",
            "adopted": True,
            "standing_on_0.45": round(H - 0.45, 2),
            "head_1.72": round(H - 0.45 - 1.72, 2),
            "head_1.85": round(H - 0.45 - 1.85, 2),
            "air_volume_wall_to_wall": vol(H),
            "why": "席の高さを変えずに、0.45の段に立つ身長1.85 mの人の頭上に0.10 mが残る。メインサウナと同じ天井高。構造階高3.0 mの内側。",
            "cost": "室の気積が約4%増える（壁から壁×天井高の単純計算。ベンチ等は引いていない）。ストーブの能力・換気・物件の階高との整合は未検証。",
        },
    ]


def options():
    s, d = self_dims(), dry_dims()
    ring = SELF["heater"]["guard_r"] + 0.75 + SEAT_D
    return {
        "ceiling": ceiling_options(),
        "self": [
            {
                "name": "A: 高さが3つに上がっていく一列＋丸い入隅（採用）",
                "adopted": True,
                "seats": 6,
                "why": (
                    "席ごとに高さ（0.45／0.675／0.90）とストーブからの距離を選べる。実際の熱さの違いは未解析。どの席も人の前を通らずに着ける。"
                    f"ストーブ・扉はv7の位置のまま、柵と中間段の間は{s['aisle_step_to_guard']:.2f} m。"
                ),
                "cost": f"0.90の席は2つだけ。0.45の足置きに立つと天井まで{H - 0.45:.2f} m（天井{H:.2f}の場合）で、身長1.85 mの人の頭上は{H - 0.45 - 1.85:.2f} m。",
            },
            {
                "name": "B: ストーブを中心にした円弧のベンチ",
                "adopted": False,
                "seats": "約4",
                "why_not": (
                    f"柵（半径{SELF['heater']['guard_r']:.2f}）＋通路0.75＋座面0.60で半径{ring:.2f} m、直径{2 * ring:.2f} mの円が要り、内法{s['room_inner'][0]:.2f} mの室に入らない。"
                    "一部の弧だけ残すと4席前後で、全員が同じ高さ・同じ距離になり、メイン室を小さくした形になる。"
                ),
            },
        ],
        "dry": [
            {
                "name": "A: 高い腰掛け2＋脚を伸ばす寝座2を南北に分ける（採用）",
                "adopted": True,
                "seats": 4,
                "why": (
                    f"どの席も目の前の段から上がれて、人の前を通らない。寝座は西壁から{DRY['d_depth']:.2f} mの平らな段に{d['back_rake_deg']:.0f}°寝かせた背を付け、"
                    f"脚を伸ばしてTVを見る。TVの壁の前は{d['aisle_east_of_d_step']:.2f} m空く。"
                ),
                "cost": "席は4。v7の2段（割り算で上3・下3）より少ない。",
            },
            {
                "name": "B: 西壁いっぱいに高い腰掛け3と寝座2を互い違い",
                "adopted": False,
                "seats": 5,
                "why_not": "壁の長さ2.45 mに5人で、寝座の人の肩と上の人の足の間が0.05 mしか残らない。上の席へ行く足元の幅も0.43 m。",
            },
            {
                "name": "C: 2段ベンチの前に寝椅子を東西に置く",
                "adopted": False,
                "seats": "5〜6",
                "why_not": (
                    f"上段0.60＋足置き0.40＋寝椅子1.45で2.45 m、内法{d['room_inner'][0]:.2f} mの室ではTVの壁の前が0.33 mしか残らない。"
                    "上段を0.50、足置きを0.32まで詰めても0.55 m。"
                ),
            },
        ],
    }


if __name__ == "__main__":
    import json

    print(json.dumps({"checks": checks(), "options": options()}, ensure_ascii=False, indent=1))
