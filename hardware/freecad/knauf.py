"""Butt-Bin-Knauf, vereinfachte Konstruktion (FreeCAD 1.x) - Platzpruefung vor dem Detailentwurf.

Aufbau von unten (z = 0 = Unterkante Knauf = Unterkante des Original-Griffs):
  Unterteil   Schacht ueber den Original-Griff (mit Gummimuffe), Zellenfach fuer einen CR2450-Halter mit
              Kabel, oben eine flache Tasche fuer die Platine
  Platine     fest im Unterteil (STEP aus KiCad), die Ring-LEDs ragen knapp ueber die Oberkante
  Leuchtring  klarer Ring genau auf Hoehe der LEDs, zwischen Unterteil und Haube; spaeter das
              Verbindungsstueck mit Gewinde zu beiden Seiten (klar gedruckt, Resin)
  Haube       hohl, oben die Platte mit dem Loch fuer den Button
  Button      Retro+ "Haute Mechanical Button" S30 (30-mm-Loch), Litze an die Stifte geloetet
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
SLEEVE_T = 2.0           # Gummimuffe: Silikonschlauch Innen-Ø 16 x Wand 2 mm (Meterware), 30 mm lang
SLEEVE_SQUEEZE = 0.4     # Muffe innen so viel kleiner als der Griff (Silikon dehnt sich oben auf Ø 20)
FLOOR_T = 1.5            # Boden zwischen Schacht und Zellenfach
# CR2450-Halter mit Drehdeckel (AliExpress 1005013142257052): Gehaeuse Ø29, mit den Loetfahnen 33 mm breit,
# Fahnen 30,5 mm auseinander; Litzen an die Fahnen geloetet. Hoehe nicht angegeben - am Teil nachmessen.
HOLDER_D, HOLDER_H = 29.0, 7.0
TAB_PITCH, TAB_W, TAB_SPAN = 30.5, 4.0, 33.0     # Fahnen: Abstand, Breite, Gesamtbreite ueber die Fahnen
HOLDER_CLR = 0.5
BOT_H = 3.0              # Luft unter der Platine: Bauteile unten, Loetstellen, Kabelbogen vom Zellenhalter
PCB_D, PCB_T = 34.0, 1.6
LEDGE_W = 1.2            # Auflage der Platine (Ring)
PCB_OVER = 0.6          # so weit ragt die Platine ueber das Unterteil (LEDs stehen dann ganz im Ring)
RING_H = 4.0             # Leuchtring (deckt die 0603-LEDs mit Abstand ab)
PANEL_T = 2.5            # Platte fuer den Button (Klemmbereich der Schnappnasen am Teil pruefen)
# ---- Button: Retro+ "Haute Mechanical Button" S30 (AliExpress), Low-Profile-Tastaturschalter "Wind Engine"
# auf kleiner Platine, 50 Mio. Schaltspiele, 40 gf. Masse aus der Zeichnung im Angebot abgelesen (+-1 mm):
# 25,8 mm hoch samt Stiften, davon ca. 7 mm ueber der Platte; Kappe Ø25,8, Rand ca. Ø34,8.
BTN_BODY_D, BTN_BODY_H = 30.0, 14.2      # Gehaeuse unter der Platte (ohne Stifte)
BTN_BEZEL_D, BTN_BEZEL_H = 34.8, 3.0     # Rand auf der Platte
BTN_CAP_D, BTN_CAP_H = 25.8, 4.1         # Kappe ueber dem Rand
PIN_LEN, PIN_X = 4.5, 3.0                # Stifte gerade nach unten
SOLDER_W, SOLDER_T = 4.0, 3.0            # Loetstelle mit Litze
WIRE_BEND = 5.0          # Loetstelle und Kabelbogen unter dem Stift (Silikonlitze ~0,25 mm2)
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

# ---- Unterteil: Schacht, Zellenfach, Platinentasche; oben direkt der Leuchtring
z_pocket = g_h + 1.0 + FLOOR_T
z_pocket_top = z_pocket + HOLDER_H + HOLDER_CLR
z_pcb = z_pocket_top + BOT_H
z_ring = z_pcb + PCB_T - PCB_OVER                    # Oberkante Unterteil = Unterkante Leuchtring
base = cyl(D_OUT / 2, z_ring, 0)
base = base.cut(bore)
base = base.cut(cyl(HOLDER_D / 2 + HOLDER_CLR, z_pocket_top - z_pocket, z_pocket))         # Zellenfach
tab_slot = Part.makeBox(TAB_SPAN + 2 * HOLDER_CLR, TAB_W + 2 * HOLDER_CLR, z_pocket_top - z_pocket,
                        V(-(TAB_SPAN / 2 + HOLDER_CLR), -(TAB_W / 2 + HOLDER_CLR), z_pocket))
base = base.cut(tab_slot)                                                                   # Aussparung fuer die Fahnen
base = base.cut(cyl(PCB_D / 2 - LEDGE_W, z_pcb - z_pocket_top + 0.01, z_pocket_top))       # unter der Platine
base = base.cut(cyl(PCB_D / 2 + 0.3, z_ring - z_pcb + 0.01, z_pcb))                        # Platinentasche
add("Knauf_Unterteil", base, (0.75, 0.04, 0.03))
add("Gummimuffe", sleeve, (0.1, 0.1, 0.1))
add("Original_Griff", grip, (0.06, 0.06, 0.06))
holder = cyl(HOLDER_D / 2, HOLDER_H, z_pocket).fuse(
    Part.makeBox(TAB_SPAN, TAB_W, 0.4, V(-TAB_SPAN / 2, -TAB_W / 2, z_pocket + 1.0)))
add("Zellenhalter", holder, (0.92, 0.9, 0.85))
add("Leuchtband", cyl(D_OUT / 2, RING_H, z_ring).cut(cyl(D_OUT / 2 - WALL, RING_H, z_ring)), (1.0, 0.85, 0.4))

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

# ---- Button: Hoehe der Platte ergibt sich aus dem Platz darunter (Stifte, Loetstelle, Luft zum Modul)
below = BTN_BODY_H + PIN_LEN + WIRE_BEND             # unter der Platte bis zur Unterkante des Kabelbogens
z_panel = z_parts_top + GAP + below                  # Oberkante Platte
pins = Part.makeCompound([Part.makeBox(0.5, 2.8, PIN_LEN, V(sx * PIN_X - 0.25, -1.4, z_panel - BTN_BODY_H - PIN_LEN))
                          for sx in (-1, 1)])
add("Button_Stifte", pins, (0.75, 0.75, 0.78))
add("Button_Rand", cyl(BTN_BODY_D / 2 - 0.2, BTN_BODY_H, z_panel - BTN_BODY_H)
    .fuse(cyl(BTN_BEZEL_D / 2, BTN_BEZEL_H, z_panel)), (0.75, 0.04, 0.03))
add("Button_Kappe", cyl(BTN_CAP_D / 2, BTN_CAP_H, z_panel + BTN_BEZEL_H), (0.75, 0.04, 0.03))
for k, sx in enumerate((-1, 1)):
    add("Kabelbogen_%d" % (k + 1), Part.makeBox(SOLDER_W, SOLDER_T, WIRE_BEND,
        V(sx * PIN_X - SOLDER_W / 2, -SOLDER_T / 2, z_panel - BTN_BODY_H - PIN_LEN - WIRE_BEND)), (0.9, 0.9, 0.2))

# ---- Haube: Rohr vom Leuchtring bis zur Platte, Loch fuer den Button
z_hood = z_ring + RING_H
hood = cyl(D_OUT / 2, z_panel - z_hood, z_hood).cut(cyl(D_OUT / 2 - WALL, z_panel - PANEL_T - z_hood, z_hood))
hood = hood.cut(cyl(BTN_BODY_D / 2, PANEL_T + 1, z_panel - PANEL_T - 0.5))     # 30-mm-Loch
add("Knauf_Haube", hood, (0.02, 0.02, 0.02))
doc.recompute()

# ---- Pruefung
knob_top = z_panel + BTN_BEZEL_H + BTN_CAP_H
hood_in = D_OUT / 2 - WALL
print("Knauf: %.1f mm hoch (Unterkante bis Kappe), mit Ascher gesamt %.1f mm"
      % (knob_top, knob_top + ascher_value.H + ascher_value.STAMP - ascher_value.GRIP_H))
print("Platine bei z = %.1f, hoechstes Bauteil %.1f, Platte %.1f; Kabelbogen endet %.1f mm ueber dem Modul"
      % (z_pcb, z_parts_top, z_panel, GAP))
print("Button: Gehaeuse Ø%.1f, Haube innen Ø%.1f -> %.1f mm seitlich frei"
      % (BTN_BODY_D, 2 * hood_in, hood_in - BTN_BODY_D / 2))
print("Zellenfach Ø%.1f, Wand zum Aussenrand %.1f mm (an den Fahnen %.1f mm); Boden ueber dem Schacht %.1f mm"
      % (HOLDER_D + 2 * HOLDER_CLR, D_OUT / 2 - HOLDER_D / 2 - HOLDER_CLR, D_OUT / 2 - TAB_SPAN / 2 - HOLDER_CLR, FLOOR_T))
names = list(COLORS)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        if {a, b} == {"Original_Griff", "Gummimuffe"}:
            continue                                  # gewollt: Muffe sitzt mit Uebermass auf dem Griff
        v = doc.getObject(a).Shape.common(doc.getObject(b).Shape).Volume
        if v > 0.5:
            print("UEBERSCHNEIDUNG %s / %s: %.1f mm3" % (a, b, v))

if not App.GuiUp:
    out = os.environ.get("KNAUF_OUT", os.path.join(HERE, "knauf.FCStd"))
    doc.saveAs(out)
    ascher_value.export_obj([doc.getObject(n) for n in COLORS], COLORS, os.path.splitext(out)[0] + ".obj")
    print("gespeichert", out)
