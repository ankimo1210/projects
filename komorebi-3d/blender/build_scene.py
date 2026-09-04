"""Komorebi 3D: a miniature coffee shop after the rain.

Run with Blender --background --python build_scene.py.
All geometry is procedural. No downloaded models or textures are used.
"""

import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parents[1] / "assets"
for folder in ("blender", "export", "previews"):
    (OUT / folder).mkdir(parents=True, exist_ok=True)
random.seed(19)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def material(name, color, roughness=0.5, metallic=0, emission=0, transmission=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    p = mat.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = roughness
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Transmission Weight"].default_value = transmission
    p.inputs["Emission Color"].default_value = (*color, 1)
    p.inputs["Emission Strength"].default_value = emission
    return mat


cream = material("Warm ivory plaster", (0.74, 0.64, 0.44), 0.83)
wood = material("Honey oak", (0.24, 0.10, 0.042), 0.4)
wood_light = material("Oak endgrain", (0.49, 0.26, 0.11), 0.45)
teal = material("Petrol enamel", (0.027, 0.19, 0.19), 0.35, 0.25)
roof_mat = material("Patinated copper roof", (0.04, 0.19, 0.20), 0.4, 0.5)
roof_edge = material("Standing copper seams", (0.07, 0.29, 0.29), 0.3, 0.55)
terracotta = material("Burnt orange canvas", (0.70, 0.19, 0.075), 0.8)
canvas = material("Linen canvas", (0.90, 0.76, 0.50), 0.9)
black = material("Black painted steel", (0.019, 0.03, 0.035), 0.3, 0.65)
brass = material("Brushed brass", (0.65, 0.38, 0.105), 0.25, 0.8)
white = material("Porcelain", (0.9, 0.84, 0.65), 0.24)
coffee = material("Espresso", (0.035, 0.011, 0.005), 0.16)
leaf_mats = [
    material("Leaf " + str(i), c, 0.55)
    for i, c in enumerate([(0.055, 0.23, 0.095), (0.12, 0.36, 0.14), (0.22, 0.42, 0.12)])
]
soil = material("Potting soil", (0.055, 0.023, 0.012), 1)
potmat = material("Unglazed clay", (0.51, 0.17, 0.08), 0.87)
stone = material("Concrete base", (0.23, 0.29, 0.31), 0.83)
pavers = [
    material("Sidewalk " + str(i), (0.38 + i * 0.018, 0.41 + i * 0.014, 0.40 + i * 0.01), 0.62)
    for i in range(5)
]
asphalt = material("Wet asphalt", (0.035, 0.059, 0.075), 0.23)
puddle = material("Water on stone", (0.09, 0.16, 0.18), 0.055, 0.45)
paint = material("Weathered road paint", (0.69, 0.68, 0.50), 0.48)
glow = material("Warm luminous glass", (1, 0.55, 0.18), 0.25, emission=3)
glass = material("Window glass", (0.72, 0.84, 0.79), 0.12, transmission=1)
# Thin architectural glass with deliberately restrained reflections at this scale.
glass_bsdf = glass.node_tree.nodes.get("Principled BSDF")
glass_bsdf.inputs["IOR"].default_value = 1.12
glass_bsdf.inputs["Base Color"].default_value = (0.95, 0.98, 0.97, 1)
glass_bsdf.inputs["Roughness"].default_value = 0.025
chalk = material("Chalk", (0.9, 0.83, 0.63), 0.75, emission=0.1)
chalkboard = material("Chalkboard", (0.026, 0.058, 0.056), 0.88)


def finish(obj, name, mat):
    obj.name = name
    if mat:
        obj.data.materials.append(mat)
    return obj


def cube(name, loc, size, mat, bevel=0.025):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new("Soft manufactured edges", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    return finish(obj, name, mat)


def cylinder(name, loc, radius, depth, mat, vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    obj = finish(bpy.context.object, name, mat)
    mod = obj.modifiers.new("Edge highlight", "BEVEL")
    mod.width = 0.012
    mod.segments = 2
    obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return obj


def sphere(name, loc, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, location=loc)
    obj = bpy.context.object
    obj.scale = scale
    for p in obj.data.polygons:
        p.use_smooth = True
    return finish(obj, name, mat)


def rod(name, a, b, radius, mat):
    a, b = Vector(a), Vector(b)
    obj = cylinder(name, (a + b) / 2, radius, (b - a).length, mat, 16)
    obj.rotation_euler = (b - a).to_track_quat("Z", "Y").to_euler()
    return obj


def curve(name, points, radius, mat):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = radius
    data.bevel_resolution = 3
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for p, co in zip(spline.bezier_points, points, strict=True):
        p.co = co
        p.handle_left_type = "AUTO"
        p.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return finish(obj, name, mat)


def torus(name, loc, major, minor, mat, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major,
        minor_radius=minor,
        major_segments=40,
        minor_segments=10,
        location=loc,
        rotation=rotation,
    )
    obj = finish(bpy.context.object, name, mat)
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def text(name, body, loc, size, mat, rotation=(math.pi / 2, 0, 0)):
    data = bpy.data.curves.new(name, "FONT")
    data.body = body
    data.align_x = "CENTER"
    data.align_y = "CENTER"
    data.size = size
    data.extrude = 0.0015
    data.space_character = 1.14
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rotation
    return finish(obj, name, mat)


def area(name, loc, target, power, color, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.color = color
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj


def point(name, loc, power, color, radius=0.15):
    data = bpy.data.lights.new(name, "POINT")
    data.energy = power
    data.color = color
    data.shadow_soft_size = radius
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = loc


# A cropped city block, with a raised sidewalk and rain-darkened road.
cube("Floating concrete city block", (0, 0, 0.01), (7, 6.2, 0.44), stone, 0.15)
cube("Wet road", (0, -2.23, 0.242), (6.85, 1.58, 0.09), asphalt, 0.02)
for ix in range(14):
    for iy in range(9):
        x = -3.19 + ix * 0.49
        y = -1.18 + iy * 0.48
        cube(
            "Individual sidewalk tile",
            (x, y, 0.31),
            (0.466, 0.454, 0.12),
            random.choice(pavers),
            0.018,
        )
for x in [-3.14 + i * 0.49 for i in range(14)]:
    cube("Kerbstone", (x, -1.475, 0.30), (0.463, 0.18, 0.21), pavers[3], 0.02)
for x in [-2.85, -2.38, -1.91]:
    cube("Crosswalk marking", (x, -2.29, 0.293), (0.27, 1.10, 0.009), paint, 0.006)
for x in [0, 1.2, 2.4]:
    cube("Road edge stripe", (x, -2.85, 0.293), (0.65, 0.047, 0.009), paint, 0.005)
for x, y, sx, sy in [
    (1.1, -2.08, 0.62, 0.2),
    (-0.8, -1.76, 0.38, 0.15),
    (2.3, -0.94, 0.28, 0.1),
    (0.15, -2.64, 0.25, 0.13),
]:
    sphere("Shallow rain puddle", (x, y, 0.297 if y < -1.5 else 0.376), (sx, sy, 0.005), puddle)

# The walls are built around actual openings, with a furnished interior.
floor = 0.38
cube("Shop oak floor", (0, 0.7, 0.44), (3.58, 2.4, 0.12), wood_light)
cube("Back plaster wall", (0, 1.88, 1.70), (3.65, 0.13, 2.6), cream)
cube("Right plaster wall", (1.78, 0.70, 1.70), (0.14, 2.4, 2.6), cream)
cube("Left plaster wall", (-1.78, 0.70, 1.70), (0.14, 2.4, 2.6), cream)
cube("Front sill wall", (-0.58, -0.49, 0.84), (2.38, 0.16, 0.77), teal)
cube("Front lintel", (0, -0.49, 2.78), (3.65, 0.18, 0.38), cream)
for x, width in [(-1.74, 0.14), (0.58, 0.16), (1.72, 0.16)]:
    cube("Oak facade post", (x, -0.60, 1.60), (width, 0.17, 2.35), wood)
for x in [-1.64 + i * 0.185 for i in range(12)]:
    cube("Facade lower panelling", (x, -0.591, 0.84), (0.022, 0.017, 0.62), roof_edge, 0.004)

# Window, doorway, and their joinery.
cube("Large clear front pane", (-0.59, -0.51, 1.9), (2.14, 0.016, 1.28), glass, 0.0)
for x in [-1.65, -0.58, 0.49]:
    cube("Front window mullion", (x, -0.615, 1.91), (0.065, 0.07, 1.47), wood, 0.01)
for z in [1.19, 2.62]:
    cube("Front window horizontal", (-0.58, -0.615, z), (2.25, 0.12, 0.075), wood, 0.012)
cube("Deep oak window ledge", (-0.58, -0.72, 1.19), (2.41, 0.43, 0.095), wood_light)
cube("Door enamel lower panel", (1.13, -0.61, 0.90), (0.91, 0.11, 0.88), teal)
cube("Door glass", (1.13, -0.60, 1.95), (0.85, 0.014, 1.23), glass, 0)
for x in [0.68, 1.57]:
    cube("Door stile", (x, -0.66, 1.56), (0.067, 0.08, 2.08), wood, 0.01)
for z in [0.51, 1.34, 2.58]:
    cube("Door rail", (1.13, -0.66, z), (0.95, 0.08, 0.075), wood, 0.01)
rod("Brass door handle", (1.45, -0.75, 1.26), (1.45, -0.75, 1.53), 0.022, brass)
cube("Entry stone step", (1.13, -0.88, 0.43), (1.02, 0.56, 0.11), pavers[4])
cube("Welcome doormat", (1.13, -1.02, 0.498), (0.65, 0.26, 0.017), wood, 0.015)

cube("Side window dark inset", (1.862, 0.73, 1.86), (0.02, 1.29, 1.11), teal)
for y in [0.07, 1.39]:
    cube("Side window jamb", (1.89, y, 1.86), (0.08, 0.075, 1.25), wood)
for z in [1.23, 2.48]:
    cube("Side window lintel", (1.89, 0.73, z), (0.08, 1.40, 0.075), wood)
for y in [0.30, 0.57, 0.84, 1.11]:
    cube("Side shutter batten", (1.92, y, 1.86), (0.045, 0.17, 1.10), wood_light, 0.01)

# Interior counter, espresso machine, back shelves, jars and cups.
cube("Bar counter body", (-0.54, 0.71, 1.01), (2.18, 0.55, 1.02), teal)
cube("Bar oak top", (-0.54, 0.70, 1.55), (2.30, 0.68, 0.09), wood_light)
cube("Espresso machine", (-0.95, 0.68, 1.79), (0.72, 0.37, 0.40), black, 0.045)
cube("Espresso machine brass face", (-0.95, 0.48, 1.80), (0.61, 0.025, 0.22), brass)
for x in [-1.11, -0.80]:
    cylinder("Cup on coffee machine", (x, 0.68, 2.03), 0.07, 0.11, white)
    rod("Espresso portafilter", (x, 0.45, 1.77), (x, 0.29, 1.77), 0.025, black)
for z in [1.80, 2.36]:
    cube("Back shelf", (-0.35, 1.66, z), (2.44, 0.32, 0.07), wood_light)
    for i in range(8):
        x = -1.39 + i * 0.29
        cylinder(
            "Shelf ceramic jar", (x, 1.65, z + 0.14), 0.079, 0.21, white if i % 3 else terracotta
        )
        cylinder("Jar lid", (x, 1.65, z + 0.255), 0.084, 0.025, wood)
for x in [-0.85, 0.3]:
    rod("Pendant cable", (x, 0.30, 2.91), (x, 0.30, 2.42), 0.012, black)
    bpy.ops.mesh.primitive_cone_add(
        vertices=32, radius1=0.20, radius2=0.075, depth=0.14, location=(x, 0.30, 2.40)
    )
    finish(bpy.context.object, "Brass pendant shade", brass)
    sphere("Pendant glowing bulb", (x, 0.30, 2.31), (0.074, 0.074, 0.075), glow)
    point("Pendant pool of light", (x, 0.30, 2.28), 30, (1, 0.54, 0.22))
area("Warm interior light", (0, 0.0, 2.58), (0, 1.1, 1.2), 70, (1, 0.65, 0.32), 1.6)

# Two genuinely sloped copper roof planes and visible raised seams.
ridge_y = 0.69
ridge_z = 3.70
eave_z = 3.01
for y in [-0.90, 2.28]:
    length = math.hypot(y - ridge_y, ridge_z - eave_z)
    angle = math.atan2(ridge_z - eave_z, abs(y - ridge_y)) * (1 if y < ridge_y else -1)
    roof = cube(
        "Sloping copper roof",
        (0, (y + ridge_y) / 2, (ridge_z + eave_z) / 2),
        (4.16, length, 0.10),
        roof_mat,
        0.02,
    )
    roof.rotation_euler.x = angle
    for x in [-2.0 + i * 0.25 for i in range(17)]:
        rod(
            "Raised roof seam",
            (x, y, eave_z + 0.058),
            (x, ridge_y, ridge_z + 0.058),
            0.016,
            roof_edge,
        )
    rod("Eave metal flashing", (-2.13, y, eave_z), (2.13, y, eave_z), 0.048, roof_edge)
rod(
    "Ridge cap", (-2.12, ridge_y, ridge_z + 0.06), (2.12, ridge_y, ridge_z + 0.06), 0.055, roof_edge
)
# Fill each triangular gable beneath the roof; keep the internal loft enclosed.
for x in [-1.78, 1.78]:
    mesh = bpy.data.meshes.new("Gable triangle")
    mesh.from_pydata([(x, -0.5, 3.0), (x, 1.88, 3.0), (x, 0.69, 3.64)], [], [(0, 1, 2)])
    obj = bpy.data.objects.new("Plastered roof gable", mesh)
    bpy.context.collection.objects.link(obj)
    finish(obj, obj.name, cream)
cube("Brick chimney", (-1.08, 1.36, 3.79), (0.38, 0.39, 0.74), terracotta)
cube("Chimney cap", (-1.08, 1.36, 4.17), (0.51, 0.51, 0.10), stone)
for z in [3.53, 3.71, 3.89, 4.07]:
    cube("Chimney mortar joint", (-1.08, 1.153, z), (0.39, 0.012, 0.018), canvas, 0.003)

cube("Shop sign wooden surround", (-0.53, -1.11, 2.91), (2.35, 0.13, 0.39), wood)
cube("Shop sign enamel face", (-0.53, -1.187, 2.91), (2.23, 0.025, 0.29), teal, 0.018)
text("Shop name", "K O M O R E B I", (-0.53, -1.206, 2.91), 0.188, canvas)
for x in [-1.49, 0.43]:
    rod("Shop sign mounting bracket", (x, -0.56, 2.94), (x, -1.09, 2.94), 0.025, black)

# Striped retractable awning below the sign.
for i in range(12):
    x = -1.72 + i * 0.2
    obj = cube(
        "Awning stripe",
        (x, -0.965, 2.62),
        (0.199, 0.81, 0.045),
        canvas if i % 2 else terracotta,
        0.007,
    )
    obj.rotation_euler.x = 0.22
    cube(
        "Awning hanging valance",
        (x, -1.36, 2.46),
        (0.199, 0.035, 0.18),
        canvas if i % 2 else terracotta,
        0.008,
    )
for x in [-1.83, 0.59]:
    rod("Awning support", (x, -0.66, 2.0), (x, -1.34, 2.50), 0.018, black)


# Planters with individually oriented leaves.
def plant(x, y, z, scale=1):
    bpy.ops.mesh.primitive_cone_add(
        vertices=24,
        radius1=0.18 * scale,
        radius2=0.24 * scale,
        depth=0.40 * scale,
        location=(x, y, z + 0.2 * scale),
    )
    finish(bpy.context.object, "Terracotta planter", potmat)
    torus("Planter rolled lip", (x, y, z + 0.39 * scale), 0.233 * scale, 0.023 * scale, potmat)
    cylinder("Visible soil", (x, y, z + 0.395 * scale), 0.214 * scale, 0.013, soil)
    for i in range(11):
        angle = i * 2.399
        h = random.uniform(0.35, 0.77) * scale
        spread = random.uniform(0.11, 0.32) * scale
        end = (x + math.cos(angle) * spread, y + math.sin(angle) * spread, z + 0.38 * scale + h)
        rod("Plant stem", (x, y, z + 0.37 * scale), end, 0.011 * scale, leaf_mats[0])
        for k in [0.52, 0.78, 1]:
            loc = (
                x + math.cos(angle) * spread * k,
                y + math.sin(angle) * spread * k,
                z + 0.38 * scale + h * k,
            )
            obj = sphere(
                "Individual leaf",
                loc,
                (0.055 * scale, 0.15 * scale, 0.025 * scale),
                leaf_mats[i % 3],
            )
            obj.rotation_euler = (0.3, i * 0.4, angle)


plant(-1.96, -0.65, 0.38, 0.82)
plant(1.87, -0.83, 0.38, 0.8)
plant(2.32, 1.31, 0.38, 1.34)
plant(-1.35, -0.73, 1.24, 0.29)

# Pavement cafe table, bent steel chairs, and two tiny coffees.
tx, ty = -2.64, 0.13
cylinder("Cafe table top", (tx, ty, 1.07), 0.43, 0.06, wood_light)
rod("Cafe table pedestal", (tx, ty, 0.42), (tx, ty, 1.05), 0.047, black)
for a in [0, 2.094, 4.188]:
    rod(
        "Cafe table foot",
        (tx, ty, 0.46),
        (tx + 0.28 * math.cos(a), ty + 0.28 * math.sin(a), 0.40),
        0.023,
        black,
    )
for dx, dy in [(-0.12, -0.05), (0.15, 0.07)]:
    cylinder("Saucer", (tx + dx, ty + dy, 1.115), 0.10, 0.013, white)
    cylinder("Coffee cup", (tx + dx, ty + dy, 1.17), 0.061, 0.09, white)
    cylinder("Coffee visible in cup", (tx + dx, ty + dy, 1.218), 0.047, 0.005, coffee)
    torus("Cup handle", (tx + dx + 0.067, ty + dy, 1.171), 0.032, 0.011, white, (math.pi / 2, 0, 0))


def chair(x, y, angle):
    def p(dx, dy, z):
        return (
            x + dx * math.cos(angle) - dy * math.sin(angle),
            y + dx * math.sin(angle) + dy * math.cos(angle),
            z,
        )

    seat = cube("Chair oak seat", p(0, 0, 0.72), (0.39, 0.40, 0.055), wood_light)
    seat.rotation_euler.z = angle
    for dx in [-0.15, 0.15]:
        for dy in [-0.14, 0.14]:
            rod("Chair steel leg", p(dx, dy, 0.70), p(dx * 1.24, dy * 1.24, 0.38), 0.014, black)
        rod("Chair back upright", p(dx, 0.15, 0.62), p(dx, 0.17, 1.16), 0.018, black)
    back = cube("Chair curved oak back", p(0, 0.175, 1.08), (0.36, 0.043, 0.16), wood_light)
    back.rotation_euler.z = angle


chair(-2.68, 0.89, 0)
chair(-2.69, -0.62, math.pi)

# Side bench and an A-frame menu.
for y in [0.00, 0.145, 0.29]:
    cube("Bench seat slat", (2.40, y, 0.80), (0.86, 0.105, 0.075), wood_light)
for x in [2.08, 2.71]:
    for y in [0.00, 0.29]:
        rod("Bench leg", (x, y, 0.40), (x, y, 0.76), 0.026, black)
cube("Menu A-frame oak panel", (0.17, -1.18, 0.87), (0.52, 0.085, 0.73), wood)
cube("Menu blackboard", (0.17, -1.228, 0.88), (0.43, 0.02, 0.61), chalkboard, 0.012)
for x in [-0.07, 0.41]:
    rod("Menu front leg", (x, -1.25, 0.38), (x, -1.20, 1.30), 0.025, wood)
    rod("Menu rear leg", (x, -0.82, 0.38), (x, -1.20, 1.30), 0.025, wood)
text("Menu heading", "COFFEE", (0.17, -1.245, 1.08), 0.083, chalk)
text("Menu drawing", "~ ~ ~", (0.17, -1.245, 0.92), 0.084, chalk)
text("Menu open", "OPEN", (0.17, -1.245, 0.75), 0.095, chalk)
text("Menu hours", "8:00 - 18:00", (0.17, -1.245, 0.61), 0.042, chalk)

# Street lantern and festoon cable with individual bulbs.
lx, ly = 2.85, -1.05
cylinder("Streetlamp plinth", (lx, ly, 0.45), 0.12, 0.13, black)
rod("Streetlamp post", (lx, ly, 0.49), (lx, ly, 3.55), 0.041, black)
curve(
    "Streetlamp curved neck",
    [(lx, ly, 3.50), (lx, ly, 3.78), (lx - 0.20, ly, 3.92), (lx - 0.43, ly, 3.78)],
    0.034,
    black,
)
bpy.ops.mesh.primitive_cone_add(
    vertices=32, radius1=0.22, radius2=0.07, depth=0.17, location=(lx - 0.43, ly, 3.69)
)
finish(bpy.context.object, "Streetlamp shade", teal)
sphere("Streetlamp light", (lx - 0.43, ly, 3.59), (0.125, 0.125, 0.045), glow)
point("Warm pool on pavement", (lx - 0.43, ly, 3.49), 65, (1, 0.53, 0.20), 0.22)
points = [(-1.84, -1.40, 2.39), (-0.6, -1.43, 2.30), (0.7, -1.38, 2.39), (2.85, -1.05, 3.0)]
curve("Cafe festoon cable", points, 0.012, black)
for i in range(13):
    t = i / 12
    x = -1.84 + 4.69 * t
    y = -1.40 + 0.35 * t
    z = 2.39 + 0.61 * t - 0.31 * math.sin(math.pi * t)
    rod("Festoon bulb socket", (x, y, z), (x, y, z - 0.055), 0.022, black)
    sphere("Festoon glowing bulb", (x, y, z - 0.09), (0.047, 0.047, 0.061), glow)

# A city bicycle parked alongside the back of the building.
by = 2.53
wheel_x = [-0.95, 0.36]
wz = 0.80
for x in wheel_x:
    torus("Bicycle rubber tire", (x, by, wz), 0.37, 0.039, black, (math.pi / 2, 0, 0))
    torus("Bicycle wheel rim", (x, by - 0.01, wz), 0.335, 0.012, brass, (math.pi / 2, 0, 0))
    for i in range(12):
        a = i * math.tau / 12
        rod(
            "Bicycle spoke",
            (x, by - 0.018, wz),
            (x + 0.33 * math.cos(a), by - 0.018, wz + 0.33 * math.sin(a)),
            0.004,
            brass,
        )
A = (-0.95, by, 0.80)
B = (-0.35, by, 0.77)
C = (-0.53, by, 1.37)
D = (0.15, by, 1.37)
E = (0.36, by, 0.80)
for a, b in [(A, B), (A, C), (B, C), (C, D), (D, B), (D, E)]:
    rod("Bicycle frame tube", a, b, 0.026, terracotta)
rod("Bicycle seatpost", C, (-0.56, by, 1.51), 0.022, black)
cube("Bicycle leather saddle", (-0.57, by, 1.53), (0.25, 0.13, 0.061), wood)
rod("Bicycle handlebar stem", D, (0.19, by, 1.56), 0.022, brass)
rod("Bicycle handlebar", (0.19, by - 0.19, 1.56), (0.19, by + 0.19, 1.56), 0.021, black)
torus("Bicycle crank", B, 0.12, 0.017, black, (math.pi / 2, 0, 0))
rod("Bicycle stand", (-0.44, by, 0.77), (-0.49, by - 0.20, 0.38), 0.015, black)

# Drain grate and sparse weeds make object contact easier to inspect.
cube("Drain recess", (2.38, -1.32, 0.378), (0.53, 0.20, 0.016), black, 0.015)
for x in [2.16 + i * 0.065 for i in range(8)]:
    cube("Drain grate bar", (x, -1.32, 0.390), (0.018, 0.18, 0.014), stone, 0.003)
for x, y in [(-3.02, 1.85), (2.83, 2.4), (-1.97, 2.6)]:
    for _i in range(5):
        rod(
            "Small sidewalk weed",
            (x, y, 0.375),
            (
                x + random.uniform(-0.08, 0.08),
                y + random.uniform(-0.08, 0.08),
                random.uniform(0.44, 0.59),
            ),
            0.009,
            leaf_mats[1],
        )

# Studio dusk lighting: cool ambient, warm late sun, interior practicals.
backdrop = material("Backdrop", (0.055, 0.085, 0.11), 0.9)
cube("Studio ground", (0, 0, -0.35), (200, 200, 0.1), backdrop, 0.0)
scene = bpy.context.scene
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.13, 0.21, 0.32, 1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.30
area("Large dusk softbox", (1, -3, 8), (0, 0, 0), 750, (0.64, 0.79, 1), 7)
area("Low golden sun", (-5, -1, 5), (0, 0, 1), 950, (1, 0.59, 0.30), 4)
area("Cool rim light", (3, 5, 6), (0, 0, 1), 1100, (0.33, 0.62, 1), 5)

bpy.ops.object.camera_add(location=(8.4, -11.5, 8.0))
cam = bpy.context.object
cam.name = "Camera - coffee shop hero"
cam.rotation_euler = (Vector((0, 0.08, 1.55)) - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.type = "ORTHO"
cam.data.ortho_scale = 9.15
cam.data.lens = 48
scene.camera = cam
scene.render.engine = "CYCLES"
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
scene.cycles.transparent_max_bounces = 8
device = "CPU"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "CUDA"
    prefs.get_devices()
    usable = [d for d in prefs.devices if d.type == "CUDA"]
    if usable:
        for d in prefs.devices:
            d.use = d.type == "CUDA"
        scene.cycles.device = "GPU"
        device = ", ".join(d.name for d in usable)
except Exception as exc:
    print("GPU unavailable, CPU fallback:", exc)
print("RENDER_DEVICE:", device, flush=True)
scene.render.resolution_x = 1400
scene.render.resolution_y = 1400
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "previews" / "komorebi.png")
scene.view_settings.view_transform = "AgX"
scene.render.film_transparent = False

for screen in bpy.data.screens:
    for editor in screen.areas:
        if editor.type == "VIEW_3D":
            editor.spaces.active.region_3d.view_perspective = "CAMERA"
            editor.spaces.active.clip_end = 300

# Save editable scene before rendering, so a render interruption loses no work.
scene.render.use_file_extension = True
scene.render.filepath = str(OUT / "previews" / "komorebi.png")
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "blender" / "komorebi.blend"))
bpy.ops.render.render(write_still=True)
# Export a portable scene with the studio backdrop excluded.
bpy.ops.object.select_all(action="DESELECT")
for obj in scene.objects:
    obj.select_set(obj.name != "Studio ground")
bpy.ops.export_scene.gltf(
    filepath=str(OUT / "export" / "komorebi.glb"),
    export_format="GLB",
    use_selection=True,
    export_apply=True,
    export_cameras=True,
    export_lights=True,
)
summary = {
    "blender": bpy.app.version_string,
    "objects": len(scene.objects),
    "meshes": sum(o.type == "MESH" for o in scene.objects),
    "materials": len(bpy.data.materials),
    "resolution": [1400, 1400],
    "samples": 64,
    "render_device": device,
    "seed": 19,
    "construction": "Procedural geometry; no external assets",
    "purpose": "Editable Blender scene for the Komorebi 3D project",
    "visual_revision": "Moved sign in front of eave; reduced glass reflections; filled gables",
}
(OUT / "previews" / "verification.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print("SCENE_COMPLETE", json.dumps(summary), flush=True)
