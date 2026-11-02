"""Rendert ein OBJ (aus den FreeCAD-Skripten, Einheit mm) mit Blender zu einem Vorschaubild.

Aufruf:  blender -b -P render_blender.py -- <modell.obj> <bild.png> [Hoehenwinkel] [Drehwinkel] [Breite] [Brennweite]
Optional ein Aufkleber auf einer Zylinderwand: Umgebungsvariablen AUFKLEBER und AUFKLEBER_MASS (siehe unten).
Materialien nach Teilnamen (Tabelle MATERIALS): Chrom, Blech, mattes und glaenzendes Schwarz, Leuchtband;
gedruckte Knaufteile matt mit Schichtlinien, der Button glaenzend, beide in der Farbe aus der .mtl;
sonst die Farbe aus der .mtl. Kamera und Licht richten sich nach der Groesse des Modells.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
OBJ, OUT = args[0], args[1]
ELEV = float(args[2]) if len(args) > 2 else 22.0      # wie das Produktfoto des Value
AZIM = float(args[3]) if len(args) > 3 else 0.0
WIDTH = int(args[4]) if len(args) > 4 else 1200
LENS = float(args[5]) if len(args) > 5 else 50.0      # Brennweite (mm, Kleinbild): klein = naeher, mehr Perspektive


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


glow = principled("Leuchtband", (1.0, 0.75, 0.35), rough=0.4)
glow.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1.0, 0.55, 0.15, 1.0)
glow.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 2.0
# Teilname enthaelt ... -> Material (erster Treffer gilt)
MATERIALS = [
    (("Deckel", "Drehteller", "Stange", "Huelse"), principled("Chrom", (0.9, 0.9, 0.92), metal=1.0, rough=0.08)),
    (("Teller",), principled("Blech_seidenmatt", (0.72, 0.73, 0.75), metal=1.0, rough=0.38)),   # nach "Drehteller"!
    (("Topf",), principled("Schwarz", (0.02, 0.02, 0.022), rough=0.55)),
    (("Griff",), principled("Schwarz_glaenzend", (0.01, 0.01, 0.01), rough=0.2, coat=0.6)),
    (("Leuchtband",), glow),
]
# Farbe aus der .mtl (je nach Farbwahl im Modell): gedruckte Knaufteile matt mit Schichtlinien,
# der gekaufte Button glaenzend (Spritzguss)
PRINTED = ("Knauf_",)
MOLDED = ("Button_", "Sanwa_Rand", "Sanwa_Kappe")
LAYER = 0.2                                    # Schichthoehe des Drucks in mm


def layer_lines(mat):
    """Feine waagrechte Rillen im Abstand LAYER als Bump (Objektkoordinaten sind mm)."""
    nt = mat.node_tree
    coord = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "Z"
    wave.inputs["Scale"].default_value = 0.314 / LAYER   # Blender: Periode = 0,314 / Scale
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.0001
    nt.links.new(coord.outputs["Object"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], nt.nodes["Principled BSDF"].inputs["Normal"])


for o in objs:
    mat = next((m for keys, m in MATERIALS if any(k in o.name for k in keys)), None)
    if mat:
        o.data.materials.clear()
        o.data.materials.append(mat)
    elif any(o.name.startswith(k) for k in PRINTED + MOLDED) and o.data.materials:
        m = o.data.materials[0]
        b = m.node_tree.nodes.get("Principled BSDF")
        if b:
            printed = o.name.startswith(PRINTED)
            b.inputs["Metallic"].default_value = 0.0
            b.inputs["Roughness"].default_value = 0.62 if printed else 0.28
            if "Coat Weight" in b.inputs:
                b.inputs["Coat Weight"].default_value = 0.0 if printed else 0.5
            if printed:
                layer_lines(m)
            # AKZENT="r,g,b" (linear): Unterteil und Button umfaerben, die Haube bleibt wie im Modell
            if os.environ.get("AKZENT") and not o.name.startswith("Knauf_Haube"):
                rgb = [float(v) for v in os.environ["AKZENT"].split(",")]
                b.inputs["Base Color"].default_value = (*rgb, 1.0)
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
# Objekte "Hilfe..." zaehlen nur fuer den Bildausschnitt (gleicher Massstab fuer mehrere Bilder), unsichtbar
for o in objs:
    if o.name.startswith("Hilfe"):
        o.hide_render = True

# Aufkleber (optional): PNG mit Transparenz auf eine senkrechte Zylinderwand, der Rundung folgend.
# AUFKLEBER=bild.png, AUFKLEBER_MASS="Radius,Hoehe-Mitte,Breite,Winkel" in mm/Grad (Winkel 0 = +x, -90 = vorn)
if os.environ.get("AUFKLEBER"):
    import bmesh
    img = bpy.data.images.load(os.environ["AUFKLEBER"])
    rad, zc, wid, ang = (float(v) for v in os.environ.get("AUFKLEBER_MASS", "70.2,22,30,-115").split(","))
    hgt = wid * img.size[1] / img.size[0]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new()
    nx = 24
    grid = []
    for j in (0, 1):
        row = []
        for i in range(nx + 1):
            s = (i / nx - 0.5) * wid
            phi = math.radians(ang) + s / rad             # von aussen gesehen links -> rechts
            row.append(bm.verts.new((rad * math.cos(phi) * 0.001, rad * math.sin(phi) * 0.001,
                                     (zc + (j - 0.5) * hgt) * 0.001)))
        grid.append(row)
    for i in range(nx):
        f = bm.faces.new((grid[0][i], grid[0][i + 1], grid[1][i + 1], grid[1][i]))
        for loop, (u, v) in zip(f.loops, ((i / nx, 0), ((i + 1) / nx, 0), ((i + 1) / nx, 1), (i / nx, 1))):
            loop[uv].uv = (u, v)
    mesh = bpy.data.meshes.new("Aufkleber")
    bm.to_mesh(mesh)
    sticker = bpy.data.objects.new("Aufkleber", mesh)
    scene.collection.objects.link(sticker)
    mat = bpy.data.materials.new("Aufkleber")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.35
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    sticker.data.materials.append(mat)

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
