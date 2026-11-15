#!/usr/bin/env python3
"""Rest-area sight-line study figure (plan + three sections) and its numbers.

Reads the same coordinates as the Blender model (blender/sauna/rest_layout.py) and writes
  <data-root>/diagrams/rest_sightlines_v6.png   (v6: the rest layout and partitions are the v5 ones; only towel pegs were added)
  <data-root>/verification/rest_sightline_study.json
Study values only: eye heights, view angles and clearances are assumptions, not ergonomic or regulatory figures.

  python3 scripts/sightline_diagram.py [<data-root>]
"""

import sys

sys.dont_write_bytecode = True
import importlib.util  # noqa: E402
import json  # noqa: E402
import pathlib  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent.parent
DATA = (
    pathlib.Path(sys.argv[1])
    if len(sys.argv) > 1
    else pathlib.Path("/home/kazumasa/projects/_data/sauna-design/fable-v6")
)
if HERE in DATA.resolve().parents:
    sys.exit("refusing to write generated files inside the source tree")
spec = importlib.util.spec_from_file_location(
    "rest_layout", HERE / "blender" / "sauna" / "rest_layout.py"
)
RL = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RL)

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
AISLE, SIGHT, BAD, WALK = "#f3dfb4", "#0d7a78", "#c8321f", "#5b6fb0"
LOUNGER_PROFILE = [
    (0.00, 0.285),
    (0.22, 0.335),
    (0.50, 0.395),
    (0.76, 0.355),
    (0.95, 0.300),
    (1.16, 0.385),
    (1.42, 0.590),
    (1.66, 0.790),
    (1.80, 0.885),
]
CHAIR_PROFILE = [
    (0.00, 0.395),
    (0.18, 0.415),
    (0.40, 0.375),
    (0.50, 0.365),
    (0.60, 0.50),
    (0.69, 0.72),
    (0.76, 0.96),
]


def height_colour(z1):
    if z1 >= 2.0:
        return "#c9b79a"
    if z1 >= 1.40:
        return "#4b2f17"
    if z1 >= 1.25:
        return "#7d4f24"
    if z1 >= 1.0:
        return "#b07a42"
    return "#d9b684"


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


def draw_plan(ax, lay, st, full):
    ax.set_facecolor(PAPER)
    ax.add_patch(Polygon(lay["outline"], closed=True, fc="#fffdf8", ec=INK, lw=2.2, zorder=1))
    for a in lay["aisles"]:
        x0, y0, x1, y1 = a["rect"]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=AISLE, ec="none", zorder=2))
    for p in lay["partitions"]:
        x0, y0, x1, y1 = p["rect"]
        fins = p["kind"] == "fins"
        if fins and any(q["kind"] == "panel" and q["rect"] == p["rect"] for q in lay["partitions"]):
            ax.add_patch(
                Rectangle(
                    (x0 - 0.035, y0),
                    x1 - x0 + 0.07,
                    y1 - y0,
                    fc="none",
                    ec="#7d4f24",
                    lw=0.8,
                    hatch="||||" if (x1 - x0) > (y1 - y0) else "----",
                    zorder=6,
                )
            )
            continue
        if "outline" in p:  # shaped top: colour each slice by the real height at that point
            along_x = (x1 - x0) >= (y1 - y0)
            run, n = (x1 - x0) if along_x else (y1 - y0), 24
            for k in range(n):
                c = height_colour(RL.top_at(p, run * (k + 0.5) / n))
                if along_x:
                    ax.add_patch(
                        Rectangle(
                            (x0 + run * k / n, y0), run / n, y1 - y0, fc=c, ec="none", zorder=5
                        )
                    )
                else:
                    ax.add_patch(
                        Rectangle(
                            (x0, y0 + run * k / n), x1 - x0, run / n, fc=c, ec="none", zorder=5
                        )
                    )
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="none", ec=INK, lw=0.5, zorder=5))
            continue
        ax.add_patch(
            Rectangle(
                (x0, y0),
                x1 - x0,
                y1 - y0,
                fc=height_colour(p["z"][1]),
                ec=INK if full else "none",
                lw=0.5,
                hatch="////" if fins else None,
                zorder=5,
            )
        )
    for s in lay["seats"]:
        ax.add_patch(Polygon(seat_poly(s), closed=True, fc="#ece3d2", ec=MUTE, lw=0.9, zorder=3))
        ex, ey, _ = s["eye"]
        ax.add_patch(Circle((ex, ey), 0.10 if full else 0.12, fc="#3d352d", ec="none", zorder=7))
        if s["kind"] == "lying":
            if full:
                ax.add_patch(Circle((ex, ey), 0.18, fc="none", ec=SIGHT, lw=1.3, zorder=7))
        else:
            fx, fy = s["facing"]
            n = 1.05 if s["kind"] == "recline" else 0.85
            ax.add_patch(
                FancyArrowPatch(
                    (ex + fx * 0.12, ey + fy * 0.12),
                    (ex + fx * n, ey + fy * n),
                    arrowstyle="-|>",
                    mutation_scale=16 if full else 9,
                    color=SIGHT if full else MUTE,
                    lw=2.0 if full else 0.9,
                    zorder=8,
                )
            )
    eyes = {s["id"]: s["eye"] for s in lay["seats"]}
    if not full:
        for a, b, _ in st["face_list"]:
            ax.plot(
                [eyes[a][0], eyes[b][0]],
                [eyes[a][1], eyes[b][1]],
                color="#e59a3a",
                lw=0.35,
                alpha=0.5,
                zorder=9,
            )
        for a, b, _ in st["mutual_gaze_list"]:
            ax.plot(
                [eyes[a][0], eyes[b][0]], [eyes[a][1], eyes[b][1]], color=BAD, lw=1.3, zorder=10
            )
    ax.plot(
        [w[0] for w in lay["walk"]],
        [w[1] for w in lay["walk"]],
        ls="none",
        marker="o",
        ms=2.6 if full else 1.4,
        color=WALK,
        zorder=6,
    )
    ax.set_aspect("equal")
    ax.set_xlim(-0.25, 10.75)
    ax.set_ylim(3.35, 9.2)
    ax.axis("off")


def dim(ax, p0, p1, text, off=(0, 0), fs=11, colour=INK):
    ax.annotate(
        "",
        xy=p0,
        xytext=p1,
        arrowprops=dict(arrowstyle="<->", color=colour, lw=1.1, shrinkA=0, shrinkB=0),
        zorder=12,
    )
    ax.text(
        (p0[0] + p1[0]) / 2 + off[0],
        (p0[1] + p1[1]) / 2 + off[1],
        text,
        fontsize=fs,
        color=colour,
        ha="center",
        va="center",
        zorder=13,
        bbox=dict(fc="#fffdf8", ec="none", pad=1.2, alpha=0.9),
    )


def note(ax, xy, text, to=None, fs=11, colour=INK, ha="center"):
    if to:
        ax.annotate(
            text,
            xy=to,
            xytext=xy,
            fontsize=fs,
            color=colour,
            ha=ha,
            va="center",
            zorder=13,
            arrowprops=dict(arrowstyle="-", color=colour, lw=0.8),
            bbox=dict(fc="#fffdf8", ec="none", pad=1.5, alpha=0.92),
        )
    else:
        ax.text(
            xy[0],
            xy[1],
            text,
            fontsize=fs,
            color=colour,
            ha=ha,
            va="center",
            zorder=13,
            bbox=dict(fc="#fffdf8", ec="none", pad=1.5, alpha=0.92),
        )


def person(ax, x, eye, colour=WALK, label=None):
    top = eye + 0.12
    ax.plot([x, x], [0, top - 0.11], color=colour, lw=2.2, zorder=6, solid_capstyle="round")
    ax.add_patch(Circle((x, top - 0.02), 0.10, fc="none", ec=colour, lw=2.0, zorder=6))
    ax.plot([x], [eye], marker="o", ms=5, color=colour, zorder=7)
    if label:
        ax.text(x, top + 0.16, label, fontsize=10.5, color=colour, ha="center", va="bottom")


def section_frame(ax, x0, x1, title, ceiling=RL.H):
    ax.set_facecolor(PAPER)
    ax.add_patch(Rectangle((x0, 0), x1 - x0, ceiling, fc="#fffdf8", ec="none", zorder=0))
    ax.plot([x0, x1], [0, 0], color=INK, lw=2.2, zorder=4)
    ax.plot([x0, x1], [ceiling, ceiling], color=INK, lw=1.4, zorder=4)
    for z in (0.5, 1.0, 1.5, 2.0, 2.5):
        ax.plot([x0, x1], [z, z], color="#e6dfd2", lw=0.6, zorder=1)
        ax.text(x0 - 0.05, z, f"{z:.1f}", fontsize=8.5, color=MUTE, ha="right", va="center")
    ax.set_title(title, fontsize=13.5, color=INK, loc="left", pad=8)
    ax.set_aspect("equal")
    ax.set_xlim(x0 - 0.28, x1 + 0.1)
    ax.set_ylim(-0.62, ceiling + 0.42)
    ax.axis("off")


def caption(ax, x0, text):
    ax.text(x0, -0.36, text, fontsize=10.5, color=INK, ha="left", va="top", linespacing=1.45)


def profile(ax, origin, direction, pts, colour="#6b5a45"):
    xs = [origin + direction * s for s, _ in pts]
    zs = [z for _, z in pts]
    ax.plot(xs, zs, color=colour, lw=4.5, solid_capstyle="round", zorder=5)
    for s in (pts[1][0], pts[-3][0]):
        z = dict(pts).get(s, 0.3)
        ax.plot([origin + direction * s] * 2, [0, z - 0.03], color=colour, lw=1.6, zorder=4)


def sight(ax, a, b, state, lw=1.6):
    if state == "blocked":
        ax.plot([a[0], b[0]], [a[1], b[1]], color=BAD, lw=lw, ls=(0, (4, 3)), zorder=8)
        ax.plot([b[0]], [b[1]], marker="x", ms=9, mew=2.2, color=BAD, zorder=9)
    else:
        ax.add_patch(
            FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=13, color=SIGHT, lw=lw, zorder=8)
        )


def main():
    cur, v3 = RL.layout_v5(), RL.layout_v3()
    s5, s4, s3, chk = RL.study(cur), RL.study(RL.layout_v4()), RL.study(v3), RL.checks()
    seats = {s["id"]: s for s in cur["seats"]}
    part = {}
    for p in cur["partitions"]:
        part.setdefault(p["label"], p)  # first panel of each kind (they share one outline per kind)

    def silhouette(p, z0=None):
        """Side elevation polygon (world coordinate along the panel, z) from the same outline the model uses."""
        x0, y0, x1, y1 = p["rect"]
        along_x = (x1 - x0) >= (y1 - y0)
        s0, s1 = (x0, x1) if along_x else (y0, y1)
        pts = [((s1 - d) if p["root"] == "end" else (s0 + d), z) for d, z in p["outline"]]
        zb = p["z"][0] if z0 is None else z0
        return pts + [(pts[-1][0], zb), (pts[0][0], zb)]

    ray = None
    rp = DATA / "verification" / "rest_sight_raycast.json"
    if rp.exists():
        ray = json.loads(rp.read_text(encoding="utf-8"))
    fig = plt.figure(figsize=(24, 16.6), dpi=100, facecolor=PAPER)
    gs = fig.add_gridspec(
        2,
        3,
        height_ratios=[1.5, 1.0],
        width_ratios=[1.17, 1.3, 1.0],
        left=0.012,
        right=0.992,
        top=0.908,
        bottom=0.012,
        hspace=0.05,
        wspace=0.03,
    )
    fig.text(
        0.014,
        0.972,
        "休憩の視線・仕切り・主通路（v6 検討図：席・仕切り・通路はv5から変更なし）",
        fontsize=25,
        color=INK,
        weight="bold",
        va="center",
    )
    fig.text(
        0.014,
        0.944,
        "模型と同じ座標（blender/sauna/rest_layout.py）から作図。目の高さ・見える角度・通路幅は検討用の仮定で、プライバシー・避難・法適合・施工の成立を保証しない。",
        fontsize=12.5,
        color=MUTE,
        va="center",
    )

    # ---------------- plan v5 ----------------
    ax = fig.add_subplot(gs[0, 0:2])
    draw_plan(ax, cur, s5, True)
    ax.set_title(
        "平面  v5：席・通路・入口はv4と同じ。仕切りの上端だけを肩落ち・斜めに（色＝その位置の実際の高さ）",
        fontsize=15,
        color=INK,
        loc="left",
        pad=4,
    )
    for s in cur["seats"]:
        ex, ey, _ = s["eye"]
        hx, hy = s["heading"]
        ax.text(
            ex + hx * 0.02 + (0.24 if hx == 0 else 0),
            ey + (0.20 if hy == 0 else 0.0) + (0.02 if hx == 0 else 0),
            s["id"],
            fontsize=10.5,
            color=INK,
            ha="center",
            va="center",
            zorder=11,
            weight="bold",
        )
    pl = RL.PLATFORM
    dim(
        ax,
        (0.45, RL.HB_Y1),
        (0.45, pl["y_front"]),
        f"主通路 {chk['main_aisle_width']:.2f} m",
        off=(0.66, 0.34),
    )
    for i, (e0, e1) in enumerate(RL.entries):
        dim(ax, (e0, 5.50), (e1, 5.50), f"入口 {e1 - e0:.3f}", off=(0, 0.17), fs=10)
        ax.add_patch(
            FancyArrowPatch(
                ((e0 + e1) / 2, 6.30),
                ((e0 + e1) / 2, 4.62),
                arrowstyle="-|>",
                mutation_scale=14,
                color=WALK,
                lw=1.6,
                ls=(0, (3, 2)),
                zorder=9,
            )
        )
        ax.add_patch(Circle(((e0 + e1) / 2, 4.92), 0.30, fc="none", ec=WALK, lw=1.2, zorder=9))
        side = (
            [((e0 + e1) / 2, e0 - 0.06)]
            if i == 0
            else [((e0 + e1) / 2, e0 - 0.06), ((e0 + e1) / 2, e1 + 0.06)]
        )
        for a, b in side:
            ax.add_patch(
                FancyArrowPatch(
                    (a, 4.55),
                    (b, 4.55),
                    arrowstyle="-|>",
                    mutation_scale=10,
                    color=WALK,
                    lw=1.2,
                    zorder=9,
                )
            )
    e0, e1 = RL.entries[1]
    dim(
        ax,
        (e0 - 0.06, 4.22),
        (e1 + 0.06, 4.22),
        f"席の縁の間 {chk['main_entry_between_loungers']:.3f}",
        off=(0, -0.17),
        fs=10,
    )
    note(
        ax,
        (0.1, 3.50),
        "席への入り方（青の破線）：入口は袖壁の間0.55 m長だけ狭く、その先は席の側面1.27 mが開く。○＝直径0.60 mの人の占有（仮）。腰掛けてから足を上げる想定。",
        fs=10,
        ha="left",
        colour=WALK,
    )
    dim(
        ax,
        (pl["x1"] + 0.055, 7.25),
        (RL.EAST_MAIN, 7.25),
        f"扉前 {chk['door_landing_width']:.2f}",
        off=(0, 0.17),
        fs=10,
    )
    yc = RL.SOUTH + 0.05 + RL.LOUNGER_W / 2
    yn = RL.EXT_NORTH - 0.05 - RL.CHAIR_W / 2
    dim(
        ax,
        (9.30, yc + 0.37),
        (9.30, yn - 0.35),
        f"延長通路 {chk['extension_aisle_width']:.2f}",
        off=(0.66, 0),
        fs=10,
    )
    dim(
        ax,
        (RL.EXT_X0, 6.20),
        (6.95, 6.20),
        f"合流 {chk['junction_width']:.2f}",
        off=(0, 0.16),
        fs=10,
    )
    dim(
        ax,
        (7.79, 5.62),
        (8.55, 5.62),
        f"足元 {chk['extension_chair_front_zone']:.2f}",
        off=(0, -0.17),
        fs=10,
    )
    note(ax, (5.96, 7.55), "浴室扉", fs=11, ha="left")
    ax.plot(
        [RL.EAST_MAIN, RL.EAST_MAIN],
        list(RL.DOOR),
        color="#3aa0c8",
        lw=5,
        zorder=6,
        solid_capstyle="butt",
    )
    note(
        ax,
        (2.45, 9.08),
        f"寝台6：頭は北壁側。仕切りは頭〜肩1.10 m高、壁から{RL.SOFT['div_level']:.2f} mで斜めに下がり足先{RL.SOFT['div_foot']:.2f} m",
        fs=11,
    )
    note(
        ax,
        (6.42, 8.20),
        "寝台東端：腰壁1.30 m＋上部格子（扉前から頭を見せない・風は通す）",
        to=(pl["x1"] + 0.03, 8.35),
        fs=10,
        ha="left",
    )
    note(
        ax,
        (3.75, 6.14),
        "ヘッドボード1.30 m高（床から80 mm浮かせ足元灯・清掃の逃げ）＋袖壁0.55 m",
        to=(2.0, RL.HB_Y1 - 0.02),
        fs=10.5,
    )
    note(ax, (4.10, 5.05), "腰壁1.30 m\n（隣ペアとの境）", to=(3.72, 5.1), fs=9.5, ha="left")
    note(
        ax,
        (8.3, 6.95),
        "延長：同じ東向きの縦列。前席のヘッドボード背面を見る。通路側に袖壁0.80／0.75 m",
        fs=10.5,
    )
    note(
        ax,
        (7.75, 6.60),
        "背付き椅子U1・U2：背板と袖壁1.45 m高",
        to=(7.3, yn - 0.33),
        fs=10.5,
        ha="left",
    )
    # legend
    lx, ly = 6.5, 9.02
    for k, (z, lab) in enumerate(
        ((0.62, "0.62 m"), (1.10, "1.10 m"), (1.30, "1.30 m"), (1.45, "1.45 m"))
    ):
        ax.add_patch(
            Rectangle(
                (lx + k * 0.78, ly), 0.2, 0.12, fc=height_colour(z), ec=INK, lw=0.5, zorder=12
            )
        )
        ax.text(lx + k * 0.78 + 0.25, ly + 0.06, lab, fontsize=10, color=INK, va="center")
    ax.add_patch(
        Rectangle(
            (lx + 3.12, ly), 0.2, 0.12, fc="none", ec="#7d4f24", lw=0.8, hatch="||||", zorder=12
        )
    )
    ax.text(lx + 3.37, ly + 0.06, "上部格子（天井まで）", fontsize=10, color=INK, va="center")
    ax.text(lx - 0.1, ly + 0.06, "仕切りの高さ", fontsize=10.5, color=INK, va="center", ha="right")
    ax.add_patch(
        FancyArrowPatch(
            (lx, ly - 0.2),
            (lx + 0.5, ly - 0.2),
            arrowstyle="-|>",
            mutation_scale=14,
            color=SIGHT,
            lw=2,
        )
    )
    ax.text(
        lx + 0.58,
        ly - 0.2,
        "正面の視線　◎＝仰向け（天井を見る）",
        fontsize=10,
        color=INK,
        va="center",
    )
    ax.plot([lx + 0.25], [ly - 0.42], marker="o", ms=3.2, color=WALK)
    ax.text(
        lx + 0.58,
        ly - 0.42,
        f"歩行者の検討点（目1.55 m・{len(cur['walk'])}点）　淡黄＝通路",
        fontsize=10,
        color=INK,
        va="center",
    )

    # ---------------- plan v3 + numbers ----------------
    sub = gs[0, 2].subgridspec(2, 1, height_ratios=[0.72, 1.0], hspace=0.04)
    ax = fig.add_subplot(sub[0])
    draw_plan(ax, v3, s3, False)
    ax.set_title(
        "比較  v3：赤＝正面で目が合う組　橙＝顔が見える視線",
        fontsize=13.5,
        color=INK,
        loc="left",
        pad=4,
    )
    ax = fig.add_subplot(sub[1])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    kinds = lambda s: f"{s['by_kind']['lying']}/{s['by_kind']['recline']}/{s['by_kind']['upright']}"  # noqa: E731
    cols = (s3, s4, s5)
    rows = [
        ("", "v3", "v4", "v5"),
        ("休憩の席数", *(f"{s['seats']}" for s in cols)),
        ("　寝台／リクライニング／背付き", "6/6/10", kinds(s4), kinds(s5)),
        ("正面で目が合う組（双方60°以内）", *(f"{s['mutual_gaze_pairs']}" for s in cols)),
        ("他席の顔が見える視線（開放）", *(f"{s['face_sightlines_open']}" for s in cols)),
        ("　同（格子越し）", *(f"{s['face_sightlines_filtered']}" for s in cols)),
        (
            "通路から顔が見える割合 座る席 平均",
            *(f"{s['aisle_exposure_seated_mean']} %" for s in cols),
        ),
        ("　同  座る席 最大", *(f"{s['aisle_exposure_seated_max']} %" for s in cols)),
        ("　同  寝台 平均", *(f"{s['aisle_exposure_lying_mean']} %" for s in cols)),
        ("　同  寝台 最大", *(f"{s['aisle_exposure_lying_max']} %" for s in cols)),
    ]
    y = 0.975
    for i, (a, b, c, d) in enumerate(rows):
        w = "bold" if i == 0 else "normal"
        ax.text(0.02, y, a, fontsize=12, color=INK, va="center", weight=w)
        ax.text(
            0.68, y, b, fontsize=12.5, color=BAD if i else INK, va="center", ha="right", weight=w
        )
        ax.text(
            0.82, y, c, fontsize=12.5, color=MUTE if i else INK, va="center", ha="right", weight=w
        )
        ax.text(
            0.97,
            y,
            d,
            fontsize=12.5,
            color=SIGHT if i else INK,
            va="center",
            ha="right",
            weight="bold",
        )
        ax.plot([0.02, 0.97], [y - 0.031, y - 0.031], color="#ddd5c6", lw=0.8)
        y -= 0.062
    a = s5["assumptions"]
    txt = (
        f"仮定：目の高さ リクライニング{a['eye_height_m']['recline']:.2f}／背付き{a['eye_height_m']['upright']:.2f}／\n"
        f"　寝台{a['eye_height_m']['lying']:.2f}／歩行{a['eye_height_m']['walk']:.2f} m。人は目の位置の点。距離{a['range_m']:.0f} m以内。\n"
        f"見る側は正面±{a['look_limit_deg']:.0f}°まで、顔は正面±{a['face_limit_deg']:.0f}°から見えるとした。\n"
        "寝台は全方向から顔が見える扱い。格子は「格子越し」、ガラス扉は素通し。\n"
        "v5の遮蔽は旧い矩形ではなく、模型と同じ上端の輪郭で判定（丸めて空いた部分は素通し）。\n"
    )
    if ray:
        c = ray["line_comparison"]
        txt += (
            f"補助確認：実メッシュへのレイ {c['lines']}本。解析で遮蔽なのにメッシュで抜ける線 {c['analytic_blocked_mesh_open']}本、\n"
            f"　解析で開放・メッシュで遮蔽 {c['analytic_open_mesh_blocked']}本。メッシュ側の集計も 目が合う組 {ray['mesh']['mutual_gaze_pairs']}・"
            f"顔の視線 {ray['mesh']['face_sightlines_open']}。\n"
        )
    txt += (
        "通路から最も見えるのは延長南列のR6（合流部から斜め前方。v4と同じ）。\n"
        "席数・通路幅・入口幅はv4から変えていない（浴室の造り付け2席は別計上）。"
    )
    ax.text(0.02, y - 0.005, txt, fontsize=10.4, color=INK, va="top", linespacing=1.5)

    # ---------------- section A: north-south through R2 ----------------
    r2 = seats["R2"]
    ax = fig.add_subplot(gs[1, 0])
    section_frame(
        ax,
        RL.SOUTH,
        RL.NORTH,
        f"断面A  南北（R2の位置 x={r2['eye'][0]:.2f}）：壁向き席・主通路・寝台",
    )
    ax.plot([RL.SOUTH, RL.SOUTH], [0, RL.H], color=INK, lw=3)
    ax.plot([RL.NORTH, RL.NORTH], [0, RL.H], color=INK, lw=3)
    profile(ax, RL.FOOT_Y, 1, LOUNGER_PROFILE)
    ax.add_patch(
        Rectangle(
            (RL.HB_Y0, 0.08),
            RL.HB_Y1 - RL.HB_Y0,
            RL.HB - 0.08,
            fc=height_colour(RL.HB),
            ec=INK,
            lw=0.6,
            zorder=5,
        )
    )
    ax.add_patch(
        Polygon(
            silhouette(part["腰壁"]),
            closed=True,
            fc=height_colour(RL.HB),
            ec="#7d4f24",
            lw=0.8,
            ls=(0, (3, 2)),
            alpha=0.16,
            zorder=2,
        )
    )
    ax.add_patch(
        Polygon(
            silhouette(part["袖壁"]),
            closed=True,
            fc=height_colour(RL.HB),
            ec="#7d4f24",
            lw=1.0,
            alpha=0.34,
            zorder=3,
        )
    )
    ax.add_patch(
        Rectangle(
            (pl["y_front"], 0),
            pl["y_wall"] - pl["y_front"],
            pl["top"],
            fc="#e6d6ba",
            ec=INK,
            lw=0.8,
            zorder=4,
        )
    )
    ax.add_patch(
        Polygon(
            silhouette(part["寝台の仕切り"], pl["top"]),
            closed=True,
            fc=height_colour(RL.DIV_TALL),
            ec="#7d4f24",
            lw=1.0,
            alpha=0.75,
            zorder=3,
        )
    )
    eye_r = (r2["eye"][1], RL.EYE["recline"])
    ax.add_patch(Circle((eye_r[0], eye_r[1] + 0.02), 0.10, fc="none", ec=SIGHT, lw=2, zorder=7))
    ax.plot([eye_r[0]], [eye_r[1]], marker="o", ms=5, color=SIGHT, zorder=8)
    sight(ax, (eye_r[0] - 0.1, eye_r[1] + 0.02), (RL.SOUTH + 0.03, 1.55), "open")
    wy = 6.40
    person(ax, wy, RL.EYE["walk"], label="歩行者 1.55")
    # grazing line over the headboard cap
    k = (RL.EYE["walk"] - RL.HB) / (wy - RL.HB_Y0)
    y_hit = RL.HB_Y0 - (RL.HB - 0.36) / k
    ax.add_patch(
        Polygon(
            [(RL.HB_Y0, RL.HB), (RL.HB_Y0, 0.0), (max(RL.SOUTH, RL.HB_Y0 - RL.HB / k), 0.0)],
            closed=True,
            fc=BAD,
            ec="none",
            alpha=0.10,
            zorder=2,
        )
    )
    ax.plot(
        [wy, max(RL.SOUTH, RL.HB_Y0 - RL.HB / k)],
        [
            RL.EYE["walk"],
            max(0.0, RL.EYE["walk"] - k * (wy - RL.SOUTH))
            if RL.HB_Y0 - RL.HB / k < RL.SOUTH
            else 0.0,
        ],
        color=WALK,
        lw=1.0,
        ls=(0, (2, 2)),
        zorder=7,
    )
    sight(
        ax,
        (wy, RL.EYE["walk"]),
        (
            RL.HB_Y1,
            RL.EYE["walk"] - (RL.EYE["walk"] - eye_r[1]) * (wy - RL.HB_Y1) / (wy - eye_r[0]),
        ),
        "blocked",
    )
    eye_l = (pl["y_front"] + RL.EYE_S["lying"], RL.EYE["lying"])
    ax.add_patch(Circle((eye_l[0], eye_l[1] + 0.02), 0.10, fc="none", ec=SIGHT, lw=2, zorder=7))
    ax.plot(
        [eye_l[0] - 0.12, eye_l[0] - 1.55],
        [eye_l[1] - 0.06, eye_l[1] - 0.10],
        color=SIGHT,
        lw=5,
        alpha=0.5,
        solid_capstyle="round",
        zorder=6,
    )
    sight(ax, (eye_l[0], eye_l[1] + 0.14), (eye_l[0], 2.45), "open")
    dim(ax, (RL.HB_Y1 + 0.16, 0.0), (RL.HB_Y1 + 0.16, RL.HB), "1.30", off=(0.2, -0.2), fs=10)
    dim(
        ax,
        (RL.HB_Y1, -0.16),
        (pl["y_front"], -0.16),
        f"主通路 {chk['main_aisle_width']:.2f}",
        fs=10,
    )
    dim(ax, (RL.SOUTH, -0.16), (RL.FOOT_Y, -0.16), f"{chk['lounger_foot_to_south_wall']:.2f}", fs=9)
    dim(
        ax,
        (pl["y_wall"] - 0.14, pl["top"]),
        (pl["y_wall"] - 0.14, RL.DIV_TALL),
        "1.10",
        off=(-0.22, 0.12),
        fs=10,
    )
    ax.text(eye_r[0] - 0.12, 1.40, "目0.90", fontsize=10, color=SIGHT, ha="center")
    ax.text(eye_l[0] - 0.42, eye_l[1] + 0.2, "目0.56", fontsize=10, color=SIGHT, ha="center")
    ax.text(4.28, 1.86, "南壁の淡い壁洗いを見る", fontsize=10, color=SIGHT, ha="center")
    ax.text(
        7.62,
        1.16,
        f"仕切り：頭〜肩は1.10、\n壁から{RL.SOFT['div_level']:.2f} mで斜めに下がり\n足先{RL.SOFT['div_foot']:.2f}",
        fontsize=9.5,
        color=INK,
        ha="center",
        va="bottom",
    )
    wa, wb = RL.SOFT["wing"]
    ax.text(
        5.02,
        1.42,
        f"袖壁の肩\n（先端{RL.HB - wb:.2f}）",
        fontsize=9,
        color="#7d4f24",
        ha="center",
        va="bottom",
    )
    ax.text(
        4.60,
        0.62,
        f"腰壁（破線）\n足側へ{RL.HB - RL.SOFT['waist'][1]:.2f}まで",
        fontsize=9,
        color="#7d4f24",
        ha="center",
        va="center",
    )
    seen = "席全体が背板の陰" if y_hit < RL.FOOT_Y else f"見えるのは y<{y_hit:.2f} の足先だけ"
    caption(
        ax,
        RL.SOUTH,
        f"赤の網＝通路中央（y=6.40）の歩行者から背板越しに見えない範囲。{seen}（入口の隙間を除く）。\n淡い茶＝袖壁0.55 mと腰壁（奥行方向に離れた位置）。輪郭は模型と同じ座標。寝台は正面に立った人からだけ見える。",
    )
    ax.text(RL.SOUTH + 0.02, RL.H + 0.12, "南壁", fontsize=10, color=MUTE)
    ax.text(RL.NORTH - 0.02, RL.H + 0.12, "北壁", fontsize=10, color=MUTE, ha="right")

    # ---------------- section B: east-west through the lying heads ----------------
    ax = fig.add_subplot(gs[1, 1])
    section_frame(
        ax,
        RL.WEST,
        RL.EAST_MAIN,
        f"断面B  東西（寝台の頭の位置 y={eye_l[0]:.2f}）：寝台6・東端の腰壁と格子・扉前",
    )
    ax.plot([RL.WEST, RL.WEST], [0, RL.H], color=INK, lw=3)
    ax.plot([RL.EAST_MAIN, RL.EAST_MAIN], [0, RL.H], color="#3aa0c8", lw=3)
    ax.add_patch(
        Rectangle(
            (pl["x0"], 0), pl["x1"] - pl["x0"], pl["top"], fc="#e6d6ba", ec=INK, lw=0.8, zorder=4
        )
    )
    pitch = (pl["x1"] - pl["x0"]) / pl["n"]
    heads = []
    for kk in range(pl["n"]):
        cx = pl["x0"] + (kk + 0.5) * pitch
        heads.append(cx)
        ax.add_patch(
            Circle((cx, RL.EYE["lying"] + 0.02), 0.10, fc="none", ec=SIGHT, lw=2, zorder=7)
        )
        ax.add_patch(
            Rectangle(
                (cx - 0.30, pl["top"]), 0.60, 0.05, fc="#3d352d", ec="none", alpha=0.55, zorder=5
            )
        )
        ax.text(
            cx,
            0.20,
            f"L{kk + 1}",
            fontsize=10.5,
            color=INK,
            ha="center",
            va="center",
            weight="bold",
            zorder=6,
        )
        sight(ax, (cx, RL.EYE["lying"] + 0.14), (cx, 1.75), "open", lw=1.2)
        if kk:
            x = pl["x0"] + kk * pitch
            ax.add_patch(
                Rectangle(
                    (x - 0.015, pl["top"]),
                    0.03,
                    RL.DIV_TALL - pl["top"],
                    fc=height_colour(RL.DIV_TALL),
                    ec=INK,
                    lw=0.5,
                    zorder=5,
                )
            )
    for a, b in zip(heads, heads[1:]):
        ax.plot(
            [a + 0.11, (a + b) / 2 - 0.02],
            [RL.EYE["lying"] + 0.02] * 2,
            color=BAD,
            lw=1.4,
            ls=(0, (3, 2)),
            zorder=8,
        )
        ax.plot(
            [(a + b) / 2 - 0.03],
            [RL.EYE["lying"] + 0.02],
            marker="x",
            ms=7,
            mew=1.8,
            color=BAD,
            zorder=9,
        )
    xe = pl["x1"] + 0.005
    ax.add_patch(
        Rectangle((xe, 0), RL.DIV_T, RL.HB, fc=height_colour(RL.HB), ec=INK, lw=0.5, zorder=5)
    )
    ax.add_patch(
        Rectangle(
            (xe, RL.HB),
            RL.DIV_T,
            RL.H - RL.HB,
            fc="none",
            ec="#7d4f24",
            lw=0.8,
            hatch="----",
            zorder=5,
        )
    )
    wx = 5.36
    person(ax, wx, RL.EYE["walk"], label="扉前の歩行者 1.55")
    tz = RL.EYE["walk"] - (RL.EYE["walk"] - RL.EYE["lying"]) * (wx - xe - RL.DIV_T) / (
        wx - heads[-1]
    )
    sight(ax, (wx, RL.EYE["walk"]), (xe + RL.DIV_T, tz), "blocked")
    dim(ax, (heads[1], -0.16), (heads[2], -0.16), f"寝台の割付 {chk['lying_pitch']:.3f}", fs=10)
    dim(
        ax,
        (xe + RL.DIV_T, -0.16),
        (RL.EAST_MAIN, -0.16),
        f"扉前 {chk['door_landing_width']:.2f}",
        fs=10,
    )
    dim(ax, (0.30, pl["top"]), (0.30, RL.DIV_TALL), "仕切り上端1.10", off=(0.42, 0.52), fs=10)
    ax.text(xe - 0.1, 1.72, "腰壁1.30＋格子", fontsize=10, color=INK, ha="right")
    ax.text(2.45, 1.95, "仰向けの視線は天井へ（目0.56 m）", fontsize=10.5, color=SIGHT, ha="center")
    caption(
        ax,
        RL.WEST,
        "隣の頭とは高さ1.10 mの仕切りで切る（頭〜肩の0.95 m。その先は足先へ斜めに下げて風と清掃を通す）。\n扉前の歩行者からL6の頭は、東端の腰壁1.30 mで遮る。上部は格子で天井まで（風は通る）。",
    )
    ax.text(RL.EAST_MAIN - 0.04, RL.H + 0.12, "浴室扉", fontsize=10, color="#3aa0c8", ha="right")

    # ---------------- section C: extension, east-west through the south file ----------------
    ax = fig.add_subplot(gs[1, 2])
    section_frame(
        ax, RL.EXT_X0, RL.EXT_EAST, f"断面C  東西（延長の南列 y={yc:.2f}）：同方向の縦列 R6・R7"
    )
    ax.plot([RL.EXT_EAST, RL.EXT_EAST], [0, RL.H], color=INK, lw=3)
    for i, sid in enumerate(("R6", "R7")):
        s = seats[sid]
        hb = s["foot"][0] - RL.LOUNGER_L - 0.08
        ax.add_patch(
            Rectangle(
                (hb, 0.08), 0.06, RL.HB - 0.08, fc=height_colour(RL.HB), ec=INK, lw=0.6, zorder=5
            )
        )
        wing = next(
            p
            for p in cur["partitions"]
            if p["label"] == "袖壁" and abs(p["rect"][0] - (hb + 0.06)) < 1e-6
        )
        ax.add_patch(
            Polygon(
                silhouette(wing),
                closed=True,
                fc=height_colour(RL.HB),
                ec="#7d4f24",
                lw=1.0,
                alpha=0.34,
                zorder=3,
            )
        )
        if i == 0:
            ax.add_patch(
                Rectangle(
                    (hb, RL.HB),
                    0.06,
                    RL.H - RL.HB,
                    fc="none",
                    ec="#7d4f24",
                    lw=0.8,
                    hatch="----",
                    zorder=5,
                )
            )
        profile(ax, s["foot"][0], -1, LOUNGER_PROFILE)
        ex = s["eye"][0]
        ax.add_patch(
            Circle((ex, RL.EYE["recline"] + 0.02), 0.10, fc="none", ec=SIGHT, lw=2, zorder=7)
        )
        ax.plot([ex], [RL.EYE["recline"]], marker="o", ms=5, color=SIGHT, zorder=8)
        ax.text(
            ex + 0.02,
            RL.EYE["recline"] + 0.22,
            sid,
            fontsize=10.5,
            color=INK,
            ha="center",
            weight="bold",
        )
    e6, e7 = seats["R6"]["eye"][0], seats["R7"]["eye"][0]
    hb7 = seats["R7"]["foot"][0] - RL.LOUNGER_L - 0.08
    sight(ax, (e6 + 0.12, RL.EYE["recline"] + 0.03), (hb7 - 0.01, 1.16), "open")
    sight(ax, (e6 + 0.12, RL.EYE["recline"]), (hb7, RL.EYE["recline"]), "blocked", lw=1.2)
    sight(ax, (e7 + 0.12, RL.EYE["recline"] + 0.03), (RL.EXT_EAST - 0.03, 1.5), "open")
    dim(ax, (hb7 + 0.2, 0.0), (hb7 + 0.2, RL.HB), "1.30", off=(0.22, -0.25), fs=10)
    dim(ax, (hb7 - 0.30, -0.16), (hb7, -0.16), "0.30", fs=9)
    ax.text(
        7.25,
        1.62,
        "前席の背板の裏を見る\n（前の人の頭は背板の陰）",
        fontsize=10,
        color=SIGHT,
        ha="center",
    )
    ax.text(9.6, 1.75, "東壁の\n淡い光", fontsize=10, color=SIGHT, ha="center")
    caption(
        ax,
        RL.EXT_X0,
        "R6の正面はR7のヘッドボード背面（1.30 m）。R7の頭（目0.90 m）はその陰。\n淡い茶＝通路側の袖壁0.80 m（先端だけ小さく丸め、頭の横は1.30 mのまま）。",
    )
    ax.text(RL.EXT_EAST - 0.03, RL.H + 0.12, "東壁", fontsize=10, color=MUTE, ha="right")

    out = DATA / "diagrams"
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "rest_sightlines_v6.png", dpi=100, facecolor=PAPER)
    ver = DATA / "verification"
    ver.mkdir(parents=True, exist_ok=True)
    record = {
        "source": "blender/sauna/rest_layout.py (same coordinates as the model)",
        "limits": "検討用の仮定に基づく幾何チェック。プライバシー・避難・法適合・施工の成立を保証しない。",
        "v3": s3,
        "v4": s4,
        "v5": s5,
        "clearances_m": chk,
        "top_edge_shapes_m": RL.SOFT,
        "seats_v5": [
            {
                "id": s["id"],
                "kind": s["kind"],
                "group": s["group"],
                "eye": [round(v, 3) for v in s["eye"]],
                "facing": list(s["facing"]),
            }
            for s in cur["seats"]
        ],
        "partitions_v5": [
            {
                "label": p["label"],
                "kind": p["kind"],
                "rect": [round(v, 3) for v in p["rect"]],
                "z": list(p["z"]),
                **(
                    {
                        "root": p["root"],
                        "outline_d_z": [[round(d, 3), round(z, 3)] for d, z in p["outline"]],
                    }
                    if "outline" in p
                    else {}
                ),
            }
            for p in cur["partitions"]
        ],
        "mesh_raycast": "verification/rest_sight_raycast.json" if ray else None,
        "entries_main_x": [[round(a, 3), round(b, 3)] for a, b in RL.entries],
    }
    (ver / "rest_sightline_study.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(out / "rest_sightlines_v6.png")
    keys = (
        "seats",
        "mutual_gaze_pairs",
        "face_sightlines_open",
        "face_sightlines_filtered",
        "aisle_exposure_seated_mean",
        "aisle_exposure_seated_max",
        "aisle_exposure_lying_mean",
        "aisle_exposure_lying_max",
    )
    print(
        json.dumps(
            {v: {k: s[k] for k in keys} for v, s in (("v3", s3), ("v4", s4), ("v5", s5))}
            | {
                "max_seat": max(
                    ((v, k) for k, v in s5["aisle_exposure_pct"].items() if not k.startswith("L"))
                )
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
