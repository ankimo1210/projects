"""Remaining rooms of plan A at lower detail: changing, entry, WC, staff, plant, linen, service, plus the TV recess and
the bucket used by the two small saunas (which v8 builds in room_sub.py).
Counts here (lockers, fixtures) are placeholders, not confirmed capacities."""

from . import geo, shell
from .geo import MB

TV = {  # dry-sauna TV recess in the east wall (reserved technical zone; study dimensions)
    "wall_x": 12.5,
    "sauna_face": 12.388,
    "alcove_face": 12.612,
    "screen": (0.94, 0.529),  # visible picture, 16:9 (about a 43-inch class)
    "glass": (1.06, 0.65),  # clear opening of the glazed front
    "centre": (12.75, 1.495),  # y, z of the picture centre
}


def tv_recess(plan, P, coll):
    """Display behind fixed double glazing inside a lined wall recess, serviced from the far (non-sauna) side.

    Geometry reserves space only. Heat/moisture rating of the equipment, cooling air path, condensation, electrical safety and
    maintenance access are NOT verified, and a consumer TV is not assumed to survive inside the hot room.
    """
    o = next(o for o in plan["openings"] if o["id"] == "dry-tv")
    y0, y1, (z0, z1) = o["seg"][1], o["seg"][3], o["z"]
    xs, xa = TV["sauna_face"], TV["alcove_face"]
    yc, zc = TV["centre"]
    steel = MB("Dry_TV_recess_steel", P["steel"], coll, bevel=0.0015, segments=1)
    for a, b, c, d in (
        (y0, y0 + 0.006, z0, z1),
        (y1 - 0.006, y1, z0, z1),
        (y0, y1, z0, z0 + 0.006),
        (y0, y1, z1 - 0.006, z1),
    ):
        steel.box(xs + 0.002, a, c, xa - 0.012, b, d)  # liner of the technical zone
    fw = 0.03
    for a, b, c, d in (
        (y0, y0 + fw, z0, z1),
        (y1 - fw, y1, z0, z1),
        (y0 + fw, y1 - fw, z0, z0 + fw),
        (y0 + fw, y1 - fw, z1 - fw, z1),
    ):
        steel.box(
            xs - 0.004, a, c, xs + 0.036, b, d
        )  # frame holding the glazing, flush with the slats
    steel.finish()
    gl = MB("Dry_TV_glazing", P["glass"], coll, bevel=0.001, segments=1)
    gl.box(
        xs + 0.002, y0 + fw - 0.004, z0 + fw - 0.004, xs + 0.012, y1 - fw + 0.004, z1 - fw + 0.004
    )  # outer pane (sauna side)
    gl.box(
        xs + 0.040, y0 + 0.008, z0 + 0.008, xs + 0.046, y1 - 0.008, z1 - 0.008
    )  # inner pane, air gap between
    gl.finish()
    sw, sh = TV["screen"]
    body = MB("Dry_TV_display_body", P["black"], coll, bevel=0.003, segments=2)
    body.box(
        xs + 0.085,
        yc - sw / 2 - 0.02,
        zc - sh / 2 - 0.02,
        xs + 0.145,
        yc + sw / 2 + 0.02,
        zc + sh / 2 + 0.03,
    )
    body.finish()
    import bpy

    me = bpy.data.meshes.new("Dry_TV_picture")
    xq = xs + 0.0835
    me.from_pydata(
        [
            (xq, yc + sw / 2, zc - sh / 2),
            (xq, yc - sw / 2, zc - sh / 2),
            (xq, yc - sw / 2, zc + sh / 2),
            (xq, yc + sw / 2, zc + sh / 2),
        ],
        [],
        [(0, 1, 2, 3)],
    )
    uv = me.uv_layers.new(name="UVMap")
    for loop, co in zip(uv.data, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop.uv = co
    me.materials.append(P["tv"])
    me.update()
    if me.polygons[0].normal.x > 0:
        me.flip_normals()
    coll.objects.link(bpy.data.objects.new("Dry_TV_picture", me))
    hatch = MB("Dry_TV_service_hatch", P["stainless"], coll, bevel=0.002, segments=1)
    hatch.box(
        xa - 0.012, y0 + 0.004, z0 + 0.004, xa, y1 - 0.004, z1 - 0.004
    )  # removable panel, carbonated-pool side
    for a, b, c, d in (
        (y0 - 0.025, y0 + 0.004, z0 - 0.025, z1 + 0.025),
        (y1 - 0.004, y1 + 0.025, z0 - 0.025, z1 + 0.025),
        (y0, y1, z0 - 0.025, z0 + 0.004),
        (y0, y1, z1 - 0.004, z1 + 0.025),
    ):
        hatch.box(xa - 0.004, a, c, xa + 0.006, b, d)
    for yy in (y0 + 0.10, y1 - 0.10):  # quarter-turn latches
        hatch.box(
            xa, yy - 0.012, (z0 + z1) / 2 - 0.03, xa + 0.008, yy + 0.012, (z0 + z1) / 2 + 0.03
        )
    hatch.finish()


def bucket(P, coll, name, x, y, ladle=(0.25, 0.10)):
    mb = MB(name, P["wood_bench"], coll, bevel=0.003)
    mb.lathe(
        [(0.11, 0.0), (0.13, 0.24), (0.118, 0.24), (0.10, 0.02)], (x, y, 0.0), seg=28, cap_top=False
    )
    mb.finish()
    ld = MB(name + "_ladle", P["wood_dark"], coll, bevel=0)
    sx = 0.05 if ladle[0] >= 0 else -0.05
    ld.tube([(x + sx, y, 0.20), (x + sx + ladle[0], y + ladle[1], 0.36)], 0.012, seg=10)
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


def build(plan, P, LM, coll, skip=(), rng_after_saunas=None):
    rooms = {r["id"]: r for r in plan["rooms"]}
    from . import room_sub

    room_sub.build_self(
        plan, P, LM, coll
    )  # v8: the two small saunas are built in room_sub.py (data: sub_layout.py)
    room_sub.build_dry(plan, P, LM, coll)
    if (
        rng_after_saunas is not None
    ):  # the service rooms and doors keep the board variation they had in v7
        geo.jump(rng_after_saunas)

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
                    LM["service_down"],
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
        z = 2.25 + k * 0.12  # overhead, so the staff route through the plant room stays walkable
        steel.tube(
            geo.fillet(
                [(18.6, 4.4 + k * 0.12, z), (17.5, 4.4 + k * 0.12, z), (17.5, 6.6, z)], 0.1, 5
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
