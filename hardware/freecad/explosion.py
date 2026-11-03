"""Butt-Bin-Knauf als Baugruppe zum Auseinanderziehen (FreeCAD 1.x).

Liest knauf.FCStd (vorher knauf.py laufen lassen) und legt knauf_explosion.FCStd an: jedes Bauteil einzeln,
in der Tabelle "Steuerung" die Zelle Explosion (0 = zusammengebaut, 1 = auseinandergezogen, Zwischenwerte
gehen auch). Die Bauteile ruecken entlang der Achse in Einbaureihenfolge auseinander.
Aufruf mit Oberflaeche, damit die Farben mitgespeichert werden (FreeCAD beendet sich danach selbst):
    freecad.exe explosion.py
Ohne Oberflaeche (freecadcmd explosion.py) entsteht dasselbe Dokument, nur ohne Farben.
"""
import os
import sys

import FreeCAD as App
import Part

V = App.Vector
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.path.join(os.path.dirname(os.path.abspath(sys.argv[-1])))

# Bauteil -> (Weg bei Explosion = 1 in mm, Farbe, Beschriftung im Baum)
# Reihenfolge = Einbaureihenfolge; nach oben gehen sie so weit, dass nichts mehr ineinandersteckt
PARTS = [
    ("Original_Griff", -70, (0.06, 0.06, 0.06), "Griff des Aschers (nur zur Kontrolle)"),
    ("Gummimuffe", -35, (0.1, 0.1, 0.1), "Gummimuffe: Silikonschlauch 21 x 16, 30 mm"),
    ("Knauf_Unterteil", 0, (0.75, 0.04, 0.03), "Unterteil (Druck, PA12)"),
    ("Zellenhalter", 30, (0.85, 0.85, 0.8), "CR2450-Halter mit Drehdeckel"),
    ("Platine", 45, (0.1, 0.45, 0.15), "Platine Rev 0.8"),
    ("Schraube_M2", 55, (0.95, 0.95, 0.9), "Nylon-Schraube M2 x 5"),
    ("Leuchtband", 60, (1.0, 0.85, 0.4), "Leuchtring / Verbinder (Druck, klares Resin)"),
    ("Knauf_Haube", 80, (0.02, 0.02, 0.02), "Haube (Druck, PA12)"),
    ("Button_Rand", 100, (0.75, 0.04, 0.03), "Retro+ Button S30: Gehaeuse"),
    ("Button_Kappe", 100, (0.75, 0.04, 0.03), "Retro+ Button S30: Kappe"),
    ("Button_Stifte", 100, (0.75, 0.75, 0.78), "Retro+ Button S30: Anschluesse"),
]
SCREW_XY = (0.0, 15.0)            # wie knauf.py
SCREW_L, HEAD_D, HEAD_H = 5.0, 3.8, 1.3

src = App.openDocument(os.path.join(HERE, "knauf.FCStd"))
doc = App.newDocument("Knauf_Explosion")
sheet = doc.addObject("Spreadsheet::Sheet", "Steuerung")
sheet.set("A1", "Explosion")
sheet.set("B1", "1")
sheet.setAlias("B1", "Explosion")
sheet.set("A2", "0 = zusammengebaut, 1 = auseinandergezogen")

# Schraube: liegt mit dem Kopf auf der Platine (Oberkante Platinenkoerper aus dem STEP)
pcb = src.getObject("Platine").Shape
z_top = max(s.BoundBox.ZMax for s in pcb.Solids if s.BoundBox.XLength > 30)
screw = Part.makeCylinder(1.0, SCREW_L, V(SCREW_XY[0], SCREW_XY[1], z_top - SCREW_L)).fuse(
    Part.makeCylinder(HEAD_D / 2, HEAD_H, V(SCREW_XY[0], SCREW_XY[1], z_top)))

group = doc.addObject("App::DocumentObjectGroup", "Bauteile")
for name, lift, rgb, label in PARTS:
    shape = screw if name == "Schraube_M2" else src.getObject(name).Shape.copy()
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    o.Label = label
    group.addObject(o)
    if lift:
        o.setExpression(".Placement.Base.z", "Steuerung.Explosion * %d mm" % lift)
    if App.GuiUp:
        o.ViewObject.ShapeColor = rgb
        if name == "Leuchtband":
            o.ViewObject.Transparency = 40
doc.recompute()
App.closeDocument(src.Name)

out = os.path.join(HERE, "knauf_explosion.FCStd")
if App.GuiUp:
    import FreeCADGui as Gui
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
doc.saveAs(out)
print("gespeichert", out)
if App.GuiUp and os.environ.get("EXPLOSION_BEENDEN"):
    from PySide import QtCore
    QtCore.QTimer.singleShot(500, Gui.getMainWindow().close)
