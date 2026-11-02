"""Rendert ein OBJ (aus den FreeCAD-Skripten, Einheit mm) mit Blender zu einem Vorschaubild.

Aufruf:  blender -b -P render_blender.py -- <modell.obj> <bild.png> [Hoehenwinkel] [Drehwinkel] [Breite] [Brennweite]
Materialien nach Teilnamen: Chrom fuer Deckel/Drehteller/Stange/Huelse, mattes Schwarz fuer den Topf,
glaenzendes Schwarz fuer den Griff,
sonst die Farbe aus der .mtl. Kamera und Licht richten sich nach der Groesse des Modells.
"""
import math
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
OBJ, OUT = args[0], args[1]
ELEV = float(args[2]) if len(args) > 2 else 22.0      # wie das Produktfoto des Value
AZIM = float(args[3]) if len(args) > 3 else 0.0
WIDTH = int(args[4]) if len(args) > 4 else 1200
LENS = float(args[5]) if len(args) > 5 else 50.0      # Brennweite (mm, Kleinbild): klein = naeher, mehr Perspektive

CHROME = ("Deckel", "Drehteller", "Stange", "Huelse")
BLACK = ("Topf",)
GLOSSY_BLACK = ("Griff",)
ORANGE = ("Button_Kappe",)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
bpy.ops.wm.obj_import(filepath=OBJ, forward_axis="Y", up_axis="Z")
objs = [o for o in scene.objects if o.type == "MESH"]
for o in objs:
    o.scale = (0.001, 0.001, 0.001)          # mm -> m
bpy.context.view_layer.update()


def principled(name, color, metal=0.0, rough=0.5, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
    return m


chrome = principled("Chrom", (0.9, 0.9, 0.92), metal=1.0, rough=0.08)
black = principled("Schwarz", (0.02, 0.02, 0.022), rough=0.55)
glossy = principled("Schwarz_glaenzend", (0.01, 0.01, 0.01), rough=0.2, coat=0.6)
orange = principled("Orange", (1.0, 0.28, 0.0), rough=0.3, coat=0.5)
for o in objs:
    mat = chrome if any(k in o.name for k in CHROME) else black if any(k in o.name for k in BLACK) \
        else glossy if any(k in o.name for k in GLOSSY_BLACK) \
        else orange if any(k in o.name for k in ORANGE) else None
    if mat:
        o.data.materials.clear()
        o.data.materials.append(mat)
    for p in o.data.polygons:
        p.use_smooth = True
    try:
        o.modifiers.new("Kanten", "EDGE_SPLIT").split_angle = math.radians(35)
    except Exception:
        pass

# Groesse des Modells
pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center, size = (lo + hi) / 2, (hi - lo).length

# Studio wie beim Produktfoto: weisser Hintergrund ohne Boden, weiche Flaechenlichter,
# dunkle Flaechen neben dem Modell (fuer die Kamera unsichtbar), damit Chrom nach Chrom aussieht
def light(offset, energy, sz):
    bpy.ops.object.light_add(type="AREA", location=center + Vector(offset) * size)
    lamp = bpy.context.object
    lamp.data.energy = energy * size * size
    lamp.data.size = sz * size
    lamp.rotation_euler = (center - lamp.location).to_track_quat("-Z", "Y").to_euler()


light((-0.8, -1.4, 1.6), 90, 1.5)       # Hauptlicht vorn links oben
light((1.5, -0.6, 0.9), 35, 1.2)        # Aufheller rechts
light((0.0, 1.6, 1.4), 45, 1.5)         # Kante von hinten
dark = principled("Abschatter", (0.0, 0.0, 0.0), rough=1.0)
for loc, rot in (((-2.2, 0.4, 0.3), (0, math.radians(90), 0)), ((2.2, 0.4, 0.3), (0, math.radians(90), 0)),
                 ((0, 0, -1.2), (0, 0, 0))):
    bpy.ops.mesh.primitive_plane_add(size=size * 2.5, location=center + Vector(loc) * size, rotation=rot)
    flag = bpy.context.object
    flag.data.materials.append(dark)
    flag.visible_camera = False
world = bpy.data.worlds.new("Welt")
scene.world = world
world.use_nodes = True
nt = world.node_tree
env = nt.nodes["Background"]
env.inputs["Color"].default_value = (0.8, 0.82, 0.85, 1.0)
env.inputs["Strength"].default_value = 0.35
white = nt.nodes.new("ShaderNodeBackground")
white.inputs["Color"].default_value = (1, 1, 1, 1)
white.inputs["Strength"].default_value = 1.0
mix = nt.nodes.new("ShaderNodeMixShader")
path = nt.nodes.new("ShaderNodeLightPath")
nt.links.new(path.outputs["Is Camera Ray"], mix.inputs[0])
nt.links.new(env.outputs[0], mix.inputs[1])
nt.links.new(white.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], nt.nodes["World Output"].inputs["Surface"])

# Kamera: Hoehen- und Drehwinkel, Abstand so, dass das Modell das Bild fuellt
bpy.ops.object.camera_add()
cam = bpy.context.object
scene.camera = cam
cam.data.lens = LENS
e, a = math.radians(ELEV), math.radians(AZIM)
half = 0.68 * max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z)       # halbe Bildbreite mit Rand (Perspektive)
dist = half / math.tan(cam.data.angle / 2)
cam.location = center + Vector((math.cos(e) * math.sin(a), -math.cos(e) * math.cos(a), math.sin(e))) * dist
aim = center - Vector((0, 0, 0.12 * (hi.z - lo.z)))           # etwas tiefer zielen: die Naehe zieht nach oben
cam.rotation_euler = (aim - cam.location).to_track_quat("-Z", "Y").to_euler()

scene.render.engine = "CYCLES"
scene.cycles.samples = 96
scene.cycles.use_denoising = True
scene.render.resolution_x = WIDTH
scene.render.resolution_y = WIDTH
scene.render.film_transparent = False
scene.view_settings.view_transform = "Standard"     # Weiss bleibt weiss, Schwarz bleibt schwarz
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("gerendert", OUT)
