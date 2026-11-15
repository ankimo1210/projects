"""Create a separate technical 3D section study. Never opens/saves the frozen interior model."""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "blender"))
from sauna import water_layout as WL

args = sys.argv[sys.argv.index("--") + 1 :]
DATA = Path(args[0])
if DATA.name != "architecture-v1":
    raise ValueError("Refusing any other output root")
data = json.loads((DATA / "calculations/design_balances.json").read_text(encoding="utf-8"))
inputs = json.loads((DATA / "sources/inputs.json").read_text(encoding="utf-8"))
p = {q["id"]: q["value"] for q in inputs["parameters"]}
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1
scene.render.engine = "CYCLES"
scene.cycles.samples = 96
scene.cycles.use_denoising = True
scene.render.resolution_x = 1800
scene.render.resolution_y = 1300
scene.render.resolution_percentage = 100
try:
    pref = bpy.context.preferences.addons["cycles"].preferences
    pref.compute_device_type = "OPTIX"
    pref.get_devices()
    for d in pref.devices:
        d.use = d.type == "OPTIX"
    scene.cycles.device = "GPU"
except Exception:
    scene.cycles.device = "CPU"
world = bpy.data.worlds.new("Technical world")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.8, 0.82, 0.82, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.7
scene.world = world


def mat(name, color, rough=0.6, alpha=1):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, alpha)
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (*color, alpha)
    bs.inputs["Roughness"].default_value = rough
    if alpha < 1:
        bs.inputs["Transmission Weight"].default_value = 0.55
    return m


stone = mat("Hypothetical shell", (0.57, 0.54, 0.48))
wood = mat("Deck and stairs", (0.62, 0.43, 0.25))
water = mat("Water - engineering representation", (0.20, 0.47, 0.60), 0.20, 0.55)
red = mat("Unknown building limits", (0.65, 0.13, 0.08))
green = mat("Headroom plane outline", (0.21, 0.40, 0.25))
skin = mat("1.85m static body", (0.67, 0.43, 0.30))
floor_mat = mat("Floor datum", (0.78, 0.76, 0.71))
steel = mat("Concept rail", (0.21, 0.24, 0.24))


def box(name, coords, material, coll):
    x0, y0, z0, x1, y1, z1 = coords
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    ob = bpy.context.object
    ob.name = name
    ob.dimensions = (x1 - x0, y1 - y0, z1 - z0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll.objects.link(ob)
    ob.data.materials.append(material)
    bevel = ob.modifiers.new("Small edge", "BEVEL")
    bevel.width = 0.008
    bevel.segments = 2
    return ob


def rod(name, a, b, r, material, coll):
    d = Vector(b) - Vector(a)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=12, radius=r, depth=d.length, location=(Vector(a) + Vector(b)) / 2
    )
    ob = bpy.context.object
    ob.name = name
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll.objects.link(ob)
    ob.data.materials.append(material)
    return ob


collections = []
cameras = []
checks = []
for idx, s in enumerate(data["sections"]):
    coll = bpy.data.collections.new(s["id"])
    scene.collection.children.link(coll)
    collections.append(coll)
    x = idx * 7.0
    z = s["deck_z_m"]
    bottom = s["bottom_z_m"]
    outer = s["assembly_bottom_z_m"]
    w = 1.78
    l = 1.9
    for key, value in [
        ("pit_depth_m", s["pit_depth_m"]),
        ("deck_z_m", z),
        ("headroom_m", s["clear_headroom_m"]),
    ]:
        coll[key] = value
    box(f"{s['id']}_shell_bottom", (x, 0, outer, x + w, l, bottom), stone, coll)
    box(f"{s['id']}_shell_east", (x + w, 0, outer, x + w + 0.12, l, z + 0.015), stone, coll)
    box(f"{s['id']}_shell_north", (x, l, outer, x + w, l + 0.12, z), stone, coll)
    box(
        f"{s['id']}_water",
        (x + 0.015, 0.015, s["water_z_m"] - 0.025, x + w - 0.015, l - 0.015, s["water_z_m"]),
        water,
        coll,
    )
    for i, (a, b, c, d, top) in enumerate(WL.pool("deep")["treads"]):
        box(
            f"{s['id']}_inner_step_{i}",
            (x + a - 10.84, b - 6.8, bottom, x + c - 10.84, d - 6.8, z + top),
            stone,
            coll,
        )
    box(f"{s['id']}_deck", (x - 0.20, 1.90, z - 0.08, x + w + 0.2, 2.20, z), wood, coll)
    for k in range(max(0, s["n_risers"] - 1)):
        top = z - (k + 1) * s["riser_m"]
        box(
            f"{s['id']}_external_step_{k}",
            (x + 0.7, 2.2 + k * 0.28, 0, x + 1.6, 2.2 + (k + 1) * 0.28, top),
            wood,
            coll,
        )
    if s["n_risers"]:
        # Separate green landing marker, after the last riser, exactly 0.90 x 0.90m.
        yy = 2.2 + s["stair_run_m"]
        box(
            f"{s['id']}_external_landing_marker",
            (x + 0.7, yy, 0.001, x + 1.6, yy + 0.90, 0.015),
            green,
            coll,
        )
    # Existing finished floor is drawn only around the hole; no claim about a real slab.
    for j, c in enumerate(
        [
            (x - 0.35, -0.35, -0.04, x - 0.02, 5.2, 0),
            (x + w + 0.14, -0.35, -0.04, x + w + 0.45, 5.2, 0),
            (x - 0.02, 2.22, -0.04, x + w + 0.14, 5.2, 0),
            (x - 0.02, -0.35, -0.04, x + w + 0.14, -0.02, 0),
        ]
    ):
        box(f"{s['id']}_floor_{j}", c, floor_mat, coll)
    for plane, height, material in [
        ("ceiling", p["soffit_z"] - p["service_depth"], green),
        ("soffit", p["soffit_z"], red),
    ]:
        pts = [
            (x - 0.3, -0.25, height),
            (x + 2.2, -0.25, height),
            (x + 2.2, 5.1, height),
            (x - 0.3, 5.1, height),
        ]
        for i in range(4):
            rod(f"{s['id']}_{plane}_{i}", pts[i], pts[(i + 1) % 4], 0.013, material, coll)
    # Section line at the sauna-side wall in the original plan: y10.388 - y6.8.
    rod(
        f"{s['id']}_wall_limit",
        (x + 2.15, 3.588, 0),
        (x + 2.15, 3.588, p["soffit_z"]),
        0.025,
        red,
        coll,
    )
    for yy in [0, 1.9]:
        rod(
            f"{s['id']}_datum_edge_{yy}", (x - 0.3, yy, -0.2), (x + 2.2, yy, -0.2), 0.010, red, coll
        )
    bx = x + 0.35
    by = 2.04
    box(
        f"{s['id']}_person_legs",
        (bx - 0.13, by - 0.09, z, bx + 0.13, by + 0.09, z + 0.9),
        skin,
        coll,
    )
    box(
        f"{s['id']}_person_torso",
        (bx - 0.23, by - 0.13, z + 0.9, bx + 0.23, by + 0.13, z + 1.60),
        skin,
        coll,
    )
    box(
        f"{s['id']}_person_head",
        (bx - 0.095, by - 0.095, z + 1.60, bx + 0.095, by + 0.095, z + 1.85),
        skin,
        coll,
    )
    cam = bpy.data.cameras.new(f"Camera_{s['id']}")
    ob = bpy.data.objects.new(cam.name, cam)
    scene.collection.objects.link(ob)
    ob.location = (x - 4.0, -5.0, 4.6)
    target = Vector((x + 0.75, 2.0, 0.65))
    ob.rotation_euler = (target - ob.location).to_track_quat("-Z", "Y").to_euler()
    cam.type = "ORTHO"
    cam.ortho_scale = 7.0
    cameras.append(ob)
    checks.append(
        {
            "case": s["id"],
            "deck_z_m": z,
            "bottom_z_m": bottom,
            "depth_m": s["water_z_m"] - bottom,
            "clear_headroom_m": s["clear_headroom_m"],
            "body_top_m": z + 1.85,
            "static_body_intersects_ceiling": z + 1.85 > p["soffit_z"] - p["service_depth"],
        }
    )
for x in [0, 7, 14]:
    lamp = bpy.data.lights.new(f"Area_{x}", "AREA")
    lamp.energy = 450
    lamp.shape = "DISK"
    lamp.size = 5
    ob = bpy.data.objects.new(lamp.name, lamp)
    ob.location = (x - 1, -1, 7)
    scene.collection.objects.link(ob)
scene.camera = cameras[0]
model = DATA / "model/section_studies.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(model), compress=True)
bpy.ops.export_scene.gltf(
    filepath=str(DATA / "model/section_studies.glb"),
    export_format="GLB",
    use_selection=False,
    export_cameras=True,
    export_lights=False,
)
for i, coll in enumerate(collections):
    for c in collections:
        c.hide_render = c != coll
    scene.camera = cameras[i]
    scene.render.filepath = str(DATA / "renders" / f"section_{coll.name}_3d.png")
    bpy.ops.render.render(write_still=True)
(DATA / "verification/native_sections.json").write_text(
    json.dumps(
        {
            "blender": bpy.app.version_string,
            "cases": checks,
            "meshes": sum(o.type == "MESH" for o in scene.objects),
            "frozen_model_loaded": False,
            "geometry_note": "Separate simplified technical cutaway. Geometry uses the same pool dimensions and internal stair layout; hypothetical shells/levels do not certify construction.",
        },
        indent=2,
    ),
    encoding="utf-8",
)
print("SECTION_STUDIES_OK")
