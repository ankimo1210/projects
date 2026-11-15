"""Vector plan views using the same layout coordinates as V8, and simple millimetre DXF export."""

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import font_manager as fm
from matplotlib import pyplot as plt
from matplotlib.patches import Arc, Circle, Polygon, Rectangle

from .audit import BL, ML, RL, SL, WL

FONT = next(
    Path(p)
    for p in [
        "/mnt/c/Windows/Fonts/YuGothM.ttc",
        "/mnt/c/Windows/Fonts/meiryo.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    if Path(p).exists()
)
fm.fontManager.addfont(str(FONT))
plt.rcParams.update(
    {
        "font.family": fm.FontProperties(fname=str(FONT)).get_name(),
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
        "axes.unicode_minus": False,
    }
)
INK = "#322e28"
MUTED = "#736e65"
PAPER = "#f8f5ee"
BLUE = "#467e92"
RED = "#b44c40"
GREEN = "#617c6c"
WOOD = "#c8a27e"
LINE = "#aca79d"
NAMES = {
    "entry": "受付・下足",
    "change": "更衣48区画",
    "wc": "洗面・WC",
    "staff": "スタッフ",
    "plant": "機械室21㎡",
    "linen": "リネン",
    "service": "保守・搬入",
    "main": "主室 約20位置",
    "self": "セルフ6位置",
    "dry": "ドライ4位置・TV",
    "carbon": "炭酸泉",
    "rest": "休憩",
    "restExt": "休憩の延長",
    "wash": "洗い場6組",
}


def rect(ax, x, y, w, h, face="none", edge=INK, lw=0.7, **kw):
    q = Rectangle((x, y), w, h, facecolor=face, edgecolor=edge, linewidth=lw, **kw)
    ax.add_patch(q)
    return q


def label(ax, x, y, text, size=7, color=INK, **kw):
    return ax.text(
        x, y, text, fontsize=size, color=color, ha="center", va="center", clip_on=True, **kw
    )


def dim(ax, a, b, offset, text, vertical=False):
    if vertical:
        x = a[0] + offset
        y0 = a[1]
        y1 = b[1]
        ax.plot([a[0], x], [y0, y0], color=LINE, lw=0.45)
        ax.plot([b[0], x], [y1, y1], color=LINE, lw=0.45)
        ax.plot([x, x], [y0, y1], color=INK, lw=0.5)
        for y in [y0, y1]:
            ax.plot([x - 0.045, x + 0.045], [y - 0.045, y + 0.045], color=INK, lw=0.5)
        label(
            ax,
            x - 0.08,
            (y0 + y1) / 2,
            text,
            6.4,
            rotation=90,
            bbox={"facecolor": PAPER, "edgecolor": "none", "pad": 1},
        )
    else:
        y = a[1] + offset
        x0 = a[0]
        x1 = b[0]
        ax.plot([x0, x0], [a[1], y], color=LINE, lw=0.45)
        ax.plot([x1, x1], [b[1], y], color=LINE, lw=0.45)
        ax.plot([x0, x1], [y, y], color=INK, lw=0.5)
        for x in [x0, x1]:
            ax.plot([x - 0.045, x + 0.045], [y - 0.045, y + 0.045], color=INK, lw=0.5)
        label(
            ax,
            (x0 + x1) / 2,
            y + 0.06,
            text,
            6.4,
            bbox={"facecolor": PAPER, "edgecolor": "none", "pad": 1},
        )


def seat_poly(s, length=None, width=None):
    fx, fy = s["foot"]
    hx, hy = s["heading"]
    l = length or s["length"]
    w = width or s["width"]
    nx, ny = -hy, hx
    return [
        (fx + nx * w / 2, fy + ny * w / 2),
        (fx - nx * w / 2, fy - ny * w / 2),
        (fx + hx * l - nx * w / 2, fy + hy * l - ny * w / 2),
        (fx + hx * l + nx * w / 2, fy + hy * l + ny * w / 2),
    ]


def draw_plan(ax, plan, names=True, front_proposal=False, people=False, step_level_labels=True):
    for r in plan["rooms"]:
        face = (
            "#e8ddd0"
            if r["id"] in ("main", "self", "dry")
            else "#e1e9e5"
            if r["id"] in ("rest", "restExt")
            else "#e9eeef"
            if r["floor"] == "wet"
            else "#edeae3"
        )
        rect(ax, *r["rect"], face, edge="none")
    for x0, y0, x1, y1 in plan["walls"] + [w["seg"] for w in plan.get("addedWalls", [])]:
        if abs(y1 - y0) < 1e-8:
            rect(ax, min(x0, x1), y0 - 0.08, abs(x1 - x0), 0.16, INK, INK, 0)
        else:
            rect(ax, x0 - 0.08, min(y0, y1), 0.16, abs(y1 - y0), INK, INK, 0)
    for d in plan["doors"]:
        x0, y0, x1, y1 = d["seg"]
        w = math.hypot(x1 - x0, y1 - y0)
        if abs(y1 - y0) < 1e-8:
            rect(ax, min(x0, x1), y0 - 0.09, w, 0.18, PAPER, "none", 0)
            ax.plot([x0 + 0.05, x1 - 0.05], [y0, y0], color=BLUE, lw=0.9)
        else:
            rect(ax, x0 - 0.09, min(y0, y1), 0.18, w, PAPER, "none", 0)
            ax.plot([x0, x0], [y0 + 0.05, y1 - 0.05], color=BLUE, lw=0.9)
    for q in ML.bench_rects():
        rect(ax, q[0], q[1], q[2] - q[0], q[3] - q[1], WOOD)
    for kind, _, x0, y0, x1, y1, z in SL.self_levels() + SL.dry_levels():
        rect(
            ax,
            x0,
            y0,
            x1 - x0,
            y1 - y0,
            WOOD if kind in ("seat", "deck", "corner") else "#e3cbb3",
            lw=0.4,
        )
    for s in RL.layout_v5()["seats"]:
        ax.add_patch(Polygon(seat_poly(s), facecolor=WOOD, edgecolor=INK, lw=0.4))
    for s in WL.loungers():
        ax.add_patch(Polygon(seat_poly(s, 1.8, 0.62), facecolor=WOOD, edgecolor=INK, lw=0.4))
    for _, x0, y0, x1, y1, _, _ in WL.partitions():
        rect(ax, x0, y0, x1 - x0, y1 - y0, GREEN, lw=0.3)
    rect(ax, 10.71, 6.50, 0.13, 2.50, GREEN)
    for r in plan["pools"]:
        x, y, w, h = r["rect"]
        rect(ax, x, y, w, h, "#b9d7e2", BLUE, 0.9)
        if r["id"] in ("deep", "seated"):
            q = WL.pool(r["id"])
            for x0, y0, x1, y1, z in q["treads"]:
                rect(ax, x0, y0, x1 - x0, y1 - y0, "#e2e9e6", BLUE, 0.5)
                if not names and step_level_labels:
                    label(ax, (x0 + x1) / 2, (y0 + y1) / 2, f"{z:.3f}", 4.3)
        if names:
            title = {
                "deep": "深1.20m\n10℃（仮）",
                "seated": "座0.60m\n16℃（仮）",
                "carbonPool": "炭酸泉37℃（仮）",
            }[r["id"]]
            label(ax, x + w / 2, y + h * 0.40, title, 6.5)
    rect(ax, 2.56, 10.695, 0.88, 0.51, "#9d9991", INK)
    for c, r in [(SL.SELF["heater"]["c"], 0.57), (SL.DRY["heater"]["c"], 0.50)]:
        ax.add_patch(Circle(c, r, facecolor="#a6a199", edgecolor=INK, lw=0.6))
    for s in BL.perch_seats() + BL.built_in_seats():
        x, y = s["b"]
        rect(ax, x - 0.26, y - 0.20, 0.52, 0.32, WOOD, lw=0.4)
    # Exact source module counts, with only symbolic front-of-house fixture geometry.
    for k in range(20):
        rect(ax, 4.2 + k * 0.3, 3.07, 0.30, 0.45, "#d2b896", lw=0.35)
    for k in range(4):
        rect(ax, 5.2 + k * 0.3, 0.08, 0.30, 0.45, "#d2b896", lw=0.35)
    rect(ax, 6.2, 1.55, 3, 0.4, WOOD)
    rect(ax, 0.45, 2.15, 1.70 if front_proposal else 2.20, 0.65, WOOD)
    for k in range(5):
        rect(ax, 0.08, 0.30 + k * 0.33, 0.36, 0.33, WOOD, lw=0.35)
    if front_proposal:
        for k in range(5):
            rect(ax, 2.30 + k * 0.30, 3.12, 0.30, 0.40, WOOD, lw=0.35)
    rect(ax, 11.75, 0.10, 1.85, 0.50, "#c9c8c1")
    for x in [12.2, 13.1]:
        ax.add_patch(Circle((x, 0.36), 0.16, facecolor=PAPER, edgecolor=INK, lw=0.5))
    for x in [12.55, 13.45]:
        ax.plot([x, x], [2, 3.52], color=INK, lw=0.8)
        ax.add_patch(Circle((x + 0.42, 3.1), 0.18, facecolor=PAPER, edgecolor=INK, lw=0.5))
    if front_proposal:
        for x0, x1 in [(12.55, 13.45), (13.45, 14.22)]:
            end = min(x1 - 0.07, x0 + 0.72)
            ax.plot([x0, end], [2, 2], color=GREEN, lw=0.9, ls="--")
            ax.add_patch(
                Arc(
                    (x0 + 0.04, 2),
                    2 * (end - x0 - 0.04),
                    2 * (end - x0 - 0.04),
                    theta1=0,
                    theta2=90,
                    edgecolor=GREEN,
                    lw=0.5,
                )
            )
    else:
        ax.plot([12.55, 14.22], [2, 2], color=RED, lw=0.9)
    for x in [11.30, 12.30, 13.30, 14.30, 15.30, 16.30]:
        rect(ax, x - 0.23, 3.70, 0.46, 0.32, "#c9c8c1", lw=0.3)
    if names:
        for r in plan["rooms"]:
            x, y, w, h = r["rect"]
            pos = {
                "main": (3, 10),
                "self": (7.5, 11.1),
                "dry": (10.8, 10.9),
                "water": (10.8, 9.75),
                "rest": (3, 6.05),
                "restExt": (8.2, 4.65),
                "carbon": (14.7, 13.65),
            }.get(r["id"], (x + w / 2, y + h / 2))
            if r["id"] == "water":
                txt = "浴室内通路"
            else:
                txt = NAMES.get(r["id"], r["name"])
            label(
                ax,
                *pos,
                txt,
                6.7,
                bbox={"facecolor": PAPER, "edgecolor": "none", "alpha": 0.86, "pad": 1.5},
            )
        label(ax, 8.8, 7.76, "離れ4", 6.5)
        label(ax, 1.7, -0.28, "入口", 7)
    if people:
        for s in ML.seats() + SL.self_seats() + SL.dry_seats():
            for part, x0, y0, x1, y1, z0, z1 in (
                ML.body_boxes(s) if s["tier"] not in ("dry_deck",) else []
            ):
                if part == "head":
                    ax.add_patch(
                        Circle(
                            ((x0 + x1) / 2, (y0 + y1) / 2),
                            0.10,
                            facecolor="#c16d51",
                            edgecolor="none",
                        )
                    )
    ax.set_aspect("equal")
    ax.axis("off")


def plan_axes(fig, x_mm, y_mm, bounds, scale):
    pw, ph = fig._paper_mm
    x0, y0, x1, y1 = bounds
    width = (x1 - x0) * 1000 / scale
    height = (y1 - y0) * 1000 / scale
    ax = fig.add_axes([x_mm / pw, y_mm / ph, width / pw, height / ph])
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.axis("off")
    return ax


def alarm_points(plan):
    rooms = {r["id"]: r for r in plan["rooms"]}
    out = {}
    for rid, dx, dy in [("main", 5.75, 0.80), ("self", 1.40, 0.20), ("dry", 1.00, 0.20)]:
        x, y, _, _ = rooms[rid]["rect"]
        out[rid] = (x + dx, y + dy)
    out["receiver"] = (1.10, 2.50)
    return out


def export_dxf(path, plan):
    """AC1015, INSUNITS=4 millimetres; centre lines/openings and key furniture envelopes only."""
    lines = [
        "0",
        "SECTION",
        "2",
        "HEADER",
        "9",
        "$ACADVER",
        "1",
        "AC1015",
        "9",
        "$INSUNITS",
        "70",
        "4",
        "0",
        "ENDSEC",
        "0",
        "SECTION",
        "2",
        "ENTITIES",
    ]

    def line(x0, y0, x1, y1, layer):
        lines.extend(
            [
                "0",
                "LINE",
                "8",
                layer,
                "10",
                str(x0 * 1000),
                "20",
                str(y0 * 1000),
                "30",
                "0",
                "11",
                str(x1 * 1000),
                "21",
                str(y1 * 1000),
                "31",
                "0",
            ]
        )

    for s in plan["walls"] + [q["seg"] for q in plan.get("addedWalls", [])]:
        line(*s, "WALL_CENTRE")
    for d in plan["doors"]:
        line(*d["seg"], "OPENING_NOT_DOOR_SWING")
    for p in plan["pools"]:
        x, y, w, h = p["rect"]
        for s in [
            (x, y, x + w, y),
            (x + w, y, x + w, y + h),
            (x + w, y + h, x, y + h),
            (x, y + h, x, y),
        ]:
            line(*s, "POOL_INNER")
    for q in ML.bench_rects():
        x, y, a, b = q
        for s in [(x, y, a, y), (a, y, a, b), (a, b, x, b), (x, b, x, y)]:
            line(*s, "BENCH_ENVELOPE")
    lines.extend(["0", "ENDSEC", "0", "EOF"])
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
