"""Bath-side rest area v4: main zone (0,3.6 6x5.4 m) and extension (6,3.6 4.5x2.9 m), ceiling 2.7 m provisional.

Seats face a wall or the back of the next shelter, never another seat or the aisle; coordinates come from rest_layout.py.
Partition heights, eye heights and clearances are study values — privacy, egress and construction are not verified.
"""

from . import furniture, geo, shell
from . import rest_layout as RL
from .geo import MB
from .shell import SLOT_H, SLOT_W, T_BACK, T_SLAT


def build(plan, P, LM, coll):
    H = 2.7
    f = T_BACK + T_SLAT
    ts = 0.014
    dh = plan["doorHeight"]
    lights = geo.collection("Rest_lights", coll)
    ceil = geo.collection("Ceilings", coll)
    X0, X1, XE, Y0, Y1, YE = 0.08, 5.92, 10.42, 3.68, 8.92, 6.42

    slat = MB("Rest_wall_slats", P["wood"], coll, bevel=0.002)
    back = MB("Rest_backing", P["wood_back"], coll, bevel=0)
    stone = MB("Rest_wall_stone", P["wall_stone"], coll, bevel=0.0008, segments=1)
    black = MB("Rest_cove_black", P["black"], ceil, bevel=0)

    shell.slat_wall(
        slat, back, "x", Y1, -1, X0, X1, 0, H + SLOT_H
    )  # north: behind the lying platforms
    shell.slat_wall(
        slat, back, "y", X1, -1, YE, Y1 - f, 0, H + 0.03, openings=[(7.0, 8.1, 0, dh)]
    )  # east wall with the bath door
    shell.slat_wall(slat, back, "x", YE, -1, X1, XE, 0, H + 0.03)  # extension north wall
    shell.panel_wall(stone, "y", X0, 1, Y0, Y1 - f, 0, H + 0.03, t=ts)  # west
    shell.panel_wall(
        stone, "x", Y0, 1, X0 + ts, XE, 0, H + SLOT_H, t=ts
    )  # south (in front of the loungers)
    shell.panel_wall(
        stone, "y", XE, -1, Y0 + ts, YE - f, 0, H + SLOT_H, t=ts
    )  # far east wall of the extension

    cs = MB("Rest_ceiling_slats", P["wood_dark"], ceil, bevel=0.002)
    shell.slat_ceiling(cs, black, X0 + ts, Y0 + ts + SLOT_W, X1, Y1 - f - SLOT_W, H, along="y")
    shell.slat_ceiling(cs, black, X1, Y0 + ts + SLOT_W, XE - ts - SLOT_W, YE - f, H, along="y")
    cs.finish()
    # ceiling reveals kept as faint wall washes only (v3 used them as the main light)
    shell.cove(
        lights, black, LM["rest_cove_n"], "x", Y1 - f, -1, X0 + ts, X1 - f, H, "LED_rest_cove_north"
    )
    shell.cove(
        lights,
        black,
        LM["rest_cove_s"],
        "x",
        Y0 + ts,
        1,
        X0 + ts,
        XE - ts,
        H,
        "LED_rest_cove_south",
    )
    shell.cove(
        lights,
        black,
        LM["rest_cove_far"],
        "y",
        XE - ts,
        -1,
        Y0 + ts + SLOT_W,
        YE - f,
        H,
        "LED_rest_cove_far",
    )

    # low skirting reveals: a stone nosing hides a down-facing strip, so the floor at the seats reads without a visible source
    nosing = MB("Rest_skirting_nosing", P["wall_stone"], coll, bevel=0.002, segments=1)
    ys, yn = Y0 + ts, YE - f
    nosing.box(X0 + ts, ys, 0.10, XE - ts, ys + 0.036, 0.135)
    nosing.box(X1 + 0.10, yn - 0.036, 0.10, XE - ts, yn, 0.135)
    nosing.finish()
    shell.strip_down(
        lights,
        LM["rest_skirt"],
        "LED_rest_skirt_south",
        X0 + ts + 0.05,
        ys + 0.007,
        XE - ts - 0.05,
        ys + 0.027,
        0.098,
    )
    shell.strip_down(
        lights,
        LM["rest_skirt"],
        "LED_rest_skirt_ext_north",
        X1 + 0.15,
        yn - 0.027,
        XE - ts - 0.05,
        yn - 0.007,
        0.098,
    )

    lay = RL.layout_v5()
    pl = RL.PLATFORM
    furniture.lying_platform(
        P,
        coll,
        lights,
        LM["rest_plinth"],
        "Rest_platform",
        pl["x0"],
        pl["x1"],
        pl["y_front"],
        pl["y_wall"],
        n=pl["n"],
        top=pl["top"],
        margin=0.017,
    )

    panels = MB("Rest_partition_panels", P["wood_mid"], coll, bevel=0.004, segments=2)
    fins = MB("Rest_partition_fins", P["wood_mid"], coll, bevel=0.002)
    plinth = MB("Rest_partition_plinths", P["black"], coll, bevel=0)
    n_head = 0
    for p in lay["partitions"]:
        x0, y0, x1, y1 = p["rect"]
        z0, z1 = p["z"]
        if p["kind"] == "fins":
            furniture.fin_row(fins, p["rect"], z0, z1)
            continue
        if "outline" in p:  # v5: eased top edge (wings, bay walls, lying dividers)
            furniture.profile_panel(panels, p["rect"], z0, p["outline"], p["root"])
            continue
        furniture.board_panel(panels, p["rect"], z0, z1)
        if (
            0.02 < z0 < 0.09
        ):  # floating headboard: recessed plinth on the seat side, toe light on the aisle side
            # seat side also gets a small ledge under the cap hiding a down-facing strip: it washes the board behind the
            # head (out of the occupant's view, below a walker's eye) so the seat reads without any ceiling light
            n_head += 1
            if (x1 - x0) >= (y1 - y0):
                plinth.box(x0 + 0.01, y0 + 0.006, 0.0, x1 - 0.01, y0 + 0.030, z0)
                panels.box(x0 + 0.06, y0 - 0.034, z1 - 0.032, x1 - 0.06, y0, z1 - 0.006, "x")
                shell.strip_down(
                    lights,
                    LM["rest_head"],
                    f"LED_rest_head_{n_head}",
                    x0 + 0.08,
                    y0 - 0.026,
                    x1 - 0.08,
                    y0 - 0.008,
                    z1 - 0.034,
                )
            else:
                plinth.box(x1 - 0.030, y0 + 0.01, 0.0, x1 - 0.006, y1 - 0.01, z0)
                panels.box(x1, y0 + 0.06, z1 - 0.032, x1 + 0.034, y1 - 0.06, z1 - 0.006, "y")
                shell.strip_down(
                    lights,
                    LM["rest_head"],
                    f"LED_rest_head_{n_head}",
                    x1 + 0.008,
                    y0 + 0.08,
                    x1 + 0.026,
                    y1 - 0.08,
                    z1 - 0.034,
                )
    panels.finish()
    fins.finish()
    plinth.finish(weighted=False)
    for i, (x0, y0, x1, y1, z) in enumerate(lay["toe_lights"]):
        shell.strip_down(lights, LM["rest_toe"], f"LED_rest_toe_{i}", x0, y0, x1, y1, z)

    # v6: one towel peg per seat on the aisle face of its headboard / wing, 1.12 m high. A towel on the peg tells from the
    # junction inside the door that the seat is taken, without walking down either dead-end aisle (a usage convention,
    # not a guarantee). Does not change any partition or sight line.
    peg = MB("Rest_seat_pegs", P["wood_chair"], coll, bevel=0)
    for px, py, (dx, dy) in lay["pegs"]:
        peg.tube([(px, py, 1.12), (px + dx * 0.050, py + dy * 0.050, 1.125)], 0.011, seg=14)
        peg.tube(
            [(px + dx * 0.050, py + dy * 0.050, 1.125), (px + dx * 0.058, py + dy * 0.058, 1.126)],
            0.016,
            seg=14,
        )
    peg.finish(weighted=False)

    mbs = {
        "frame": MB("Rest_chair_frames", P["wood_chair"], coll, bevel=0.004, segments=2),
        "slats": MB("Rest_chair_slats", P["wood_chair"], coll, bevel=0.004, segments=2),
    }
    for s in lay["seats"]:
        if s["kind"] == "recline":
            furniture.slat_seat(mbs, s["foot"][0], s["foot"][1], s["heading"])
        elif s["kind"] == "upright":
            furniture.slat_seat(
                mbs,
                s["foot"][0],
                s["foot"][1],
                s["heading"],
                profile=furniture.CHAIR_PROFILE,
                width=RL.CHAIR_W,
                legs=((0.07, 0.0), (0.52, 0.04)),
            )
    for mb in mbs.values():
        mb.finish()

    furniture.floor_drain(P, coll, "Rest_floor_drain", 5.1, 6.4)
    slat.finish()
    back.finish(weighted=False)
    stone.finish()
    black.finish(weighted=False)
