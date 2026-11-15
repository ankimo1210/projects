"""Bath-side rest area: main zone (0,3.6 6x5.4 m) and extension (6,3.6 4.5x2.9 m), ceiling 2.7 m provisional."""

from . import furniture, geo, shell
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
    shell.panel_wall(stone, "x", Y0, 1, X0 + ts, XE, 0, H + SLOT_H, t=ts)  # south (behind chairs)
    shell.panel_wall(
        stone, "y", XE, -1, Y0 + ts, YE - f, 0, H + SLOT_H, t=ts
    )  # far east wall of the extension

    cs = MB("Rest_ceiling_slats", P["wood_dark"], ceil, bevel=0.002)
    shell.slat_ceiling(cs, black, X0 + ts, Y0 + ts + SLOT_W, X1, Y1 - f - SLOT_W, H, along="y")
    shell.slat_ceiling(cs, black, X1, Y0 + ts + SLOT_W, XE - ts - SLOT_W, YE - f, H, along="y")
    cs.finish()
    shell.cove(
        lights, black, LM["cove"], "x", Y1 - f, -1, X0 + ts, X1 - f, H, "LED_rest_cove_north"
    )
    shell.cove(
        lights, black, LM["cove_mid"], "x", Y0 + ts, 1, X0 + ts, XE - ts, H, "LED_rest_cove_south"
    )
    shell.cove(
        lights,
        black,
        LM["cove"],
        "y",
        XE - ts,
        -1,
        Y0 + ts + SLOT_W,
        YE - f,
        H,
        "LED_rest_cove_far",
    )

    # lying platforms along the north wall (heads at the wall)
    furniture.lying_platform(
        P, coll, lights, LM["plinth"], "Rest_platform", 0.25, 4.81, Y1 - f - 2.03, Y1 - f, n=6
    )

    # loungers along the south wall in pairs separated by fin screens (heads toward the wall)
    mbs = {
        "frame": MB("Rest_chair_frames", P["wood_chair"], coll, bevel=0.004, segments=2),
        "slats": MB("Rest_chair_slats", P["wood_chair"], coll, bevel=0.004, segments=2),
    }
    fins = MB("Rest_fin_screens", P["wood"], coll, bevel=0.003)
    foot_y = 5.74
    for cx in (0.90, 1.70, 2.75, 3.55, 4.60, 5.40):
        furniture.slat_seat(mbs, cx, foot_y, (0.0, -1.0))
    for sx in (2.225, 4.075, 5.93):
        furniture.fin_screen(fins, "y", sx, Y0 + ts + 0.06, Y0 + ts + 1.06, H + 0.02)
    # extension: upright slatted chairs on both walls
    for cx in (6.55, 7.35, 8.15, 8.95, 9.75):
        furniture.slat_seat(
            mbs,
            cx,
            4.50,
            (0.0, -1.0),
            profile=furniture.CHAIR_PROFILE,
            width=0.58,
            legs=((0.07, 0.0), (0.52, 0.04)),
        )
        furniture.slat_seat(
            mbs,
            cx,
            5.60,
            (0.0, 1.0),
            profile=furniture.CHAIR_PROFILE,
            width=0.58,
            legs=((0.07, 0.0), (0.52, 0.04)),
        )
    for mb in mbs.values():
        mb.finish()
    fins.finish()

    trim = MB("Rest_downlight_trims", P["steel"], ceil, bevel=0)
    for i, (dx, dy) in enumerate(((1.6, 6.3), (4.2, 6.3), (6.8, 5.05), (9.0, 5.05), (5.3, 7.55))):
        shell.downlight(trim, lights, LM["down_dim"], f"LED_rest_down_{i}", dx, dy, H)
    trim.finish()
    furniture.floor_drain(P, coll, "Rest_floor_drain", 5.1, 6.3)
    slat.finish()
    back.finish(weighted=False)
    stone.finish()
    black.finish(weighted=False)
