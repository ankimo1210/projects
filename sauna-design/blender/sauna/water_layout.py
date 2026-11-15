"""v8 bath strip as plain data (no bpy): two smaller cold pools and the rest annex that takes the freed floor.

Shared by room_water.py (model), blender/verify_v8.py (mesh check) and scripts/v8_diagram.py (figure).
Metres, x east, y north, z up; deck level z = 0, water surface z = -0.06.

Everything here is a concept study with assumed adult body sizes (main_layout.BODY). Pool count, water temperature, cooling
and filtration plant, slip resistance, structure, code compliance and cost are not selected or verified. The number of
people shown in the water is where bodies fit without touching, not a bather-load rating.
"""

import math

from . import main_layout as ML

B = ML.BODY
XW, XE, YN = (
    6.112,
    16.906,
    10.388,
)  # finished faces: west timber wall, east stone wall, north timber wall
YS_STONE, YS_TIMBER = (
    6.594,
    6.612,
)  # south wall face behind the pools (stone) / in the annex (timber slats)
COPING_N, COPING_W, WATER_DROP = 9.0, 0.30, 0.06
REST_DOOR = (7.0, 8.1)  # opening in the west wall (y range), unchanged
MAIN_DOOR = (9.25, 10.25)  # main sauna door in the west wall (y range), unchanged
NORTH_DOORS = {"self": (7.1, 8.1), "dry": (10.2, 11.2)}  # x ranges in the north wall, unchanged
PERCH_X = (12.62, 15.0)  # v6 spare perch seats in the north wall recess, unchanged
WASH_OPENING = (
    14.98,
    16.906,
)  # x range of the opening to the wash area in the south wall, unchanged

# v3-v7 pools (for the comparison only)
OLD = {
    "deep": {
        "rect": (7.1, 6.8, 3.2, 1.9),
        "depth": 1.2,
        "steps": {"width": 0.9, "treads": 4, "tread": 0.28},
    },
    "seated": {
        "rect": (11.3, 6.8, 3.2, 1.9),
        "depth": 0.6,
        "steps": {"width": 0.9, "treads": 1, "tread": 0.28},
    },
    "outer_x": (6.8, 14.8),  # outer edges of the copings
}
# v8 pools: both keep the old north / south lines (so the walkway is not touched) and are turned so the long side runs
# north-south; they share one divider and stand at the east end of the old pool block.
POOLS = {
    "deep": {
        "rect": (10.84, 6.8, 1.78, 1.9),
        "depth": 1.2,
        "steps": {"corner": "NE", "run": "south", "width": 0.78, "treads": 4, "tread": 0.28},
    },
    "seated": {
        "rect": (12.90, 6.8, 1.60, 1.9),
        "depth": 0.6,
        "steps": {"corner": "NE", "run": "south", "width": 0.60, "treads": 2, "tread": 0.28},
    },
}
# Both stairs stand in the north-east corner of their pool and come down southwards. The floor in front of the last tread
# (step_foot) is kept free in both pools: nobody is counted there, a person coming down or going out always has it.
# In the seated pool it is the 0.60 m lane along the east wall, beyond the feet of the people sitting against the west wall.
DIVIDER = (12.62, 12.90)  # shared coping between the two pools
EAST_COPING = (
    14.50,
    14.80,
)  # unchanged outer edge: the east zone and the wash opening keep their width
SCREEN = {
    "x0": 10.71,
    "x1": 10.84,
    "h": 2.10,  # splash wall between the annex and the deep pool
    "y1": COPING_N,
    "ease": (0.50, 0.80),
    "timber_t": 0.116,
}  # north end comes down to 1.30 m as a quarter ellipse
# Grab rails. Deep pool: inside the stair on the divider side, low post on the third tread (0.70 m clear beside it).
# Seated pool: on the east coping beside the stair, both posts on the coping, so the 0.60 m stair stays clear.
RAILS = {
    "deep": {"inset": 0.04, "low_tread": 3},
    "seated": {"x": 14.56, "y": (8.84, 8.10), "low_h": 0.55},
}
SPOTS = {
    "deep": (11.73, 7.75),
    "seated": (13.70, 7.75),
}  # one caustic spot per pool (v7 had two each)
PEG_Z = 1.05

# rest annex in the freed west end: four loungers in two rows, heads east, all facing the same way (west)
LOUNGER = {"len": 1.80, "w": 0.62}
ANNEX = {
    "x0": 6.952,
    "x1": SCREEN["x0"],
    "y0": YS_TIMBER,
    "y1": 8.95,
    "panel_h": 1.30,
    "screen_t": 0.035,
    "north_t": 0.05,
    "z0": 0.06,
    "ease": (0.18, 0.12),  # panels float 60 mm; free ends ease down 0.12 m
    "drain": (8.83, 7.756),
    "foot_w": 6.995,
    "foot_e": 8.86,
    "divider": (8.815, 8.85),  # the lounger mesh is 1.808 long: 42 mm stay free behind each head
    "row_s": YS_TIMBER + 0.06 + LOUNGER["w"] / 2,
    "row_n": 8.95 - 0.05 - 0.06 - LOUNGER["w"] / 2,
    "mouth": (7.38, 8.17),  # clear opening of the aisle between the ends of the foot screens
}


def loungers():
    a = ANNEX
    return [
        {"id": "RA1", "foot": (a["foot_w"], a["row_s"]), "heading": (1, 0), "row": "S"},
        {"id": "RA2", "foot": (a["foot_e"], a["row_s"]), "heading": (1, 0), "row": "S"},
        {"id": "RA3", "foot": (a["foot_w"], a["row_n"]), "heading": (1, 0), "row": "N"},
        {"id": "RA4", "foot": (a["foot_e"], a["row_n"]), "heading": (1, 0), "row": "N"},
    ]


def partitions():
    """Timber screens of the annex: (name, x0, y0, x1, y1, height, fins_above)."""
    a = ANNEX
    t, h = a["screen_t"], a["panel_h"]
    m0, m1 = a["mouth"]
    d0, d1 = a["divider"]
    return [
        ("foot screen south", a["x0"], a["y0"], a["x0"] + t, m0, h, False),
        ("foot screen north", a["x0"], m1, a["x0"] + t, a["y1"] - a["north_t"], h, False),
        ("divider south", d0, a["y0"], d1, m0, h, False),
        ("divider north", d0, m1, d1, a["y1"] - a["north_t"], h, False),
        ("walkway screen", a["x0"], a["y1"] - a["north_t"], a["x1"], a["y1"], h, True),
    ]


def pegs():
    """One towel peg per lounger on the screen end that faces the aisle mouth: (x, y, (dx, dy))."""
    a = ANNEX
    m0, m1 = a["mouth"]
    xs = (a["x0"] + a["screen_t"] / 2, (a["divider"][0] + a["divider"][1]) / 2)
    return [(xs[0], m0, (0, 1)), (xs[1], m0, (0, 1)), (xs[0], m1, (0, -1)), (xs[1], m1, (0, -1))]


# ---- pools ----------------------------------------------------------------------------------------------------
def pool(pid, src=None):
    """Inner rectangle, floor level, treads and the free floor of one pool."""
    p = (src or POOLS)[pid]
    x, y, w, d = p["rect"]
    x1, y1 = x + w, y + d
    s = p["steps"]
    n, tr, sw = s["treads"], s["tread"], s["width"]
    zf = -WATER_DROP - p["depth"]
    rise = (p["depth"] + WATER_DROP) / (n + 1)
    treads = []
    if s.get("run", "south") == "south":  # entered from the north coping, descending south
        xa, xb = (x1 - sw, x1) if s.get("corner", "NW") == "NE" else (x, x + sw)
        for k in range(n):
            treads.append((xa, y1 - (k + 1) * tr, xb, y1 - k * tr, -(k + 1) * rise))
        foot = (xa, y, xb, y1 - n * tr)  # floor in front of the last tread
        zone = (x, y, xa, y1) if s.get("corner", "NW") == "NE" else (xb, y, x1, y1)
    else:  # entered from the east coping, descending west
        ya, yb = y1 - sw, y1
        for k in range(n):
            treads.append((x1 - (k + 1) * tr, ya, x1 - k * tr, yb, -(k + 1) * rise))
        foot = (x, ya, x1 - n * tr, yb)
        zone = (x, y, x1, ya)
    step_area = sum((t[2] - t[0]) * (t[3] - t[1]) for t in treads)
    return {
        "id": pid,
        "rect": (x, y, x1, y1),
        "floor_z": round(zf, 3),
        "rise": round(rise, 3),
        "treads": treads,
        "step_foot": foot,
        "zone": zone,
        "surface_m2": round(w * d, 2),
        "step_area_m2": round(step_area, 2),
        "free_floor_m2": round(w * d - step_area, 2),
        "depth": p["depth"],
    }


def areas():
    """Water surface, outline incl. copings and water volume, old against new. Volumes ignore the steps (and the old ledge)."""
    out = {}
    for tag, src in (("v7", OLD), ("v8", POOLS)):
        ps = {k: pool(k, src) for k in ("deep", "seated")}
        out[tag] = {
            "surface_m2": {k: v["surface_m2"] for k, v in ps.items()},
            "surface_total_m2": round(sum(v["surface_m2"] for v in ps.values()), 2),
            "free_floor_m2": {k: v["free_floor_m2"] for k, v in ps.items()},
            "volume_m3_ignoring_steps": {
                k: round(v["surface_m2"] * v["depth"], 2) for k, v in ps.items()
            },
        }
        out[tag]["volume_total_m3_ignoring_steps"] = round(
            sum(out[tag]["volume_m3_ignoring_steps"].values()), 2
        )
    out["v7"]["block_outline_incl_copings"] = [
        OLD["outer_x"][0],
        YS_STONE,
        OLD["outer_x"][1],
        COPING_N,
    ]
    out["v8"]["block_outline_incl_copings"] = [SCREEN["x1"], YS_STONE, EAST_COPING[1], COPING_N]
    for tag in ("v7", "v8"):
        o = out[tag]["block_outline_incl_copings"]
        out[tag]["block_outline_m2"] = round((o[2] - o[0]) * (o[3] - o[1]), 2)
    out["freed_floor"] = {
        "x": [OLD["outer_x"][0], SCREEN["x1"]],
        "y": [YS_STONE, COPING_N],
        "m2": round((SCREEN["x1"] - OLD["outer_x"][0]) * (COPING_N - YS_STONE), 2),
        "note": "旧浴槽ブロック西端 x=6.80 から新しい仕切り壁の東面 x=10.84 まで。西壁際の0.69 m（休憩扉への通り）は元から床。",
    }
    out["surface_ratio"] = round(out["v8"]["surface_total_m2"] / out["v7"]["surface_total_m2"], 2)
    out["volume_ratio"] = round(
        out["v8"]["volume_total_m3_ignoring_steps"] / out["v7"]["volume_total_m3_ignoring_steps"], 2
    )
    return out


# ---- bodies ---------------------------------------------------------------------------------------------------
def _stand(cx, cy, z, wide="x", tall=False):
    h = B["stature_tall"] if tall else B["stature"]
    a, b = B["shoulder"] / 2, B["torso_d"] / 2
    wx, wy = (a, b) if wide == "x" else (b, a)
    return [
        ("stand_body", cx - wx, cy - wy, cx + wx, cy + wy, z, z + h - 0.24),
        ("stand_head", cx - 0.09, cy - 0.10, cx + 0.09, cy + 0.10, z + h - 0.24, z + h),
    ]


def _floor_sit(back_x, cy, z, legs=0.95):
    """Sitting on the pool floor with the back against the west wall, legs out to the east."""
    hw = B["shoulder"] / 2
    return [
        ("torso", back_x, cy - hw, back_x + B["torso_d"], cy + hw, z, z + B["shoulder_h"]),
        (
            "head",
            back_x + 0.03,
            cy - 0.09,
            back_x + 0.23,
            cy + 0.09,
            z + B["shoulder_h"],
            z + B["sit_h"],
        ),
        (
            "legs",
            back_x + B["torso_d"],
            cy - B["thigh_w"] / 2,
            back_x + legs,
            cy + B["thigh_w"] / 2,
            z,
            z + B["thigh_t"],
        ),
        (
            "feet",
            back_x + legs - 0.08,
            cy - B["feet_w"] / 2,
            back_x + legs,
            cy + B["feet_w"] / 2,
            z + B["thigh_t"],
            z + 0.27,
        ),
    ]


def _recline(foot, heading, w=0.50):
    """Body on a lounger (furniture.LOUNGER_PROFILE): boxes along the lounger axis s = 0 (foot) .. 1.80 (head)."""
    fx, fy = foot
    hx, hy = heading

    def box(part, s0, s1, z0, z1, width=w):
        xs = [fx + hx * s + (-hy) * q for s in (s0, s1) for q in (-width / 2, width / 2)]
        ys = [fy + hy * s + hx * q for s in (s0, s1) for q in (-width / 2, width / 2)]
        return (part, min(xs), min(ys), max(xs), max(ys), z0, z1)

    # the back of the lounger rises from s = 1.16: the trunk is three stepped boxes that follow it
    return [
        box("feet", 0.03, 0.12, 0.33, 0.60, 0.36),
        box("legs", 0.12, 0.98, 0.42, 0.58, 0.40),
        box("torso", 0.98, 1.20, 0.45, 0.70),
        box("torso", 1.20, 1.38, 0.59, 0.86),
        box("torso", 1.38, 1.54, 0.72, 1.00),
        box("head", 1.54, 1.76, 0.89, 1.13, 0.20),
    ]


def bodies():
    """Check bodies: where people fit in the two pools, on the four loungers and at the tight walking spots.
    (id, kind, label, boxes)"""
    out = []
    d, s = pool("deep"), pool("seated")
    zx0, zy0, zx1, zy1 = d["zone"]
    fx0, fy0, fx1, fy1 = d["step_foot"]
    zc = (zx0 + zx1) / 2
    n = 3
    pitch = (zy1 - zy0) / n
    for k in range(
        n
    ):  # all three stand in the 1.00 m wide part west of the stair; the floor below the stair stays free
        out.append(
            (
                f"PD{k + 1}",
                "pool",
                "深い槽：階段の西の床に立つ",
                _stand(zc, zy0 + (k + 0.5) * pitch, d["floor_z"]),
            )
        )
    t = d["treads"][1]
    out.append(
        (
            "PT1",
            "moving",
            "深い槽：階段の途中（出入り）",
            _stand((t[0] + t[2]) / 2, (t[1] + t[3]) / 2, t[4]),
        )
    )
    out.append(
        (
            "PF1",
            "moving",
            "深い槽：最後の段を下りた床（出入りの1人。静止の人数に数えない）",
            _stand((fx0 + fx1) / 2, fy1 - 0.40, d["floor_z"]),
        )
    )
    x0, y0, x1, y1 = s["rect"]
    pitch = (y1 - y0) / n
    for k in range(n):
        out.append(
            (
                f"PS{k + 1}",
                "pool",
                "座る槽：西の壁を背に床へ座る",
                _floor_sit(x0, y0 + (k + 0.5) * pitch, s["floor_z"]),
            )
        )
    t = s["treads"][0]
    out.append(
        (
            "PT2",
            "moving",
            "座る槽：階段の途中（出入り）",
            _stand((t[0] + t[2]) / 2, (t[1] + t[3]) / 2, t[4]),
        )
    )
    fx0, fy0, fx1, fy1 = s["step_foot"]
    out.append(
        (
            "PF2",
            "moving",
            "座る槽：最後の段を下りた床＝東の壁沿いの通り（出入りの1人。静止の人数に数えない）",
            _stand((fx0 + fx1) / 2, fy1 - 0.55, s["floor_z"], wide="y"),
        )
    )
    for L in loungers():
        out.append((L["id"], "rest", "休憩の離れ：寝椅子", _recline(L["foot"], L["heading"])))
    a = ANNEX
    out.append(
        (
            "RT1",
            "moving",
            "離れの通路に立つ",
            _stand(8.0, (a["row_s"] + a["row_n"]) / 2, 0.0, wide="y"),
        )
    )
    out.append(("RT2", "moving", "休憩の扉の前を通る", _stand((XW + a["x0"]) / 2, 8.45, 0.0)))
    out.append(
        (
            "WT1",
            "moving",
            "水風呂前の通路（予備席の足先の前）",
            _stand(13.6, COPING_N + 0.51, 0.0, wide="y"),
        )
    )
    return out


def _overlap(a, b, eps=1e-6):
    return (
        min(a[3], b[3]) - max(a[1], b[1]) > eps
        and min(a[4], b[4]) - max(a[2], b[2]) > eps
        and min(a[6], b[6]) - max(a[5], b[5]) > eps
    )


def _gap(a, b):
    """Horizontal clear distance between two boxes that overlap in height (None if they do not share a height band)."""
    if min(a[6], b[6]) - max(a[5], b[5]) <= 0:
        return None
    dx = max(a[1] - b[3], b[1] - a[3], 0.0)
    dy = max(a[2] - b[4], b[2] - a[4], 0.0)
    return math.hypot(dx, dy)


def clearances():
    a = ANNEX
    d, s = pool("deep"), pool("seated")
    half = LOUNGER["w"] / 2
    perch_toes = None
    try:
        from . import bath_layout as BL

        perch_toes = min(
            q[2] for st in BL.perch_seats() for q in ML.body_boxes(st) if q[0] == "feet"
        )
    except Exception:
        pass
    out = {
        "walkway_north_of_pools": round(YN - COPING_N, 3),
        "walkway_north_of_pools_v7": round(YN - COPING_N, 3),
        "walkway_north_of_annex_screen": round(YN - a["y1"], 3),
        "rest_door_path_width": round(a["x0"] - XW, 3),
        "rest_door_path_width_v7": round(OLD["outer_x"][0] - XW, 3),
        "annex_aisle_between_loungers": round((a["row_n"] - half) - (a["row_s"] + half), 3),
        "annex_aisle_mouth_between_screen_ends": round(a["mouth"][1] - a["mouth"][0], 3),
        "annex_aisle_length": round(a["x1"] - a["x0"], 3),
        "lounger_to_south_wall": round(a["row_s"] - half - a["y0"], 3),
        "lounger_head_to_splash_wall": round(a["x1"] - (a["foot_e"] + LOUNGER["len"]), 3),
        "east_zone_from_coping_to_east_wall": round(XE - EAST_COPING[1], 3),
        "east_zone_v7": round(XE - OLD["outer_x"][1], 3),
        "deep_steps_clear_width_incl_rail": round(d["treads"][0][2] - d["treads"][0][0] - 0.08, 3),
        "deep_step_foot_spot": [
            round(d["step_foot"][2] - d["step_foot"][0], 3),
            round(d["step_foot"][3] - d["step_foot"][1], 3),
        ],
        "deep_standing_zone": [
            round(d["zone"][2] - d["zone"][0], 3),
            round(d["zone"][3] - d["zone"][1], 3),
        ],
        "seated_passage_past_feet": round(s["rect"][2] - (s["rect"][0] + 0.95), 3),
        "seated_step_foot_lane": [
            round(s["step_foot"][2] - s["step_foot"][0], 3),
            round(s["step_foot"][3] - s["step_foot"][1], 3),
        ],
        "seated_steps_clear_width": round(s["treads"][0][2] - s["treads"][0][0], 3),
        "seated_seat_pitch": round((s["rect"][3] - s["rect"][1]) / 3, 3),
        "deep_standing_pitch": round((d["zone"][3] - d["zone"][1]) / 3, 3),
        "deep_steps_x": [d["treads"][0][0], d["treads"][0][2]],
        "seated_steps_x": [s["treads"][0][0], s["treads"][0][2]],
        "deep_steps_opposite": "北壁の高温ドライ扉（x 10.2〜11.2）と予備の腰掛け（x 12.62〜）の間の壁の前に上がる",
        "seated_steps_entry": "北の縁石の東端（x 13.9〜14.5）から南へ下りる。東の縁石の角からも回り込める。予備の腰掛けP3の足先までは通路1.02 m",
        "divider_coping": "2槽の間の縁石（幅0.28 m）は客の通行帯に数えない",
    }
    if perch_toes is not None:
        out["walkway_between_coping_and_perch_toes"] = round(perch_toes - COPING_N, 3)
    return out


def checks():
    bs = bodies()
    clashes = []
    for i, (ia, ka, la, ba) in enumerate(bs):
        for ib, kb, lb, bb in bs[i + 1 :]:
            if any(_overlap(p, q) for p in ba for q in bb):
                clashes.append([ia, ib])
    gaps = {}
    for ia, ka, la, ba in bs:
        best = None
        for ib, kb, lb, bb in bs:
            if ia == ib:
                continue
            for p in ba:
                for q in bb:
                    g = _gap(p, q)
                    if g is not None and (best is None or g < best[0]):
                        best = (g, ib)
        gaps[ia] = None if best is None else [round(best[0], 3), best[1]]
    d, s = pool("deep"), pool("seated")
    legs_on_steps, in_step_foot = [], []
    for ib, kb, lb, bb in bs:
        if kb != "pool":
            continue
        pl = d if ib.startswith("PD") else s
        for part, x0, y0, x1, y1, z0, z1 in bb:
            for t in pl["treads"]:
                if min(x1, t[2]) - max(x0, t[0]) > 1e-6 and min(y1, t[3]) - max(y0, t[1]) > 1e-6:
                    legs_on_steps.append([ib, part])
            f = pl["step_foot"]
            if min(x1, f[2]) - max(x0, f[0]) > 1e-6 and min(y1, f[3]) - max(y0, f[1]) > 1e-6:
                in_step_foot.append([ib, part])
    return {
        "bodies": [{"id": i, "kind": k, "label": l} for i, k, l, b in bs],
        "body_clashes": clashes,
        "nearest_other_body_m": gaps,
        "seated_bodies_on_steps": legs_on_steps,
        "resting_bodies_in_the_floor_below_the_stairs": in_step_foot,
        "in_water_positions": {
            "deep_standing": 3,
            "seated_on_floor": 3,
            "total": 6,
            "usual": 5,
            "note": (
                "静止して体が触れずに入る位置の数。階段を下りた床（深い槽0.78×0.78、座る槽は東壁沿い0.60×1.34）には誰も数えていないので、"
                "満員でも下りる人・出る人の立つ床は残る（PF1・PF2）。深い槽の3人は幅1.00 mの床に間隔0.63 m（前後の体の間0.37 m）で詰めた状態で、"
                "ゆとりを持つなら2人。通常は5（深い槽2＋座る槽3）、詰めて6と読む。座る槽で奥（南）の人が出るときは他の2人の足先の前0.65 mを通る。"
                "利用人数の基準ではない。"
            ),
        },
        "head_above_water": {
            "deep_standing_1.72": round(d["floor_z"] + B["stature"] + WATER_DROP, 2),
            "seated_shoulder_to_surface": round(s["floor_z"] + B["shoulder_h"] + WATER_DROP, 2),
        },
        "clearances": clearances(),
        "areas": areas(),
    }


# ---- rest seats, routes, demand -------------------------------------------------------------------------------
def rest_count():
    return {
        "v7": {"rest_room": 15, "built_in_bath_seats": 2, "spare_perch": 3, "total": 20},
        "v8": {
            "rest_room": 15,
            "built_in_bath_seats": 2,
            "spare_perch": 3,
            "annex_loungers": 4,
            "total": 24,
        },
        "existing_seats_changed_or_removed": 0,
        "net_added": 4,
        "new_seat": {
            "type": "休憩室と同じ木の寝椅子（長さ1.80×幅0.62 m）",
            "side_access_aisle_m": clearances()["annex_aisle_between_loungers"],
            "facing": "4席とも頭を東・足を西（同じ向き）。向かい合う席は無い",
        },
    }


def _len(path):
    return round(sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:])), 1)


def routes():
    a = ANNEX
    ya = (a["row_s"] + a["row_n"]) / 2
    xp = (XW + a["x0"]) / 2
    d, s = pool("deep"), pool("seated")
    dx = (d["treads"][0][0] + d["treads"][0][2]) / 2
    yw = COPING_N + 0.45
    r = [
        {
            "id": "A",
            "label": "深い水風呂 → 離れの寝椅子",
            "path": [(dx, COPING_N - 0.15), (dx, yw), (xp, yw), (xp, ya), (a["x0"] + 0.45, ya)],
        },
        {
            "id": "B",
            "label": "座る水風呂 → 離れ",
            "path": [
                (14.2, COPING_N - 0.12),
                (14.2, yw + 0.12),
                (xp + 0.14, yw + 0.12),
                (xp + 0.14, ya + 0.14),
                (a["x0"] + 0.45, ya + 0.14),
            ],
        },
        {
            "id": "C",
            "label": "離れが満席 → 休憩室の扉（同じ通り）",
            "path": [
                (a["x0"] + 0.45, ya - 0.14),
                (xp - 0.14, ya - 0.14),
                (xp - 0.14, 7.55),
                (6.0, 7.55),
                (5.36, 6.55),
            ],
        },
        {
            "id": "D",
            "label": "休憩室も満席 → 予備の腰掛け／造り付け席（v6の経路）",
            "path": [(5.36, 6.55), (6.0, 7.75), (xp, 7.9), (xp, yw - 0.12), (13.4, yw - 0.12)],
        },
    ]
    for x in r:
        x["length_m"] = _len(x["path"])
    return r


def demand():
    main = len(ML.seats())
    pos = checks()["in_water_positions"]["total"]
    rc = rest_count()
    regular = rc["v8"]["rest_room"] + rc["v8"]["built_in_bath_seats"] + rc["v8"]["annex_loungers"]
    guests = 40
    return {
        "pool_positions": pos,
        "pool_positions_usual": checks()["in_water_positions"]["usual"],
        "simple_examples": [
            {
                "case": f"{main}人が5分に分かれて出て1人1分入る",
                "in_water_at_once": round(main * 1 / 5, 1),
                "against_positions": pos,
            },
            {
                "case": f"{main}人が2分に集中して出て1人1分入る",
                "in_water_at_once": round(main * 1 / 2, 1),
                "against_positions": pos,
            },
        ],
        "reading": (
            "単純な割り算の例で、入浴時間の推奨でも実測でもない。5分に分かれれば位置の数に収まるが、2分に集中すると"
            f"{round(main / 2)}人分に対して詰めて{pos}か所（通常5）で、4〜5人分の需要が受けきれない。"
            "通路や縁石に待ち列を作る使い方は想定しない。別途、通路外の待機位置やイベント後の分散を検討する必要がある。"
            "短く入るから無制限に小さくできるわけではない。"
        ),
        "rest_after_event": {
            "seats_total": rc["v8"]["total"],
            "regular_seats": regular,
            "spare_perch": rc["v8"]["spare_perch"],
            "if_the_same_17_others_as_v6": {
                "demand": main + 17,
                "seats": rc["v8"]["total"],
                "short": main + 17 - rc["v8"]["total"],
            },
            "if_all_40_guests_seek_rest": {
                "demand": guests,
                "seats": rc["v8"]["total"],
                "short": guests - rc["v8"]["total"],
            },
            "reading": (
                "v6は休憩できる場所20に対し、既存17人＋イベント20人＝37人で17人不足だった。離れの4席で場所は24になり、同じ17人なら不足は13人。"
                "全館40人の仮定で全員が同時に休憩を求めると16人分不足する。増えた4席も埋まる場合は追加の余裕が無く、"
                "全席が埋まると、水へ戻らずに確実に座れる場所はもう無い（v6と同じ）。"
            ),
        },
        "assumed_guests_in_house": guests,
    }


def options():
    """The two bath arrangements compared before building."""
    inline_block = SCREEN["x1"] - SCREEN["x0"] + 2.2 + 0.30 + 2.0 + 0.30
    inline_west = EAST_COPING[1] - inline_block
    return [
        {
            "name": "A: 長辺を東西に並べる（briefの入口寸法 2.2×1.6 と 2.0×1.5）",
            "adopted": False,
            "surface_m2": round(2.2 * 1.6 + 2.0 * 1.5, 2),
            "block_length_m": round(inline_block, 2),
            "annex_width_m": round(inline_west - ANNEX["x0"], 2),
            "walkway_north_m": round(YN - (6.8 + 1.6 + COPING_W), 3),
            "loungers": 3,
            "why_not": (
                f"浴槽ブロックが東西{inline_block:.2f} mを取り、離れの幅は{inline_west - ANNEX['x0']:.2f} m。寝椅子は足を北に3脚まで"
                "（休憩室と同じ席幅0.70 m・入口幅0.725 mで4脚並べるには4.25 m要る）。通路は0.3 m広がる。"
            ),
        },
        {
            "name": "B: 長辺を南北に向けて東端へ寄せる（採用）",
            "adopted": True,
            "surface_m2": areas()["v8"]["surface_total_m2"],
            "block_length_m": round(EAST_COPING[1] - SCREEN["x0"], 2),
            "annex_width_m": round(ANNEX["x1"] - ANNEX["x0"], 2),
            "walkway_north_m": round(YN - COPING_N, 3),
            "loungers": 4,
            "why": (
                f"浴槽ブロックが{EAST_COPING[1] - SCREEN['x0']:.2f} mに収まり、離れに{ANNEX['x1'] - ANNEX['x0']:.2f}×{ANNEX['y1'] - ANNEX['y0']:.2f} mのまとまった床が残る。"
                f"寝椅子を東西に2列×2脚置け、4脚とも中の通路（幅{clearances()['annex_aisle_between_loungers']:.2f} m）から横に入れる。水風呂前の通路幅はv7のまま。"
            ),
            "cost": "深い槽の奥は幅1.00 m、座る槽は幅1.60 mで、どちらも一列に入る形になる。",
        },
    ]


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            {
                "pools": {k: pool(k) for k in POOLS},
                "checks": checks(),
                "rest": rest_count(),
                "routes": [{k: v for k, v in r.items() if k != "path"} for r in routes()],
                "demand": demand(),
                "options": options(),
            },
            ensure_ascii=False,
            indent=1,
        )
    )
