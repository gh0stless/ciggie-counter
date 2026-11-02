"""Drehascher "Value" als Referenzmodell (FreeCAD 1.x) - zum Anpassen des Knaufs.

Gemessen: Ø 140 mm, Korpus 60 mm hoch, Stempel 50 mm ueber dem Deckel (davon 30 mm Griff);
Deckel aus Silberblech ca. 17 mm hoch, Aussenring ca. 12 mm, Innenring Ø ca. 100 mm 10 mm tiefer,
darin ein Drehteller mit drei geschwungenen Armen zur Mitte, leicht gewoelbt.
Alles andere ist nach Foto geschaetzt und steht unten als Konstante.
Aufruf: in FreeCAD Makro > Makros ... > ascher_value.py ausfuehren (mit Farben),
oder ohne Oberflaeche: freecadcmd ascher_value.py  (schreibt ascher_value.FCStd, .step und .obj/.mtl
fuer Blender neben das Skript).
Andere Modelle holen ihn sich mit:  os.environ["ASCHER_MODUL"] = "1"; import ascher_value;
                                    info, farben = ascher_value.build(doc)
Koordinaten: z nach oben, Stempel auf der z-Achse, Standflaeche bei z = 0.
"""
import math
import os

import FreeCAD as App
import Part

V = App.Vector
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.getcwd()

# gemessen
D = 140.0                 # Durchmesser
H = 60.0                  # Korpus mit Deckel
STAMP = 50.0              # Stempel ueber dem Deckel (Stange + Griff)
GRIP_H = 30.0             # davon der schwarze Griff
RIM_H = 17.0              # Chrom-Deckel (Silberblech) aussen, ca.
FLAT_W = 12.0             # flacher Aussenring oben, ca.
INNER_D = 100.0           # Innenring, ca.
DISH_DEPTH = 10.0         # Innenring liegt so viel tiefer als der Aussenring
DOME_TOP = 0.0            # Kuppeldom in der Mitte: Oberkante etwa auf Hoehe des Aussenrings (relativ dazu)
ROD_FREE = 12.0           # blanke Stange zwischen Huelse und Griff
STROKE = 16.0             # Hub beim Druecken, ca. 15-16 mm (Griff laesst sich nicht abziehen)
# geschaetzt
BLACK_H = H - RIM_H       # schwarzer Topf
RIM_OVER = 0.6            # Deckel steht seitlich etwas ueber
RIM_R = 2.0               # Rundung der Deckel-Oberkante
SHEET = 1.2               # Blechstaerke
ARM_W = 26.0              # Drehteller: Breite der drei Arme (Foto: fast geschlossen, schmale Oeffnungen)
ARM_BEND = INNER_D / 4    # Drehteller: Kruemmung der Arme (Bogen von der Mitte bis zum Innenring)
SPIN_RISE = 4.0           # Drehteller: die Arme steigen zur Mitte hin leicht an
DOME_D = 40.0             # Kuppeldom: Durchmesser
ROD_D = 6.0               # Stange
COLLAR_D = 8.0            # verchromte Huelse unten an der Stange (Hoehe ergibt sich aus Stempel - Griff - Stange)
GRIP_D_TOP, GRIP_D_BOTTOM = 20.0, 16.0
GRIP_R = 2.0              # Rundung oben am Griff
ROD_IN_GRIP = 15.0        # so weit steckt die Stange im Griff

def fillet_top(shape, z, r):
    edges = [e for e in shape.Edges if abs(e.BoundBox.ZMin - z) < 1e-6 and abs(e.BoundBox.ZMax - z) < 1e-6]
    return shape.makeFillet(r, edges)


def build(doc, prefix="Ascher_", with_grip=True):
    """Legt den Ascher in doc an. Liefert Hoehen fuer den Knauf und die Farben {Objektname: rgb}."""
    colors = {}

    def add(name, shape, rgb):
        o = doc.addObject("Part::Feature", prefix + name)
        o.Shape = shape
        colors[o.Name] = rgb

    # ---- Topf und Deckel aus Silberblech: flacher Aussenring, Schraege hinunter zum Innenring,
    # darunter offen (dort sieht man in den Topf)
    z_lid = H
    z_dish = z_lid - DISH_DEPTH
    rim = fillet_top(Part.makeCylinder(D / 2 + RIM_OVER, RIM_H, V(0, 0, BLACK_H)), z_lid, RIM_R)
    rim = rim.cut(Part.makeCone(INNER_D / 2, D / 2 - FLAT_W, DISH_DEPTH, V(0, 0, z_dish)))
    rim = rim.cut(Part.makeCylinder(INNER_D / 2 - SHEET, z_dish - BLACK_H, V(0, 0, BLACK_H)))
    add("Topf", Part.makeCylinder(D / 2, BLACK_H), (0.08, 0.08, 0.09))
    add("Deckel", rim, (0.88, 0.89, 0.91))

    # ---- Drehteller: drei geschwungene Arme (wie Pflugscharen) vom Innenring zur Mitte, leicht gewoelbt,
    # in der Mitte der Kuppeldom; zwischen den Armen offen - dort fallen die Kippen beim Drehen in den Topf
    r_in = INNER_D / 2
    R_sph = (r_in ** 2 + SPIN_RISE ** 2) / (2 * SPIN_RISE)
    c = V(0, 0, z_dish + SPIN_RISE - R_sph)
    dome = Part.makeSphere(R_sph, c).cut(Part.makeSphere(R_sph - SHEET, c)).common(
        Part.makeCylinder(r_in, SPIN_RISE + 1, V(0, 0, z_dish - 1)))
    z0, hz = z_dish - 2, SPIN_RISE + 4
    # ein Arm: Bogen von der Mitte bis zum Innenring (Halbkreis um einen Punkt auf halbem Radius)
    arm = Part.makeCylinder(ARM_BEND + ARM_W / 2, hz, V(ARM_BEND, 0, z0)).cut(
        Part.makeCylinder(ARM_BEND - ARM_W / 2, hz, V(ARM_BEND, 0, z0))).common(
        Part.makeBox(INNER_D, r_in, hz, V(-r_in, 0, z0)))
    pattern = Part.makeCylinder(DOME_D / 2, hz, V(0, 0, z0))
    for k in range(3):
        a = arm.copy()
        a.rotate(V(0, 0, 0), V(0, 0, 1), k * 120 + 30)   # +30: weg von der Zylindernaht bei 0 Grad
        pattern = pattern.fuse(a)
    spin = dome.common(pattern)
    # Kuppeldom: Kugelkalotte auf den Armen, oben etwa auf Hoehe des Aussenrings
    r_d = DOME_D / 2
    z_base = c.z + math.sqrt(R_sph ** 2 - r_d ** 2)          # Hoehe der Arm-Woelbung am Domrand
    z_spin = z_lid + DOME_TOP
    rise = z_spin - z_base
    R_d = (r_d ** 2 + rise ** 2) / (2 * rise)
    cap = Part.makeSphere(R_d, V(0, 0, z_spin - R_d)).common(Part.makeCylinder(r_d, rise + SHEET, V(0, 0, z_base - SHEET)))
    add("Drehteller", spin.fuse(cap), (0.86, 0.87, 0.9))

    # ---- Stempel: Huelse, Stange, schwarzer Griff (with_grip=False: Griff abgezogen)
    z_grip = z_lid + STAMP - GRIP_H
    collar_h = z_grip - ROD_FREE - z_spin
    add("Huelse", Part.makeCylinder(COLLAR_D / 2, collar_h, V(0, 0, z_spin)), (0.8, 0.8, 0.82))
    add("Stange", Part.makeCylinder(ROD_D / 2, z_grip - z_spin + ROD_IN_GRIP, V(0, 0, z_spin)), (0.75, 0.75, 0.78))
    if with_grip:
        grip = Part.makeCone(GRIP_D_BOTTOM / 2, GRIP_D_TOP / 2, GRIP_H, V(0, 0, z_grip))
        add("Griff", fillet_top(grip, z_grip + GRIP_H, GRIP_R), (0.06, 0.06, 0.06))
    info = {"z_lid": z_lid, "z_dish": z_dish, "z_dome": z_spin, "z_grip": z_grip, "z_grip_top": z_grip + GRIP_H,
            "z_rod_top": z_grip + ROD_IN_GRIP, "rod_d": ROD_D, "grip_d_top": GRIP_D_TOP,
            "grip_d_bottom": GRIP_D_BOTTOM, "grip_h": GRIP_H, "stroke": STROKE, "d": D}
    return info, colors


def export_obj(objs, colors, path, deflection=0.1):
    """Wavefront OBJ + MTL, ein Material je Teil (Blender: Datei > Import > Wavefront, Einheit mm)."""
    mtl = os.path.splitext(path)[0] + ".mtl"
    with open(mtl, "w") as f:
        for o in objs:
            r, g, b = colors[o.Name]
            f.write("newmtl %s\nKd %.3f %.3f %.3f\n" % (o.Name, r, g, b))
    with open(path, "w") as f:
        f.write("mtllib %s\n" % os.path.basename(mtl))
        n = 1
        for o in objs:
            pts, tris = o.Shape.tessellate(deflection)
            f.write("o %s\nusemtl %s\n" % (o.Name, o.Name))
            f.writelines("v %.4f %.4f %.4f\n" % (p.x, p.y, p.z) for p in pts)
            f.writelines("f %d %d %d\n" % (a + n, b + n, c + n) for a, b, c in tris)
            n += len(pts)


def show(doc, colors):
    if App.GuiUp:
        import FreeCADGui as Gui
        for name, rgb in colors.items():
            doc.getObject(name).ViewObject.ShapeColor = rgb
        Gui.activeDocument().activeView().viewIsometric()
        Gui.SendMsgToActiveView("ViewFit")


# FreeCAD setzt __name__ auch beim direkten Ausfuehren auf den Dateinamen; wer importiert, setzt ASCHER_MODUL
if not os.environ.get("ASCHER_MODUL"):
    doc = App.newDocument("Ascher_Value")
    info, colors = build(doc, prefix="")
    doc.recompute()
    show(doc, colors)
    if not App.GuiUp:
        out = os.environ.get("ASCHER_OUT", os.path.join(HERE, "ascher_value.FCStd"))
        doc.saveAs(out)
        print("gespeichert", out, "|", ", ".join("%s %.0f" % kv for kv in info.items()))
        # Austausch: STEP fuer CAD, OBJ mit Farben fuer Blender & Co. (Millimeter, z nach oben)
        base = os.path.splitext(out)[0]
        objs = [doc.getObject(n) for n in colors]
        Part.export(objs, base + ".step")
        export_obj(objs, colors, base + ".obj")
        print("exportiert", base + ".step", base + ".obj")
