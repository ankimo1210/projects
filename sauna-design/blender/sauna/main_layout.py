"""Main aufguss sauna v6 as plain data — no bpy import.

Central stove, benches on three sides (north, west, east), the south side open for the door and the performer.
One source for the Blender builder (room_main.py), the check figures (scripts/main_diagram.py) and the mesh check
(blender/verify_main.py). Metres, x east, y north, z up.

Body sizes are assumed adult study values (not a survey, not a regulation). Seat counts, clearances, heater distances,
headroom and the towel ranges are concept checks only: code compliance, the heater maker's clearances, structure,
ventilation / heat load and a performer's review are all outside this file.
"""

import math

# finished faces of the room (structure 0.08 inside the grid line + 0.032 slat lining)
XW, XE, YS, YN, H = 0.112, 5.888, 9.112, 13.888, 2.4
DOOR = (9.25, 10.25)  # opening in the east wall (y range), unchanged from v5
TOP_UP, TOP_LOW, TOP_STEP = 0.90, 0.45, 0.225
D_UP = 0.60  # upper seat depth on all three sides (wall face to nose)
N_FOOT, N_SEAT = 0.30, 0.50  # north lower tier = foot strip for the upper row + front-row seat
S_FOOT, S_STEP = 0.40, 0.28  # side benches: foot bench at 0.45 and a continuous half step at 0.225
Y_END = 10.55  # south end of both side benches (0.30 north of the door jamb)
HEATER = {
    "c": (3.0, 10.95),
    "r": 0.42,
    "h": 1.05,
    "guard_r": 0.74,
    "guard_h": 0.82,
}  # same heater and guard as v5, moved
GUARD_RAIL_T = 0.042  # rail thickness in furniture.heater()
R_END = {"upper": 0.07, "foot": 0.10, "step": 0.10}  # plan radius of the free south ends (v5 motif)
DIAG = {"upper": 0.22, "step": 0.30}  # diagonal infill at the inside corners (v5 motif)

# assumed adult (study values)
BODY = {
    "shoulder": 0.50,
    "torso_d": 0.26,
    "sit_h": 0.92,
    "sit_h_tall": 0.98,
    "shoulder_h": 0.60,
    "thigh_w": 0.40,
    "thigh_t": 0.15,
    "buttock_knee": 0.60,
    "leg_d": 0.12,
    "feet_w": 0.36,
    "foot_l": 0.27,
    "back_gap": 0.12,
    "stature": 1.72,
    "stature_tall": 1.85,
}
PITCH = {
    "n_upper": 0.68,
    "n_lower": 0.66,
    "side": 0.6375,
}  # n_lower was 0.70; narrowed so each north landing grows 0.49 -> 0.57 m
COUNT = {"n_upper": 6, "n_lower": 4, "side": 4}


def dims():
    hx, hy = HEATER["c"]
    # outer face of the guard rails: octagon apothem (flats face the benches) + half the 42 mm rail
    ap = HEATER["guard_r"] * math.cos(math.pi / 8) + GUARD_RAIL_T / 2
    d = {
        "room_inner": (round(XE - XW, 3), round(YN - YS, 3)),
        "ceiling": H,
        "n_upper_front": YN - D_UP,
        "n_lower_front": YN - D_UP - N_FOOT - N_SEAT,
        "n_foot_line": YN - D_UP - N_FOOT,
        "w_upper_front": XW + D_UP,
        "w_foot_front": XW + D_UP + S_FOOT,
        "w_step_front": XW + D_UP + S_FOOT + S_STEP,
        "e_upper_front": XE - D_UP,
        "e_foot_front": XE - D_UP - S_FOOT,
        "e_step_front": XE - D_UP - S_FOOT - S_STEP,
        "guard_apothem": ap,
    }
    d["aisle_west"] = hx - ap - d["w_step_front"]
    d["aisle_east"] = d["e_step_front"] - (hx + ap)
    d["aisle_north"] = d["n_lower_front"] - (hy + ap)
    d["floor_south"] = (hy - ap) - YS
    d["bench_end_to_door_jamb"] = Y_END - DOOR[1]
    d["heater_shell_to_n_lower_nose"] = d["n_lower_front"] - (hy + HEATER["r"] + 0.05)
    d["heater_shell_to_side_step"] = d["e_step_front"] - (hx + HEATER["r"] + 0.05)
    d["heater_shell_to_side_foot_bench"] = d["e_foot_front"] - (hx + HEATER["r"] + 0.05)
    d["guard_to_heater_shell"] = (
        ap - GUARD_RAIL_T - (HEATER["r"] + 0.05)
    )  # inner face of the rail to the plinth ring
    d["headroom_upper_seat"] = H - TOP_UP
    d["headroom_standing_foot_level"] = H - TOP_LOW
    d["headroom_standing_step"] = H - TOP_STEP
    d["head_clear_upper"] = H - TOP_UP - BODY["sit_h"]
    d["head_clear_upper_tall"] = H - TOP_UP - BODY["sit_h_tall"]
    return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()}


def seats():
    """20 seat positions. 'b' = centre of the back line on the seat, 'f' = facing, tier = upper / lower / corner."""
    D = dims()
    out = []

    def add(sid, tier, b, f, pitch, seat_z, foot_z, posture="legs_down", back=True):
        out.append(
            {
                "id": sid,
                "tier": tier,
                "b": (round(b[0], 4), round(b[1], 4)),
                "f": f,
                "pitch": pitch,
                "seat_z": seat_z,
                "foot_z": foot_z,
                "posture": posture,
                "backrest": back,
            }
        )

    g = BODY["back_gap"]
    n, p = COUNT["n_upper"], PITCH["n_upper"]
    x0 = (XW + XE) / 2 - n * p / 2
    for k in range(n):
        add(f"NU{k + 1}", "upper", (x0 + (k + 0.5) * p, YN - g), (0, -1), p, TOP_UP, TOP_LOW)
    n, p = COUNT["n_lower"], PITCH["n_lower"]
    x0 = (XW + XE) / 2 - n * p / 2
    for k in range(
        n
    ):  # front row: no backrest, the back sits 30 mm in front of the foot-strip line
        add(
            f"NL{k + 1}",
            "lower",
            (x0 + (k + 0.5) * p, D["n_foot_line"] - 0.03),
            (0, -1),
            p,
            TOP_LOW,
            0.0,
            back=False,
        )
    n, p = COUNT["side"], PITCH["side"]
    y1 = Y_END + n * p
    for k in range(n):  # numbered from the north
        add(f"W{k + 1}", "upper", (XW + g, y1 - (k + 0.5) * p), (1, 0), p, TOP_UP, TOP_LOW)
        add(f"E{k + 1}", "upper", (XE - g, y1 - (k + 0.5) * p), (-1, 0), p, TOP_UP, TOP_LOW)
    # corner squares: one person each with the feet up on the bench (cross-legged / knees up), nobody else counted there
    add(
        "CW",
        "corner",
        (XW + D_UP / 2, YN - D_UP / 2),
        (0.7071, -0.7071),
        D_UP,
        TOP_UP,
        TOP_UP,
        posture="feet_up",
    )
    add(
        "CE",
        "corner",
        (XE - D_UP / 2, YN - D_UP / 2),
        (-0.7071, -0.7071),
        D_UP,
        TOP_UP,
        TOP_UP,
        posture="feet_up",
    )
    return out


def body_boxes(s, tall=False):
    """Axis-aligned boxes of a simple seated body: (part, x0, y0, x1, y1, z0, z1)."""
    B = BODY
    sz, fz = s["seat_z"], s["foot_z"]
    sit = B["sit_h_tall"] if tall else B["sit_h"]
    bx, by = s["b"]
    if s["posture"] == "feet_up":
        h = 0.27
        return [
            ("legs", bx - h, by - h, bx + h, by + h, sz, sz + 0.22),
            ("torso", bx - 0.22, by - 0.22, bx + 0.22, by + 0.22, sz + 0.22, sz + B["shoulder_h"]),
            ("head", bx - 0.10, by - 0.10, bx + 0.10, by + 0.10, sz + B["shoulder_h"], sz + sit),
        ]
    fx, fy = s["f"]
    lx, ly = -fy, fx

    def box(part, u, v0, v1, z0, z1):
        xs = [bx + fx * v + lx * w for v in (v0, v1) for w in (-u / 2, u / 2)]
        ys = [by + fy * v + ly * w for v in (v0, v1) for w in (-u / 2, u / 2)]
        return (part, min(xs), min(ys), max(xs), max(ys), z0, z1)

    k = B["buttock_knee"]
    return [
        box("torso", B["shoulder"], 0.0, B["torso_d"], sz, sz + B["shoulder_h"]),
        box("head", 0.18, 0.03, 0.23, sz + B["shoulder_h"], sz + sit),
        box("thighs", B["thigh_w"], 0.0, k, sz, sz + B["thigh_t"]),
        box("shins", B["feet_w"], k - B["leg_d"], k, fz + 0.06, sz),
        box("feet", B["feet_w"], k - 0.15, k - 0.15 + B["foot_l"], fz, fz + 0.06),
    ]


def standing():
    """Check bodies for the standing moments (all 20 seats taken): on the north-east landing, on the east half step in
    front of a seat, passing along the north aisle, and the performer on the south floor."""
    D = dims()
    S = seats()
    nl = [s for s in S if s["id"].startswith("NL")]
    xb = nl[-1]["b"][0] + nl[-1]["pitch"] / 2
    toes = min(p[2] for s in nl for p in body_boxes(s) if p[0] == "feet")
    hx, hy = HEATER["c"]
    e3 = next(s for s in S if s["id"] == "E3")
    return [
        {
            "id": "T1",
            "label": "北東の踊り場に立つ",
            "c": ((xb + D["e_foot_front"]) / 2, (D["n_lower_front"] + D["n_foot_line"]) / 2),
            "z": TOP_LOW,
            "wide": "x",
        },
        {
            "id": "T2",
            "label": "東の中間段に立つ",
            "c": ((D["e_step_front"] + D["e_foot_front"]) / 2, e3["b"][1]),
            "z": TOP_STEP,
            "wide": "y",
        },
        {
            "id": "T3",
            "label": "北通路を通る",
            "c": (hx, (hy + D["guard_apothem"] + toes) / 2),
            "z": 0.0,
            "wide": "y",
        },
        {
            "id": "T4",
            "label": "演者（南）",
            "c": (hx, (YS + hy - D["guard_apothem"]) / 2),
            "z": 0.0,
            "wide": "x",
        },
    ]


def standing_boxes(t, tall=False):
    """(part, x0, y0, x1, y1, z0, z1) of a standing body: shoulders along t['wide']."""
    h = BODY["stature_tall"] if tall else BODY["stature"]
    cx, cy = t["c"]
    a, b = BODY["shoulder"] / 2, BODY["torso_d"] / 2
    wx, wy = (a, b) if t["wide"] == "x" else (b, a)
    z = t["z"]
    return [
        ("stand_body", cx - wx, cy - wy, cx + wx, cy + wy, z, z + h - 0.24),
        ("stand_head", cx - 0.09, cy - 0.10, cx + 0.09, cy + 0.10, z + h - 0.24, z + h),
    ]


def zones():
    """Plan rectangles by use, so seat, footrest, step / landing and floor are never counted twice.
    (kind, label, x0, y0, x1, y1, level)"""
    D = dims()
    z = []
    for s in seats():
        bx, by = s["b"]
        p = s["pitch"]
        if s["tier"] == "corner":
            z.append(
                (
                    "seat_corner",
                    s["id"],
                    bx - D_UP / 2,
                    by - D_UP / 2,
                    bx + D_UP / 2,
                    by + D_UP / 2,
                    TOP_UP,
                )
            )
        elif s["id"].startswith("NU"):
            z.append(("seat", s["id"], bx - p / 2, D["n_upper_front"], bx + p / 2, YN, TOP_UP))
        elif s["id"].startswith("NL"):
            z.append(
                (
                    "seat",
                    s["id"],
                    bx - p / 2,
                    D["n_lower_front"],
                    bx + p / 2,
                    D["n_foot_line"],
                    TOP_LOW,
                )
            )
        elif s["id"].startswith("W"):
            z.append(("seat", s["id"], XW, by - p / 2, D["w_upper_front"], by + p / 2, TOP_UP))
        else:
            z.append(("seat", s["id"], D["e_upper_front"], by - p / 2, XE, by + p / 2, TOP_UP))
    z.append(
        (
            "foot",
            "北上段の足置き",
            D["w_foot_front"],
            D["n_foot_line"],
            D["e_foot_front"],
            D["n_upper_front"],
            TOP_LOW,
        )
    )
    z.append(
        (
            "foot",
            "西の足置き段",
            D["w_upper_front"],
            Y_END,
            D["w_foot_front"],
            D["n_foot_line"],
            TOP_LOW,
        )
    )
    z.append(
        (
            "foot",
            "東の足置き段",
            D["e_foot_front"],
            Y_END,
            D["e_upper_front"],
            D["n_foot_line"],
            TOP_LOW,
        )
    )
    z.append(
        (
            "step",
            "西の中間段",
            D["w_foot_front"],
            Y_END,
            D["w_step_front"],
            D["n_lower_front"],
            TOP_STEP,
        )
    )
    z.append(
        (
            "step",
            "東の中間段",
            D["e_step_front"],
            Y_END,
            D["e_foot_front"],
            D["n_lower_front"],
            TOP_STEP,
        )
    )
    nl = [s for s in seats() if s["id"].startswith("NL")]
    xa, xb = nl[0]["b"][0] - nl[0]["pitch"] / 2, nl[-1]["b"][0] + nl[-1]["pitch"] / 2
    z.append(
        (
            "landing",
            "北西の踊り場",
            D["w_foot_front"],
            D["n_lower_front"],
            xa,
            D["n_foot_line"],
            TOP_LOW,
        )
    )
    z.append(
        (
            "landing",
            "北東の踊り場",
            xb,
            D["n_lower_front"],
            D["e_foot_front"],
            D["n_foot_line"],
            TOP_LOW,
        )
    )
    z.append(
        (
            "landing",
            "北西の角",
            D["w_upper_front"],
            D["n_foot_line"],
            D["w_foot_front"],
            D["n_upper_front"],
            TOP_LOW,
        )
    )
    z.append(
        (
            "landing",
            "北東の角",
            D["e_foot_front"],
            D["n_foot_line"],
            D["e_upper_front"],
            D["n_upper_front"],
            TOP_LOW,
        )
    )
    return z


def access():
    """How each seat is reached without stepping on a seat surface, and how many seated people are passed on the way."""
    out = {}
    for s in seats():
        sid = s["id"]
        if sid[0] in "WE":
            out[sid] = {
                "route": "側通路 → 目の前の中間段(0.225) → 足置き段(0.45) → 向きを変えて座る",
                "pass": 0,
                "rises": [0.225, 0.225],
            }
        elif sid.startswith("C"):
            out[sid] = {
                "route": "側通路の奥 → 中間段 → 北の踊り場(0.45) → 角へ腰を下ろす",
                "pass": 0,
                "rises": [0.225, 0.225],
            }
        elif sid.startswith("NL"):
            k = int(sid[2:])
            out[sid] = {
                "route": "北通路（ストーブ柵とベンチの間）から腰掛ける",
                "pass": min(k - 1, COUNT["n_lower"] - k),
                "rises": [],
            }
        else:
            k = int(sid[2:])
            out[sid] = {
                "route": "側通路の奥 → 中間段 → 北の踊り場(0.45) → 足置き帯を横へ → 座る",
                "pass": min(k - 1, COUNT["n_upper"] - k),
                "rises": [0.225, 0.225],
            }
    return out


# ---- floor, clearances, towel ranges -------------------------------------------------------------------------
def _octagon(c, r):
    return [
        (
            c[0] + r * math.cos(math.pi / 8 + math.pi / 4 * k),
            c[1] + r * math.sin(math.pi / 8 + math.pi / 4 * k),
        )
        for k in range(8)
    ]


def _d_rect(p, r):
    dx = max(r[0] - p[0], 0.0, p[0] - r[2])
    dy = max(r[1] - p[1], 0.0, p[1] - r[3])
    return math.hypot(dx, dy)


def _d_poly(p, poly):
    """Distance to a convex polygon (0 inside)."""
    inside, best = True, 1e9
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        if ex * (p[1] - a[1]) - ey * (p[0] - a[0]) < 0:
            inside = False
        t = max(0.0, min(1.0, ((p[0] - a[0]) * ex + (p[1] - a[1]) * ey) / (ex * ex + ey * ey)))
        best = min(best, math.hypot(p[0] - a[0] - t * ex, p[1] - a[1] - t * ey))
    return 0.0 if inside else best


def bench_rects():
    """Footprints of everything built on the floor except the heater (benches, foot benches, steps)."""
    D = dims()
    return [
        (XW, D["n_lower_front"], XE, YN),
        (XW, Y_END, D["w_step_front"], D["n_lower_front"]),
        (D["e_step_front"], Y_END, XE, D["n_lower_front"]),
    ]


def diag_treads():
    """Diagonal half-step treads in the two inside corners where the side step meets the front row (plan triangles)."""
    D = dims()
    g = DIAG["step"]
    y = D["n_lower_front"]
    return [
        [(D["w_step_front"], y), (D["w_step_front"], y - g), (D["w_step_front"] + g, y)],
        [(D["e_step_front"], y), (D["e_step_front"] - g, y), (D["e_step_front"], y - g)],
    ]


def floor_obstacles(people=True):
    rects = bench_rects()
    if people:  # front-row knees and feet beyond the bench nose
        for s in seats():
            if s["id"].startswith("NL"):
                for part, x0, y0, x1, y1, z0, z1 in body_boxes(s):
                    if part in ("thighs", "shins", "feet"):
                        rects.append((x0, y0, x1, y1))
    return rects, [
        _octagon(HEATER["c"], dims()["guard_apothem"] / math.cos(math.pi / 8))
    ] + diag_treads()


def clearance(p, rects, polys, walls=(XW, YS, XE, YN)):
    d = min(p[0] - walls[0], walls[2] - p[0], p[1] - walls[1], walls[3] - p[1])
    for r in rects:
        d = min(d, _d_rect(p, r))
    for q in polys:
        d = min(d, _d_poly(p, q))
    return d


def _best(region, fn, step=0.025):
    best = (0.0, None)
    x = region[0]
    while x <= region[2] + 1e-9:
        y = region[1]
        while y <= region[3] + 1e-9:
            d = fn((x, y))
            if d > best[0]:
                best = (d, (round(x, 3), round(y, 3)))
            y += step
        x += step
    return best


def floor_discs(rects=None, polys=None, regions=None):
    """Largest clear floor circle in each named part of the floor: (name, diameter, centre)."""
    if rects is None:
        rects, polys = floor_obstacles()
    D = dims()
    hx, hy = HEATER["c"]
    regions = regions or [
        ("南（ストーブ正面・演者の主位置）", (hx - 0.6, YS, hx + 0.6, hy)),
        ("南東（扉前）", (hx + 0.6, YS, XE, Y_END + 0.4)),
        ("南西", (XW, YS, hx - 0.6, Y_END + 0.4)),
        ("西の側通路", (D["w_step_front"], Y_END + 0.4, hx, D["n_lower_front"] - 0.5)),
        ("東の側通路", (hx, Y_END + 0.4, D["e_step_front"], D["n_lower_front"] - 0.5)),
        ("北西の隅", (D["w_step_front"], D["n_lower_front"] - 0.9, hx - 0.5, D["n_lower_front"])),
        ("北東の隅", (hx + 0.5, D["n_lower_front"] - 0.9, D["e_step_front"], D["n_lower_front"])),
        ("北（ストーブとベンチの間）", (hx - 0.4, hy, hx + 0.4, D["n_lower_front"])),
    ]
    out = []
    for name, reg in regions:
        d, c = _best(reg, lambda p: clearance(p, rects, polys))
        out.append({"where": name, "diameter": round(2 * d, 2), "centre": c})
    return out


TOWEL = {
    "arm": 0.65,
    "towel": 0.65,
    "margin_people": 0.25,
    "note": "腕0.65 m＋タオルの振り出し0.65 mを水平に一周させる半径1.30 mの仮定。人の胴・頭からは0.25 m離す。演者の確認は未実施。",
}


def swing_radius(over_stove):
    """Largest horizontal towel radius from any standing point on the clear floor: plan distance to the walls and to every
    seated torso / head (plus a margin). over_stove=False also keeps the towel off the guard octagon."""
    rects_floor, polys = floor_obstacles()
    people = []
    m = TOWEL["margin_people"]
    for s in seats():
        for part, x0, y0, x1, y1, z0, z1 in body_boxes(s):
            if part in ("torso", "head", "legs"):
                people.append((x0 - m, y0 - m, x1 + m, y1 + m))
    air_polys = [] if over_stove else polys[:1]

    def fn(p):
        if clearance(p, rects_floor, polys) < 0.30:  # the performer needs a place to stand
            return 0.0
        return clearance(p, people, air_polys)

    d, c = _best((XW, YS, XE, YN), fn)
    return {
        "radius": round(d, 2),
        "stand_at": c,
        "needed_for_full_turn": TOWEL["arm"] + TOWEL["towel"],
    }


def v5_reference():
    """Same floor measures on the v5 L-shaped room (benches only; v5 never placed bodies). For comparison."""
    f_n, f_w = YN - 1.34, XW + 1.34
    rects = [(XW, f_n, XE - 0.32, YN), (XW, 10.55, f_w, f_n)]
    polys = [_octagon((2.90, 9.95), 0.74)]
    d, c = _best((XW, YS, XE, YN), lambda p: clearance(p, rects, polys))
    return {
        "largest_floor_circle": round(2 * d, 2),
        "centre": c,
        "stove": "南壁前 (2.90, 9.95)",
        "bench": "北＋西のL字2段、上段0.62＋下段0.72",
    }


# ---- checks ---------------------------------------------------------------------------------------------------
def _overlap(a, b, eps=1e-6):
    return (
        min(a[3], b[3]) - max(a[1], b[1]) > eps
        and min(a[4], b[4]) - max(a[2], b[2]) > eps
        and min(a[6], b[6]) - max(a[5], b[5]) > eps
    )


def checks():
    S = seats()
    Z = zones()
    body = {s["id"]: body_boxes(s) for s in S}
    clashes = []
    ids = [s["id"] for s in S]
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            for pa in body[a]:
                for pb in body[b]:
                    if _overlap(pa, pb):
                        clashes.append([a, pa[0], b, pb[0]])
    seat_z = [z for z in Z if z[0] in ("seat", "seat_corner")]
    feet_on_seat, in_way = [], []
    for s in S:
        for part, x0, y0, x1, y1, z0, z1 in body[s["id"]]:
            if part != "feet":
                continue
            for kind, label, a0, b0, a1, b1, lvl in seat_z:
                if (
                    label != s["id"]
                    and abs(lvl - s["foot_z"]) < 0.01
                    and min(x1, a1) - max(x0, a0) > 1e-6
                    and min(y1, b1) - max(y0, b0) > 1e-6
                ):
                    feet_on_seat.append([s["id"], label])
            for kind, label, a0, b0, a1, b1, lvl in Z:
                if (
                    kind in ("landing", "step")
                    and abs(lvl - s["foot_z"]) < 0.01
                    and min(x1, a1) - max(x0, a0) > 1e-6
                    and min(y1, b1) - max(y0, b0) > 1e-6
                ):
                    in_way.append([s["id"], label])
    zone_overlap = []
    for i, a in enumerate(Z):
        for b in Z[i + 1 :]:
            if (
                min(a[4], b[4]) - max(a[2], b[2]) > 1e-6
                and min(a[5], b[5]) - max(a[3], b[3]) > 1e-6
            ):
                zone_overlap.append([a[1], b[1]])
    neighbour_gaps = {}
    for grp in ("NU", "NL", "W", "E"):
        row = [s for s in S if s["id"].startswith(grp)]
        neighbour_gaps[grp] = round(row[0]["pitch"] - BODY["shoulder"], 3)
    D = dims()
    nl = [s for s in S if s["id"].startswith("NL")]
    toes = min(p[2] for s in nl for p in body[s["id"]] if p[0] == "feet")
    hy = HEATER["c"][1]
    acc = access()
    stand = []
    for t in standing():
        hit = sorted(
            {
                f"{sid}:{pb[0]}"
                for sid in ids
                for pb in body[sid]
                for pa in standing_boxes(t)
                if _overlap(pa, pb)
            }
        )
        standing_gaps = [
            max(max(pa[1] - pb[3], pb[1] - pa[3]), max(pa[2] - pb[4], pb[2] - pa[4]))
            for sid in ids
            for pb in body[sid]
            for pa in standing_boxes(t)[:1]
            if min(pa[6], pb[6]) - max(pa[5], pb[5]) > 0
        ]
        stand.append(
            {
                "id": t["id"],
                "label": t["label"],
                "at": [round(v, 3) for v in t["c"]],
                "level": t["z"],
                "head_to_ceiling": round(H - t["z"] - BODY["stature"], 3),
                "head_to_ceiling_tall": round(H - t["z"] - BODY["stature_tall"], 3),
                "overlaps_seated_body": hit,
                "nearest_seated_body_m": round(min(standing_gaps), 3) if standing_gaps else None,
            }
        )
    lz = [z for z in Z if z[0] == "landing" and "踊り場" in z[1]][0]
    return {
        "standing": stand,
        "north_landing_size": [round(lz[4] - lz[2], 3), round(lz[5] - lz[3], 3)],
        "seats_needing_cooperation": sorted(k for k, a in acc.items() if a["pass"]),
        "seats": len(S),
        "legs_down": sum(1 for s in S if s["posture"] == "legs_down"),
        "feet_up_corner": sum(1 for s in S if s["posture"] == "feet_up"),
        "by_row": {
            "north_upper": COUNT["n_upper"],
            "north_lower": COUNT["n_lower"],
            "west_upper": COUNT["side"],
            "east_upper": COUNT["side"],
            "corner": 2,
        },
        "pitch": PITCH,
        "shoulder_gap_between_neighbours": neighbour_gaps,
        "body_clashes": clashes,
        "feet_on_another_seat": feet_on_seat,
        "feet_on_step_or_landing": in_way,
        "zone_overlaps": zone_overlap,
        "north_aisle_clear_of_front_row_toes": round(toes - (hy + D["guard_apothem"]), 3),
        "north_foot_strip_used_by_feet": round(
            max(
                p[4] for s in S if s["id"].startswith("NU") for p in body[s["id"]] if p[0] == "feet"
            )
            - min(
                p[2] for s in S if s["id"].startswith("NU") for p in body[s["id"]] if p[0] == "feet"
            ),
            3,
        ),
        "seats_passed_max": max(a["pass"] for a in acc.values()),
        "seats_reached_without_passing_anyone": sum(1 for a in acc.values() if a["pass"] == 0),
        "dims": D,
    }


def options():
    """The two candidates compared under the centre-stove condition (same room, same ceiling, about 20 seats)."""
    D = dims()
    ap = D["guard_apothem"]
    top3, mid3, foot3 = (
        1.26,
        0.84,
        0.42,
    )  # ceiling 2.4 - 1.14 (maker guidance 1.1-1.2) -> three equal rises
    depth3 = D_UP + (N_FOOT + N_SEAT) + S_FOOT  # top seat + middle (feet + seat) + foot bench
    front3 = YN - depth3
    hy3 = front3 - D["aisle_north"] - ap
    return [
        {
            "name": "A: 囲み型2段（採用）",
            "north_depth": round(D_UP + N_FOOT + N_SEAT, 2),
            "stove_y": HEATER["c"][1],
            "stove_off_room_centre": round((YS + YN) / 2 - HEATER["c"][1], 2),
            "floor_south": D["floor_south"],
            "aisle_north": D["aisle_north"],
            "top_seat": TOP_UP,
            "top_seat_to_ceiling": D["headroom_upper_seat"],
            "head_to_ceiling": D["head_clear_upper"],
            "standing_headroom_on_access_level": D["headroom_standing_foot_level"],
            "rises": [0.225, 0.225],
            "seats": checks()["seats"],
        },
        {
            "name": "B: 北奥だけ3段（不採用）",
            "north_depth": round(depth3, 2),
            "stove_y": round(hy3, 2),
            "stove_off_room_centre": round((YS + YN) / 2 - hy3, 2),
            "floor_south": round(hy3 - ap - YS, 2),
            "aisle_north": D["aisle_north"],
            "top_seat": top3,
            "top_seat_to_ceiling": round(H - top3, 2),
            "head_to_ceiling": round(H - top3 - BODY["sit_h"], 2),
            "standing_headroom_on_access_level": round(H - mid3, 2),
            "rises": [0.21] * 4,
            "foot_level": foot3,
            "guard_south_face_y": round(hy3 - ap, 2),
            "door_y": list(DOOR),
            "seats": "北 上6＋角2＋中4、東西 各3〜4 で約20（未配置の概算）",
        },
    ]


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            {
                "checks": checks(),
                "floor_discs": floor_discs(),
                "floor_discs_benches_only": floor_discs(*floor_obstacles(people=False)),
                "swing_not_over_stove": swing_radius(False),
                "swing_over_stove": swing_radius(True),
                "v5_reference": v5_reference(),
                "options": options(),
            },
            ensure_ascii=False,
            indent=1,
        )
    )
