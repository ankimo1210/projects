"""Remaining rooms of plan A at lower detail: self-loyly sauna, dry sauna, changing, entry, WC, staff, plant, linen, service.
Counts here (seats, lockers, fixtures) are placeholders, not confirmed capacities."""

from . import furniture, geo, shell
from .furniture import Frame
from .geo import MB
from .shell import SLOT_H, SLOT_W, T_BACK, T_SLAT


def small_sauna(plan, P, LM, coll, rid, x0, x1, door, heater_xy, heater_r):
    """Sauna with two bench tiers along the north wall. x0/x1 = structural faces, door = (a0, a1) on the south wall."""
    Y0, Y1, H = 10.58, 13.92, 2.3
    f = T_BACK + T_SLAT
    lights = geo.collection(f"{rid}_lights", coll)
    ceil = geo.collection("Ceilings", coll)
    slat = MB(f"{rid}_wall_slats", P["wood"], coll, bevel=0.002)
    back = MB(f"{rid}_backing", P["wood_back"], coll, bevel=0)
    black = MB(f"{rid}_cove_black", P["black"], ceil, bevel=0)
    shell.slat_wall(slat, back, "x", Y1, -1, x0, x1, 0, H + SLOT_H)
    shell.slat_wall(
        slat,
        back,
        "x",
        Y0,
        1,
        x0,
        x1,
        0,
        H + 0.03,
        openings=[(door[0], door[1], 0, plan["doorHeight"])],
    )
    shell.slat_wall(slat, back, "y", x0, 1, Y0 + f, Y1 - f, 0, H + 0.03)
    shell.slat_wall(slat, back, "y", x1, -1, Y0 + f, Y1 - f, 0, H + 0.03)
    cs = MB(f"{rid}_ceiling_slats", P["wood_dark"], ceil, bevel=0.002)
    shell.slat_ceiling(cs, black, x0 + f, Y0 + f, x1 - f, Y1 - f - SLOT_W, H, along="x")
    cs.finish()
    shell.cove(lights, black, LM["cove"], "x", Y1 - f, -1, x0 + f, x1 - f, H, f"LED_{rid}_cove")
    mbs = {
        "boards": MB(f"{rid}_bench_boards", P["wood_bench"], coll, bevel=0.005, segments=3),
        "frame": MB(f"{rid}_bench_frame", P["wood_bench"], coll, bevel=0.003),
        "slat": slat,
        "back": back,
    }
    xa, xb, yn = x0 + f, x1 - f, Y1 - f
    L = xb - xa
    furniture.bench_tier(
        Frame(xa, yn - 0.62, "+x", "+y"),
        L,
        0.62,
        0.90,
        0.45,
        mbs,
        lights,
        LM["bench"],
        f"{rid}_upper",
        riser_v=0.10,
        legs=[0.06, L / 2, L - 0.06],
    )
    furniture.bench_tier(
        Frame(xa, yn - 1.24, "+x", "+y"),
        L,
        0.72,
        0.45,
        0.0,
        mbs,
        lights,
        LM["bench"],
        f"{rid}_lower",
        riser_v=0.32,
        legs=[0.06, L / 2, L - 0.06],
    )
    furniture.backrest(Frame(xa, yn, "+x", "-y"), L, 1.15, mbs)
    for mb in (mbs["boards"], mbs["frame"]):
        mb.finish()
    slat.finish()
    back.finish(weighted=False)
    furniture.heater(
        P,
        coll,
        f"{rid}_heater",
        heater_xy[0],
        heater_xy[1],
        r=heater_r,
        h=0.85,
        guard_r=heater_r + 0.27,
        guard_h=0.78,
    )
    trim = MB(f"{rid}_downlight_trims", P["steel"], ceil, bevel=0)
    shell.downlight(trim, lights, LM["down_dim"], f"LED_{rid}_down", (x0 + x1) / 2, 11.9, H)
    shell.downlight(
        trim, lights, LM["down"], f"LED_{rid}_heater", heater_xy[0], heater_xy[1] + 0.25, H, r=0.03
    )
    trim.finish()
    black.finish(weighted=False)


def bucket(P, coll, name, x, y):
    mb = MB(name, P["wood_bench"], coll, bevel=0.003)
    mb.lathe(
        [(0.11, 0.0), (0.13, 0.24), (0.118, 0.24), (0.10, 0.02)], (x, y, 0.0), seg=28, cap_top=False
    )
    mb.finish()
    ld = MB(name + "_ladle", P["wood_dark"], coll, bevel=0)
    ld.tube([(x + 0.05, y, 0.20), (x + 0.30, y + 0.10, 0.36)], 0.012, seg=10)
    ld.finish(weighted=False)


def lockers(mb, mb_gap, axis, fixed, sign, a0, cols, col_w=0.30, tiers=2, h=1.8, depth=0.45):
    """Locker bank: carcass box with door fronts separated by 4 mm shadow gaps."""
    shell.wall_box(
        mb_gap, axis, fixed, sign, 0.0, depth - 0.02, a0, a0 + cols * col_w, 0.08, h + 0.08
    )
    for c in range(cols):
        for t in range(tiers):
            z0 = 0.08 + t * h / tiers
            shell.wall_box(
                mb,
                axis,
                fixed,
                sign,
                depth - 0.02,
                depth,
                a0 + c * col_w + 0.002,
                a0 + (c + 1) * col_w - 0.002,
                z0 + 0.002,
                z0 + h / tiers - 0.002,
                "z",
            )
    shell.wall_box(mb_gap, axis, fixed, sign, 0.03, depth - 0.03, a0, a0 + cols * col_w, 0.0, 0.08)


def build(plan, P, LM, coll, skip=()):
    rooms = {r["id"]: r for r in plan["rooms"]}
    small_sauna(plan, P, LM, coll, "Self", 6.08, 9.42, (7.1, 8.1), (8.78, 11.25), 0.30)
    bucket(P, coll, "Self_loyly_bucket", 6.45, 12.25)
    small_sauna(plan, P, LM, coll, "Dry", 9.58, 12.42, (10.2, 11.2), (11.80, 11.24), 0.28)

    ceil = geo.collection("Ceilings", coll)
    lights = geo.collection("Service_lights", coll)
    trim = MB("Service_downlight_trims", P["steel"], ceil, bevel=0)
    for rid in ("entry", "change", "wc", "staff", "plant", "linen", "service"):
        r = rooms[rid]
        shell.plain_ceiling(r, P, coll)
        x, y, w, d = r["rect"]
        nx, ny = max(1, round(w / 2.2)), max(1, round(d / 2.2))
        for i in range(nx):
            for j in range(ny):
                shell.downlight(
                    trim,
                    lights,
                    LM["down"],
                    f"LED_{rid}_{i}{j}",
                    x + w * (i + 0.5) / nx,
                    y + d * (j + 0.5) / ny,
                    r["ceiling"],
                )
    trim.finish()

    wood = MB("Service_joinery", P["locker"], coll, bevel=0.003)
    dark = MB("Service_carcass", P["black"], coll, bevel=0)
    stone = MB("Service_stone_tops", P["coping"], coll, bevel=0.004)
    steel = MB("Service_equipment", P["steel"], coll, bevel=0.006)
    white = MB("Service_sanitary", P["white"], coll, bevel=0.01, segments=3)
    # entry: reception counter, shoe lockers, waiting bench
    wood.box(0.5, 2.2, 0.0, 2.6, 2.75, 1.0)
    stone.box(0.45, 2.15, 1.0, 2.65, 2.80, 1.04)
    lockers(wood, dark, "y", 0.08, 1, 0.3, 5, col_w=0.33, tiers=4, h=1.6, depth=0.36)
    wood.box(2.9, 0.35, 0.40, 3.8, 0.75, 0.45)
    for bx in (2.95, 3.70):
        wood.box(bx, 0.38, 0.0, bx + 0.05, 0.72, 0.40, "z")
    # changing: 48 placeholder lockers (2 tiers) + bench
    lockers(wood, dark, "x", 3.52, -1, 4.2, 20)
    lockers(wood, dark, "x", 0.08, 1, 5.2, 4)
    wood.box(6.2, 1.55, 0.40, 9.2, 1.95, 0.45)
    for bx in (6.3, 7.65, 9.05):
        wood.box(bx, 1.60, 0.0, bx + 0.05, 1.90, 0.40, "z")
    # WC / powder: two cubicles + vanity
    for cx in (12.55, 13.45):
        wood.box(cx - 0.02, 2.0, 0.1, cx + 0.02, 3.52, 2.0, "z")
        white.lathe(
            [(0.17, 0.0), (0.19, 0.36), (0.20, 0.40), (0.0, 0.40)],
            (cx + 0.42 if cx < 13 else cx + 0.42, 3.1, 0.0),
            seg=24,
            cap_top=False,
        )
    wood.box(12.55, 1.98, 0.1, 14.22, 2.02, 2.0, "z")
    stone.box(11.75, 0.10, 0.80, 13.6, 0.60, 0.85)
    for bx in (12.2, 13.1):
        white.lathe(
            [(0.10, 0.0), (0.19, 0.11), (0.20, 0.12), (0.18, 0.12), (0.09, 0.02)],
            (bx, 0.36, 0.85),
            seg=28,
            cap_top=False,
        )
    # staff: desk + shelving
    wood.box(14.6, 2.6, 0.70, 16.2, 3.3, 0.74)
    wood.box(14.62, 2.62, 0.0, 14.66, 3.28, 0.70, "z")
    wood.box(16.14, 2.62, 0.0, 16.18, 3.28, 0.70, "z")
    lockers(wood, dark, "y", 16.92, -1, 0.5, 3, col_w=0.4, tiers=1, h=1.9, depth=0.4)
    # plant: reserved equipment volumes (not sized)
    steel.box(17.4, 0.5, 0.0, 19.6, 1.6, 1.8)
    steel.box(18.6, 2.4, 0.0, 19.7, 4.2, 1.5)
    for cy in (5.0, 6.0):
        steel.lathe(
            [(0.38, 0.0), (0.40, 0.05), (0.40, 1.65), (0.30, 1.85), (0.0, 1.9)],
            (19.3, cy, 0.0),
            seg=32,
            cap_top=False,
        )
    for k in range(3):
        steel.tube(
            geo.fillet(
                [
                    (18.6, 4.4 + k * 0.12, 0.3 + k * 0.25),
                    (17.5, 4.4 + k * 0.12, 0.3 + k * 0.25),
                    (17.5, 6.6, 0.3 + k * 0.25),
                ],
                0.1,
                5,
            ),
            0.035,
            seg=12,
        )
    # linen + service
    for k in range(4):
        wood.box(19.45, 7.3, 0.3 + k * 0.45, 19.9, 9.7, 0.33 + k * 0.45)
    wood.box(19.45, 7.28, 0.0, 19.9, 7.32, 1.75, "z")
    wood.box(19.45, 9.68, 0.0, 19.9, 9.72, 1.75, "z")
    steel.box(17.5, 12.6, 0.0, 18.7, 13.7, 1.2)
    steel.box(19.0, 10.4, 0.0, 19.8, 11.6, 0.9)
    for mb in (wood, stone, steel, white):
        mb.finish()
    dark.finish(weighted=False)
