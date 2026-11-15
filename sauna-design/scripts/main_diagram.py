#!/usr/bin/env python3
"""Main sauna v6 check figure: plan with the 20 assumed bodies, feet, step-ups, door, stove and the floor that is really
free for aufguss, plus two sections (headroom, rises). Reads blender/sauna/main_layout.py — the same data the model is
built from — and writes

  <data-root>/diagrams/main_seats_v6.png
  <data-root>/verification/main_seat_study.json

Assumed adult sizes; a concept check, not code compliance, not a heater clearance and not a performer's review.
"""

import sys

sys.dont_write_bytecode = True
import json  # noqa: E402
import math  # noqa: E402
import pathlib  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, Polygon, Rectangle  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "blender"))
from sauna import main_layout as ML  # noqa: E402

V = "v6"
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
    "seat": "#ecd2ac",
    "seat_corner": "#dcb98e",
    "foot": "#c8d9e2",
    "step": "#cfe4c2",
    "landing": "#efe6a4",
    "floor": "#fffdf8",
    "torso": "#7b5d47",
    "thigh": "#b99578",
    "feet": "#3f3129",
    "stove": "#5b504a",
    "free": "#1f7f79",
    "towel": "#b4442f",
    "route": "#2a67ad",
}
D = ML.dims()
S = ML.seats()
HX, HY = ML.HEATER["c"]


def dim(ax, p0, p1, text, off=0.0, fs=10.5, colour=INK, side=0.0):
    """Dimension line p0-p1 shifted sideways by `off`; text sits beside it, `side` further out."""
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
        bbox=dict(fc="#fffdf8", ec="none", pad=1.2, alpha=0.9),
    )


def note(ax, xy, text, to=None, fs=10.5, colour=INK, ha="center", va="center"):
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
            va=va,
            zorder=22,
            bbox=dict(fc="#fffdf8", ec="none", pad=1.5, alpha=0.92),
        )


def arrow(ax, pts, colour=C["route"], lw=2.0, ls="-"):
    for a, b in zip(pts, pts[1:-1]):
        ax.plot(
            [a[0], b[0]],
            [a[1], b[1]],
            color=colour,
            lw=lw,
            ls=ls,
            zorder=18,
            solid_capstyle="round",
        )
    ax.add_patch(
        FancyArrowPatch(
            pts[-2],
            pts[-1],
            arrowstyle="-|>",
            mutation_scale=13,
            color=colour,
            lw=lw,
            ls=ls,
            zorder=18,
        )
    )


def plan(ax):
    ax.set_facecolor(PAPER)
    ax.add_patch(
        Rectangle((ML.XW, ML.YS), ML.XE - ML.XW, ML.YN - ML.YS, fc=C["floor"], ec="none", zorder=1)
    )
    for (
        x0,
        y0,
        x1,
        y1,
    ) in ML.bench_rects():  # bench surface that is neither a counted seat nor a footrest
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#f3ebdc", ec=INK, lw=0.5, zorder=2))
    for kind, label, x0, y0, x1, y1, lvl in ML.zones():
        ax.add_patch(
            Rectangle(
                (x0, y0),
                x1 - x0,
                y1 - y0,
                fc=C[kind],
                ec=INK,
                lw=0.5,
                zorder=2,
                hatch="////" if kind == "seat_corner" else None,
            )
        )
    for tri in ML.diag_treads():
        ax.add_patch(Polygon(tri, closed=True, fc=C["step"], ec=INK, lw=0.5, zorder=2))
    # walls and door
    t = 0.16
    for x0, y0, w, h in (
        (ML.XW - t, ML.YS - t, ML.XE - ML.XW + 2 * t, t),
        (ML.XW - t, ML.YN, ML.XE - ML.XW + 2 * t, t),
        (ML.XW - t, ML.YS, t, ML.YN - ML.YS),
        (ML.XE, ML.YS, t, ML.DOOR[0] - ML.YS),
        (ML.XE, ML.DOOR[1], t, ML.YN - ML.DOOR[1]),
    ):
        ax.add_patch(Rectangle((x0, y0), w, h, fc="#4a433d", ec="none", zorder=3))
    ax.plot(
        [ML.XE + 0.08, ML.XE + 0.08],
        [ML.DOOR[0] + 0.05, ML.DOOR[1] - 0.05],
        color=C["route"],
        lw=3,
        zorder=4,
    )
    note(ax, (ML.XE + 0.82, sum(ML.DOOR) / 2), "扉\n有効0.90 m\n（位置はv5のまま）", fs=10)
    # stove
    ap = D["guard_apothem"]
    ax.add_patch(
        Polygon(
            ML._octagon((HX, HY), ap / math.cos(math.pi / 8)),
            closed=True,
            fc="#e9ded2",
            ec=INK,
            lw=1.6,
            zorder=5,
        )
    )
    ax.add_patch(Circle((HX, HY), ML.HEATER["r"] + 0.05, fc=C["stove"], ec="none", zorder=6))
    ax.text(
        HX,
        HY,
        "ストーブ\nφ0.94\n柵 対辺1.41",
        fontsize=9.5,
        color="#fffdf8",
        ha="center",
        va="center",
        zorder=7,
    )
    # bodies
    for s in S:
        for part, x0, y0, x1, y1, z0, z1 in ML.body_boxes(s):
            if part in ("thighs", "legs"):
                ax.add_patch(
                    Rectangle(
                        (x0, y0), x1 - x0, y1 - y0, fc=C["thigh"], ec="none", alpha=0.85, zorder=9
                    )
                )
            elif part == "feet":
                ax.add_patch(
                    Rectangle(
                        (x0, y0), x1 - x0, y1 - y0, fc=C["feet"], ec="none", alpha=0.9, zorder=10
                    )
                )
            elif part == "torso":
                ax.add_patch(
                    Rectangle((x0, y0), x1 - x0, y1 - y0, fc=C["torso"], ec="none", zorder=11)
                )
            elif part == "head":
                ax.add_patch(
                    Ellipse(
                        ((x0 + x1) / 2, (y0 + y1) / 2),
                        x1 - x0,
                        y1 - y0,
                        fc="#f2e3cf",
                        ec=C["torso"],
                        lw=0.8,
                        zorder=12,
                    )
                )
    acc = ML.access()
    need = set(ML.checks()["seats_needing_cooperation"])
    for (
        kind,
        label,
        x0,
        y0,
        x1,
        y1,
        lvl,
    ) in ML.zones():  # seats that are reached only past someone's feet / knees
        if label in need:
            ax.add_patch(
                Rectangle(
                    (x0 + 0.02, y0 + 0.02),
                    x1 - x0 - 0.04,
                    y1 - y0 - 0.04,
                    fc="none",
                    ec=C["towel"],
                    lw=1.5,
                    ls=(0, (4, 2)),
                    zorder=13,
                )
            )
    for t in ML.standing():  # standing check bodies (also in the 3D check layer)
        _, x0, y0, x1, y1, z0, z1 = ML.standing_boxes(t)[0]
        ax.add_patch(
            Rectangle(
                (x0, y0), x1 - x0, y1 - y0, fc="#6f8fb0", ec="#31506e", lw=1.0, alpha=0.8, zorder=14
            )
        )
        ax.text(
            (x0 + x1) / 2,
            (y0 + y1) / 2,
            t["id"],
            fontsize=8,
            color="#fffdf8",
            ha="center",
            va="center",
            zorder=15,
        )
    for s in S:
        bx, by = s["b"]
        fx, fy = s["f"]
        n = acc[s["id"]]["pass"]
        if s["tier"] == "corner" or s["id"].startswith("NU"):
            pos = (bx, ML.YN + 0.30)
        elif s["id"].startswith("NL"):
            pos = (bx, by - 0.45)
        else:
            pos = (bx - fx * 0.42, by)
        lab = s["id"] + (f"\n前{n}人" if n else "")
        ax.text(
            pos[0],
            pos[1],
            lab,
            fontsize=9.2,
            color=INK,
            ha="center",
            va="center",
            zorder=23,
            linespacing=1.1,
            bbox=dict(fc="#fffdf8", ec="none", pad=0.8, alpha=0.85)
            if s["id"].startswith("NL")
            else None,
        )
    # free floor circles
    for d in ML.floor_discs():
        if "隅" in d["where"]:
            continue
        cx, cy = d["centre"]
        ax.add_patch(
            Circle(
                (cx, cy),
                d["diameter"] / 2,
                fc="none",
                ec=C["free"],
                lw=1.4,
                ls=(0, (5, 3)),
                zorder=14,
            )
        )
        ax.text(
            cx - (0.50 if d["where"].startswith("北") else 0.0),
            cy
            + (
                0.3
                if d["where"].startswith("南（")
                else 0.10
                if d["where"].startswith("北")
                else 0.0
            ),
            f"φ{d['diameter']:.2f}",
            fontsize=10.5,
            color=C["free"],
            ha="center",
            va="center",
            zorder=15,
            weight="bold",
        )
    sw, so = ML.swing_radius(False), ML.swing_radius(True)
    ax.add_patch(
        Circle(
            sw["stand_at"],
            sw["radius"],
            fc=C["towel"],
            ec=C["towel"],
            lw=1.2,
            alpha=0.10,
            zorder=13,
        )
    )
    ax.add_patch(Circle(sw["stand_at"], sw["radius"], fc="none", ec=C["towel"], lw=1.2, zorder=13))
    ax.plot(*sw["stand_at"], marker="x", color=C["towel"], ms=8, mew=2, zorder=16)
    note(
        ax,
        (1.0, 8.52),
        f"タオルを水平に回せる最大半径 {sw['radius']:.2f} m（柵の上を通さない場合）\n一周に要る仮定 {sw['needed_for_full_turn']:.2f} m に届かない",
        to=(sw["stand_at"][0] - 0.3, sw["stand_at"][1] - 0.75),
        fs=10,
        colour=C["towel"],
    )
    # access routes
    door = (ML.XE - 0.05, sum(ML.DOOR) / 2)
    ye = ML.Y_END
    arrow(
        ax,
        [
            door,
            (4.3, 9.75),
            (4.3, 11.3),
            (D["e_step_front"] + 0.14, 11.3),
            (D["e_foot_front"] + 0.2, 11.3),
        ],
    )
    arrow(
        ax,
        [
            (4.3, 11.3),
            (4.3, 12.15),
            (D["e_step_front"] + 0.14, 12.3),
            (D["e_foot_front"] - 0.2, 12.75),
            (D["e_foot_front"] - 0.2, 13.12),
        ],
    )
    arrow(ax, [(D["e_foot_front"] - 0.2, 13.12), (3.9, 13.12)], lw=1.4, ls=(0, (3, 2)))
    arrow(
        ax,
        [
            door,
            (4.3, 9.75),
            (3.0, 9.62),
            (1.75, 9.75),
            (1.75, 11.3),
            (D["w_step_front"] - 0.14, 11.3),
            (D["w_foot_front"] - 0.2, 11.3),
        ],
    )
    arrow(ax, [(4.3, 12.15), (3.75, 12.25), (3.75, 12.42)], lw=1.4)
    # dimensions
    yb = HY
    dim(ax, (D["w_step_front"], yb), (HX - ap, yb), f"{D['aisle_west']:.2f}")
    dim(ax, (HX + ap, yb), (D["e_step_front"], yb), f"{D['aisle_east']:.2f}")
    dim(
        ax,
        (HX + 0.42, HY + ap),
        (HX + 0.42, D["n_lower_front"]),
        f"{D['aisle_north']:.2f}",
        side=-0.22,
    )
    toes = ML.checks()["north_aisle_clear_of_front_row_toes"]
    note(ax, (HX - 0.50, HY + ap + 0.06), f"つま先まで{toes:.2f}\n（1人ずつ）", fs=9.5, colour=MUTE)
    dim(ax, (HX + 0.5, ML.YS), (HX + 0.5, HY - ap), f"{D['floor_south']:.2f}", side=-0.22)
    dim(
        ax,
        (ML.XE - 0.22, ML.DOOR[1]),
        (ML.XE - 0.22, ye),
        f"{D['bench_end_to_door_jamb']:.2f}",
        side=-0.2,
        fs=9.5,
    )
    yd = ye - 0.16
    dim(ax, (ML.XW, yd), (D["w_upper_front"], yd), "0.60", fs=9)
    dim(ax, (D["w_upper_front"], yd), (D["w_foot_front"], yd), "0.40", fs=9)
    dim(ax, (D["w_foot_front"], yd), (D["w_step_front"], yd), "0.28", fs=9)
    note(ax, (0.76, ye - 0.47), "座面0.90｜足置き段0.45｜中間段0.225", fs=9.5)
    xd = ML.XW - 0.52
    dim(ax, (xd, ML.YN), (xd, D["n_upper_front"]), "0.60", fs=9)
    dim(ax, (xd, D["n_upper_front"]), (xd, D["n_foot_line"]), "0.30", fs=9)
    dim(ax, (xd, D["n_foot_line"]), (xd, D["n_lower_front"]), "0.50", fs=9)
    dim(
        ax,
        (ML.XW, ML.YS - 0.36),
        (ML.XE, ML.YS - 0.36),
        f"仕上げ内法 {D['room_inner'][0]:.2f}",
        fs=10,
    )
    dim(ax, (ML.XW - 0.86, ML.YS), (ML.XW - 0.86, ML.YN), f"{D['room_inner'][1]:.2f}", fs=10)
    note(
        ax,
        (6.8, 13.8),
        "角は足を上げて座る1人\n（脚を下ろす席に数えない）",
        to=(ML.XE - 0.3, ML.YN - 0.3),
        fs=9.5,
    )
    ls = ML.checks()["north_landing_size"]
    note(
        ax,
        (6.95, 12.46),
        f"踊り場0.45（{ls[0]:.2f}×{ls[1]:.2f} m）\n席も足も置かない",
        to=(D["e_foot_front"] - 0.12, 12.6),
        fs=9.5,
    )
    note(
        ax,
        (6.8, 11.3),
        "東西の席は目の前の\n中間段→足置き段→座る\n（人の前を通らない）",
        to=(D["e_foot_front"] + 0.2, 11.3),
        fs=9.5,
        colour=C["route"],
    )
    note(
        ax,
        (6.8, 13.0),
        "北上段へは踊り場から\n足置き帯を横へ（点線）\n中央2席は2人の前を通る",
        to=(4.0, 13.12),
        fs=9.5,
        colour=C["route"],
    )
    note(ax, (2.75, 9.28), "演者の主位置（南）", fs=10, colour=C["free"])
    ax.text(ML.XW - 0.9, ML.YN + 0.45, "N ↑", fontsize=12, color=MUTE)
    # legend
    lx, ly = -0.85, 8.02
    for k, (key, lab) in enumerate(
        (
            ("seat", "座面（1人ずつ）"),
            ("seat_corner", "角の席（足上げ）"),
            ("foot", "足置き"),
            ("step", "中間段 0.225"),
            ("landing", "踊り場 0.45"),
        )
    ):
        ax.add_patch(
            Rectangle(
                (lx + k * 1.52, ly),
                0.24,
                0.14,
                fc=C[key],
                ec=INK,
                lw=0.5,
                zorder=12,
                hatch="////" if key == "seat_corner" else None,
            )
        )
        ax.text(lx + k * 1.52 + 0.3, ly + 0.07, lab, fontsize=9.8, color=INK, va="center")
    ax.plot([lx, lx + 0.24], [ly - 0.2, ly - 0.2], color=C["free"], lw=1.4, ls=(0, (5, 3)))
    ax.text(
        lx + 0.3,
        ly - 0.2,
        "床に入る最大の円（前列の膝・足と柵を除いた実際の空き）",
        fontsize=9.8,
        color=INK,
        va="center",
    )
    ax.plot([lx + 5.2, lx + 5.44], [ly - 0.2, ly - 0.2], color=C["route"], lw=2)
    ax.text(lx + 5.5, ly - 0.2, "上り口までの動線", fontsize=9.8, color=INK, va="center")
    ax.add_patch(
        Rectangle(
            (lx, ly - 0.47), 0.24, 0.14, fc="none", ec=C["towel"], lw=1.5, ls=(0, (4, 2)), zorder=12
        )
    )
    ax.text(
        lx + 0.3,
        ly - 0.4,
        "着席者の足・膝の前を通らないと着けない席（足を引くなど協力が要る）",
        fontsize=9.8,
        color=INK,
        va="center",
    )
    ax.add_patch(
        Rectangle((lx + 5.2, ly - 0.47), 0.24, 0.14, fc="#6f8fb0", ec="#31506e", lw=1.0, zorder=12)
    )
    ax.text(
        lx + 5.5,
        ly - 0.4,
        "立つ人の確認（T1踊り場・T2中間段・T3北通路・T4演者）",
        fontsize=9.8,
        color=INK,
        va="center",
    )
    ax.set_xlim(-1.05, 7.85)
    ax.set_ylim(7.4, 14.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "平面  メインサウナ v6：中央ストーブを北・西・東の3辺で囲む2段。20人の胴・腿・足を実寸で配置",
        fontsize=14.5,
        color=INK,
        loc="left",
        pad=4,
    )


def body_side(ax, a0, sgn, seat_z, foot_z, feet_up=False, colour=C["torso"]):
    """Seated body in side view: a0 = position of the back plane on the section axis, sgn = +1 facing right."""
    B = ML.BODY

    def r(v0, v1, z0, z1, fc, z=8):
        ax.add_patch(
            Rectangle(
                (min(a0 + sgn * v0, a0 + sgn * v1), z0),
                abs(v1 - v0),
                z1 - z0,
                fc=fc,
                ec="none",
                zorder=z,
            )
        )

    if feet_up:
        r(-0.27, 0.27, seat_z, seat_z + 0.22, C["thigh"])
        r(-0.13, 0.13, seat_z + 0.22, seat_z + B["shoulder_h"], colour)
        ax.add_patch(
            Ellipse(
                (a0, seat_z + B["shoulder_h"] + 0.16),
                0.2,
                0.32,
                fc="#f2e3cf",
                ec=colour,
                lw=0.8,
                zorder=9,
            )
        )
        return
    k = B["buttock_knee"]
    r(0, k, seat_z, seat_z + B["thigh_t"], C["thigh"])
    r(k - B["leg_d"], k, foot_z + 0.06, seat_z, C["thigh"])
    r(k - 0.15, k - 0.15 + B["foot_l"], foot_z, foot_z + 0.06, C["feet"])
    r(0, B["torso_d"], seat_z, seat_z + B["shoulder_h"], colour)
    ax.add_patch(
        Ellipse(
            (a0 + sgn * 0.13, seat_z + B["shoulder_h"] + (B["sit_h"] - B["shoulder_h"]) / 2),
            0.2,
            B["sit_h"] - B["shoulder_h"],
            fc="#f2e3cf",
            ec=colour,
            lw=0.8,
            zorder=9,
        )
    )


def standing(ax, a, z0, h, label, colour="#6f7f8f"):
    ax.add_patch(
        Rectangle((a - 0.13, z0), 0.26, h - 0.24, fc=colour, ec="none", alpha=0.8, zorder=8)
    )
    ax.add_patch(Ellipse((a, z0 + h - 0.12), 0.19, 0.24, fc="#e6edf2", ec=colour, lw=0.8, zorder=9))
    ax.text(
        a + 0.2, z0 + h - 0.62, label, fontsize=9, color=colour, ha="left", va="center", zorder=22
    )


def vdim(ax, x, z0, z1, text, tx, fs=9.3, ha="left", colour=INK):
    """Vertical dimension at x with its text set aside at tx (same height), so it never sits on a body."""
    ax.plot([x, x], [z0, z1], color=colour, lw=1.0, zorder=20)
    for z in (z0, z1):
        ax.plot([x - 0.04, x + 0.04], [z, z], color=colour, lw=1.0, zorder=20)
    zm = (z0 + z1) / 2
    if abs(tx - x) > 0.08:
        ax.plot([x, tx], [zm, zm], color=colour, lw=0.6, zorder=20)
    ax.text(
        tx,
        zm,
        text,
        fontsize=fs,
        color=colour,
        ha=ha,
        va="center",
        zorder=21,
        bbox=dict(fc="#fffdf8", ec="none", pad=1.0, alpha=0.92),
    )


def tier(ax, a0, a1, top, base=0.0, fc="#d8b98f"):
    ax.add_patch(
        Rectangle((min(a0, a1), top - 0.028), abs(a1 - a0), 0.028, fc=fc, ec=INK, lw=0.6, zorder=6)
    )
    ax.add_patch(
        Rectangle(
            (min(a0, a1), base), abs(a1 - a0), top - 0.028 - base, fc="#efe6d8", ec="none", zorder=3
        )
    )


def frame(ax, a0, a1, title):
    ax.set_facecolor(PAPER)
    ax.add_patch(Rectangle((a0, 0), a1 - a0, ML.H, fc=C["floor"], ec="none", zorder=1))
    ax.plot([a0, a1], [0, 0], color=INK, lw=2.2, zorder=10)
    ax.plot([a0, a1], [ML.H, ML.H], color=INK, lw=2.2, zorder=10)
    ax.plot([a0, a0], [0, ML.H], color=INK, lw=2.2, zorder=10)
    ax.plot([a1, a1], [0, ML.H], color=INK, lw=2.2, zorder=10)
    ax.text(a1 + 0.06, ML.H, f"天井 {ML.H:.1f}", fontsize=9.5, color=MUTE, va="center")
    ax.set_title(title, fontsize=13, color=INK, loc="left", pad=6)
    ax.set_aspect("equal")
    ax.axis("off")


def stove_side(ax, c):
    ap = D["guard_apothem"]
    r = ML.HEATER["r"]
    ax.add_patch(
        Rectangle(
            (c - r - 0.05, 0), 2 * r + 0.1, ML.HEATER["h"], fc=C["stove"], ec="none", zorder=5
        )
    )
    ax.add_patch(Ellipse((c, ML.HEATER["h"]), 2 * r, 0.26, fc=C["stove"], ec="none", zorder=5))
    for s in (-1, 1):
        ax.plot([c + s * ap, c + s * ap], [0, ML.HEATER["guard_h"]], color=INK, lw=2.4, zorder=6)
    ax.plot(
        [c - ap, c + ap], [ML.HEATER["guard_h"], ML.HEATER["guard_h"]], color=INK, lw=1.2, zorder=6
    )
    ax.plot(
        [c - ap, c + ap],
        [ML.HEATER["guard_h"] / 2, ML.HEATER["guard_h"] / 2],
        color=INK,
        lw=1.0,
        zorder=6,
    )


def section_we(ax):
    frame(
        ax,
        ML.XW,
        ML.XE,
        "断面A  西–東（ストーブ中心を通る。北を見る）：東西は座面＋足置き段＋中間段",
    )
    up, low, st = ML.TOP_UP, ML.TOP_LOW, ML.TOP_STEP
    for sg, wall, k in ((1, ML.XW, "w"), (-1, ML.XE, "e")):
        tier(ax, wall, D[f"{k}_upper_front"], up)
        tier(ax, D[f"{k}_upper_front"], D[f"{k}_foot_front"], low)
        tier(ax, D[f"{k}_foot_front"], D[f"{k}_step_front"], st, fc="#cfe4c2")
        body_side(ax, wall + sg * ML.BODY["back_gap"], sg, up, low)
    stove_side(ax, HX)
    B = ML.BODY
    xa = (D["w_upper_front"] + D["w_foot_front"]) / 2 + 0.06
    standing(ax, xa, low, B["stature"], f"足置き段に立つ\n（身長{B['stature']:.2f}）")
    standing(ax, (D["e_step_front"] + HX + D["guard_apothem"]) / 2, 0.0, B["stature"], "側通路")
    xs = D["w_step_front"] + 0.12
    vdim(ax, xs, 0, st, "0.225", xs + 0.2)
    vdim(ax, xs, st, low, "0.225", xs + 0.2)
    vdim(ax, xs, low, up, "座る 0.45", xs + 0.2)
    sz = low + B["stature"]
    vdim(
        ax,
        xa,
        sz,
        ML.H,
        f"立つと天井まで {ML.H - sz:.2f}（身長1.85で{ML.H - low - B['stature_tall']:.2f}）",
        xa + 0.3,
    )
    vdim(
        ax,
        D["e_upper_front"] + 0.08,
        up,
        ML.H,
        f"座面〜天井 {D['headroom_upper_seat']:.2f}",
        D["e_upper_front"] - 0.12,
        ha="right",
    )
    hz = up + B["sit_h"]
    vdim(
        ax,
        ML.XE - B["back_gap"] - 0.13,
        hz,
        ML.H,
        f"頭上 {D['head_clear_upper']:.2f}（座高0.98で{D['head_clear_upper_tall']:.2f}）",
        D["e_upper_front"] - 0.12,
        ha="right",
    )
    dim(
        ax,
        (HX + D["guard_apothem"], 0.60),
        (D["e_step_front"], 0.60),
        f"通路 {D['aisle_east']:.2f}",
        fs=9.5,
        side=0.12,
    )
    dim(
        ax,
        (HX + ML.HEATER["r"] + 0.05, 1.34),
        (D["e_foot_front"], 1.34),
        f"本体〜足置き段 {D['heater_shell_to_side_foot_bench']:.2f}",
        fs=9,
        side=0.12,
    )
    ax.set_xlim(ML.XW - 0.15, ML.XE + 0.75)
    ax.set_ylim(-0.15, ML.H + 0.12)


def section_sn(ax):
    frame(
        ax,
        ML.YS,
        ML.YN,
        "断面B  南–北（ストーブ中心を通る。西を見る）：北は座る2段、南は扉と演者の側",
    )
    up, low = ML.TOP_UP, ML.TOP_LOW
    tier(ax, ML.YN, D["n_upper_front"], up)
    tier(ax, D["n_upper_front"], D["n_lower_front"], low)
    ax.plot([D["n_foot_line"], D["n_foot_line"]], [low - 0.028, low], color=INK, lw=0.6, zorder=7)
    nu = next(s for s in S if s["id"] == "NU3")
    nl = next(s for s in S if s["id"] == "NL2")
    body_side(ax, nu["b"][1], -1, up, low)
    body_side(ax, nl["b"][1], -1, low, 0.0, colour="#8c6a50")
    stove_side(ax, HY)
    B = ML.BODY
    ys = (ML.YS + HY - D["guard_apothem"]) / 2
    standing(ax, ys, 0.0, B["stature"], "演者", colour=C["free"])
    arm_z = 1.42
    ax.add_patch(
        FancyArrowPatch(
            (ys + 0.12, arm_z),
            (ys + 0.12 + ML.TOWEL["arm"] + ML.TOWEL["towel"], arm_z + 0.25),
            arrowstyle="-",
            color=C["towel"],
            lw=2.2,
            zorder=9,
        )
    )
    ax.text(
        ys + 1.0,
        arm_z + 0.52,
        f"腕0.65＋タオル0.65 = {ML.TOWEL['arm'] + ML.TOWEL['towel']:.2f}\n（前へ振り出すとストーブの上に届く）",
        fontsize=9,
        color=C["towel"],
        ha="center",
        va="bottom",
    )
    dim(
        ax,
        (ML.YS, -0.1),
        (HY - D["guard_apothem"], -0.1),
        f"南の床 {D['floor_south']:.2f}",
        fs=9.5,
        side=-0.14,
    )
    dim(
        ax,
        (HY + D["guard_apothem"], -0.1),
        (D["n_lower_front"], -0.1),
        f"北通路 {D['aisle_north']:.2f}",
        fs=9.5,
        side=-0.14,
    )
    dim(
        ax,
        (HY + ML.HEATER["r"] + 0.05, 1.5),
        (D["n_lower_front"], 1.5),
        f"本体〜前列の座面先端 {D['heater_shell_to_n_lower_nose']:.2f}",
        fs=9,
        side=0.13,
    )
    vdim(
        ax,
        D["n_upper_front"] + 0.06,
        up,
        ML.H,
        f"座面〜天井 {D['headroom_upper_seat']:.2f}",
        D["n_upper_front"] - 0.1,
        ha="right",
    )
    dim(ax, (D["n_upper_front"], -0.1), (D["n_foot_line"], -0.1), "足0.30", fs=8.8, side=-0.14)
    dim(ax, (D["n_foot_line"], -0.1), (D["n_lower_front"], -0.1), "座0.50", fs=8.8, side=0.14)
    ax.text(HY, ML.HEATER["h"] + 0.24, "石の上面 約1.2", fontsize=9, color=MUTE, ha="center")
    ax.set_xlim(ML.YS - 0.15, ML.YN + 0.75)
    ax.set_ylim(-0.42, ML.H + 0.12)


def wrap(text, limit):
    """Wrap Japanese text by display width (ASCII counts 0.55); never breaks inside a number or before punctuation."""
    out, cur, w = [], "", 0.0
    for ch in text:
        cw = 0.55 if ord(ch) < 128 else 1.0
        if (
            w + cw > limit
            and not (ch.isascii() and cur[-1:].isascii() and ch != " ")
            and ch not in "、。）」・"
        ):
            out.append(cur.rstrip())
            cur, w = "", 0.0
            if ch == " ":
                continue
        cur += ch
        w += cw
    if cur:
        out.append(cur)
    return out


def main():
    chk, discs, discs0 = (
        ML.checks(),
        ML.floor_discs(),
        ML.floor_discs(*ML.floor_obstacles(people=False)),
    )
    sw, so, v5, opts, acc = (
        ML.swing_radius(False),
        ML.swing_radius(True),
        ML.v5_reference(),
        ML.options(),
        ML.access(),
    )
    fig = plt.figure(figsize=(24, 16.6), dpi=100, facecolor=PAPER)
    fig.text(
        0.014,
        0.972,
        "メインサウナ：20人の位置・足元・上り口・実演の床（v6 検討図）",
        fontsize=25,
        color=INK,
        weight="bold",
        va="center",
    )
    fig.text(
        0.014,
        0.945,
        "模型と同じ寸法ソース（blender/sauna/main_layout.py）から作図。成人の仮寸法（肩幅0.50・座高0.92・尻〜膝0.60・足長0.27 m）による概念検討で、"
        "法適合・ストーブ機種と離隔・構造・換気熱負荷・演者の確認は別途。",
        fontsize=12.5,
        color=MUTE,
        va="center",
    )
    plan(fig.add_axes([0.005, 0.03, 0.555, 0.895]))
    section_we(fig.add_axes([0.565, 0.655, 0.43, 0.265]))
    section_sn(fig.add_axes([0.565, 0.365, 0.43, 0.265]))
    ax = fig.add_axes([0.565, 0.02, 0.43, 0.325])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    by = chk["by_row"]
    big = max(d["diameter"] for d in discs)
    a, b = opts
    lines = [
        (
            "席",
            f"脚を下ろして座る{chk['legs_down']}（北上段{by['north_upper']}・幅{ML.PITCH['n_upper']:.2f}、北下段{by['north_lower']}・{ML.PITCH['n_lower']:.2f}、西{by['west_upper']}・東{by['east_upper']}・{ML.PITCH['side']:.2f}）"
            f"＋角で足を上げて座る{chk['feet_up_corner']}＝{chk['seats']}位置。角は姿勢が限られるので、{chk['legs_down']}人を通常、角2人を任意と見るのが正直。"
            f"足置きは席に数えていない。人体の重なり{len(chk['body_clashes'])}、他席の座面に乗る足{len(chk['feet_on_another_seat'])}、段・踊り場に掛かる足{len(chk['feet_on_step_or_landing'])}。",
        ),
        (
            "上り口",
            f"東西8席は目の前の中間段から2回×0.225 mで足置き段へ。角2席とNU1・NU6は北の踊り場（{chk['north_landing_size'][0]:.2f}×{chk['north_landing_size'][1]:.2f} m）から。"
            f"ここまでの{chk['seats_reached_without_passing_anyone']}位置は誰の前も通らない。残る{len(chk['seats_needing_cooperation'])}席（赤点線）は協力が要る："
            f"NU2〜NU5は足置き帯0.30 m（足が0.27 mを占める）を1〜2人の足の前で横へ進み、NL2・NL3は北通路で隣の膝の前を通る。座ったまま自由に通れる通路ではない。",
        ),
        (
            "頭上",
            f"座面〜天井{D['headroom_upper_seat']:.2f} m（メーカー目安1.1〜1.3 mより低い位置に座る）。足置き段に立つと天井まで{D['headroom_standing_foot_level']:.2f} m。"
            "上段の座面（0.90）には立てない高さなので、移動はすべて0.45の面で行う。",
        ),
        (
            "実演の床",
            f"中央のストーブで床は南・東西の側通路・北に分かれる。空きの最大円 φ{big:.2f}（南東＝扉前／南西）、ストーブ正面 φ{discs[0]['diameter']:.2f}、"
            f"側通路 φ{discs[3]['diameter']:.2f}、北 φ{discs[-1]['diameter']:.2f}。v5（南壁ストーブ・L字）は φ{v5['largest_floor_circle']:.2f}。"
            f"北通路は前列のつま先まで{chk['north_aisle_clear_of_front_row_toes']:.2f} mで、1人ずつ・横向きに通る幅（T3）。",
        ),
        (
            "タオル",
            f"水平に一周（半径{sw['needed_for_full_turn']:.2f} mの仮定）は、柵の上を通さない限り不可（最大{sw['radius']:.2f} m）。"
            f"柵と石の上を通せば{so['radius']:.2f} mまで取れるが、熱い石の上を通す操作になる。体の前であおぐ・短く振る動きと、南→側通路の移動が前提。北側の4人の前では振れない。",
        ),
        (
            "3段の検討",
            f"北奥だけ3段にすると奥行{b['north_depth']:.2f} m（2段は{a['north_depth']:.2f}）。ストーブが南へ{b['stove_off_room_centre'] - a['stove_off_room_centre']:.2f} m寄り、"
            f"南の床が{b['floor_south']:.2f} m（2段は{a['floor_south']:.2f}）、柵の南面が扉の幅の中（y={b['guard_south_face_y']:.2f}）に入る。"
            f"最上段は頭上{b['head_to_ceiling']:.2f} m、移動する中段に立つと{b['standing_headroom_on_access_level']:.2f} m。→ 2段を採用。",
        ),
        (
            "未確認",
            "ストーブの機種・出力・離隔、柵と席の熱さ、給排気、床排水、手すり（未設置）、避難、構造、費用。席数は仮寸法での配置で、定員の保証ではない。",
        ),
    ]
    y = 0.99
    for head, text in lines:
        ax.text(0.0, y, head, fontsize=11.5, color=INK, weight="bold", va="top")
        wrapped = wrap(text, 57)
        ax.text(0.105, y, "\n".join(wrapped), fontsize=10.6, color=INK, va="top", linespacing=1.42)
        y -= 0.0385 * len(wrapped) + 0.02
    out = DATA / "diagrams"
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / f"main_seats_{V}.png", dpi=100, facecolor=PAPER)
    ver = DATA / "verification"
    ver.mkdir(parents=True, exist_ok=True)
    rec = {
        "source": "blender/sauna/main_layout.py (same data as the model)",
        "limits": "成人の仮寸法による概念検討。法適合・ストーブ機種と離隔・構造・換気熱負荷・演者の確認は別途。席数は定員の保証ではない。",
        "body_assumption_m": ML.BODY,
        "checks": chk,
        "seats": [{**s, "access": acc[s["id"]]} for s in S],
        "zones": [
            {"kind": z[0], "label": z[1], "rect": [round(v, 3) for v in z[2:6]], "level": z[6]}
            for z in ML.zones()
        ],
        "standing_check_bodies": [
            {**t, "boxes": [[b[0]] + [round(v, 3) for v in b[1:]] for b in ML.standing_boxes(t)]}
            for t in ML.standing()
        ],
        "floor_circles_with_front_row_legs": discs,
        "floor_circles_benches_only": discs0,
        "towel": {"assumption": ML.TOWEL, "not_over_stove": sw, "over_stove": so},
        "v5_reference": v5,
        "options_compared": opts,
        "heater": ML.HEATER,
    }
    (ver / "main_seat_study.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(out / f"main_seats_{V}.png")


if __name__ == "__main__":
    main()
