"""Drehascher "Value" als Referenzmodell (FreeCAD 1.x) - zum Anpassen des Knaufs.

Gemessen: Ø 140 mm, Korpus 60 mm hoch, Stempel 50 mm ueber dem Deckel (davon 30 mm Griff).
Alles andere ist nach Foto geschaetzt und steht unten als Konstante.
Aufruf: in FreeCAD Makro > Makros ... > ascher_value.py ausfuehren (mit Farben),
oder ohne Oberflaeche: freecadcmd ascher_value.py  (schreibt ascher_value.FCStd neben das Skript).
Andere Modelle holen ihn sich mit:  os.environ["ASCHER_MODUL"] = "1"; import ascher_value;
                                    info, farben = ascher_value.build(doc)
Koordinaten: z nach oben, Stempel auf der z-Achse, Standflaeche bei z = 0.
"""
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
# geschaetzt
BLACK_H = 38.0            # schwarzer Topf
RIM_H = 22.0              # Chrom-Deckel aussen (Topf + Deckel = H)
RIM_OVER = 0.6            # Deckel steht seitlich etwas ueber
RIM_R = 2.0               # Rundung der Deckel-Oberkante
FLAT_W = 18.0             # flacher Deckelring aussen
DISH_D = 96.0             # Mulde: Durchmesser oben
DISH_DEPTH = 12.0         # Mulde: Tiefe
SPIN_D = 62.0             # Drehteller in der Mulde
SPIN_RISE = 4.0           # Woelbung des Drehtellers
SLOT_W = 9.0              # Breite der beiden Sichel-Schlitze im Drehteller
ROD_D = 6.0               # Stange
COLLAR_D, COLLAR_H = 9.0, 8.0     # Huelse unten an der Stange
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

    # ---- Topf und Deckel
    z_lid = H
    rim = fillet_top(Part.makeCylinder(D / 2 + RIM_OVER, RIM_H, V(0, 0, BLACK_H)), z_lid, RIM_R)
    # Mulde: Kegel vom flachen Ring hinunter zum Drehteller
    z_dish = z_lid - DISH_DEPTH
    rim = rim.cut(Part.makeCone(SPIN_D / 2, D / 2 - FLAT_W, DISH_DEPTH, V(0, 0, z_dish)))
    add("Topf", Part.makeCylinder(D / 2, BLACK_H), (0.08, 0.08, 0.09))
    add("Deckel", rim, (0.88, 0.89, 0.91))

    # ---- Drehteller mit zwei Sichel-Schlitzen (dort fallen die Kippen durch)
    R_sph = ((SPIN_D / 2) ** 2 + SPIN_RISE ** 2) / (2 * SPIN_RISE)
    spin = Part.makeSphere(R_sph, V(0, 0, z_dish + SPIN_RISE - R_sph)).common(
        Part.makeCylinder(SPIN_D / 2, SPIN_RISE, V(0, 0, z_dish)))
    spin = spin.fuse(Part.makeCylinder(SPIN_D / 2, 1.0, V(0, 0, z_dish - 1.0)))
    for sign in (1, -1):
        outer = Part.makeCylinder(SPIN_D * 0.32, SPIN_RISE + 2, V(sign * SPIN_D * 0.12, 0, z_dish - 1.5))
        inner = Part.makeCylinder(SPIN_D * 0.32 - SLOT_W / 2, SPIN_RISE + 2,
                                  V(sign * (SPIN_D * 0.12 + SLOT_W * 0.6), 0, z_dish - 1.5))
        half = Part.makeBox(SPIN_D, SPIN_D, SPIN_RISE + 2, V(-SPIN_D / 2, 0 if sign > 0 else -SPIN_D, z_dish - 1.5))
        spin = spin.cut(outer.cut(inner).common(half))
    add("Drehteller", spin, (0.86, 0.87, 0.9))

    # ---- Stempel: Huelse, Stange, schwarzer Griff (with_grip=False: Griff abgezogen)
    z_grip = z_lid + STAMP - GRIP_H
    z_spin = z_dish + SPIN_RISE
    add("Huelse", Part.makeCylinder(COLLAR_D / 2, COLLAR_H, V(0, 0, z_spin)), (0.1, 0.1, 0.1))
    add("Stange", Part.makeCylinder(ROD_D / 2, z_grip - z_spin + ROD_IN_GRIP, V(0, 0, z_spin)), (0.75, 0.75, 0.78))
    if with_grip:
        grip = Part.makeCone(GRIP_D_BOTTOM / 2, GRIP_D_TOP / 2, GRIP_H, V(0, 0, z_grip))
        add("Griff", fillet_top(grip, z_grip + GRIP_H, GRIP_R), (0.06, 0.06, 0.06))
    info = {"z_lid": z_lid, "z_dish": z_dish, "z_grip": z_grip, "z_grip_top": z_grip + GRIP_H,
            "z_rod_top": z_grip + ROD_IN_GRIP, "rod_d": ROD_D, "grip_d_top": GRIP_D_TOP, "d": D}
    return info, colors


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
