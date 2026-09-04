"""Build a compact metallic orbital sculpture for the web experience."""

import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1] / "assets"
for folder in ("blender", "export", "previews"):
    (ROOT / folder).mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def material(name, color, metal=0, roughness=0.3, emission=0):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, 1)
    result.use_nodes = True
    shader = result.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Emission Color"].default_value = (*color, 1)
    shader.inputs["Emission Strength"].default_value = emission
    return result


def enable_gpu(scene):
    """Enable the first Cycles GPU backend this machine has; fall back to CPU.

    Blender only exposes the backends its build and platform support, so the
    unsupported ones raise on assignment: CUDA/OptiX on the Windows RTX box,
    METAL on Apple silicon, HIP/oneAPI elsewhere.
    """
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
    except Exception as exc:
        print("Cycles preferences unavailable:", exc)
        return "CPU"
    for backend in ("OPTIX", "CUDA", "METAL", "HIP", "ONEAPI"):
        try:
            prefs.compute_device_type = backend
            if hasattr(prefs, "refresh_devices"):
                prefs.refresh_devices()
            else:
                prefs.get_devices()
        except Exception:
            continue
        usable = [device for device in prefs.devices if device.type == backend]
        if not usable:
            continue
        for device in prefs.devices:
            device.use = device.type == backend
        scene.cycles.device = "GPU"
        return backend + ": " + ", ".join(device.name for device in usable)
    return "CPU"


chrome = material("Liquid titanium", (0.47, 0.52, 0.49), 1, 0.19)
dark = material("Obsidian center", (0.013, 0.027, 0.019), 0.7, 0.22)
lime = material("Ion green", (0.57, 1.0, 0.16), 0.2, 0.22, 2.2)
matte = material("Ceramic orbit", (0.12, 0.16, 0.135), 0.8, 0.33)

# A closed trefoil curve provides the sculpture's continuous silhouette.
curve = bpy.data.curves.new("Trefoil", "CURVE")
curve.dimensions = "3D"
curve.bevel_depth = 0.18
curve.bevel_resolution = 4
spline = curve.splines.new("POLY")
count = 256
spline.points.add(count - 1)
for i, point in enumerate(spline.points):
    t = i / count * math.tau
    radius = 1.04 + 0.32 * math.cos(3 * t)
    point.co = (radius * math.cos(2 * t), radius * math.sin(2 * t), 0.46 * math.sin(3 * t), 1)
spline.use_cyclic_u = True
knot = bpy.data.objects.new("Titanium trefoil", curve)
bpy.context.collection.objects.link(knot)
knot.data.materials.append(chrome)
knot.rotation_euler = (0.7, 0.4, 0.2)

bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=0.59)
core = bpy.context.object
core.name = "Inner core"
core.data.materials.append(dark)
for polygon in core.data.polygons:
    polygon.use_smooth = True

for name, radius, thickness, angles, mat in [
    ("Ion orbit", 1.73, 0.015, (0.25, 0.6, 0), lime),
    ("Polar orbit", 1.57, 0.026, (1.05, -0.7, 0.2), matte),
    ("Inner ion ring", 0.69, 0.019, (0.8, 0.3, -0.2), lime),
]:
    bpy.ops.mesh.primitive_torus_add(
        major_segments=128,
        minor_segments=10,
        major_radius=radius,
        minor_radius=thickness,
        rotation=angles,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True

for angle in (0.2, 2.6, 4.5):
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=2, radius=0.045, location=(1.73 * math.cos(angle), 1.73 * math.sin(angle), 0.1)
    )
    bpy.context.object.name = "Orbit beacon"
    bpy.context.object.data.materials.append(lime)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(
    filepath=str(ROOT / "export" / "orbit-core.glb"),
    export_format="GLB",
    use_selection=True,
    export_apply=True,
)

world = bpy.context.scene.world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.06, 0.08, 0.07, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.35
for location, energy, size, color in [
    ((3, -3, 4), 1000, 5, (0.9, 1, 0.96)),
    ((-4, -1, 1), 1400, 3, (0.61, 0.91, 0.76)),
    ((1, 4, 2), 1600, 4, (0.92, 1, 0.94)),
]:
    light = bpy.data.lights.new("Studio reflection", "AREA")
    light.energy, light.size, light.color = energy, size, color
    obj = bpy.data.objects.new(light.name, light)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (-obj.location).to_track_quat("-Z", "Y").to_euler()

bpy.ops.object.camera_add(location=(3.4, -6, 3))
camera = bpy.context.object
camera.rotation_euler = (-Vector(camera.location)).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = 4.7
scene = bpy.context.scene
scene.camera = camera
scene.render.engine = "CYCLES"
scene.cycles.samples = 48
scene.cycles.use_denoising = True
print("RENDER_DEVICE:", enable_gpu(scene), flush=True)
scene.render.resolution_x = 1200
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = True
scene.render.filepath = str(ROOT / "previews" / "orbit-core.png")
scene.view_settings.view_transform = "AgX"
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "blender" / "orbit-core.blend"))
bpy.ops.render.render(write_still=True)
print("ORBIT_CORE_COMPLETE")
