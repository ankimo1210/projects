#!/usr/bin/env python3
"""Where people go when the rest area is full (v6): plan of rest + bath with the routes, the spare perch seats, the widths
with knees and feet, and the three load cases. Reads blender/sauna/bath_layout.py, rest_layout.py and plan/plan_a.json —
the data the model is built from — and writes

  <data-root>/diagrams/rest_full_routes_v6.png
  <data-root>/verification/rest_full_study.json

A concept study with assumed adult sizes. It does not promise that everyone can rest at once.
"""

import sys

sys.dont_write_bytecode = True
import json  # noqa: E402
import pathlib  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, Polygon, Rectangle  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "blender"))
sys.path.insert(0, str(HERE / "scripts"))
from main_diagram import dim, note, wrap  # noqa: E402
from sauna import bath_layout as BL  # noqa: E402
from sauna import main_layout as ML
from sauna import rest_layout as RL

V = "v6"
DATA = (
    pathlib.Path(sys.argv[1])
    if len(sys.argv) > 1
    else pathlib.Path(f"/home/kazumasa/projects/_data/sauna-design/fable-{V}")
)
INK, MUTE, PAPER = "#2a2520", "#8a8178", "#f6f2ea"
ROUTE = {"A": "#2a67ad", "B": "#b4442f", "C": "#1f7f79", "D": "#7a4fa3", "E": "#8a7a2a"}
plan = json.loads((HERE / "plan" / "plan_a.json").read_text(encoding="utf-8"))


def seat_poly(s):
    hx, hy = s["heading"]
    lx, ly = hy, -hx
    fx, fy = s["foot"]
    w, ln = s["width"] / 2, s["length"]
    return [
        (fx - lx * w, fy - ly * w),
        (fx + lx * w, fy + ly * w),
        (fx + lx * w + hx * ln, fy + ly * w + hy * ln),
        (fx - lx * w + hx * ln, fy - ly * w + hy * ln),
    ]


def body(ax, s, z=9):
    for part, x0, y0, x1, y1, z0, z1 in ML.body_boxes(s):
        if part == "thighs":
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#b99578", ec="none", zorder=z))
        elif part == "feet":
            ax.add_patch(
                Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#3f3129", ec="none", zorder=z + 1)
            )
        elif part == "torso":
            ax.add_patch(
                Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#7b5d47", ec="none", zorder=z + 2)
            )
        elif part == "head":
            ax.add_patch(
                Ellipse(
                    ((x0 + x1) / 2, (y0 + y1) / 2),
                    x1 - x0,
                    y1 - y0,
                    fc="#f2e3cf",
                    ec="#7b5d47",
                    lw=0.8,
                    zorder=z + 3,
                )
            )


def route(ax, r):
    c = ROUTE[r["id"]]
    pts = r["path"]
    for a, b in zip(pts, pts[1:-1]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color=c, lw=2.6, zorder=16, solid_capstyle="round")
    ax.add_patch(
        FancyArrowPatch(
            pts[-2], pts[-1], arrowstyle="-|>", mutation_scale=16, color=c, lw=2.6, zorder=16
        )
    )


def badge(ax, xy, text, colour):
    ax.text(
        xy[0],
        xy[1],
        text,
        fontsize=11,
        color="#fffdf8",
        weight="bold",
        ha="center",
        va="center",
        zorder=24,
        bbox=dict(boxstyle="circle,pad=0.25", fc=colour, ec="none"),
    )


def draw(ax, lay):
    ax.set_facecolor(PAPER)
    P = BL.PERCH
    rooms = {r["id"]: r["rect"] for r in plan["rooms"]}
    # floors
    ax.add_patch(Polygon(lay["outline"], closed=True, fc="#fffdf8", ec=INK, lw=2.2, zorder=1))
    for x0, y0, x1, y1 in (
        (6.112, 6.594, 16.906, BL.NORTH_FACE),
        (10.594, 3.694, 16.906, 6.406),
        (14.994, 6.406, 16.906, 6.594),
        (15.0, BL.NORTH_FACE, 16.906, 11.15),
        (P["x0"], BL.NORTH_FACE, P["x1"], P["y_back"]),
    ):
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#f4f6f5", ec="none", zorder=1))
    ax.plot(
        [6.112, 6.112, 16.906, 16.906, 10.594, 10.594],
        [BL.NORTH_FACE, 6.594, 6.594, 3.694, 3.694, 6.406],
        color=INK,
        lw=0,
        zorder=1,
    )
    for seg in (
        [(6.112, 6.594), (14.994, 6.594)],
        [(16.906, 3.694), (16.906, 11.15)],
        [(10.594, 3.694), (16.906, 3.694)],
        [(10.594, 6.406), (14.994, 6.406)],
        [(6.112, BL.NORTH_FACE), (P["x0"], BL.NORTH_FACE)],
        [(P["x0"], P["y_back"]), (P["x1"], P["y_back"])],
        [(6.112, 6.594), (6.112, BL.NORTH_FACE)],
    ):
        ax.plot([seg[0][0], seg[1][0]], [seg[0][1], seg[1][1]], color=INK, lw=2.2, zorder=3)
    # doors (gaps drawn as coloured bars)
    for (x0, y0, x1, y1), lab, pos in (
        ((6.0, 7.0, 6.0, 8.1), "休憩の扉", (6.0, 8.32)),
        ((6.0, 9.25, 6.0, 10.25), "メインサウナ", (5.35, 9.75)),
        ((7.1, 10.39, 8.1, 10.39), "セルフロウリュ", (7.6, 10.62)),
        ((10.2, 10.39, 11.2, 10.39), "高温ドライ", (10.7, 10.62)),
        ((16.906, 5.3, 16.906, 6.2), "裏方", (17.25, 5.75)),
        ((10.5, 3.694, 11.5, 3.694), "更衣室から", (11.0, 3.45)),
    ):
        ax.plot([x0, x1], [y0, y1], color="#fffdf8", lw=5, zorder=4)
        ax.plot([x0, x1], [y0, y1], color=ROUTE["A"], lw=2.2, zorder=5)
        ax.text(pos[0], pos[1], lab, fontsize=9.5, color=MUTE, ha="center", va="center", zorder=6)
    # pools with copings
    for p in plan["pools"]:
        if p["room"] != "water":
            continue
        x, y, w, d = p["rect"]
        ax.add_patch(
            Rectangle(
                (x - 0.3, 6.594),
                w + 0.6,
                y + d + 0.3 - 6.594,
                fc="#d9d5cf",
                ec=MUTE,
                lw=0.6,
                zorder=2,
            )
        )
        ax.add_patch(Rectangle((x, y), w, d, fc="#bcd9e0", ec=MUTE, lw=0.6, zorder=3))
        ax.text(
            x + w / 2,
            y + d / 2,
            p["name"],
            fontsize=10.5,
            color="#4f7884",
            ha="center",
            va="center",
            zorder=4,
        )
        ax.add_patch(
            Rectangle(
                (x, y + d - 0.9), 0.9, 0.9, fc="none", ec="#4f7884", lw=0.6, hatch="---", zorder=4
            )
        )
    ax.add_patch(Rectangle((12.2, 6.8), 2.3, 0.38, fc="#a9cbd4", ec="none", zorder=4))
    for q in BL.LEDGE:
        ax.add_patch(Circle(q, 0.09, fc="#4f7884", ec="none", zorder=5))
    ax.text(
        13.35,
        7.36,
        "水中のへりに座る人（北向き）",
        fontsize=9,
        color="#4f7884",
        ha="center",
        zorder=5,
    )
    ax.add_patch(Rectangle((12.8, 10.8), 3.9, 0.35, fc="#d9d5cf", ec=MUTE, lw=0.6, zorder=2))
    ax.text(
        15.95, 10.98, "炭酸泉", fontsize=10, color="#4f7884", ha="center", va="center", zorder=4
    )
    for yy in (7.05, 7.85):
        ax.add_patch(Circle((16.72, yy), 0.09, fc="none", ec=MUTE, lw=1.0, zorder=5))
    ax.text(16.45, 7.45, "汗流し", fontsize=9, color=MUTE, ha="right", va="center")
    ax.text(13.6, 5.0, "洗い場", fontsize=11, color=MUTE, ha="center", va="center")
    # rest: partitions, seats (all taken), pegs
    for a in lay["aisles"]:
        x0, y0, x1, y1 = a["rect"]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#f6ecd2", ec="none", zorder=2))
    for p in lay["partitions"]:
        x0, y0, x1, y1 = p["rect"]
        ax.add_patch(
            Rectangle(
                (x0, y0),
                x1 - x0,
                y1 - y0,
                fc="#7d4f24" if p["kind"] == "panel" else "#c9b79a",
                ec="none",
                zorder=5,
            )
        )
    for s in lay["seats"]:
        ax.add_patch(Polygon(seat_poly(s), closed=True, fc="#c9a888", ec=MUTE, lw=0.8, zorder=3))
        ax.add_patch(Circle(s["eye"][:2], 0.11, fc="#7b5d47", ec="none", zorder=7))
    J = BL.JUNCTION
    for px, py, (dx, dy) in lay["pegs"]:
        q = (px + dx * 0.06, py + dy * 0.06)
        ax.plot([J[0], q[0]], [J[1], q[1]], color=ROUTE["A"], lw=0.6, alpha=0.55, zorder=8)
        ax.add_patch(Circle(q, 0.07, fc=ROUTE["A"], ec="#fffdf8", lw=0.6, zorder=12))
    ax.add_patch(Circle(J, 0.16, fc="#fffdf8", ec=ROUTE["A"], lw=2.2, zorder=14))
    ax.text(
        J[0],
        J[1],
        "J",
        fontsize=10,
        color=ROUTE["A"],
        weight="bold",
        ha="center",
        va="center",
        zorder=15,
    )
    # built-in seats and perch (all with bodies)
    b = BL.BUILT_IN
    ax.add_patch(
        Rectangle(
            (b["xf"] - 0.72, b["y0"]),
            0.72,
            b["y1"] - b["y0"],
            fc="#cfcac2",
            ec=INK,
            lw=0.8,
            zorder=6,
        )
    )
    for s in BL.built_in_seats():
        body(ax, s)
    ax.add_patch(
        Rectangle(
            (P["x0"], P["y_front"]),
            P["x1"] - P["x0"],
            P["y_back"] - P["y_front"],
            fc="#cfcac2",
            ec=INK,
            lw=0.8,
            zorder=6,
        )
    )
    for x0, y0, x1, y1 in BL.perch_panels():
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#6b655d", ec="none", zorder=7))
    for s in BL.perch_seats():
        body(ax, s)
    # gaze pairs in the bath
    g = BL.gaze()
    eye = {s["id"]: (s["b"][0], s["b"][1] - 0.13) for s in BL.perch_seats()}
    eye.update({s["id"]: (s["b"][0] - 0.13, s["b"][1]) for s in BL.built_in_seats()})
    eye.update({f"ledge{k + 1}": q for k, q in enumerate(BL.LEDGE)})
    for key in ("perch-built_in", "perch-ledge"):
        for a, c, *_ in g[key]:
            ax.plot(
                [eye[a][0], eye[c][0]],
                [eye[a][1], eye[c][1]],
                color="#e08a2c",
                lw=0.6 if key == "perch-ledge" else 1.4,
                alpha=0.35 if key == "perch-ledge" else 0.7,
                zorder=8,
            )
    # routes
    R = {r["id"]: r for r in BL.routes()}
    for r in R.values():
        route(ax, r)
    badge(ax, (6.62, 8.45), "A", ROUTE["A"])
    badge(ax, (8.0, R["B"]["path"][3][1]), "B", ROUTE["B"])
    badge(ax, (12.1, 9.2), "C", ROUTE["C"])
    badge(ax, (10.2, R["D"]["path"][2][1]), "D", ROUTE["D"])
    badge(ax, (15.0, R["E"]["path"][1][1]), "E", ROUTE["E"])
    # dimensions
    c = BL.clearances()
    chk = RL.checks()
    px = (BL.perch_seats()[1]["b"][0] + BL.perch_seats()[2]["b"][0]) / 2
    toes = BL.COPING_N + c["walkway_width_seats_occupied"]
    dim(
        ax,
        (px, BL.COPING_N),
        (px, toes),
        f"足先まで {c['walkway_width_seats_occupied']:.2f}",
        fs=10,
    )
    dim(
        ax,
        (P["x1"] + 0.3, BL.COPING_N),
        (P["x1"] + 0.3, BL.NORTH_FACE),
        f"空席時\n{c['walkway_width_seats_empty']:.2f}",
        fs=10,
        side=-0.42,
    )
    dim(
        ax,
        (11.2, 10.2),
        (P["x0"], 10.2),
        f"{c['west_end_to_dry_sauna_door']:.2f}",
        fs=9.5,
        side=-0.16,
    )
    dim(
        ax,
        (14.8, 8.1),
        (14.8 + c["east_zone_width_past_built_in_legs"], 8.1),
        f"{c['east_zone_width_past_built_in_legs']:.2f}",
        fs=9.5,
        side=-0.18,
    )
    dim(ax, (15.0, 10.55), (16.9, 10.55), "炭酸泉の入口 1.90", fs=9.5, side=0.0)
    pl = RL.PLATFORM
    dim(
        ax,
        (1.2, RL.HB_Y1),
        (1.2, pl["y_front"]),
        f"主通路 {chk['main_aisle_width']:.2f}",
        fs=10,
        side=0.7,
    )
    dim(
        ax,
        (pl["x1"] + 0.055, 8.55),
        (RL.EAST_MAIN, 8.55),
        f"扉前 {chk['door_landing_width']:.2f}",
        fs=9.5,
        side=0.16,
    )
    dim(
        ax,
        (9.9, 4.424),
        (9.9, 4.424 + chk["extension_aisle_width"]),
        f"延長通路 {chk['extension_aisle_width']:.2f}",
        fs=9.5,
        side=-0.62,
    )
    dim(ax, (6.112, 8.72), (6.8, 8.72), "0.69", fs=9.5, side=0.17)
    note(ax, (2.6, 9.25), "寝台6：足元が通路から直接見える", to=(2.6, 7.0), fs=10)
    note(
        ax,
        (2.6, 9.75),
        "席ごとのタオル掛け（●）＝使用中の合図。合流点Jに立てば9席分が見通せる",
        to=(3.34, 5.94),
        fs=10,
        colour=ROUTE["A"],
    )
    note(
        ax,
        (2.6, 10.25),
        "休憩15席は扉1か所の行き止まり（第2経路なし）。合図が無いと奥まで往復 約%.0f m"
        % BL.search_walk()["inside_walk_without_cue_m"],
        fs=10,
    )
    note(
        ax,
        (13.8, 11.45),
        "予備の腰掛け3席（短時間用・石・壁の中に納める）",
        to=(13.8, 10.62),
        fs=11,
    )
    note(ax, (15.45, 8.5), "造り付け2席\n（v4から）", to=(16.3, 9.0), fs=9.5)
    note(
        ax,
        (12.9, 8.42),
        "予備席は座る水風呂のへりの人と向かい合う\n（3.6〜4.2 m・浴槽越し）。P3は造り付け席と斜め50°",
        fs=9.5,
        colour="#b56a14",
    )
    ax.text(-0.2, 9.75, "N ↑", fontsize=12, color=MUTE)
    ax.set_xlim(-0.35, 17.75)
    ax.set_ylim(3.2, 11.75)
    ax.set_aspect("equal")
    ax.axis("off")


def main():
    for f in (
        "/mnt/c/Windows/Fonts/YuGothM.ttc",
        "/mnt/c/Windows/Fonts/meiryo.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ):
        if pathlib.Path(f).exists():
            font_manager.fontManager.addfont(f)
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name()
            break
    lay = RL.layout_v5()
    c, g, sc, sw, rts = BL.clearances(), BL.gaze(), BL.scenarios(), BL.search_walk(), BL.routes()
    fig = plt.figure(figsize=(24, 16.6), dpi=100, facecolor=PAPER)
    fig.text(
        0.014,
        0.972,
        "休憩が満席のときの行き先と戻り道（v6 検討図）",
        fontsize=25,
        color=INK,
        weight="bold",
        va="center",
    )
    fig.text(
        0.014,
        0.945,
        "模型と同じ寸法ソース（bath_layout.py / rest_layout.py / plan_a.json）から作図。休憩15席・造り付け2席・予備3席がすべて埋まった状態を描いている。"
        "成人の仮寸法による概念検討で、全員が同時に休めることは保証しない。",
        fontsize=12.5,
        color=MUTE,
        va="center",
    )
    draw(fig.add_axes([0.005, 0.345, 0.99, 0.585]), lay)
    ax = fig.add_axes([0.02, 0.01, 0.96, 0.33])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    R = {r["id"]: r for r in rts}
    n = sc["places_out_of_water"]
    left = [
        (
            "A",
            f"水風呂を出て休憩の扉へ（{R['A']['length_m']:.1f} m）。扉を入って1歩の合流点Jで、寝台の足元と各席のタオル掛けを見て空きを確かめる。",
        ),
        (
            "B",
            f"満席なら同じ扉から戻り、北側の通路を予備の腰掛けへ（Jから約{R['B']['length_m']:.0f} m）。サ室や浴槽へ戻る必要はない。",
        ),
        (
            "C",
            f"座る水風呂からは扉へ寄らずに約{R['C']['length_m']:.1f} m。予備席は2槽のどちらからも見える。",
        ),
        (
            "D",
            "休憩から人が出てくるのは予備席から水風呂越しに見える。空いたら同じ道を戻る（確実に空いている保証は無い）。",
        ),
        ("E", "造り付け2席（東壁）は予備席のすぐ東。3か所とも通路から見える。"),
    ]
    y = 0.97
    ax.text(0.0, y + 0.02, "動線", fontsize=13, color=INK, weight="bold", va="top")
    y -= 0.07
    for k, text in left:
        ax.text(
            0.008,
            y - 0.012,
            k,
            fontsize=10.5,
            color="#fffdf8",
            weight="bold",
            ha="center",
            va="center",
            bbox=dict(boxstyle="circle,pad=0.22", fc=ROUTE[k], ec="none"),
        )
        w = wrap(text, 44)
        ax.text(0.025, y, "\n".join(w), fontsize=10.8, color=INK, va="top", linespacing=1.42)
        y -= 0.052 * len(w) + 0.022
    mid = [
        (
            "幅（膝と足を含む）",
            f"予備席の前の通路は空席時{c['walkway_width_seats_empty']:.2f} m（v5と同じ。座面は壁の線から出ない）。3人が座ると膝と足が{c['legs_reach_into_walkway']:.2f} m出て、"
            f"足先〜縁石は{c['walkway_width_seats_occupied']:.2f} m：1人が通る幅で、3人の足の前{c['walk_past_three_pairs_of_feet_length']:.2f} mの間はすれ違えない（片方が待つか縁石へ寄る）。"
            f"座る水風呂の上がり口から最も近い足まで{c['seated_pool_steps_to_nearest_feet']:.2f} m、炭酸泉の入口の端まで{c['nearest_feet_to_carbon_opening_edge']:.2f} m。"
            f"入口1.90 m・東側{c['east_zone_width_past_built_in_legs']:.2f} m・裏方の扉は変えていない。動線は足の中を通していない。",
        ),
        (
            "満席の把握",
            f"浴室側からは扉のガラス越しに一部しか見えない。席の入口ごとにタオル掛けを1つ付け、合流点Jで見渡せるようにした。"
            f"ただし利用者の協力が前提の目印で、掛け忘れ・掛けたままの離席があり得る。空席を判定する設備でも、探さずに済む保証でもない。"
            f"目印が働かないときの往復は約{sw['inside_walk_without_cue_m']:.0f} m。出入りは扉1か所（扉前1.07 m）で、回遊にはならない。",
        ),
        (
            "目線",
            f"予備席どうしは横並びで向かい合わない。造り付け席とは斜め（{len(g['perch-built_in'])}組が60°の範囲内）、"
            f"座る水風呂のへりに座る人とは浴槽越しに向かい合う（{len(g['perch-ledge'])}組）。休憩の仕切りと視線はv5から変えていない。",
        ),
    ]
    y = 0.97
    for head, text in mid:
        ax.text(0.345, y + 0.02, head, fontsize=13, color=INK, weight="bold", va="top")
        y -= 0.07
        w = wrap(text, 45)
        ax.text(0.345, y, "\n".join(w), fontsize=10.8, color=INK, va="top", linespacing=1.42)
        y -= 0.052 * len(w) + 0.03
    right = [
        ("① 通常の満席", sc["1_normal_full"]),
        ("② 20人イベントの直後", sc["2_after_event"]),
        ("③ 予備まで満席", sc["3_all_full"]),
        ("今回解いた範囲／残る課題", sc["solved_by_this_change"] + " ／ " + sc["still_open"]),
    ]
    y = 0.97
    for head, text in right:
        ax.text(0.685, y + 0.02, head, fontsize=13, color=INK, weight="bold", va="top")
        y -= 0.07
        w = wrap(text, 43)
        ax.text(0.685, y, "\n".join(w), fontsize=10.8, color=INK, va="top", linespacing=1.42)
        y -= 0.052 * len(w) + 0.025
    out = DATA / "diagrams"
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / f"rest_full_routes_{V}.png", dpi=100, facecolor=PAPER)
    ver = DATA / "verification"
    ver.mkdir(parents=True, exist_ok=True)
    rec = {
        "source": "blender/sauna/bath_layout.py, rest_layout.py (same data as the model)",
        "limits": "成人の仮寸法による概念検討。40人全員が同時に休めることは保証しない。タオル掛けは使い方に頼る合図。滑り・防水・衛生・構造は未検証。",
        "perch": BL.PERCH,
        "perch_seats": BL.perch_seats(),
        "clearances_m": c,
        "gaze_pairs_within_60deg": g,
        "routes": [
            {
                "id": r["id"],
                "label": r["label"],
                "length_m": r["length_m"],
                "path": [list(p) for p in r["path"]],
            }
            for r in rts
        ],
        "finding_out_that_rest_is_full": sw,
        "pegs": [
            {"x": round(p[0], 3), "y": round(p[1], 3), "dir": list(p[2])} for p in lay["pegs"]
        ],
        "scenarios": sc,
        "rest_clearances_m": RL.checks(),
    }
    (ver / "rest_full_study.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(out / f"rest_full_routes_{V}.png")


if __name__ == "__main__":
    main()
