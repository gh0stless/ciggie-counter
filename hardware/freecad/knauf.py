"""Butt-Bin-Knauf, Konstruktion zum Drucken (FreeCAD 1.x).

Aufbau von unten (z = 0 = Unterkante Knauf = Unterkante des Original-Griffs):
  Unterteil   Schacht ueber den Original-Griff (mit Gummimuffe), Zellenfach fuer einen CR2450-Halter mit
              Kabel, darueber die Platinentasche (Umriss mit beiden Abflachungen = Verdrehschutz), Schraubdom
              M2 und Nase fuer die Platine; oben Innengewinde
  Platine     Rev 0.8 (STEP aus KiCad), liegt auf einem schmalen Rand, M2-Nylonschraube + Nase
  Leuchtring  klar (Resin), Verbindungsstueck: unten und oben Aussengewinde, dazwischen das sichtbare Band;
              unten kleine Lichtleiter-Nasen ueber den LEDs
  Haube       unten Innengewinde, oben die Platte mit dem 30-mm-Loch fuer den Button
  Button      Retro+ "Haute Mechanical Button" S30, Litze an die Stifte geloetet
Zum Zellenwechsel: Haube samt Ring vom Unterteil schrauben, Schraube raus, Platine anheben (Litzen mit Spiel).
Beim Schrauben verdrillen sich die Button-Litzen um die Gangzahl (gut 3 Umdrehungen): Litzen lang und weich.
Aufruf: freecadcmd knauf.py  -> knauf.FCStd, knauf.obj (Blender), druck/*.stl + *.step und die Pruefungen.
Masse vom Button, Zellenhalter und Schlauch sind aus den Angeboten abgelesen - nach Eintreffen nachmessen.
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
D_OUT = 44.0             # Aussendurchmesser (bei 40 waeren die Gewindewaende nur ~1 mm)
WALL = 2.0               # Wand der Haube ueber dem Gewinde
SLEEVE_T = 2.5           # Gummimuffe: Silikonschlauch OD 21 x ID 16 mm (Meterware, AliExpress), 30 mm lang
SLEEVE_SQUEEZE = 0.0     # ID 16 sitzt unten genau auf dem Griff, oben wird er auf Ø 20 gedehnt (25 %)
FLOOR_T = 1.5            # Boden zwischen Schacht und Zellenfach
# CR2450-Halter mit Drehdeckel (AliExpress 1005013142257052): Gehaeuse Ø29, mit den Loetfahnen 33 mm breit,
# Fahnen 30,5 mm auseinander; Litzen an die Fahnen geloetet. Hoehe nicht angegeben - am Teil nachmessen.
HOLDER_D, HOLDER_H = 29.0, 7.0
TAB_PITCH, TAB_W, TAB_SPAN = 30.5, 4.0, 33.0     # Fahnen: Abstand, Breite, Gesamtbreite ueber die Fahnen
HOLDER_CLR = 0.5
BOT_H = 3.0              # Luft unter der Platine: Bauteile unten (C1 1,7 mm), Loetstellen, Litzen
# ---- Platine (Masse aus dem KiCad-Generator, Koordinaten wie im STEP: Mitte 0/0, y nach oben = KiCad -y)
PCB_R, PCB_FLAT_X, PCB_FLAT_Y = 17.0, -14.0, -16.0   # Kreis mit Abflachung links und unten (Programmier-Klemme)
POCKET_CLR = 0.2         # Spiel in der Tasche
LEDGE_W = 0.8            # Auflage am Rand (unten sitzen die Pads bis 1 mm an den Rand)
SCREW_XY, SCREW_PILOT = (0.0, 15.0), 1.6         # Loch H2 (M2 Nylon) mittig ueber der Antenne, Kernloch im Dom
SCREW_BOSS_D = 4.4
PEG_XY, PEG_D, PEG_POST_D = (10.5, -11.0), 1.3, 2.6   # Loch H1 Ø1,5 unten rechts: Nase Ø1,3 auf einem Sockel
LED_R, LED_ANG, LED_IN = 15.4, (30, 65, 115, 150, 230, 310), {150: 1.0}   # wie gen_pcb.py (Bildschirmwinkel)
# ---- Gewinde Unterteil/Ring und Ring/Haube: M40 x 1,5 (Aussengewinde am Ring), 5 mm = gut 3 Umdrehungen
TH_D, TH_P, TH_DEPTH, TH_L = 40.0, 1.5, 0.92, 5.0
TH_CLR = 0.2             # Spiel radial und axial (MJF/SLS und Resin)
RING_IN = 34.0           # Innendurchmesser des Rings (Platine Ø34 und die Litzen gehen hindurch)
RING_H = 5.0             # sichtbares Band
LIGHT_GAP, LIGHT_W, LIGHT_H, LIGHT_R_IN = 0.3, 2.4, 1.2, 14.6   # Lichtleiter-Nasen ueber den LEDs
PANEL_T = 2.5            # Platte fuer den Button (Klemmbereich der Schnappnasen am Teil pruefen)
EDGE_R = 1.0             # Rundung der aeusseren Kanten oben und unten
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
PRINT = ("Knauf_Unterteil", "Leuchtband", "Knauf_Haube")   # Druckteile -> druck/


def add(name, shape, rgb):
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    COLORS[name] = rgb
    return o


def cone(r1, r2, h, z):
    return Part.makeCone(r1, r2, h, V(0, 0, z))


def cyl(r, h, z, xy=(0.0, 0.0)):
    return Part.makeCylinder(r, h, V(xy[0], xy[1], z))


def tube(r_out, r_in, h, z):
    return cyl(r_out, h, z).cut(cyl(r_in, h, z))


def outline(grow, h, z):
    """Platinenumriss (Kreis mit zwei Abflachungen), um grow vergroessert, als Prisma."""
    r = PCB_R + grow
    big = 2 * r + 2
    s = cyl(r, h, z)
    s = s.common(Part.makeBox(big, big, h, V(PCB_FLAT_X - grow, -r - 1, z)))
    return s.common(Part.makeBox(big, big, h, V(-r - 1, PCB_FLAT_Y - grow, z)))


HELIX_LEN = 6 * TH_P      # immer dieselbe Helix: FreeCAD naehert sie an, verschieden lange laufen auseinander


def ridge(r_root, depth, length, z0, widen=0.0, ref=None):
    """Gewindegang (Flanken 60 Grad, Spitze abgeflacht) aussen an r_root, auf z0..z0+length zugeschnitten.
    ref: Bezugshoehe der Helix (Aussen- und Innengewinde mit gleichem ref greifen ineinander);
    widen macht den Gang breiter (Gegenstueck mit Spiel)."""
    ref = z0 if ref is None else ref
    assert ref - TH_P <= z0 and z0 + length <= ref - TH_P + HELIX_LEN, "Helix zu kurz"
    helix = Part.makeHelix(TH_P, HELIX_LEN, r_root)
    hb, ht = TH_P * 0.42 + widen, TH_P * 0.08 + widen
    pts = [V(r_root - 0.05, 0, -hb), V(r_root + depth, 0, -ht), V(r_root + depth, 0, ht), V(r_root - 0.05, 0, hb)]
    sweep = Part.Wire(helix).makePipeShell([Part.makePolygon(pts + [pts[0]])], True, True)
    sweep.translate(V(0, 0, ref - TH_P))
    return sweep.common(cyl(r_root + depth + 1, length, z0))


R_MAJ = TH_D / 2
R_MIN = R_MAJ - TH_DEPTH


def male(z0):
    """Aussengewinde des Rings: Rohr bis zum Kerndurchmesser plus Gang."""
    return tube(R_MIN, RING_IN / 2, TH_L, z0).fuse(ridge(R_MIN, TH_DEPTH, TH_L, z0))


def female_cut(z_male):
    """Was aus Unterteil/Haube fuer das Innengewinde herausgeschnitten wird (mit Spiel), passend zum
    Aussengewinde ab z_male. Laenge und Ansatz nicht aendern: bei anderen Werten (z. B. 5,4 mm) schneidet
    OpenCASCADE die Nut stillschweigend nicht - die Spitzenpruefung unten meldet das."""
    z0, h = z_male - TH_CLR, TH_L + TH_CLR + 0.01
    return cyl(R_MIN + TH_CLR, h, z0).fuse(ridge(R_MIN + TH_CLR - 0.05, TH_DEPTH + TH_CLR, h, z0, TH_CLR / 2, z_male))


def round_edges(shape, z_list, r=EDGE_R):
    """Aeussere Kreiskanten bei den angegebenen Hoehen runden (wenn es nicht klappt, eckig lassen)."""
    edges = [e for e in shape.Edges if e.Curve.TypeId == "Part::GeomCircle"
             and abs(e.Curve.Radius - D_OUT / 2) < 0.01 and any(abs(e.Curve.Center.z - z) < 0.01 for z in z_list)]
    try:
        return shape.makeFillet(r, edges) if edges else shape
    except Exception as ex:
        print("Rundung ausgelassen:", ex)
        return shape


def led_xy():
    for a in LED_ANG:
        r = LED_R - LED_IN.get(a, 0.0)
        yield a, r * math.cos(math.radians(a)), -r * math.sin(math.radians(a))   # KiCad y nach unten


# ---- Original-Griff (nur zur Kontrolle), Gummimuffe und Schacht
g_bot, g_top, g_h = ascher_value.GRIP_D_BOTTOM / 2, ascher_value.GRIP_D_TOP / 2, ascher_value.GRIP_H
grip = cone(g_bot, g_top, g_h, 0)
sl_in = (g_bot - SLEEVE_SQUEEZE / 2, g_top - SLEEVE_SQUEEZE / 2)
sl_out = (sl_in[0] + SLEEVE_T, sl_in[1] + SLEEVE_T)
sleeve = cone(sl_out[0], sl_out[1], g_h, 0).cut(cone(sl_in[0], sl_in[1], g_h, 0))
bore = cone(sl_out[0] + 0.1, sl_out[1] + 0.1, g_h + 1.0, -0.01)

# ---- Platine aus KiCad (STEP mit Bauteilen, Mitte im Ursprung: kicad-cli ... --user-origin 100x100mm)
z_pocket = g_h + 1.0 + FLOOR_T
z_pocket_top = z_pocket + HOLDER_H + HOLDER_CLR
z_pcb = z_pocket_top + BOT_H
step = os.path.join(HERE, "buttbin_carrier.step")
board = Part.read(step)
board.translate(V(0, 0, z_pcb))
bb = [s.BoundBox for s in board.Solids]
pcb_t = max(b.ZLength for b in bb if b.XLength > 30) if bb else 1.6     # Platinenkoerper
z_pcb_top = z_pcb + pcb_t
z_parts_top = board.BoundBox.ZMax                    # hoechstes Bauteil oben (Modul)
z_led_top = max(b.ZMax for b in bb if b.XLength < 2.5 and b.YLength < 2.5 and b.ZMin > z_pcb_top - 0.1
                and math.hypot(b.Center.x, b.Center.y) > 13.5)

# ---- Hoehen: Ring-Unterkante (Gewinde) knapp ueber den LEDs, das Band darueber, dann die Haube
z_spigot = z_led_top + LIGHT_GAP                     # Unterkante Ring (Gewindestutzen)
z_ring = z_spigot + TH_L                             # Unterkante sichtbares Band = Oberkante Unterteil
z_hood = z_ring + RING_H                             # Unterkante Haube
below = BTN_BODY_H + PIN_LEN + WIRE_BEND             # unter der Platte bis zur Unterkante des Kabelbogens
z_panel = max(z_parts_top + GAP + below, z_hood + TH_L + 3.0)   # Oberkante Platte

# ---- Unterteil
base = cyl(D_OUT / 2, z_ring, 0)
base = base.cut(bore)
base = base.cut(cyl(HOLDER_D / 2 + HOLDER_CLR, z_pocket_top - z_pocket, z_pocket))         # Zellenfach
tab_slot = Part.makeBox(TAB_SPAN + 2 * HOLDER_CLR, TAB_W + 2 * HOLDER_CLR, z_pocket_top - z_pocket,
                        V(-(TAB_SPAN / 2 + HOLDER_CLR), -(TAB_W / 2 + HOLDER_CLR), z_pocket))
base = base.cut(tab_slot)                                                                   # Fahnen
base = base.cut(outline(-LEDGE_W, z_pcb - z_pocket_top + 0.01, z_pocket_top))              # unter der Platine
base = base.cut(outline(POCKET_CLR, z_spigot - TH_CLR - z_pcb + 0.01, z_pcb))               # Tasche bis zum Ring
base = base.cut(female_cut(z_spigot))                                                      # Innengewinde
# Schraubdom und Nase: vom Zellenfach-Deckel bis unter die Platine, haengen seitlich an der Wand
boss = cyl(SCREW_BOSS_D / 2, z_pcb - z_pocket_top, z_pocket_top, SCREW_XY)
boss = boss.cut(cyl(SCREW_PILOT / 2, z_pcb - z_pocket_top + 0.01, z_pocket_top - 0.005, SCREW_XY))
post = cyl(PEG_POST_D / 2, z_pcb - z_pocket_top, z_pocket_top, PEG_XY)
peg = cyl(PEG_D / 2, pcb_t + 0.6, z_pcb, PEG_XY)
base = base.fuse([boss, post, peg]).removeSplitter()
base = round_edges(base, (0.0,))
add("Knauf_Unterteil", base, (0.75, 0.04, 0.03))
add("Gummimuffe", sleeve, (0.1, 0.1, 0.1))
add("Original_Griff", grip, (0.06, 0.06, 0.06))
holder = cyl(HOLDER_D / 2, HOLDER_H, z_pocket).fuse(
    Part.makeBox(TAB_SPAN, TAB_W, 0.4, V(-TAB_SPAN / 2, -TAB_W / 2, z_pocket + 1.0)))
add("Zellenhalter", holder, (0.92, 0.9, 0.85))
add("Platine", board, (0.1, 0.4, 0.15))

# ---- Leuchtring: Band + Gewindestutzen unten und oben + Lichtleiter-Nasen ueber den LEDs
ring = tube(D_OUT / 2, RING_IN / 2, RING_H, z_ring)
ring = ring.fuse([male(z_spigot), male(z_hood)])
for a, x, y in led_xy():
    nose = Part.makeBox(RING_IN / 2 - LIGHT_R_IN + 0.5, LIGHT_W, LIGHT_H, V(LIGHT_R_IN, -LIGHT_W / 2, z_spigot))
    nose.rotate(V(0, 0, 0), V(0, 0, 1), math.degrees(math.atan2(y, x)))
    ring = ring.fuse(nose)
ring = ring.removeSplitter()
add("Leuchtband", ring, (1.0, 0.85, 0.4))

# ---- Button: Hoehe der Platte ergibt sich aus dem Platz darunter (Stifte, Loetstelle, Luft zum Modul)
pins = Part.makeCompound([Part.makeBox(0.5, 2.8, PIN_LEN, V(sx * PIN_X - 0.25, -1.4, z_panel - BTN_BODY_H - PIN_LEN))
                          for sx in (-1, 1)])
add("Button_Stifte", pins, (0.75, 0.75, 0.78))
add("Button_Rand", cyl(BTN_BODY_D / 2 - 0.2, BTN_BODY_H, z_panel - BTN_BODY_H)
    .fuse(cyl(BTN_BEZEL_D / 2, BTN_BEZEL_H, z_panel)), (0.75, 0.04, 0.03))
add("Button_Kappe", cyl(BTN_CAP_D / 2, BTN_CAP_H, z_panel + BTN_BEZEL_H), (0.75, 0.04, 0.03))
for k, sx in enumerate((-1, 1)):
    add("Kabelbogen_%d" % (k + 1), Part.makeBox(SOLDER_W, SOLDER_T, WIRE_BEND,
        V(sx * PIN_X - SOLDER_W / 2, -SOLDER_T / 2, z_panel - BTN_BODY_H - PIN_LEN - WIRE_BEND)), (0.9, 0.9, 0.2))

# ---- Haube: unten Innengewinde, Rohr bis zur Platte, Loch fuer den Button
# Die Bohrung beginnt 0,5 mm ueber dem Ende der Gewindenut: fast deckungsgleiche Flaechen an der Helix
# bringen OpenCASCADE durcheinander (die Haube kaeme dann ungeschnitten heraus)
LIP = 0.5
hood = cyl(D_OUT / 2, z_panel - z_hood, z_hood)
hood = hood.cut(cyl(D_OUT / 2 - WALL, z_panel - PANEL_T - (z_hood + TH_L + LIP), z_hood + TH_L + LIP))
hood = hood.cut(cyl(R_MIN - 0.1, TH_L + LIP + 0.01, z_hood - 0.01))           # Mitte bis zur Bohrung frei
hood = hood.cut(cyl(BTN_BODY_D / 2, PANEL_T + 1, z_panel - PANEL_T - 0.5))     # 30-mm-Loch
hood = round_edges(hood, (z_panel,))
hood = hood.cut(female_cut(z_hood))
add("Knauf_Haube", hood, (0.02, 0.02, 0.02))
doc.recompute()

# ---- Pruefung
knob_top = z_panel + BTN_BEZEL_H + BTN_CAP_H
print("Knauf Ø%.0f: %.1f mm hoch (Unterkante bis Kappe), mit Ascher gesamt %.1f mm"
      % (D_OUT, knob_top, knob_top + ascher_value.H + ascher_value.STAMP - ascher_value.GRIP_H))
print("Platine bei z = %.1f (%.2f dick), LEDs bis %.1f, Modul bis %.1f; Ring %.1f..%.1f, Band %.1f..%.1f, Platte %.1f"
      % (z_pcb, pcb_t, z_led_top, z_parts_top, z_spigot, z_hood + TH_L, z_ring, z_hood, z_panel))
print("Gewinde M%.0f x %.1f, %.1f Umdrehungen; Wand Ring %.2f mm (Kern bis innen), Unterteil/Haube %.2f mm"
      % (TH_D, TH_P, TH_L / TH_P, R_MIN - RING_IN / 2, D_OUT / 2 - (R_MAJ + TH_CLR)))
print("Zellenfach Ø%.1f, Wand zum Aussenrand %.1f mm; Boden ueber dem Schacht %.1f mm; Schraube M2 x %.0f (Nylon)"
      % (HOLDER_D + 2 * HOLDER_CLR, D_OUT / 2 - HOLDER_D / 2 - HOLDER_CLR, FLOOR_T, math.ceil(pcb_t + z_pcb - z_pocket_top)))
names = list(COLORS)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        if {a, b} == {"Original_Griff", "Gummimuffe"}:
            continue                                  # gewollt: Muffe sitzt mit Uebermass auf dem Griff
        v = doc.getObject(a).Shape.common(doc.getObject(b).Shape).Volume
        if v > 0.5:
            print("UEBERSCHNEIDUNG %s / %s: %.1f mm3" % (a, b, v))
# Boolesche Operationen mit Helixflaechen sind unzuverlaessig (auch common): Gewindespitzen des Rings
# zusaetzlich als Punkte gegen Unterteil und Haube pruefen
tips = [p for p in ring.tessellate(0.3)[0] if math.hypot(p.x, p.y) > R_MAJ - 0.5][::5]
for n in ("Knauf_Unterteil", "Knauf_Haube"):
    s = doc.getObject(n).Shape
    hit = sum(1 for p in tips if s.isInside(p, 0.05, False))
    print("Gewindespitzen im %s: %d von %d%s" % (n, hit, len(tips), "" if hit == 0 else "  <-- FEHLER"))
for n in PRINT:
    s = doc.getObject(n).Shape
    print("%-16s gueltig %s, %d Koerper, %.1f cm3" % (n, s.isValid(), len(s.Solids), s.Volume / 1000))

if not App.GuiUp:
    out = os.environ.get("KNAUF_OUT", os.path.join(HERE, "knauf.FCStd"))
    doc.saveAs(out)
    ascher_value.export_obj([doc.getObject(n) for n in COLORS], COLORS, os.path.splitext(out)[0] + ".obj")
    if not os.environ.get("KNAUF_OUT"):
        import Mesh
        import MeshPart
        dd = os.path.join(HERE, "druck")
        os.makedirs(dd, exist_ok=True)
        for n in PRINT:
            s = doc.getObject(n).Shape
            s.exportStep(os.path.join(dd, n + ".step"))
            MeshPart.meshFromShape(Shape=s, LinearDeflection=0.02, AngularDeflection=0.2).write(
                os.path.join(dd, n + ".stl"))
        # Platine mit Bauteilen als Referenz (Ansehen, Probe-Passung, Dummy drucken), in Einbaulage
        MeshPart.meshFromShape(Shape=doc.getObject("Platine").Shape, LinearDeflection=0.02,
                               AngularDeflection=0.2).write(os.path.join(dd, "Platine_Referenz.stl"))
    print("gespeichert", out)
