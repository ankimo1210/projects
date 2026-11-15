"""Wet zone: two cold plunge pools + circulation strip, carbonated pool alcove, wash area (ceiling 2.7 m provisional)."""

import math

import bmesh
import bpy
from mathutils import Vector, noise

from . import geo, shell
from .geo import MB
from .shell import SLOT_H, SLOT_W, T_BACK, T_SLAT

WATER_DROP = 0.06  # water surface below deck level
COPING_W = 0.30


def water_body(name, mat, coll, x0, y0, x1, y1, z_top, z_bot, amp=0.0030, seed=1.0, cell=0.011):
    nx, ny = max(2, int((x1 - x0) / cell)), max(2, int((y1 - y0) / cell))
    bm = bmesh.new()
    grid = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x, y = x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny
            edge = min(x - x0, x1 - x, y - y0, y1 - y)
            fade = min(1.0, edge / 0.08)
            # long swell + mid ripples + short ripples (the short ones focus light at 0.5-1 m depth)
            wx = x + 0.05 * noise.noise(Vector((x * 3.0, y * 3.0, seed + 40.0)))
            wy = y + 0.05 * noise.noise(Vector((x * 3.0, y * 3.0, seed + 50.0)))
            h = (
                0.50 * noise.noise(Vector((wx * 2.3, wy * 2.3, seed)))
                + 0.34 * noise.noise(Vector((wx * 6.5, wy * 6.5, seed + 9.0)))
                + 0.30 * noise.noise(Vector((wx * 13.0, wy * 13.0, seed + 21.0)))
                + 0.16 * noise.noise(Vector((wx * 24.0, wy * 24.0, seed + 33.0)))
            )
            row.append(bm.verts.new((x, y, z_top + amp * 2.0 * h * (0.35 + 0.65 * fade))))
        grid.append(row)
    top = []
    for j in range(ny):
        for i in range(nx):
            top.append(
                bm.faces.new([grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]])
            )
    for f in top:
        f.smooth = True
    ring = (
        [grid[0][i] for i in range(nx + 1)]
        + [grid[j][nx] for j in range(1, ny + 1)]
        + [grid[ny][i] for i in range(nx - 1, -1, -1)]
        + [grid[j][0] for j in range(ny - 1, 0, -1)]
    )
    low = [bm.verts.new((v.co.x, v.co.y, z_bot)) for v in ring]
    n = len(ring)
    for k in range(n):
        k2 = (k + 1) % n
        bm.faces.new([ring[k2], ring[k], low[k], low[k2]])
    bm.faces.new(low)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.cycles.is_caustics_caster = True
    return ob


def caustic_spot(coll, name, x, y, z, watts=75.0, size=100.0, color=(1.0, 0.72, 0.44)):
    l = bpy.data.lights.new(name, "SPOT")
    l.energy = watts
    l.color = color
    l.spot_size = math.radians(size)
    l.spot_blend = 0.55
    l.shadow_soft_size = 0.012
    l.cycles.is_caustics_light = True
    ob = bpy.data.objects.new(name, l)
    ob.location = (x, y, z)
    coll.objects.link(ob)
    return ob


def handrail(mb, x, y_deck, y_low, z_low, top=0.90, r=0.019):
    """Inverted-U rail in the plane x: deck post -> horizontal -> slope down along the steps -> low post."""
    pts = [
        (x, y_deck, -0.01),
        (x, y_deck, top),
        (x, y_deck - 0.42, top),
        (x, y_low, z_low + 0.78),
        (x, y_low, z_low - 0.005),
    ]
    mb.tube(geo.fillet(pts, 0.07, 7), r, seg=18)
    mb.lathe(
        [(0.036, 0.0), (0.036, 0.005), (r + 0.002, 0.008)],
        (x, y_deck, 0.012),
        seg=20,
        cap_bottom=False,
    )
    mb.lathe(
        [(0.036, 0.0), (0.036, 0.005), (r + 0.002, 0.008)],
        (x, y_low, z_low),
        seg=20,
        cap_bottom=False,
    )


def pool(
    P,
    LM,
    coll,
    lights,
    pid,
    rect,
    depth,
    steps_w=0.9,
    ledge=False,
    curb_to=None,
    spots=(),
    seed=1.0,
    water_mat=None,
):
    """Recessed pool: lined basin, entry steps (north-west corner, descending south), coping, water, rail."""
    x, y, w, d = rect
    x1, y1 = x + w, y + d
    zf = -WATER_DROP - depth
    lin = MB(f"Pool_{pid}_lining", P["lining"], coll, bevel=0, smooth=False)
    lin.quad([(x, y, zf), (x1, y, zf), (x1, y1, zf), (x, y1, zf)])
    lin.quad([(x, y, zf), (x, y, 0), (x1, y, 0), (x1, y, zf)])
    lin.quad([(x1, y1, zf), (x1, y1, 0), (x, y1, 0), (x, y1, zf)])
    lin.quad([(x, y1, zf), (x, y1, 0), (x, y, 0), (x, y, zf)])
    lin.quad([(x1, y, zf), (x1, y, 0), (x1, y1, 0), (x1, y1, zf)])
    ob = lin.finish(weighted=False)
    ob.cycles.is_caustics_receiver = True
    # steps
    st = MB(f"Pool_{pid}_steps", P["lining"], coll, bevel=0.004, segments=2)
    n = max(1, round(depth / 0.24) - 1)
    rise = (depth + WATER_DROP) / (n + 1)
    tread = 0.28
    for k in range(n):
        ztop = -(k + 1) * rise
        st.box(
            x + 0.002, y1 - (k + 1) * tread, zf - 0.01, x + steps_w, y1 - k * tread - 0.002, ztop
        )
    if ledge:
        st.box(x + steps_w + 0.004, y + 0.002, zf - 0.01, x1 - 0.002, y + 0.38, zf + 0.26)
    ob = st.finish()
    ob.cycles.is_caustics_receiver = True
    # coping slabs (raised 12 mm, 15 mm overhang, bullnose)
    cp = MB(f"Pool_{pid}_coping", P["coping"], coll, bevel=0.006, segments=3)

    def slabs(a0, a1, fn):
        nseg = max(1, round((a1 - a0) / 0.6))
        for k in range(nseg):
            s0, s1 = a0 + (a1 - a0) * k / nseg, a0 + (a1 - a0) * (k + 1) / nseg
            fn(s0 + 0.0015, s1 - 0.0015)

    zc0, zc1 = -0.03, 0.012
    slabs(
        x - COPING_W, x1 + COPING_W, lambda a, b: cp.box(a, y1 - 0.015, zc0, b, y1 + COPING_W, zc1)
    )
    slabs(y, y1 - 0.018, lambda a, b: cp.box(x - COPING_W, a, zc0, x + 0.015, b, zc1))
    slabs(y, y1 - 0.018, lambda a, b: cp.box(x1 - 0.015, a, zc0, x1 + COPING_W, b, zc1))
    if curb_to is not None:  # raised curb between pool and the wall behind
        slabs(x - COPING_W, x1 + COPING_W, lambda a, b: cp.box(a, curb_to, zc0, b, y + 0.015, 0.11))
    else:
        slabs(
            x - COPING_W,
            x1 + COPING_W,
            lambda a, b: cp.box(a, y - COPING_W, zc0, b, y + 0.015, zc1),
        )
    cp.finish()
    # water
    # the water volume overlaps the lining by a few mm so tile surfaces are inside the water (single refractive interface)
    wat = water_body(
        f"Pool_{pid}_water",
        water_mat or P["water"],
        coll,
        x - 0.006,
        y - 0.006,
        x1 + 0.006,
        y1 + 0.006,
        -WATER_DROP,
        zf - 0.012,
        seed=seed,
    )
    # rail beside the steps
    rail = MB(f"Pool_{pid}_rail", P["stainless"], coll, bevel=0)
    handrail(rail, x + steps_w + 0.06, y1 + 0.14, y1 - (min(n, 3) - 0.5) * tread, -min(n, 3) * rise)
    rail.finish(weighted=False)
    # overflow slot under the north coping + inlet
    for i, (sx, sy) in enumerate(spots):
        caustic_spot(lights, f"Spot_{pid}_{i}", sx, sy, 2.7 - 0.05)
    return wat


def deck_drain(P, coll, name, x0, x1, y, w=0.07):
    """Linear slot drain with crosswise bars."""
    pit = MB(name + "_channel", P["black"], coll, bevel=0)
    pit.box(x0, y - w / 2, -0.03, x1, y + w / 2, 0.0005)
    pit.finish(weighted=False)
    mb = MB(name, P["stainless"], coll, bevel=0.0006, segments=1)
    mb.box(x0, y - w / 2 - 0.006, -0.004, x1, y - w / 2 + 0.004, 0.003)
    mb.box(x0, y + w / 2 - 0.004, -0.004, x1, y + w / 2 + 0.006, 0.003)
    n = int((x1 - x0) / 0.016)
    for k in range(n):
        xx = x0 + (x1 - x0) * (k + 0.5) / n
        mb.box(xx - 0.004, y - w / 2 + 0.004, -0.004, xx + 0.004, y + w / 2 - 0.004, 0.002)
    mb.finish()


def shower(mb, x, y, sign_x, head_z=2.05):
    """Simple wall shower on an x-facing wall: valve plate, riser, arm and head."""
    mb.box(min(x, x + sign_x * 0.012), y - 0.06, 1.0, max(x, x + sign_x * 0.012), y + 0.06, 1.12)
    mb.tube(
        geo.fillet(
            [
                (x + sign_x * 0.03, y, 1.06),
                (x + sign_x * 0.03, y, head_z),
                (x + sign_x * 0.30, y, head_z),
            ],
            0.05,
            6,
        ),
        0.011,
        seg=12,
    )
    mb.lathe(
        [(0.012, 0.0), (0.085, -0.012), (0.085, -0.022), (0.0, -0.022)][::-1],
        (x + sign_x * 0.30, y, head_z),
        seg=24,
        cap_bottom=False,
        cap_top=False,
    )
    mb.tube([(x, y, 1.06), (x + sign_x * 0.05, y, 1.06)], 0.02, seg=12)


def build(plan, P, LM, coll):
    H = 2.7
    f = T_BACK + T_SLAT
    ts = 0.014  # stone cladding thickness
    lights = geo.collection("Water_lights", coll)
    ceil = geo.collection("Ceilings", coll)
    dh = plan["doorHeight"]
    pools = {p["id"]: p for p in plan["pools"]}

    slat = MB("Water_wall_slats", P["wood"], coll, bevel=0.002)
    back = MB("Water_backing", P["wood_back"], coll, bevel=0)
    stone = MB("Water_wall_stone", P["wall_stone"], coll, bevel=0.0008, segments=1)
    black = MB("Water_cove_black", P["black"], ceil, bevel=0)

    # --- cold-plunge strip (x 6..17, y 6.5..10.5) ---
    xw, xe, ys, yn = 6.08, 16.92, 6.58, 10.42
    # south stone wall incl. free end of the added partition
    shell.panel_wall(stone, "x", ys, 1, xw, 14.98, 0, H + SLOT_H, t=ts)
    stone.box(14.98, 6.42 - ts, 0, 14.98 + ts, 6.58 + ts, H + 0.03)
    # west timber wall with the rest door and the main-sauna door
    shell.slat_wall(
        slat,
        back,
        "y",
        xw,
        1,
        ys + ts,
        yn,
        0,
        H + SLOT_H,
        openings=[(7.0, 8.1, 0, dh), (9.25, 10.25, 0, dh)],
    )
    # north timber wall (sauna fronts) with the self-loyly and dry sauna doors, plus its free end
    shell.slat_wall(
        slat,
        back,
        "x",
        yn,
        -1,
        xw + f,
        12.58,
        0,
        H + SLOT_H,
        openings=[(7.1, 8.1, 0, dh), (10.2, 11.2, 0, dh)],
    )
    # east wall: stone with rinse showers
    shell.panel_wall(stone, "y", xe, -1, 3.68, 13.92, 0, H + 0.03, t=ts)

    # --- carbonated pool alcove (x 12.5..17, y 10.5..14) ---
    shell.slat_wall(slat, back, "y", 12.58, 1, 10.42, 13.92, 0, H + 0.03)
    shell.panel_wall(stone, "x", 13.92, -1, 12.58 + f, xe - ts, 0, H + SLOT_H, t=ts)

    # --- wash area (x 10.5..17, y 3.6..6.5) ---
    shell.panel_wall(
        stone, "x", 3.68, 1, 10.58, xe - ts, 0, H + SLOT_H, t=ts, openings=[(10.5, 11.5, 0, dh)]
    )
    shell.panel_wall(stone, "y", 10.58, 1, 3.68 + ts, 6.42, 0, H + 0.03, t=ts)
    shell.panel_wall(stone, "x", 6.42, -1, 10.58 + ts, 14.98, 0, H + 0.03, t=ts)

    # --- semi-open timber fin screen in front of the carbonated-pool alcove (opening stays x 15.0..16.9) ---
    fins = MB("Carbon_screen_fins", P["wood"], coll, bevel=0.003)
    nf = int((15.0 - 12.62) / 0.115)
    for k in range(nf + 1):
        fx = 12.62 + (15.0 - 12.62) * k / nf
        fins.box(fx - 0.02, 10.40, 0.0, fx + 0.02, 10.50, H + 0.02, "z")
    fins.box(12.60, 10.41, 0.0, 15.02, 10.49, 0.05, "x")
    fins.finish()

    # --- ceilings: dark slats running along the strip ---
    cs = MB("Water_ceiling_slats", P["wood_dark"], ceil, bevel=0.002)
    shell.slat_ceiling(
        cs, black, xw + f + SLOT_W, ys + ts + SLOT_W, xe - ts, yn - f - 0.24, H, along="x"
    )
    shell.slat_ceiling(
        cs, black, 12.58, yn - f - 0.24, xe - ts, yn - f, H, along="x"
    )  # strip (west part bounded by north wall)
    shell.slat_ceiling(
        cs, black, 12.58 + f, yn - f, xe - ts, 13.92 - ts - SLOT_W, H, along="x"
    )  # carbon alcove
    shell.slat_ceiling(
        cs, black, 10.58 + ts, 3.68 + ts + SLOT_W, xe - ts, 6.42 - ts, H, along="x"
    )  # wash
    shell.slat_ceiling(
        cs, black, 14.98 + ts, 6.42 - ts, xe - ts, ys + ts + SLOT_W, H, along="x"
    )  # opening wash<->bath
    cs.finish()
    shell.cove(lights, black, LM["cove"], "x", ys + ts, 1, xw + f, 14.98, H, "LED_water_cove_south")
    shell.cove(
        lights, black, LM["cove_soft"], "y", xw + f, 1, ys + ts, yn - f, H, "LED_water_cove_west"
    )
    shell.cove(
        lights,
        black,
        LM["cove_wall"],
        "x",
        yn - f,
        -1,
        xw + f + SLOT_W,
        12.58,
        H,
        "LED_water_cove_north",
        mode="wall",
        slot=0.24,
        width=0.06,
    )
    shell.cove(
        lights, black, LM["cove"], "x", 13.92 - ts, -1, 12.58 + f, xe - ts, H, "LED_carbon_cove"
    )
    shell.cove(
        lights, black, LM["cove"], "x", 3.68 + ts, 1, 10.58 + ts, xe - ts, H, "LED_wash_cove"
    )

    # --- pools ---
    deep, seated, carb = pools["deep"], pools["seated"], pools["carbonPool"]
    pool(
        P,
        LM,
        coll,
        lights,
        "deep",
        deep["rect"],
        deep["depth"],
        curb_to=ys + ts,
        spots=[(8.4, 7.75), (9.6, 7.75)],
        seed=3.0,
    )
    pool(
        P,
        LM,
        coll,
        lights,
        "seated",
        seated["rect"],
        seated["depth"],
        ledge=True,
        curb_to=ys + ts,
        spots=[(12.5, 7.75), (13.7, 7.75)],
        seed=11.0,
    )
    pool(
        P,
        LM,
        coll,
        lights,
        "carbon",
        carb["rect"],
        carb["depth"],
        ledge=True,
        spots=[(14.2, 12.2), (15.5, 12.2)],
        seed=23.0,
        water_mat=P["water_warm"],
    )
    py1 = deep["rect"][1] + deep["rect"][3]
    deck_drain(P, coll, "Water_deck_drain", 6.75, 14.85, py1 + COPING_W + 0.05)
    deck_drain(P, coll, "Carbon_deck_drain", 12.9, 16.7, 10.72)

    # --- lights over the strip ---
    trim = MB("Water_downlight_trims", P["steel"], ceil, bevel=0)
    for i, dx in enumerate((7.3, 9.4, 11.5, 13.6, 15.7)):
        shell.downlight(trim, lights, LM["down_dim"], f"LED_water_down_{i}", dx, 9.72, H)
    for i, (dx, dy) in enumerate(
        ((12.4, 5.2), (14.4, 5.2), (16.0, 5.2), (16.0, 7.8), (14.0, 12.2), (15.8, 12.2))
    ):
        shell.downlight(trim, lights, LM["down_dim"], f"LED_wet_down_{i}", dx, dy, H)
    for p in (deep, seated, carb):
        pass
    for name in [o.name for o in lights.objects if o.name.startswith("Spot_")]:
        o = bpy.data.objects[name]
        trim.lathe(
            [(0.03, -0.014), (0.03, -0.05), (0.042, -0.05), (0.042, 0.0)],
            (o.location.x, o.location.y, H),
            seg=24,
            cap_top=False,
            cap_bottom=False,
        )
        o.location.z = H - 0.02
    trim.finish()

    # --- rinse showers on the east wall, wash stations ---
    sh = MB("Wet_showers", P["stainless"], coll, bevel=0)
    for yy in (7.3, 8.1, 8.9, 9.7):
        shower(sh, xe - ts, yy, -1)
    wash = MB("Wash_counter", P["coping"], coll, bevel=0.004, segments=2)
    mir = MB("Wash_mirrors", P["mirror"], coll, bevel=0.001, segments=1)
    stool = MB("Wash_stools", P["wood_chair"], coll, bevel=0.004, segments=2)
    ysw = 3.68 + ts
    stations = [(x, ysw, 1) for x in (12.2, 13.25, 14.3, 15.35, 16.4)] + [(11.4, 6.42 - ts, -1)]
    wash.box(11.7, ysw, 0.0, xe - ts, ysw + 0.26, 0.42)
    wash.box(10.9, 6.42 - ts - 0.26, 0.0, 11.9, 6.42 - ts, 0.42)
    for sx, sy, sg in stations:
        y_m0, y_m1 = sorted((sy, sy + sg * 0.012))
        mir.box(sx - 0.24, y_m0, 0.62, sx + 0.24, y_m1, 1.42)
        sh.tube(
            geo.fillet(
                [
                    (sx, sy + sg * 0.02, 0.52),
                    (sx, sy + sg * 0.16, 0.52),
                    (sx, sy + sg * 0.16, 0.47),
                ],
                0.03,
                5,
            ),
            0.012,
            seg=12,
        )
        sh.tube(
            [(sx + 0.16, sy + sg * 0.03, 0.56), (sx + 0.16, sy + sg * 0.03, 1.05)], 0.008, seg=10
        )
        sh.lathe(
            [(0.03, 0.0), (0.03, 0.02), (0.012, 0.03)], (sx + 0.16, sy + sg * 0.05, 1.05), seg=16
        )
        stool.lathe(
            [(0.15, 0.0), (0.16, 0.02), (0.16, 0.28), (0.15, 0.30)],
            (sx, sy + sg * 0.62, 0.0),
            seg=32,
        )
    wash.finish()
    mir.finish()
    stool.finish()
    sh.finish(weighted=False)

    slat.finish()
    back.finish(weighted=False)
    stone.finish()
    black.finish(weighted=False)
