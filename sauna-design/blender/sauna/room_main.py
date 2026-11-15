"""Main aufguss sauna (plan rect 0,9 6x5 m, ceiling 2.4 m provisional)."""

from . import furniture, geo, shell
from .furniture import Frame
from .geo import MB
from .shell import SLOT_H, SLOT_W, T_BACK, T_SLAT


def build(plan, P, LM, coll):
    X0, X1, Y0, Y1, H = 0.08, 5.92, 9.08, 13.92, 2.4
    f = T_BACK + T_SLAT
    xw, xe, ys, yn = X0 + f, X1 - f, Y0 + f, Y1 - f
    lights = geo.collection("Main_lights", coll)
    ceil = geo.collection("Ceilings", coll)

    slat = MB("Main_wall_slats", P["wood"], coll, bevel=0.002)
    back = MB("Main_backing", P["wood_back"], coll, bevel=0)
    stone = MB("Main_heat_shield", P["wall_stone"], coll, bevel=0.001, segments=1)
    black = MB("Main_cove_black", P["black"], ceil, bevel=0)
    hx, hy = 2.90, 9.95  # heater centre
    sx0, sx1 = 1.90, 3.90  # stone heat shield on the south wall
    shell.slat_wall(slat, back, "x", Y1, -1, X0, X1, 0, H + SLOT_H)
    shell.slat_wall(slat, back, "y", X0, 1, ys, yn, 0, H + 0.03)
    shell.slat_wall(
        slat,
        back,
        "y",
        X1,
        -1,
        ys,
        yn,
        0,
        H + 0.03,
        openings=[(9.25, 10.25, 0, plan["doorHeight"])],
    )
    shell.slat_wall(slat, back, "x", Y0, 1, X0, sx0, 0, H + 0.03)
    shell.slat_wall(slat, back, "x", Y0, 1, sx1, X1, 0, H + 0.03)
    shell.panel_wall(stone, "x", Y0, 1, sx0, sx1, 0, H + 0.03, t=f)

    # ceiling: dark slats running east-west, light reveal along the north wall
    cs = MB("Main_ceiling_slats", P["wood_dark"], ceil, bevel=0.002)
    shell.slat_ceiling(cs, black, xw, ys, xe, yn - SLOT_W, H, along="x")
    cs.finish()
    shell.cove(lights, black, LM["cove"], "x", yn, -1, xw, xe, H, "LED_main_cove_north")

    # benches -----------------------------------------------------------
    mbs = {
        "boards": MB("Main_bench_boards", P["wood_bench"], coll, bevel=0.005, segments=3),
        "frame": MB("Main_bench_frame", P["wood_bench"], coll, bevel=0.003),
        "slat": slat,
        "back": back,
    }
    east_end = xe - 0.32
    Lb = east_end - xw
    legs_x = [2.0, 3.78, east_end - 0.06]
    d_up, d_low, rv_up, rv_low = 0.62, 0.72, 0.10, 0.32
    y_up, y_low = yn - d_up, yn - 2 * d_up
    ws = 10.55  # south end of the west return
    # back wall, upper tier
    F = Frame(xw, y_up, "+x", "+y")
    furniture.bench_tier(
        F,
        Lb,
        d_up,
        0.90,
        0.45,
        mbs,
        lights,
        LM["bench"],
        "main_back_upper",
        riser_v=rv_up,
        riser_run=(0.52, Lb),
        legs=[x - xw for x in legs_x],
        joints=[x - xw for x in legs_x[:2]],
        cheeks=(False, True),
    )
    # back wall, lower tier
    o = xw + d_up - rv_up
    F = Frame(o, y_low, "+x", "+y")
    furniture.bench_tier(
        F,
        east_end - o,
        d_low,
        0.45,
        0.0,
        mbs,
        lights,
        LM["bench"],
        "main_back_lower",
        riser_v=rv_low,
        riser_run=(0.40, east_end - o),
        legs=[x - o for x in legs_x],
        joints=[x - o for x in legs_x[:2]],
        cheeks=(False, True),
    )
    # west return, upper tier
    F = Frame(xw + d_up, ws, "+y", "-x")
    Lw = y_up - ws
    furniture.bench_tier(
        F,
        Lw,
        d_up,
        0.90,
        0.45,
        mbs,
        lights,
        LM["bench"],
        "main_west_upper",
        riser_v=rv_up,
        riser_run=(0.0, Lw + rv_up),
        legs=[0.06, Lw * 0.52],
        cheeks=(True, False),
    )
    # west return, lower tier
    F = Frame(xw + 2 * d_up, ws, "+y", "-x")
    Lw2 = y_low - ws
    furniture.bench_tier(
        F,
        Lw2,
        d_low,
        0.45,
        0.0,
        mbs,
        lights,
        LM["bench"],
        "main_west_lower",
        riser_v=rv_low,
        riser_run=(0.0, Lw2 + rv_low),
        legs=[0.06, Lw2 - 0.06],
        cheeks=(True, False),
    )
    furniture.backrest(
        Frame(xw, yn, "+x", "-y"), Lb, 1.15, mbs, joints=[x - xw for x in legs_x[:2]]
    )
    furniture.backrest(Frame(xw, ws, "+y", "+x"), yn - ws - 0.05, 1.15, mbs, joints=[1.45])
    for mb in (mbs["boards"], mbs["frame"]):
        mb.finish()
    slat.finish()
    back.finish(weighted=False)
    stone.finish()

    # heater, guard, hood, vents -------------------------------------------
    furniture.heater(P, coll, "Main_heater", hx, hy)
    hood = MB("Main_heater_hood", P["steel"], ceil, bevel=0)
    hood.lathe([(0.50, -0.06), (0.54, -0.035), (0.54, 0.0)], (hx, hy, H), seg=64, cap_top=False)
    hood.finish()
    furniture.grille(
        P, coll, "Main_supply_grille", "x", Y0 + f, 1, hx - 0.30, hx + 0.30, 0.08, 0.22, mat="steel"
    )
    furniture.grille(P, coll, "Main_exhaust_grille", "y", xe, -1, 9.35, 10.15, 2.13, 2.27)
    furniture.floor_drain(P, coll, "Main_floor_drain", 2.7, 11.1)
    trim = MB("Main_downlight_trims", P["steel"], ceil, bevel=0)
    for i, (dx, dy) in enumerate(((1.7, 11.2), (4.1, 11.2), (1.7, 12.3), (4.1, 12.3), (5.0, 9.9))):
        shell.downlight(trim, lights, LM["down_dim"], f"LED_main_down_{i}", dx, dy, H)
    for i, (dx, dy) in enumerate(((hx - 0.3, hy + 0.34), (hx + 0.3, hy + 0.34))):
        shell.downlight(trim, lights, LM["down"], f"LED_main_heater_{i}", dx, dy, H - 0.06, r=0.03)
    trim.finish()
    black.finish(weighted=False)
