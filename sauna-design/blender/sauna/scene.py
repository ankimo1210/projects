"""Scene-level setup: light materials, cameras, render settings."""

import math

import bpy

from . import materials

# Emitter strengths (Cycles emission, relative units). v3 = value of the same emitter in the accepted v3 model, None = new in v4.
# key: (kelvin, v4 strength, v3 strength, where)
LIGHTS = {
    "rest_cove_n": (2700, 8.0, 21.0, "休憩 北壁（寝台の頭上）の天井スリット"),
    "rest_cove_s": (2700, 6.5, 13.0, "休憩 南壁（リクライニング正面）の天井スリット"),
    "rest_cove_far": (2700, 8.0, 21.0, "休憩 延長区画の東壁の天井スリット"),
    "rest_plinth": (2700, 6.0, 11.0, "休憩 寝台の台座下"),
    "rest_toe": (2700, 9.0, None, "休憩 ヘッドボード足元の通路灯（新設・床向き）"),
    "rest_skirt": (2700, 9.0, None, "休憩 南壁と延長北壁の幅木下（新設・床向き）"),
    "rest_head": (2700, 3.0, None, "休憩 ヘッドボード席側の笠木下（新設・板面向き）"),
    "sauna_cove": (2700, 5.0, 21.0, "サ室3室 ベンチ背面壁の天井スリット"),
    "sauna_bench": (2700, 8.5, 24.0, "サ室3室 ベンチ下"),
    "sauna_heater": (2900, 140.0, 420.0, "サ室3室 ストーブ上の小型スポット"),
    "bath_cove": (2700, 16.0, 21.0, "浴室 石壁・炭酸泉・洗い場の天井スリット"),
    "bath_cove_soft": (2700, 9.0, 12.0, "浴室 西壁の天井スリット"),
    "bath_cove_wall": (2700, 3.5, 4.5, "浴室 北壁の光溝"),
    "bath_down": (2800, 80.0, 110.0, "浴室・洗い場・炭酸泉のダウンライト"),
    "bath_seat": (2700, 9.0, None, "浴室 造り付け席の座面下（新設・床向き）"),
    "service_down": (2900, 420.0, 420.0, "更衣・受付・裏方のダウンライト（変更なし）"),
}
# Lights that existed in v3 and are deleted in v4 (count, v3 strength).
REMOVED = [
    ("休憩 天井ダウンライト", 5, 110.0),
    ("メインサウナ 天井ダウンライト", 5, 110.0),
    ("セルフロウリュ 天井ダウンライト", 1, 110.0),
    ("高温ドライ 天井ダウンライト", 1, 110.0),
]
POOL_SPOT_W = {"v3": 75.0, "v4": 55.0}  # caustic spot lights over the three pools (watts)
TV_LEVEL = 0.22  # emission multiplier of the dummy picture (peak about 0.2, mean about 0.06)
# Camera exposure in stops. Interior views keep the v3 values so the lower light output is visible instead of being compensated.
EXPOSURE = {
    "main": (2.45, 2.45),
    "rest": (3.2, 3.2),
    "water": (3.0, 3.0),
    "bath": (3.0, None),
    "dry": (2.45, None),
    "self": (2.45, None),
    "overview": (1.6, 1.6),
    "plan": (1.6, 1.6),
}  # view: (v4, v3)


def light_materials():
    return {k: materials.light("light_" + k, v[0], v[1]) for k, v in LIGHTS.items()}


def lighting_record():
    return {
        "unit": "Cycles emission strength (relative); pool spots in watts; exposure in stops",
        "emitters": [
            {
                "key": k,
                "kelvin": v[0],
                "v4": v[1],
                "v3": v[2],
                "where": v[3],
                "ratio": (round(v[1] / v[2], 2) if v[2] else None),
            }
            for k, v in LIGHTS.items()
        ],
        "removed": [{"what": w, "count": n, "v3": s} for w, n, s in REMOVED],
        "pool_spot_watts": POOL_SPOT_W,
        "tv_emission_level": TV_LEVEL,
        "exposure_stops": {k: {"v4": v[0], "v3": v[1]} for k, v in EXPOSURE.items()},
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
