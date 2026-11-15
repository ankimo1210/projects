"""Wet zone: two cold plunge pools + circulation strip, carbonated pool alcove, wash area (ceiling 2.7 m provisional).

v8: the two cold pools are smaller and stand at the east end of the old pool block; the freed west end is a rest annex
with four loungers behind a splash wall. Coordinates: water_layout.py. The carbonated pool, the spare perch seats, the
built-in seats, the showers and the wash area are as v7."""

import math

import bmesh
import bpy
from mathutils import Vector, noise

from . import furniture, geo, shell
from .geo import MB
from .scene import POOL_SPOT_W
from .shell import SLOT_H, SLOT_W, T_BACK, T_SLAT

WATER_DROP = 0.06  # water surface below deck level
COPING_W = 0.30
POOL_CORNER_R = {
    "turn": 0.22,
    "between": 0.12,
}  # v5 plan radii of the outer coping corners (study values)
BATH_SEAT = {
    "wing_round": (0.30, 0.34),
    "nose_r": 0.04,
    "under_r": 0.03,
    "lumbar": 0.014,
    "lumbar_h": 0.40,
}  # v5 section shapes


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


def caustic_spot(coll, name, x, y, z, watts=POOL_SPOT_W["v4"], size=100.0, color=(1.0, 0.72, 0.44)):
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
    corner_r=(0.0, 0.0),
):
    """Recessed pool: lined basin, entry steps (north-west corner, descending south), coping, water, rail.

    corner_r = plan radius of the outer coping corner at the north-west / north-east (walkway side). The basin, water and
    coping width are unchanged; only the outside corner of the end slab is rounded (v5)."""
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
    xa, xb, ya, yb = x - COPING_W, x1 + COPING_W, y1 - 0.015, y1 + COPING_W
    Mz = geo.basis(
        (0.0, 0.0, (zc0 + zc1) / 2), (1, 0, 0), (0, 0, 1), (0, 1, 0)
    )  # plan polygon extruded vertically

    def north_slab(a, b):
        rw = corner_r[0] if a < xa + 0.01 else 0.0
        re = corner_r[1] if b > xb - 0.01 else 0.0
        if not (rw or re):
            cp.box(a, ya, zc0, b, yb, zc1)
            return
        pts = [(a, ya), (b, ya)]
        if re:
            pts += [
                (
                    b - re + re * math.cos(math.pi / 2 * k / 12),
                    yb - re + re * math.sin(math.pi / 2 * k / 12),
                )
                for k in range(13)
            ]
        else:
            pts.append((b, yb))
        if rw:
            pts += [
                (
                    a + rw - rw * math.sin(math.pi / 2 * k / 12),
                    yb - rw + rw * math.cos(math.pi / 2 * k / 12),
                )
                for k in range(13)
            ]
        else:
            pts.append((a, yb))
        cp.prism(pts, Mz, zc1 - zc0)

    slabs(xa, xb, north_slab)
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


def stair_rail(mb, p, d, flat, run, z_top_low, z_base_low, top=0.90, r=0.019):
    """Grab rail beside pool steps. p = (x, y) of the deck post, d = plan direction of the descent; level for `flat`,
    then sloping to the low post at `run`, which stands on a surface at z_base_low (a tread or the coping)."""
    q1 = (p[0] + d[0] * flat, p[1] + d[1] * flat)
    q2 = (p[0] + d[0] * run, p[1] + d[1] * run)
    pts = [
        (p[0], p[1], -0.01),
        (p[0], p[1], top),
        (q1[0], q1[1], top),
        (q2[0], q2[1], z_top_low),
        (q2[0], q2[1], z_base_low - 0.005),
    ]
    mb.tube(geo.fillet(pts, 0.07, 7), r, seg=18)
    for (fx, fy), fz in ((p, 0.012), (q2, z_base_low)):
        mb.lathe(
            [(0.036, 0.0), (0.036, 0.005), (r + 0.002, 0.008)],
            (fx, fy, fz),
            seg=20,
            cap_bottom=False,
        )


def cold_pools(P, LM, coll, lights, curb_y):
    """v8: the two smaller cold pools at the east end of the old pool block (data: water_layout.py).

    Deep pool 1.78 x 1.9 m (1.2 m of water) with four treads in its north-east corner descending south; seated pool
    1.60 x 1.9 m (0.6 m) with two treads in its north-east corner, also descending south. One shared divider coping.
    The west side of the deep pool is the splash wall, so there is no coping there. No underwater ledge: in the seated
    pool people sit on the floor against the divider wall. Shape only; plant, water quality, slip resistance, barrier
    and rescue rules are not verified.
    """
    from . import water_layout as WL

    geo_pools = {pid: WL.pool(pid) for pid in ("deep", "seated")}
    for pid, seed in (("deep", 3.0), ("seated", 11.0)):
        pl = geo_pools[pid]
        x, y, x1, y1 = pl["rect"]
        zf = pl["floor_z"]
        lin = MB(f"Pool_{pid}_lining", P["lining"], coll, bevel=0, smooth=False)
        lin.quad([(x, y, zf), (x1, y, zf), (x1, y1, zf), (x, y1, zf)])
        lin.quad([(x, y, zf), (x, y, 0), (x1, y, 0), (x1, y, zf)])
        lin.quad([(x1, y1, zf), (x1, y1, 0), (x, y1, 0), (x, y1, zf)])
        lin.quad([(x, y1, zf), (x, y1, 0), (x, y, 0), (x, y, zf)])
        lin.quad([(x1, y, zf), (x1, y, 0), (x1, y1, 0), (x1, y1, zf)])
        lin.finish(weighted=False).cycles.is_caustics_receiver = True
        st = MB(f"Pool_{pid}_steps", P["lining"], coll, bevel=0.004, segments=2)
        for xa, ya, xb, yb, zt in pl["treads"]:
            st.box(
                max(xa, x + 0.002),
                max(ya, y + 0.002),
                zf - 0.01,
                min(xb, x1) - 0.002,
                min(yb, y1) - 0.002,
                zt,
            )
        st.finish().cycles.is_caustics_receiver = True
        water_body(
            f"Pool_{pid}_water",
            P["water"],
            coll,
            x - 0.006,
            y - 0.006,
            x1 + 0.006,
            y1 + 0.006,
            -WATER_DROP,
            zf - 0.012,
            seed=seed,
        )
        sx, sy = WL.SPOTS[pid]
        caustic_spot(lights, f"Spot_{pid}_0", sx, sy, 2.7 - 0.05)

    cp = MB("Pool_cold_coping", P["coping"], coll, bevel=0.006, segments=3)
    zc0, zc1 = -0.03, 0.012
    Mz = geo.basis((0.0, 0.0, (zc0 + zc1) / 2), (1, 0, 0), (0, 0, 1), (0, 1, 0))
    xa, xb = WL.SCREEN["x1"] + 0.002, WL.EAST_COPING[1]
    y0, y1 = geo_pools["deep"]["rect"][1], geo_pools["deep"]["rect"][3]
    ya, yb = y1 - 0.015, WL.COPING_N
    r = POOL_CORNER_R["turn"]

    def slabs(a0, a1, fn):
        nseg = max(1, round((a1 - a0) / 0.6))
        for k in range(nseg):
            fn(a0 + (a1 - a0) * k / nseg + 0.0015, a0 + (a1 - a0) * (k + 1) / nseg - 0.0015)

    def north(a, b):
        if b < xb - 0.01:
            cp.box(a, ya, zc0, b, yb, zc1)
            return
        pts = (
            [(a, ya), (b, ya)]
            + [
                (
                    b - r + r * math.cos(math.pi / 2 * k / 12),
                    yb - r + r * math.sin(math.pi / 2 * k / 12),
                )
                for k in range(13)
            ]
            + [(a, yb)]
        )
        cp.prism(pts, Mz, zc1 - zc0)

    slabs(xa, xb, north)  # walkway side, north-east corner rounded
    slabs(
        y0,
        y1 - 0.018,
        lambda a, b: cp.box(WL.DIVIDER[0] - 0.015, a, zc0, WL.DIVIDER[1] + 0.015, b, zc1),
    )  # shared divider
    slabs(
        y0, y1 - 0.018, lambda a, b: cp.box(WL.EAST_COPING[0] - 0.015, a, zc0, xb, b, zc1)
    )  # east coping (entry to the seated pool)
    slabs(
        xa, xb, lambda a, b: cp.box(a, curb_y, zc0, b, y0 + 0.015, 0.11)
    )  # raised curb against the south wall
    cp.finish()

    rail = MB("Pool_cold_rails", P["stainless"], coll, bevel=0)
    d = geo_pools["deep"]
    t = d["treads"][WL.RAILS["deep"]["low_tread"] - 1]
    xr = d["treads"][0][2] - WL.RAILS["deep"]["inset"]
    yd = d["rect"][3] + 0.14
    stair_rail(rail, (xr, yd), (0, -1), 0.14, yd - (t[1] + t[3]) / 2, t[4] + 0.78, t[4])
    rs = WL.RAILS["seated"]
    stair_rail(
        rail,
        (rs["x"], rs["y"][0]),
        (0, -1),
        rs["y"][0] - geo_pools["seated"]["rect"][3],
        rs["y"][0] - rs["y"][1],
        rs["low_h"],
        0.012,
    )
    rail.finish(weighted=False)


def splash_wall_and_annex(P, LM, coll, lights, y_stone, H):
    """v8: the floor freed by the smaller pools becomes a rest annex (data: water_layout.py).

    A 2.10 m wall stands between the annex and the deep pool (stone towards the water, timber towards the loungers); its
    walkway end comes down to 1.30 m as a quarter ellipse. Four loungers in two rows, heads east, all facing west; 1.30 m
    timber screens at the feet and between the pairs, and a 1.30 m screen with open fins above towards the walkway.
    Study shapes: splash, humidity, cleaning, supervision sight lines and egress are not verified.
    """
    from . import water_layout as WL

    sc, a = WL.SCREEN, WL.ANNEX
    panels = MB("Annex_partition_panels", P["wood_mid"], coll, bevel=0.004, segments=2)
    fins = MB("Annex_partition_fins", P["wood_mid"], coll, bevel=0.002)
    plinth = MB("Annex_partition_plinths", P["black"], coll, bevel=0)

    def eased(length, h, ea, eb):
        return [(0.0, h), (length - ea, h)] + [
            (
                length - ea + ea * math.sin(math.pi / 2 * k / 14),
                h - eb + eb * math.cos(math.pi / 2 * k / 14),
            )
            for k in range(1, 15)
        ]

    # splash wall
    L = sc["y1"] - y_stone
    line = eased(L, sc["h"], *sc["ease"])
    xt = sc["x0"] + sc["timber_t"]
    furniture.profile_panel(panels, (sc["x0"], y_stone, xt, sc["y1"]), 0.0, line, "start")
    st = MB("Water_splash_wall_stone", P["wall_stone"], coll, bevel=0.0008, segments=1)
    poly = [(y_stone, 0.0)] + [(y_stone + d, z) for d, z in line] + [(sc["y1"], 0.0)]
    st.prism(
        poly,
        geo.basis(((xt + sc["x1"]) / 2, 0.0, 0.0), (0, 1, 0), (1, 0, 0), (0, 0, 1)),
        sc["x1"] - xt,
        grain_along=False,
    )
    st.finish()

    # screens of the annex
    z0, ea, eb = a["z0"], *a["ease"]
    for name, x0, y0, x1, y1, h, fin_above in WL.partitions():
        if fin_above:
            furniture.board_panel(panels, (x0, y0, x1, y1), z0, h)
            furniture.fin_row(fins, (x0, y0, x1, y1), h, H + 0.02)
            plinth.box(x0 + 0.01, y0 + 0.004, 0.0, x1 - 0.01, y0 + 0.022, z0)
            shell.strip_down(
                lights,
                LM["rest_toe"],
                "LED_annex_toe",
                x0 + 0.10,
                y0 + 0.028,
                x1 - 0.10,
                y1 - 0.004,
                z0 - 0.004,
            )
            continue
        south = name.endswith("south")
        furniture.profile_panel(
            panels, (x0, y0, x1, y1), z0, eased(y1 - y0, h, ea, eb), "start" if south else "end"
        )
        plinth.box(
            x0 + 0.006,
            y0 + (0.01 if south else 0.07),
            0.0,
            x1 - 0.006,
            y1 - (0.07 if south else 0.01),
            z0,
        )
    panels.finish()
    fins.finish()
    plinth.finish(weighted=False)

    peg = MB("Annex_seat_pegs", P["wood_chair"], coll, bevel=0)
    for px, py, (dx, dy) in WL.pegs():
        z = WL.PEG_Z
        peg.tube([(px, py, z), (px + dx * 0.050, py + dy * 0.050, z + 0.005)], 0.011, seg=14)
        peg.tube(
            [
                (px + dx * 0.050, py + dy * 0.050, z + 0.005),
                (px + dx * 0.058, py + dy * 0.058, z + 0.006),
            ],
            0.016,
            seg=14,
        )
    peg.finish(weighted=False)

    mbs = {
        "frame": MB("Annex_chair_frames", P["wood_chair"], coll, bevel=0.004, segments=2),
        "slats": MB("Annex_chair_slats", P["wood_chair"], coll, bevel=0.004, segments=2),
    }
    for s in WL.loungers():
        furniture.slat_seat(mbs, s["foot"][0], s["foot"][1], s["heading"])
    for mb in mbs.values():
        mb.finish()
    furniture.floor_drain(P, coll, "Annex_floor_drain", *a["drain"])


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


def built_in_seat(P, LM, coll, lights, xf, y0, y1, seats=2):
    """Stone-tiled built-in rest seat in a niche on an x-facing wall (finished face xf, seat faces -x).

    Out of the water, for a short sit after the cold plunge. Wing walls carry the seat slabs and shield shower splash; the slabs
    stop 110 mm short of the wall and the wall-hung back pad floats 38 mm above them, so water drops to the open floor below.
    Shape and position only: slip resistance, waterproofing, hygiene, structure and durability are not verified.
    """
    wing_t, wing_d, wing_h = 0.08, 0.72, 1.50
    nose, back_x = xf - 0.57, xf - 0.11
    st = MB("Bath_seat_stone", P["coping"], coll, bevel=0.012, segments=3)
    from mathutils import Matrix

    # v5: the wing's front top corner comes down as a quarter ellipse (0.30 along, 0.34 down) — an arm-height shoulder
    # instead of a square slab end. Full height stays over the back two thirds (splash side of the showers).
    wa, wb = BATH_SEAT["wing_round"]
    wing_prof = (
        [(xf, 0.0), (xf, wing_h)]
        + [
            (
                xf - wing_d + wa - wa * math.sin(math.pi / 2 * k / 14),
                wing_h - wb + wb * math.cos(math.pi / 2 * k / 14),
            )
            for k in range(15)
        ]
        + [(xf - wing_d, 0.0)]
    )
    for yc in (y0 + wing_t / 2, y1 - wing_t / 2):
        st.prism(wing_prof, Matrix.Translation((0.0, yc, 0.0)), wing_t, grain_along=False)
    a, b = y0 + wing_t - 0.01, y1 - wing_t + 0.01
    slot = 0.03
    w = (b - a - slot * (seats - 1)) / seats
    # seat: same height, depth and 1.5 % fall as v4 (no dish, so water still runs off the front); the front edge rolls over
    # with a 40 mm radius under the thighs and the underside is eased back
    rn, ru = BATH_SEAT["nose_r"], BATH_SEAT["under_r"]
    z_nose = 0.432 - 0.015 * (back_x - nose - rn)
    seat_prof = (
        [(back_x, 0.355), (back_x, 0.432)]
        + [
            (
                nose + rn + rn * math.cos(math.pi / 2 + math.pi / 2 * k / 8),
                z_nose - rn + rn * math.sin(math.pi / 2 + math.pi / 2 * k / 8),
            )
            for k in range(9)
        ]
        + [
            (
                nose + ru + ru * math.cos(math.pi + math.pi / 2 * k / 6),
                0.355 + ru + ru * math.sin(math.pi + math.pi / 2 * k / 6),
            )
            for k in range(7)
        ]
    )
    # back pad: v4 wedge (110 mm at the bottom to 33 mm at the top, about 8 degrees) plus a shallow lumbar swell
    hb, sw, sh = 1.02 - 0.47, BATH_SEAT["lumbar"], BATH_SEAT["lumbar_h"]
    face = [
        (
            xf - (0.033 + 0.077 * (1 - h / hb) + sw * math.sin(math.pi * min(1.0, h / sh)) ** 2),
            0.47 + h,
        )
        for h in (hb * k / 18 for k in range(19))
    ]
    back_prof = [(xf, 0.47), (xf, 1.02)] + face[::-1]
    for k in range(seats):
        s0 = a + k * (w + slot)
        M = Matrix.Translation((0.0, s0 + w / 2, 0.0))
        st.prism(seat_prof, M, w, grain_along=False)
        st.prism(back_prof, Matrix.Translation((0.0, s0 + w / 2, 0.0)), w - 0.04, grain_along=False)
        if k:  # pier under each joint, set back for the heels
            st.box(nose + 0.11, s0 - slot / 2 - 0.05, 0.0, xf, s0 - slot / 2 + 0.05, 0.355)
    st.finish()
    shell.strip_down(
        lights,
        LM["bath_seat"],
        "LED_bath_seat",
        nose + 0.035,
        a + 0.05,
        nose + 0.06,
        b - 0.05,
        0.350,
    )
    bar = MB("Bath_seat_grab_bars", P["stainless"], coll, bevel=0)
    for yy, sg in ((y0 + wing_t, 1), (y1 - wing_t, -1)):
        xb = xf - wing_d + 0.07
        bar.tube(
            geo.fillet(
                [
                    (xb, yy, 0.74),
                    (xb, yy + sg * 0.05, 0.74),
                    (xb, yy + sg * 0.05, 1.22),
                    (xb, yy, 1.22),
                ],
                0.03,
                5,
            ),
            0.016,
            seg=14,
        )
    bar.finish(weighted=False)
    furniture.floor_drain(P, coll, "Bath_seat_floor_drain", xf - 0.24, y0 + wing_t + 0.45)


def perch_bench(P, LM, coll, lights, H=2.7):
    """v6: three spare perch seats in the recess that held the carbonated-pool fin screen (data: bath_layout.PERCH).

    For a short sit when the rest area and the two built-in seats are taken. Same stone, seat height, front roll and
    under-seat light and end wings as the built-in seats; shallower (0.35 m) and upright so it is not mistaken for a rest
    seat. The seat stays behind the wall line. The back keeps the alcove screened: stone to 1.10 m, timber fins above. Slip resistance, waterproofing, hygiene, structure and durability are not verified.
    """
    from . import bath_layout as BL

    p = BL.PERCH
    x0, x1, yf, yb = p["x0"], p["x1"], p["y_front"], p["y_back"]
    st = MB("Bath_perch_stone", P["coping"], coll, bevel=0.012, segments=3)

    def M(xc):  # prism frame: local X = world y (depth), local Y = world x (run), local Z = up
        return geo.basis((xc, 0.0, 0.0), (0, 1, 0), (1, 0, 0), (0, 0, 1))

    def shoulder(
        h, a, b
    ):  # side profile of a wing: full height at the back, quarter ellipse down to the front edge
        return (
            [(yb, 0.0), (yb, h)]
            + [
                (
                    yf + a - a * math.sin(math.pi / 2 * k / 14),
                    h - b + b * math.cos(math.pi / 2 * k / 14),
                )
                for k in range(15)
            ]
            + [(yf, 0.0)]
        )

    t = p["wing_t"]
    for xc in (x0 + t / 2, x1 - t / 2):
        st.prism(shoulder(p["wing_h"], *p["wing_round"]), M(xc), t, grain_along=False)
    seats = BL.perch_seats()
    w = seats[0]["pitch"]
    y_pad = yb - p["back_t"] - p["pad_t"]  # face of the back pad = rear edge of the seat slab
    st.box(x0 + t - 0.01, yb - p["back_t"], 0.0, x1 - t + 0.01, yb, p["back_h"])
    rn, ru, top, under = (
        BATH_SEAT["nose_r"],
        BATH_SEAT["under_r"],
        p["seat_top"],
        p["seat_top"] - 0.077,
    )
    z_nose = top - 0.015 * (y_pad - yf - rn)  # same 1.5 % fall to the front as the built-in seats
    seat_prof = (
        [(y_pad, under), (y_pad, top)]
        + [
            (
                yf + rn + rn * math.cos(math.pi / 2 + math.pi / 2 * k / 8),
                z_nose - rn + rn * math.sin(math.pi / 2 + math.pi / 2 * k / 8),
            )
            for k in range(9)
        ]
        + [
            (
                yf + ru + ru * math.cos(math.pi + math.pi / 2 * k / 6),
                under + ru + ru * math.sin(math.pi + math.pi / 2 * k / 6),
            )
            for k in range(7)
        ]
    )
    bar = MB("Bath_perch_grab_bars", P["stainless"], coll, bevel=0)
    for i, s in enumerate(seats):
        xc = s["b"][0]
        st.prism(
            seat_prof, M(xc), w + (0.02 if i in (0, len(seats) - 1) else 0.0), grain_along=False
        )
        st.box(xc - w / 2 + 0.03, y_pad, 0.50, xc + w / 2 - 0.03, yb - p["back_t"] + 0.004, 1.02)
        if i:  # pier under each joint, set back for the heels (as the built-in seats)
            xj = xc - w / 2 - p["slot"] / 2
            st.box(xj - 0.05, yf + 0.11, 0.0, xj + 0.05, yb - p["back_t"], under)
        shell.strip_down(
            lights,
            LM["bath_seat"],
            f"LED_bath_perch_{i}",
            xc - w / 2 + 0.05,
            yf + 0.035,
            xc + w / 2 - 0.05,
            yf + 0.06,
            under - 0.005,
        )
    st.finish()
    for xi, sg in (
        (x0 + t, 1),
        (x1 - t, -1),
    ):  # a grip on each end wing for standing up on a wet floor
        yy = yf + 0.07
        bar.tube(
            geo.fillet(
                [
                    (xi, yy, 0.74),
                    (xi + sg * 0.05, yy, 0.74),
                    (xi + sg * 0.05, yy, 1.22),
                    (xi, yy, 1.22),
                ],
                0.03,
                5,
            ),
            0.016,
            seg=14,
        )
    bar.finish(weighted=False)
    # timber fins above the stone back, as deep as the v5 screen allowed here (0.08 m at 0.10 m pitch)
    fins = MB("Carbon_screen_fins", P["wood"], coll, bevel=0.003)
    a, b = x0 + t + 0.03, x1 - t - 0.03
    n = int((b - a) / 0.10)
    fins.box(
        x0 + t + 0.004,
        yb - 0.085,
        p["back_h"] + 0.001,
        x1 - t - 0.004,
        yb,
        p["back_h"] + 0.036,
        "x",
    )  # sill on the stone back
    for k in range(n + 1):
        fx = a + (b - a) * k / n
        fins.box(fx - 0.0175, yb - 0.08, p["back_h"] + 0.036, fx + 0.0175, yb, H + 0.02, "z")
    fins.finish()


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
    # south wall: v8 timber slats behind the rest annex (west of the splash wall), stone behind the pools, incl. the free
    # end of the added partition
    from . import water_layout as WL

    x_sp = WL.SCREEN["x0"]
    shell.slat_wall(slat, back, "x", ys, 1, xw, x_sp, 0, H + SLOT_H)
    shell.panel_wall(stone, "x", ys, 1, x_sp, 14.98, 0, H + SLOT_H, t=ts)
    stone.box(14.98, 6.42 - ts, 0, 14.98 + ts, 6.58 + ts, H + 0.03)
    # west timber wall with the rest door and the main-sauna door
    shell.slat_wall(
        slat,
        back,
        "y",
        xw,
        1,
        ys + f,
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
    east_doors = [
        (min(d["seg"][1], d["seg"][3]), max(d["seg"][1], d["seg"][3]), 0, dh)
        for d in plan["doors"]
        if abs(d["seg"][0] - 17) < 1e-6
        and abs(d["seg"][2] - 17) < 1e-6
        and 3.68 < d["seg"][1] < 13.92
    ]
    shell.panel_wall(
        stone, "y", xe, -1, 3.68, 13.92, 0, H + 0.03, t=ts, openings=east_doors
    )  # back-of-house doors stay passable

    # --- carbonated pool alcove (x 12.5..17, y 10.5..14) ---
    tv = next(
        (o for o in plan.get("openings", []) if o.get("id") == "dry-tv"), None
    )  # service hatch of the TV recess
    hatch = [(tv["seg"][1], tv["seg"][3], tv["z"][0], tv["z"][1])] if tv else []
    shell.slat_wall(slat, back, "y", 12.58, 1, 10.42, 13.92, 0, H + 0.03, openings=hatch)
    shell.panel_wall(stone, "x", 13.92, -1, 12.58 + f, xe - ts, 0, H + SLOT_H, t=ts)

    # --- wash area (x 10.5..17, y 3.6..6.5) ---
    shell.panel_wall(
        stone, "x", 3.68, 1, 10.58, xe - ts, 0, H + SLOT_H, t=ts, openings=[(10.5, 11.5, 0, dh)]
    )
    shell.panel_wall(stone, "y", 10.58, 1, 3.68 + ts, 6.42, 0, H + 0.03, t=ts)
    shell.panel_wall(stone, "x", 6.42, -1, 10.58 + ts, 14.98, 0, H + 0.03, t=ts)

    # --- v6: the floor-to-ceiling fin screen in front of the carbonated-pool alcove (x 12.62..15.0) becomes a recess with three
    #     spare perch seats; stone back to 1.10 m and fins above keep the alcove screened (opening stays x 15.0..16.9) ---
    perch_bench(P, LM, coll, lights, H)

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
    # v8: the south reveal is split at the splash wall. Over the loungers it uses the dim rest-room strength (rest_cove_s),
    # over the pools the bath strength as before.
    shell.cove(
        lights,
        black,
        LM["rest_cove_s"],
        "x",
        ys + f,
        1,
        xw + f,
        x_sp,
        H,
        "LED_annex_cove_south",
        slot=SLOT_W - (f - ts),
    )
    shell.cove(
        lights,
        black,
        LM["bath_cove"],
        "x",
        ys + ts,
        1,
        WL.SCREEN["x1"],
        14.98,
        H,
        "LED_water_cove_south",
    )
    black.box(x_sp, ys + ts, H + SLOT_H, WL.SCREEN["x1"], ys + ts + SLOT_W, H + SLOT_H + 0.02)
    shell.cove(
        lights,
        black,
        LM["bath_cove_soft"],
        "y",
        xw + f,
        1,
        ys + f,
        yn - f,
        H,
        "LED_water_cove_west",
    )
    shell.cove(
        lights,
        black,
        LM["bath_cove_wall"],
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
        lights,
        black,
        LM["bath_cove"],
        "x",
        13.92 - ts,
        -1,
        12.58 + f,
        xe - ts,
        H,
        "LED_carbon_cove",
    )
    shell.cove(
        lights, black, LM["bath_cove"], "x", 3.68 + ts, 1, 10.58 + ts, xe - ts, H, "LED_wash_cove"
    )

    # --- pools ---
    deep, seated, carb = pools["deep"], pools["seated"], pools["carbonPool"]
    for pid, pp in (("deep", deep), ("seated", seated)):
        assert (
            max(abs(a - b) for a, b in zip(pp["rect"], WL.POOLS[pid]["rect"])) < 1e-6
            and abs(pp["depth"] - WL.POOLS[pid]["depth"]) < 1e-6
        ), "plan_a.json and water_layout.py disagree on the cold pools"
    # v8: two smaller cold pools at the east end, the splash wall and the rest annex on the freed floor
    cold_pools(P, LM, coll, lights, ys + ts)
    splash_wall_and_annex(P, LM, coll, lights, ys + ts, H)
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
    deck_drain(P, coll, "Water_deck_drain", WL.SCREEN["x1"] + 0.06, 14.85, WL.COPING_N + 0.05)
    deck_drain(
        P, coll, "Carbon_deck_drain", 15.08, 16.7, 10.72
    )  # v6: shortened; the part west of x=15 lay where the perch back now stands

    # --- lights over the strip ---
    trim = MB("Water_downlight_trims", P["steel"], ceil, bevel=0)
    for i, dx in enumerate((7.3, 9.4, 11.5, 13.6, 15.7)):
        shell.downlight(trim, lights, LM["bath_down"], f"LED_water_down_{i}", dx, 9.72, H)
    for i, (dx, dy) in enumerate(
        (
            (12.4, 5.2),
            (14.4, 5.2),
            (16.0, 5.2),
            (16.0, 7.45),
            (16.25, 9.35),
            (14.0, 12.2),
            (15.8, 12.2),
        )
    ):
        shell.downlight(trim, lights, LM["bath_down"], f"LED_wet_down_{i}", dx, dy, H)
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
    for yy in (7.05, 7.85):  # v3 had four; two give way to the built-in seat niche
        shower(sh, xe - ts, yy, -1)
    built_in_seat(P, LM, coll, lights, xe - ts, 8.40, 10.30)
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
