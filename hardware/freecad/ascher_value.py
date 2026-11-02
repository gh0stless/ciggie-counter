"""Drehascher "Value" als Referenzmodell (FreeCAD 1.x) - zum Anpassen des Knaufs.

Gemessen: Ø 140 mm, Korpus 60 mm hoch, Stempel 50 mm ueber dem Deckel (davon 30 mm Griff);
Deckel aus Silberblech ca. 17 mm hoch, Aussenring ca. 12 mm, Innenring Ø ca. 100 mm 10 mm tiefer,
darin ein gewoelbter Stern mit drei schmalen geschwungenen Armen zur Nabe (wie ein 45er-Puck),
darunter eine helle Schuessel mit runder Oeffnung in der Mitte (Fotos von oben, 02.11.2026).
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
SPIN_RISE = DISH_DEPTH    # Stern (Kuppeldom): gewoelbt, die Mitte liegt wieder etwa auf Hoehe des Aussenrings
ROD_FREE = 12.0           # blanke Stange zwischen Huelse und Griff
STROKE = 16.0             # Hub beim Druecken, ca. 15-16 mm (Griff laesst sich nicht abziehen)
# geschaetzt
BLACK_H = H - RIM_H       # schwarzer Topf
RIM_OVER = 0.6            # Deckel steht seitlich etwas ueber
RIM_R = 2.0               # Rundung der Deckel-Oberkante
SHEET = 1.2               # Blechstaerke
HUB_R = 11.0              # Stern: Nabe (Ring um die Stange)
ARM_W_IN, ARM_W_OUT = 7.0, 15.0   # Stern: Breite eines Arms an der Nabe und am Innenring (Fotos von oben)
ARM_SWEEP = 45.0          # Stern: so weit (Grad) biegt sich ein Arm von der Nabe bis zum Innenring
ARM_ANGLES = (270, 30, 150)       # wo die Arme am Innenring ankommen: vorn (-y), rechts hinten, links hinten
PLATE_DEPTH = 7.0         # helle Schuessel unter dem Stern: faellt vom Innenring zur Mitte so weit ab
PLATE_HOLE_D = 35.0       # runde Oeffnung in der Mitte der Schuessel
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

    # ---- helle Schuessel unter dem Stern: faellt vom Innenring zur Mitte ab, dort eine runde Oeffnung
    r_in = INNER_D / 2
    bowl = Part.makeCone(PLATE_HOLE_D / 2, r_in, PLATE_DEPTH, V(0, 0, z_dish - PLATE_DEPTH))
    inner = Part.makeCone(PLATE_HOLE_D / 2, r_in, PLATE_DEPTH, V(0, 0, z_dish - PLATE_DEPTH + SHEET))
    plate = bowl.cut(inner).cut(Part.makeCylinder(PLATE_HOLE_D / 2, PLATE_DEPTH + 2, V(0, 0, z_dish - PLATE_DEPTH - 1)))
    add("Teller", plate, (0.86, 0.87, 0.9))

    # ---- Drehteller: gewoelbter Stern (Kuppeldom) wie ein 45er-Puck: drei geschwungene Arme von der Nabe
    # zum Innenring, nach aussen breiter werdend
    R_sph = (r_in ** 2 + SPIN_RISE ** 2) / (2 * SPIN_RISE)
    c = V(0, 0, z_dish + SPIN_RISE - R_sph)
    dome = Part.makeSphere(R_sph, c).cut(Part.makeSphere(R_sph - SHEET, c)).common(
        Part.makeCylinder(r_in, SPIN_RISE + 1, V(0, 0, z_dish - 1)))
    z0, hz = z_dish - 2, SPIN_RISE + 4
    # ein Arm: Mittellinie von der Nabe zum Innenring, die sich um ARM_SWEEP Grad biegt (endet bei 0 Grad),
    # Breite waechst von ARM_W_IN auf ARM_W_OUT; Umriss als Polygon aus beiden Kanten
    n = 40
    left, right = [], []
    for i in range(n + 1):
        t = i / n
        r = HUB_R * 0.5 + (r_in + 3 - HUB_R * 0.5) * t
        phi = math.radians(-ARM_SWEEP * (1 - t) ** 2)            # Biegung vor allem nahe der Nabe
        w = ARM_W_IN + (ARM_W_OUT - ARM_W_IN) * t ** 1.5
        p = V(r * math.cos(phi), r * math.sin(phi), z0)
        # Normale zur Mittellinie (numerisch aus dem naechsten Punkt)
        t2 = min(t + 1e-3, 1.0) if t < 1 else t - 1e-3
        r2 = HUB_R * 0.5 + (r_in + 3 - HUB_R * 0.5) * t2
        phi2 = math.radians(-ARM_SWEEP * (1 - t2) ** 2)
        d = V(r2 * math.cos(phi2), r2 * math.sin(phi2), z0) - p
        if t >= 1:
            d = d * -1
        nrm = V(-d.y, d.x, 0).normalize()
        left.append(p + nrm * (w / 2))
        right.append(p - nrm * (w / 2))
    arm = Part.Face(Part.makePolygon(left + right[::-1] + [left[0]])).extrude(V(0, 0, hz))
    star = Part.makeCylinder(HUB_R, hz, V(0, 0, z0))
    for ang in ARM_ANGLES:
        a = arm.copy()
        a.rotate(V(0, 0, 0), V(0, 0, 1), ang)
        star = star.fuse(a)
    add("Drehteller", dome.common(star), (0.86, 0.87, 0.9))

    # ---- Stempel: Huelse, Stange, schwarzer Griff (with_grip=False: Griff abgezogen)
    z_spin = z_dish + SPIN_RISE
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
