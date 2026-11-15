"""Rest-area layout (v4) as plain data — no bpy import.

Shared by the Blender builder (room_rest.py) and the sight-line study (scripts/sightline_diagram.py) so the
drawing and the numbers come from the same coordinates as the model. Metres, x east, y north, z up.
Eye heights and view-angle limits are study assumptions, not ergonomic or regulatory values.
"""

import math

H = 2.7
# finished wall faces of the rest area
WEST, NORTH, SOUTH = 0.094, 8.888, 3.694
EAST_MAIN = 5.888  # slatted wall with the bath door (y > 6.42)
EXT_X0, EXT_NORTH, EXT_EAST = 5.92, 6.388, 10.406
DOOR = (7.0, 8.1)  # bath door on the east wall of the main zone (y range)

EYE = {"recline": 0.90, "upright": 1.18, "lying": 0.56, "walk": 1.55}
HB = 1.30  # opaque headboard / wing / waist-wall height for reclined seats
HB_UP = 1.45  # same for upright chairs
LOUNGER_L, LOUNGER_W = 1.80, 0.62
CHAIR_L, CHAIR_W = 0.76, 0.58
EYE_S = {"recline": 1.58, "upright": 0.60, "lying": 1.68}  # eye position measured from the foot end
PLATFORM = {"x0": 0.11, "x1": 4.76, "y_front": 6.918, "y_wall": NORTH, "n": 6, "top": 0.40}
DIV_TALL, DIV_TALL_LEN, DIV_LOW = 1.10, 1.10, 0.62
FOOT_Y, HB_Y0, HB_Y1, WING, DIV_T = 4.00, 5.82, 5.88, 0.55, 0.05
WING_EXT, WING_UP = (
    0.80,
    0.75,
)  # aisle-side wings in the extension (walkers pass in front of these seats)
SEAT_BAY = 0.70  # lounger 0.62 + 2 x 0.02 clearance + 0.04 wing
MAIN_UNITS = ("single", "pair", "pair")
entries = []  # (x0, x1) of the entry gaps in the main-zone headboard line, filled by layout_v4()


def main_entry_width():
    """Clear width of each entry gap so that the single + two pairs + three waist walls fill WEST..EXT_X0."""
    bays = sum(1 if u == "single" else 2 for u in MAIN_UNITS)
    return (EXT_X0 - WEST - bays * SEAT_BAY - len(MAIN_UNITS) * DIV_T) / len(MAIN_UNITS)


def _seat(kind, sid, foot, heading, group):
    hx, hy = heading
    length = {"recline": LOUNGER_L, "upright": CHAIR_L, "lying": 1.97}[kind]
    width = {"recline": LOUNGER_W, "upright": CHAIR_W, "lying": 0.70}[kind]
    s = EYE_S[kind]
    return {
        "id": sid,
        "kind": kind,
        "group": group,
        "foot": foot,
        "heading": heading,
        "length": length,
        "width": width,
        "eye": (foot[0] + hx * s, foot[1] + hy * s, EYE[kind]),
        "facing": (-hx, -hy),
    }


# ---- v5 top-edge shapes ---------------------------------------------------------------------------------
# A partition may carry an "outline": its silhouette as (d, z) points, d = distance from the "root" end along the long
# axis of its rect. The model (furniture.profile_panel), the figure and the sight-line study all read this one polyline.
SOFT = {  # study values in metres; radii differ by role (not one radius everywhere)
    "wing": (
        0.24,
        0.26,
    ),  # head wing of a lounger: level over the head, quarter ellipse (along, down) at the free end
    "waist": (
        0.40,
        0.30,
    ),  # wall between two bays: easier shoulder towards the feet (0.50/0.42 read as a slide)
    "wing_ext": (
        0.18,
        0.16,
    ),  # aisle-side wings in the extension: small, walkers pass right beside the head
    # (0.26/0.26 let three aisle points see the top of a head that v4 hid)
    "div_level": 0.95,  # lying divider: full height for this far from the wall (head and shoulders) ...
    "div_foot": 0.52,  # ... then one straight slope down to this height at the foot end
    "div_r": (0.30, 0.07),  # radius where the slope leaves the level top / at the foot-end nose
}  # a first trial with an S-curve plus a rolled nose on every divider looked like a row of waves; one slope is calmer


def fillet2(pts, radii, n=8):
    """Round the interior corners of a 2D polyline; radii[i] belongs to pts[i + 1]."""
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        p0, p1, p2, r = pts[i - 1], pts[i], pts[i + 1], radii[i - 1]
        d0, d1 = (p0[0] - p1[0], p0[1] - p1[1]), (p2[0] - p1[0], p2[1] - p1[1])
        l0, l1 = math.hypot(*d0), math.hypot(*d1)
        u0, u1 = (d0[0] / l0, d0[1] / l0), (d1[0] / l1, d1[1] / l1)
        ang = math.acos(max(-1.0, min(1.0, u0[0] * u1[0] + u0[1] * u1[1])))
        if r <= 0 or ang > math.pi - 1e-3:
            out.append(p1)
            continue
        t = min(r / math.tan(ang / 2), l0 * 0.49, l1 * 0.49)
        rr = t * math.tan(ang / 2)
        bl = math.hypot(u0[0] + u1[0], u0[1] + u1[1])
        c = (
            p1[0] + (u0[0] + u1[0]) / bl * rr / math.sin(ang / 2),
            p1[1] + (u0[1] + u1[1]) / bl * rr / math.sin(ang / 2),
        )
        a0 = math.atan2(p1[1] + u0[1] * t - c[1], p1[0] + u0[0] * t - c[0])
        a1 = math.atan2(p1[1] + u1[1] * t - c[1], p1[0] + u1[0] * t - c[0])
        sweep = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        out += [
            (c[0] + rr * math.cos(a0 + sweep * k / n), c[1] + rr * math.sin(a0 + sweep * k / n))
            for k in range(n + 1)
        ]
    out.append(pts[-1])
    return out


def shoulder(length, z1, a, b, n=14):
    """Level top, then a quarter ellipse (a along, b down) that ends vertical at the tip. Returns (d, z) from the root."""
    a = min(a, length)
    pts = [(0.0, z1)]
    for k in range(n + 1):
        t = math.pi / 2 * k / n
        pts.append((length - a + a * math.sin(t), z1 - b + b * math.cos(t)))
    return pts


def ease(d1, d2, z_hi, z_lo, n=14):
    """S-curve (smoothstep) from z_hi at d1 to z_lo at d2, horizontal at both ends."""
    out = []
    for k in range(n + 1):
        u = k / n
        out.append((d1 + (d2 - d1) * u, z_hi - (z_hi - z_lo) * (3 * u * u - 2 * u**3)))
    return out


def top_at(p, d_start):
    """Silhouette height of a partition at distance d_start from the start (x0 or y0) of its long axis."""
    if "outline" not in p:
        return p["z"][1]
    x0, y0, x1, y1 = p["rect"]
    length = max(x1 - x0, y1 - y0)
    d = length - d_start if p["root"] == "end" else d_start
    pts = p["outline"]
    if d <= pts[0][0]:
        return pts[0][1]
    for (da, za), (db, zb) in zip(pts, pts[1:]):
        if da <= d <= db and db > da:
            return za + (zb - za) * (d - da) / (db - da)
    return pts[-1][1]


def layout_v4():
    return _layout(soft=False)


def layout_v5():
    """v4 arrangement with eased top edges on the partitions (no seat, aisle or entry dimension changes)."""
    return _layout(soft=True)


def _layout(soft):
    seats, parts, toes = [], [], []
    pegs = []  # v6: one towel peg per seat on the aisle face of its shelter (x, y, outward direction) — "in use" cue

    def panel(label, x0, y0, x1, y1, z0, z1, outline=None, root="end"):
        p = {"kind": "panel", "label": label, "rect": (x0, y0, x1, y1), "z": (z0, z1)}
        if soft and outline:
            p["outline"], p["root"] = outline, root
        parts.append(p)

    def fins(label, x0, y0, x1, y1, z0, z1):
        parts.append({"kind": "fins", "label": label, "rect": (x0, y0, x1, y1), "z": (z0, z1)})

    # --- lying platforms: heads at the north wall, stepped dividers, screened east end ---------------------
    pl = PLATFORM
    pitch = (pl["x1"] - pl["x0"]) / pl["n"]
    for k in range(pl["n"]):
        seats.append(
            _seat(
                "lying",
                f"L{k + 1}",
                (pl["x0"] + (k + 0.5) * pitch, pl["y_front"]),
                (0, 1),
                "寝台（頭を壁側）",
            )
        )
    div_len = pl["y_wall"] - (pl["y_front"] + 0.25)
    div_line = fillet2(
        [
            (0.0, DIV_TALL),
            (SOFT["div_level"], DIV_TALL),
            (div_len, SOFT["div_foot"]),
            (div_len, pl["top"]),
        ],
        SOFT["div_r"],
    )
    for k in range(1, pl["n"]):
        x = pl["x0"] + k * pitch
        if soft:  # one piece: full height beside head and shoulders, then a single slope down to the foot end
            panel(
                "寝台の仕切り",
                x - 0.015,
                pl["y_front"] + 0.25,
                x + 0.015,
                pl["y_wall"],
                0.10,
                DIV_TALL,
                div_line,
            )
            continue
        panel(
            "寝台の仕切り（頭側）",
            x - 0.015,
            pl["y_wall"] - DIV_TALL_LEN,
            x + 0.015,
            pl["y_wall"],
            0.10,
            DIV_TALL,
        )
        panel(
            "寝台の仕切り（足側）",
            x - 0.015,
            pl["y_front"] + 0.25,
            x + 0.015,
            pl["y_wall"] - DIV_TALL_LEN,
            0.10,
            DIV_LOW,
        )
    xe = pl["x1"] + 0.005
    panel("寝台東端の腰壁", xe, pl["y_front"], xe + DIV_T, pl["y_wall"], 0.0, HB)
    fins("寝台東端の格子", xe, pl["y_front"], xe + DIV_T, pl["y_wall"], HB, H + 0.02)

    # --- main zone: five loungers facing the south wall (one single + two pairs), entered from behind ---------
    # Each entry is a gap in the headboard line; a pair shares one. Entry width is solved so the row fills the wall.
    entry = main_entry_width()
    entries.clear()
    xs, n = WEST, 0
    for unit in MAIN_UNITS:
        if unit == "single":  # lounger against the west wall, entry on its east side
            n += 1
            seats.append(
                _seat("recline", f"R{n}", (xs + 0.33, FOOT_Y), (0, 1), "壁向きリクライニング")
            )
            heads = [(xs, xs + SEAT_BAY)]
            wings = [xs + SEAT_BAY - 0.04]
            entries.append((xs + SEAT_BAY, xs + SEAT_BAY + entry))
            end = xs + SEAT_BAY + entry
        else:  # two loungers sharing the entry between them
            width = 2 * SEAT_BAY + entry
            for cx in (xs + 0.33, xs + width - 0.33):
                n += 1
                seats.append(
                    _seat("recline", f"R{n}", (cx, FOOT_Y), (0, 1), "壁向きリクライニング")
                )
            heads = [(xs - DIV_T, xs + SEAT_BAY), (xs + width - SEAT_BAY, xs + width)]
            wings = [xs + SEAT_BAY - 0.04, xs + width - SEAT_BAY]
            entries.append((xs + SEAT_BAY, xs + width - SEAT_BAY))
            end = xs + width
        for h0, h1 in heads:
            panel("ヘッドボード", h0, HB_Y0, h1, HB_Y1, 0.08, HB)
            pegs.append(((h0 + h1) / 2, HB_Y1, (0, 1)))
            toes.append((h0 + 0.03, HB_Y1 - 0.024, h1 - 0.03, HB_Y1 - 0.006, 0.076))
        for wx in wings:
            panel(
                "袖壁",
                wx,
                HB_Y0 - WING,
                wx + 0.04,
                HB_Y0,
                0.0,
                HB,
                shoulder(WING, HB, *SOFT["wing"]),
            )
        panel(
            "腰壁",
            end,
            4.55,
            end + DIV_T,
            HB_Y0,
            0.0,
            HB,
            shoulder(HB_Y0 - 4.55, HB, *SOFT["waist"]),
        )
        xs = end + DIV_T
    panel("ヘッドボード", xs - DIV_T, HB_Y0, xs, HB_Y1, 0.0, HB)  # closes the east end of the row

    # --- extension: two files facing east (same direction), aisle between them ------------------------------
    yc = SOUTH + 0.05 + LOUNGER_W / 2
    for i, hx0 in enumerate((6.02, 8.20)):
        seats.append(
            _seat("recline", f"R{6 + i}", (hx0 + 0.08 + LOUNGER_L, yc), (-1, 0), "同方向の縦列")
        )
        panel("ヘッドボード", hx0, SOUTH, hx0 + 0.06, yc + 0.37, 0.08, HB)
        panel(
            "袖壁",
            hx0 + 0.06,
            yc + 0.33,
            hx0 + 0.06 + WING_EXT,
            yc + 0.37,
            0.0,
            HB,
            shoulder(WING_EXT, HB, *SOFT["wing_ext"]),
            "start",
        )
        pegs.append((hx0 + 0.20, yc + 0.37, (0, 1)))
        if i == 0:
            fins("ヘッドボード上の格子", hx0, SOUTH, hx0 + 0.06, yc + 0.37, HB, H + 0.02)
            toes.append((hx0 + 0.006, SOUTH + 0.04, hx0 + 0.024, yc + 0.34, 0.076))
    yn = EXT_NORTH - 0.05 - CHAIR_W / 2
    for i, hx0 in enumerate((6.95, 8.55)):
        seats.append(
            _seat("upright", f"U{i + 1}", (hx0 + 0.08 + CHAIR_L, yn), (-1, 0), "同方向の縦列")
        )
        panel("ヘッドボード（高）", hx0, yn - 0.35, hx0 + 0.06, EXT_NORTH, 0.08, HB_UP)
        panel(
            "袖壁（高）",
            hx0 + 0.06,
            yn - 0.35,
            hx0 + 0.06 + WING_UP,
            yn - 0.31,
            0.0,
            HB_UP,
            shoulder(WING_UP, HB_UP, *SOFT["wing_ext"]),
            "start",
        )
        pegs.append((hx0 + 0.20, yn - 0.35, (0, -1)))
        if i == 0:
            fins("ヘッドボード上の格子", hx0, yn - 0.35, hx0 + 0.06, EXT_NORTH, HB_UP, H + 0.02)
            toes.append((hx0 + 0.006, yn - 0.32, hx0 + 0.024, EXT_NORTH - 0.04, 0.076))

    walls = [  # full-height walls inside the study area (the glazed door is treated as open)
        {"kind": "wall", "label": "壁", "rect": (EAST_MAIN, 6.42, 6.08, DOOR[0]), "z": (0.0, 3.0)},
        {"kind": "wall", "label": "壁", "rect": (EAST_MAIN, DOOR[1], 6.08, 9.0), "z": (0.0, 3.0)},
        {"kind": "wall", "label": "壁", "rect": (EXT_X0, EXT_NORTH, 10.5, 6.58), "z": (0.0, 3.0)},
    ]
    aisles = [
        {"name": "主通路", "rect": (WEST, HB_Y1, EXT_X0, pl["y_front"])},
        {"name": "扉前", "rect": (xe + DIV_T, pl["y_front"], EAST_MAIN, NORTH)},
        {"name": "合流", "rect": (EXT_X0, yc + 0.37, 6.95, EXT_NORTH)},
        {"name": "延長通路", "rect": (6.95, yc + 0.37, EXT_EAST, yn - 0.35)},
    ]
    walk = (
        [(0.4 + 0.25 * i, 6.40) for i in range(22)]
        + [(5.36, 6.9 + 0.25 * i) for i in range(8)]
        + [(6.45, 4.7 + 0.25 * i) for i in range(7)]
        + [(6.9 + 0.25 * i, 5.06) for i in range(14)]
    )
    return {
        "version": "v5" if soft else "v4",
        "seats": seats,
        "partitions": parts,
        "walls": walls,
        "aisles": aisles,
        "walk": walk,
        "toe_lights": toes,
        "pegs": pegs,
        "outline": [
            (WEST, SOUTH),
            (EXT_EAST, SOUTH),
            (EXT_EAST, EXT_NORTH),
            (EAST_MAIN, EXT_NORTH),
            (EAST_MAIN, NORTH),
            (WEST, NORTH),
        ],
    }


def layout_v3():
    """The accepted v3 arrangement, reconstructed from the v3 source for comparison only."""
    seats, parts = [], []
    for k in range(6):
        seats.append(_seat("lying", f"L{k + 1}", (0.25 + (k + 0.5) * 0.76, 6.858), (0, 1), "寝台"))
    for i, cx in enumerate((0.90, 1.70, 2.75, 3.55, 4.60, 5.40)):
        seats.append(
            _seat("recline", f"R{i + 1}", (cx, 5.74), (0, -1), "リクライニング（通路向き）")
        )
    for sx in (2.225, 4.075, 5.93):
        parts.append(
            {
                "kind": "fins",
                "label": "木フィン",
                "rect": (sx - 0.055, 3.754, sx + 0.055, 4.754),
                "z": (0.0, H),
            }
        )
    for i, cx in enumerate((6.55, 7.35, 8.15, 8.95, 9.75)):
        seats.append(_seat("upright", f"U{i + 1}", (cx, 4.50), (0, -1), "背付き椅子（南列）"))
        seats.append(_seat("upright", f"U{i + 6}", (cx, 5.60), (0, 1), "背付き椅子（北列）"))
    lay = layout_v4()
    walk = (
        [(0.4 + 0.25 * i, 6.30) for i in range(22)]
        + [(5.36, 6.9 + 0.25 * i) for i in range(8)]
        + [(6.3 + 0.25 * i, 5.05) for i in range(16)]
    )
    return {
        "version": "v3",
        "seats": seats,
        "partitions": parts,
        "walls": lay["walls"],
        "aisles": [],
        "walk": walk,
        "toe_lights": [],
        "outline": lay["outline"],
    }


# ---- sight-line study ------------------------------------------------------------------------------------
def _clip(ax, ay, bx, by, rect):
    """Parameter range (t0, t1) of segment A->B inside an axis-aligned rect, or None."""
    x0, y0, x1, y1 = rect
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    t0, t1 = 0.0, 1.0
    for p, q in (
        (-(bx - ax), ax - x0),
        (bx - ax, x1 - ax),
        (-(by - ay), ay - y0),
        (by - ay, y1 - ay),
    ):
        if abs(p) < 1e-12:
            if q < 0:
                return None
        else:
            r = q / p
            if p < 0:
                t0 = max(t0, r)
            else:
                t1 = min(t1, r)
    return (t0, t1) if t0 < t1 else None


def line_state(lay, a, b, skip=()):
    """'blocked' if an opaque partition or wall cuts the 3D line a->b, 'filtered' if only fin screens do, else 'open'."""
    state = "open"
    for p in lay["partitions"] + lay["walls"]:
        if id(p) in skip:
            continue
        hit = _clip(a[0], a[1], b[0], b[1], p["rect"])
        if not hit:
            continue
        za, zb = a[2] + hit[0] * (b[2] - a[2]), a[2] + hit[1] * (b[2] - a[2])
        if (
            "outline" in p
        ):  # shaped top: test the line against the real silhouette where it crosses the panel
            x0, y0, x1, y1 = p["rect"]
            along_x = (x1 - x0) >= (y1 - y0)
            cut = False
            for k in range(5):
                t = hit[0] + (hit[1] - hit[0]) * k / 4
                d = (a[0] + t * (b[0] - a[0]) - x0) if along_x else (a[1] + t * (b[1] - a[1]) - y0)
                z = a[2] + t * (b[2] - a[2])
                if p["z"][0] <= z <= top_at(p, d):
                    cut = True
                    break
            if not cut:
                continue
        elif max(za, zb) < p["z"][0] or min(za, zb) > p["z"][1]:
            continue
        if p["kind"] == "fins":
            state = "filtered"
        else:
            return "blocked"
    return state


def _angle(facing, frm, to):
    dx, dy = to[0] - frm[0], to[1] - frm[1]
    d = math.hypot(dx, dy)
    if d < 1e-9:
        return 0.0
    c = (facing[0] * dx + facing[1] * dy) / d
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


GAZE_CONE = 60.0  # both people within this angle of each other's straight-ahead -> eyes can meet without turning
LOOK_LIMIT = 100.0  # how far a viewer is assumed to look sideways (head + eyes)
FACE_LIMIT = (
    80.0  # a face is readable when the viewer is within this angle of the subject's straight-ahead
)
RANGE = 8.0


def study(lay, state=None):
    """Count seat-to-seat and aisle-to-seat face sight lines. Lying people: face treated as visible from any side.

    state(lay, a, b) may replace the analytic line_state, e.g. a ray cast against the built mesh (blender/verify_sight.py)."""
    line_state = state or globals()["line_state"]
    seats = lay["seats"]
    mutual, faces, filtered = [], [], []
    for i, a in enumerate(seats):
        for j, b in enumerate(seats):
            if i == j:
                continue
            d = math.hypot(a["eye"][0] - b["eye"][0], a["eye"][1] - b["eye"][1])
            if d > RANGE:
                continue
            ang_a = _angle(a["facing"], a["eye"], b["eye"])
            ang_b = _angle(b["facing"], b["eye"], a["eye"])
            st = line_state(lay, a["eye"], b["eye"])
            if st == "blocked":
                continue
            a_looks = (
                ang_a <= LOOK_LIMIT and a["kind"] != "lying"
            )  # a lying person looks at the ceiling
            b_face = b["kind"] == "lying" or ang_b <= FACE_LIMIT
            if a_looks and b_face:
                (faces if st == "open" else filtered).append((a["id"], b["id"], round(d, 2)))
            if (
                i < j
                and st == "open"
                and ang_a <= GAZE_CONE
                and ang_b <= GAZE_CONE
                and "lying" not in (a["kind"], b["kind"])
            ):
                mutual.append((a["id"], b["id"], round(d, 2)))
    exposure = {}
    for s in seats:
        seen = 0
        for wx, wy in lay["walk"]:
            w = (wx, wy, EYE["walk"])
            if math.hypot(wx - s["eye"][0], wy - s["eye"][1]) > RANGE:
                continue
            if s["kind"] != "lying" and _angle(s["facing"], s["eye"], w) > FACE_LIMIT:
                continue
            if line_state(lay, w, s["eye"]) == "open":
                seen += 1
        exposure[s["id"]] = round(100.0 * seen / len(lay["walk"]), 1)
    kinds = {}
    for s in seats:
        kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
    seated = [v for k, v in exposure.items() if not k.startswith("L")]
    lying = [v for k, v in exposure.items() if k.startswith("L")]
    return {
        "version": lay["version"],
        "seats": len(seats),
        "by_kind": kinds,
        "mutual_gaze_pairs": len(mutual),
        "mutual_gaze_list": mutual,
        "face_sightlines_open": len(faces),
        "face_sightlines_filtered": len(filtered),
        "face_list": faces,
        "aisle_exposure_pct": exposure,
        "aisle_exposure_seated_mean": round(sum(seated) / len(seated), 1) if seated else 0.0,
        "aisle_exposure_seated_max": max(seated) if seated else 0.0,
        "aisle_exposure_lying_mean": round(sum(lying) / len(lying), 1) if lying else 0.0,
        "aisle_exposure_lying_max": max(lying) if lying else 0.0,
        "assumptions": {
            "eye_height_m": EYE,
            "gaze_cone_deg": GAZE_CONE,
            "look_limit_deg": LOOK_LIMIT,
            "face_limit_deg": FACE_LIMIT,
            "range_m": RANGE,
            "walk_points": len(lay["walk"]),
            "note": "fin screens count as 'filtered', glazed door as open; people are points at eye position",
        },
    }


def checks():
    """Clearances of the v4 layout in metres (study values, not code compliance)."""
    pl = PLATFORM
    e = main_entry_width()
    yc = SOUTH + 0.05 + LOUNGER_W / 2
    yn = EXT_NORTH - 0.05 - CHAIR_W / 2
    return {
        "main_aisle_width": round(pl["y_front"] - HB_Y1, 3),
        "door_landing_width": round(EAST_MAIN - (pl["x1"] + 0.005 + DIV_T), 3),
        "main_entry_width": round(e, 3),  # gap in the headboard line, between wings
        "main_entry_between_loungers": round(
            e + 0.12, 3
        ),  # floor between the two lounger edges of a pair
        "main_entry_passage_length": WING,  # the narrow part is only as long as the wings
        "lounger_open_side_beyond_wing": round(
            HB_Y0 - WING - FOOT_Y, 3
        ),  # length of lounger side free for sitting down
        "extension_lounger_open_side": round(LOUNGER_L + 0.02 - WING_EXT, 3),
        "extension_chair_front_zone": round(
            1.60 - 0.08 - CHAIR_L, 3
        ),  # legroom zone in front of an upright chair
        "extension_aisle_width": round((yn - 0.35) - (yc + 0.37), 3),
        "junction_width": round(6.95 - EXT_X0, 3),
        "lounger_foot_to_south_wall": round(FOOT_Y - SOUTH, 3),
        "lying_pitch": round((pl["x1"] - pl["x0"]) / pl["n"], 3),
        "feet_projecting_into_aisle": 0.0,
    }


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            {
                "v3": study(layout_v3()),
                "v4": study(layout_v4()),
                "v5": study(layout_v5()),
                "checks": checks(),
            },
            ensure_ascii=False,
            indent=1,
        )
    )
