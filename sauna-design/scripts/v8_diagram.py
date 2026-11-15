#!/usr/bin/env python3
"""v8 check figure (one sheet, Japanese, dimensioned): the bath strip with the two smaller cold pools and the rest annex
(old water outlines dashed, bodies, routes, walking widths), and the two small saunas in plan and section.

Reads blender/sauna/water_layout.py, sub_layout.py and bath_layout.py — the same data the model is built from — and writes

  <data-root>/diagrams/v8_plan.png

Assumed adult sizes; a concept check, not code compliance, not a heater clearance, not a bather-load rating.
"""

import sys

sys.dont_write_bytecode = True
import math  # noqa: E402
import pathlib  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import FancyArrowPatch, Polygon, Rectangle  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "blender"))
from sauna import bath_layout as BL  # noqa: E402
from sauna import main_layout as ML
from sauna import sub_layout as SL
from sauna import water_layout as WL

V = "v8"
DATA = (
    pathlib.Path(sys.argv[1])
    if len(sys.argv) > 1
    else pathlib.Path(f"/home/kazumasa/projects/_data/sauna-design/fable-{V}")
)
for f in (
    "/mnt/c/Windows/Fonts/YuGothM.ttc",
    "/mnt/c/Windows/Fonts/meiryo.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
):
    if pathlib.Path(f).exists():
        font_manager.fontManager.addfont(f)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name()
        break
else:
    sys.exit("no Japanese font found")

INK, MUTE, PAPER = "#2a2520", "#8a8178", "#f6f2ea"
C = {
    "floor": "#fffdf8",
    "water": "#bcd9e3",
    "tread": "#8fb9c9",
    "coping": "#d9d4cb",
    "timber": "#c9a57a",
    "seat": "#ecd2ac",
    "foot": "#c8d9e2",
    "step": "#cfe4c2",
    "deck": "#e6c39a",
    "corner": "#e3d6c4",
    "torso": "#7b5d47",
    "limb": "#b99578",
    "stand": "#5f7385",
    "stove": "#5b504a",
    "old": "#b4442f",
    "A": "#2a67ad",
    "B": "#1f7f79",
    "C": "#8b5fb0",
    "D": "#b07a1f",
    "wall": "#4a433d",
}
B = ML.BODY


def dim(ax, p0, p1, text, off=0.0, fs=9.5, colour=INK, side=0.0, rot=None):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    n = math.hypot(dx, dy)
    nx, ny = -dy / n, dx / n
    a, b = (p0[0] + nx * off, p0[1] + ny * off), (p1[0] + nx * off, p1[1] + ny * off)
    ax.plot([a[0], b[0]], [a[1], b[1]], color=colour, lw=1.0, zorder=20)
    for q in (a, b):
        ax.plot(
            [q[0] - nx * 0.04, q[0] + nx * 0.04],
            [q[1] - ny * 0.04, q[1] + ny * 0.04],
            color=colour,
            lw=1.0,
            zorder=20,
        )
    ax.text(
        (a[0] + b[0]) / 2 + nx * side,
        (a[1] + b[1]) / 2 + ny * side,
        text,
        fontsize=fs,
        color=colour,
        ha="center",
        va="center",
        zorder=21,
        rotation=rot or 0,
        bbox=dict(fc="#fffdf8", ec="none", pad=1.0, alpha=0.92),
    )


def note(ax, xy, text, to=None, fs=9.3, colour=INK, ha="center", va="center"):
    if to:
        ax.annotate(
            text,
            xy=to,
            xytext=xy,
            fontsize=fs,
            color=colour,
            ha=ha,
            va=va,
            zorder=22,
            arrowprops=dict(arrowstyle="-", color=colour, lw=0.8),
            bbox=dict(fc="#fffdf8", ec="none", pad=1.3, alpha=0.92),
        )
    else:
        ax.text(
            xy[0],
            xy[1],
            text,
            fontsize=fs,
            color=colour,
            ha=ha,
            va=va,
            zorder=22,
            bbox=dict(fc="#fffdf8", ec="none", pad=1.3, alpha=0.92),
        )


def route(ax, pts, colour, lw=1.8, ls="-"):
    for a, b in zip(pts, pts[1:-1]):
        ax.plot(
            [a[0], b[0]],
            [a[1], b[1]],
            color=colour,
            lw=lw,
            ls=ls,
            zorder=17,
            solid_capstyle="round",
        )
    ax.add_patch(
        FancyArrowPatch(
            pts[-2],
            pts[-1],
            arrowstyle="-|>",
            mutation_scale=12,
            color=colour,
            lw=lw,
            ls=ls,
            zorder=17,
        )
    )


def rect(ax, x0, y0, x1, y1, fc, ec=INK, lw=0.6, z=3, **kw):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=fc, ec=ec, lw=lw, zorder=z, **kw))


def body_plan(ax, boxes, label=None, z=12):
    for part, x0, y0, x1, y1, z0, z1 in boxes:
        col = (
            C["stand"]
            if part.startswith("stand")
            else (C["torso"] if part in ("torso", "head", "hips") else C["limb"])
        )
        if part == "stand_head":
            continue
        rect(ax, x0, y0, x1, y1, col, ec="none", z=z + (1 if part in ("head",) else 0), alpha=0.92)
    if label:
        t = next(b for b in boxes if b[0] in ("torso", "stand_body", "hips"))
        ax.text(
            (t[1] + t[3]) / 2,
            (t[2] + t[4]) / 2,
            label,
            fontsize=6.6,
            color="#fffdf8",
            ha="center",
            va="center",
            zorder=z + 3,
        )


def octagon(c, r):
    return [
        (
            c[0] + r * math.cos(math.pi / 8 + math.pi / 4 * k),
            c[1] + r * math.sin(math.pi / 8 + math.pi / 4 * k),
        )
        for k in range(8)
    ]


def frame(ax, x0, x1, y0, y1, title):
    ax.set_facecolor(PAPER)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=12.5, color=INK, loc="left", pad=5)


# ---- bath strip ------------------------------------------------------------------------------------------------------
def bath(ax):
    cl = WL.clearances()
    ar = WL.areas()
    a, sc = WL.ANNEX, WL.SCREEN
    frame(
        ax,
        5.2,
        20.6,
        5.92,
        11.06,
        f"浴室の平面（v8）  水風呂 2槽の水面 {ar['v7']['surface_total_m2']:.2f} → {ar['v8']['surface_total_m2']:.2f} m²、空いた床に寝椅子4の休憩の離れ",
    )
    rect(ax, WL.XW, WL.YS_STONE, WL.XE, WL.YN, C["floor"], ec="none", z=1)
    p = BL.PERCH
    rect(ax, p["x0"], WL.YN, p["x1"], p["y_back"], C["floor"], ec="none", z=1)
    W = dict(color=C["wall"], lw=3.2, zorder=9, solid_capstyle="butt")
    for (x0, y0), (x1, y1) in (
        ((WL.XW, WL.YS_STONE), (WL.XW, WL.REST_DOOR[0])),
        ((WL.XW, WL.REST_DOOR[1]), (WL.XW, WL.MAIN_DOOR[0])),
        ((WL.XW, WL.MAIN_DOOR[1]), (WL.XW, WL.YN)),
        ((WL.XW, WL.YN), (7.1, WL.YN)),
        ((8.1, WL.YN), (10.2, WL.YN)),
        ((11.2, WL.YN), (p["x0"], WL.YN)),
        ((p["x0"], WL.YN), (p["x0"], p["y_back"])),
        ((p["x0"], p["y_back"]), (p["x1"], p["y_back"])),
        ((p["x1"], p["y_back"]), (p["x1"], WL.YN)),
        ((WL.XW, WL.YS_STONE), (WL.WASH_OPENING[0], WL.YS_STONE)),
        ((WL.XE, WL.YS_STONE - 0.3), (WL.XE, 11.1)),
    ):
        ax.plot([x0, x1], [y0, y1], **W)
    for (x, y), t, ha, va in (
        ((WL.XW - 0.08, 7.55), "休憩室の扉", "right", "center"),
        ((WL.XW - 0.08, 9.75), "メイン\nサウナの扉", "right", "center"),
        ((7.6, WL.YN + 0.1), "セルフロウリュの扉", "center", "bottom"),
        ((10.7, WL.YN + 0.1), "高温ドライの扉", "center", "bottom"),
        ((15.95, WL.YS_STONE - 0.12), "洗い場から（開口 1.93）", "center", "top"),
        ((15.95, WL.YN + 0.3), "炭酸泉へ", "center", "bottom"),
    ):
        ax.text(x, y, t, fontsize=8.6, color=MUTE, ha=ha, va=va, zorder=10)
    # v7 water outlines
    for pid in ("deep", "seated"):
        x, y, w, d = WL.OLD[pid]["rect"]
        ax.add_patch(
            Rectangle((x, y), w, d, fc="none", ec=C["old"], lw=1.4, ls=(0, (5, 3)), zorder=16)
        )
    note(
        ax,
        (8.0, 6.12),
        "赤の破線 = v7の水面（3.2×1.9 m ×2）。縁石を含むブロックは x 6.80〜14.80",
        colour=C["old"],
        fs=8.8,
    )
    # v8 pools
    rect(ax, sc["x1"], WL.YS_STONE, WL.EAST_COPING[1], WL.COPING_N, C["coping"], lw=0.8, z=2)
    for pid, name in (("deep", "立つ槽"), ("seated", "座る槽")):
        pl = WL.pool(pid)
        x0, y0, x1, y1 = pl["rect"]
        rect(ax, x0, y0, x1, y1, C["water"], lw=0.9, z=3)
        for k, t in enumerate(pl["treads"]):
            rect(ax, t[0], t[1], t[2], t[3], C["tread"], lw=0.5, z=4)
        ax.text(
            (x0 + x1) / 2,
            y0 - 0.1,
            f"{name} {x1 - x0:.2f}×{y1 - y0:.2f}・深さ{pl['depth']:.1f}",
            fontsize=8.6,
            color=INK,
            ha="center",
            va="center",
            zorder=22,
            bbox=dict(fc="#fffdf8", ec="none", pad=1.0, alpha=0.92),
        )
    d, s = WL.pool("deep"), WL.pool("seated")
    ax.plot(
        [d["treads"][0][2] - 0.04] * 2,
        [d["rect"][3] + 0.14, d["treads"][2][1] + 0.14],
        color="#555",
        lw=2.2,
        zorder=14,
    )
    ax.plot(
        [WL.RAILS["seated"]["x"]] * 2,
        list(WL.RAILS["seated"]["y"]),
        color="#555",
        lw=2.2,
        zorder=14,
    )
    # splash wall and annex
    rect(ax, sc["x0"], WL.YS_STONE, sc["x1"], sc["y1"], C["wall"], lw=0.4, z=8)
    for name, x0, y0, x1, y1, h, fin in WL.partitions():
        rect(ax, x0, y0, x1, y1, C["timber"], lw=0.5, z=8)
    for L in WL.loungers():
        fx, fy = L["foot"]
        rect(
            ax,
            fx,
            fy - WL.LOUNGER["w"] / 2,
            fx + WL.LOUNGER["len"],
            fy + WL.LOUNGER["w"] / 2,
            "#e9e0d2",
            lw=0.6,
            z=5,
        )
    for px, py, (dx, dy) in WL.pegs():
        ax.plot([px, px + dx * 0.06], [py, py + dy * 0.06], color=INK, lw=2.0, zorder=15)
    for bid, kind, label, boxes in WL.bodies():
        body_plan(ax, boxes, bid)
    # existing seats on the bath side
    for st in BL.perch_seats() + BL.built_in_seats():
        body_plan(ax, ML.body_boxes(st), st["id"], z=11)
    b = BL.BUILT_IN
    rect(ax, b["xf"] - 0.72, b["y0"], b["xf"], b["y1"], "none", lw=0.8, z=10)
    for yy in (7.05, 7.85):
        ax.plot([WL.XE - 0.3, WL.XE], [yy, yy], color="#555", lw=2.0, zorder=10)
    ax.text(WL.XE + 0.06, 7.45, "汗流し2", fontsize=8.4, color=MUTE, ha="left", va="center")
    ax.text(WL.XE + 0.06, 9.35, "造り付け\n2席", fontsize=8.4, color=MUTE, ha="left", va="center")
    ax.text(
        (p["x0"] + p["x1"]) / 2,
        p["y_back"] + 0.12,
        "予備の腰掛け3席（v6）",
        fontsize=8.4,
        color=MUTE,
        ha="center",
        va="bottom",
    )
    # routes
    for r in WL.routes():
        route(ax, r["path"], C[r["id"]], ls="-" if r["id"] in "AB" else (0, (4, 2)))
    # dimensions
    yn = WL.YN
    dim(ax, (11.45, WL.COPING_N), (11.45, yn), f"{cl['walkway_north_of_pools']:.2f}", fs=9.5)
    toes = WL.COPING_N + cl["walkway_between_coping_and_perch_toes"]
    dim(
        ax,
        (14.72, WL.COPING_N),
        (14.72, toes),
        f"{cl['walkway_between_coping_and_perch_toes']:.2f}（足先まで）",
        side=-0.62,
        fs=9.0,
    )
    dim(ax, (9.55, a["y1"]), (9.55, yn), f"{cl['walkway_north_of_annex_screen']:.2f}")
    dim(ax, (WL.XW, 8.62), (a["x0"], 8.62), f"{cl['rest_door_path_width']:.2f}", side=0.14, fs=9.0)
    half = WL.LOUNGER["w"] / 2
    dim(
        ax,
        (9.55, a["row_s"] + half),
        (9.55, a["row_n"] - half),
        f"{cl['annex_aisle_between_loungers']:.2f}",
        side=-0.26,
        fs=9.0,
    )
    dim(
        ax,
        (a["x0"] + 0.16, a["mouth"][0]),
        (a["x0"] + 0.16, a["mouth"][1]),
        f"{cl['annex_aisle_mouth_between_screen_ends']:.2f}",
        side=-0.24,
        fs=9.0,
    )
    dim(ax, (a["x0"], 6.42), (a["x1"], 6.42), f"離れ {a['x1'] - a['x0']:.2f}", fs=9.0)
    dim(
        ax,
        (WL.EAST_COPING[1], 7.45),
        (WL.XE, 7.45),
        f"{cl['east_zone_from_coping_to_east_wall']:.2f}",
        fs=9.5,
    )
    dim(
        ax,
        (d["treads"][0][0], 9.12),
        (d["treads"][0][2], 9.12),
        f"階段幅 {d['treads'][0][2] - d['treads'][0][0]:.2f}",
        fs=8.6,
    )
    dim(
        ax,
        (s["treads"][0][0], 9.26),
        (s["treads"][0][2], 9.26),
        f"階段幅 {s['treads'][0][2] - s['treads'][0][0]:.2f}",
        fs=8.6,
    )
    note(
        ax,
        (11.2, 6.32),
        f"仕切り壁 高さ{sc['h']:.2f}（通路側の端は1.30へ丸く下がる）",
        to=((sc["x0"] + sc["x1"]) / 2, 6.75),
        fs=8.8,
    )
    note(
        ax,
        (8.3, 9.45),
        f"通路側の板 高さ{a['panel_h']:.2f}＋上は格子",
        to=(8.3, a["y1"] - 0.02),
        fs=8.8,
    )
    note(
        ax,
        (13.6, 6.12),
        "PF = 階段を下りた床（深い槽0.78×0.78、座る槽は東壁沿い0.60）。静止の人数に数えず、出入りの人のために空けてある",
        fs=8.6,
    )
    # legend (right of the plan)
    lx, ly = 17.95, 10.8
    ax.text(20.5, 10.95, "N ↑", fontsize=11, color=MUTE, ha="right")
    ax.text(lx, ly, "動線", fontsize=10, color=INK, weight="bold", va="center")
    for k, r in enumerate(WL.routes()):
        yy = ly - 0.27 * (k + 1)
        ax.plot(
            [lx, lx + 0.3],
            [yy, yy],
            color=C[r["id"]],
            lw=2.0,
            ls="-" if r["id"] in "AB" else (0, (4, 2)),
        )
        ax.text(
            lx + 0.38,
            yy,
            f"{r['id']}: {r['label'].split('（')[0]}（{r['length_m']:.1f} m）",
            fontsize=8.4,
            color=INK,
            va="center",
        )
    rc = WL.rest_count()
    lines = [
        "人体（成人の仮寸法）",
        "茶＝座る・寝る　青灰＝立つ",
        "PD 深い槽に立つ　PS 座る槽の床に座る",
        "PT 階段の途中　PF 階段を下りた床　RA 寝椅子",
        "",
        "v7 → v8",
        f"水面 {ar['v7']['surface_total_m2']:.2f} → {ar['v8']['surface_total_m2']:.2f} m²（{ar['surface_ratio']:.2f}倍）",
        f"縁石を含む外形 {ar['v7']['block_outline_m2']:.2f} → {ar['v8']['block_outline_m2']:.2f} m²",
        f"水量 {ar['v7']['volume_total_m3_ignoring_steps']:.1f} → {ar['v8']['volume_total_m3_ignoring_steps']:.1f} m³（階段の体積は引いていない）",
        "水の中の静止位置：通常5、詰めて6（階段下の床は別に空き）",
        f"休憩できる場所 {rc['v7']['total']} → {rc['v8']['total']}（寝椅子＋{rc['net_added']}）",
        "既存の休憩15・造り付け2・予備3は変更なし",
        "水風呂前の通路 1.39 は v7 のまま",
    ]
    for k, t in enumerate(lines):
        ax.text(
            lx,
            ly - 1.55 - 0.235 * k,
            t,
            fontsize=9.6 if t in ("人体（成人の仮寸法）", "v7 → v8") else 8.6,
            color=INK,
            va="center",
            weight="bold" if t in ("人体（成人の仮寸法）", "v7 → v8") else "normal",
        )


# ---- small saunas ----------------------------------------------------------------------------------------------------
def levels(ax, lv, fs=8.2):
    for kind, label, x0, y0, x1, y1, z in lv:
        rect(ax, x0, y0, x1, y1, C[kind], lw=0.6, z=3)


def sub_shell(ax, xw, xe, door, tv=None):
    W = dict(color=C["wall"], lw=3.2, zorder=9, solid_capstyle="butt")
    ax.plot([xw, xw, xe], [SL.Y0, SL.Y1, SL.Y1], **W)
    if tv:
        ax.plot([xe, xe], [SL.Y1, tv[1]], **W)
        ax.plot([xe, xe], [tv[0], SL.Y0], **W)
        ax.plot([xe + 0.05, xe + 0.05], list(tv), color="#3b6ea5", lw=4.0, zorder=10)
    else:
        ax.plot([xe, xe], [SL.Y1, SL.Y0], **W)
    ax.plot([xw, door[0]], [SL.Y0, SL.Y0], **W)
    ax.plot([door[1], xe], [SL.Y0, SL.Y0], **W)
    ax.text(
        (door[0] + door[1]) / 2, SL.Y0 - 0.1, "扉", fontsize=8.6, color=MUTE, ha="center", va="top"
    )


def stove(ax, h):
    ax.add_patch(Polygon(octagon(h["c"], h["guard_r"]), fc="none", ec=INK, lw=1.0, zorder=6))
    ax.add_patch(plt.Circle(h["c"], h["r"], fc=C["stove"], ec="none", zorder=6))
    ax.text(
        h["c"][0],
        h["c"][1],
        "ストーブ\n（v7の位置）",
        fontsize=7.4,
        color="#fffdf8",
        ha="center",
        va="center",
        zorder=7,
    )


def self_plan(ax):
    s, D = SL.SELF, SL.self_dims()
    frame(ax, 5.75, 9.75, 10.2, 14.25, "セルフロウリュ 平面：高さ3つの席が回り込む（6位置）")
    rect(ax, s["xw"], SL.Y0, s["xe"], SL.Y1, C["floor"], ec="none", z=1)
    levels(ax, SL.self_levels())
    R = s["corner_r"]
    cx, cy = s["xw"] + R, SL.Y1 - R
    ax.add_patch(
        Polygon(
            [(s["xw"], cy)]
            + [
                (
                    cx + R * math.cos(math.pi - math.pi / 2 * k / 24),
                    cy + R * math.sin(math.pi - math.pi / 2 * k / 24),
                )
                for k in range(25)
            ]
            + [(s["xw"], SL.Y1)],
            fc=C["wall"],
            ec="none",
            zorder=8,
        )
    )
    sub_shell(ax, s["xw"], s["xe"], s["door"])
    stove(ax, s["heater"])
    ax.add_patch(plt.Circle(s["bucket"], 0.13, fc=C["timber"], ec=INK, lw=0.6, zorder=6))
    for st in SL.self_seats():
        body_plan(ax, SL.boxes(st), st["id"])
    for t in SL.self_standing():
        body_plan(ax, ML.standing_boxes(t), t["id"])
    note(ax, (7.3, 12.55), "足置き0.225", to=(6.95, 13.05), fs=7.8)
    note(ax, (9.56, 13.1), "足置き\n0.45", to=(9.2, 13.1), fs=7.8, ha="left")
    note(ax, (9.56, 12.77), "中間段\n0.225", to=(9.2, 12.77), fs=7.8, ha="left")
    note(ax, (5.92, 12.06), "席0.45", fs=7.8, ha="center")
    note(ax, (7.38, 14.05), "席0.675", fs=7.8)
    note(ax, (8.72, 14.05), "席0.90", fs=7.8)
    note(ax, (6.2, 14.05), "丸い入隅 R0.90\n（台0.675・席に数えない）", to=(6.45, 13.5), fs=7.6)
    hx, hy = s["heater"]["c"]
    dim(
        ax,
        (hx + 0.38, hy + D["guard_apothem"]),
        (hx + 0.38, D["step_front"]),
        f"{D['aisle_step_to_guard']:.2f}",
        fs=8.6,
        side=-0.2,
    )
    dim(
        ax,
        (D["w_front"], 11.05),
        (hx - D["guard_apothem"], 11.05),
        f"{D['floor_w_bench_to_guard']:.2f}",
        fs=8.6,
    )
    dim(ax, (s["xw"], 10.36), (s["xe"], 10.36), f"内法 {D['room_inner'][0]:.2f}", fs=8.6)
    note(ax, (9.56, 11.93), "桶", to=(s["bucket"][0] + 0.1, s["bucket"][1]), fs=7.8, ha="left")


def self_section(ax):
    s = SL.SELF
    x0, x1 = s["xw"], s["xe"]
    frame(ax, 5.75, 9.95, -0.25, 2.85, "セルフロウリュ 北壁を見る：0.45 → 0.675 → 0.90")
    rect(ax, x0, 0, x1, SL.H, C["floor"], ec=INK, lw=1.0, z=1)
    xf, xs = SL.self_dims()["w_front"], s["n_split"]
    rect(ax, x0, 0, xf, 0.675, C["corner"], z=3)
    rect(ax, x0, 0, xf, 0.45, C["seat"], z=4, alpha=0.55, hatch="//")
    rect(ax, xf, 0.225, xs, 0.675, C["seat"], z=3)
    rect(ax, xf, 0, xs, 0.225, C["foot"], z=3)
    rect(ax, xs, 0.45, x1, 0.90, C["seat"], z=3)
    rect(ax, xs, 0.225, x1, 0.45, C["foot"], z=3)
    rect(ax, xs, 0, x1, 0.225, C["step"], z=3)
    for st in SL.self_seats():
        if st["id"].startswith("SN"):
            bx = st["b"][0]
            rect(
                ax,
                bx - 0.25,
                st["seat_z"],
                bx + 0.25,
                st["seat_z"] + B["shoulder_h"],
                C["torso"],
                ec="none",
                z=6,
                alpha=0.9,
            )
            rect(
                ax,
                bx - 0.09,
                st["seat_z"] + B["shoulder_h"],
                bx + 0.09,
                st["seat_z"] + B["sit_h"],
                C["torso"],
                ec="none",
                z=6,
                alpha=0.9,
            )
            rect(
                ax,
                bx - 0.18,
                st["foot_z"],
                bx + 0.18,
                st["seat_z"],
                C["limb"],
                ec="none",
                z=5,
                alpha=0.9,
            )
            ax.text(
                bx,
                st["seat_z"] + 0.3,
                st["id"],
                fontsize=6.6,
                color="#fffdf8",
                ha="center",
                va="center",
                zorder=8,
            )
    note(ax, (6.41, 1.05), "西の2席\n座面0.45\n（斜線）", fs=7.8)
    for xx, z0, z1, t in (
        (xf + 0.12, 0.675 + B["sit_h"], SL.H, f"{SL.H - 0.675 - B['sit_h']:.2f}"),
        (x1 - 0.14, 0.90 + B["sit_h"], SL.H, f"{SL.H - 0.90 - B['sit_h']:.2f}"),
    ):
        dim(ax, (xx, z0), (xx, z1), t, fs=8.2, side=0.18)
    dim(ax, (x1 + 0.14, 0), (x1 + 0.14, 0.90), "0.90", fs=8.2, side=-0.17)
    dim(ax, (x1 + 0.14, 0.90), (x1 + 0.14, SL.H), f"{SL.H - 0.90:.2f}", fs=8.2, side=-0.17)
    ax.text(x0 + 0.05, SL.H + 0.08, f"天井 {SL.H:.1f}（仮）", fontsize=8.4, color=MUTE)
    ax.text(
        x0 + 0.05,
        -0.16,
        f"天井は2.30→{SL.H:.2f}（サブ2室とも）。0.45の足置きに立つと天井まで{SL.H - 0.45:.2f} m、身長1.85 mで頭上{SL.H - 0.45 - 1.85:.2f} m",
        fontsize=8.0,
        color=C["old"],
    )


def dry_plan(ax):
    d, m = SL.DRY, SL.dry_dims()
    frame(ax, 9.25, 12.95, 10.2, 14.25, "高温ドライ 平面：高い腰掛け2＋脚を伸ばす寝座2（4位置）")
    rect(ax, d["xw"], SL.Y0, d["xe"], SL.Y1, C["floor"], ec="none", z=1)
    levels(ax, SL.dry_levels())
    ax.add_patch(Polygon(SL.dry_diag(), fc=C["step"], ec=INK, lw=0.6, zorder=3))
    rect(ax, d["xw"], d["wing"]["y"][0], m["u_nose"], d["wing"]["y"][1], C["timber"], lw=0.5, z=8)
    rect(
        ax,
        d["xw"],
        d["split"] + 0.01,
        d["xw"] + d["back"]["base"],
        SL.Y1 - 0.01,
        C["timber"],
        lw=0.5,
        z=4,
        hatch="|||",
    )
    tv = d["tv"]
    sub_shell(ax, d["xw"], d["xe"], d["door"], tv=(tv["c"][0] - 0.56, tv["c"][0] + 0.56))
    stove(ax, d["heater"])
    for st in SL.dry_seats():
        body_plan(ax, SL.boxes(st), st["id"])
        ex, ey, ez = SL.eye(st)
        ax.plot([ex, tv["x"]], [ey, tv["c"][0]], color="#3b6ea5", lw=0.7, ls=(0, (3, 2)), zorder=16)
    for t in SL.dry_standing():
        body_plan(ax, ML.standing_boxes(t), t["id"])
    ax.text(
        tv["x"] + 0.12,
        tv["c"][0],
        "TV\n（壁内・v7の位置）",
        fontsize=7.8,
        color="#3b6ea5",
        ha="left",
        va="center",
    )
    dim(
        ax, (m["d_step_front"], 13.75), (d["xe"], 13.75), f"{m['aisle_east_of_d_step']:.2f}", fs=8.6
    )
    dim(
        ax, (m["u_step_front"], 11.72), (d["xe"], 11.72), f"{m['aisle_east_of_u_step']:.2f}", fs=8.6
    )
    dim(ax, (d["xw"], 14.05), (m["d_front"], 14.05), f"寝座 奥行{d['d_depth']:.2f}", fs=8.4)
    dim(ax, (d["xw"], 10.36), (d["xe"], 10.36), f"内法 {m['room_inner'][0]:.2f}", fs=8.6)
    note(ax, (9.42, 11.25), "腰掛け0.90\n足置き0.45\n中間段0.225", fs=7.6, ha="left")
    note(ax, (11.9, 12.45), "斜めの踏み板", to=(11.05, 12.5), fs=7.6)
    note(ax, (9.42, 12.52), "袖板", to=(9.8, 12.657), fs=7.6, ha="left")


def dry_section(ax):
    d, m = SL.DRY, SL.dry_dims()
    frame(ax, 9.25, 13.15, -0.25, 2.85, "高温ドライ 断面（北を見る）：寝座に脚を伸ばしてTVを見る")
    rect(ax, d["xw"], 0, d["xe"], SL.H, C["floor"], ec=INK, lw=1.0, z=1)
    rect(ax, d["xw"], 0, m["u_nose"], 0.90, C["seat"], z=2, alpha=0.35, ls=(0, (3, 2)))
    rect(ax, d["xw"], 0, m["d_front"], d["deck_top"], C["deck"], z=3)
    rect(ax, m["d_front"], 0, m["d_step_front"], d["step_top"], C["step"], z=3)
    bk = d["back"]
    base, tip = (
        (d["xw"] + bk["base"], d["deck_top"]),
        (d["xw"] + bk["top_in"], d["deck_top"] + bk["h"]),
    )
    ax.add_patch(
        Polygon(
            [(d["xw"], d["deck_top"]), base, tip, (d["xw"], tip[1])],
            fc=C["timber"],
            ec=INK,
            lw=0.6,
            zorder=4,
        )
    )
    tv = d["tv"]
    rect(
        ax,
        d["xe"],
        tv["c"][1] - 0.355,
        d["xe"] + 0.1,
        tv["c"][1] + 0.355,
        "#3b6ea5",
        ec="none",
        z=5,
    )
    st = SL.dry_seats()[2]
    for part, x0, y0, x1, y1, z0, z1 in SL.boxes(st):
        rect(
            ax,
            x0,
            z0,
            x1,
            z1,
            C["torso"] if part in ("torso", "head", "hips") else C["limb"],
            ec="none",
            z=6,
            alpha=0.92,
        )
    ex, ey, ez = SL.eye(st)
    ax.plot([ex, d["xe"]], [ez, tv["c"][1]], color="#3b6ea5", lw=0.9, ls=(0, (3, 2)), zorder=7)
    su = SL.dry_seats()[1]
    eu = SL.eye(su)
    ax.plot(
        [eu[0], d["xe"]], [eu[2], tv["c"][1]], color="#3b6ea5", lw=0.7, ls=(0, (1, 2)), zorder=7
    )
    v = SL.dry_tv_view()
    note(
        ax,
        (11.2, 1.78),
        f"寝座：画面まで{v['DD1']['distance_m']:.2f} m・見上げ{v['DD1']['look_up_deg']:.0f}°\n腰掛け（点線・奥）：{v['DU2']['distance_m']:.2f} m・見下ろし{-v['DU2']['look_up_deg']:.0f}°",
        fs=7.8,
    )
    note(ax, (9.95, 2.08), f"背 {m['back_rake_deg']:.0f}°", to=(9.76, 1.0), fs=7.8)
    dim(ax, (d["xw"], -0.12), (m["d_front"], -0.12), f"{d['d_depth']:.2f}", fs=8.2)
    dim(
        ax, (m["d_step_front"], -0.12), (d["xe"], -0.12), f"{m['aisle_east_of_d_step']:.2f}", fs=8.2
    )
    dim(
        ax,
        (d["xe"] + 0.3, 0),
        (d["xe"] + 0.3, tv["c"][1]),
        f"画面中心 {tv['c'][1]:.2f}",
        fs=8.0,
        side=-0.02,
        rot=90,
    )
    ax.text(d["xw"] + 0.05, SL.H + 0.08, f"天井 {SL.H:.1f}（仮）", fontsize=8.4, color=MUTE)


def main():
    fig = plt.figure(figsize=(24, 16.4), dpi=100)
    fig.patch.set_facecolor(PAPER)
    fig.text(
        0.014,
        0.975,
        "v8 検討図：水風呂を縮めて休憩の離れに／サブ2室を違う座り方に",
        fontsize=24,
        color=INK,
        weight="bold",
        va="center",
    )
    fig.text(
        0.014,
        0.948,
        "寸法はm。成人の仮寸法（肩幅0.50・座高0.92・身長1.72）で人体を置いた概念検討。定員・法適合・ストーブ機種とメーカー離隔・熱と蒸気の流れ・"
        "浴槽設備と水質・滑り・構造・費用は未検証。",
        fontsize=11.5,
        color=MUTE,
        va="center",
    )
    bath(fig.add_axes([0.012, 0.452, 0.976, 0.462]))
    self_plan(fig.add_axes([0.012, 0.03, 0.235, 0.40]))
    self_section(fig.add_axes([0.25, 0.03, 0.245, 0.40]))
    dry_plan(fig.add_axes([0.505, 0.03, 0.225, 0.40]))
    dry_section(fig.add_axes([0.735, 0.03, 0.255, 0.40]))
    out = DATA / "diagrams"
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "v8_plan.png", dpi=100, facecolor=PAPER)
    print("DIAGRAM_OK", out / "v8_plan.png")


if __name__ == "__main__":
    main()
