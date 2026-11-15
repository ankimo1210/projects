"""Scene-level setup: light materials, cameras, render settings."""

import math

import bpy

from . import materials


def light_materials():
    return {
        "cove": materials.light("light_cove", 2700, 21.0),
        "cove_soft": materials.light("light_cove_soft", 2700, 12.0),
        "cove_mid": materials.light("light_cove_mid", 2700, 13.0),
        "cove_wall": materials.light("light_cove_wall", 2700, 4.5),
        "bench": materials.light("light_bench", 2700, 24.0),
        "down_dim": materials.light("light_down_dim", 2800, 110.0),
        "down": materials.light("light_down", 2900, 420.0),
        "plinth": materials.light("light_plinth", 2700, 11.0),
        "service": materials.light("light_service", 3000, 6.0),
    }


def add_overview_camera(name, loc, target, lens=35.0, ortho=None, coll=None):
    from mathutils import Vector

    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_width = 36.0
    cam.clip_end = 200
    if ortho:
        cam.type = "ORTHO"
        cam.ortho_scale = ortho
    ob = bpy.data.objects.new(name, cam)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def add_camera(name, loc, target, lens=24.0, shift_y=0.0, shift_x=0.0, coll=None):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_width = 36.0
    cam.shift_y = shift_y
    cam.shift_x = shift_x
    cam.clip_start = 0.05
    cam.clip_end = 100
    ob = bpy.data.objects.new(name, cam)
    ob.location = loc
    dx, dy = target[0] - loc[0], target[1] - loc[1]
    ob.rotation_euler = (math.pi / 2, 0.0, math.atan2(-dx, dy))
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def configure_render(
    scene,
    res_x=2400,
    res_y=1600,
    samples=1024,
    threshold=0.015,
    exposure=0.0,
    look="AgX - Medium High Contrast",
    white_balance=4300.0,
    ambient=0.0,
):
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == "OPTIX"
    c = scene.cycles
    c.device = "GPU"
    c.samples = samples
    c.use_adaptive_sampling = True
    c.adaptive_threshold = threshold
    c.adaptive_min_samples = 64
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    c.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    try:
        c.denoising_prefilter = "ACCURATE"
        c.denoising_use_gpu = True
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
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = look
    scene.view_settings.exposure = exposure
    scene.display_settings.display_device = "sRGB"
    vs = scene.view_settings
    try:  # camera white balance: keep the 2600 K sources amber without going red
        vs.use_white_balance = True
        vs.white_balance_temperature = white_balance
        vs.white_balance_tint = 10.0
    except Exception as e:
        print("white balance unavailable:", e)
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (1.0, 0.66, 0.38, 1) if ambient > 0 else (0, 0, 0, 1)
        bg.inputs[1].default_value = ambient
