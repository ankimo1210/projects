"""Main aufguss sauna v6 (plan rect 0,9 6x5 m, ceiling 2.4 m provisional): central stove, benches on three sides.

All coordinates come from main_layout.py, which the check figures and the mesh check read as well.
North: two sitting tiers (0.90 / 0.45). West and east: one sitting tier with a foot bench (0.45) and a continuous half
step (0.225), so every side seat is reached from the aisle in two 0.225 m rises without passing anyone's knees.
The south side stays open for the door and the performer. Heater type, output and clearances are not selected.
"""

import math

from . import furniture, geo, materials, shell
from . import main_layout as ML
from .furniture import Frame
from .geo import MB
from .shell import SLOT_H, SLOT_W, T_BACK, T_SLAT


def build(plan, P, LM, coll):
    X0, X1, Y0, Y1, H = 0.08, 5.92, 9.08, 13.92, ML.H
    f = T_BACK + T_SLAT
    xw, xe, ys, yn = X0 + f, X1 - f, Y0 + f, Y1 - f
    assert max(abs(xw - ML.XW), abs(xe - ML.XE), abs(ys - ML.YS), abs(yn - ML.YN)) < 1e-6, (
        "main_layout.py and the wall lining disagree"
    )
    D = ML.dims()
    lights = geo.collection("Main_lights", coll)
    ceil = geo.collection("Ceilings", coll)

    slat = MB("Main_wall_slats", P["wood"], coll, bevel=0.002)
    back = MB("Main_backing", P["wood_back"], coll, bevel=0)
    stone = MB("Main_heat_shield", P["wall_stone"], coll, bevel=0.001, segments=1)
    black = MB("Main_cove_black", P["black"], ceil, bevel=0)
    hx, hy = ML.HEATER["c"]
    sx0, sx1 = (
        hx - 1.0,
        hx + 1.0,
    )  # stone panel on the south wall behind the performer (kept from v5, re-centred)
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
        openings=[(ML.DOOR[0], ML.DOOR[1], 0, plan["doorHeight"])],
    )
    shell.slat_wall(slat, back, "x", Y0, 1, X0, sx0, 0, H + 0.03)
    shell.slat_wall(slat, back, "x", Y0, 1, sx1, X1, 0, H + 0.03)
    shell.panel_wall(stone, "x", Y0, 1, sx0, sx1, 0, H + 0.03, t=f)

    # ceiling: dark slats running east-west, light reveal along the north wall (as v5)
    cs = MB("Main_ceiling_slats", P["wood_dark"], ceil, bevel=0.002)
    shell.slat_ceiling(cs, black, xw, ys, xe, yn - SLOT_W, H, along="x")
    cs.finish()
    shell.cove(lights, black, LM["sauna_cove"], "x", yn, -1, xw, xe, H, "LED_main_cove_north")

    # benches -----------------------------------------------------------
    mbs = {
        "boards": MB("Main_bench_boards", P["wood_bench"], coll, bevel=0.005, segments=3),
        "frame": MB("Main_bench_frame", P["wood_bench"], coll, bevel=0.003),
        "slat": slat,
        "back": back,
    }
    LB = LM["sauna_bench"]
    du, rv_up, rv_low, leg_in = ML.D_UP, 0.10, 0.32, 0.105
    up, low, stp = ML.TOP_UP, ML.TOP_LOW, ML.TOP_STEP
    R = ML.R_END
    y_up, y_low, y_end = D["n_upper_front"], D["n_lower_front"], ML.Y_END
    W = xe - xw
    third = [W / 3, 2 * W / 3]
    # north, upper tier: wall to wall; the two end squares are the corner seats
    furniture.bench_tier(
        Frame(xw, y_up, "+x", "+y"),
        W,
        du,
        up,
        low,
        mbs,
        lights,
        LB,
        "main_n_upper",
        riser_v=rv_up,
        riser_run=(du - rv_up, W - du + rv_up),
        legs=[du + 0.06] + third + [W - du - 0.06],
        joints=third,
        led_run=(du + 0.06, W - du - 0.06),
    )
    # north, lower tier (front row seat + foot strip for the upper row), between the risers of the side benches
    o = xw + du - rv_up
    Ln = (xe - du + rv_up) - o
    furniture.bench_tier(
        Frame(o, y_low, "+x", "+y"),
        Ln,
        ML.N_FOOT + ML.N_SEAT,
        low,
        0.0,
        mbs,
        lights,
        LB,
        "main_n_lower",
        riser_v=rv_low,
        riser_run=(D["w_foot_front"] - o, D["e_foot_front"] - o),
        legs=[D["w_step_front"] + 0.10 - o, Ln / 2, D["e_step_front"] - 0.10 - o],
        joints=[Ln / 3, 2 * Ln / 3],
        led_run=(D["w_step_front"] + 0.06 - o, D["e_step_front"] - 0.06 - o),
    )
    # west and east: sitting tier, foot bench, half step; all three end together at y_end with rounded free ends
    for side, x_up, x_foot, x_step, vdir in (
        ("w", D["w_upper_front"], D["w_foot_front"], D["w_step_front"], "-x"),
        ("e", D["e_upper_front"], D["e_foot_front"], D["e_step_front"], "+x"),
    ):
        Lu, Ll = y_up - y_end, y_low - y_end
        furniture.bench_tier(
            Frame(x_up, y_end, "+y", vdir),
            Lu,
            du,
            up,
            low,
            mbs,
            lights,
            LB,
            f"main_{side}_upper",
            riser_v=rv_up,
            riser_run=(0.0, Lu + rv_up),
            legs=[leg_in, Lu * 0.52],
            cheeks=(True, False),
            round_ends=(R["upper"], 0.0),
        )
        furniture.bench_tier(
            Frame(x_foot, y_end, "+y", vdir),
            Ll,
            ML.S_FOOT,
            low,
            0.0,
            mbs,
            lights,
            LB,
            f"main_{side}_foot",
            riser_v=0.10,
            riser_run=(0.0, Ll),
            legs=[leg_in, Ll - 0.06],
            cheeks=(True, False),
            round_ends=(R["foot"], 0.0),
            led_w=0.012,
        )
        # half step: open underneath (no riser, no hidden void), the strip under its nose marks the first rise
        furniture.bench_tier(
            Frame(x_step, y_end, "+y", vdir),
            Ll,
            ML.S_STEP,
            stp,
            0.0,
            mbs,
            lights,
            LB,
            f"main_{side}_step",
            riser_v=None,
            legs=[leg_in, Ll * 0.5, Ll - 0.06],
            cheeks=(True, False),
            round_ends=(R["step"], 0.0),
            led_w=0.012,
        )
    # diagonal boards across the inside corners (v5 motif): at the upper tier they widen the corner seat, at the half step
    # they give a turning tread towards the north landing. Frame origin = the inside corner, u / v along the two fronts.
    k = 0.03 / math.sqrt(2)  # fascia 30 mm behind the diagonal edge, like the aprons
    for xc, yc_, udir, top, g in (
        (D["w_upper_front"], y_up, "+x", up, ML.DIAG["upper"]),
        (D["e_upper_front"], y_up, "-x", up, ML.DIAG["upper"]),
        (D["w_step_front"], y_low, "+x", stp, ML.DIAG["step"]),
        (D["e_step_front"], y_low, "-x", stp, ML.DIAG["step"]),
    ):
        Fc = Frame(xc, yc_, udir, "-y")
        zb = top - furniture.BOARD_T
        furniture.plan_prism(
            mbs["boards"], Fc, [(-0.004, -0.004), (g, -0.004), (-0.004, g)], zb, top, grain="u"
        )
        furniture.plan_prism(
            mbs["frame"],
            Fc,
            [
                (g - 2 * k - 0.028, 0.0),
                (g - 2 * k, 0.0),
                (0.0, g - 2 * k),
                (0.0, g - 2 * k - 0.028),
            ],
            zb - furniture.APRON_H,
            zb,
            grain="u",
        )
    furniture.backrest(Frame(xw, yn, "+x", "-y"), W, 1.15, mbs, joints=third)
    furniture.backrest(Frame(xw, y_end, "+y", "+x"), yn - y_end - 0.05, 1.15, mbs, joints=[1.45])
    furniture.backrest(Frame(xe, y_end, "+y", "-x"), yn - y_end - 0.05, 1.15, mbs, joints=[1.45])
    for mb in (mbs["boards"], mbs["frame"]):
        mb.finish()
    slat.finish()
    back.finish(weighted=False)
    stone.finish()

    # heater in the middle of the floor the benches enclose, guard all round, hood, vents ---------------------
    furniture.heater(
        P,
        coll,
        "Main_heater",
        hx,
        hy,
        r=ML.HEATER["r"],
        h=ML.HEATER["h"],
        guard_r=ML.HEATER["guard_r"],
        guard_h=ML.HEATER["guard_h"],
    )
    hood = MB("Main_heater_hood", P["steel"], ceil, bevel=0)
    hood.lathe([(0.50, -0.06), (0.54, -0.035), (0.54, 0.0)], (hx, hy, H), seg=64, cap_top=False)
    hood.finish()
    furniture.grille(
        P, coll, "Main_supply_grille", "x", Y0 + f, 1, hx - 0.30, hx + 0.30, 0.08, 0.22, mat="steel"
    )
    furniture.grille(P, coll, "Main_exhaust_grille", "y", xe, -1, 9.35, 10.15, 2.13, 2.27)
    furniture.floor_drain(P, coll, "Main_floor_drain", hx, (ys + hy - D["guard_apothem"]) / 2)
    trim = MB("Main_downlight_trims", P["steel"], ceil, bevel=0)
    # as v4/v5: only the two dimmed heater accents, now beside the central stove (north-west / north-east of it)
    for i, (dx, dy) in enumerate(((hx - 0.3, hy + 0.34), (hx + 0.3, hy + 0.34))):
        shell.downlight(
            trim, lights, LM["sauna_heater"], f"LED_main_heater_{i}", dx, dy, H - 0.06, r=0.03
        )
    trim.finish()
    black.finish(weighted=False)


def check_layer(root):
    """Check layer: the 20 assumed seated bodies and four standing ones as plain boxes. Hidden in renders (render.py
    --show Check_people shows them) and tagged CHECK_ in the .glb so the viewer hides them until asked. Called last in
    build.py so it cannot shift the random board / stone variation of any room."""
    people = geo.collection("Check_people", root)
    people.hide_render = True
    seated = materials.flat("check_body", (0.62, 0.50, 0.40), 0.85)
    upright = materials.flat("check_body_standing", (0.36, 0.46, 0.56), 0.85)
    for s in ML.seats():
        mb = MB(f"Body_{s['id']}", seated, people, bevel=0.012, segments=2)
        for part, x0, y0, x1, y1, z0, z1 in ML.body_boxes(s):
            mb.box(x0, y0, z0, x1, y1, z1)
        mb.finish()
    for t in ML.standing():
        mb = MB(f"Body_{t['id']}", upright, people, bevel=0.012, segments=2)
        for part, x0, y0, x1, y1, z0, z1 in ML.standing_boxes(t):
            mb.box(x0, y0, z0, x1, y1, z1)
        mb.finish()
