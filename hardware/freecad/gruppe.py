"""Gruppenbild: mehrere Value-Ascher mit Butt-Bin-Knauf nebeneinander, je eine Knauffarbe (FreeCAD 1.x).

Braucht knauf.FCStd (vorher freecadcmd knauf.py). Farben und Abstand ueber Umgebungsvariablen:
  GRUPPE="rot,orange,blau"   Reihenfolge von links nach rechts; der mittlere steht im Ursprung
  GRUPPE_ABSTAND=165         Mittenabstand in mm
  GRUPPE_VERSATZ=40          jeder zweite steht so weit weiter hinten
Schreibt gruppe.obj fuer render_blender.py. Die Haube bleibt schwarz.
"""
import os
import sys

import FreeCAD as App

V = App.Vector
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.getcwd()
sys.path.insert(0, HERE)
os.environ["ASCHER_MODUL"] = "1"
import ascher_value

FARBEN = {"rot": (0.75, 0.04, 0.03), "orange": (0.9, 0.13, 0.0), "gelb": (0.95, 0.62, 0.0),
          "gruen": (0.0, 0.35, 0.06), "hellgruen": (0.3, 0.75, 0.05), "blau": (0.01, 0.08, 0.6),
          "violett": (0.22, 0.03, 0.5), "pink": (0.95, 0.15, 0.4), "weiss": (0.85, 0.85, 0.85),
          "schwarz": (0.02, 0.02, 0.02)}
names = os.environ.get("GRUPPE", "rot,orange,blau").split(",")
step = float(os.environ.get("GRUPPE_ABSTAND", "165"))
back = float(os.environ.get("GRUPPE_VERSATZ", "40"))
KNOB = {"Knauf_Unterteil": None, "Knauf_Haube": (0.02, 0.02, 0.02), "Leuchtband": (1.0, 0.85, 0.4),
        "Button_Rand": None, "Button_Kappe": None}       # None = Knauffarbe

kn = App.openDocument(os.path.join(HERE, "knauf.FCStd"))
doc = App.newDocument("Gruppe")
colors = {}
mid = (len(names) - 1) / 2
for k, farbe in enumerate(names):
    dx, dy = (k - mid) * step, (back if abs(k - mid) % 2 == 1 else 0.0)
    tmp = App.newDocument("Tmp")
    info, ash = ascher_value.build(tmp, prefix="Ascher_")
    for o in tmp.Objects:
        s = o.Shape.copy()
        s.translate(V(dx, dy, 0))
        n = doc.addObject("Part::Feature", "%s_%d" % (o.Name, k))
        n.Shape = s
        colors[n.Name] = ash[o.Name]
    App.closeDocument(tmp.Name)
    for name, rgb in KNOB.items():
        s = kn.getObject(name).Shape.copy()
        s.translate(V(dx, dy, info["z_grip"]))
        n = doc.addObject("Part::Feature", "%s_%d" % (name, k))
        n.Shape = s
        colors[n.Name] = rgb or FARBEN[farbe]
ascher_value.export_obj([doc.getObject(n) for n in colors], colors,
                        os.environ.get("GRUPPE_OUT", os.path.join(HERE, "gruppe.obj")))
print("Gruppe:", ", ".join(names))
