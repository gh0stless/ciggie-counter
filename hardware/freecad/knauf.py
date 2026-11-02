"""Butt-Bin-Knauf (Entwurf) fuer FreeCAD 1.x - parametrisch.

Alle Masse stehen in der Tabelle "Parameter" (Objekt P). Wert dort aendern, Strg+R: alles rechnet nach.
Teile von unten nach oben: Gummimuffe, Unterteil, Knopfzelle, Zellendeckel mit Anschlag, Wellenfeder,
Oberteil, Platine (STEP aus KiCad), Leuchtring, Kuppel (Positiv) und daneben die Gussform (Negativ).

In der Datei: "Baugruppe" (alles in Einbaulage) und "Einzelteile" (Verknuepfungen, druckfertig nebeneinander).
Aufruf: in FreeCAD Makro > Makros ... > knauf.py ausfuehren (mit Farben),
oder ohne Oberflaeche: freecadcmd knauf.py  (schreibt knauf.FCStd und stl/*.stl neben das Skript).
Platine: liegt buttbin_carrier.step neben dem Skript, wird sie eingesetzt, sonst ein Platzhalter.
Erzeugen:  kicad-cli pcb export step --user-origin 100x100mm --subst-models -o buttbin_carrier.step
           ../kicad/buttbin_carrier/buttbin_carrier.kicad_pcb
Koordinaten: z nach oben, Knauf-Mitte auf der z-Achse, Unterseite des Unterteils bei z = 0.
"""
import os

import FreeCAD as App

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.getcwd()

# Name, Wert, Beschreibung. Werte mit "=" sind Formeln aus den anderen Parametern.
PARAMS = [
    ("d_out", 40.0, "Aussendurchmesser Knauf"),
    ("wall", 2.0, "Wandstaerke Oberteil"),
    ("clr", 0.3, "Spiel der Gleitfuehrung Oberteil/Unterteil (je Seite)"),
    ("hole_d", 15.0, "Bohrung fuer die Gummimuffe"),
    ("hole_depth", 20.0, "Tiefe der Bohrung"),
    ("handle_d", 10.0, "Durchmesser des Original-Griffs"),
    ("sleeve_squeeze", 0.5, "Uebermass: Muffe innen kleiner als der Griff"),
    ("floor_t", 1.5, "Boden zwischen Bohrung und Zellenfach"),
    ("cell_d", 24.5, "Knopfzelle CR2450: Durchmesser"),
    ("cell_h", 5.0, "Knopfzelle CR2450: Hoehe"),
    ("cell_clr", 0.4, "Spiel im Zellenfach"),
    ("lid_t", 1.0, "Zellendeckel: Dicke (liegt buendig in einer Senkung)"),
    ("lid_extra", 1.5, "Zellendeckel: Rand ueber das Zellenfach hinaus"),
    ("guide_h", 6.0, "Laenge der Gleitfuehrung oben am Unterteil"),
    ("spring_od", 34.0, "Wellenfeder: aussen (muss auf die Fuehrung passen: < guide_d)"),
    ("spring_id", 30.0, "Wellenfeder: innen (liegt unter der Auflagekante, ueber dem Zellendeckel)"),
    ("spring_h", 3.0, "Wellenfeder: Hoehe eingebaut (vorgespannt)"),
    ("ledge_w", 1.5, "Auflagekante fuer die Platine im Oberteil"),
    ("ledge_t", 1.2, "Dicke der Auflagekante"),
    ("pcb_d", 34.0, "Platine: Durchmesser"),
    ("pcb_t", 1.6, "Platine: Dicke"),
    ("sw_h", 3.2, "Taster unter der Platine: KSC621G 3,2 mm (der KSC621J waere 7,7 mm hoch)"),
    ("gap0", 0.3, "Luft Taster - Anschlag in Ruhe"),
    ("sw_travel", 0.5, "Schaltweg des Tasters"),
    ("over_travel", 0.2, "Reserve nach dem Schaltpunkt bis zum harten Anschlag"),
    ("stop_d", 4.0, "Anschlag-Noppe auf dem Zellendeckel (unter dem Taster)"),
    ("comp_h", 3.5, "Bauhoehe oben (Modul) - darueber beginnt der Ring"),
    ("ring_id", 28.0, "Leuchtring: innen"),
    ("ring_h", 4.0, "Leuchtring: Hoehe"),
    ("collar_w", 0.8, "Leuchtring: Kragen nach unten, haelt die Platine am Rand und leitet das LED-Licht"),
    ("dome_h", 14.0, "Kuppel: Hoehe"),
    ("mold_wall", 4.0, "Gussform: Wandstaerke"),
    ("mold_x", 70.0, "Gussform: Abstand neben dem Knauf (nur Ansicht)"),
    ("wire_d", 2.0, "Durchfuehrung der Litzen im Zellendeckel"),
    ("wire_x", 11.0, "Litzen: x (Pads BAT+/BAT- auf der Platine)"),
    ("wire_y", 7.5, "Litzen: y"),
    # abgeleitet
    ("base_h", "=hole_depth + floor_t + cell_h + cell_clr + lid_t", "Hoehe Unterteil"),
    ("base_low_h", "=base_h - guide_h", "Unterteil: Hoehe bis zur Gleitfuehrung"),
    ("guide_d", "=d_out - 2 * wall - 2 * clr", "Durchmesser der Gleitfuehrung"),
    ("pocket_z", "=hole_depth + floor_t", "Boden des Zellenfachs"),
    ("lid_d", "=cell_d + cell_clr + 2 * lid_extra", "Zellendeckel: Durchmesser"),
    ("stop_h", "=spring_h + ledge_t - sw_h - gap0", "Anschlag-Noppe: Hoehe (muss > 0 sein)"),
    ("stroke", "=gap0 + sw_travel + over_travel", "Hub bis zum harten Anschlag"),
    ("z_ledge", "=base_h + spring_h", "Unterkante Auflagekante = Oberkante Feder"),
    ("z_pcb", "=z_ledge + ledge_t", "Unterseite Platine"),
    ("z_skirt", "=base_low_h + stroke", "Unterkante Oberteil"),
    ("z_ring", "=z_pcb + pcb_t + comp_h", "Unterkante Leuchtring = Oberkante Oberteil"),
    ("z_dome", "=z_ring + ring_h", "Unterkante Kuppel"),
]

doc = App.newDocument("Knauf")
P = doc.addObject("Spreadsheet::Sheet", "P")
P.Label = "Parameter"
P.set("A1", "Name"); P.set("B1", "Wert"); P.set("C1", "Beschreibung")
for row, (name, val, text) in enumerate(PARAMS, start=2):
    P.set("A%d" % row, name)
    P.set("B%d" % row, str(val))
    P.set("C%d" % row, text)
    P.setAlias("B%d" % row, name)
doc.recompute()


def expr(obj, **props):
    for prop, e in props.items():
        obj.setExpression(prop, e)


def cyl(name, d, h, z="0", x="0", y="0"):
    c = doc.addObject("Part::Cylinder", name)
    expr(c, **{"Radius": "(%s) / 2" % d, "Height": h,
               "Placement.Base.x": x, "Placement.Base.y": y, "Placement.Base.z": z})
    return c


def cut(name, base, *tools):
    tool = tools[0] if len(tools) == 1 else fuse(name + "_Werkzeug", *tools)
    c = doc.addObject("Part::Cut", name)
    c.Base, c.Tool = base, tool
    return c


def fuse(name, *shapes):
    f = doc.addObject("Part::MultiFuse", name)
    f.Shapes = list(shapes)
    return f


def ellipsoid(name, z, x="0", lower=False):
    e = doc.addObject("Part::Ellipsoid", name)
    e.Angle1, e.Angle2 = (-90, 0) if lower else (0, 90)
    expr(e, **{"Radius1": "P.dome_h", "Radius2": "P.d_out / 2", "Placement.Base.x": x, "Placement.Base.z": z})
    return e


# ---------------------------------------------------------------- Unterteil
# unten voll (d_out), oben die schmalere Gleitfuehrung fuer das Oberteil;
# von unten die Bohrung fuer die Gummimuffe, oben Zellenfach und Senkung fuer den Deckel
body = fuse("Unterteil_Koerper",
            cyl("U_unten", "P.d_out", "P.base_low_h"),
            cyl("U_Fuehrung", "P.guide_d", "P.guide_h", z="P.base_low_h"))
base = cut("Unterteil", body,
           cyl("U_Bohrung", "P.hole_d", "P.hole_depth"),
           cyl("U_Zellenfach", "P.cell_d + P.cell_clr", "P.cell_h + P.cell_clr + P.lid_t", z="P.pocket_z"),
           cyl("U_Senkung", "P.lid_d", "P.lid_t", z="P.base_h - P.lid_t"))

sleeve = cut("Gummimuffe", cyl("M_aussen", "P.hole_d", "P.hole_depth"),
             cyl("M_innen", "P.handle_d - P.sleeve_squeeze", "P.hole_depth"))

cell = cyl("Knopfzelle", "P.cell_d", "P.cell_h", z="P.pocket_z")

# Zellendeckel mit Anschlag-Noppe unter dem Taster und zwei Loechern fuer die Litzen
lid = cut("Zellendeckel",
          fuse("D_Koerper", cyl("D_Scheibe", "P.lid_d", "P.lid_t", z="P.base_h - P.lid_t"),
               cyl("D_Noppe", "P.stop_d", "P.stop_h", z="P.base_h")),
          cyl("D_Litze1", "P.wire_d", "P.lid_t", z="P.base_h - P.lid_t", x="P.wire_x", y="P.wire_y - 1.5"),
          cyl("D_Litze2", "P.wire_d", "P.lid_t", z="P.base_h - P.lid_t", x="P.wire_x", y="P.wire_y + 1.5"))

spring = cut("Wellenfeder", cyl("F_aussen", "P.spring_od", "P.spring_h", z="P.base_h"),
             cyl("F_innen", "P.spring_id", "P.spring_h", z="P.base_h"))

# ---------------------------------------------------------------- Oberteil
# Rohr vom Rock (gleitet ueber die Fuehrung) bis zum Ring; innen die Auflagekante fuer die Platine,
# auf deren Unterseite die Feder drueckt. Platine, Ring und Kuppel bilden mit dem Oberteil den Druckknopf.
top = cut("Oberteil", cyl("O_aussen", "P.d_out", "P.z_ring - P.z_skirt", z="P.z_skirt"),
          cyl("O_Rock", "P.d_out - 2 * P.wall", "P.z_ledge - P.z_skirt", z="P.z_skirt"),
          cyl("O_Kante", "P.pcb_d - 2 * P.ledge_w", "P.z_ring - P.z_skirt", z="P.z_skirt"),
          cyl("O_Platine", "P.pcb_d + 2 * P.clr", "P.z_ring - P.z_pcb", z="P.z_pcb"))

# ---------------------------------------------------------------- Platine
step = os.path.join(HERE, "buttbin_carrier.step")
if os.path.isfile(step):
    import Import
    before = set(o.Name for o in doc.Objects)
    Import.insert(step, doc.Name)
    pcb = [o for o in doc.Objects if o.Name not in before and not o.InList]
    for o in pcb:
        o.Label = "Platine"
        expr(o, **{"Placement.Base.z": "P.z_pcb"})   # STEP aus KiCad: Unterseite bei z = 0
else:
    pcb = [cyl("Platine_Platzhalter", "P.pcb_d", "P.pcb_t", z="P.z_pcb")]

# Leuchtring mit Kragen: der Kragen steht innen im Oberteil auf dem Platinenrand (ausserhalb der LEDs)
ring = cut("Leuchtring",
           fuse("R_Koerper", cyl("R_aussen", "P.d_out", "P.ring_h", z="P.z_ring"),
                cyl("R_Kragen", "P.pcb_d + 2 * P.clr - 0.1", "P.z_ring - P.z_pcb - P.pcb_t", z="P.z_pcb + P.pcb_t")),
           cyl("R_innen", "P.ring_id", "P.ring_h", z="P.z_ring"),
           cyl("R_Kragen_innen", "P.pcb_d + 2 * P.clr - 0.1 - 2 * P.collar_w", "P.z_ring - P.z_pcb - P.pcb_t",
               z="P.z_pcb + P.pcb_t"))

dome = ellipsoid("Kuppel_Positiv", "P.z_dome")

# Gussform: Block mit der Kuppel als Hohlraum, offen nach oben (Harz einfuellen, flache Seite = Unterseite)
mold = cut("Gussform_Negativ",
           cyl("G_Block", "P.d_out + 2 * P.mold_wall", "P.dome_h + P.mold_wall", x="P.mold_x"),
           ellipsoid("G_Hohlraum", "P.dome_h + P.mold_wall", x="P.mold_x", lower=True))

doc.recompute()

# ---------------------------------------------------------------- Baugruppe + Einzelteile
# Baugruppe: die Teile selbst in Einbaulage. Einzelteile: Verknuepfungen darauf, nebeneinander auf z = 0
# gestellt (Druckbett) - sie folgen jeder Parameteraenderung. Hilfskoerper: Zylinder und Werkzeuge der Booleschen.
ASM = ["Gummimuffe", "Unterteil", "Knopfzelle", "Zellendeckel", "Wellenfeder", "Oberteil", "Leuchtring",
       "Kuppel_Positiv"]
helpers = [o for o in doc.Objects if o.TypeId.startswith("Part::") and o.Name not in ASM + ["Gussform_Negativ"]
           and o not in pcb]
asm = doc.addObject("App::DocumentObjectGroup", "Baugruppe")
for name in ASM:
    asm.addObject(doc.getObject(name))
for o in pcb:
    asm.addObject(o)
aux = doc.addObject("App::DocumentObjectGroup", "Hilfskoerper")
for o in helpers:
    aux.addObject(o)
# Druckteile mit der Unterkante, auf die sie gestellt werden (Gussform steht schon auf z = 0)
PRINT = [("Unterteil", "0"), ("Zellendeckel", "P.base_h - P.lid_t"), ("Oberteil", "P.z_skirt"),
         ("Leuchtring", "P.z_pcb + P.pcb_t"), ("Kuppel_Positiv", "P.z_dome"), ("Gummimuffe", "0")]
parts = doc.addObject("App::DocumentObjectGroup", "Einzelteile")
for i, (name, zmin) in enumerate(PRINT):
    ln = doc.addObject("App::Link", name + "_einzeln")
    ln.LinkedObject = doc.getObject(name)
    expr(ln, **{"Placement.Base.x": "%d * (P.d_out + 10)" % i, "Placement.Base.y": "-(P.d_out + 30)",
                "Placement.Base.z": "-(%s)" % zmin})
    parts.addObject(ln)
parts.addObject(doc.getObject("Gussform_Negativ"))
doc.recompute()

PARTS = {"Gummimuffe": (0.2, 0.2, 0.2), "Unterteil": (0.35, 0.22, 0.15), "Knopfzelle": (0.75, 0.75, 0.78),
         "Zellendeckel": (0.55, 0.4, 0.3), "Wellenfeder": (0.6, 0.6, 0.65), "Oberteil": (0.35, 0.22, 0.15),
         "Leuchtring": (0.95, 0.95, 0.9), "Kuppel_Positiv": (0.9, 0.75, 0.45), "Gussform_Negativ": (0.3, 0.5, 0.7)}
if App.GuiUp:
    import FreeCADGui as Gui
    for o in helpers:
        o.ViewObject.Visibility = False
    for name, rgb in PARTS.items():
        vo = doc.getObject(name).ViewObject
        vo.ShapeColor = rgb
    doc.getObject("Leuchtring").ViewObject.Transparency = 50
    doc.getObject("Kuppel_Positiv").ViewObject.Transparency = 40
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewIsometric()
else:
    out = os.environ.get("KNAUF_OUT", os.path.join(HERE, "knauf.FCStd"))
    doc.saveAs(out)
    print("gespeichert", out)
    # STL je Druckteil (Gummimuffe: aus TPU drucken oder als Schlauchstueck kaufen)
    import Mesh
    stl = os.path.join(os.path.dirname(out), "stl")
    os.makedirs(stl, exist_ok=True)
    for name, _ in PRINT + [("Gussform_Negativ", "0")]:
        Mesh.export([doc.getObject(name)], os.path.join(stl, name + ".stl"))
    print("STL in", stl)
