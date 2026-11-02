"""Butt-Bin-Konzept (nur zur Ansicht): Ascher mit aufgestecktem Knauf im Schaltknauf-/Arcade-Stil.

Grobe Formen, keine Konstruktion - die steht in knauf.py. Der Ascher kommt aus ascher_value.py.
Aufruf: in FreeCAD Makro > Makros ... > konzept.py ausfuehren (mit Farben),
oder ohne Oberflaeche: freecadcmd konzept.py  (schreibt konzept.FCStd und konzept.obj fuer Blender
neben das Skript).
"""
import os

import FreeCAD as App
import Part

V = App.Vector
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.getcwd()

import sys
sys.path.insert(0, HERE)
os.environ["ASCHER_MODUL"] = "1"   # nur build() nutzen, nicht als eigenes Modell speichern
import ascher_value                # Referenzmodell des Aschers (Masse dort)

# Der Original-Griff laesst sich nicht abziehen: der Knauf wird ueber den ganzen Griff gestuelpt
# (Schacht mit Gummimuffe), seine Unterkante liegt auf Hoehe der Griff-Unterkante.
KNOB_D, KNOB_H = 40.0, 90.0        # Hoehe mit Button
BASE_H = 42.0                      # Unterteil (Alu-Optik): Schacht fuer den Griff + Zellenfach
BAND_H = 3.0                       # Leuchtband (klar)
TOP_R = 3.0                        # Rundung oben
BTN_FLANGE_D, BTN_FLANGE_H, BTN_CAP_D, BTN_CAP_H = 33.0, 3.0, 26.0, 7.0

doc = App.newDocument("Konzept")
COLORS = {}


def add(name, shape, rgb, transp=0):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    COLORS[name] = (rgb, transp)
    return o


# ---- Ascher aus dem Referenzmodell
info, ash_colors = ascher_value.build(doc)
for name, rgb in ash_colors.items():
    COLORS[name] = (rgb, 0)

# ---- Knauf: ueber den Original-Griff gestuelpt
z0 = info["z_grip"]
z_band = z0 + BASE_H
z_hood = z_band + BAND_H
z_top = z0 + KNOB_H - BTN_FLANGE_H - BTN_CAP_H
lower = Part.makeCylinder(KNOB_D / 2, BASE_H, V(0, 0, z0))
add("Knauf_Unterteil", lower.makeFillet(1.5, [e for e in lower.Edges if abs(e.BoundBox.ZMax - z0) < 1e-6]),
    (0.78, 0.79, 0.8))
add("Leuchtband", Part.makeCylinder(KNOB_D / 2, BAND_H, V(0, 0, z_band)), (1.0, 0.85, 0.4), 30)
hood = Part.makeCylinder(KNOB_D / 2, z_top - z_hood, V(0, 0, z_hood))
top_edge = [e for e in hood.Edges if abs(e.BoundBox.ZMin - z_top) < 1e-6]
add("Knauf_Haube", hood.makeFillet(TOP_R, top_edge), (0.78, 0.79, 0.8))
cap = Part.makeSphere(1.0).common(Part.makeCylinder(1.0, 1.0))      # Halbkugel, dann skaliert
m = App.Matrix()
m.scale(BTN_CAP_D / 2, BTN_CAP_D / 2, BTN_CAP_H)
cap = cap.transformGeometry(m)
cap.translate(V(0, 0, z_top + BTN_FLANGE_H))
add("Button_Rand", Part.makeCylinder(BTN_FLANGE_D / 2, BTN_FLANGE_H, V(0, 0, z_top)), (0.1, 0.1, 0.1))
add("Button_Kappe", cap, (1.0, 0.42, 0.0))
doc.recompute()

if App.GuiUp:
    import FreeCADGui as Gui
    for name, (rgb, transp) in COLORS.items():
        vo = doc.getObject(name).ViewObject
        vo.ShapeColor = rgb
        vo.Transparency = transp
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
else:
    out = os.environ.get("KONZEPT_OUT", os.path.join(HERE, "konzept.FCStd"))
    doc.saveAs(out)
    print("gespeichert", out, "| Knauf von z = %.1f bis %.1f; gedrueckt %.1f mm ueber dem Kuppeldom"
          % (z0, z0 + KNOB_H, z0 - info["stroke"] - info["z_dome"]))
    # OBJ fuer Blender (render_blender.py)
    objs = [doc.getObject(n) for n in COLORS]
    ascher_value.export_obj(objs, {n: rgb for n, (rgb, _) in COLORS.items()}, os.path.splitext(out)[0] + ".obj")
