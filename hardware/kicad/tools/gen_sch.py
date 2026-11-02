"""Erzeugt den Butt-Bin-Trägerplatinen-Schaltplan (KiCad 10) mit eingebetteten Symbolen.

Verbindungen laufen über Netz-Labels bzw. Power-Symbole direkt an den Pin-Enden.
"""
import os
import re
import sys
import uuid

def _kicad_share():
    """KiCad-Bibliotheken: Umgebungsvariable KICAD_SHARE, sonst die ueblichen Installationsorte (KiCad 10)."""
    cands = [os.environ.get("KICAD_SHARE", ""),
             os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "KiCad", "10.0", "share", "kicad"),
             r"C:/Program Files/KiCad/10.0/share/kicad", "/usr/share/kicad", "/Applications/KiCad/KiCad.app/Contents/SharedSupport"]
    for c in cands:
        if c and os.path.isdir(os.path.join(c, "symbols")):
            return c
    raise SystemExit("KiCad-Bibliotheken nicht gefunden: KICAD_SHARE setzen")

KLIB = os.path.join(_kicad_share(), "symbols") + os.sep
OUT = sys.argv[1]
PROJECT = "buttbin_carrier"

def uid():
    return str(uuid.uuid4())

ROOT = uid()

# ---------------------------------------------------------------- Bibliothek
def lib_block(lib, name):
    t = open(KLIB + lib, encoding="utf-8").read()
    i = t.find('(symbol "%s"' % name)
    if i < 0:
        raise KeyError(name)
    d = 0
    for j in range(i, len(t)):
        if t[j] == "(":
            d += 1
        elif t[j] == ")":
            d -= 1
            if d == 0:
                return t[i:j + 1]

PIN_RE = re.compile(r'\(pin (\w+) \w+\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)[\s\S]*?\(number "([^"]*)"')

class Sym:
    def __init__(self, lib_id, text):
        self.lib_id = lib_id
        self.text = text
        # Pin-Nummer -> (x, y, Winkel); bei doppelten Nummern gewinnt der erste Eintrag
        self.pins = {}
        for m in PIN_RE.finditer(text):
            num = m.group(5)
            self.pins.setdefault(num, (float(m.group(2)), float(m.group(3)), int(float(m.group(4)))))
        self.pin_numbers = []
        for m in PIN_RE.finditer(text):
            self.pin_numbers.append(m.group(5))
        # Lage von Referenz und Wert aus der Bibliothek übernehmen
        self.prop_at = {}
        for m in re.finditer(r'\(property "(Reference|Value)" "[^"]*"\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)', text):
            self.prop_at[m.group(1)] = (float(m.group(2)), float(m.group(3)), int(float(m.group(4))))

def from_lib(lib, name):
    lid = lib.replace(".kicad_sym", "") + ":" + name
    t = lib_block(lib, name)
    t = t.replace('(symbol "%s"' % name, '(symbol "%s"' % lid, 1)
    return Sym(lid, t)

def box_symbol(lib_id, ref, value, footprint, left, right, top=(), bottom=(), width=15.24, desc=""):
    """Rechteck-Symbol. Pin-Listen: (Nummer, Name, Typ) oder None für eine Lücke."""
    name = lib_id.split(":")[1]
    n = max(len(left), len(right), 1)
    h = (n + 1) * 2.54
    top_y = round(h / 2 / 1.27) * 1.27
    pins = []
    def side(lst, x, ang):
        for i, p in enumerate(lst):
            if p is None:
                continue
            y = top_y - 2.54 * (i + 1)
            pins.append((p, x, y, ang))
    side(left, -width / 2 - 2.54, 0)
    side(right, width / 2 + 2.54, 180)
    for i, p in enumerate(top):
        if p is not None:
            pins.append((p, -2.54 * (len(top) - 1) / 2 + 2.54 * i, top_y + 2.54, 270))
    by = top_y - 2.54 * (n + 1)
    for i, p in enumerate(bottom):
        if p is not None:
            pins.append((p, -2.54 * (len(bottom) - 1) / 2 + 2.54 * i, by - 2.54, 90))
    rect = '(rectangle (start %.2f %.2f) (end %.2f %.2f) (stroke (width 0.254) (type default)) (fill (type background)))' % (
        -width / 2, top_y, width / 2, by)
    ptxt = []
    for (num, pname, ptype), x, y, ang in pins:
        hide = ""
        ptxt.append('(pin %s line (at %.2f %.2f %d) (length 2.54)%s (name "%s" (effects (font (size 1.27 1.27)))) (number "%s" (effects (font (size 1.27 1.27)))))'
                    % (ptype, x, y, ang, hide, pname, num))
    text = ('(symbol "%s" (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)\n'
            '(property "Reference" "%s" (at 0 %.2f 0) (effects (font (size 1.27 1.27))))\n'
            '(property "Value" "%s" (at 0 %.2f 0) (effects (font (size 1.27 1.27))))\n'
            '(property "Footprint" "%s" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
            '(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
            '(property "Description" "%s" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
            '(symbol "%s_0_1" %s)\n(symbol "%s_1_1" %s))'
            % (lib_id, ref, (top_y + 3.81 if not bottom else top_y + 3.81) if not top else top_y + 6.35, value,
               (top_y + 1.27 if not top else by - 6.35) if bottom else by - 2.54,
               footprint, desc, name, rect, name, "\n".join(ptxt)))
    return Sym(lib_id, text)

R = from_lib("Device.kicad_sym", "R")
C = from_lib("Device.kicad_sym", "C")
LED = from_lib("Device.kicad_sym", "LED")
TP = from_lib("Connector.kicad_sym", "TestPoint")
USBC = from_lib("Connector.kicad_sym", "USB_C_Receptacle_PowerOnly_6P")
DS = from_lib("Device.kicad_sym", "D_Schottky")
DZ = from_lib("Device.kicad_sym", "D_Zener")
BAT = from_lib("Device.kicad_sym", "Battery_Cell")
SW = from_lib("Switch.kicad_sym", "SW_Push")
GND = from_lib("power.kicad_sym", "GND")
P3V3 = from_lib("power.kicad_sym", "+3V3")
FLAG = from_lib("power.kicad_sym", "PWR_FLAG")

B, PI, PO, PA, NC = "bidirectional", "power_in", "power_out", "passive", "no_connect"
CHG = box_symbol("ButtBin:TP4056", "U", "TP4056", "Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.29x3mm",
                 left=[("4", "VCC", PI), ("8", "CE", "input"), ("1", "TEMP", "input"), ("2", "PROG", PA)],
                 right=[("5", "BAT", PO), ("7", "~{CHRG}", "open_collector"), ("6", "~{STDBY}", "open_collector")],
                 bottom=[("3", "GND", PI), ("9", "EP", PI)],
                 width=15.24, desc="Li-Ion-Lader 4,2 V, NTC-Eingang, zwei Status-Ausgaenge")
LDO = box_symbol("ButtBin:TPS7A0333DBV", "U", "TPS7A0333DBVR", "Package_TO_SOT_SMD:SOT-23-5",
                 left=[("1", "IN", PI), ("3", "EN", "input")], right=[("5", "OUT", PO), ("4", "NC", NC)],
                 bottom=[("2", "GND", PI)],
                 width=15.24, desc="LDO 3,3 V, 200 nA Ruhestrom, EN mit internem Pulldown")
TB03 = box_symbol("ButtBin:TB-03F", "U", "TB-03F (TLSR8253)", "RF_Module:ESP-12E",
                  left=[("8", "3V3", PI), ("1", "RST", "input"), ("3", "SWS/PA7", B), None,
                        ("22", "PB1/TX", B), ("21", "PA0/RX", B), None, ("9", "NC", NC), ("14", "NC", NC),
                        None, ("15", "GND", PI)],
                  right=[("16", "PD2", B), ("17", "PD3", B), ("18", "PD4", B), ("12", "PB4/ADC", B),
                         ("13", "PB5", B), ("20", "PC0", B), ("2", "PC4", B), ("4", "PC3", B),
                         ("5", "PD7", B), ("6", "PB7", B), ("7", "PB6", B), ("10", "PA1", B),
                         ("11", "PC2", B), ("19", "PC1", B)],
                  width=20.32, desc="Ai-Thinker TB-03F-AT_Mesh, TLSR8253, Pads wie ESP-12")

SYMS = [R, C, LED, TP, SW, GND, FLAG, TB03]

# ---------------------------------------------------------------- Platzierung
items = []
pwr_n = [0]

def place_power(sym, value, x, y, rot):
    pwr_n[0] += 1
    ref = "#PWR%02d" % pwr_n[0] if sym is not FLAG else "#FLG%02d" % pwr_n[0]
    items.append(('(symbol (lib_id "%s") (at %.2f %.2f %d) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (uuid %s)\n'
                  '(property "Reference" "%s" (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
                  '(property "Value" "%s" (at %.2f %.2f %d) (effects (font (size 1.27 1.27))))\n'
                  '(property "Footprint" "" (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
                  '(property "Datasheet" "" (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) (hide yes)))\n'
                  '(pin "1" (uuid %s))\n'
                  '(instances (project "%s" (path "/%s" (reference "%s") (unit 1)))))')
                 % (sym.lib_id, x, y, rot, uid(), ref, x, y, value, x, y + (3.81 if sym is GND else -3.81), 0,
                    x, y, x, y, uid(), PROJECT, ROOT, ref))

POWER_NETS = {"GND": GND, "+3V3": P3V3}
# Pin-Winkel (Bibliothek) -> Label-Winkel, Power-Symbol-Rotation (GND, +3V3)
DIR = {0: (180, 270, 90), 180: (0, 90, 270), 90: (270, 0, 180), 270: (90, 180, 0)}
FONT = 1.524
PIN = {}  # (Referenz, Pin) -> Anschlusspunkt im Schaltplan

def rot_xy(px, py, rot):
    """Bibliothekskoordinate (y nach oben) um rot Grad gegen den Uhrzeigersinn drehen."""
    c, s = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[rot]
    return px * c - py * s, px * s + py * c

def lab(net, x, y, ang):
    just = "left bottom" if ang in (0, 90) else "right bottom"
    items.append('(label "%s" (at %.2f %.2f %d) (effects (font (size %.3f %.3f)) (justify %s)) (uuid %s))'
                 % (net, x, y, ang, FONT, FONT, just, uid()))

def wire(*pts):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        items.append('(wire (pts (xy %.2f %.2f) (xy %.2f %.2f)) (stroke (width 0) (type default)) (uuid %s))'
                     % (x1, y1, x2, y2, uid()))

def junction(x, y):
    items.append('(junction (at %.2f %.2f) (diameter 0) (color 0 0 0 0) (uuid %s))' % (x, y, uid()))

def pin(ref, num):
    return PIN[(ref, num)]

def place(sym, ref, value, x, y, nets, footprint="", lcsc="", note="", rot=0):
    """nets: Pin-Nummer -> Netzname; 'NC' = nicht verbunden, 'W' = wird per Leitung verbunden."""
    props = [("Reference", ref), ("Value", value), ("Footprint", footprint), ("Datasheet", "")]
    if lcsc:
        props.append(("LCSC", lcsc))
    if note:
        props.append(("Hinweis", note))
    small = sym in (R, C, LED, DS, DZ)
    ptxt = []
    for k, v in props:
        if small and k in ("Reference", "Value"):
            # Kleine Bauteile: Beschriftung waagrecht daneben statt gedreht im Körper
            # Feldwinkel zählt relativ zum gedrehten Symbol: bei 90° mitdrehen, damit der Text waagrecht bleibt
            fa = rot
            if rot in (90, 270) and sym is R:
                px, py, just = x, y - 2.54 if k == "Reference" else y + 3.175, "center"
            elif rot in (90, 270):
                # gedrehte Felder ignorieren justify sichtbar, also mittig mit Abstand
                px, py, just = x + 1.27 + 0.45 * len(v) * FONT, y - 0.635 if k == "Reference" else y + 1.905, "center"
            else:
                px, py, just = x + 2.54, y - 0.635 if k == "Reference" else y + 1.905, "left"
            ptxt.append('(property "%s" "%s" (at %.2f %.2f %d) (effects (font (size %.3f %.3f))%s))'
                        % (k, v, px, py, fa, FONT, FONT, "" if just == "center" else " (justify left)"))
        elif k in sym.prop_at:
            px, py, pa = sym.prop_at[k]
            rx, ry = rot_xy(px, py, rot)
            ptxt.append('(property "%s" "%s" (at %.2f %.2f %d) (effects (font (size %.3f %.3f))))'
                        % (k, v, x + rx, y - ry, 0, FONT, FONT))
        else:
            ptxt.append('(property "%s" "%s" (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) (hide yes)))'
                        % (k, v, x, y))
    pins = "\n".join('(pin "%s" (uuid %s))' % (n, uid()) for n in sym.pin_numbers)
    items.append(('(symbol (lib_id "%s") (at %.2f %.2f %d) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (uuid %s)\n%s\n%s\n'
                  '(instances (project "%s" (path "/%s" (reference "%s") (unit 1)))))')
                 % (sym.lib_id, x, y, rot, uid(), "\n".join(ptxt), pins, PROJECT, ROOT, ref))
    for num, (px, py, ang) in sym.pins.items():
        rx, ry = rot_xy(px, py, rot)
        PIN[(ref, num)] = (round(x + rx, 2), round(y - ry, 2))
    for num, net in nets.items():
        ax, ay = PIN[(ref, num)]
        lab_ang, gnd_rot, vcc_rot = DIR[(sym.pins[num][2] + rot) % 360]
        if net == "W":
            continue
        if net == "NC":
            items.append("(no_connect (at %.2f %.2f) (uuid %s))" % (ax, ay, uid()))
        elif net in POWER_NETS:
            place_power(POWER_NETS[net], net, ax, ay, gnd_rot if net == "GND" else vcc_rot)
        else:
            lab(net, ax, ay, lab_ang)
    # Pins ohne Eintrag sind ein Fehler im Generator
    used = {sym.pins[n][:2] for n in nets}
    missing = {n for n in sym.pins if n not in nets and sym.pins[n][:2] not in used}
    if missing:
        raise SystemExit("%s: Pins ohne Netz: %s" % (ref, sorted(missing)))

def flag(net, x, y):
    """PWR_FLAG mit kurzem Label an einem Netz."""
    place_power(FLAG, "PWR_FLAG", x, y, 0)
    if net in POWER_NETS:
        place_power(POWER_NETS[net], net, x, y, 0 if net == "GND" else 180)
    else:
        items.append('(label "%s" (at %.2f %.2f 270) (effects (font (size 1.27 1.27)) (justify right bottom)) (uuid %s))'
                     % (net, x, y, uid()))

def text(s, x, y, size=1.27):
    items.append('(text "%s" (exclude_from_sim no) (at %.2f %.2f 0) (effects (font (size %.2f %.2f)) (justify left bottom)) (uuid %s))'
                 % (s.replace("\n", "\\n"), x, y, size, size, uid()))

# Klein bauen: Passive in 0402, LEDs 0603, Anschlüsse als Lötpads statt Stecker.
# Innerhalb eines Blocks echte Leitungen, Netznamen nur zwischen den Blöcken.
R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
L0603 = "LED_SMD:LED_0603_1608Metric"
SOD323 = "Diode_SMD:D_SOD-323"
TP_S = "TestPoint:TestPoint_Pad_1.0x1.0mm"
TP_L = "TestPoint:TestPoint_Pad_2.0x2.0mm"
TITLE = 2.0

def res(ref, val, lcsc, x, y, nets, rot=0):
    place(R, ref, val, x, y, nets, R0402, lcsc, rot=rot)

def cap(ref, val, lcsc, x, y, nets):
    place(C, ref, val, x, y, nets, C0402, lcsc)

def pad(ref, value, x, y, net, fp=TP_S, note=""):
    place(TP, ref, value, x, y, {"1": net}, fp, "", note)

# ============ Versorgung: Knopfzelle CR2450, direkt am Modul ============
text("Versorgung: Knopfzelle CR2450 (3 V) im Knauf-Unterteil, zwei Litzen zur Platine", 17.78, 25.4, TITLE)
# Die Zelle sitzt im festen Unterteil (Federkontakte oder fertiger Halter mit Kabel),
# die Platine schwimmt auf der Feder -> nur zwei Loetpads fuer kurze, flexible Litzen.
pad("TP1", "BAT+", 30.48, 50.8, "W", TP_L, "Litze vom Pluskontakt der CR2450")
pad("TP2", "BAT-", 30.48, 63.5, "GND", TP_L, "Litze vom Minuskontakt der CR2450")
vcc = pin("TP1", "1")
# 100 uF keramisch puffert die 10-15-mA-Spitzen beim Senden (Knopfzellen haben hohen Innenwiderstand)
place(C, "C1", "100u", 45.72, vcc[1] + 3.81, {"1": "W", "2": "GND"}, "Capacitor_SMD:C_1206_3216Metric", "", "keramisch, 6,3 V, X5R")
cap("C2", "10u", "C15525", 55.88, vcc[1] + 3.81, {"1": "W", "2": "GND"})
cap("C3", "100n", "C1525", 66.04, vcc[1] + 3.81, {"1": "W", "2": "GND"})
wire(vcc, pin("C1", "1"))
wire(pin("C1", "1"), pin("C2", "1"))
wire(pin("C2", "1"), pin("C3", "1"))
wire(pin("C3", "1"), (76.2, vcc[1]))
lab("VBAT", 76.2, vcc[1], 0)
for p in (pin("C1", "1"), pin("C2", "1"), pin("C3", "1")):
    junction(*p)
text("Gesamtstrom geschaetzt 12-20 uA (Werbung alle 1 s) -> CR2450 ca. 2-4 Jahre.\n"
     "Akkustand misst der TLSR8253 intern an seiner Versorgung, kein Teiler noetig.\n"
     "C1: keramisch 100 uF / 6,3 V (1206), kein Elko: der haette mehr Leckstrom als das ganze Geraet.", 17.78, 78.74, FONT)

# ============ Ring-LEDs ============
text("Ring: 8 LEDs auf 4 Kanaelen (A B C D A B C D rundherum = Lauflicht)", 17.78, 96.52, TITLE)
# 4 Kanaele wie beim Dev-Board, jeder mit eigenem PWM-Kanal (dimmbar). Im Ring reihum angeschlossen:
# schaltet die Firmware A, B, C, D nacheinander, laeuft das Licht rundherum.
CHANNELS = [("LED_A", "rot", "C2286", "2"),     # PC4, PWM2
            ("LED_B", "gelb", "", "19"),        # PC1, PWM1_N (PWM1 frei, PC3 ist I2C)
            ("LED_C", "gruen", "", "12"),       # PB4, PWM4
            ("LED_D", "orange", "", "13")]      # PB5, PWM5
N_LED = 8
for i in range(N_LED):
    net, col, lcsc, _ = CHANNELS[i % 4]
    x = 25.4 + i * 15.24
    place(LED, "D%d" % (i + 1), col, x, 111.76, {"2": net, "1": "W"}, L0603, lcsc, rot=90)
    res("R%d" % (i + 1), "1k", "C11702", x, 119.38, {"1": "W", "2": "GND"})
text("Nur Farben mit ca. 1,8-2,2 V Flussspannung (kein Blau/Weiss): gleich hell bis zur leeren Zelle.\n"
     "Je LED ein eigener Widerstand (ca. 1 mA), 2 LEDs je Kanal; mehr LEDs pro Kanal gehen genauso.\n"
     "Pins: LED_A PC4 (PWM2), LED_B PC1 (PWM1_N), LED_C PB4 (PWM4), LED_D PB5 (PWM5).\n"
     "Strom nur waehrend der Animation: Lauflicht ca. 2 s je Stempeln.", 17.78, 142.24, FONT)

# ============ Modul ============
text("Funkmodul TB-03F (TLSR8253)", 152.4, 25.4, TITLE)
place(TB03, "U4", "TB-03F-AT_Mesh", 220.98, 71.12,
      dict({"8": "VBAT", "1": "RST", "3": "SWS", "22": "TX", "21": "RX", "9": "NC", "14": "NC", "15": "GND",
            "7": "BTN",     # PB6: Stempel-Taster (PB5 wird fuer den PWM5-Kanal von LED_D gebraucht)
            # alle uebrigen GPIOs offen; Ring, Erweiterungen und Reserve ueberschreiben die Zeilen darunter
            **{p: "NC" for p in ("2", "4", "5", "6", "10", "11", "12", "13", "16", "17", "18", "19", "20")}},
           **{p: net for net, _, _, p in CHANNELS},
           # Erweiterungs-Pads (Prototypen): I2C, 2. Taster, Pumpe; Reserve IO1/IO2
           **{"11": "SDA", "4": "SCL", "17": "BTN2", "16": "PUMP", "6": "IO1", "18": "IO2"}),
      "RF_Module:ESP-12E", "C2764070", "Antenne nach oben in die Harzkuppel, kein Metall darueber")
cap("C8", "100n", "C1525", 187.96, 48.26, {"1": "VBAT", "2": "GND"})
text("Modul direkt an der Zelle (1,8-3,6 V). Sendeleistung moeglichst 0 dBm statt 10 dBm:\n"
     "halbiert die Stromspitzen, Reichweite im Raum reicht trotzdem.\n"
     "Batteriestand: intern ueber den VBAT-Kanal des ADC (SDK battery_check.c ohne GPIO_VBAT_DETECT).", 152.4, 109.22, FONT)

# ============ Erweiterungs-Pads ============
text("Erweiterungs-Pads (Unterseite) fuer Prototypen", 152.4, 137.16, TITLE)
# Reihe im Raster 2,54 mm: Stiftleiste oder Litzen fuer Erweiterungs-Prototypen
for i, (ref, name, net, note) in enumerate([("TP17", "VBAT", "VBAT", "Versorgung fuer Erweiterungen"),
                                            ("TP18", "GND", "GND", "Masse fuer Erweiterungen"),
                                            ("TP13", "SDA", "SDA", "PC2, I2C-Daten (Umweltsensor, Display)"),
                                            ("TP14", "SCL", "SCL", "PC3, I2C-Takt"),
                                            ("TP15", "BTN2", "BTN2", "PD3, 2. Taster nach GND, weckt aus dem Schlaf"),
                                            ("TP16", "PUMP", "PUMP", "PD2 (PWM3), Gate eines MOSFETs fuer Pumpe/Spruehkopf")]):
    pad(ref, name, 157.48 + i * 12.7, 149.86, net, "TestPoint:TestPoint_Pad_D1.5mm", note)
text("I2C-Pull-ups (z. B. 4,7k nach VBAT) auf dem Erweiterungs-Board oder intern im Chip.\n"
     "Pumpe, Spruehkopf und Gas-Sensoren brauchen mehr Strom als eine CR2450 liefert:\n"
     "fuer diese Ausbaustufe wieder Akku + Lader (siehe Revision 0.4 in der Git-Historie).", 152.4, 167.64, FONT)

# ============ Stempel und Pads ============
text("Stempel-Taster (Unterseite, Mitte) und Programmier-Pads", 17.78, 152.4, TITLE)
# Platine schwimmt auf der Feder; beim Druecken trifft SW1 auf den Silikonpuffer im Unterteil.
place(SW, "SW1", "KSC621J", 33.02, 165.1, {"1": "W", "2": "GND"},
      "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC6xxJ", "",
      "C&K KSC6 (6,2 x 6,2 mm SMD), IP67 abgedichtet, 300.000 Schaltspiele, 1,7 N; unten mittig")
cap("C9", "100n", "C1525", 43.18, 168.91, {"1": "W", "2": "GND"})
wire(pin("SW1", "2"), (pin("SW1", "2")[0], 175.26))
place_power(GND, "GND", pin("SW1", "2")[0], 175.26, 0)
wire(pin("SW1", "1"), pin("C9", "1")) if pin("SW1", "1")[1] == pin("C9", "1")[1] else None
wire(pin("C9", "1"), (53.34, 165.1))
lab("BTN", 53.34, 165.1, 0)
junction(*pin("C9", "1"))
# Alternative: externer Taster (Mikroschalter, Reed-Kontakt ...) parallel zu SW1 an zwei Litzen
pad("TP11", "BTN", 60.96, 175.26, "BTN", "TestPoint:TestPoint_Pad_1.5x1.5mm", "externer Taster, parallel zu SW1")
pad("TP12", "GND", 68.58, 175.26, "GND", "TestPoint:TestPoint_Pad_1.5x1.5mm", "externer Taster, Masse")
text("PB6 mit internem Pull-up, Taster nach GND, Aufwecken bei Low.\n"
     "Mechanik: Platine mit Kuppel schwimmt auf Wellenfeder, Anschlagring nimmt die Kraft auf.\n"
     "BTN/GND (TP11/TP12): Loetpads fuer einen externen Taster statt oder parallel zu SW1.", 17.78, 190.5, FONT)
# VBAT/SWS/GND/RST: runde Pads in einer Reihe (2,54 mm) an der Abflachung -> Pogo-Pin-Klemme
# TX/RX/IO1/IO2: zweite Reihe (2,54 mm) - Debug-UART und zwei Reserve-Pins fuer Unvorhergesehenes
for i, (name, net) in enumerate([("VBAT", "VBAT"), ("SWS", "SWS"), ("GND", "GND"),
                                 ("RST", "RST"), ("TX", "TX"), ("RX", "RX")]):
    pad("TP%d" % (5 + i), name, 81.28 + i * 10.16, 165.1, net, "TestPoint:TestPoint_Pad_D1.5mm")
pad("TP19", "IO1", 81.28 + 6 * 10.16, 165.1, "IO1", "TestPoint:TestPoint_Pad_D1.5mm", "Reserve: PB7, ADC-faehig")
pad("TP20", "IO2", 81.28 + 7 * 10.16, 165.1, "IO2", "TestPoint:TestPoint_Pad_D1.5mm", "Reserve: PD4, PWM-faehig (PWM2_N)")
text("TX/RX: Debug-UART (PB1/PA0), im fertigen Geraet ebenfalls frei verwendbar.", 81.28, 177.8, FONT)

# ============ Netz-Treiber fuer den ERC ============
text("PWR_FLAG", 149.86, 170.18, FONT)
flag("VBAT", 152.4, 175.26)
flag("GND", 162.56, 175.26)


# ---------------------------------------------------------------- Ausgabe
lib = "\n".join(s.text for s in SYMS)
doc = ('(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0") (uuid %s) (paper "A4")\n'
       '(title_block (title "Butt Bin Traegerplatine") (date "2026-10-31") (rev "0.7 Entwurf") (company "crazy-midi.de")'
       ' (comment 1 "TB-03F direkt an Knopfzelle CR2450, Stempel-Taster, Ring 8 LEDs auf 4 PWM-Kanaelen") (comment 2 "Knauf: Harzkuppel, Leuchtring, schwimmende Platine auf Feder, Zelle im Unterteil"))\n'
       '(lib_symbols\n%s\n)\n%s\n(sheet_instances (path "/" (page "1"))))\n') % (ROOT, lib, "\n".join(items))
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, PROJECT + ".kicad_sch"), "w", encoding="utf-8", newline="\n").write(doc)
# Eigene Symbole zusätzlich als Projekt-Bibliothek, damit KiCad sie kennt
own = [s for s in SYMS if s.lib_id.startswith("ButtBin:")]
open(os.path.join(OUT, "ButtBin.kicad_sym"), "w", encoding="utf-8", newline="\n").write(
    '(kicad_symbol_lib (version 20241209) (generator "buttbin_gen")\n%s\n)\n'
    % "\n".join(s.text.replace('(symbol "ButtBin:', '(symbol "', 1) for s in own))
open(os.path.join(OUT, "sym-lib-table"), "w", encoding="utf-8", newline="\n").write(
    '(sym_lib_table\n  (version 7)\n  (lib (name "ButtBin")(type "KiCad")(uri "${KIPRJMOD}/ButtBin.kicad_sym")(options "")(descr "Butt Bin Projektsymbole"))\n)\n')
pro = os.path.join(OUT, PROJECT + ".kicad_pro")
if not os.path.exists(pro):
    open(pro, "w", encoding="utf-8").write('{"meta": {"filename": "%s.kicad_pro", "version": 1}}\n' % PROJECT)
print("ok", os.path.join(OUT, PROJECT + ".kicad_sch"))
