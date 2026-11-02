"""Butt-Bin-Konzept (nur zur Ansicht): Ascher mit aufgestecktem Knauf im Schaltknauf-/Arcade-Stil.

Grobe Formen, keine Konstruktion - die steht in knauf.py. Der Ascher kommt aus ascher_value.py.
Zwei Varianten (Umgebungsvariable KONZEPT_VARIANTE), Akzentfarbe rot oder orange (KONZEPT_FARBE):
  original - gekaufter 30-mm-Arcade-Button (Sanwa-Typ): schwarzer Rand, Kappe, Leuchtband in der Mitte
  nachbau  - gedruckter Button: grosse flache Kappe direkt in der Haube, drueckt auf den Taster der
             Platine; ein leuchtender Spaltring um die Kappe statt des Leuchtbands
Aufruf: in FreeCAD Makro > Makros ... > konzept.py ausfuehren (mit Farben),
oder ohne Oberflaeche: freecadcmd konzept.py  (schreibt konzept[_nachbau].FCStd und .obj fuer Blender
neben das Skript).
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

import sys
sys.path.insert(0, HERE)
os.environ["ASCHER_MODUL"] = "1"   # nur build() nutzen, nicht als eigenes Modell speichern
import ascher_value                # Referenzmodell des Aschers (Masse dort)

VARIANT = os.environ.get("KONZEPT_VARIANTE", "original")
# Der Original-Griff laesst sich nicht abziehen: der Knauf wird ueber den ganzen Griff gestuelpt
# (Schacht mit Gummimuffe), seine Unterkante liegt auf Hoehe der Griff-Unterkante.
KNOB_D = 40.0
BASE_H = 42.0                      # Unterteil: Schacht fuer den Griff + Zellenfach
ELEC_H = 7.0                       # Platine mit Modul und etwas Luft ueber dem Unterteil
BAND_H = 3.0                       # Leuchtband (klar), nur beim Original-Button
TOP_R = 3.0                        # Rundung oben
# Farben (Umgebungsvariable KONZEPT_FARBE): Unterteil und Button in der Akzentfarbe, Haube schwarz
ACCENT = {"rot": (0.75, 0.04, 0.03), "orange": (0.9, 0.13, 0.0)}   # linear (Blender), Orange ~ RAL 2004
FARBE = os.environ.get("KONZEPT_FARBE", "rot")
COL_BASE, COL_HOOD, COL_BTN = ACCENT[FARBE], (0.02, 0.02, 0.02), ACCENT[FARBE]
# Original-Button: echtes Modell (Sanwa OBSF-30 von GrabCAD, nicht im Repo) unter fremd/, sonst Platzhalter.
# Im STEP zeigt die Hochachse nach +y; Panel-Oberkante = Oberkante Rand - SANWA_BEZEL_H (geschaetzt).
SANWA_STEP = os.path.join(HERE, "fremd", "sanwa_obsf30.step")
SANWA_BEZEL_H = 3.0
BTN_FLANGE_D, BTN_FLANGE_H, BTN_CAP_D, BTN_CAP_H, BTN_DEPTH = 33.0, 3.0, 26.0, 4.0, 35.0   # Platzhalter
# Nachbau: gedruckte Kappe in der Haube, Spaltring leuchtet
DIY_CAP_D, DIY_CAP_H, DIY_GAP, DIY_TRAVEL = 33.0, 5.0, 1.0, 3.0

doc = App.newDocument("Konzept")
COLORS = {}


def add(name, shape, rgb, transp=0):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    COLORS[name] = (rgb, transp)
    return o


def dome_cap(d, h, z):
    """Flache Kuppel (skalierte Halbkugel) mit Unterkante bei z."""
    cap = Part.makeSphere(1.0).common(Part.makeCylinder(1.0, 1.0))
    m = App.Matrix()
    m.scale(d / 2, d / 2, h)
    cap = cap.transformGeometry(m)
    cap.translate(V(0, 0, z))
    return cap


# ---- Ascher aus dem Referenzmodell
info, ash_colors = ascher_value.build(doc)
for name, rgb in ash_colors.items():
    COLORS[name] = (rgb, 0)

def sanwa_parts():
    """Echtes Sanwa-Modell, aufgestellt (Hochachse z), Panel-Oberkante bei z = 0, Mitte auf der Achse.
    Liefert {Teil: Form} sowie Hoehe ueber und Bautiefe unter dem Panel, oder None ohne Datei."""
    if not os.path.isfile(SANWA_STEP):
        return None
    solids = sorted(Part.read(SANWA_STEP).Solids, key=lambda s: s.BoundBox.YMax)
    switch, base, cap = solids                     # nach Oberkante: Mikroschalter, Gehaeuse mit Rand, Kappe
    bb = base.BoundBox
    m = App.Matrix()
    m.rotateX(math.radians(90))                    # +y -> +z
    out = {}
    for name, s in (("Sanwa_Mikroschalter", switch), ("Sanwa_Rand", base), ("Sanwa_Kappe", cap)):
        s = s.copy()
        s.translate(V(-(bb.XMin + bb.XMax) / 2, -(bb.YMax - SANWA_BEZEL_H), -(bb.ZMin + bb.ZMax) / 2))
        out[name] = s.transformGeometry(m)
    above = max(s.BoundBox.ZMax for s in out.values())
    depth = -min(s.BoundBox.ZMin for s in out.values())
    return out, above, depth


# ---- Knauf: ueber den Original-Griff gestuelpt, Hoehe ergibt sich aus Unterteil, Elektronik und Button
z0 = info["z_grip"]
lower = Part.makeCylinder(KNOB_D / 2, BASE_H, V(0, 0, z0))
add("Knauf_Unterteil", lower.makeFillet(1.5, [e for e in lower.Edges if abs(e.BoundBox.ZMax - z0) < 1e-6]),
    COL_BASE)
if VARIANT == "original":
    sanwa = sanwa_parts()
    above, depth = (sanwa[1], sanwa[2]) if sanwa else (BTN_FLANGE_H + BTN_CAP_H, BTN_DEPTH)
    z_band = z0 + BASE_H
    z_hood = z_band + BAND_H
    z_top = z0 + BASE_H + ELEC_H + depth          # Panel-Oberkante: Button-Unterseite ueber der Elektronik
    add("Leuchtband", Part.makeCylinder(KNOB_D / 2, BAND_H, V(0, 0, z_band)), (1.0, 0.85, 0.4), 30)
    hood = Part.makeCylinder(KNOB_D / 2, z_top - z_hood, V(0, 0, z_hood))
    add("Knauf_Haube", hood.makeFillet(TOP_R, [e for e in hood.Edges if abs(e.BoundBox.ZMin - z_top) < 1e-6]),
        COL_HOOD)
    if sanwa:
        for name, s in sanwa[0].items():
            s.translate(V(0, 0, z_top))
            add(name, s, (0.6, 0.6, 0.6) if name == "Sanwa_Mikroschalter" else COL_BTN)
    else:
        add("Button_Rand", Part.makeCylinder(BTN_FLANGE_D / 2, BTN_FLANGE_H, V(0, 0, z_top)), COL_BTN)
        add("Button_Kappe", dome_cap(BTN_CAP_D, BTN_CAP_H, z_top + BTN_FLANGE_H), COL_BTN)
    knob_top = z_top + above
else:
    # Haube bis oben, mit einer Senkung fuer die Kappe; der Spalt um die Kappe leuchtet (Lichtleiter-Ring).
    # Die Kappe drueckt direkt auf den Taster der Platine: nur Tasterhub statt Button-Bautiefe.
    z_hood = z0 + BASE_H
    z_top = z0 + BASE_H + ELEC_H + DIY_TRAVEL + 2.0
    hood = Part.makeCylinder(KNOB_D / 2, z_top - z_hood, V(0, 0, z_hood))
    hood = hood.makeFillet(TOP_R, [e for e in hood.Edges if abs(e.BoundBox.ZMin - z_top) < 1e-6])
    pocket = Part.makeCylinder(DIY_CAP_D / 2 + DIY_GAP, 2.0, V(0, 0, z_top - 2.0))
    add("Knauf_Haube", hood.cut(pocket), COL_HOOD)
    add("Leuchtband", Part.makeCylinder(DIY_CAP_D / 2 + DIY_GAP, 1.2, V(0, 0, z_top - 2.0))
        .cut(Part.makeCylinder(DIY_CAP_D / 2, 1.2, V(0, 0, z_top - 2.0))), (1.0, 0.85, 0.4), 30)
    add("Button_Kappe", Part.makeCylinder(DIY_CAP_D / 2, 2.0, V(0, 0, z_top - 2.0))
        .fuse(dome_cap(DIY_CAP_D, DIY_CAP_H, z_top)), COL_BTN)
    knob_top = z_top + DIY_CAP_H
KNOB_H = knob_top - z0
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
    name = ("konzept" if VARIANT == "original" else "konzept_" + VARIANT) + ("" if FARBE == "rot" else "_" + FARBE)
    out = os.environ.get("KONZEPT_OUT", os.path.join(HERE, name + ".FCStd"))
    doc.saveAs(out)
    print("gespeichert", out, "| Variante %s, Knauf von z = %.1f bis %.1f; gedrueckt %.1f mm ueber dem Kuppeldom"
          % (VARIANT, z0, z0 + KNOB_H, z0 - info["stroke"] - info["z_dome"]))
    # OBJ fuer Blender (render_blender.py)
    objs = [doc.getObject(n) for n in COLORS]
    ascher_value.export_obj(objs, {n: rgb for n, (rgb, _) in COLORS.items()}, os.path.splitext(out)[0] + ".obj")
