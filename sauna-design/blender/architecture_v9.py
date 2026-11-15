"""V9 building-integration prototype (study model for matching a future property; plan A "recessed", provisional).

NOT EXECUTED BY THE AUTHOR. Written for audit first; the parent runs it after review.

What it does
  The accepted V8 model is opened without ever being saved, its SHA256 is checked before and after, and a new
  file fable-v9/model/sauna_a_v9.blend is written with one save_as call. All V8 objects, cameras, materials and
  coordinates stay as they are (metres, x east, y north, z up, finished floor FL = 0). The study graphics are
  added in a separate collection tree "V9_Architecture_Study" that is render-hidden in the saved file, so every
  V8 camera renders the V8 interior unless the study is switched on.

Provisional conditions shown (none of them is a property, structure, equipment or code-compliance fact)
  footprint 20 x 14 m, FL 0, assumed existing slab top -0.20, assumed beam soffit +3.00, service band 0.35
  (underside +2.65), deep pool inner 1.78 x 1.90 at x 10.84 / y 6.80, water depth 1.20, water surface -0.06,
  pool bottom -1.26, support underside -1.51 (0.25 envelope), pit 1.31 below the assumed slab top,
  machine room 21 m2 (x 17..20, y 0..7). Outdoor heat rejection and the carry-in / replacement route are HOLD
  markers parked beside the model: no location, area, opening or route is decided.
  No beam, column, existing pit or slab thickness of a real building is modelled.

Display assumptions introduced by this file (flagged in the JSON records, not design values)
  * the slab is drawn as a 20 mm plate at its assumed top; its thickness is unknown
  * the 0.25 m envelope below the pool bottom is also drawn sideways to size the slab openings
  * seated and carbonated pools use the V8 dimensions and the same rule (bottom -0.66, underside -0.91)
  * labels are ASCII (no font file is read); "*" means assumed

Files read: the V8 .blend (plus the image files that .blend itself links to, loaded by Blender) and this
script's own outputs. Files written: only under <out-root> = .../sauna-design/fable-v9, only names starting with
"v9_" or "sauna_a_v9", never overwriting unless --replace is given.

Steps (one Blender process each; see scripts/blender_v9.sh)
  estimate   disk estimate against the budget (no model is opened)
  build      V8 hash check -> open V8 -> fingerprint -> add study -> save_as V9 -> V8 hash check
  verify     open V9 -> compare every V8 object/camera/mesh/material with the fingerprint -> study checks
  render     open V9 -> one camera -> PNG (start with: --tests --res 600 --samples 48)
  glb        open V9 -> simplified materials in memory -> light .glb (the .blend is not saved)

  blender -b --python-exit-code 1 --python architecture_v9.py -- --step build --v8 <sauna_a_v8.blend> --out-root <fable-v9>
"""

import argparse
import hashlib
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector

sys.dont_write_bytecode = True

V8_SHA256 = "1213509aa6fef497125d3d41cef5bb5682cd410acc0c588ee6048c4b2f5e0f94"
MODEL_NAME = "sauna_a_v9.blend"
GLB_NAME = "sauna_a_v9_light.glb"
BUDGET_MB = 1000.0
STUDY_ROOT = "V9_Architecture_Study"
SUB = {
    "levels": "V9_Levels",
    "slab": "V9_Slab_assumed",
    "pools": "V9_Pool_envelopes_A",
    "band": "V9_Service_band",
    "marks": "V9_Plan_marks",
    "machine": "V9_Machine_room_21m2",
    "outdoor": "V9_Outdoor_and_carry_in_HOLD",
    "section": "V9_Section_y7750",
    "sec_local": "V9_Section_labels_local",
    "sec_long": "V9_Section_labels_long",
    "plan_labels": "V9_Plan_labels",
    "cameras": "V9_Cameras",
}

# ---------------------------------------------------------------- provisional conditions
P = {
    "footprint": (0.0, 0.0, 20.0, 14.0),
    "fl": 0.0,
    "slab_top": -0.20,
    "beam_soffit": 3.00,
    "service_band": 0.35,
    "water_drop": 0.06,
    "envelope_below": 0.25,
    "envelope_side_display": 0.25,
    "slab_display_thickness": 0.02,
    "machine_room": (17.0, 0.0, 20.0, 7.0),
    "section_y": 7.75,
}
POOLS = [
    {
        "key": "deep",
        "label": "DEEP",
        "rect": (10.84, 6.80, 1.78, 1.90),
        "depth": 1.20,
        "basis": "provisional plan A given for V9",
    },
    {
        "key": "seated",
        "label": "SEATED",
        "rect": (12.90, 6.80, 1.60, 1.90),
        "depth": 0.60,
        "basis": "V8 model dimension; levels derived by the same rule, not specified",
    },
    {
        "key": "carbon",
        "label": "CARBON",
        "rect": (13.10, 11.10, 3.30, 2.20),
        "depth": 0.60,
        "basis": "V8 model dimension; levels derived by the same rule, not specified",
    },
]
UNCONFIRMED = [
    "site, jurisdiction, structure drawings, beams, columns, slab, foundations, groundwater",
    "permission and feasibility of cutting the slab or excavating; waterproofing; support down to the foundation",
    "slab thickness and level (the -0.20 top is assumed); beam soffit (+3.00 is assumed)",
    "service band 0.35 m: crossings, fire parts and access are not designed",
    "lateral envelope of the pool assemblies (0.25 m is a display assumption)",
    "seated / carbonated pool undersides (derived, not specified)",
    "machine room layout, equipment sizes, headers, backwash drain, CO2 / chemical storage and exhaust",
    "outdoor heat rejection: location, area, permission (about 34.6 kW for two cooling systems plus AC)",
    "carry-in and replacement route: a D1.00 x H2.10 tank does not pass a 0.90 opening / 0.80 clear frame",
    "supply utilities, exhaust routes, legal applicability, permits",
]


def derived():
    side = P["envelope_side_display"]
    water = P["fl"] - P["water_drop"]
    pools = []
    for p in POOLS:
        x, y, w, h = p["rect"]
        bottom = water - p["depth"]
        under = bottom - P["envelope_below"]
        pools.append(
            {
                **p,
                "inner": (x, y, x + w, y + h),
                "env": (x - side, y - side, x + w + side, y + h + side),
                "water": water,
                "bottom": bottom,
                "under": under,
                "pit_below_slab_top": P["slab_top"] - under,
                "below_fl": P["fl"] - under,
            }
        )
    mr = P["machine_room"]
    d = {
        "pools": pools,
        "band_underside": P["beam_soffit"] - P["service_band"],
        "headroom_a": P["beam_soffit"] - P["service_band"] - P["fl"],
        "machine_area": (mr[2] - mr[0]) * (mr[3] - mr[1]),
    }
    deep = pools[0]
    for got, want, what in [
        (deep["water"], -0.06, "water surface"),
        (deep["bottom"], -1.26, "pool bottom"),
        (deep["under"], -1.51, "support underside"),
        (deep["pit_below_slab_top"], 1.31, "pit"),
        (d["band_underside"], 2.65, "band underside"),
        (d["machine_area"], 21.0, "machine room"),
    ]:
        if abs(got - want) > 1e-9:
            raise RuntimeError(f"V9 provisional condition mismatch: {what} {got} != {want}")
    return d


# ---------------------------------------------------------------- paths and records
def norm(p):
    return os.path.normcase(os.path.normpath(os.path.abspath(p)))


def inside(root, p):
    r, q = norm(root), norm(p)
    return q.startswith(r + os.sep)


def check_root(p):
    q = os.path.normpath(os.path.abspath(p))
    if (
        os.path.basename(q).lower() != "fable-v9"
        or os.path.basename(os.path.dirname(q)).lower() != "sauna-design"
    ):
        raise RuntimeError(f"out-root must be .../sauna-design/fable-v9, got {q}")
    if not os.path.isdir(q):
        raise RuntimeError(f"out-root does not exist: {q}")
    return q


def check_v8(p, root):
    q = os.path.normpath(os.path.abspath(p))
    parts = q.replace("\\", "/").lower().split("/")
    if parts[-3:] != ["fable-v8", "model", "sauna_a_v8.blend"]:
        raise RuntimeError(f"--v8 must be .../fable-v8/model/sauna_a_v8.blend, got {q}")
    if inside(root, q) or not os.path.isfile(q):
        raise RuntimeError(f"V8 model not found or inside the output root: {q}")
    return q


def out_path(root, sub, name, replace=False, append=False):
    if not (name.startswith("v9_") or name.startswith("sauna_a_v9")):
        raise RuntimeError(f"output name must start with v9_ or sauna_a_v9: {name}")
    path = os.path.join(root, sub, name)
    if not inside(root, path):
        raise RuntimeError(f"refusing to write outside the V9 root: {path}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path) and not (replace or append):
        raise RuntimeError(
            f"refusing to overwrite {path} (pass --replace for this script's own outputs)"
        )
    return path


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def file_state(path):
    st = os.stat(path)
    return {
        "path": path,
        "bytes": st.st_size,
        "mtime_ns": st.st_mtime_ns,
        "sha256": sha256_file(path),
    }


def dir_bytes(root):
    total = 0
    for base, _dirs, files in os.walk(root):
        for n in files:
            try:
                total += os.path.getsize(os.path.join(base, n))
            except OSError:
                pass
    return total


def check_v8_hash(v8, expected):
    st = file_state(v8)
    if st["sha256"] != expected:
        raise RuntimeError(
            f"V8 model SHA256 {st['sha256']} differs from the expected {expected}; nothing was opened or written"
        )
    return st


def estimate(root, v8):
    s = os.path.getsize(v8)
    existing = dir_bytes(root)
    items = {
        "blend_expected": 1.15 * s + 2e6,
        "blend_upper": 4.0 * s
        + 2e6,  # if V8 is zstd-compressed and V9 ends up much less compressible
        "glb_upper": 20e6,  # the V8 .glb with textures was 16.3 MB
        "final_renders_upper": 10 * 11.6e6,  # 10 PNG, 2400 x 1600 RGB8 uncompressed size
        "test_renders_upper": 20 * 1.1e6,  # 20 PNG at 600 px
        "records_and_logs_upper": 10e6,
    }
    expected = (
        existing
        + items["blend_expected"]
        + 0.9 * items["glb_upper"]
        + 0.5 * items["final_renders_upper"]
        + 0.5 * items["test_renders_upper"]
        + 0.2 * items["records_and_logs_upper"]
    )
    upper = (
        existing
        + items["blend_upper"]
        + items["glb_upper"]
        + items["final_renders_upper"]
        + items["test_renders_upper"]
        + items["records_and_logs_upper"]
    )
    rec = {
        "budget_mb": BUDGET_MB,
        "v8_blend_mb": round(s / 1e6, 2),
        "existing_in_root_mb": round(existing / 1e6, 2),
        "items_mb": {k: round(v / 1e6, 1) for k, v in items.items()},
        "expected_total_mb": round(expected / 1e6, 1),
        "upper_total_mb": round(upper / 1e6, 1),
        "within_budget": upper / 1e6 <= BUDGET_MB,
    }
    return rec


# ---------------------------------------------------------------- fingerprint of everything that came from V8
def is_v9(name):
    return name.startswith("V9_") or name.startswith("Cam_v9_")


def plain(v):
    if hasattr(v, "to_dict"):
        return {k: plain(x) for k, x in v.to_dict().items()}
    if hasattr(v, "to_list"):
        return [plain(x) for x in v.to_list()]
    if isinstance(v, bool) or v is None or isinstance(v, (int, str)):
        return v
    if isinstance(v, float):
        return round(v, 6)
    if isinstance(v, (list, tuple)):
        return [plain(x) for x in v]
    if isinstance(v, dict):
        return {str(k): plain(x) for k, x in v.items()}
    return str(v)


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=True).encode()).hexdigest()[
        :24
    ]


def props(idblock):
    return {k: plain(idblock[k]) for k in idblock.keys() if not k.startswith("_")}


def mesh_digest(me):
    import numpy as np

    h = hashlib.sha256()
    nv, nl, npoly = len(me.vertices), len(me.loops), len(me.polygons)
    h.update(f"{nv},{len(me.edges)},{nl},{npoly}".encode())
    if nv:
        a = np.empty(nv * 3, np.float32)
        me.vertices.foreach_get("co", a)
        h.update(a.tobytes())
    if nl:
        a = np.empty(nl, np.int32)
        me.loops.foreach_get("vertex_index", a)
        h.update(a.tobytes())
    if npoly:
        for attr in ("loop_start", "loop_total", "material_index"):
            a = np.empty(npoly, np.int32)
            me.polygons.foreach_get(attr, a)
            h.update(a.tobytes())
    for uv in me.uv_layers:
        h.update(uv.name.encode())
        if not nl:
            continue
        a = np.empty(nl * 2, np.float32)
        try:
            uv.uv.foreach_get("vector", a)
        except Exception:
            try:
                uv.data.foreach_get("uv", a)
            except Exception:
                h.update(b"uv-unread")
                continue
        h.update(a.tobytes())
    h.update("|".join(m.name if m else "-" for m in me.materials).encode())
    return h.hexdigest()[:24]


def fingerprint():
    """Everything that is not a V9 addition. Computed on V8 before the study is added and again on the saved V9."""
    bpy.context.view_layer.update()
    scene = bpy.context.scene
    fp = {
        "objects": {},
        "cameras": {},
        "lights": {},
        "meshes": {},
        "materials": {},
        "collections": {},
        "images": {},
    }
    for ob in bpy.data.objects:
        if is_v9(ob.name):
            continue
        fp["objects"][ob.name] = digest(
            {
                "type": ob.type,
                "data": ob.data.name if ob.data else None,
                "parent": ob.parent.name if ob.parent else None,
                "m": [round(v, 6) for row in ob.matrix_world for v in row],
                "hr": ob.hide_render,
                "hv": ob.hide_viewport,
                "coll": sorted(c.name for c in ob.users_collection),
                "mods": [m.type for m in ob.modifiers],
                "mats": [s.material.name if s.material else None for s in ob.material_slots],
                "props": props(ob),
            }
        )
        if ob.type == "CAMERA":
            c = ob.data
            fp["cameras"][ob.name] = {
                "loc": [round(v, 6) for v in ob.matrix_world.translation],
                "rot": [round(v, 6) for v in ob.matrix_world.to_euler()],
                "type": c.type,
                "lens": round(c.lens, 6),
                "ortho_scale": round(c.ortho_scale, 6),
                "sensor_width": round(c.sensor_width, 6),
                "shift": [round(c.shift_x, 6), round(c.shift_y, 6)],
                "clip": [round(c.clip_start, 6), round(c.clip_end, 6)],
                "props": props(ob),
            }
        elif ob.type == "LIGHT":
            li = ob.data
            fp["lights"][ob.name] = {
                "type": li.type,
                "energy": round(li.energy, 6),
                "color": [round(v, 6) for v in li.color],
                "spot_size": round(getattr(li, "spot_size", 0.0), 6),
                "shadow_soft_size": round(getattr(li, "shadow_soft_size", 0.0), 6),
            }
    for me in bpy.data.meshes:
        if not is_v9(me.name):
            fp["meshes"][me.name] = mesh_digest(me)
    for mat in bpy.data.materials:
        if is_v9(mat.name):
            continue
        nt = mat.node_tree
        fp["materials"][mat.name] = digest(
            {
                "nodes": sorted(f"{n.bl_idname}:{n.name}" for n in nt.nodes) if nt else None,
                "links": len(nt.links) if nt else 0,
                "props": props(mat),
            }
        )
    for col in bpy.data.collections:
        if is_v9(col.name):
            continue
        fp["collections"][col.name] = {
            "children": sorted(c.name for c in col.children if not is_v9(c.name)),
            "objects": digest(sorted(o.name for o in col.objects if not is_v9(o.name))),
            "hr": col.hide_render,
            "hv": col.hide_viewport,
        }
    for img in bpy.data.images:
        packed = img.packed_file is not None
        exists = None
        if img.source == "FILE" and img.filepath and not packed:
            exists = os.path.exists(bpy.path.abspath(img.filepath))
        fp["images"][img.name] = {
            "source": img.source,
            "size": [img.size[0], img.size[1]],
            "packed": packed,
            "file_found": exists,
        }
    r, vs = scene.render, scene.view_settings
    fp["scene"] = {
        "name": scene.name,
        "root_children": sorted(c.name for c in scene.collection.children if not is_v9(c.name)),
        "camera": scene.camera.name if scene.camera else None,
        "engine": r.engine,
        "resolution": [r.resolution_x, r.resolution_y, r.resolution_percentage],
        "view": [vs.view_transform, vs.look, round(vs.exposure, 6)],
        "world": scene.world.name if scene.world else None,
        "unit": [scene.unit_settings.system, round(scene.unit_settings.scale_length, 6)],
    }
    fp["counts"] = {k: len(v) for k, v in fp.items() if isinstance(v, dict) and k != "scene"}
    return fp


def diff_fingerprints(a, b):
    out = {}
    for sec in sorted(set(a) | set(b)):
        x, y = a.get(sec, {}), b.get(sec, {})
        if x == y:
            continue
        if isinstance(x, dict) and isinstance(y, dict):
            out[sec] = {
                "removed": sorted(set(x) - set(y))[:50],
                "added": sorted(set(y) - set(x))[:50],
                "changed": sorted(k for k in set(x) & set(y) if x[k] != y[k])[:50],
            }
        else:
            out[sec] = {"before": x, "after": y}
    return out


# ---------------------------------------------------------------- study geometry kit (self-contained)
COLORS = {  # key: (rgb linear, alpha)
    "fl": ((0.90, 0.90, 0.90), 1.0),
    "fl_fill": ((0.75, 0.75, 0.75), 0.25),
    "slab": ((1.00, 0.42, 0.08), 0.65),
    "beam": ((1.00, 0.12, 0.08), 1.0),
    "band": ((1.00, 0.78, 0.08), 1.0),
    "band_fill": ((1.00, 0.78, 0.08), 0.20),
    "water": ((0.10, 0.80, 1.00), 1.0),
    "water_fill": ((0.10, 0.80, 1.00), 0.25),
    "bottom": ((0.20, 0.40, 1.00), 1.0),
    "support": ((1.00, 0.20, 0.80), 1.0),
    "support_fill": ((1.00, 0.20, 0.80), 0.20),
    "machine": ((0.35, 1.00, 0.30), 1.0),
    "machine_fill": ((0.35, 1.00, 0.30), 0.12),
    "hold": ((1.00, 0.60, 0.00), 1.0),
    "hold_fill": ((1.00, 0.60, 0.00), 0.25),
    "text": ((1.00, 1.00, 1.00), 1.0),
    "back": ((0.00, 0.00, 0.00), 0.78),
}
EMIT_BASE = 0.8  # scene-linear at exposure 0; the render step divides by 2**exposure so the colours stay readable


def study_mat(key):
    rgb, alpha = COLORS[key]
    name = "V9_mat_" + key
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.name = "V9_EMIT"
    strength = 0.0 if key == "back" else EMIT_BASE
    em.inputs["Color"].default_value = (*rgb, 1.0)
    em.inputs["Strength"].default_value = strength
    if alpha < 1.0:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs[0].default_value = alpha
        nt.links.new(tr.outputs[0], mix.inputs[1])
        nt.links.new(em.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
    else:
        nt.links.new(em.outputs[0], out.inputs["Surface"])
    mat["v9_emit_base"] = strength
    mat["v9_rgb"] = list(rgb)
    mat["v9_alpha"] = alpha
    mat.diffuse_color = (*rgb, alpha)
    try:
        mat.cycles.emission_sampling = (
            "NONE"  # graphics only: never a light source for the V8 interior
        )
    except Exception:
        pass
    return mat


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


class Acc:
    """Axis-aligned boxes collected into one mesh."""

    def __init__(self):
        self.v, self.f = [], []

    def box(self, x0, y0, z0, x1, y1, z1):
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        z0, z1 = min(z0, z1), max(z0, z1)
        i = len(self.v)
        self.v += [
            (x0, y0, z0),
            (x1, y0, z0),
            (x1, y1, z0),
            (x0, y1, z0),
            (x0, y0, z1),
            (x1, y0, z1),
            (x1, y1, z1),
            (x0, y1, z1),
        ]
        self.f += [
            (i, i + 3, i + 2, i + 1),
            (i + 4, i + 5, i + 6, i + 7),
            (i, i + 1, i + 5, i + 4),
            (i + 1, i + 2, i + 6, i + 5),
            (i + 2, i + 3, i + 7, i + 6),
            (i + 3, i, i + 4, i + 7),
        ]

    def bar(self, a, b, t, cap=True):
        lo = [min(a[k], b[k]) for k in range(3)]
        hi = [max(a[k], b[k]) for k in range(3)]
        for k in range(3):
            if hi[k] - lo[k] < 1e-9 or cap:
                lo[k] -= t / 2
                hi[k] += t / 2
        self.box(lo[0], lo[1], lo[2], hi[0], hi[1], hi[2])

    def dashed(self, a, b, t, dash=0.25, gap=0.15):
        d = Vector(b) - Vector(a)
        length = d.length
        if length < 1e-9:
            return
        u = d / length
        s = 0.0
        while s < length - 1e-9:
            e = min(s + dash, length)
            self.bar(tuple(Vector(a) + u * s), tuple(Vector(a) + u * e), t, cap=False)
            s += dash + gap

    def rect_xy(self, r, z, t, dashed=False):
        x0, y0, x1, y1 = r
        pts = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
        for k in range(4):
            (self.dashed if dashed else self.bar)(pts[k], pts[(k + 1) % 4], t)

    def wire_box(self, r, z0, z1, t):
        x0, y0, x1, y1 = r
        self.rect_xy(r, z0, t)
        self.rect_xy(r, z1, t)
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            self.bar((x, y, z0), (x, y, z1), t)

    def cyl(self, cx, cy, r, z0, z1, n=32):
        i = len(self.v)
        ring = [
            (cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n))
            for k in range(n)
        ]
        self.v += [(x, y, z0) for x, y in ring] + [(x, y, z1) for x, y in ring]
        for k in range(n):
            j = (k + 1) % n
            self.f.append((i + k, i + j, i + n + j, i + n + k))
        self.f.append(tuple(i + k for k in reversed(range(n))))
        self.f.append(tuple(i + n + k for k in range(n)))


class Study:
    def __init__(self, scene):
        self.root = bpy.data.collections.new(STUDY_ROOT)
        scene.collection.children.link(self.root)
        self.coll = {}
        for key, name in SUB.items():
            c = bpy.data.collections.new(name)
            self.root.children.link(c)
            self.coll[key] = c
        self.mat = {k: study_mat(k) for k in COLORS}
        self.accs = {}
        self.texts = []
        self.n_text = 0
        self.warnings = []

    def acc(self, ck, mk, part="all"):
        return self.accs.setdefault((ck, mk, part), Acc())

    def flush(self):
        names = []
        for (ck, mk, part), a in self.accs.items():
            if not a.v:
                continue
            name = f"V9_{ck}_{part}__{mk}"
            me = bpy.data.meshes.new(name)
            me.from_pydata(a.v, [], a.f)
            me.update()
            me.materials.append(self.mat[mk])
            ob = bpy.data.objects.new(name, me)
            ob["v9_study"] = True
            self.coll[ck].objects.link(ob)
            camera_only(ob)
            names.append(name)
        self.accs = {}
        return names

    def label(self, ck, text, loc, size, plane="XY", ax="LEFT", ay="BOTTOM", backing=True):
        """ASCII label. plane XY lies flat (read from above, north up); XZ stands in the section plane (read from the south)."""
        self.n_text += 1
        name = f"V9_txt_{ck}_{self.n_text:03d}"
        cu = bpy.data.curves.new(name, "FONT")
        cu.body = text
        cu.size = size
        cu.align_x = ax
        cu.align_y = ay
        ob = bpy.data.objects.new(name, cu)
        ob.location = loc
        if plane == "XZ":
            ob.rotation_euler = (math.pi / 2, 0.0, 0.0)
        ob["v9_text"] = text
        self.coll[ck].objects.link(ob)
        self.texts.append(ob)
        if backing:
            lines = text.split("\n")
            w = max(len(s) for s in lines) * size * 0.62
            h = len(lines) * size * 1.25
            pad = 0.35 * size
            x = loc[0]
            x0 = {"LEFT": x, "RIGHT": x - w, "CENTER": x - w / 2}[ax] - pad
            v = loc[1] if plane == "XY" else loc[2]
            v0 = {"TOP": v - h, "BOTTOM": v, "CENTER": v - h / 2}[ay] - pad
            a = self.acc(ck, "back", "labels")
            if plane == "XY":
                a.box(x0, v0, loc[2] - 0.004, x0 + w + 2 * pad, v0 + h + 2 * pad, loc[2] - 0.002)
            else:
                a.box(x0, loc[1] + 0.0008, v0, x0 + w + 2 * pad, loc[1] + 0.0016, v0 + h + 2 * pad)

    def realize_labels(self):
        """Text objects become meshes, so the .glb and any viewer show them without a font."""
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        for ob in self.texts:
            try:
                me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps))
                if len(me.polygons) == 0:
                    bpy.data.meshes.remove(me)
                    raise RuntimeError("empty text mesh")
                name, cu = ob.name, ob.data
                me.name = name
                me.materials.clear()
                me.materials.append(self.mat["text"])
                new = bpy.data.objects.new(name + "_m", me)
                new.location = ob.location
                new.rotation_euler = ob.rotation_euler
                new["v9_text"] = ob["v9_text"]
                new["v9_study"] = True
                for c in ob.users_collection:
                    c.objects.link(new)
                bpy.data.objects.remove(ob)
                bpy.data.curves.remove(cu)
                new.name = name
                camera_only(new)
            except Exception as e:
                ob.data.materials.append(self.mat["text"])
                camera_only(ob)
                self.warnings.append(f"label {ob.name} kept as a text object: {e}")
        self.texts = []


def rect_minus(outer, holes):
    x0, y0, x1, y1 = outer
    xs = sorted({x0, x1} | {min(max(h[k], x0), x1) for h in holes for k in (0, 2)})
    ys = sorted({y0, y1} | {min(max(h[k], y0), y1) for h in holes for k in (1, 3)})
    cells = []
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            if not any(h[0] < cx < h[2] and h[1] < cy < h[3] for h in holes):
                cells.append((xs[i], ys[j], xs[i + 1], ys[j + 1]))
    return cells


def segments(a, b, cuts):
    out = [(a, b)]
    for c0, c1 in cuts:
        nxt = []
        for s, e in out:
            if c1 <= s or c0 >= e:
                nxt.append((s, e))
                continue
            if c0 > s:
                nxt.append((s, c0))
            if c1 < e:
                nxt.append((c1, e))
        out = nxt
    return out


def add_camera(name, coll, loc, ortho, rot=None, target=None, clip=(0.1, 200.0), **custom):
    cam = bpy.data.cameras.new(name)
    cam.type = "ORTHO"
    cam.ortho_scale = ortho
    cam.sensor_width = 36.0
    cam.clip_start, cam.clip_end = clip
    ob = bpy.data.objects.new(name, cam)
    ob.location = loc
    if rot is not None:
        ob.rotation_euler = rot
    else:
        ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    coll.objects.link(ob)
    for k, v in custom.items():
        ob[k] = v
    return ob


# ---------------------------------------------------------------- the study itself
def build_study(scene):
    D = derived()
    S = Study(scene)
    fx0, fy0, fx1, fy1 = P["footprint"]
    fl, slab, beam = P["fl"], P["slab_top"], P["beam_soffit"]
    band_u = D["band_underside"]
    st = P["slab_display_thickness"]
    deep = D["pools"][0]

    # 3D level frames just outside the perimeter
    ring = (fx0 - 0.06, fy0 - 0.06, fx1 + 0.06, fy1 + 0.06)
    for mk, z in (("beam", beam), ("band", band_u), ("fl", fl), ("slab", slab)):
        S.acc("levels", mk).rect_xy(ring, z, 0.04)

    # assumed slab top as a thin plate with openings where the pool assemblies pass through
    holes = [p["env"] for p in D["pools"]]
    a = S.acc("slab", "slab", "top_plate")
    for c in rect_minus(P["footprint"], holes):
        a.box(c[0], c[1], slab - st, c[2], c[3], slab)

    # pool assemblies below the floor (plan A recessed)
    for p in D["pools"]:
        k = p["key"]
        S.acc("pools", "support_fill", k).box(
            p["env"][0], p["env"][1], p["under"], p["env"][2], p["env"][3], slab
        )
        S.acc("pools", "support", k).wire_box(p["env"], p["under"], slab, 0.02)
        S.acc("pools", "bottom", k).rect_xy(p["inner"], p["bottom"], 0.02)
        S.acc("pools", "water", k).rect_xy(p["inner"], p["water"], 0.02)
        S.acc("marks", "water", k).rect_xy(p["inner"], fl + 0.03, 0.03)
        S.acc("marks", "support", k).rect_xy(p["env"], fl + 0.03, 0.03, dashed=True)
        cx, cy = (p["inner"][0] + p["inner"][2]) / 2, (p["inner"][1] + p["inner"][3]) / 2
        star = "" if k == "deep" else "*"
        S.label(
            "plan_labels",
            f"{p['label']}\n{p['bottom']:+.2f}{star}\nu/s {p['under']:+.2f}{star}",
            (cx, cy, beam + 0.30),
            0.17,
            ax="CENTER",
            ay="CENTER",
        )

    # service band below the assumed beam soffit
    S.acc("band", "band").wire_box(P["footprint"], band_u, beam, 0.03)
    S.acc("band", "band_fill").box(fx0, fy0, band_u - 0.004, fx1, fy1, band_u)

    # machine room 21 m2: envelope only, equipment and layout are not fixed here
    mr = P["machine_room"]
    S.acc("machine", "machine").rect_xy(mr, fl + 0.03, 0.05)
    S.acc("machine", "machine").wire_box(mr, fl, beam, 0.025)
    S.acc("machine", "machine_fill").box(mr[0], mr[1], fl, mr[2], mr[3], beam)
    S.label(
        "plan_labels",
        f"MACHINE RM\n{D['machine_area']:.0f} m2\n(provisional)",
        ((mr[0] + mr[2]) / 2, (mr[1] + mr[3]) / 2, beam + 0.30),
        0.28,
        ax="CENTER",
        ay="CENTER",
    )

    # HOLD markers parked east of the model: no location, area, opening or route is decided
    hx0 = fx1 + 0.6
    hold = (hx0, 0.2, hx0 + 4.8, 7.6)
    a = S.acc("outdoor", "hold")
    a.rect_xy(hold, fl + 0.03, 0.04, dashed=True)
    pad = (
        hx0 + 0.3,
        0.6,
        hx0 + 0.3 + 1.06,
        2.6,
    )  # 2.12 m2 = outline of the two provisional units, not a required yard
    a.rect_xy(pad, fl + 0.03, 0.03)
    S.acc("outdoor", "hold_fill").box(pad[0], pad[1], fl, pad[2], pad[3], fl + 0.05)
    S.label(
        "outdoor",
        "HEAT REJECTION\n~34.6kW + AC\n2.12m2 = unit outline\narea/location TBD",
        (hx0 + 1.6, 2.6, fl + 0.06),
        0.20,
        ay="TOP",
    )
    tx, ty = hx0 + 0.9, 4.6  # tank D1.00 x H2.10 against a 0.80 clear frame / 0.90 opening
    S.acc("outdoor", "hold_fill", "tank").cyl(tx, ty, 0.50, fl, fl + 2.10)
    gy = 5.9
    for sx in (-1, 1):
        x_in = tx + sx * 0.40
        a.box(
            min(x_in, x_in + sx * 0.05),
            gy - 0.025,
            fl,
            max(x_in, x_in + sx * 0.05),
            gy + 0.025,
            fl + 2.10,
        )
        a.box(tx + sx * 0.45 - 0.01, gy - 0.15, fl, tx + sx * 0.45 + 0.01, gy + 0.15, fl + 0.03)
    S.label(
        "outdoor",
        "TANK D1.00 x H2.10\nvs CLEAR 0.80/OPEN 0.90\nNO PASS (0.20 short)\nCARRY-IN / REPLACEMENT\nROUTE: TBD",
        (hx0 + 1.6, 6.9, fl + 0.06),
        0.20,
        ay="TOP",
    )
    S.label("outdoor", "HOLD - not located", (hx0, 7.75, fl + 0.06), 0.22)

    # section graphics in the plane y = section_y, read from the south (thin layers, nearest first: text, backing, lines, fills)
    yc = P["section_y"]
    yt, yl, yf = yc + 0.0004, yc + 0.0030, yc + 0.0050
    cut = [p for p in D["pools"] if p["env"][1] <= yc <= p["env"][3]]
    gaps = [(p["env"][0], p["env"][2]) for p in cut]

    def line_h(mk, x0, x1, z, t=0.014, part="lines"):
        S.acc("section", mk, part).box(x0, yl, z - t / 2, x1, yl + 0.001, z + t / 2)

    def line_v(mk, x, z0, z1, t=0.014, part="lines"):
        S.acc("section", mk, part).box(x - t / 2, yl, z0, x + t / 2, yl + 0.001, z1)

    def dash_h(mk, x0, x1, z, t=0.012, dash=0.30, gap=0.18):
        s = x0
        while s < x1 - 1e-9:
            line_h(mk, s, min(s + dash, x1), z, t)
            s += dash + gap

    def fill(mk, x0, z0, x1, z1, part="fills"):
        S.acc("section", mk, part).box(x0, yf, z0, x1, yf + 0.001, z1)

    for s, e in segments(fx0, fx1, gaps):
        line_h("fl", s, e, fl, 0.02)
        fill("fl_fill", s, slab, e, fl)  # finished-floor build-up zone FL 0 .. assumed slab top
        fill("slab", s, slab - st, e, slab)
    for mk, z in (
        ("beam", beam),
        ("band", band_u),
        ("slab", slab),
        ("fl", fl),
        ("bottom", deep["bottom"]),
        ("support", deep["under"]),
    ):
        dash_h(mk, fx0 - 0.6, fx1 + 0.6, z)
    fill("band_fill", fx0, band_u, fx1, beam)
    for p in cut:
        e0, e1 = p["env"][0], p["env"][2]
        i0, i1 = p["inner"][0], p["inner"][2]
        fill("support_fill", e0, p["under"], e1, slab)
        for x in (e0, e1):
            line_v("support", x, p["under"], slab, 0.02)
        line_h("support", e0, e1, p["under"], 0.02)
        fill("water_fill", i0, p["bottom"], i1, p["water"])
        for x in (i0, i1):
            line_v("bottom", x, p["bottom"], fl, 0.014)
        line_h("bottom", i0, i1, p["bottom"], 0.02)
        line_h("water", i0, i1, p["water"], 0.02)
        if p["key"] != "deep":
            S.label(
                "section",
                f"{p['label']} {p['bottom']:+.2f}* u/s {p['under']:+.2f}*",
                (i0 + 0.04, yt, p["under"] - 0.05),
                0.10,
                plane="XZ",
                ay="TOP",
            )
    # dimensions of the deep pool case
    xd = deep["env"][0] - 0.18
    line_v("support", xd, deep["under"], slab, 0.012, "dims")
    for z in (deep["under"], slab):
        line_h("support", xd - 0.06, xd + 0.06, z, 0.012, "dims")
    S.label(
        "section",
        f"{deep['pit_below_slab_top']:.2f}",
        (xd - 0.06, yt, (deep["under"] + slab) / 2),
        0.14,
        plane="XZ",
        ax="RIGHT",
        ay="CENTER",
    )
    xw = deep["inner"][0] + 0.40
    line_v("water", xw, deep["bottom"], deep["water"], 0.012, "dims")
    S.label(
        "section",
        f"{deep['depth']:.2f}",
        (xw + 0.06, yt, (deep["bottom"] + deep["water"]) / 2 - 0.1),
        0.14,
        plane="XZ",
        ay="CENTER",
    )
    S.label(
        "section",
        f"WL {deep['water']:+.2f}",
        (deep["inner"][0] + 0.50, yt, deep["water"] - 0.05),
        0.11,
        plane="XZ",
        ay="TOP",
    )
    xh = 9.30
    line_v("band", xh, fl, band_u, 0.012, "dims")
    S.label(
        "section", f"{D['headroom_a']:.2f}", (xh + 0.06, yt, 1.30), 0.14, plane="XZ", ay="CENTER"
    )
    S.label(
        "section",
        f"{P['service_band']:.2f}",
        (xh + 0.06, yt, (band_u + beam) / 2),
        0.14,
        plane="XZ",
        ay="CENTER",
    )
    S.label(
        "section",
        f"V9 STUDY  A recessed  section y={yc:.2f} looking north  (provisional, no property)",
        (8.7, yt, 3.70),
        0.15,
        plane="XZ",
    )
    S.label(
        "section",
        "* assumed. Property, structure, equipment and code compliance are NOT confirmed.",
        (8.7, yt, -2.25),
        0.14,
        plane="XZ",
        ay="TOP",
    )
    levels = [
        ("FL 0.00", fl, "above"),
        (f"SLAB TOP {slab:+.2f} *", slab, "below"),
        (f"BEAM SOFFIT {beam:+.2f} *", beam, "above"),
        (f"BAND U/S {band_u:+.2f} * ({P['service_band']:.2f})", band_u, "below"),
        (f"DEEP BOTTOM {deep['bottom']:+.2f}", deep["bottom"], "above"),
        (f"SUPPORT U/S {deep['under']:+.2f} *", deep["under"], "below"),
    ]
    for text, z, side in levels:
        dz, ay = (0.035, "BOTTOM") if side == "above" else (-0.035, "TOP")
        S.label("sec_local", text, (15.0, yt, z + dz), 0.15, plane="XZ", ay=ay)
        S.label("sec_long", text, (fx0 - 0.25, yt, z + dz), 0.22, plane="XZ", ax="RIGHT", ay=ay)
    S.label(
        "sec_long",
        f"V9 STUDY  A recessed  section y={yc:.2f} looking north  (provisional, no property)",
        (fx0, yt, 4.30),
        0.26,
        plane="XZ",
    )

    objects = S.flush()
    S.realize_labels()

    # study cameras (the V8 cameras are untouched)
    cc = S.coll["cameras"]
    add_camera(
        "Cam_v9_plan",
        cc,
        (12.2, 7.0, 40.0),
        27.8,
        rot=(0.0, 0.0, 0.0),
        exposure=1.6,
        v9_ambient=0.5,
        v9_aspect=1.5,
        v9_show="marks,machine,outdoor,plan_labels",
        v9_hide_collections="Ceilings",
        v9_hide_objects="",
    )
    add_camera(
        "Cam_v9_section_deep",
        cc,
        (13.6, -12.0, 0.75),
        10.2,
        rot=(math.pi / 2, 0.0, 0.0),
        clip=(12.0 + yc, 60.0),
        exposure=3.0,
        v9_ambient=0.0,
        v9_aspect=1.5,
        v9_show="section,sec_local,slab,pools",
        v9_hide_collections="",
        v9_hide_objects="Structure_Base",
    )
    add_camera(
        "Cam_v9_section_long",
        cc,
        (7.8, -12.0, 0.75),
        25.6,
        rot=(math.pi / 2, 0.0, 0.0),
        clip=(12.0 + yc, 60.0),
        exposure=3.0,
        v9_ambient=0.0,
        v9_aspect=3.0,
        v9_show="section,sec_long,slab,pools",
        v9_hide_collections="",
        v9_hide_objects="Structure_Base",
    )
    add_camera(
        "Cam_v9_axo",
        cc,
        (30.0, -14.0, 22.0),
        31.0,
        target=(11.5, 7.0, 0.5),
        exposure=1.6,
        v9_ambient=0.5,
        v9_aspect=1.5,
        v9_show="marks,machine,outdoor,levels",
        v9_hide_collections="Ceilings",
        v9_hide_objects="",
    )
    add_camera(
        "Cam_v9_under",
        cc,
        (21.0, -7.0, -13.0),
        11.0,
        target=(12.6, 8.2, -0.5),
        exposure=1.6,
        v9_ambient=0.8,
        v9_aspect=1.5,
        v9_show="slab,pools,levels",
        v9_hide_collections="",
        v9_hide_objects="Structure_Base",
    )

    S.root["v9_params"] = json.dumps({"P": P, "POOLS": POOLS}, sort_keys=True)
    S.root["v9_note"] = (
        "Provisional study graphics. Property, structure, equipment and code compliance are not confirmed."
    )
    S.root.hide_render = True  # V8 cameras render the V8 interior unless the study is switched on
    return {
        "objects": objects,
        "labels": S.n_text,
        "warnings": S.warnings,
        "collections": [STUDY_ROOT] + list(SUB.values()),
        "cameras": [
            "Cam_v9_plan",
            "Cam_v9_section_deep",
            "Cam_v9_section_long",
            "Cam_v9_axo",
            "Cam_v9_under",
        ],
    }


# ---------------------------------------------------------------- geometric checks (V8 geometry is measured, not edited)
def horizontal_index(want):
    """Horizontal faces of the mesh objects selected by want(ob), in world coordinates."""
    import numpy as np

    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    index, unindexed = [], []
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH" or not want(ob):
            continue
        try:
            me = ob.data
            try:
                ev = ob.evaluated_get(deps).data
                if len(ev.vertices) and len(ev.polygons):
                    me = ev
            except Exception:
                pass
            nv, nl, npoly = len(me.vertices), len(me.loops), len(me.polygons)
            if not nv or not npoly:
                continue
            co = np.empty(nv * 3, np.float32)
            me.vertices.foreach_get("co", co)
            m = np.array(ob.matrix_world, dtype=np.float64)
            w = co.reshape(-1, 3).astype(np.float64) @ m[:3, :3].T + m[:3, 3]
            lv = np.empty(nl, np.int32)
            me.loops.foreach_get("vertex_index", lv)
            ls = np.empty(npoly, np.int32)
            me.polygons.foreach_get("loop_start", ls)
            lt = np.empty(npoly, np.int32)
            me.polygons.foreach_get("loop_total", lt)
            if np.any(np.diff(ls) <= 0):
                unindexed.append(ob.name)
                continue
            lco = w[lv]
            mn = np.minimum.reduceat(lco, ls.astype(np.intp), axis=0)
            mx = np.maximum.reduceat(lco, ls.astype(np.intp), axis=0)
            sel = np.nonzero((mx[:, 2] - mn[:, 2]) < 1e-4)[0]
            if not len(sel):
                continue
            index.append(
                {
                    "name": ob.name,
                    "mn": mn[sel],
                    "mx": mx[sel],
                    "ls": ls[sel],
                    "lt": lt[sel],
                    "lco": lco,
                    "bb": (mn[sel].min(axis=0), mx[sel].max(axis=0)),
                }
            )
        except Exception as e:
            unindexed.append(f"{ob.name}: {e}")
    return index, unindexed


def in_poly(x, y, pts):
    n, hit = len(pts), False
    j = n - 1
    for i in range(n):
        xi, yi, xj, yj = pts[i][0], pts[i][1], pts[j][0], pts[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def faces_at(cand, x, y, zlo, zhi):
    import numpy as np

    out = []
    for e in cand:
        m = (
            (e["mn"][:, 0] <= x)
            & (e["mx"][:, 0] >= x)
            & (e["mn"][:, 1] <= y)
            & (e["mx"][:, 1] >= y)
            & (e["mn"][:, 2] >= zlo)
            & (e["mn"][:, 2] <= zhi)
        )
        for k in np.nonzero(m)[0]:
            s, t = int(e["ls"][k]), int(e["lt"][k])
            if in_poly(x, y, e["lco"][s : s + t, :2]):
                out.append((e["name"], float(e["mn"][k, 2])))
    return out


def grid(x0, x1, nx, y0, y1, ny):
    return [
        (x0 + (x1 - x0) * i / (nx - 1), y0 + (y1 - y0) * j / (ny - 1))
        for i in range(nx)
        for j in range(ny)
    ]


def bbox_z(ob):
    zs = [(ob.matrix_world @ Vector(c)).z for c in ob.bound_box]
    return min(zs), max(zs)


def study_checks():
    D = derived()
    res = {"failures": [], "not_measured": [], "pools": {}, "info": {}}
    check_cols = [c for c in bpy.data.collections if c.name.startswith("Check_people")]

    def v8_solid(ob):
        return (
            not is_v9(ob.name)
            and not ob.name.startswith("Body_")
            and not any(c in check_cols for c in ob.users_collection)
        )

    index, unindexed = horizontal_index(v8_solid)
    res["info"]["meshes_with_horizontal_faces"] = len(index)
    res["info"]["meshes_not_indexed"] = unindexed[:40]
    if not any(e["name"].startswith("Floor_") for e in index):
        res["not_measured"].append(
            "no Floor_* mesh found: the floor opening over the pools was not measured"
        )
    slab_index, _ = horizontal_index(lambda ob: ob.name.startswith("V9_slab_"))
    if not slab_index:
        res["failures"].append("the V9 slab plate is missing")
    for p in D["pools"]:
        x0, y0, x1, y1 = p["inner"]
        w, h = x1 - x0, y1 - y0
        cand = [
            e
            for e in index
            if e["bb"][0][0] <= x1
            and e["bb"][1][0] >= x0
            and e["bb"][0][1] <= y1
            and e["bb"][1][1] >= y0
        ]
        floor_hits, other = set(), {}
        for x, y in grid(x0 + 0.03, x1 - 0.03, 5, y0 + 0.03, y1 - 0.03, 5):
            for name, z in faces_at(cand, x, y, P["slab_top"] - 0.005, P["fl"] + 0.005):
                if name.startswith("Floor_"):
                    floor_hits.add(name)
                else:
                    other.setdefault(name, set()).add(round(z, 3))
        levels = {}
        for x, y in grid(
            x0 + 0.10 * w, x0 + 0.45 * w, 4, y0 + 0.10 * h, y0 + 0.90 * h, 5
        ):  # west part, clear of the pool stairs
            for name, z in faces_at(cand, x, y, p["bottom"] - 0.30, P["fl"] - 0.02):
                levels.setdefault(round(z, 3), set()).add(name)
        bottom_found = any(abs(z - p["bottom"]) <= 0.005 for z in levels)
        water_found = any(abs(z - p["water"]) <= 0.005 for z in levels)
        e0, e1, e2, e3 = p["env"]
        slab_hits = sorted(
            {
                n
                for x, y in grid(e0 + 0.01, e2 - 0.01, 5, e1 + 0.01, e3 - 0.01, 5)
                for n, _z in faces_at(slab_index, x, y, P["slab_top"] - 0.05, P["slab_top"] + 0.001)
            }
        )
        res["pools"][p["key"]] = {
            "inner": p["inner"],
            "envelope_display": p["env"],
            "water": p["water"],
            "bottom": p["bottom"],
            "support_underside": p["under"],
            "pit_below_assumed_slab_top": round(p["pit_below_slab_top"], 3),
            "below_fl": round(p["below_fl"], 3),
            "basis": p["basis"],
            "v8_floor_faces_over_the_pool": sorted(floor_hits),
            "other_v8_horizontal_faces_between_fl_and_slab_top": {
                k: sorted(v) for k, v in sorted(other.items())
            },
            "v8_horizontal_levels_in_the_basin": {
                f"{z:+.3f}": sorted(n)[:6] for z, n in sorted(levels.items())
            },
            "v8_bottom_at_expected_level": bottom_found,
            "v8_water_surface_at_expected_level": water_found,
            "v9_slab_faces_inside_the_opening": slab_hits,
        }
        if floor_hits:
            res["failures"].append(
                f"{p['key']}: V8 floor covers the pool (not pierced): {sorted(floor_hits)}"
            )
        if slab_hits:
            res["failures"].append(f"{p['key']}: the V9 slab plate covers the opening")
        if not levels:
            res["not_measured"].append(
                f"{p['key']}: no horizontal V8 face found in the basin; bottom level not measured"
            )
        elif not bottom_found:
            res["failures"].append(
                f"{p['key']}: V8 basin has no face at the study bottom {p['bottom']:+.2f}: {sorted(levels)}"
            )
        if levels and not water_found:
            res["not_measured"].append(
                f"{p['key']}: no flat V8 water face at {p['water']:+.2f} (a displaced water mesh is not measured)"
            )
    ov = []
    pools = D["pools"]
    for i in range(len(pools)):
        for j in range(i + 1, len(pools)):
            a, b = pools[i]["env"], pools[j]["env"]
            dx, dy = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
            if dx > 1e-9 and dy > 1e-9:
                ov.append(
                    {
                        "pools": [pools[i]["key"], pools[j]["key"]],
                        "overlap_x": round(dx, 3),
                        "overlap_y": round(dy, 3),
                        "meaning": "the display envelopes merge: a shared wall or a common pit must be designed downstream",
                    }
                )
    res["info"]["envelope_overlaps"] = ov
    fx0, fy0, fx1, fy1 = P["footprint"]
    res["info"]["envelope_to_footprint_edge_m"] = {
        p["key"]: round(
            min(p["env"][0] - fx0, p["env"][1] - fy0, fx1 - p["env"][2], fy1 - p["env"][3]), 3
        )
        for p in pools
    }
    base = bpy.data.objects.get("Structure_Base")
    if base is not None:
        z0, z1 = bbox_z(base)
        res["info"]["v8_structure_base"] = {
            "z": [round(z0, 3), round(z1, 3)],
            "clear_below_deep_support_underside": round(pools[0]["under"] - z1, 3),
            "note": "V8 backdrop solid, not a real slab or pit floor; hidden in the study section and under views",
        }
        if z1 > pools[0]["under"] + 1e-6:
            res["failures"].append("V8 Structure_Base is above the deep-pool support underside")
    band_u = D["band_underside"]
    ceil = {}
    for col in bpy.data.collections:
        if col.name.startswith("Ceilings"):
            for ob in col.objects:
                if ob.type == "MESH" and not is_v9(ob.name):
                    z0, _z1 = bbox_z(ob)
                    ceil.setdefault(f"{z0:.3f}", []).append(ob.name)
    res["info"]["v8_ceiling_undersides"] = {
        z: {"count": len(n), "examples": sorted(n)[:5]} for z, n in sorted(ceil.items())
    }
    res["info"]["v8_ceilings_inside_the_service_band"] = sorted(
        n
        for z, names in ceil.items()
        if band_u + 1e-6 < float(z) < P["beam_soffit"] - 1e-6
        for n in names
    )[:60]
    res["info"]["service_band_note"] = (
        f"V8 finished ceilings whose underside is above {band_u:+.2f} sit inside the provisional 0.35 band "
        "(the V8 interior is not changed in V9; to be resolved downstream)"
    )
    res["ok"] = not res["failures"]
    return res


# ---------------------------------------------------------------- steps
def open_model(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    if norm(bpy.data.filepath) != norm(path):
        raise RuntimeError(f"opened {bpy.data.filepath}, expected {path}")
    return bpy.context.scene


def step_estimate(args, root, v8):
    rec = estimate(root, v8)
    write_json(out_path(root, "verification", "v9_disk_estimate.json", replace=True), rec)
    print(
        f"V9_ESTIMATE expected {rec['expected_total_mb']} MB, upper {rec['upper_total_mb']} MB, budget {rec['budget_mb']} MB, "
        f"within_budget={rec['within_budget']}"
    )
    if not rec["within_budget"]:
        raise RuntimeError("the upper disk estimate exceeds the budget")
    return rec


def step_build(args, root, v8):
    model = out_path(root, "model", MODEL_NAME, replace=args.replace)
    fp_path = out_path(root, "verification", "v9_v8_fingerprint.json", replace=args.replace)
    rec_path = out_path(root, "verification", "v9_build.json", replace=args.replace)
    before = check_v8_hash(v8, args.v8_sha256)
    est = step_estimate(args, root, v8)
    scene = open_model(v8)
    bpy.context.preferences.filepaths.save_version = 0  # no .blend1 anywhere
    clash = [
        n
        for group in (
            bpy.data.objects,
            bpy.data.collections,
            bpy.data.materials,
            bpy.data.meshes,
            bpy.data.cameras,
        )
        for n in (b.name for b in group)
        if is_v9(n)
    ]
    if clash:
        raise RuntimeError(f"the V8 model already has V9-named data: {clash[:10]}")
    fp = fingerprint()
    write_json(fp_path, fp)
    study = build_study(scene)
    checks = study_checks()
    if norm(model) == norm(v8) or not inside(root, model):
        raise RuntimeError("refusing to save: the target is not a new file under the V9 root")
    bpy.ops.wm.save_as_mainfile(
        filepath=model, check_existing=False, compress=True, relative_remap=True, copy=False
    )
    if norm(bpy.data.filepath) != norm(model):
        raise RuntimeError(f"saved to {bpy.data.filepath}, expected {model}")
    after = file_state(v8)
    unchanged = all(before[k] == after[k] for k in ("bytes", "mtime_ns", "sha256"))
    total = dir_bytes(root)
    rec = {
        "blender": bpy.app.version_string,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "method": "V8 opened and never saved; study added in memory; one save_as to a new file",
        "v8_before": before,
        "v8_after": after,
        "v8_unchanged": unchanged,
        "v8_expected_sha256": args.v8_sha256,
        "v9_model": file_state(model),
        "disk_estimate": est,
        "root_total_mb_after_build": round(total / 1e6, 2),
        "provisional_conditions": {"P": P, "pools": derived()["pools"]},
        "unconfirmed": UNCONFIRMED,
        "study": study,
        "checks": checks,
        "v8_fingerprint_counts": fp["counts"],
        "saved_state": "study root collection is render-hidden; viewport-visible",
    }
    write_json(rec_path, rec)
    print(
        f"V9_BUILD_MODEL {rec['v9_model']['bytes'] / 1e6:.1f} MB sha256={rec['v9_model']['sha256']} -> {model}"
    )
    print(f"V9_BUILD_V8 sha256={after['sha256']} unchanged={unchanged}")
    print(
        f"V9_BUILD_CHECKS failures={len(checks['failures'])} not_measured={len(checks['not_measured'])} warnings={len(study['warnings'])}"
    )
    if not unchanged:
        raise RuntimeError("the V8 model file changed during the build")
    if total / 1e6 > BUDGET_MB:
        raise RuntimeError(f"V9 root is {total / 1e6:.0f} MB, over the budget")
    if checks["failures"]:
        raise RuntimeError("study checks failed: " + "; ".join(checks["failures"]))
    print("V9_BUILD_OK")


def step_verify(args, root, v8):
    model = os.path.join(root, "model", MODEL_NAME)
    rec_path = out_path(root, "verification", "v9_verification.json", replace=True)
    with open(os.path.join(root, "verification", "v9_v8_fingerprint.json"), encoding="utf-8") as f:
        fp_v8 = json.load(f)
    with open(os.path.join(root, "verification", "v9_build.json"), encoding="utf-8") as f:
        build = json.load(f)
    v8_before = file_state(v8)
    m_before = file_state(model)
    open_model(model)
    fp_v9 = json.loads(json.dumps(fingerprint()))
    diff = diff_fingerprints(fp_v8, fp_v9)
    failures = []
    if diff:
        failures.append(f"V8 content differs in the V9 file: sections {sorted(diff)}")
    root_col = bpy.data.collections.get(STUDY_ROOT)
    if root_col is None:
        failures.append("study root collection missing")
    else:
        if not root_col.hide_render:
            failures.append("study root is not render-hidden in the saved file")
        allowed = {root_col} | set(root_col.children)
        stray = [
            o.name
            for o in bpy.data.objects
            if is_v9(o.name) and not set(o.users_collection) <= allowed
        ]
        mixed = [o.name for c in allowed for o in c.objects if not is_v9(o.name)]
        if stray or mixed:
            failures.append(f"study/V8 separation broken: stray={stray[:10]} mixed={mixed[:10]}")
        missing = [n for n in SUB.values() if bpy.data.collections.get(n) is None]
        if missing:
            failures.append(f"study collections missing: {missing}")
    for name in build["study"]["cameras"]:
        if bpy.data.objects.get(name) is None:
            failures.append(f"camera missing: {name}")
    checks = study_checks()
    failures += checks["failures"]
    v8_after = file_state(v8)
    m_after = file_state(model)
    if v8_after["sha256"] != args.v8_sha256 or v8_before["sha256"] != v8_after["sha256"]:
        failures.append("V8 model SHA256 mismatch")
    if m_before["sha256"] != m_after["sha256"] or m_after["sha256"] != build["v9_model"]["sha256"]:
        failures.append("the V9 model differs from the file recorded by the build step")
    rec = {
        "blender": bpy.app.version_string,
        "checked": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "v8": v8_after,
        "v8_expected_sha256": args.v8_sha256,
        "v9_model": m_after,
        "v8_content_identical_in_v9": not diff,
        "fingerprint_counts": fp_v9["counts"],
        "fingerprint_diff": diff,
        "v8_cameras_kept": len(fp_v9["cameras"]),
        "checks": checks,
        "failures": failures,
        "not_measured": checks["not_measured"],
        "unconfirmed": UNCONFIRMED,
        "root_total_mb": round(dir_bytes(root) / 1e6, 2),
        "ok": not failures,
    }
    write_json(rec_path, rec)
    print(
        f"V9_VERIFY v8_identical={not diff} cameras={len(fp_v9['cameras'])} failures={len(failures)} "
        f"not_measured={len(checks['not_measured'])} root={rec['root_total_mb']} MB"
    )
    if failures:
        raise RuntimeError("V9 verification failed: " + "; ".join(failures))
    print("V9_VERIFY_OK")


def configure_render(
    scene,
    res_x,
    res_y,
    samples,
    threshold,
    exposure,
    device,
    look="AgX - Medium High Contrast",
    white_balance=4300.0,
    ambient=0.0,
    neutral=False,
):
    """Same settings as the V8 pipeline (sauna/scene.py configure_render); a study view may use a neutral ambient."""
    scene.render.engine = "CYCLES"
    c = scene.cycles
    used = []
    if device != "CPU":
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = device
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == device
            if d.use:
                used.append(d.name)
        if not used:
            raise RuntimeError(f"no {device} device found (nothing rendered)")
        c.device = "GPU"
    else:
        c.device = "CPU"
        used = ["CPU"]
    c.samples = samples
    c.use_adaptive_sampling = True
    c.adaptive_threshold = threshold
    c.adaptive_min_samples = min(64, samples)
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    c.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    try:
        c.denoising_prefilter = "ACCURATE"
        c.denoising_use_gpu = device != "CPU"
    except Exception:
        pass
    c.max_bounces = 12
    c.diffuse_bounces = 6
    c.glossy_bounces = 6
    c.transmission_bounces = 12
    c.transparent_max_bounces = 12
    c.volume_bounces = 0
    c.caustics_reflective = False
    c.caustics_refractive = True
    c.blur_glossy = 0.5
    c.sample_clamp_indirect = 8.0
    c.use_light_tree = True
    c.seed = 20261114
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    vs = scene.view_settings
    vs.view_transform = "AgX"
    vs.look = look
    vs.exposure = exposure
    scene.display_settings.display_device = "sRGB"
    try:
        vs.use_white_balance = True
        vs.white_balance_temperature = white_balance
        vs.white_balance_tint = 10.0
    except Exception as e:
        print("white balance unavailable:", e)
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    if world.node_tree is None:
        world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        warm = (1.0, 1.0, 1.0, 1) if neutral else (1.0, 0.66, 0.38, 1)
        bg.inputs[0].default_value = warm if ambient > 0 else (0, 0, 0, 1)
        bg.inputs[1].default_value = ambient
    if neutral:
        try:
            world.cycles_visibility.camera = (
                False  # the ambient lights the model but the background stays black for the labels
            )
        except Exception:
            pass
    return used


def named(group, name):
    return [b for b in group if b.name == name or b.name.startswith(name + ".")]


def step_render(args, root, v8):
    model = os.path.join(root, "model", MODEL_NAME)
    view = args.view
    if not view:
        raise RuntimeError("--view is required")
    study_cam = view.startswith("v9_")
    study_on = study_cam if args.study == "auto" else args.study == "on"
    stem = (
        "v9_"
        + (view[3:] if study_cam else "v8cam_" + view)
        + ("_study" if study_on and not study_cam else "")
        + (f"_{args.tag}" if args.tag else "")
    )
    png = out_path(root, "tests" if args.tests else "renders", stem + ".png", replace=args.replace)
    log = out_path(root, "verification", "v9_render_log.jsonl", append=True)
    m_before = file_state(model)
    scene = open_model(model)
    cam = bpy.data.objects.get("Cam_" + view)
    if cam is None or cam.type != "CAMERA":
        raise RuntimeError(f"camera Cam_{view} not found in the V9 model")
    scene.camera = cam
    exposure = args.exposure if args.exposure is not None else float(cam.get("exposure", 0.0))
    ambient = args.world if args.world is not None else float(cam.get("v9_ambient", 0.0))
    aspect = args.aspect if args.aspect is not None else float(cam.get("v9_aspect", 1.5))
    devices = configure_render(
        scene,
        args.res,
        int(round(args.res / aspect)),
        args.samples,
        args.threshold,
        exposure,
        args.device,
        ambient=ambient,
        neutral=study_cam,
    )
    root_col = bpy.data.collections[STUDY_ROOT]
    root_col.hide_render = not study_on
    shown = []
    if study_on:
        keys = [
            k
            for k in (
                args.show or cam.get("v9_show", "levels,slab,pools,marks,machine,outdoor")
            ).split(",")
            if k
        ]
        unknown = [k for k in keys if k not in SUB]
        if unknown:
            raise RuntimeError(f"unknown study collection keys: {unknown}")
        for k, name in SUB.items():
            bpy.data.collections[name].hide_render = k not in keys
        shown = keys
        gain = args.study_gain * 2.0 ** (
            -exposure
        )  # study colours stay the same at any camera exposure
        for mat in bpy.data.materials:
            if (
                "v9_emit_base" in mat.keys()
                and mat.node_tree
                and mat.node_tree.nodes.get("V9_EMIT")
            ):
                mat.node_tree.nodes["V9_EMIT"].inputs["Strength"].default_value = (
                    float(mat["v9_emit_base"]) * gain
                )
    hide_cols = [
        n
        for n in (args.hide if args.hide is not None else cam.get("v9_hide_collections", "")).split(
            ","
        )
        if n
    ]
    for n in hide_cols:
        for col in named(bpy.data.collections, n):
            col.hide_render = True
    hide_obs = [
        n
        for n in (
            args.hide_objects if args.hide_objects is not None else cam.get("v9_hide_objects", "")
        ).split(",")
        if n
    ]
    for n in hide_obs:
        for ob in bpy.data.objects:
            if ob.name.startswith(n):
                ob.hide_render = True
    scene.render.filepath = png
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t0
    if not os.path.isfile(png):
        raise RuntimeError(f"render produced no file: {png}")
    m_after = file_state(model)
    rec = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "view": view,
        "file": png,
        "bytes": os.path.getsize(png),
        "model_used": bpy.data.filepath,
        "model_sha256": m_after["sha256"],
        "model_bytes": m_after["bytes"],
        "model_unchanged_by_render": m_before["sha256"] == m_after["sha256"],
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "max_samples": args.samples,
        "threshold": args.threshold,
        "exposure": exposure,
        "ambient": ambient,
        "study": study_on,
        "study_collections_shown": shown,
        "collections_hidden": hide_cols,
        "object_prefixes_hidden": hide_obs,
        "devices": devices,
        "seconds": round(dt, 1),
        "blender": bpy.app.version_string,
        "test": bool(args.tests),
        "visibility_changes": "in memory for this render only; the model file is not saved",
    }
    if v8:
        rec["v8_sha256_after_render"] = sha256_file(v8)
        rec["v8_matches_expected"] = rec["v8_sha256_after_render"] == args.v8_sha256
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    if not rec["model_unchanged_by_render"] or rec.get("v8_matches_expected") is False:
        raise RuntimeError("a model file changed during the render")
    print(
        f"V9_RENDER_OK view={view} {rec['resolution'][0]}x{rec['resolution'][1]} samples<={args.samples} exposure={exposure} "
        f"study={study_on} time={dt:.1f}s {rec['bytes'] / 1e6:.2f} MB -> {png}"
    )
    print(f"V9_RENDER_MODEL {bpy.data.filepath} sha256={m_after['sha256']}")


def step_glb(args, root, v8):
    """Light interchange file. Materials are simplified in memory only; the product floor is not baked (flat colour)."""
    model = os.path.join(root, "model", MODEL_NAME)
    glb = out_path(root, "model", GLB_NAME, replace=args.replace)
    rec_path = out_path(root, "verification", "v9_glb.json", replace=True)
    m_before = file_state(model)
    open_model(model)
    for col in bpy.data.collections:
        if col.name.startswith("Ceilings"):
            for ob in col.objects:
                ob.name = "CEIL_" + ob.name
        elif col.name.startswith("Check_people"):
            for ob in col.objects:
                ob.name = "CHECK_" + ob.name
    flat, textured, left = [], [], []
    for mat in bpy.data.materials:
        nt = mat.node_tree
        if nt is None:
            continue
        if "v9_rgb" in mat.keys():
            rgba, rough, metal, alpha = (
                list(mat["v9_rgb"]) + [1.0],
                0.9,
                0.0,
                float(mat["v9_alpha"]),
            )
            emit = 1.0 if float(mat["v9_emit_base"]) > 0 else 0.0
        elif "glb_color" in mat.keys() and not mat.name.startswith("moon_rock"):
            rgba, rough, metal = (
                list(mat["glb_color"]) + [1.0],
                float(mat["glb_rough"]),
                float(mat["glb_metal"]),
            )
            emit, alpha = float(mat["glb_emit"]), float(mat["glb_alpha"])
        else:
            left.append(mat.name)
            continue
        image, scale = None, None
        if mat.get("glb_image", "") and not args.no_textures:
            for n in nt.nodes:
                if n.type == "TEX_IMAGE" and n.image and "diff" in n.image.name:
                    image = n.image
                if n.type == "MAPPING":
                    scale = tuple(n.inputs["Scale"].default_value)
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        if image:
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = image
            uv = nt.nodes.new("ShaderNodeUVMap")
            mp = nt.nodes.new("ShaderNodeMapping")
            if scale:
                mp.inputs["Scale"].default_value = scale
            nt.links.new(uv.outputs[0], mp.inputs[0])
            nt.links.new(mp.outputs[0], tex.inputs[0])
            mx = nt.nodes.new("ShaderNodeMix")
            mx.data_type = "RGBA"
            mx.blend_type = "MULTIPLY"
            mx.inputs[0].default_value = 1.0
            nt.links.new(tex.outputs[0], mx.inputs[6])
            mx.inputs[7].default_value = rgba
            nt.links.new(mx.outputs[2], bsdf.inputs["Base Color"])
            textured.append(mat.name)
        else:
            bsdf.inputs["Base Color"].default_value = rgba
            flat.append(mat.name)
        if emit > 0:
            bsdf.inputs["Emission Color"].default_value = rgba
            bsdf.inputs["Emission Strength"].default_value = emit
        if alpha < 1.0:
            bsdf.inputs["Alpha"].default_value = alpha
            try:
                mat.surface_render_method = "BLENDED"
            except Exception:
                mat.blend_method = "BLEND"
    kw = dict(
        filepath=glb,
        export_format="GLB",
        export_apply=True,
        export_cameras=True,
        export_lights=False,
        export_yup=True,
        export_image_format="NONE" if args.no_textures else "AUTO",
        export_texcoords=True,
        export_normals=True,
    )
    if args.draco:
        kw.update(export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
    bpy.ops.export_scene.gltf(**kw)
    m_after = file_state(model)
    rec = {
        "file": file_state(glb),
        "source_model": bpy.data.filepath,
        "source_model_sha256": m_after["sha256"],
        "source_model_unchanged": m_before["sha256"] == m_after["sha256"],
        "draco": bool(args.draco),
        "textures": not args.no_textures,
        "materials_flat": len(flat),
        "materials_textured": len(textured),
        "materials_left_as_is": left,
        "product_floor": "not baked in V9 (flat colour or left as is); use the V8 exporter path if the baked floor is needed",
        "tags": "CEIL_ ceilings, CHECK_ check bodies, V9_ study graphics (all exported; a viewer can hide them)",
        "root_total_mb": round(dir_bytes(root) / 1e6, 2),
    }
    write_json(rec_path, rec)
    if not rec["source_model_unchanged"]:
        raise RuntimeError("the V9 model changed during the export")
    print(f"V9_GLB_OK {rec['file']['bytes'] / 1e6:.1f} MB from {bpy.data.filepath} -> {glb}")


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--step", required=True, choices=["estimate", "build", "verify", "render", "glb"]
    )
    ap.add_argument("--out-root", required=True, help=".../sauna-design/fable-v9 (must exist)")
    ap.add_argument("--v8", default=None, help=".../fable-v8/model/sauna_a_v8.blend (read only)")
    ap.add_argument("--v8-sha256", default=V8_SHA256)
    ap.add_argument(
        "--replace", action="store_true", help="allow replacing this script's own earlier outputs"
    )
    ap.add_argument(
        "--view",
        default=None,
        help="camera name without Cam_, e.g. v9_plan, v9_section_deep, water",
    )
    ap.add_argument("--res", type=int, default=2400)
    ap.add_argument("--aspect", type=float, default=None)
    ap.add_argument("--samples", type=int, default=1024)
    ap.add_argument("--threshold", type=float, default=0.015)
    ap.add_argument("--exposure", type=float, default=None)
    ap.add_argument("--world", type=float, default=None)
    ap.add_argument(
        "--study",
        default="auto",
        choices=["auto", "on", "off"],
        help="auto: on for Cam_v9_*, off for V8 cameras",
    )
    ap.add_argument("--study-gain", type=float, default=1.0)
    ap.add_argument("--show", default=None, help="comma separated study keys: " + ",".join(SUB))
    ap.add_argument(
        "--hide", default=None, help="comma separated collection names to hide for this render"
    )
    ap.add_argument(
        "--hide-objects",
        default=None,
        help="comma separated object-name prefixes to hide for this render",
    )
    ap.add_argument("--tests", action="store_true", help="write to tests/ instead of renders/")
    ap.add_argument("--tag", default="")
    ap.add_argument("--device", default="OPTIX", choices=["OPTIX", "CUDA", "CPU"])
    ap.add_argument("--draco", action="store_true")
    ap.add_argument("--no-textures", action="store_true")
    args = ap.parse_args(argv)
    root = check_root(args.out_root)
    v8 = check_v8(args.v8, root) if args.v8 else None
    if args.step in ("estimate", "build", "verify") and not v8:
        raise RuntimeError(f"--v8 is required for --step {args.step}")
    {
        "estimate": step_estimate,
        "build": step_build,
        "verify": step_verify,
        "render": step_render,
        "glb": step_glb,
    }[args.step](args, root, v8)


main()
