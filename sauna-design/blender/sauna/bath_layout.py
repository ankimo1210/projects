"""Where to go when the rest area is full (v6) — plain data, no bpy import.

Three spare perch seats are built into the recess that held the fin screen in front of the carbonated-pool alcove
(north side of the bath walkway, opposite the seated cold pool). The seat stays behind the wall line; only the legs of a
seated person reach into the walkway. Shared by room_water.py, scripts/overflow_diagram.py and blender/verify_main.py.

v8 note: the cold pools moved and shrank (water_layout.py). PERCH, BUILT_IN, perch_seats() and built_in_seats() are still
what the model is built from; POOL_EXIT, LEDGE, the pool-step distances in clearances(), gaze(), routes(), search_walk()
and scenarios() describe the v6 / v7 pools and are kept only so the v6 figures can be regenerated. For v8 use
water_layout.clearances() / routes() / demand().

Capacity figures and routes are a concept study with assumed adult body sizes. They do not promise that everyone can
rest at once; event size, entry control and how people actually behave are operational matters outside this model.
"""

import math

from . import main_layout as ML
from . import rest_layout as RL

# bath walkway north of the two cold pools
COPING_N = 9.0  # north edge of the pool copings (raised 12 mm)
NORTH_FACE = 10.388  # finished face of the timber north wall = front of the recess
PERCH = {
    "x0": 12.62,
    "x1": 15.00,
    "y_front": NORTH_FACE,
    "y_back": 10.80,
    "seats": 3,
    "wing_t": 0.08,
    "wing_h": 1.50,
    "wing_round": (0.20, 0.30),
    "seat_top": 0.432,
    "back_t": 0.04,
    "pad_t": 0.02,
    "back_h": 1.10,
    "slot": 0.03,
}  # a first trial with head-high dividers between the seats read as a row of headstones; dropped
BUILT_IN = {
    "xf": 16.906,
    "y0": 8.40,
    "y1": 10.30,
    "seats": 2,
    "nose": 0.57,
}  # the two v4 seats on the east wall (unchanged)
REST_DOOR = (6.0, 7.55)  # middle of the glazed door between bath and rest
JUNCTION = (
    5.36,
    6.55,
)  # one step inside the rest door: where the main aisle and the extension meet
POOL_EXIT = {"deep": (7.55, 9.15), "seated": (11.75, 9.15)}
LEDGE = [
    (12.45 + 0.6 * k, 7.0) for k in range(4)
]  # people sitting on the underwater ledge of the seated pool, facing north
EYE = {"perch": 1.18, "built_in": 1.18, "ledge": 0.35}


def perch_seats():
    p = PERCH
    a, b = p["x0"] + p["wing_t"], p["x1"] - p["wing_t"]
    w = (b - a - p["slot"] * (p["seats"] - 1)) / p["seats"]
    yb = p["y_back"] - p["back_t"] - p["pad_t"]
    return [
        {
            "id": f"P{k + 1}",
            "tier": "perch",
            "b": (round(a + k * (w + p["slot"]) + w / 2, 4), round(yb, 4)),
            "f": (0, -1),
            "pitch": round(w, 4),
            "seat_z": p["seat_top"],
            "foot_z": 0.0,
            "posture": "legs_down",
            "backrest": True,
        }
        for k in range(p["seats"])
    ]


def built_in_seats():
    b = BUILT_IN
    a, c = b["y0"] + 0.07, b["y1"] - 0.07
    w = (c - a - 0.03) / 2
    return [
        {
            "id": f"B{k + 1}",
            "tier": "built_in",
            "b": (b["xf"] - 0.14, round(a + k * (w + 0.03) + w / 2, 4)),
            "f": (-1, 0),
            "pitch": round(w, 4),
            "seat_z": 0.432,
            "foot_z": 0.0,
            "posture": "legs_down",
            "backrest": True,
        }
        for k in range(2)
    ]


def _toes(s):
    return [p for p in ML.body_boxes(s) if p[0] == "feet"][0]


def clearances():
    p = PERCH
    toes_y = min(_toes(s)[2] for s in perch_seats())
    toes_x = min(_toes(s)[1] for s in built_in_seats())
    feet_w = min(_toes(s)[1] for s in perch_seats())  # west edge of the westernmost pair of feet
    feet_e = max(_toes(s)[3] for s in perch_seats())
    steps_e = 12.2  # east end of the seated-pool entry steps (x 11.3..12.2 at y = 9.0)
    return {
        "walkway_two_people_passing": "足先まで1.02 mは1人が通る幅。すれ違いは片方が待つか、12 mm高い縁石（幅0.30 m・滑りは未検証）に寄る",
        "seated_pool_steps_to_nearest_feet": round(
            math.hypot(feet_w - steps_e, toes_y - COPING_N), 3
        ),
        "seated_pool_handrail_to_nearest_feet": round(math.hypot(feet_w - 12.26, toes_y - 8.84), 3),
        "nearest_feet_to_carbon_opening_edge": round(15.0 - feet_e, 3),
        "walk_past_three_pairs_of_feet_length": round(feet_e - feet_w, 3),
        "walkway_width_v5": round(NORTH_FACE - COPING_N, 3),
        "walkway_width_seats_empty": round(p["y_front"] - COPING_N, 3),
        "walkway_width_seats_occupied": round(toes_y - COPING_N, 3),
        "legs_reach_into_walkway": round(p["y_front"] - toes_y, 3),
        "seat_projection_beyond_wall_line": round(NORTH_FACE - p["y_front"], 3),
        "seat_depth": round(p["y_back"] - p["back_t"] - p["pad_t"] - p["y_front"], 3),
        "seat_pitch": perch_seats()[0]["pitch"],
        "west_end_to_dry_sauna_door": round(p["x0"] - 11.2, 3),
        "west_end_to_seated_pool_steps": round(p["x0"] - 12.2, 3),
        "east_end_to_carbon_opening": round(15.0 - p["x1"], 3),
        "carbon_opening_width": 1.9,
        "east_zone_width_past_built_in_legs": round(toes_x - 14.8, 3),
        "nearest_staff_door": "東壁 y=11.5〜12.4（炭酸泉の奥）と y=5.3〜6.2（洗い場）。どちらも席の前を通らない",
    }


def _angle(facing, frm, to):
    dx, dy = to[0] - frm[0], to[1] - frm[1]
    d = math.hypot(dx, dy)
    c = (facing[0] * dx + facing[1] * dy) / d
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def perch_panels():
    """The two end wings of the perch as plan rects (1.20 m at the front tip, 1.50 m behind: above a seated eye)."""
    p = PERCH
    return [
        (p["x0"], p["y_front"], p["x0"] + p["wing_t"], p["y_back"]),
        (p["x1"] - p["wing_t"], p["y_front"], p["x1"], p["y_back"]),
    ]


def gaze():
    """Who faces whom (same 60 degree cone as the rest study); the two perch end wings are the only screens here."""
    panels = perch_panels()
    pts = [
        {"id": s["id"], "kind": "perch", "eye": (s["b"][0], s["b"][1] - 0.13), "f": s["f"]}
        for s in perch_seats()
    ]
    pts += [
        {"id": s["id"], "kind": "built_in", "eye": (s["b"][0] - 0.13, s["b"][1]), "f": s["f"]}
        for s in built_in_seats()
    ]
    pts += [
        {"id": f"ledge{k + 1}", "kind": "ledge", "eye": q, "f": (0, 1)} for k, q in enumerate(LEDGE)
    ]
    pairs = {"perch-perch": [], "perch-built_in": [], "perch-ledge": []}
    for i, a in enumerate(pts):
        for b in pts[i + 1 :]:
            key = (
                "-".join(
                    sorted(
                        {a["kind"], b["kind"]},
                        key=lambda k: ["perch", "built_in", "ledge"].index(k),
                    )
                )
                if a["kind"] != b["kind"]
                else f"{a['kind']}-{a['kind']}"
            )
            if key not in pairs:
                continue
            aa, ab = _angle(a["f"], a["eye"], b["eye"]), _angle(b["f"], b["eye"], a["eye"])
            if any(RL._clip(a["eye"][0], a["eye"][1], b["eye"][0], b["eye"][1], q) for q in panels):
                continue
            if aa <= RL.GAZE_CONE and ab <= RL.GAZE_CONE:
                pairs[key].append(
                    [
                        a["id"],
                        b["id"],
                        round(math.hypot(a["eye"][0] - b["eye"][0], a["eye"][1] - b["eye"][1]), 2),
                        round(aa),
                        round(ab),
                    ]
                )
    return pairs


def _len(path):
    return round(sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:])), 1)


def routes():
    """Walking lines used in the figure (plan polylines) with their lengths."""
    px = (PERCH["x0"] + PERCH["x1"]) / 2
    toes = min(_toes(s)[2] for s in perch_seats())
    yw = (
        COPING_N + toes
    ) / 2  # middle of what is left of the walkway when all three seats are taken
    stop = toes - 0.12  # walking lines stop short of the feet; nobody walks through them
    # the three lines through the door are drawn 0.12-0.18 m apart so they can be told apart; they are the same walk
    r = [
        {
            "id": "A",
            "label": "深い水風呂 → 休憩の扉 → 合流点で空席を確認",
            "path": [POOL_EXIT["deep"], (6.62, 9.15), (6.62, 7.30), (6.0, 7.30), JUNCTION],
        },
        {
            "id": "B",
            "label": "満席 → 同じ扉から浴室へ戻り、予備の腰掛けへ",
            "path": [
                JUNCTION,
                REST_DOOR,
                (6.44, 7.55),
                (6.44, yw - 0.1),
                (px - 0.2, yw - 0.1),
                (px - 0.2, stop),
            ],
        },
        {
            "id": "C",
            "label": "座る水風呂 → 予備の腰掛け（扉へ寄らない場合）",
            "path": [POOL_EXIT["seated"], (12.45, yw - 0.1), (px - 0.75, stop)],
        },
        {
            "id": "D",
            "label": "席が空いたら予備の腰掛け → 休憩へ",
            "path": [
                (px + 0.2, stop),
                (px + 0.2, yw + 0.1),
                (6.26, yw + 0.1),
                (6.26, 7.80),
                (6.0, 7.80),
                JUNCTION,
            ],
        },
        {
            "id": "E",
            "label": "造り付け席（v4の2席）へ",
            "path": [(px + 0.4, yw - 0.1), (15.35, yw - 0.1), (15.85, 9.35)],
        },
    ]
    for x in r:
        x["length_m"] = _len(x["path"])
    return r


def search_walk():
    """How far someone walks inside the rest area to learn that it is full, with and without the towel pegs at each entry."""
    main_west = RL.WEST + 0.9  # far enough to look into the single bay at the west wall
    ext_east = 8.6  # far enough to see the second lounger and chair of the extension
    without = 2 * (JUNCTION[0] - main_west) + 2 * (ext_east - RL.EXT_X0)
    return {
        "door_to_junction_m": round(
            math.hypot(REST_DOOR[0] - JUNCTION[0], REST_DOOR[1] - JUNCTION[1]), 1
        ),
        "inside_walk_without_cue_m": round(without, 1),
        "inside_walk_if_every_peg_is_used_m": 0.0,
        "peg_limits": "タオル掛けは利用者の協力が前提の目印。掛け忘れ・掛けたままの離席があり得るので、空席を自動で判定する設備でも、探さずに済むことの保証でもない。",
        "dead_ends": ["主通路の西端", "延長通路の東端"],
        "second_exit": "無し（出入りは浴室側の扉1か所。回遊にはならない）",
    }


def scenarios():
    rest, built, perch = len(RL.layout_v5()["seats"]), BUILT_IN["seats"], PERCH["seats"]
    main = len(ML.seats())
    total = rest + built + perch
    return {
        "places_out_of_water": {"rest": rest, "built_in": built, "perch": perch, "total": total},
        "assumed_guests_in_house": 40,
        "1_normal_full": f"休憩{rest}＋造り付け{built}が埋まった状態で1〜{perch}人が水風呂を出る → 予備の腰掛け{perch}席で受けられる。",
        "2_after_event": (
            f"メインの{main}人が同時に出ると、汗流し2基と水風呂2槽で時間差はつくが、数分のうちに{main}人前後が座る場所を求める。"
            f"その時点で休憩{rest}＋造り付け{built}＝{rest + built}席が他の客で埋まっていれば、需要は{main}＋{rest + built}＝{main + rest + built}人、"
            f"水から出て座れる場所は{total}。不足は{main + rest + built - total}人。全席が空いていた場合だけ{main}人を受けられる。"
        ),
        "3_all_full": (
            f"予備まで{total}席すべて埋まると、このモデルには、水へ戻らずに確実に座れる場所がもう無い。"
            "浴槽のへり・洗い場の椅子・立って待つことは解決策として勧めない（実際に起きることとして記すだけ）。"
        ),
        "solved_by_this_change": f"平常時に満席へ当たった1〜{perch}人が、通路に立たずに座れる場所と、そこから休憩へ戻る道。",
        "still_open": (
            f"館内{40}人という仮定に対して休む場所は{total}。イベント{main}人と既存の利用が重なる場面は席が足りない。"
            "席を増やす・配置を変える・イベントの定員や入場数を席数に合わせる、のどれを取るかは事業計画側へ持ち越す課題で、今回の局所変更では解いていない。"
        ),
        "not_claimed": "40人全員が同時に休めるとは言えない。予備3席は平常時の数人分の受け皿で、同時集中は保証しない。",
    }


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            {
                "perch": perch_seats(),
                "clearances": clearances(),
                "gaze": gaze(),
                "routes": [{k: v for k, v in r.items() if k != "path"} for r in routes()],
                "search": search_walk(),
                "scenarios": scenarios(),
            },
            ensure_ascii=False,
            indent=1,
        )
    )
