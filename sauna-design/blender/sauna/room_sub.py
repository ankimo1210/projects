"""v8 small saunas as real mesh: the self-loyly room and the dry room with the TV (data: sub_layout.py).

Self-loyly: one row of seats climbing round the room in three heights (0.45 west, 0.675 north-west, 0.90 north-east), each
with a foot level 0.45 m below, and the north-west corner lined on a 0.90 m plan radius. Dry room: a high bench for two
and, north of a low timber wing, a 1.50 m deep deck for two with a raked back where the legs lie out towards the TV.
Heater position, guard, door, TV recess and light strengths are as v7. Heater type and clearances, how heat and steam
move, ventilation, structure and code compliance are not verified.
"""

import math

from mathutils import Matrix

from . import furniture, geo, materials, shell
from . import main_layout as ML
from . import sub_layout as SL
from . import water_layout as WL
from .furniture import Frame
from .geo import MB
from .shell import SLOT_H, SLOT_W, T_BACK, T_SLAT

Y0S, Y1S = 10.58, 13.92  # structural south / north faces of both rooms


def _eased(length, h, ea, eb):
    return [(0.0, h), (length - ea, h)] + [
        (
            length - ea + ea * math.sin(math.pi / 2 * k / 14),
            h - eb + eb * math.cos(math.pi / 2 * k / 14),
        )
        for k in range(1, 15)
    ]


def build_self(plan, P, LM, coll):
    from .room_other import bucket

    s, D = SL.SELF, SL.self_dims()
    rid, x0, x1, H = "Self", 6.08, 9.42, SL.H
    f = T_BACK + T_SLAT
    xw, xe, ys, yn = x0 + f, x1 - f, Y0S + f, Y1S - f
    assert max(abs(xw - s["xw"]), abs(xe - s["xe"]), abs(ys - SL.Y0), abs(yn - SL.Y1)) < 1e-6, (
        "sub_layout.py and the wall lining disagree"
    )
    lights = geo.collection(f"{rid}_lights", coll)
    ceil = geo.collection("Ceilings", coll)
    slat = MB(f"{rid}_wall_slats", P["wood"], coll, bevel=0.002)
    back = MB(f"{rid}_backing", P["wood_back"], coll, bevel=0)
    black = MB(f"{rid}_cove_black", P["black"], ceil, bevel=0)
    shell.slat_wall(slat, back, "x", Y1S, -1, x0, x1, 0, H + SLOT_H)
    shell.slat_wall(
        slat,
        back,
        "x",
        Y0S,
        1,
        x0,
        x1,
        0,
        H + 0.03,
        openings=[(s["door"][0], s["door"][1], 0, plan["doorHeight"])],
    )
    shell.slat_wall(slat, back, "y", x0, 1, ys, yn, 0, H + 0.03)
    shell.slat_wall(slat, back, "y", x1, -1, ys, yn, 0, H + 0.03)
    # rounded lining of the north-west corner: the same vertical slats set out on a quarter circle (the space behind is closed)
    R = s["corner_r"]
    cx, cy = xw + R, yn - R
    n = max(1, int((math.pi / 2 * R + 0.008) / 0.05))
    zc = (H + SLOT_H) / 2
    for k in range(n):
        a = math.pi - (k + 0.5) * (math.pi / 2) / n
        rot = Matrix.Rotation(a + math.pi / 2, 4, "Z")
        rs, rb = R + T_SLAT / 2, R + T_SLAT + T_BACK / 2
        slat.box_m(
            (0.042, T_SLAT, H + SLOT_H),
            Matrix.Translation((cx + rs * math.cos(a), cy + rs * math.sin(a), zc)) @ rot,
            grain=2,
        )
        back.box_m(
            (math.pi / 2 * (rb + T_BACK) / n + 0.004, T_BACK, H + SLOT_H),
            Matrix.Translation((cx + rb * math.cos(a), cy + rb * math.sin(a), zc)) @ rot,
            grain=2,
        )
    # ceiling: dark slats east-west as v7; over the rounded corner they stop on the same radius, so the light reveal of the
    # north wall carries on round the curve (same strip, same strength, 0.14 m slot)
    cs = MB(f"{rid}_ceiling_slats", P["wood_dark"], ceil, bevel=0.002)
    sw, sg, st = 0.07, 0.022, 0.018
    rows = max(1, int((yn - SLOT_W - ys + sg) / (sw + sg)))
    pitch = (yn - SLOT_W - ys) / rows
    ri = R - SLOT_W
    for i in range(rows):
        c = ys + (i + 0.5) * pitch
        dy = c + pitch / 2 - cy
        xa = xw if dy <= 0 else cx - math.sqrt(max(0.0, (ri - 0.018) ** 2 - dy * dy))
        cs.box(xa, c - sw / 2, H, xe, c + sw / 2, H + st, grain="x")
        black.box(xa, c - pitch / 2, H + st + 0.012, xe, c + pitch / 2, H + st + 0.03)
    cs.finish()
    shell.cove(lights, black, LM["sauna_cove"], "x", yn, -1, cx, xe, H, f"LED_{rid}_cove")
    black.box(xw, cy, H + SLOT_H, cx, yn, H + SLOT_H + 0.02)  # lid of the curved reveal
    na = 18
    verts, faces = [], []
    for k in range(na + 1):
        a = math.pi - k * (math.pi / 2) / na
        for rr in (R - 0.10, R - 0.05):
            verts.append((cx + rr * math.cos(a), cy + rr * math.sin(a), H + SLOT_H - 0.012))
        if k:
            faces.append((2 * k - 2, 2 * k - 1, 2 * k + 1, 2 * k))
            am = a + (math.pi / 4) / na
            black.box_m(
                (math.pi / 2 * ri / na + 0.004, 0.018, SLOT_H + 0.02),
                Matrix.Translation(
                    (
                        cx + (ri - 0.009) * math.cos(am),
                        cy + (ri - 0.009) * math.sin(am),
                        H + (SLOT_H + 0.02) / 2,
                    )
                )
                @ Matrix.Rotation(am + math.pi / 2, 4, "Z"),
            )
    import bpy

    me = bpy.data.meshes.new(f"LED_{rid}_cove_arc")
    me.from_pydata(verts, [], faces)
    me.materials.append(LM["sauna_cove"])
    me.update()
    if me.polygons[0].normal.z > 0:
        me.flip_normals()
    lights.objects.link(bpy.data.objects.new(f"LED_{rid}_cove_arc", me))

    mbs = {
        "boards": MB(f"{rid}_bench_boards", P["wood_bench"], coll, bevel=0.005, segments=3),
        "frame": MB(f"{rid}_bench_frame", P["wood_bench"], coll, bevel=0.003),
        "slat": slat,
        "back": back,
    }
    LB = LM["sauna_bench"]
    lo, mid, hi = s["levels"]
    xf, y_n, y_l, y_s, xs = (
        D["w_front"],
        D["n_front"],
        D["ledge_front"],
        D["step_front"],
        s["n_split"],
    )
    Lw, La, Lb = s["w_top"] - s["w_end"], xs - xf, xe - xs
    d_seat = SL.SEAT_D
    # west run, 0.45: sat on straight from the floor; free south end rounded
    furniture.bench_tier(
        Frame(xf, s["w_end"], "+y", "-x"),
        Lw,
        d_seat,
        lo,
        0.0,
        mbs,
        lights,
        LB,
        "self_w",
        riser_v=0.32,
        legs=[0.105, Lw - 0.06],
        cheeks=(True, False),
        round_ends=(0.10, 0.0),
    )
    # corner platform, 0.675: turns the row from the west wall to the north wall under the rounded lining (not counted as a seat)
    furniture.bench_tier(
        Frame(xf, s["w_top"], "+y", "-x"),
        yn - s["w_top"],
        d_seat,
        mid,
        0.0,
        mbs,
        lights,
        LB,
        "self_corner",
        riser_v=0.10,
        legs=[0.06],
        cheeks=(True, False),
        led=False,
    )
    # north run: 0.675 west of the split, 0.90 east of it
    furniture.bench_tier(
        Frame(xf, y_n, "+x", "+y"),
        La,
        d_seat,
        mid,
        mid - 0.45,
        mbs,
        lights,
        LB,
        "self_n_mid",
        riser_v=0.10,
        legs=[0.06, La - 0.06],
    )
    furniture.bench_tier(
        Frame(xs, y_n, "+x", "+y"),
        Lb,
        d_seat,
        hi,
        hi - 0.45,
        mbs,
        lights,
        LB,
        "self_n_high",
        riser_v=0.10,
        legs=[0.06, Lb - 0.06],
        cheeks=(True, False),
    )
    # foot levels 0.45 m below each seat, and the half step in front of the higher one
    furniture.bench_tier(
        Frame(xf, y_l, "+x", "+y"),
        La,
        s["ledge_d"],
        mid - 0.45,
        0.0,
        mbs,
        lights,
        LB,
        "self_foot_mid",
        riser_v=None,
        legs=[0.06, La / 2, La - 0.06],
        led_w=0.012,
    )
    furniture.bench_tier(
        Frame(xs, y_l, "+x", "+y"),
        Lb,
        s["ledge_d"],
        hi - 0.45,
        0.0,
        mbs,
        lights,
        LB,
        "self_foot_high",
        riser_v=0.10,
        legs=[0.06, Lb - 0.06],
        cheeks=(True, False),
        led_w=0.012,
    )
    furniture.bench_tier(
        Frame(xs, y_s, "+x", "+y"),
        Lb,
        s["step_d"],
        0.225,
        0.0,
        mbs,
        lights,
        LB,
        "self_step",
        riser_v=None,
        legs=[0.105, Lb / 2, Lb - 0.06],
        cheeks=(True, False),
        round_ends=(0.10, 0.0),
        led_w=0.012,
    )
    furniture.backrest(Frame(cx + 0.02, yn, "+x", "-y"), xs - cx - 0.03, mid + 0.25, mbs)
    furniture.backrest(Frame(xs + 0.01, yn, "+x", "-y"), Lb - 0.02, hi + 0.25, mbs)
    furniture.backrest(Frame(xw, s["w_end"] + 0.03, "+y", "+x"), Lw - 0.06, lo + 0.25, mbs)
    for mb in (mbs["boards"], mbs["frame"]):
        mb.finish()
    slat.finish()
    back.finish(weighted=False)
    hx, hy = s["heater"]["c"]
    furniture.heater(
        P,
        coll,
        f"{rid}_heater",
        hx,
        hy,
        r=s["heater"]["r"],
        h=0.85,
        guard_r=s["heater"]["guard_r"],
        guard_h=0.78,
    )
    trim = MB(f"{rid}_downlight_trims", P["steel"], ceil, bevel=0)
    shell.downlight(trim, lights, LM["sauna_heater"], f"LED_{rid}_heater", hx, hy + 0.25, H, r=0.03)
    trim.finish()
    black.finish(weighted=False)
    bucket(P, coll, "Self_loyly_bucket", *s["bucket"], ladle=s["ladle"])


def build_dry(plan, P, LM, coll):
    from .room_other import tv_recess

    d, m = SL.DRY, SL.dry_dims()
    rid, x0, x1, H = "Dry", 9.58, 12.42, SL.H
    f = T_BACK + T_SLAT
    xw, xe, ys, yn = x0 + f, x1 - f, Y0S + f, Y1S - f
    assert max(abs(xw - d["xw"]), abs(xe - d["xe"]), abs(ys - SL.Y0), abs(yn - SL.Y1)) < 1e-6, (
        "sub_layout.py and the wall lining disagree"
    )
    lights = geo.collection(f"{rid}_lights", coll)
    ceil = geo.collection("Ceilings", coll)
    slat = MB(f"{rid}_wall_slats", P["wood"], coll, bevel=0.002)
    back = MB(f"{rid}_backing", P["wood_back"], coll, bevel=0)
    black = MB(f"{rid}_cove_black", P["black"], ceil, bevel=0)
    o = next(o for o in plan["openings"] if o["id"] == "dry-tv")
    shell.slat_wall(slat, back, "x", Y1S, -1, x0, x1, 0, H + 0.03)
    shell.slat_wall(
        slat,
        back,
        "x",
        Y0S,
        1,
        x0,
        x1,
        0,
        H + 0.03,
        openings=[(d["door"][0], d["door"][1], 0, plan["doorHeight"])],
    )
    shell.slat_wall(slat, back, "y", x0, 1, ys, yn, 0, H + SLOT_H)
    shell.slat_wall(
        slat,
        back,
        "y",
        x1,
        -1,
        ys,
        yn,
        0,
        H + 0.03,
        openings=[(o["seg"][1], o["seg"][3], o["z"][0], o["z"][1])],
    )
    cs = MB(f"{rid}_ceiling_slats", P["wood_dark"], ceil, bevel=0.002)
    shell.slat_ceiling(cs, black, xw + SLOT_W, ys, xe, yn, H, along="y")
    cs.finish()
    shell.cove(
        lights, black, LM["sauna_cove"], "y", xw, 1, ys, yn, H, f"LED_{rid}_cove", mode="wall"
    )  # strip never visible from the seats

    mbs = {
        "boards": MB(f"{rid}_bench_boards", P["wood_bench"], coll, bevel=0.005, segments=3),
        "frame": MB(f"{rid}_bench_frame", P["wood_bench"], coll, bevel=0.003),
        "slat": slat,
        "back": back,
    }
    LB = LM["sauna_bench"]
    xu, xf, xst, xd, xds = (
        m["u_nose"],
        m["u_foot_front"],
        m["u_step_front"],
        m["d_front"],
        m["d_step_front"],
    )
    (u0, u1), sp, dy0 = d["u_y"], d["split"], d["deck_y0"]
    top, deck, stp = d["u_top"], d["deck_top"], d["step_top"]
    Lu, Lf, Ld = u1 - u0, sp - dy0, yn - sp
    # high bench for two (upright, feet on the deck 0.45 below)
    furniture.bench_tier(
        Frame(xu, u0, "+y", "-x"),
        Lu,
        SL.SEAT_D,
        top,
        0.0,
        mbs,
        lights,
        LB,
        "dry_high",
        riser_v=0.10,
        legs=[0.105, Lu - 0.06],
        cheeks=(True, False),
        round_ends=(0.07, 0.0),
    )
    furniture.bench_tier(
        Frame(xf, dy0, "+y", "-x"),
        Lf,
        d["u_foot_d"],
        deck,
        0.0,
        mbs,
        lights,
        LB,
        "dry_foot",
        riser_v=0.10,
        legs=[0.105, Lf - 0.06],
        cheeks=(True, False),
        round_ends=(0.10, 0.0),
        led_w=0.012,
    )
    furniture.bench_tier(
        Frame(xst, dy0, "+y", "-x"),
        Lf,
        d["step_d"],
        stp,
        0.0,
        mbs,
        lights,
        LB,
        "dry_step_high",
        riser_v=None,
        legs=[0.105, Lf / 2, Lf - 0.06],
        cheeks=(True, False),
        round_ends=(0.10, 0.0),
        led_w=0.012,
    )
    # low deck for two: 1.50 m from the wall, legs out flat towards the TV
    furniture.bench_tier(
        Frame(xd, sp, "+y", "-x"),
        Ld,
        d["d_depth"],
        deck,
        0.0,
        mbs,
        lights,
        LB,
        "dry_deck",
        riser_v=0.10,
        legs=[0.06, Ld - 0.06],
        cheeks=(True, False),
    )
    furniture.bench_tier(
        Frame(xds, sp, "+y", "-x"),
        Ld,
        d["step_d"],
        stp,
        0.0,
        mbs,
        lights,
        LB,
        "dry_step_deck",
        riser_v=None,
        legs=[0.06, Ld / 2, Ld - 0.06],
        led_w=0.012,
    )
    # diagonal tread where the two half steps jog (v5 / v6 motif)
    g = d["diag"]
    k = 0.03 / math.sqrt(2)
    Fc = Frame(xst, sp, "+x", "-y")
    zb = stp - furniture.BOARD_T
    furniture.plan_prism(
        mbs["boards"], Fc, [(-0.004, -0.004), (g, -0.004), (-0.004, g)], zb, stp, grain="u"
    )
    furniture.plan_prism(
        mbs["frame"],
        Fc,
        [(g - 2 * k - 0.028, 0.0), (g - 2 * k, 0.0), (0.0, g - 2 * k), (0.0, g - 2 * k - 0.028)],
        zb - furniture.APRON_H,
        zb,
        grain="u",
    )
    # timber wing between the two postures, standing on the deck; front top corner eased
    wing = MB(f"{rid}_wing", P["wood_bench"], coll, bevel=0.004, segments=2)
    wy0, wy1 = d["wing"]["y"]
    furniture.profile_panel(
        wing,
        (xw, wy0, xu, wy1),
        deck,
        _eased(xu - xw, d["wing"]["top"], *d["wing"]["ease"]),
        "start",
    )
    wing.finish()
    # raked back on the deck: boards across three ribs, 0.30 m out at the deck and 0.06 m at the top
    bk = d["back"]
    base = (xw + bk["base"], deck)
    tip = (xw + bk["top_in"], deck + bk["h"])
    ln = math.hypot(tip[0] - base[0], tip[1] - base[1])
    e = ((tip[0] - base[0]) / ln, 0.0, (tip[1] - base[1]) / ln)
    nrm = (e[2], 0.0, -e[0])
    yb0, yb1 = sp + 0.01, yn - 0.01
    nb, bw, bt = 7, 0.092, 0.022
    gap = (ln - nb * bw) / (nb - 1)
    for i in range(nb):
        sd = bw / 2 + i * (bw + gap)
        c = (
            base[0] + e[0] * sd - nrm[0] * bt / 2,
            (yb0 + yb1) / 2,
            base[1] + e[2] * sd - nrm[2] * bt / 2,
        )
        mbs["boards"].box_m((yb1 - yb0, bw, bt), geo.basis(c, (0, 1, 0), e, nrm), grain=0)
    off = bt + 0.002
    rib = [(xw, deck), (base[0] - off, deck), (tip[0] - off, tip[1]), (xw, tip[1])]
    for yc in (yb0 + 0.03, (yb0 + yb1) / 2, yb1 - 0.03):
        mbs["frame"].prism(rib, geo.basis((0.0, yc, 0.0), (1, 0, 0), (0, 1, 0), (0, 0, 1)), 0.03)
    # cap shelf behind the heads; a narrow strip under its front edge washes the raked boards (behind the sitters' heads)
    mbs["boards"].box(xw, yb0, tip[1], tip[0] + 0.06, yb1, tip[1] + bt, "y")
    shell.strip_down(
        lights,
        LB,
        "LED_dry_back",
        tip[0] + 0.032,
        yb0 + 0.06,
        tip[0] + 0.040,
        yb1 - 0.06,
        tip[1] - 0.002,
    )
    furniture.backrest(Frame(xw, u0 + 0.03, "+y", "+x"), Lu - 0.06, top + 0.25, mbs)
    for mb in (mbs["boards"], mbs["frame"]):
        mb.finish()
    slat.finish()
    back.finish(weighted=False)
    hx, hy = d["heater"]["c"]
    furniture.heater(
        P,
        coll,
        f"{rid}_heater",
        hx,
        hy,
        r=d["heater"]["r"],
        h=0.85,
        guard_r=d["heater"]["guard_r"],
        guard_h=0.78,
    )
    trim = MB(f"{rid}_downlight_trims", P["steel"], ceil, bevel=0)
    shell.downlight(
        trim, lights, LM["sauna_heater"], f"LED_{rid}_heater", hx - 0.22, hy + 0.22, H, r=0.03
    )
    trim.finish()
    black.finish(weighted=False)
    tv_recess(plan, P, coll)
    furniture.grille(P, coll, "Dry_exhaust_grille", "x", yn, -1, 11.3, 12.1, 2.05, 2.19)


def check_layer(root):
    """v8 check bodies (boxes, hidden in renders, CHECK_ in the .glb): the six + four seats of the small saunas with their
    standing moments, the people in the two cold pools, on the four annex loungers and at the tight walking spots.
    Called after room_main.check_layer, at the very end of the geometry."""
    people = geo.collection("Check_people", root)
    people.hide_render = True
    seated = materials.flat("check_body", (0.62, 0.50, 0.40), 0.85)
    upright = materials.flat("check_body_standing", (0.36, 0.46, 0.56), 0.85)

    def put(name, mat, boxes):
        mb = MB(f"Body_{name}", mat, people, bevel=0.012, segments=2)
        for part, x0, y0, x1, y1, z0, z1 in boxes:
            mb.box(x0, y0, z0, x1, y1, z1)
        mb.finish()

    for s in SL.all_seats():
        put(s["id"], seated, SL.boxes(s))
    for t in SL.all_standing():
        put(t["id"], upright, ML.standing_boxes(t))
    for bid, kind, label, boxes in WL.bodies():
        put(bid, upright if boxes[0][0] == "stand_body" else seated, boxes)
