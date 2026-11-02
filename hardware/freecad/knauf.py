"""Butt-Bin-Knauf, vereinfachte Konstruktion (FreeCAD 1.x) - Platzpruefung vor dem Detailentwurf.

Aufbau von unten (z = 0 = Unterkante Knauf = Unterkante des Original-Griffs):
  Unterteil   Schacht ueber den Original-Griff (mit Gummimuffe), Zellenfach fuer einen CR2450-Halter mit
              Kabel, Auflage fuer die Platine, oben ein Hals (spaeter mit Gewinde)
  Leuchtring  klare Scheibe auf der Schulter, wird von der Haube eingeklemmt
  Platine     fest im Unterteil (STEP aus KiCad)
  Haube       hohl, oben die Platte mit dem Loch fuer den Arcade-Button
  Button      Sanwa OBSF-30 (fremd/sanwa_obsf30.step, nicht im Repo) oder kompakter Button mit eingebautem
              Schalter (Standard: roter Button dieser Bauart von AliExpress; Masse nach dem Joy-IT-Datenblatt),
              mit Flachsteckhuelsen und Kabelbogen; KNAUF_BUTTON=sanwa fuer den Sanwa
Noch ohne Gewinde und Rundungen. Masse oben als Konstanten; die Hoehen ergeben sich daraus.
Aufruf: freecadcmd knauf.py  -> knauf.FCStd, knauf.obj (Blender) und die Pruefung der Abstaende.
"""
import math
import os
import sys

import FreeCAD as App
import Part

V = App.Vector
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.getcwd()
sys.path.insert(0, HERE)
os.environ["ASCHER_MODUL"] = "1"
import ascher_value                       # Masse des Original-Griffs

# ---- Knauf
D_OUT = 40.0             # Aussendurchmesser
WALL = 2.0               # Wand der Haube
SLEEVE_T = 1.5           # Gummimuffe: Wandstaerke
SLEEVE_SQUEEZE = 0.4     # Muffe innen so viel kleiner als der Griff
FLOOR_T = 1.5            # Boden zwischen Schacht und Zellenfach
HOLDER_D, HOLDER_H = 30.0, 7.0   # CR2450-Halter mit Kabel (nachmessen, wenn er da ist)
HOLDER_CLR = 0.5
BOT_H = 3.0              # Luft unter der Platine: Bauteile unten, Loetstellen, Kabelbogen vom Zellenhalter
PCB_D, PCB_T = 34.0, 1.6
LEDGE_W = 1.2            # Auflage der Platine (Ring)
NECK_H = 6.0             # Hals oben am Unterteil (spaeter Gewinde), ragt in die Haube
RING_H = 3.0             # Leuchtring
PANEL_T = 2.5            # Platte fuer den Button (Schnappbefestigung des Sanwa)
# ---- Button und Anschluss (KNAUF_BUTTON=kompakt | sanwa)
BUTTON = os.environ.get("KNAUF_BUTTON", "kompakt")
# Kompakter 30-mm-Button mit eingebautem Mikroschalter (gewaehlt: rot von AliExpress). Masse nach dem
# Datenblatt des Joy-IT "Mini Arcade Button" (Reichelt ARC BUTTON M ..), gleiche Bauart:
# Gehaeuse Ø30 und 17 mm unter der Platte (Schalter innen), Rand Ø33 x 3,5, Kappe Ø24,5 x 5
JOY_BODY_D, JOY_BODY_H, JOY_BEZEL_D, JOY_BEZEL_H, JOY_CAP_D, JOY_CAP_H = 30.0, 17.0, 33.0, 3.5, 24.5, 5.0
# Die Fahnen kommen seitlich aus dem Gehaeuse (Fotos des Ali-Angebots, YingLucky) und wuerden die Haube
# beruehren: nach unten umgebogen, Litze angeloetet. Laenge der gebogenen Fahne unter dem Gehaeuse geschaetzt.
JOY_TAB_LEN, JOY_TAB_X = 4.0, JOY_BODY_D / 2 - 1.5
SANWA_STEP = os.path.join(HERE, "fremd", "sanwa_obsf30.step")
SANWA_BEZEL_H = 2.6      # Rand ueber der Platte (aus dem Modell gemessen)
FASTON_OVER = 7.0        # Flachsteckhuelse steckt so weit auf der Zunge
FASTON_LEN = 14.0        # Huelse 2,8 mm gerade, mit Isolierung (Winkelhuelsen: deutlich kuerzer nach unten)
FASTON_W, FASTON_T = 4.0, 3.0
WIRE_BEND = 5.0          # Kabelbogen unter der Huelse (Silikonlitze ~0,25 mm2)
GAP = 1.0                # Luft zum Modul

doc = App.newDocument("Knauf")
COLORS = {}


def add(name, shape, rgb):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    COLORS[name] = rgb
    return o


def cone(r1, r2, h, z):
    return Part.makeCone(r1, r2, h, V(0, 0, z))


def cyl(r, h, z):
    return Part.makeCylinder(r, h, V(0, 0, z))


# ---- Original-Griff (nur zur Kontrolle), Gummimuffe und Schacht
g_bot, g_top, g_h = ascher_value.GRIP_D_BOTTOM / 2, ascher_value.GRIP_D_TOP / 2, ascher_value.GRIP_H
grip = cone(g_bot, g_top, g_h, 0)
sl_in = (g_bot - SLEEVE_SQUEEZE / 2, g_top - SLEEVE_SQUEEZE / 2)
sl_out = (sl_in[0] + SLEEVE_T, sl_in[1] + SLEEVE_T)
sleeve = cone(sl_out[0], sl_out[1], g_h, 0).cut(cone(sl_in[0], sl_in[1], g_h, 0))
bore = cone(sl_out[0] + 0.1, sl_out[1] + 0.1, g_h + 1.0, -0.01)

# ---- Unterteil: Schacht, Zellenfach, Platinenauflage, Schulter, Hals
z_pocket = g_h + 1.0 + FLOOR_T
z_pocket_top = z_pocket + HOLDER_H + HOLDER_CLR
z_pcb = z_pocket_top + BOT_H
z_neck_top = z_pcb + PCB_T + 1.0
z_shoulder = z_neck_top - NECK_H
neck_r = D_OUT / 2 - WALL - 0.2                       # passt in die Haube
base = cyl(D_OUT / 2, z_shoulder, 0).fuse(cyl(neck_r, z_neck_top - z_shoulder, z_shoulder))
base = base.cut(bore)
base = base.cut(cyl(HOLDER_D / 2 + HOLDER_CLR, z_pocket_top - z_pocket, z_pocket))         # Zellenfach
base = base.cut(cyl(PCB_D / 2 - LEDGE_W, z_pcb - z_pocket_top + 0.01, z_pocket_top))       # unter der Platine
base = base.cut(cyl(PCB_D / 2 + 0.3, z_neck_top - z_pcb + 0.01, z_pcb))                    # Platine von oben
add("Knauf_Unterteil", base, (0.75, 0.04, 0.03))
add("Gummimuffe", sleeve, (0.1, 0.1, 0.1))
add("Original_Griff", grip, (0.06, 0.06, 0.06))
add("Zellenhalter", cyl(HOLDER_D / 2, HOLDER_H, z_pocket), (0.15, 0.15, 0.15))
add("Leuchtband", cyl(D_OUT / 2, RING_H, z_shoulder).cut(cyl(neck_r + 0.2, RING_H, z_shoulder)), (1.0, 0.85, 0.4))

# ---- Platine aus KiCad (STEP mit Bauteilen), sonst Platzhalter
step = os.path.join(HERE, "buttbin_carrier.step")
if os.path.isfile(step):
    board = Part.read(step)
    # der KSC6 unten (7,7 mm hoch) wird beim Arcade-Button nicht bestueckt: alles weglassen, was weiter als
    # 1,5 mm unter die Platine ragt
    board = Part.makeCompound([s for s in board.Solids if s.BoundBox.ZMin > -1.5])
    board.translate(V(0, 0, z_pcb))
else:
    board = cyl(PCB_D / 2, PCB_T, z_pcb).fuse(Part.makeBox(16, 24, 3.3, V(-8, -12, z_pcb + PCB_T)))
add("Platine", board, (0.1, 0.4, 0.15))
z_parts_top = board.BoundBox.ZMax                    # hoechstes Bauteil oben (Modul)

# ---- Button mit Flachsteckhuelsen: Hoehe der Platte ergibt sich aus dem Platz darunter
def sanwa_button():
    solids = sorted(Part.read(SANWA_STEP).Solids, key=lambda s: s.BoundBox.YMax)   # Schalter, Gehaeuse, Kappe
    bb = solids[1].BoundBox
    m = App.Matrix()
    m.rotateX(math.radians(90))                      # im STEP zeigt +y nach oben
    out = []
    for s in solids:
        s = s.copy()
        s.translate(V(-(bb.XMin + bb.XMax) / 2, -(bb.YMax - SANWA_BEZEL_H), -(bb.ZMin + bb.ZMax) / 2))
        out.append(s.transformGeometry(m))           # Platte (Oberkante) bei z = 0
    return out


def joyit_button():
    """Aus dem Datenblatt: Gehaeuse mit eingebautem Schalter, Rand, Kappe; dazu die zwei umgebogenen Fahnen."""
    tabs = Part.makeCompound([Part.makeBox(0.5, 2.8, JOY_TAB_LEN, V(sx * JOY_TAB_X - 0.25, -1.4,
                                                                    -JOY_BODY_H - JOY_TAB_LEN)) for sx in (-1, 1)])
    housing = cyl(JOY_BODY_D / 2 - 0.2, JOY_BODY_H, -JOY_BODY_H).fuse(cyl(JOY_BEZEL_D / 2, JOY_BEZEL_H, 0))
    return [tabs, housing, cyl(JOY_CAP_D / 2, JOY_CAP_H, JOY_BEZEL_H)]


sanwa = sanwa_button() if BUTTON == "sanwa" else joyit_button()
switch, housing, cap = sanwa
tip = switch.BoundBox.ZMin                           # Ende der Flachsteckzungen (negativ)
# Mitte jeder Zunge aus einem Schnitt kurz ueber dem Zungenende
tabs = [w.BoundBox for w in switch.slice(V(0, 0, 1), tip + 1.0)]
fastons = []
if BUTTON == "sanwa":
    # Flachsteckhuelsen auf den Zungen, Kabelbogen darunter
    for t in tabs:
        fastons.append(Part.makeBox(FASTON_W, FASTON_T, FASTON_LEN, V(t.Center.x - FASTON_W / 2, t.Center.y - FASTON_T / 2,
                                                                      tip + FASTON_OVER - FASTON_LEN)))
    below = FASTON_LEN - FASTON_OVER + WIRE_BEND     # so weit reicht der Anschluss unter die Zungen
else:
    # angeloetete Litze: nur Loetstelle und Kabelbogen unter der Fahne
    below = WIRE_BEND
z_panel = z_parts_top + GAP + below - tip            # Oberkante Platte
for s, name, rgb in ((switch, "Sanwa_Mikroschalter", (0.6, 0.6, 0.6)), (housing, "Sanwa_Rand", (0.75, 0.04, 0.03)),
                     (cap, "Sanwa_Kappe", (0.75, 0.04, 0.03))):
    s.translate(V(0, 0, z_panel))
    add(name, s, rgb)
for k, f in enumerate(fastons):
    f.translate(V(0, 0, z_panel))
    add("Flachsteckhuelse_%d" % (k + 1), f, (0.2, 0.3, 0.8))
# Kabelbogen unter der Huelse (Sanwa) bzw. Loetstelle mit Bogen unter der Fahnenspitze (kompakt)
ends = [(f.BoundBox.Center, f.BoundBox.ZMin) for f in fastons] or [(t.Center, tip + z_panel) for t in tabs]
for k, (c, z_end) in enumerate(ends):
    bend = Part.makeBox(FASTON_W, FASTON_T, WIRE_BEND, V(c.x - FASTON_W / 2, c.y - FASTON_T / 2, z_end - WIRE_BEND))
    add("Kabelbogen_%d" % (k + 1), bend, (0.9, 0.9, 0.2))

# ---- Haube: Rohr ueber dem Hals bis zur Platte, Loch fuer den Button
z_hood = z_shoulder + RING_H
hood = cyl(D_OUT / 2, z_panel - z_hood, z_hood).cut(cyl(D_OUT / 2 - WALL, z_panel - PANEL_T - z_hood, z_hood))
hood = hood.cut(cyl(15.0, PANEL_T + 1, z_panel - PANEL_T - 0.5))     # 30-mm-Loch
add("Knauf_Haube", hood, (0.02, 0.02, 0.02))
doc.recompute()

# ---- Pruefung
knob_top = max(s.BoundBox.ZMax for s in sanwa)
hood_in = D_OUT / 2 - WALL
sw_bb = switch.BoundBox
r_switch = max(math.hypot(x, y) for x in (sw_bb.XMin, sw_bb.XMax) for y in (sw_bb.YMin, sw_bb.YMax))
print("Knauf: %.1f mm hoch (Unterkante bis Kappe), mit Ascher gesamt %.1f mm"
      % (knob_top, knob_top + ascher_value.H + ascher_value.STAMP - ascher_value.GRIP_H))
print("Platine bei z = %.1f, hoechstes Bauteil %.1f, Platte %.1f; Zungenende %.1f mm ueber dem Modul; %d Zungen"
      % (z_pcb, z_parts_top, z_panel, z_panel + tip - z_parts_top, len(tabs)))
print("Schalter: aeusserste Ecke %.1f mm von der Mitte, Haube innen %.1f mm -> %.1f mm seitlich frei"
      % (r_switch, hood_in, hood_in - r_switch))
print("Zellenfach Ø%.1f, Wand zum Aussenrand %.1f mm; Boden ueber dem Schacht %.1f mm"
      % (HOLDER_D + 2 * HOLDER_CLR, D_OUT / 2 - HOLDER_D / 2 - HOLDER_CLR, FLOOR_T))
names = list(COLORS)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        pair = {a.split("_")[0], b.split("_")[0]}
        if pair <= {"Original", "Gummimuffe"} or pair <= {"Flachsteckhuelse", "Sanwa"} or "Kabelbogen" in pair \
                and "Flachsteckhuelse" in pair or {a, b} == {"Sanwa_Rand", "Knauf_Haube"}:
            continue      # gewollt: Muffe auf dem Griff, Huelsen auf den Zungen, Schnappnasen in der Platte
        v = doc.getObject(a).Shape.common(doc.getObject(b).Shape).Volume
        if v > 0.5:
            print("UEBERSCHNEIDUNG %s / %s: %.1f mm3" % (a, b, v))

if not App.GuiUp:
    out = os.environ.get("KNAUF_OUT", os.path.join(HERE, "knauf.FCStd"))
    doc.saveAs(out)
    ascher_value.export_obj([doc.getObject(n) for n in COLORS], COLORS, os.path.splitext(out)[0] + ".obj")
    print("gespeichert", out)
