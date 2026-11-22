"""V10 compact comparison model (170 m2, 24 people in house as an operating target): geometry builders.

All placements come from plan/compact_v10.json (metres, x east, y north, FL = 0). This module only turns them into
meshes with the V8 kit (sauna.geo / materials / shell / furniture / products / room_water), so timber boards, tile
joints, soft edges, coves, wet floor and rippled water are the same kind of geometry and shaders as in V8.
Nothing here is a scaled copy of the 280 m2 model. Study shapes only: structure, law, equipment and cost are not verified.

Collections: CompactV10 > Structure, Main, Self, Bath, Rest, Service, Doors, Cameras, CEIL_ceilings (objects CEIL_*),
CHECK_people (objects CHECK_*, render-hidden), STUDY_architecture (objects STUDY_*, render-hidden).
"""

import itertools
import math
import random

import bpy
from mathutils import Matrix
from sauna import furniture, geo, materials, products, room_water, shell
from sauna import scene as sc
from sauna.furniture import Frame
from sauna.geo import MB
from sauna.shell import SLOT_H, SLOT_W, T_BACK, T_SLAT

F_SLAT = T_BACK + T_SLAT  # finished timber wall: 12 mm backing + 20 mm slats
TS = 0.014  # stone cladding
DIR = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}
UP = 0.018  # upstand of a ceiling cove (shell.cove)


class Ctx:
    def __init__(self, plan, surface_palette, fixture_materials, root):
        self.plan, self.surface_palette, self.fixture_materials, self.root = (
            plan,
            surface_palette,
            fixture_materials,
            root,
        )
        self.th = plan["wallThickness"]
        self.zones = {z["id"]: z for z in plan["zones"]}
        self.ceil = geo.collection("CEIL_ceilings", root)
        self.check = geo.collection("CHECK_people", root)
        self.study = geo.collection("STUDY_architecture", root)
        self.doors = {d["id"]: d for d in plan["doors"]}
        self.bath_floor = products.bath_floor()

    def inner(self, zid):
        x, y, w, d = self.zones[zid]["rect"]
        t = self.th / 2
        return x + t, y + t, x + w - t, y + d - t

    def door(self, did):
        x0, y0, x1, y1 = self.doors[did]["seg"]
        return (min(y0, y1), max(y0, y1)) if abs(x1 - x0) < 1e-9 else (min(x0, x1), max(x0, x1))


def tag(ob, **kw):
    if ob is not None:
        for k, v in kw.items():
            ob[k] = v
    return ob


def eased(length, h, ea, eb):
    """Top edge of a screen: level, then a quarter ellipse down at the free end (V5/V8 motif)."""
    return [(0.0, h), (length - ea, h)] + [
        (
            length - ea + ea * math.sin(math.pi / 2 * k / 14),
            h - eb + eb * math.cos(math.pi / 2 * k / 14),
        )
        for k in range(1, 15)
    ]


def world_uv(ob):
    uv = ob.data.uv_layers.active
    for poly in ob.data.polygons:
        for li in poly.loop_indices:
            p = ob.data.vertices[ob.data.loops[li].vertex_index].co
            uv.data[li].uv = (p.x, p.y)


# ---------------------------------------------------------------------------------------------- structure
def build_structure(c):
    plan, surface_palette = c.plan, c.surface_palette
    th, room_height, dh = plan["wallThickness"], plan["structureHeight"], plan["doorHeight"]
    coll = geo.collection("Structure", c.root)
    mb = MB("Structure_Walls", surface_palette["plaster"], coll, bevel=0)
    segs = [list(s) for s in plan["walls"]] + [
        plan["screens"]["wash_lobby"],
        plan["screens"]["lobby_hall"],
    ]
    cuts = [(d["seg"], 0.0, dh) for d in plan["doors"]] + [
        (o["seg"], o["z"][0], o["z"][1]) for o in plan.get("openings", [])
    ]
    used = set()
    for x0, y0, x1, y1 in segs:
        horiz = abs(y1 - y0) < 1e-9
        a0, a1 = (min(x0, x1), max(x0, x1)) if horiz else (min(y0, y1), max(y0, y1))
        fixed = y0 if horiz else x0
        ops = []
        for i, ((dx0, dy0, dx1, dy1), lo, hi) in enumerate(cuts):
            if (abs(dy1 - dy0) < 1e-9) != horiz or abs((dy0 if horiz else dx0) - fixed) > 1e-6:
                continue
            s0, s1 = (min(dx0, dx1), max(dx0, dx1)) if horiz else (min(dy0, dy1), max(dy0, dy1))
            if s0 >= a0 - 1e-6 and s1 <= a1 + 1e-6:
                ops.append((s0, s1, lo, hi))
                used.add(i)
        for s0, s1, lo, hi in shell.split_openings(a0 - th / 2, a1 + th / 2, 0.0, room_height, ops):
            if horiz:
                mb.box(s0, fixed - th / 2, lo, s1, fixed + th / 2, hi)
            else:
                mb.box(fixed - th / 2, s0, lo, fixed + th / 2, s1, hi)
    if len(used) != len(cuts):
        raise RuntimeError(
            f"{len(cuts) - len(used)} door/opening segment(s) of the plan lie on no wall"
        )
    mb.finish(weighted=False)

    for z in plan["zones"]:
        x, y, w, d = z["rect"]
        wet = z["floor"] == "wet"
        fb = MB(
            f"Floor_{z['id']}",
            c.bath_floor if wet else surface_palette["floor"],
            coll,
            bevel=0,
            smooth=False,
        )
        holes = [p["rect"] for p in plan["pools"] if p["zone"] == z["id"]]
        xs = sorted({x, x + w} | {v for h in holes for v in (h[0], h[0] + h[2])})
        ys = sorted({y, y + d} | {v for h in holes for v in (h[1], h[1] + h[3])})
        for xa, xb in itertools.pairwise(xs):
            for ya, yb in itertools.pairwise(ys):
                cx, cy = (xa + xb) / 2, (ya + yb) / 2
                if any(h[0] < cx < h[0] + h[2] and h[1] < cy < h[1] + h[3] for h in holes):
                    continue
                fb.quad([(xa, ya, 0), (xb, ya, 0), (xb, yb, 0), (xa, yb, 0)])
        ob = tag(fb.finish(weighted=False), v10_zone=z["id"])
        if wet:
            world_uv(ob)
            ob["product"] = (
                "LIXIL IFT-300/ST-33N bathroom-floor type; colour provisional (comparison stage, as V7/V8)"
            )
    roof = MB("CEIL_Structure_Roof", surface_palette["struct"], c.ceil, bevel=0)
    roof.box(-0.1, -0.1, room_height, plan["width"] + 0.1, plan["height"] + 0.1, room_height + 0.15)
    roof.finish(weighted=False)


def bench_set(prefix, surface_palette, coll, slat, back):
    return {
        "boards": MB(
            f"{prefix}_bench_boards", surface_palette["wood_bench"], coll, bevel=0.004, segments=3
        ),
        "frame": MB(f"{prefix}_bench_frame", surface_palette["wood_bench"], coll, bevel=0.003),
        "slat": slat,
        "back": back,
    }


def bucket(surface_palette, coll, name, x, y, ladle_heading=(1.0, 0.0)):
    mb = MB(name, surface_palette["wood_bench"], coll, bevel=0.003)
    mb.lathe(
        [(0.11, 0.0), (0.13, 0.24), (0.118, 0.24), (0.10, 0.02)], (x, y, 0.0), seg=28, cap_top=False
    )
    mb.finish()
    ld = MB(name + "_ladle", surface_palette["wood_dark"], coll, bevel=0)
    dx, dy = ladle_heading
    ld.tube(
        [
            (x + 0.05 * dx, y + 0.05 * dy, 0.20),
            (x + 0.30 * dx - 0.10 * dy, y + 0.30 * dy + 0.10 * dx, 0.36),
        ],
        0.012,
        seg=10,
    )
    ld.finish(weighted=False)


def sauna_shell(c, zid, prefix, coll, lights, door_side, door_range):
    """Timber slat walls on all four sides, dark slat ceiling, concealed strip above the north (bench) wall."""
    surface_palette, fixture_materials = c.surface_palette, c.fixture_materials
    room_height, dh, f = c.zones[zid]["ceiling"], c.plan["doorHeight"], F_SLAT
    x0, y0, x1, y1 = c.inner(zid)
    slat = MB(f"{prefix}_wall_slats", surface_palette["wood"], coll, bevel=0.002)
    back = MB(f"{prefix}_backing", surface_palette["wood_back"], coll, bevel=0)
    black = MB(f"CEIL_{prefix}_cove_black", surface_palette["black"], c.ceil, bevel=0)
    op = [(door_range[0], door_range[1], 0, dh)]
    shell.slat_wall(slat, back, "x", y1, -1, x0, x1, 0, room_height + SLOT_H)
    shell.slat_wall(
        slat,
        back,
        "x",
        y0,
        1,
        x0,
        x1,
        0,
        room_height + SLOT_H,
        openings=op if door_side == "S" else (),
    )
    shell.slat_wall(slat, back, "y", x0, 1, y0 + f, y1 - f, 0, room_height + SLOT_H)
    shell.slat_wall(
        slat,
        back,
        "y",
        x1,
        -1,
        y0 + f,
        y1 - f,
        0,
        room_height + SLOT_H,
        openings=op if door_side == "E" else (),
    )
    cs = MB(f"CEIL_{prefix}_ceiling_slats", surface_palette["wood_dark"], c.ceil, bevel=0.002)
    shell.slat_ceiling(
        cs, black, x0 + f, y0 + f, x1 - f, y1 - f - SLOT_W - UP, room_height, along="x"
    )
    cs.finish()
    shell.cove(
        lights,
        black,
        fixture_materials["sauna_cove"],
        "x",
        y1 - f,
        -1,
        x0 + f,
        x1 - f,
        room_height,
        f"LED_{prefix.lower()}_cove_north",
    )
    return x0 + f, x1 - f, y0 + f, y1 - f, slat, back, black


def north_tiers(floor_frame, xw, xe, yn, nb, mbs, lights, fixture_materials, name):
    """Two tiers on the north wall: the lower one runs under the nose of the upper one up to its riser."""
    span_length = xe - xw
    yu = yn - nb["upper"]["depth"]
    yl = yu - nb["lower"]["depth"]
    furniture.bench_tier(
        Frame(xw, yl, "+x", "+y"),
        span_length,
        nb["lower"]["depth"] + 0.095,
        nb["lower"]["top"],
        0.0,
        mbs,
        lights,
        fixture_materials["sauna_bench"],
        f"{name}_north_lower",
    )
    furniture.bench_tier(
        Frame(xw, yu, "+x", "+y"),
        span_length,
        nb["upper"]["depth"],
        nb["upper"]["top"],
        nb["lower"]["top"],
        mbs,
        lights,
        fixture_materials["sauna_bench"],
        f"{name}_north_upper",
    )
    furniture.backrest(Frame(xw, yn, "+x", "-y"), span_length, nb["upper"]["top"] + 0.24, mbs)
    return yl


_zl_stone = {}


def zl300(surface_palette, coll, name, cx, cy, size):
    """Exterior approximation of the METOS ZIEL ZL-300 used in V7/V8 (same proportions and stone study). Not CAD."""
    w, d, h = size
    metal = materials.brushed("ZIEL_stainless_APPROX", color=(0.52, 0.54, 0.56), rough=0.36)
    body = MB(f"{name}_casing_APPROX", metal, coll, bevel=0.0015, segments=2)
    body.box(cx - w / 2, cy - d / 2, 0.075, cx + w / 2, cy + d / 2, 0.595)
    body.finish()
    det = MB(f"{name}_rim_and_legs_APPROX", metal, coll, bevel=0.001, segments=1)
    for x in (cx - w / 2 + 0.055, cx + w / 2 - 0.055):
        for y in (cy - d / 2 + 0.055, cy + d / 2 - 0.055):
            det.box(x - 0.018, y - 0.018, 0, x + 0.018, y + 0.018, 0.075)
    for y in (cy - d / 2 + 0.008, cy + d / 2 - 0.008):
        det.box(cx - w / 2, y - 0.008, 0.580, cx + w / 2, y + 0.008, 0.607)
    for x in (cx - w / 2 + 0.008, cx + w / 2 - 0.008):
        det.box(x - 0.008, cy - d / 2, 0.580, x + 0.008, cy + d / 2, 0.607)
    for i in range(12):
        x = cx - w / 2 + 0.035 + i * (w - 0.070) / 11
        det.box(x - 0.003, cy - d / 2 + 0.015, 0.588, x + 0.003, cy + d / 2 - 0.015, 0.597)
    det.finish()
    if "mesh" not in _zl_stone:
        _zl_stone["mesh"] = products.stone_mesh()
        _zl_stone["mesh"].materials.append(products.ceramic())
    stone = _zl_stone["mesh"]
    sc_coll = geo.collection(f"{name}_stones", coll)
    rng = random.Random(300)
    for row in range(3):
        for col in range(6):
            ob = bpy.data.objects.new(f"{name}_stone_APPROX_{row}_{col}", stone)
            sc_coll.objects.link(ob)
            ob.location = (
                cx - 0.350 + col * 0.140 + rng.uniform(-0.006, 0.006),
                cy - 0.160 + row * 0.160 + rng.uniform(-0.006, 0.006),
                0.640 + rng.uniform(-0.003, 0.003),
            )
            ob.scale = (0.065, 0.065, 0.055 + rng.uniform(-0.004, 0.004))
            ob.rotation_euler = (
                rng.uniform(-0.25, 0.25),
                rng.uniform(-0.25, 0.25),
                rng.uniform(0, math.tau),
            )
    top = bpy.data.objects.new(f"{name}_stone_APPROX_top", stone)
    sc_coll.objects.link(top)
    top.location = (cx, cy, 0.660)
    top.scale = (0.065, 0.062, 0.050)
    bpy.context.view_layer.update()
    highest = max((top.matrix_world @ v.co).z for v in stone.vertices)
    top.location.z += h - highest


def rect_guard(surface_palette, coll, name, x0, y0, x1, y1, h):
    """Timber rails on steel posts around the stove (centre lines of the rails on the given rectangle)."""
    gp = MB(f"{name}_guard_posts", surface_palette["steel"], coll, bevel=0.002, segments=1)
    gr = MB(f"{name}_guard_rails", surface_palette["wood_bench"], coll, bevel=0.005, segments=3)
    xm = (x0 + x1) / 2
    for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (xm, y0), (xm, y1)):
        gp.box(px - 0.02, py - 0.02, 0, px + 0.02, py + 0.02, h, "z")
        gp.lathe([(0.05, 0.0), (0.05, 0.006)], (px, py, 0), seg=16)
    for z in (h - 0.035, h * 0.5):
        for y in (y0, y1):
            for xa, xb in ((x0, xm), (xm, x1)):
                gr.box(xa + 0.026, y - 0.021, z - 0.035, xb - 0.026, y + 0.021, z + 0.035, "x")
        for x in (x0, x1):
            gr.box(x - 0.021, y0 + 0.026, z - 0.035, x + 0.021, y1 - 0.026, z + 0.035, "y")
    gp.finish()
    gr.finish()


# ---------------------------------------------------------------------------------------------- main sauna
def build_main(c):
    """Stove a little towards the back, benches on three sides (12 seats), open performer floor towards the door side."""
    surface_palette, fixture_materials, m = c.surface_palette, c.fixture_materials, c.plan["main"]
    room_height = c.zones["main"]["ceiling"]
    coll = geo.collection("Main", c.root)
    lights = geo.collection("Main_lights", coll)
    xw, xe, ys, yn, slat, back, black = sauna_shell(
        c, "main", "Main", coll, lights, "E", c.door("main")
    )
    mbs = bench_set("Main", surface_palette, coll, slat, back)
    north_tiers(None, xw, xe, yn, m["bench"]["north"], mbs, lights, fixture_materials, "main")
    sb = m["bench"]["side"]
    span_length = sb["y1"] - sb["y0"]
    furniture.bench_tier(
        Frame(xw + sb["depth"], sb["y0"], "+y", "-x"),
        span_length,
        sb["depth"],
        sb["top"],
        0.0,
        mbs,
        lights,
        fixture_materials["sauna_bench"],
        "main_west",
        round_ends=(sb["end_radius"], 0.0),
        cheeks=(True, False),
    )
    furniture.bench_tier(
        Frame(xe - sb["depth"], sb["y1"], "-y", "+x"),
        span_length,
        sb["depth"],
        sb["top"],
        0.0,
        mbs,
        lights,
        fixture_materials["sauna_bench"],
        "main_east",
        round_ends=(0.0, sb["end_radius"]),
        cheeks=(False, True),
    )
    furniture.backrest(
        Frame(xw, sb["y0"] + 0.03, "+y", "+x"), span_length - 0.03, sb["top"] + 0.24, mbs
    )
    furniture.backrest(
        Frame(xe, sb["y0"] + 0.03, "+y", "-x"), span_length - 0.03, sb["top"] + 0.24, mbs
    )
    for k in ("boards", "frame"):
        mbs[k].finish()
    h = m["heater"]
    step = MB("Main_access_steps_225", surface_palette["wood_bench"], coll, bevel=0.004, segments=3)
    for xa, xb in ((1.0, 1.6), (3.1, 3.7)):
        step.box(xa, 8.50, 0.0, xb, 8.798, 0.225)
    tag(
        step.finish(),
        v10_note="Intermediate access step; upper footboard travel still requires human review",
    )
    (cx, cy), (w, d, _hh), go = h["centre"], h["size"], h["guard_offset"]
    zl300(surface_palette, coll, "Main_ZL300", cx, cy, h["size"])
    rect_guard(
        surface_palette,
        coll,
        "Main_heater",
        cx - w / 2 - go,
        cy - d / 2 - go,
        cx + w / 2 + go,
        cy + d / 2 + go,
        h["guard_h"],
    )
    trim = MB("CEIL_Main_downlight_trims", surface_palette["steel"], c.ceil, bevel=0)
    for i, dx in enumerate((-0.3, 0.3)):
        shell.downlight(
            trim,
            lights,
            fixture_materials["sauna_heater"],
            f"LED_main_heater_{i}",
            cx + dx,
            cy + 0.30,
            room_height,
            r=0.03,
        )
    trim.finish()
    furniture.floor_drain(surface_palette, coll, "Main_floor_drain", *m["drain"])
    furniture.grille(surface_palette, coll, "Main_vent_low", "x", ys, 1, 1.5, 2.0, 0.12, 0.30)
    furniture.grille(surface_palette, coll, "Main_vent_high", "x", yn, -1, 1.7, 2.3, 2.02, 2.20)
    bucket(surface_palette, coll, "Main_bucket", *m["bucket"])
    slat.finish()
    back.finish(weighted=False)
    black.finish(weighted=False)


# ---------------------------------------------------------------------------------------------- self-loyly sauna
def build_self(c):
    """About 10 m2: two tiers on the north wall (4 seats), a low bench on the west wall (2), stove in the south-east corner."""
    surface_palette, fixture_materials, s = c.surface_palette, c.fixture_materials, c.plan["self"]
    room_height = c.zones["self"]["ceiling"]
    coll = geo.collection("Self", c.root)
    lights = geo.collection("Self_lights", coll)
    xw, xe, _ys, yn, slat, back, black = sauna_shell(
        c, "self", "Self", coll, lights, "S", c.door("self")
    )
    mbs = bench_set("Self", surface_palette, coll, slat, back)
    north_tiers(None, xw, xe, yn, s["bench"]["north"], mbs, lights, fixture_materials, "self")
    wb = s["bench"]["west"]
    span_length = wb["y1"] - wb["y0"]
    furniture.bench_tier(
        Frame(xw + wb["depth"], wb["y0"], "+y", "-x"),
        span_length,
        wb["depth"],
        wb["top"],
        0.0,
        mbs,
        lights,
        fixture_materials["sauna_bench"],
        "self_west",
        round_ends=(wb["end_radius"], 0.0),
        cheeks=(True, False),
    )
    furniture.backrest(
        Frame(xw, wb["y0"] + 0.03, "+y", "+x"), span_length - 0.03, wb["top"] + 0.24, mbs
    )
    for k in ("boards", "frame"):
        mbs[k].finish()
    h = s["heater"]
    furniture.heater(
        surface_palette,
        coll,
        "Self_heater",
        h["centre"][0],
        h["centre"][1],
        r=h["r"],
        h=h["h"],
        guard_r=h["guard_r"],
        guard_h=h["guard_h"],
    )
    trim = MB("CEIL_Self_downlight_trims", surface_palette["steel"], c.ceil, bevel=0)
    shell.downlight(
        trim,
        lights,
        fixture_materials["sauna_heater"],
        "LED_self_heater_0",
        h["centre"][0] - 0.25,
        h["centre"][1] + 0.25,
        room_height,
        r=0.03,
    )
    trim.finish()
    furniture.floor_drain(surface_palette, coll, "Self_floor_drain", *s["drain"])
    furniture.grille(surface_palette, coll, "Self_vent_high", "x", yn, -1, 5.2, 5.7, 2.02, 2.20)
    bucket(surface_palette, coll, "Self_bucket", *s["bucket"], ladle_heading=(0.0, 1.0))
    step = MB("Self_access_step_225", surface_palette["wood_bench"], coll, bevel=0.004, segments=3)
    step.box(5.65, 8.50, 0.0, 6.25, 8.798, 0.225)
    step.finish()
    slat.finish()
    back.finish(weighted=False)
    black.finish(weighted=False)


# ---------------------------------------------------------------------------------------------- wet zone
def shower_y(mb, x, y, sign_y, head_z=2.05):
    """Wall shower on a y-facing wall (room_water.shower turned by 90 degrees): valve plate, riser, arm, head."""
    mb.box(x - 0.06, min(y, y + sign_y * 0.012), 1.0, x + 0.06, max(y, y + sign_y * 0.012), 1.12)
    mb.tube(
        geo.fillet(
            [
                (x, y + sign_y * 0.03, 1.06),
                (x, y + sign_y * 0.03, head_z),
                (x, y + sign_y * 0.30, head_z),
            ],
            0.05,
            6,
        ),
        0.011,
        seg=12,
    )
    mb.lathe(
        [(0.012, 0.0), (0.085, -0.012), (0.085, -0.022), (0.0, -0.022)][::-1],
        (x, y + sign_y * 0.30, head_z),
        seg=24,
        cap_bottom=False,
        cap_top=False,
    )
    mb.tube([(x, y, 1.06), (x, y + sign_y * 0.05, 1.06)], 0.02, seg=12)


def build_pools(c, coll, lights, trim, room_height):
    """Cold pool and carbonated pool, 2.4 x 1.8 m of water each, side by side on the north wall with one divider coping."""
    surface_palette, plan = c.surface_palette, c.plan
    drop = plan["assumptions"]["water_drop"]
    pc = plan["pool_coping"]
    yn = plan["height"] - c.th / 2 - TS
    for p in plan["pools"]:
        pid = p["id"]
        x, y, w, d = p["rect"]
        x1, y1 = x + w, y + d
        zf = -drop - p["depth"]
        lin = MB(f"Pool_{pid}_lining", surface_palette["lining"], coll, bevel=0, smooth=False)
        lin.quad([(x, y, zf), (x1, y, zf), (x1, y1, zf), (x, y1, zf)])
        lin.quad([(x, y, zf), (x, y, 0), (x1, y, 0), (x1, y, zf)])
        lin.quad([(x1, y1, zf), (x1, y1, 0), (x, y1, 0), (x, y1, zf)])
        lin.quad([(x, y1, zf), (x, y1, 0), (x, y, 0), (x, y, zf)])
        lin.quad([(x1, y, zf), (x1, y, 0), (x1, y1, 0), (x1, y1, zf)])
        tag(lin.finish(weighted=False), v10_pool=pid).cycles.is_caustics_receiver = True
        st = MB(f"Pool_{pid}_steps", surface_palette["lining"], coll, bevel=0.004, segments=2)
        for xa, ya, xb, yb, zt in p["treads"]:
            st.box(
                max(xa, x + 0.002),
                max(ya, y + 0.002),
                zf - 0.01,
                min(xb, x1) - 0.002,
                min(yb, y1) - 0.002,
                zt,
            )
        tag(st.finish(), v10_pool=pid).cycles.is_caustics_receiver = True
        wat = room_water.water_body(
            f"Pool_{pid}_water",
            surface_palette["water"] if pid == "cold" else surface_palette["water_warm"],
            coll,
            x - 0.006,
            y - 0.006,
            x1 + 0.006,
            y1 + 0.006,
            -drop,
            zf - 0.012,
            seed=p["seed"],
        )
        tag(wat, v10_pool=pid)
        sx, sy = p["spot"]
        room_water.caustic_spot(lights, f"Spot_{pid}_0", sx, sy, room_height - 0.02)
        trim.lathe(
            [(0.03, -0.014), (0.03, -0.05), (0.042, -0.05), (0.042, 0.0)],
            (sx, sy, room_height),
            seg=24,
            cap_top=False,
            cap_bottom=False,
        )

    cp = MB("Pool_coping", surface_palette["coping"], coll, bevel=0.006, segments=3)
    zc0, zc1 = -0.03, 0.012
    rects = [p["rect"] for p in plan["pools"]]
    ya, yb = rects[0][1], rects[0][1] + rects[0][3]

    def slabs(a0, a1, fn):
        n = max(1, round((a1 - a0) / 0.6))
        for k in range(n):
            fn(a0 + (a1 - a0) * k / n + 0.0015, a0 + (a1 - a0) * (k + 1) / n - 0.0015)

    slabs(
        pc["x0"], pc["x1"], lambda a, b: cp.box(a, pc["front_y"], zc0, b, ya + 0.015, zc1)
    )  # hall side
    slabs(
        pc["x0"], pc["x1"], lambda a, b: cp.box(a, yb - 0.015, zc0, b, yn, pc["curb_top"])
    )  # raised curb at the wall
    edges = [pc["x0"]] + [v for r in rects for v in (r[0], r[0] + r[2])] + [pc["x1"]]
    for xa, xb in zip(edges[0::2], edges[1::2], strict=False):  # two ends + the divider
        slabs(
            ya + 0.018,
            yb - 0.018,
            lambda a, b, xa=xa, xb=xb: cp.box(
                xa - (0.015 if xa > pc["x0"] else 0),
                a,
                zc0,
                xb + (0.015 if xb < pc["x1"] else 0),
                b,
                zc1,
            ),
        )
    cp.finish()
    rail = MB("Pool_rails", surface_palette["stainless"], coll, bevel=0)
    for p in plan["pools"]:
        r = p["rail"]
        room_water.stair_rail(
            rail, tuple(r["post"]), tuple(r["dir"]), r["flat"], r["run"], r["low_top"], zc1
        )
    rail.finish(weighted=False)


def build_bath(c):
    """Pools, bath hall with a waiting perch, wash bays (4 showers), the walk in front of the saunas, the entry lobby."""
    surface_palette, fixture_materials, plan = c.surface_palette, c.fixture_materials, c.plan
    room_height, dh, t, f = c.zones["bathHall"]["ceiling"], plan["doorHeight"], c.th / 2, F_SLAT
    coll = geo.collection("Bath", c.root)
    lights = geo.collection("Bath_lights", coll)
    bath_west, bath_south = (
        c.zones["wash"]["rect"][0] + t,
        c.zones["wash"]["rect"][1] + t,
    )  # main east wall / changing north wall
    bath_east, bath_north = (
        c.zones["rest"]["rect"][0] - t,
        plan["height"] - t,
    )  # rest west wall / north wall
    self_east_edge = c.zones["pools"]["rect"][0] + t  # self east wall, bath side
    self_south_edge = c.zones["self"]["rect"][1] - t  # self south wall, bath side
    sw, lw = plan["screens"]["wash_lobby"], plan["screens"]["lobby_hall"]
    xs_w, xs_e, ys_end = sw[0] - t, sw[0] + t, sw[3] + t
    yl_s, yl_n, xl_end = lw[1] - t, lw[1] + t, lw[0] - t
    yp = c.zones["pools"]["rect"][1]
    y_split = plan["wash"]["stone_to_y"]
    md, sd, rd, cl, pl = (
        c.door("main"),
        c.door("self"),
        c.door("rest"),
        c.door("change-lobby"),
        c.door("plant"),
    )

    stone = MB("Bath_wall_stone", surface_palette["wall_stone"], coll, bevel=0.0008, segments=1)
    slat = MB("Bath_wall_slats", surface_palette["wood"], coll, bevel=0.002)
    back = MB("Bath_backing", surface_palette["wood_back"], coll, bevel=0)
    black = MB("CEIL_Bath_cove_black", surface_palette["black"], c.ceil, bevel=0)
    # stone where water splashes: behind and beside the pools, around the showers, the hall side of the lobby wall
    shell.panel_wall(
        stone, "x", bath_north, -1, self_east_edge, bath_east, 0, room_height + SLOT_H, t=TS
    )
    shell.panel_wall(
        stone, "y", self_east_edge, 1, self_south_edge, bath_north - TS, 0, room_height + 0.03, t=TS
    )
    shell.panel_wall(stone, "y", bath_east, -1, yp, bath_north - TS, 0, room_height + 0.03, t=TS)
    shell.panel_wall(
        stone,
        "y",
        bath_west,
        1,
        bath_south,
        y_split,
        0,
        room_height + 0.03,
        t=TS,
        openings=[(md[0], md[1], 0, dh)],
    )
    shell.panel_wall(stone, "x", bath_south, 1, bath_west + TS, xs_w, 0, room_height + SLOT_H, t=TS)
    shell.panel_wall(stone, "y", xs_w, -1, bath_south + TS, ys_end, 0, room_height + 0.03, t=TS)
    stone.box(xs_w - TS, ys_end, 0, xs_e + f, ys_end + TS, room_height + 0.03)
    shell.panel_wall(stone, "x", yl_n, 1, xl_end, bath_east, 0, room_height + 0.03, t=TS)
    stone.box(xl_end - TS, yl_s - f, 0, xl_end, yl_n + TS, room_height + 0.03)
    # timber: sauna fronts, the rest wall towards the hall, the entry lobby
    shell.slat_wall(
        slat,
        back,
        "x",
        self_south_edge,
        -1,
        bath_west,
        self_east_edge,
        0,
        room_height + 0.03,
        openings=[(sd[0], sd[1], 0, dh)],
    )
    shell.slat_wall(
        slat,
        back,
        "y",
        bath_west,
        1,
        y_split,
        self_south_edge - f,
        0,
        room_height + 0.03,
        openings=[(md[0], md[1], 0, dh)],
    )
    shell.slat_wall(
        slat,
        back,
        "y",
        bath_east,
        -1,
        yl_n + TS,
        yp,
        0,
        room_height + 0.03,
        openings=[(rd[0], rd[1], 0, dh)],
    )
    shell.slat_wall(slat, back, "y", xs_e, 1, bath_south, ys_end, 0, room_height + 0.03)
    shell.slat_wall(
        slat,
        back,
        "x",
        bath_south,
        1,
        xs_e + f,
        bath_east,
        0,
        room_height + SLOT_H,
        openings=[(cl[0], cl[1], 0, dh), (pl[0], pl[1], 0, dh)],
    )
    shell.slat_wall(slat, back, "x", yl_s, -1, xl_end, bath_east, 0, room_height + 0.03)
    shell.slat_wall(slat, back, "y", bath_east, -1, bath_south + f, yl_s - f, 0, room_height + 0.03)

    # ceilings: dark slats; reveals with concealed strips at the shower wall, the lobby wall and behind the pools
    cs = MB("CEIL_Bath_ceiling_slats", surface_palette["wood_dark"], c.ceil, bevel=0.002)
    y_c0 = bath_south + f + SLOT_W + UP
    y_c1 = bath_north - TS - SLOT_W - UP
    shell.slat_ceiling(
        cs, black, bath_west, y_c0, bath_east, self_south_edge, room_height, along="x"
    )
    shell.slat_ceiling(
        cs, black, self_east_edge, self_south_edge, bath_east, y_c1, room_height, along="x"
    )
    cs.finish()
    shell.cove(
        lights,
        black,
        fixture_materials["bath_cove"],
        "x",
        bath_south + TS,
        1,
        bath_west + TS,
        xs_w,
        room_height,
        "LED_wash_cove",
        slot=SLOT_W + (f - TS),
    )
    shell.cove(
        lights,
        black,
        fixture_materials["bath_cove_soft"],
        "x",
        bath_south + f,
        1,
        xs_e + f,
        bath_east - f,
        room_height,
        "LED_lobby_cove",
    )
    shell.cove(
        lights,
        black,
        fixture_materials["bath_cove"],
        "x",
        bath_north - TS,
        -1,
        self_east_edge + TS,
        bath_east - TS,
        room_height,
        "LED_pool_cove",
    )
    trim = MB("CEIL_Bath_downlight_trims", surface_palette["steel"], c.ceil, bevel=0)
    for i, (dx, dy) in enumerate(plan["hall"]["downlights"]):
        shell.downlight(
            trim, lights, fixture_materials["bath_down"], f"LED_bath_down_{i}", dx, dy, room_height
        )

    build_pools(c, coll, lights, trim, room_height)
    trim.finish()
    hd = plan["hall"]["drain"]
    room_water.deck_drain(surface_palette, coll, "Bath_deck_drain", hd["x0"], hd["x1"], hd["y"])

    # wash bays on the changing-room wall: stone dividers with an eased top, one shower set and a stool per bay
    wa = plan["wash"]
    wy = bath_south + TS
    dv = wa["divider"]
    div = MB("Wash_dividers", surface_palette["coping"], coll, bevel=0.012, segments=3)
    prof = (
        [(wy, 0.0)]
        + [(wy + d, z) for d, z in eased(dv["depth"], dv["h"], 0.30, 0.34)]
        + [(wy + dv["depth"], 0.0)]
    )
    for x in wa["dividers"]:
        div.prism(
            prof,
            geo.basis((x, 0.0, 0.0), (0, 1, 0), (1, 0, 0), (0, 0, 1)),
            dv["t"],
            grain_along=False,
        )
    div.finish()
    stool = MB("Wash_stools", surface_palette["wood_chair"], coll, bevel=0.004, segments=2)
    shelf = MB("Wash_shelves", surface_palette["coping"], coll, bevel=0.004, segments=2)
    for i, x in enumerate(wa["showers"]):
        sh = MB(f"Wash_shower_{i + 1}", surface_palette["stainless"], coll, bevel=0)
        shower_y(sh, x, wy, 1)
        tag(sh.finish(weighted=False), v10_item="shower", v10_zone="wash")
        stool.lathe(
            [(0.15, 0.0), (0.16, 0.02), (0.16, 0.28), (0.15, 0.30)], (x, wy + 0.40, 0.0), seg=32
        )
        shelf.box(x + 0.20, wy, 0.84, x + 0.40, wy + 0.11, 0.865)
    stool.finish()
    shelf.finish()
    wd = wa["drain"]
    room_water.deck_drain(surface_palette, coll, "Wash_drain", wd["x0"], wd["x1"], wd["y"])

    # waiting perch on the hall side of the lobby wall (not counted as rest seats)
    pe = plan["hall"]["perch"]
    px0, py0, px1, py1 = pe["rect"]
    st = MB("Hall_perch_stone", surface_palette["coping"], coll, bevel=0.012, segments=3)
    n = len(pe["seats"])
    for k in range(n):
        a, b = px0 + (px1 - px0) * k / n + 0.006, px0 + (px1 - px0) * (k + 1) / n - 0.006
        st.box(a, py0, pe["top"] - 0.07, b, py1, pe["top"])
    for k in range(n + 1):
        xx = min(max(px0 + (px1 - px0) * k / n, px0 + 0.06), px1 - 0.06)
        st.box(xx - 0.05, py0, 0.0, xx + 0.05, py1 - 0.11, pe["top"] - 0.07)
    st.finish()
    shell.strip_down(
        lights,
        fixture_materials["bath_seat"],
        "LED_hall_perch",
        px0 + 0.05,
        py1 - 0.06,
        px1 - 0.05,
        py1 - 0.035,
        pe["top"] - 0.075,
    )

    # entry lobby: towel shelf on the hall wall, water counter at the east end
    lb = plan["lobby"]
    tx0, ty0, tx1, ty1 = lb["towel_shelf"]
    wood = MB("Lobby_towel_shelf", surface_palette["wood_mid"], coll, bevel=0.003)
    for zz in (0.45, 0.95, 1.45):
        wood.box(tx0, ty0, zz, tx1, ty1, zz + 0.03, "x")
    for xx in (tx0, (tx0 + tx1) / 2 - 0.015, tx1 - 0.03):
        wood.box(xx, ty0 + 0.01, 0.0, xx + 0.03, ty1, 1.75, "z")
    wood.finish()
    tw = MB("Lobby_towels", surface_palette["white"], coll, bevel=0.012, segments=3)
    for zz in (0.48, 0.98):
        for k in range(5):
            xx = tx0 + 0.10 + k * (tx1 - tx0 - 0.5) / 4
            tw.box(xx, ty0 + 0.04, zz, xx + 0.30, ty1 - 0.03, zz + 0.12)
    tw.finish()
    wx0, wy0, wx1, wy1 = lb["water_counter"]
    base = MB("Lobby_water_base", surface_palette["wood_mid"], coll, bevel=0.003)
    furniture.board_panel(base, (wx0, wy0, wx0 + 0.03, wy1), 0.05, 0.84)
    base.box(wx0 + 0.03, wy0, 0.05, wx1, wy0 + 0.03, 0.82, "z")
    base.box(wx0 + 0.03, wy1 - 0.03, 0.05, wx1, wy1, 0.82, "z")
    base.finish()
    top = MB("Lobby_water_top", surface_palette["coping"], coll, bevel=0.004, segments=2)
    top.box(wx0 - 0.015, wy0 - 0.015, 0.84, wx1, wy1 + 0.015, 0.88)
    top.finish()
    disp = MB("Lobby_water_dispenser", surface_palette["stainless"], coll, bevel=0)
    disp.lathe(
        [(0.11, 0.0), (0.11, 0.32), (0.09, 0.34), (0.0, 0.34)],
        ((wx0 + wx1) / 2, wy0 + 0.25, 0.88),
        seg=28,
        cap_top=False,
    )
    disp.finish(weighted=False)

    slat.finish()
    back.finish(weighted=False)
    stone.finish()
    black.finish(weighted=False)


# ---------------------------------------------------------------------------------------------- rest room
def build_rest(c):
    """14 places in the room plus 2 built-in places in the bath hall; all face north."""
    surface_palette, fixture_materials, r = c.surface_palette, c.fixture_materials, c.plan["rest"]
    room_height, dh, f = c.zones["rest"]["ceiling"], c.plan["doorHeight"], F_SLAT
    x0, y0, x1, y1 = c.inner("rest")
    rd = c.door("rest")
    coll = geo.collection("Rest", c.root)
    lights = geo.collection("Rest_lights", coll)
    slat = MB("Rest_wall_slats", surface_palette["wood"], coll, bevel=0.002)
    back = MB("Rest_backing", surface_palette["wood_back"], coll, bevel=0)
    black = MB("CEIL_Rest_cove_black", surface_palette["black"], c.ceil, bevel=0)
    shell.slat_wall(slat, back, "x", y1, -1, x0, x1, 0, room_height + SLOT_H)
    shell.slat_wall(slat, back, "x", y0, 1, x0, x1, 0, room_height + SLOT_H)
    shell.slat_wall(
        slat,
        back,
        "y",
        x0,
        1,
        y0 + f,
        y1 - f,
        0,
        room_height + 0.03,
        openings=[(rd[0], rd[1], 0, dh)],
    )
    shell.slat_wall(slat, back, "y", x1, -1, y0 + f, y1 - f, 0, room_height + 0.03)
    cs = MB("CEIL_Rest_ceiling_slats", surface_palette["wood_dark"], c.ceil, bevel=0.002)
    shell.slat_ceiling(
        cs,
        black,
        x0 + f,
        y0 + f + SLOT_W + UP,
        x1 - f,
        y1 - f - SLOT_W - UP,
        room_height,
        along="y",
    )
    cs.finish()
    shell.cove(
        lights,
        black,
        fixture_materials["rest_cove_n"],
        "x",
        y1 - f,
        -1,
        x0 + f,
        x1 - f,
        room_height,
        "LED_rest_cove_north",
    )
    shell.cove(
        lights,
        black,
        fixture_materials["rest_cove_s"],
        "x",
        y0 + f,
        1,
        x0 + f,
        x1 - f,
        room_height,
        "LED_rest_cove_south",
    )

    for s in r["chairs"]:
        mbs = {
            "frame": MB(
                f"Rest_chair_{s['id']}_frame",
                surface_palette["wood_chair"],
                coll,
                bevel=0.004,
                segments=2,
            ),
            "slats": MB(
                f"Rest_chair_{s['id']}_slats",
                surface_palette["wood_chair"],
                coll,
                bevel=0.004,
                segments=2,
            ),
        }
        furniture.slat_seat(
            mbs,
            s["foot"][0],
            s["foot"][1],
            tuple(s["heading"]),
            profile=furniture.CHAIR_PROFILE,
            legs=((0.10, 0.0), (0.56, 0.0)),
        )
        mbs["frame"].finish()
        tag(mbs["slats"].finish(), v10_item="rest_chair", v10_id=s["id"], v10_zone="rest")
    for s in r["loungers"]:
        mbs = {
            "frame": MB(
                f"Rest_lounger_{s['id']}_frame",
                surface_palette["wood_chair"],
                coll,
                bevel=0.004,
                segments=2,
            ),
            "slats": MB(
                f"Rest_lounger_{s['id']}_slats",
                surface_palette["wood_chair"],
                coll,
                bevel=0.004,
                segments=2,
            ),
        }
        furniture.slat_seat(mbs, s["foot"][0], s["foot"][1], tuple(s["heading"]))
        mbs["frame"].finish()
        tag(mbs["slats"].finish(), v10_item="rest_lounger", v10_id=s["id"], v10_zone="rest")

    # a 1.30 m board screen behind each row, a wing towards the aisle, a floor-facing strip under each screen
    panels = MB("Rest_screens", surface_palette["wood_mid"], coll, bevel=0.004, segments=2)
    plinth = MB("Rest_screen_plinths", surface_palette["black"], coll, bevel=0)
    hs = r["screen_h"]
    for i, (sx0, sy0, sx1, sy1) in enumerate(r["screens"]):
        furniture.board_panel(panels, (sx0, sy0, sx1, sy1), 0.05, hs)
        plinth.box(sx0 + 0.01, sy0 + 0.004, 0.0, sx1 - 0.01, sy0 + 0.014, 0.05)
        shell.strip_down(
            lights,
            fixture_materials["rest_toe"],
            f"LED_rest_toe_{i}",
            sx0 + 0.10,
            sy0 + 0.018,
            sx1 - 0.10,
            sy1 - 0.004,
            0.046,
        )
    for wx0, wy0, wx1, wy1 in r["wings"]:
        furniture.profile_panel(
            panels, (wx0, wy0, wx1, wy1), 0.05, eased(wy1 - wy0, hs, 0.30, 0.34), "start"
        )
        plinth.box(wx0 + 0.006, wy0 + 0.01, 0.0, wx1 - 0.006, wy1 - 0.07, 0.05)
    panels.finish()
    plinth.finish(weighted=False)

    # Built-in official rest for two in the bath hall, separate from the two spare perch places.
    b = r["builtin"]
    bx0, by0, bx1, by1 = b["rect"]
    bslat = MB("Rest_builtin_riser_slats", surface_palette["wood"], coll, bevel=0.002)
    mbs = bench_set("Rest_builtin", surface_palette, coll, bslat, back)
    furniture.bench_tier(
        Frame(bx0, by1, "+x", "-y"),
        bx1 - bx0,
        by1 - by0,
        b["top"],
        0.0,
        mbs,
        lights,
        fixture_materials["rest_plinth"],
        "rest_builtin",
        cheeks=(True, True),
    )
    furniture.backrest(Frame(bx0, by0, "+x", "+y"), bx1 - bx0, b["top"] + 0.22, mbs)
    for k in ("boards", "frame"):
        mbs[k].finish()
    bslat.finish()
    furniture.floor_drain(surface_palette, coll, "Rest_floor_drain", *r["drain"])
    slat.finish()
    back.finish(weighted=False)
    black.finish(weighted=False)


# ---------------------------------------------------------------------------------------------- dry service rooms
def locker_bank(surface_palette, coll, name, axis, fixed, sign, spec, item):
    """Carcass with one object per door, so the doors can be counted in the model."""
    a0, cols, cw, tiers, h, depth = (
        spec["a0"],
        spec["cols"],
        spec["col_w"],
        spec["tiers"],
        spec["h"],
        spec["depth"],
    )
    car = MB(f"{name}_carcass", surface_palette["black"], coll, bevel=0)
    shell.wall_box(car, axis, fixed, sign, 0.0, depth - 0.02, a0, a0 + cols * cw, 0.08, h + 0.08)
    shell.wall_box(car, axis, fixed, sign, 0.03, depth - 0.03, a0, a0 + cols * cw, 0.0, 0.08)
    car.finish(weighted=False)
    pulls = MB(f"{name}_pulls", surface_palette["stainless"], coll, bevel=0)
    n = 0
    for col in range(cols):
        for tier in range(tiers):
            n += 1
            z0 = 0.08 + tier * h / tiers
            door = MB(f"{name}_door_{n:02d}", surface_palette["locker"], coll, bevel=0.003)
            shell.wall_box(
                door,
                axis,
                fixed,
                sign,
                depth - 0.02,
                depth,
                a0 + col * cw + 0.002,
                a0 + (col + 1) * cw - 0.002,
                z0 + 0.002,
                z0 + h / tiers - 0.002,
                "z",
            )
            tag(door.finish(), v10_item=item, v10_zone=spec.get("zone", ""))
            zc = z0 + h / tiers / 2
            shell.wall_box(
                pulls,
                axis,
                fixed,
                sign,
                depth,
                depth + 0.012,
                a0 + (col + 1) * cw - 0.045,
                a0 + (col + 1) * cw - 0.03,
                zc - 0.05,
                zc + 0.05,
            )
    pulls.finish(weighted=False)


def build_service(c):
    """Reception, staff, linen, changing (30 lockers), washroom/WC, plant room with equipment bodies."""
    surface_palette, fixture_materials, plan = c.surface_palette, c.fixture_materials, c.plan
    coll = geo.collection("Service", c.root)
    lights = geo.collection("Service_lights", coll)
    trim = MB("CEIL_Service_downlight_trims", surface_palette["steel"], c.ceil, bevel=0)
    t = c.th / 2
    for zid in ("reception", "staff", "linen", "changing", "wc", "plantArm", "plantMain"):
        z = c.zones[zid]
        x, y, w, d = z["rect"]
        cb = MB(f"CEIL_Ceiling_{zid}", surface_palette["plaster"], c.ceil, bevel=0)
        cb.box(x + t, y + t, z["ceiling"], x + w - t, y + d - t, z["ceiling"] + 0.03)
        cb.finish(weighted=False)
        nx, ny = max(1, round(w / 2.2)), max(1, round(d / 2.2))
        for i in range(nx):
            for j in range(ny):
                shell.downlight(
                    trim,
                    lights,
                    fixture_materials["service_down"],
                    f"LED_{zid}_{i}{j}",
                    x + w * (i + 0.5) / nx,
                    y + d * (j + 0.5) / ny,
                    z["ceiling"],
                )
    trim.finish()
    wood = MB("Service_joinery", surface_palette["locker"], coll, bevel=0.003)
    stone = MB("Service_stone_tops", surface_palette["coping"], coll, bevel=0.004)
    mir = MB("Service_mirrors", surface_palette["mirror"], coll, bevel=0.001, segments=1)

    # reception: counter towards the staff door, shoe lockers on the west wall
    rc = plan["reception"]
    cx0, cy0, cx1, cy1 = rc["counter"]
    furniture.board_panel(wood, (cx0, cy0, cx1, cy0 + 0.03), 0.0, 1.0)
    wood.box(cx1 - 0.03, cy0 + 0.03, 0.0, cx1, cy1, 1.0, "z")
    stone.box(cx0, cy0 - 0.03, 1.0, cx1 + 0.03, cy1, 1.04)
    locker_bank(
        surface_palette,
        coll,
        "Reception_shoe_locker",
        "y",
        t,
        1,
        {**rc["shoe_lockers"], "zone": "reception"},
        "shoe_locker",
    )

    # staff desk and shelves; linen shelves in the nook
    sf = plan["staff"]
    dx0, dy0, dx1, dy1 = sf["desk"]
    wood.box(dx0, dy0, 0.70, dx1, dy1, 0.74)
    for xx in (dx0 + 0.02, dx1 - 0.06):
        wood.box(xx, dy0 + 0.02, 0.0, xx + 0.04, dy1 - 0.02, 0.70, "z")
    for rect in (sf["shelf"], sf["linen_shelf"]):
        rx0, ry0, rx1, ry1 = rect
        for k in range(4):
            wood.box(rx0, ry0, 0.30 + k * 0.45, rx1, ry1, 0.33 + k * 0.45)
        wood.box(rx0, ry0 - 0.02, 0.0, rx1, ry0 + 0.02, 1.75, "z")
        wood.box(rx0, ry1 - 0.02, 0.0, rx1, ry1 + 0.02, 1.75, "z")
    linen = MB("Service_linen_stacks", surface_palette["white"], coll, bevel=0.012, segments=3)
    lx0, ly0, lx1, _ly1 = sf["linen_shelf"]
    for k in range(3):
        for j in range(2):
            linen.box(
                lx0 + 0.04,
                ly0 + 0.05 + j * 0.32,
                0.33 + k * 0.45,
                lx1 - 0.03,
                ly0 + 0.31 + j * 0.32,
                0.33 + k * 0.45 + 0.16,
            )
    linen.finish()

    # changing: 30 lockers on the south wall, centre bench, vanity with two basins on the north wall
    ch = plan["changing"]
    _x0, y0, _x1, y1 = c.inner("changing")
    locker_bank(
        surface_palette,
        coll,
        "Change_locker",
        "x",
        y0,
        1,
        {**ch["lockers"], "zone": "changing"},
        "locker",
    )
    bx0, by0, bx1, by1 = ch["bench"]
    nb = max(2, round((by1 - by0) / 0.1))
    for k in range(nb):
        a, b = by0 + (by1 - by0) * k / nb + 0.004, by0 + (by1 - by0) * (k + 1) / nb - 0.004
        wood.box(bx0, a, 0.42, bx1, b, 0.45, "x")
    for xx in (bx0 + 0.12, (bx0 + bx1) / 2 - 0.025, bx1 - 0.17):
        wood.box(xx, by0 + 0.03, 0.0, xx + 0.05, by1 - 0.03, 0.42, "z")
        wood.box(xx - 0.02, by0 + 0.02, 0.37, xx + 0.07, by1 - 0.02, 0.42, "y")
    va = ch["vanity"]
    stone.box(va["x0"], y1 - va["depth"], 0.80, va["x1"], y1, 0.85)
    wood.box(va["x0"] + 0.03, y1 - va["depth"] + 0.06, 0.10, va["x1"] - 0.03, y1, 0.80, "x")
    for i, bx in enumerate(va["basins"]):
        ba = MB(f"Change_basin_{i + 1}", surface_palette["white"], coll, bevel=0.01, segments=3)
        ba.lathe(
            [(0.10, 0.0), (0.19, 0.11), (0.20, 0.12), (0.18, 0.12), (0.09, 0.02)],
            (bx, y1 - va["depth"] / 2, 0.85),
            seg=28,
            cap_top=False,
        )
        tag(ba.finish(), v10_item="basin", v10_zone="changing")
        mir.box(bx - 0.35, y1 - 0.012, 1.05, bx + 0.35, y1, 1.85)

    # washroom: two WC cubicles on the east side, one basin
    wc = plan["wc"]
    for i, (qx0, qy0, qx1, qy1) in enumerate(wc["cubicles"]):
        wood.box(qx0, qy1, 0.10, qx1, qy1 + 0.03, 2.0, "z")
        wood.box(qx0 - 0.03, qy0, 0.10, qx0, qy0 + 0.12, 2.0, "z")
        wood.box(qx0 - 0.03, qy1 - 0.10, 0.10, qx0, qy1 + 0.03, 2.0, "z")
        leaf = MB(f"WC_door_{i + 1}", surface_palette["wood_dark"], coll, bevel=0.003)
        leaf.box(qx0 - 0.03, qy0 + 0.125, 0.12, qx0 - 0.005, qy1 - 0.105, 1.98, "z")
        leaf.finish()
        wt = MB(f"WC_toilet_{i + 1}", surface_palette["white"], coll, bevel=0.01, segments=3)
        wt.lathe(
            [(0.17, 0.0), (0.19, 0.36), (0.20, 0.40), (0.0, 0.40)],
            (qx1 - 0.48, (qy0 + qy1) / 2, 0.0),
            seg=24,
            cap_top=False,
        )
        wt.box(qx1 - 0.20, (qy0 + qy1) / 2 - 0.20, 0.38, qx1 - 0.02, (qy0 + qy1) / 2 + 0.20, 0.78)
        tag(wt.finish(), v10_item="wc", v10_zone="wc")
    wx, wyy = wc["basin"]
    y_n = c.zones["wc"]["rect"][1] + c.zones["wc"]["rect"][3] - t
    stone.box(wx - 0.45, y_n - 0.44, 0.80, wx + 0.45, y_n, 0.85)
    ba = MB("WC_basin_1", surface_palette["white"], coll, bevel=0.01, segments=3)
    ba.lathe(
        [(0.10, 0.0), (0.19, 0.11), (0.20, 0.12), (0.18, 0.12), (0.09, 0.02)],
        (wx, wyy, 0.85),
        seg=28,
        cap_top=False,
    )
    tag(ba.finish(), v10_item="basin", v10_zone="wc")
    mir.box(wx - 0.35, y_n - 0.012, 1.05, wx + 0.35, y_n, 1.85)

    # plant: equipment bodies (provisional outer sizes), overhead pipe runs
    pipes = MB("Plant_pipes", surface_palette["steel"], coll, bevel=0)
    for e in plan["plant"]["equipment"]:
        mb = MB(f"Plant_{e['id']}", surface_palette["steel"], coll, bevel=0.006)
        if e["kind"] == "box":
            ex0, ey0, ex1, ey1 = e["rect"]
            mb.box(ex0, ey0, e["z"][0], ex1, ey1, e["z"][1])
            if e["z"][0] < 0.01:
                mb.box(ex0 + 0.03, ey0 + 0.03, 0.0, ex1 - 0.03, ey1 - 0.03, 0.05)
            top = (ex0 + ex1) / 2, (ey0 + ey1) / 2, e["z"][1]
        else:
            (ex, ey), rr, hh = e["c"], e["r"], e["h"]
            mb.lathe(
                [(rr - 0.02, 0.0), (rr, 0.05), (rr, hh - 0.18), (rr * 0.72, hh - 0.03), (0.0, hh)],
                (ex, ey, 0.0),
                seg=32,
                cap_top=False,
            )
            top = ex, ey, hh
        tag(
            mb.finish(),
            v10_item="equipment",
            v10_id=e["id"],
            v10_label=e["label"],
            v10_zone="plant",
            v10_status="provisional outer size; capacity, count and maker not selected",
        )
        if e["id"] in (
            "chiller",
            "cold_filter",
            "carbon_filter",
            "carbon_unit",
            "hot_tank_1",
            "hot_tank_2",
        ):
            pipes.tube(
                geo.fillet([top, (top[0], top[1], 2.30), (top[0], 1.85, 2.30)], 0.08, 5),
                0.03,
                seg=12,
            )
    for k, yy in enumerate((1.75, 1.85, 1.95)):
        pipes.tube([(12.95, yy, 2.30 + 0.09 * k), (16.6, yy, 2.30 + 0.09 * k)], 0.035, seg=12)
    pipes.finish(weighted=False)
    for mb in (wood, stone, mir):
        mb.finish()


# ---------------------------------------------------------------------------------------------- check bodies
BODY = {"shoulder": 0.50, "torso_d": 0.26, "sit_h": 0.90, "stature": 1.72}


def _box(x, y, facing, d0, d1, hw, z0, z1):
    fx, fy = DIR[facing]
    lx, ly = -fy, fx
    xs = [x + fx * d + lx * s for d in (d0, d1) for s in (-hw, hw)]
    ys = [y + fy * d + ly * s for d in (d0, d1) for s in (-hw, hw)]
    return min(xs), min(ys), z0, max(xs), max(ys), z1


def seated_boxes(x, y, facing, seat_z, foot_z):
    """Seated adult from the back plane (x, y): torso, head, thighs, shins, feet (provisional body sizes of V6/V8)."""
    return [
        _box(x, y, facing, 0.0, 0.26, 0.25, seat_z + 0.02, seat_z + 0.60),
        _box(x, y, facing, 0.03, 0.23, 0.09, seat_z + 0.62, seat_z + 0.90),
        _box(x, y, facing, 0.20, 0.60, 0.20, seat_z + 0.005, seat_z + 0.15),
        _box(x, y, facing, 0.57, 0.69, 0.18, foot_z + 0.08, seat_z + 0.005),
        _box(x, y, facing, 0.50, 0.77, 0.18, foot_z + 0.002, foot_z + 0.08),
    ]


def floor_sit_boxes(x, y, facing, z):
    """Sitting on the pool floor with the back on the pool wall, legs out."""
    return [
        _box(x, y, facing, 0.0, 0.26, 0.25, z + 0.002, z + 0.60),
        _box(x, y, facing, 0.03, 0.23, 0.09, z + 0.62, z + 0.88),
        _box(x, y, facing, 0.20, 0.90, 0.20, z + 0.002, z + 0.16),
    ]


def standing_boxes(x, y, facing):
    return [
        _box(x, y, facing, -0.14, 0.14, 0.25, 0.002, 1.50),
        _box(x, y, facing, -0.10, 0.10, 0.09, 1.50, BODY["stature"]),
    ]


def reclined_boxes(fx, fy, heading):
    """On a lounger: s runs from the foot end along the heading (foot -> head)."""
    out = []
    for s0, s1, hw, z0, z1 in (
        (0.10, 0.95, 0.20, 0.36, 0.56),
        (0.90, 1.25, 0.22, 0.34, 0.60),
        (1.20, 1.42, 0.25, 0.50, 0.74),
        (1.40, 1.62, 0.25, 0.66, 0.92),
        (1.60, 1.78, 0.09, 0.86, 1.10),
    ):
        hx, hy = heading
        xs = [fx + hx * s + hy * lateral_offset for s in (s0, s1) for lateral_offset in (-hw, hw)]
        ys = [fy + hy * s - hx * lateral_offset for s in (s0, s1) for lateral_offset in (-hw, hw)]
        out.append((min(xs), min(ys), z0, max(xs), max(ys), z1))
    return out


def build_check(c):
    """Assumed adult bodies at every counted position. Render-hidden; in the .glb their names start with CHECK_."""
    plan = c.plan
    c.check.hide_render = True
    seated = materials.flat("check_body", (0.62, 0.50, 0.40), 0.85)
    upright = materials.flat("check_body_standing", (0.36, 0.46, 0.56), 0.85)

    def put(name, boxes, mat, role, support=None, seat_z=None, zone=""):
        mb = MB(f"CHECK_body_{name}", mat, c.check, bevel=0.012, segments=2)
        for b in boxes:
            mb.box(*b)
        ob = tag(mb.finish(), v10_role=role, v10_zone=zone)
        if support is not None:
            ob["v10_support"] = [float(support[0]), float(support[1])]
            ob["v10_seat_z"] = float(seat_z)

    def seats(lst, zone, role):
        for s in lst:
            fx, fy = DIR[s["facing"]]
            put(
                f"{zone}_{s['id']}",
                seated_boxes(s["x"], s["y"], s["facing"], s["seat_z"], s["foot_z"]),
                seated,
                role,
                (s["x"] + fx * 0.25, s["y"] + fy * 0.25),
                s["seat_z"],
                zone,
            )

    seats(plan["main"]["seats"], "main", "main_seat")
    seats(plan["self"]["seats"], "self", "self_seat")
    seats(
        plan["rest"]["builtin"]["seats"],
        plan["rest"]["builtin"].get("zone", "rest"),
        "rest_builtin",
    )
    seats(plan["hall"]["perch"]["seats"], "bathHall", "perch")
    for s in plan["rest"]["chairs"]:
        (fx, fy), (hx, hy) = s["foot"], s["heading"]
        facing = {(0, -1): "N", (0, 1): "S", (1, 0): "W", (-1, 0): "E"}[(hx, hy)]
        bx, by = fx + hx * 0.60, fy + hy * 0.60
        put(
            f"rest_{s['id']}",
            seated_boxes(bx, by, facing, 0.40, 0.0),
            seated,
            "rest_chair",
            (fx + hx * 0.35, fy + hy * 0.35),
            0.40,
            "rest",
        )
    for s in plan["rest"]["loungers"]:
        (fx, fy), (hx, hy) = s["foot"], s["heading"]
        put(
            f"rest_{s['id']}",
            reclined_boxes(fx, fy, (hx, hy)),
            seated,
            "rest_lounger",
            (fx + hx * 0.90, fy + hy * 0.90),
            0.33,
            "rest",
        )
    drop = plan["assumptions"]["water_drop"]
    for p in plan["pools"]:
        zf = -drop - p["depth"]
        for s in p["positions"]:
            put(
                f"pool_{p['id']}_{s['id']}",
                floor_sit_boxes(s["x"], s["y"], s["facing"], zf),
                seated,
                f"pool_{p['id']}",
                zone="pools",
            )
    for s in plan["hall"]["waiting_standing"]:
        put(
            f"bathHall_{s['id']}",
            standing_boxes(s["x"], s["y"], s["facing"]),
            upright,
            "waiting",
            zone="bathHall",
        )
    px, py = plan["main"]["performer"]["centre"]
    put("main_performer", standing_boxes(px, py, "N"), upright, "performer", zone="main")
    wy = c.zones["wash"]["rect"][1] + c.th / 2 + TS
    for i, x in enumerate(plan["wash"]["showers"]):
        put(
            f"wash_shower_{i + 1}",
            standing_boxes(x, wy + 0.78, "S"),
            upright,
            "showering",
            zone="wash",
        )


# ---------------------------------------------------------------------------------------------- study overlay
STUDY_COLORS = {
    "slab": ((1.00, 0.42, 0.08), 0.60),
    "support": ((1.00, 0.20, 0.80), 1.0),
    "support_fill": ((1.00, 0.20, 0.80), 0.22),
    "beam": ((1.00, 0.12, 0.08), 1.0),
    "band": ((1.00, 0.78, 0.08), 1.0),
    "fl": ((0.90, 0.90, 0.90), 1.0),
    "water": ((0.10, 0.80, 1.00), 1.0),
    "route": ((0.35, 1.00, 0.30), 1.0),
    "wait": ((1.00, 0.60, 0.00), 1.0),
    "perform": ((0.30, 0.60, 1.00), 1.0),
    "zone": ((0.70, 0.70, 0.70), 1.0),
    "text": ((1.0, 1.0, 1.0), 1.0),
    "backing": ((0.0, 0.0, 0.0), 0.78),
}
EMIT_BASE = 0.8


def study_mat(key):
    rgbv, alpha = STUDY_COLORS[key]
    t = materials.NT("STUDY_mat_" + key)
    em = t.node("ShaderNodeEmission")
    em.name = "STUDY_EMIT"
    strength = 0.0 if key == "backing" else EMIT_BASE
    em.inputs["Color"].default_value = (*rgbv, 1.0)
    em.inputs["Strength"].default_value = strength
    if alpha < 1.0:
        tr = t.node("ShaderNodeBsdfTransparent")
        mix = t.node("ShaderNodeMixShader")
        mix.inputs[0].default_value = alpha
        t.link(tr.outputs[0], mix.inputs[1])
        t.link(em.outputs[0], mix.inputs[2])
        t.link(mix.outputs[0], t.out.inputs["Surface"])
    else:
        t.link(em.outputs[0], t.out.inputs["Surface"])
    t.mat["v10_emit_base"] = strength
    materials._glb(t.mat, rgbv, 0.9, 0.0, emit=1.0 if strength > 0 else 0.0, alpha=alpha)
    try:
        t.mat.cycles.emission_sampling = "NONE"  # drawing only, never a light source
    except Exception:
        pass
    return t.mat


def camera_only(ob):
    for attr in (
        "visible_diffuse",
        "visible_glossy",
        "visible_transmission",
        "visible_volume_scatter",
        "visible_shadow",
    ):
        try:
            setattr(ob, attr, False)
        except Exception:
            pass


class Study:
    def __init__(self, c):
        self.c = c
        self.mat = {k: study_mat(k) for k in STUDY_COLORS}
        self.mbs = {}
        self.warnings = []
        self.n = 0

    def mb(self, name, key):
        k = (name, key)
        if k not in self.mbs:
            self.mbs[k] = MB(f"STUDY_{name}", self.mat[key], self.c.study, bevel=0, smooth=False)
        return self.mbs[k]

    def frame(self, name, key, rect, z, t=0.03):
        x0, y0, x1, y1 = rect
        m = self.mb(name, key)
        m.box(x0 - t / 2, y0 - t / 2, z, x1 + t / 2, y0 + t / 2, z + t)
        m.box(x0 - t / 2, y1 - t / 2, z, x1 + t / 2, y1 + t / 2, z + t)
        m.box(x0 - t / 2, y0, z, x0 + t / 2, y1, z + t)
        m.box(x1 - t / 2, y0, z, x1 + t / 2, y1, z + t)

    def ring(self, name, key, cx, cy, r, z=0.02, w=0.025):
        self.mb(name, key).lathe(
            [(r - w, 0.0), (r - w, 0.008), (r, 0.008), (r, 0.0)],
            (cx, cy, z),
            seg=72,
            cap_top=False,
            cap_bottom=False,
        )

    def route(self, name, key, pts, z=0.02, w=0.05, dash=0.22, gap=0.14):
        m = self.mb(name, key)
        for (xa, ya), (xb, yb) in itertools.pairwise(pts):
            span_length = math.hypot(xb - xa, yb - ya)
            if span_length < 1e-6:
                continue
            ang = math.atan2(yb - ya, xb - xa)
            s = 0.0
            while s < span_length - 1e-6:
                e = min(s + dash, span_length)
                mid = (
                    xa + (xb - xa) * (s + e) / 2 / span_length,
                    ya + (yb - ya) * (s + e) / 2 / span_length,
                    z + 0.004,
                )
                m.box_m(
                    (e - s, w, 0.008),
                    Matrix.Translation(mid) @ Matrix.Rotation(ang, 4, "Z"),
                    grain=0,
                )
                s += dash + gap

    def label(self, text, loc, size, plane="XY", ax="CENTER", ay="CENTER"):
        """ASCII label turned into a mesh (no font file). XY lies flat, XZ stands in a section plane read from the south."""
        self.n += 1
        name = f"STUDY_txt_{self.n:03d}"
        try:
            cu = bpy.data.curves.new(name, "FONT")
            cu.body, cu.size, cu.align_x, cu.align_y = text, size, ax, ay
            tmp = bpy.data.objects.new(name + "_f", cu)
            tmp.location = loc
            if plane == "XZ":
                tmp.rotation_euler = (math.pi / 2, 0.0, 0.0)
            self.c.study.objects.link(tmp)
            bpy.context.view_layer.update()
            me = bpy.data.meshes.new_from_object(
                tmp.evaluated_get(bpy.context.evaluated_depsgraph_get())
            )
            me.name = name
            me.materials.clear()
            me.materials.append(self.mat["text"])
            ob = bpy.data.objects.new(name, me)
            ob.location, ob.rotation_euler = tmp.location, tmp.rotation_euler
            ob["v10_text"] = text
            self.c.study.objects.link(ob)
            bpy.data.objects.remove(tmp)
            bpy.data.curves.remove(cu)
            lines = text.split("\n")
            w, h, pad = (
                max(len(s) for s in lines) * size * 0.62,
                len(lines) * size * 1.25,
                0.3 * size,
            )
            x0 = {"LEFT": loc[0], "RIGHT": loc[0] - w, "CENTER": loc[0] - w / 2}[ax] - pad
            v = loc[1] if plane == "XY" else loc[2]
            v0 = {"TOP": v - h, "BOTTOM": v, "CENTER": v - h / 2}[ay] - pad
            bk = self.mb("label_backing", "backing")
            if plane == "XY":
                bk.box(x0, v0, loc[2] - 0.006, x0 + w + 2 * pad, v0 + h + 2 * pad, loc[2] - 0.003)
            else:
                bk.box(x0, loc[1] + 0.0008, v0, x0 + w + 2 * pad, loc[1] + 0.0016, v0 + h + 2 * pad)
        except Exception as e:
            self.warnings.append(f"label '{text}' not built: {e}")

    def finish(self):
        for m in self.mbs.values():
            ob = m.finish(weighted=False)
            if ob is not None:
                camera_only(ob)
        for ob in self.c.study.objects:
            camera_only(ob)


def build_study(c):
    """Provisional conditions and flows as a separate, render-hidden layer: assumed slab with openings, pool assemblies down to
    the support underside, levels, the performer circle, waiting places and return routes, zone outlines and numbers."""
    plan, a = c.plan, c.plan["assumptions"]
    c.study.hide_render = True
    study_layer = Study(c)
    plan_width, plan_depth = plan["width"], plan["height"]
    slab, beam, band_u = a["slab_top"], a["beam_soffit"], a["beam_soffit"] - a["service_band"]
    side, st = a["envelope_side_display"], a["slab_display_thickness"]
    envs = []
    for p in plan["pools"]:
        x, y, w, d = p["rect"]
        bottom = a["fl"] - a["water_drop"] - p["depth"]
        under = bottom - a["envelope_below"]
        env = (x - side, y - side, x + w + side, min(y + d + side, plan_depth))
        envs.append(env)
        study_layer.mb(f"pool_{p['id']}_envelope", "support_fill").box(
            env[0], env[1], under, env[2], env[3], slab
        )
        study_layer.frame(f"pool_{p['id']}_underside", "support", env, under, 0.02)
        study_layer.frame(f"pool_{p['id']}_bottom", "water", (x, y, x + w, y + d), bottom, 0.02)
        study_layer.frame(f"pool_{p['id']}_plan_mark", "support", env, 0.02, 0.025)
    plate = study_layer.mb("slab_top_plate", "slab")
    xs = sorted({0.0, plan_width} | {min(max(e[k], 0.0), plan_width) for e in envs for k in (0, 2)})
    ys = sorted({0.0, plan_depth} | {min(max(e[k], 0.0), plan_depth) for e in envs for k in (1, 3)})
    for xa, xb in itertools.pairwise(xs):
        for ya, yb in itertools.pairwise(ys):
            cx, cy = (xa + xb) / 2, (ya + yb) / 2
            if not any(e[0] < cx < e[2] and e[1] < cy < e[3] for e in envs):
                plate.box(xa, ya, slab - st, xb, yb, slab)
    ring = (-0.06, -0.06, plan_width + 0.06, plan_depth + 0.06)
    study_layer.frame("level_beam_soffit", "beam", ring, beam, 0.04)
    study_layer.frame("level_band_underside", "band", ring, band_u, 0.04)
    study_layer.frame("level_slab_top", "slab", ring, slab - 0.04, 0.04)

    # section graphics in the plane y = section_y (read from the south with a clipped camera)
    yc = plan["study"]["section_y"]
    yt, yl = yc + 0.0004, yc + 0.003
    deep = max(plan["pools"], key=lambda p: p["depth"])
    under = a["fl"] - a["water_drop"] - deep["depth"] - a["envelope_below"]
    levels = [
        ("fl", a["fl"], "FL 0.00", 1),
        ("slab", slab, f"SLAB TOP {slab:+.2f} *", -1),
        ("beam", beam, f"BEAM SOFFIT {beam:+.2f} *", 1),
        ("band", band_u, f"BAND U/S {band_u:+.2f} *", -1),
        (
            "support",
            under,
            f"COLD SUPPORT U/S {under:+.2f} * ({slab - under:.2f} below slab top)",
            -1,
        ),
    ]
    for key, z, text, sgn in levels:
        m = study_layer.mb(f"section_level_{key}", key if key in STUDY_COLORS else "fl")
        s = -0.4
        while s < plan_width + 0.4:
            m.box(s, yl, z - 0.006, min(s + 0.30, plan_width + 0.4), yl + 0.001, z + 0.006)
            s += 0.48
        study_layer.label(
            text,
            (-0.25, yt, z + sgn * 0.04),
            0.20,
            plane="XZ",
            ax="RIGHT",
            ay="BOTTOM" if sgn > 0 else "TOP",
        )
    for p in plan["pools"]:
        x, y, w, d = p["rect"]
        bottom = a["fl"] - a["water_drop"] - p["depth"]
        study_layer.label(
            f"{p['id'].upper()} water {a['fl'] - a['water_drop']:+.2f} bottom {bottom:+.2f} u/s {bottom - a['envelope_below']:+.2f} *",
            (x + w / 2, yt, bottom - a["envelope_below"] - 0.08),
            0.10,
            plane="XZ",
            ay="TOP",
        )
    study_layer.label(
        "V10 compact study  section looking north  * = assumed; property, structure, equipment, code: NOT confirmed",
        (0.0, yt, 3.45),
        0.20,
        plane="XZ",
        ax="LEFT",
        ay="BOTTOM",
    )

    # main sauna: performer circle (reference R1.30), standing disc, entry lane
    pf = plan["main"]["performer"]
    study_layer.ring(
        "main_performer_towel_R130",
        "perform",
        pf["centre"][0],
        pf["centre"][1],
        pf["towel_radius_ref"],
    )
    study_layer.ring(
        "main_performer_stand", "perform", pf["centre"][0], pf["centre"][1], pf["stand_radius"]
    )
    lanes = {p["id"]: p["line"] for p in plan["passages"]}
    study_layer.route("main_entry_lane", "route", lanes["main_entry_lane"])
    # bath hall: waiting places outside the lane, way back when the rest room is full
    for s in plan["hall"]["waiting_standing"]:
        study_layer.ring("hall_waiting_places", "wait", s["x"], s["y"], 0.30)
    for s in plan["hall"]["perch"]["seats"]:
        study_layer.ring("hall_waiting_places", "wait", s["x"], s["y"] + 0.30, 0.26)
    study_layer.route("hall_return_when_rest_full", "wait", plan["hall"]["return_route"])
    study_layer.route("hall_to_wash", "route", plan["hall"]["wash_route"])
    study_layer.route(
        "guest_route",
        "route",
        lanes["entry_to_changing"]
        + lanes["locker_front"]
        + lanes["changing_to_lobby"][1:]
        + lanes["lobby_to_hall"][1:],
    )
    study_layer.route("staff_route", "wait", lanes["staff_to_changing"])
    study_layer.route("plant_service", "wait", lanes["plant_arm"] + lanes["plant_aisle"][1:])
    for p in plan["pools"]:
        study_layer.frame(
            f"pool_{p['id']}_landing_keep_clear",
            "wait",
            tuple(p["landing"]),
            a["fl"] - a["water_drop"] + 0.01,
            0.02,
        )
    # zone outlines and numbers above the walls (top view with the ceilings hidden)
    for z in plan["zones"]:
        x, y, w, d = z["rect"]
        study_layer.frame("zone_outlines", "zone", (x, y, x + w, y + d), 3.02, 0.02)
        study_layer.label(f"{z['no']}", (x + w / 2, y + d / 2, 3.06), 0.34)
    study_layer.label(
        "EXT. ACCESS / HEAT REJECTION: TBD", (plan_width + 0.3, 1.75, 0.05), 0.20, ax="LEFT"
    )
    study_layer.finish()
    return study_layer.warnings


# ---------------------------------------------------------------------------------------------- cameras, doors, all
def build_cameras(c):
    plan = c.plan
    cams = geo.collection("Cameras", c.root)
    yc = plan["study"]["section_y"]
    for k in plan["cameras"]:
        name = "Cam_" + k["name"]
        if k["kind"] == "interior":
            ob = sc.add_camera(
                name,
                tuple(k["loc"]),
                tuple(k["target"]),
                lens=k["lens"],
                shift_y=k.get("shift_y", 0.0),
                coll=cams,
            )
        elif k["kind"] == "overview":
            ob = sc.add_overview_camera(
                name, tuple(k["loc"]), tuple(k["target"]), lens=k["lens"], coll=cams
            )
        elif k["kind"] == "top":
            x, y, z = k["loc"]
            ob = sc.add_overview_camera(name, (x, y, z), (x, y, 0.0), ortho=k["ortho"], coll=cams)
        else:  # section: orthographic, looking north, clipped at the section plane
            cam = bpy.data.cameras.new(name)
            cam.type, cam.ortho_scale, cam.sensor_width = "ORTHO", k["ortho"], 36.0
            cam.clip_start, cam.clip_end = 12.0 + yc, 60.0
            ob = bpy.data.objects.new(name, cam)
            ob.location = (k["x"], -12.0, k["z"])
            ob.rotation_euler = (math.pi / 2, 0.0, 0.0)
            cams.objects.link(ob)
            ob["v10_section_y"] = yc
        ob["exposure"] = k["exposure"]
        ob["v10_hide"] = ",".join(k.get("hide", []))
        ob["v10_show"] = ",".join(k.get("show", []))
        ob["v10_ambient"] = float(k.get("ambient", 0.0))
        ob["v10_aspect"] = float(k.get("aspect", 1.5))
        ob["v10_kind"] = k["kind"]


def build_all(plan, surface_palette, fixture_materials, root):
    c = Ctx(plan, surface_palette, fixture_materials, root)
    build_structure(c)
    build_main(c)
    build_self(c)
    build_bath(c)
    build_rest(c)
    build_service(c)
    doors = geo.collection("Doors", root)
    for d in plan["doors"]:
        shell.door(plan, d, surface_palette, doors)
    build_check(c)  # after all rooms, so the bodies cannot shift the board / stone variation
    warnings = build_study(c)
    build_cameras(c)
    for col, prefix in ((c.ceil, "CEIL_"), (c.check, "CHECK_"), (c.study, "STUDY_")):
        for ob in col.objects:
            if not ob.name.startswith(prefix):
                ob.name = prefix + ob.name
    return warnings
