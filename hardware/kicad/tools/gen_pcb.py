"""Butt-Bin-Platine (Entwurf): Platzierung + einfacher 2-Lagen-Router + GND-Flaechen.
Aufruf mit KiCads Python: python.exe gen_pcb.py <netzliste.net> <ausgabe.kicad_pcb>
"""
import heapq
import math
import os
import re
import sys
from array import array

import pcbnew

NET_FILE, OUT = sys.argv[1], sys.argv[2]
def _kicad_share():
    """KiCad-Bibliotheken: Umgebungsvariable KICAD_SHARE, sonst die ueblichen Installationsorte (KiCad 10)."""
    cands = [os.environ.get("KICAD_SHARE", ""),
             os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "KiCad", "10.0", "share", "kicad"),
             r"C:/Program Files/KiCad/10.0/share/kicad", "/usr/share/kicad", "/Applications/KiCad/KiCad.app/Contents/SharedSupport"]
    for c in cands:
        if c and os.path.isdir(os.path.join(c, "symbols")):
            return c
    raise SystemExit("KiCad-Bibliotheken nicht gefunden: KICAD_SHARE setzen")

FPDIR = os.path.join(_kicad_share(), "footprints")
R_BOARD = 17.0          # Ø 34 mm
CX, CY = 100.0, 100.0   # Platinenmitte im KiCad-Koordinatensystem
TRACK, CLEAR, VIA_D, VIA_DRILL = 0.2, 0.15, 0.6, 0.3
mm = pcbnew.FromMM

# ------------------------------------------------------------------ Netzliste
txt = open(NET_FILE, encoding="utf-8").read()
comps = {}
for blk in re.split(r"\(comp\s", txt)[1:]:
    ref = re.search(r'\(ref "([^"]+)"', blk).group(1)
    val = re.search(r'\(value "([^"]*)"', blk).group(1)
    fpid = re.search(r'\(footprint "([^"]+)"', blk).group(1)
    comps[ref] = (val, fpid)
nets = {}
i = txt.find("(nets")
for blk in re.split(r"\(net\s+\(code", txt[i:])[1:]:
    name = re.search(r'\(name "([^"]*)"', blk).group(1)
    nets[name] = re.findall(r'\(ref "([^"]*)"\)\s*\(pin "([^"]*)"', blk)

# ------------------------------------------------------------------ Board
board = pcbnew.BOARD()
board.SetCopperLayerCount(2)
ds = board.GetDesignSettings()
try:
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetClearance(mm(CLEAR)); nc.SetTrackWidth(mm(TRACK))
    nc.SetViaDiameter(mm(VIA_D)); nc.SetViaDrill(mm(VIA_DRILL))
except Exception as e:
    print("Netzklasse:", e)

netobj = {}
for name in nets:
    ni = pcbnew.NETINFO_ITEM(board, name)
    board.Add(ni)
    netobj[name] = ni
pinnet = {(r, p): n for n, nodes in nets.items() for r, p in nodes}

fps = {}
for ref, (val, fpid) in sorted(comps.items()):
    lib, name = fpid.split(":")
    fp = pcbnew.FootprintLoad(os.path.join(FPDIR, lib + ".pretty"), name)
    fp.SetReference(ref)
    fp.SetValue(val)
    fp.Reference().SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
    fp.Reference().SetTextThickness(mm(0.15))
    board.Add(fp)
    fps[ref] = fp
    for pad in fp.Pads():
        n = pinnet.get((ref, pad.GetNumber()))
        if n:
            pad.SetNet(netobj[n])

def put(ref, x, y, rot=0.0, bottom=False):
    fp = fps[ref]
    fp.SetPosition(pcbnew.VECTOR2I(mm(CX + x), mm(CY + y)))
    if bottom and not fp.IsFlipped():
        try:
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        except Exception:
            fp.Flip(fp.GetPosition(), True)
    fp.SetOrientationDegrees(rot)

# Umriss: Kreis mit zwei Abflachungen - unten fuer die Programmier-Klemme (4 Pins),
# links fuer die Klemme an der Erweiterungs-Reihe (6 Pins); zugleich Verdrehschutz im Gehaeuse
Y_FLAT = R_BOARD - 1.0       # unten
X_FLAT = R_BOARD - 3.0       # links (Platinenkoordinate -X_FLAT)
ROW_EDGE = 2.0               # Erweiterungs-Reihe: Pad-Mitten 2 mm vor der Abflachung (6er-Klemme, optional)

def outline_pts(shrink=0.0, step=1.0):
    """Kreis, an den Abflachungen auf die Geraden geklemmt, um shrink nach innen versetzt."""
    r, yf, xf = R_BOARD - shrink, Y_FLAT - shrink, X_FLAT - shrink
    pts = []
    for k in range(int(360 / step)):
        a = math.radians(k * step)
        x, y = max(r * math.cos(a), -xf), min(r * math.sin(a), yf)
        if not pts or (abs(pts[-1][0] - x) > 1e-6 or abs(pts[-1][1] - y) > 1e-6):
            pts.append((x, y))
    return pts

def inside(x, y, margin):
    return math.hypot(x, y) <= R_BOARD - margin and y <= Y_FLAT - margin and x >= -X_FLAT + margin

edge = pcbnew.PCB_SHAPE(board)
edge.SetShape(pcbnew.SHAPE_T_POLY)
edge.SetPolyPoints([pcbnew.VECTOR2I(mm(CX + x), mm(CY + y)) for x, y in outline_pts()])
edge.SetLayer(pcbnew.Edge_Cuts)
edge.SetWidth(mm(0.1))
board.Add(edge)

# ------------------------------------------------------------------ Platzierung
put("U4", 0, 0, 0)                 # Antenne zeigt nach oben (-y)
R_LED = R_BOARD - 1.6              # LED-Ring am Rand, unter dem Leuchtring
# Winkel im Uhrzeigersinn (Bildschirm, y nach unten), Luecken an den Abflachungen;
# 6 LEDs spiegelsymmetrisch zur senkrechten Achse (oben 230/310, unten 65/115, seitlich 30/150).
# Die Vorwiderstaende (einer je LED) sitzen unten, siehe weiter unten.
LED_ANG = [30, 65, 115, 150, 230, 310]
N_LED = sum(1 for r in fps if r.startswith("D") and r[1:].isdigit())
assert N_LED == len(LED_ANG), "LED_ANG passt nicht zur Zahl der LEDs im Schaltplan"
LED_IN = {150: 1.0}   # D4 (150 Grad) liegt nah an der linken Abflachung (Pads 0,5 mm Abstand); 1 mm radial sieht man im Ring nicht
for k, th in enumerate(LED_ANG):
    a = math.radians(th)
    r = R_LED - LED_IN.get(th, 0.0)
    put("D%d" % (k + 1), r * math.cos(a), r * math.sin(a), -(th + 90))

def rect_of(fp, inflate=0.0):
    cy = fp.GetCourtyard(pcbnew.F_CrtYd if not fp.IsFlipped() else pcbnew.B_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox()
    return (bb.GetLeft() / 1e6 - CX - inflate, bb.GetTop() / 1e6 - CY - inflate,
            bb.GetRight() / 1e6 - CX + inflate, bb.GetBottom() / 1e6 - CY + inflate)

def overlap(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])

# Sperrflaeche der Antenne (beide Lagen) plus 1,5 mm: dort keine Bauteile
ant = None
for z in fps["U4"].Zones():
    bb = z.GetBoundingBox()
    ant = (bb.GetLeft() / 1e6 - CX - 1.5, bb.GetTop() / 1e6 - CY - 1.5,
           bb.GetRight() / 1e6 - CX + 1.5, bb.GetBottom() / 1e6 - CY + 1.5)

placed = {False: [rect_of(fps[r]) for r in fps if r == "U4" or r[0] == "D"],
          True: []}

def pad_pos(ref, num):
    for p in fps[ref].Pads():
        if p.GetNumber() == num:
            return p.GetPosition().x / 1e6 - CX, p.GetPosition().y / 1e6 - CY
    raise KeyError((ref, num))

def autoplace(ref, target, bottom=False):
    tx, ty = target
    rmax = (R_LED - 1.6) if not bottom else (R_BOARD - 1.4)
    best = None
    for gx in range(-40, 41):
        for gy in range(-40, 41):
            x, y = gx * 0.5, gy * 0.5
            if math.hypot(x, y) > rmax or y > Y_FLAT - 3.5 or x < -X_FLAT + 2.5:
                continue
            d = math.hypot(x - tx, y - ty)
            if best and d >= best[0]:
                continue
            for rot in (0, 90):
                put(ref, x, y, rot, bottom)
                r = rect_of(fps[ref])
                corners = [(r[0], r[1]), (r[2], r[1]), (r[0], r[3]), (r[2], r[3])]
                if any(math.hypot(cx_, cy_) > rmax + 0.6 for cx_, cy_ in corners):
                    continue
                if ant and overlap(r, ant):
                    continue
                if any(overlap(rect_of(fps[ref], 0.15), q) for q in placed[bottom]):
                    continue
                best = (d, x, y, rot)
                break
    if not best:
        raise SystemExit("kein Platz fuer " + ref)
    put(ref, best[1], best[2], best[3], bottom)
    placed[bottom].append(rect_of(fps[ref]))

# unten: Programmier-Pads, Erweiterungs- und Litzen-Pads, Entprell-C am Button-Pad
# Programmier-Reihe VBAT, SWS, GND, RST im Raster 2,54 mm, 2 mm vor der Abflachung (Pogo-Pin-Klemme)
# Langloch-Pads 1,5 x 3,5 mm senkrecht zur Kante: die Klemme trifft, egal ob ihre Stifte 1,5 oder 4,5 mm
# von der Kante sitzen (ihr Mass ist vor der Bestellung nicht bekannt)
PROG_PAD_L = 3.5
for i, ref in enumerate(("TP5", "TP6", "TP7", "TP8")):
    put(ref, (i - 1.5) * 2.54, Y_FLAT - 1.2 - PROG_PAD_L / 2, 0, bottom=True)
    for pad in fps[ref].Pads():
        pad.SetShape(pcbnew.PADSTACK.ALL_LAYERS, pcbnew.PAD_SHAPE_OVAL)
        pad.SetSize(pcbnew.PADSTACK.ALL_LAYERS, pcbnew.VECTOR2I(mm(1.5), mm(PROG_PAD_L)))
    placed[True].append(rect_of(fps[ref]))
# Erweiterungs-Reihe VBAT, GND, SDA, SCL, BTN2, PUMP: senkrecht am Rand, Raster 2,54 mm, eine Teilung
# ueber der Mitte, damit D4 bei 150 Grad (gespiegelt zu D1) Platz hat
EXT_ROW = ("TP17", "TP18", "TP13", "TP14", "TP15", "TP16")
# gegenueber: TX, RX und die Reserve-Pins IO1 (PB7), IO2 (PD4); IO3 (PB5) rechts oben, wo frueher D8 sass
AUX_ROW = ("TP9", "TP10", "TP19", "TP20")
# daneben (aussen) eine zweite Spalte VBAT, GND, VBAT: mit der Reserve-Reihe ein Block im Raster 2,54 mm
PWR_COL = ("TP23", "TP24", "TP25")
EXT = EXT_ROW + AUX_ROW + ("TP1", "TP2", "TP11", "TP12")   # Beschriftung nach innen (aussen waere sie abgeschnitten)
# Erweiterungs-Reihe an der linken Abflachung (mittig), Reserve-Reihe gegenueber
for i, ref in enumerate(EXT_ROW):
    put(ref, -X_FLAT + ROW_EDGE, (i - 3.5) * 2.54, 0, bottom=True)
    placed[True].append(rect_of(fps[ref], 0.3))
for i, ref in enumerate(AUX_ROW):
    put(ref, 12.0, -3.0 + i * 2.54, 0, bottom=True)
    placed[True].append(rect_of(fps[ref], 0.3))
for i, ref in enumerate(PWR_COL):
    put(ref, 12.0 + 2.54, -3.0 + i * 2.54, 0, bottom=True)
    placed[True].append(rect_of(fps[ref], 0.3))
# feste Plaetze (die automatische Suche weicht hier sonst auf unguenstige Stellen aus):
# Zelle oben rechts neben der Antennen-Sperrflaeche, Button-Litzen unten rechts
# (BTN durchkontaktiert, deshalb rechts neben dem Modul)
for ref, x, y in (("TP2", 11.0, -8.9), ("TP1", 11.0, -6.1), ("TP11", 10.5, 8.6), ("TP12", 8.0, 11.5), ("TP21", 14.0, -6.2)):
    put(ref, x, y, 0, bottom=True)
    r = rect_of(fps[ref])
    assert not any(overlap(rect_of(fps[ref], 0.15), q) for q in placed[True]), "Pad ueberlappt: " + ref
    # Randabstand am Kupfer messen (der Courtyard ist um 0,55 mm groesser und steht am Rand ueber)
    for c in (p.GetBoundingBox() for p in fps[ref].Pads()):
        cu = [(c.GetLeft() / 1e6 - CX, c.GetTop() / 1e6 - CY), (c.GetRight() / 1e6 - CX, c.GetBottom() / 1e6 - CY)]
        assert all(inside(cu[i][0], cu[j][1], 0.5) for i in (0, 1) for j in (0, 1)), "Pad am Rand: " + ref
    placed[True].append(r)

# durchkontaktierte Pads belegen auch die Oberseite: dort weder Modul noch LED-Ring treffen
TH = [r for r in fps if r.startswith("TP") and any(p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH for p in fps[r].Pads())]
def hits_courtyard(r, fp):
    """Rechteck r gegen den echten (gedrehten) Courtyard von fp, an einem 7x7-Raster von Punkten geprueft."""
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    return any(cy.Contains(pcbnew.VECTOR2I(mm(CX + r[0] + (r[2] - r[0]) * i / 6), mm(CY + r[1] + (r[3] - r[1]) * j / 6)))
               for i in range(7) for j in range(7))

top_refs = [n for n in fps if n == "U4" or n[0] == "D"]
for ref in TH:
    r = rect_of(fps[ref])
    # ohne Zuschlag: der Courtyard laesst schon 0,55 mm um das Kupfer (TP11 sitzt knapp zwischen Modul und D1);
    # nur gegen Bauteile pruefen - Nachbarn im Raster 2,54 mm beruehren sich mit den Courtyards
    hit = [n for n in top_refs if hits_courtyard(r, fps[n])]
    assert not hit, "Pad trifft Oberseite: %s an %s" % (ref, ", ".join(hit))
    placed[False].append(r)
# Befestigung im gedruckten Unterteil: die Abflachungen liegen an der Taschenwand (Lage, Verdrehschutz),
# dazu eine Schraube M2 mitten ueber der Antenne (Nylon - Metall so nah verstimmt die Antenne) und ein
# Loch fuer eine Nase unten rechts, plus ein Tupfen Heisskleber. Ohne Kupfer, nur Bohrung.
# Mehr Loecher gehen nicht: oben ueber der Antenne zerschneiden sie die GND-Verbindung auf der Unterseite,
# unten links und rechts am Rand sperren sie Leiterbahnen (getestet 02.11.2026).
HOLES = [("H1", 10.5, 11.0, 1.5),
         ("H2", 0.0, -15.0, 2.2)]
for ref, x, y, d in HOLES:
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(ref)
    fp.SetValue("M2" if d > 2 else "Nase")
    fp.SetAttributes(pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM)
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    pad = pcbnew.PAD(fp)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
    pad.SetShape(pcbnew.PADSTACK.ALL_LAYERS, pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetSize(pcbnew.PADSTACK.ALL_LAYERS, pcbnew.VECTOR2I(mm(d), mm(d)))
    pad.SetDrillSize(pcbnew.VECTOR2I(mm(d), mm(d)))
    pad.SetLayerSet(pcbnew.PAD.UnplatedHoleMask())
    fp.Add(pad)
    board.Add(fp)
    fps[ref] = fp
    put(ref, x, y)
    r = rect_of(fp, 0.4)
    # gegen das Kupfer der schon gesetzten Pads pruefen (deren Courtyards sind fuer die engen Ecken zu grob)
    pads = [p.GetBoundingBox() for n, f in fps.items() if n[0] not in "RCH" for p in f.Pads()]
    assert not any(overlap(r, (b.GetLeft() / 1e6 - CX, b.GetTop() / 1e6 - CY, b.GetRight() / 1e6 - CX,
                               b.GetBottom() / 1e6 - CY)) for b in pads), "Loch trifft Pad: " + ref
    assert not [n for n in top_refs if hits_courtyard(r, fps[n])], "Loch trifft Oberseite: " + ref
    placed[True].append(r)
    placed[False].append(r)
# Pufferkondensatoren unten unter dem Modul, dicht am Versorgungs-Pin
# (oben links neben dem Modul laeuft jetzt die durchkontaktierte Erweiterungs-Reihe)
for ref in ("C8", "C3", "C2", "C1"):
    autoplace(ref, pad_pos("U4", "8"), bottom=True)
# Vorwiderstaende unten, jeder moeglichst direkt unter der Kathode seiner LED
for k in range(N_LED):
    autoplace("R%d" % (k + 1), pad_pos("D%d" % (k + 1), "1"), bottom=True)
# Entprell-C unten am Button-Pad (BTN)
autoplace("C9", pad_pos("TP11", "1"), bottom=True)

# ------------------------------------------------------------------ Router
G = 0.1
N = int(2 * R_BOARD / G) + 1
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)
FREE, BLOCK = -1, -2
netid = {n: k for k, n in enumerate(nets)}
idnet = {k: n for n, k in netid.items()}
owner = [array("h", [FREE]) * (N * N) for _ in LAYERS]

def cell(x, y):
    return int(round((x + R_BOARD) / G)), int(round((y + R_BOARD) / G))

def xy(ix, iy):
    return ix * G - R_BOARD, iy * G - R_BOARD

for L in range(2):
    o = owner[L]
    for iy in range(N):
        for ix in range(N):
            x, y = xy(ix, iy)
            if not inside(x, y, 0.65):   # 0,5 mm Randabstand + halbe Bahn
                o[iy * N + ix] = BLOCK

def mark_rect(L, x0, y0, x1, y1, val):
    o = owner[L]
    a0, b0 = cell(x0, y0)
    a1, b1 = cell(x1, y1)
    for iy in range(max(b0, 0), min(b1, N - 1) + 1):
        for ix in range(max(a0, 0), min(a1, N - 1) + 1):
            k = iy * N + ix
            cur = o[k]
            if cur == FREE:
                o[k] = val
            elif cur != val:
                o[k] = BLOCK

def mark_disc(L, x, y, r, val):
    o = owner[L]
    c0, c1 = cell(x - r, y - r), cell(x + r, y + r)
    for iy in range(max(c0[1], 0), min(c1[1], N - 1) + 1):
        for ix in range(max(c0[0], 0), min(c1[0], N - 1) + 1):
            px, py = xy(ix, iy)
            if (px - x) ** 2 + (py - y) ** 2 <= r * r:
                k = iy * N + ix
                cur = o[k]
                if cur == FREE:
                    o[k] = val
                elif cur != val:
                    o[k] = BLOCK

# Sperrflaeche der Antenne (aus dem Modul-Footprint) fuer Leiterbahnen auf beiden Lagen
for z in fps["U4"].Zones():
    bb = z.GetBoundingBox()
    for L in range(2):
        mark_rect(L, bb.GetLeft() / 1e6 - CX - 0.25, bb.GetTop() / 1e6 - CY - 0.25,
                  bb.GetRight() / 1e6 - CX + 0.25, bb.GetBottom() / 1e6 - CY + 0.25, BLOCK)

INFL = CLEAR + TRACK / 2
terminals = {}   # netz -> liste von (L, set(zellen))
for ref, fp in fps.items():
    for pad in fp.Pads():
        net = pad.GetNetname()
        bb = pad.GetBoundingBox()
        x0, y0 = bb.GetLeft() / 1e6 - CX, bb.GetTop() / 1e6 - CY
        x1, y1 = bb.GetRight() / 1e6 - CX, bb.GetBottom() / 1e6 - CY
        val = netid[net] if net in netid and len(nets[net]) > 1 else BLOCK
        inf = INFL + (0.1 if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH else 0)   # Loecher: 0,25 mm Freiraum
        for L, lay in enumerate(LAYERS):
            if pad.IsOnLayer(lay):
                mark_rect(L, x0 - inf, y0 - inf, x1 + inf, y1 + inf, val)
        if val >= 0:
            # Kernzellen: Zellmitte liegt wirklich im Pad (gedrehte Pads!), mit 0,1 mm Abstand zum Rand
            inner = set()
            a0, b0 = cell(x0, y0)
            a1, b1 = cell(x1, y1)
            for iy in range(b0, b1 + 1):
                for ix in range(a0, a1 + 1):
                    px, py = xy(ix, iy)
                    ok = all(pad.HitTest(pcbnew.VECTOR2I(mm(CX + px + dx), mm(CY + py + dy)))
                             for dx, dy in ((0, 0), (0.1, 0), (-0.1, 0), (0, 0.1), (0, -0.1)))
                    if ok:
                        inner.add((ix, iy))
            core = [(L, inner) for L, lay in enumerate(LAYERS) if pad.IsOnLayer(lay)]
            terminals.setdefault(net, []).append(core)

# Pad-Kerne gehoeren sicher ihrem Netz (falls Ueberlappung oben BLOCK gesetzt hat)
for net, plist in terminals.items():
    for core in plist:
        for L, cells in core:
            for ix, iy in cells:
                owner[L][iy * N + ix] = netid[net]

DIRS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
        (1, 1, 1.42), (1, -1, 1.42), (-1, 1, 1.42), (-1, -1, 1.42)]
VIA_COST = 25.0
VIA_CHECK = 4   # Zellen Radius, die fuer eine Durchkontaktierung frei sein muessen (3 war knapp: 0,18 statt 0,2 mm)

def passable(L, ix, iy, nid):
    if not (0 <= ix < N and 0 <= iy < N):
        return False
    v = owner[L][iy * N + ix]
    return v == FREE or v == nid

def via_ok(ix, iy, nid):
    for L in range(2):
        for dy in range(-VIA_CHECK, VIA_CHECK + 1):
            for dx in range(-VIA_CHECK, VIA_CHECK + 1):
                if dx * dx + dy * dy <= VIA_CHECK * VIA_CHECK and not passable(L, ix + dx, iy + dy, nid):
                    return False
    return True

def route(nid, sources, targets, box):
    """Dijkstra von beliebiger Quellzelle zu beliebiger Zielzelle. Zellen: (L, ix, iy)."""
    x0, y0, x1, y1 = box
    dist, prev, pq = {}, {}, []
    for s in sources:
        dist[s] = 0.0
        heapq.heappush(pq, (0.0, s))
    while pq:
        d, cur = heapq.heappop(pq)
        if d > dist.get(cur, 1e18):
            continue
        if cur in targets:
            path = [cur]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            return path[::-1]
        L, ix, iy = cur
        for dx, dy, c in DIRS:
            nx, ny = ix + dx, iy + dy
            if not (x0 <= nx <= x1 and y0 <= ny <= y1) or not passable(L, nx, ny, nid):
                continue
            if dx and dy and not (passable(L, ix + dx, iy, nid) and passable(L, ix, iy + dy, nid)):
                continue
            nxt = (L, nx, ny)
            nd = d + c
            if nd < dist.get(nxt, 1e18):
                dist[nxt] = nd
                prev[nxt] = cur
                heapq.heappush(pq, (nd, nxt))
        if via_ok(ix, iy, nid):
            nxt = (1 - L, ix, iy)
            nd = d + VIA_COST
            if nd < dist.get(nxt, 1e18):
                dist[nxt] = nd
                prev[nxt] = cur
                heapq.heappush(pq, (nd, nxt))
    return None

def commit(net, path):
    nid = netid[net]
    tr_r = TRACK / 2 + CLEAR + TRACK / 2
    via_r = VIA_D / 2 + CLEAR + TRACK / 2 + 0.05   # +0,05: Rasterrundung, sonst nur 0,18 mm zur naechsten Bahn
    segs, vias = [], []
    start = path[0]
    for a, b in zip(path, path[1:]):
        if a[0] != b[0]:
            vias.append((a[1], a[2]))
    # Zellen belegen
    for L, ix, iy in path:
        x, y = xy(ix, iy)
        mark_disc(L, x, y, tr_r, nid)
    for ix, iy in vias:
        x, y = xy(ix, iy)
        for L in range(2):
            mark_disc(L, x, y, via_r, nid)
    # Strecken zusammenfassen
    run = [path[0]]
    def flush(run):
        if len(run) > 1:
            segs.append((run[0], run[-1]))
    for a, b in zip(path, path[1:]):
        if a[0] != b[0]:
            flush(run)
            run = [b]
            continue
        if len(run) >= 2:
            d0 = (run[1][1] - run[0][1], run[1][2] - run[0][2])
            d1 = (b[1] - a[1], b[2] - a[2])
            if d0 != d1:
                flush(run)
                run = [a]
        run.append(b)
    flush(run)
    for (L, ax, ay), (_, bx, by) in segs:
        t = pcbnew.PCB_TRACK(board)
        (sx, sy), (ex, ey) = xy(ax, ay), xy(bx, by)
        t.SetStart(pcbnew.VECTOR2I(mm(CX + sx), mm(CY + sy)))
        t.SetEnd(pcbnew.VECTOR2I(mm(CX + ex), mm(CY + ey)))
        t.SetWidth(mm(TRACK))
        t.SetLayer(LAYERS[L])
        t.SetNet(netobj[net])
        board.Add(t)
        created.append(t)
    for ix, iy in vias:
        v = pcbnew.PCB_VIA(board)
        x, y = xy(ix, iy)
        v.SetPosition(pcbnew.VECTOR2I(mm(CX + x), mm(CY + y)))
        v.SetDrill(mm(VIA_DRILL))
        try:
            v.SetWidth(mm(VIA_D))
        except TypeError:
            v.SetWidth(pcbnew.F_Cu, mm(VIA_D))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(netobj[net])
        board.Add(v)
        created.append(v)
    return len(vias)

def net_span(plist):
    xs = [ix for core in plist for _, cells in core for ix, _ in cells]
    ys = [iy for core in plist for _, cells in core for _, iy in cells]
    return max(xs) - min(xs) + max(ys) - min(ys)

created = []
BASE = [array("h", o) for o in owner]   # Belegung nur mit Pads, fuer neue Versuche

def route_all(order):
    """Alle Netze in dieser Reihenfolge verlegen; liefert (fehlgeschlagene Netze, Anzahl Durchkontaktierungen)."""
    for obj in created:
        board.Remove(obj)
    created.clear()
    for L in range(2):
        owner[L] = array("h", BASE[L])
    failed, nvias = [], 0
    for net in order:
        nid = netid[net]
        plist = terminals[net]
        if net == "GND":
            # GND als Baum ab dem groessten GND-Pad; die Flaechen kommen danach dazu
            big = max(plist, key=lambda core: sum(len(c) for _, c in core))
            tree = {(L, ix, iy) for L, cells in big for ix, iy in cells}
            rest = [core for core in plist if core is not big]
        else:
            tree = {(L, ix, iy) for L, cells in plist[0] for ix, iy in cells}
            rest = plist[1:]
        while rest:
            targets = {}
            for k, core in enumerate(rest):
                for L, cells in core:
                    for ix, iy in cells:
                        targets[(L, ix, iy)] = k
            allc = list(tree) + list(targets)
            pad = 60
            box = (min(c[1] for c in allc) - pad, min(c[2] for c in allc) - pad,
                   max(c[1] for c in allc) + pad, max(c[2] for c in allc) + pad)
            path = route(nid, tree, targets, box)
            if not path:
                failed.append(net)
                break
            k = targets[path[-1]]
            nvias += commit(net, path)
            tree |= set(path)
            for L, cells in rest[k]:
                tree |= {(L, ix, iy) for ix, iy in cells}
            rest.pop(k)
    return failed, nvias

order = sorted((n for n in terminals if len(terminals[n]) > 1 and n != "GND"), key=lambda n: net_span(terminals[n]))
order.append("GND")
# Rip-up and retry: gescheiterte Netze beim naechsten Versuch zuerst verlegen
best = None
for attempt in range(8):
    failed, nvias = route_all(order)
    print("Versuch %d: %s" % (attempt + 1, "alles verlegt" if not failed else "offen: " + ", ".join(failed)))
    if best is None or len(failed) < len(best[1]):
        best = (list(order), failed)
    if not failed:
        break
    order = failed + [n for n in order if n not in failed]
if failed and best[1] != failed:
    failed, nvias = route_all(best[0])   # bestes Ergebnis wiederherstellen

# ------------------------------------------------------------------ GND-Flaechen
for lay in LAYERS:
    z = pcbnew.ZONE(board)
    z.SetLayer(lay)
    z.SetNet(netobj["GND"])
    z.SetLocalClearance(mm(0.25))
    z.SetMinThickness(mm(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    poly = z.Outline()
    poly.NewOutline()
    for x, y in outline_pts(0.3):
        poly.Append(mm(CX + x), mm(CY + y))
    board.Add(z)
filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())

# Testpunkte: Funktion (BAT+, SWS, TX ...) statt TPx in den Bestueckungsdruck
TOP_NAME = {"VBAT": "V+", "BTN2": "B2", "PUMP": "PMP", "BAT+": "B+", "BAT-": "B-"}
for fp in fps.values():
    if fp.GetReference().startswith("TP"):
        fp.Reference().SetVisible(False)
        val = fp.Value()
        val.SetLayer(pcbnew.B_SilkS if fp.IsFlipped() else pcbnew.F_SilkS)
        val.SetMirrored(fp.IsFlipped())
        val.SetVisible(True)
        val.SetTextSize(pcbnew.VECTOR2I(mm(0.9), mm(0.9)))
        val.SetTextThickness(mm(0.15))
        pos = fp.GetPosition()
        if fp.GetReference() in ("TP5", "TP6", "TP7", "TP8"):
            # Programmier-Reihe: Text senkrecht ueber dem Pad, Richtung Platinenmitte
            val.SetTextAngleDegrees(90)
            val.SetPosition(pcbnew.VECTOR2I(pos.x, pos.y - mm(PROG_PAD_L / 2 + 0.5 + 0.35 * len(fp.GetValue()))))
        elif fp.GetReference() in PWR_COL:
            # aussen am Rand ist nur Platz fuer ein Zeichen
            val.SetText("+" if fp.GetValue() == "VBAT" else "-")
            val.SetPosition(pcbnew.VECTOR2I(pos.x + mm(1.55), pos.y))
        elif fp.GetReference() == "TP21":
            val.SetPosition(pcbnew.VECTOR2I(pos.x, pos.y - mm(1.4)))
        else:
            # neben das Pad, zur Aussenseite der Platine (Erweiterungs-Reihe: nach innen, sonst abgeschnitten)
            side = -1 if pos.x < mm(100) else 1
            if fp.GetReference() in EXT:
                side = -side
            val.SetPosition(pcbnew.VECTOR2I(pos.x + side * mm(1.2 + 0.35 * len(fp.GetValue())), pos.y))
        if fp.GetReference() in TH:
            # durchkontaktiert: Beschriftung auch oben - dort ist zwischen Pad und Modul nur gut 2 mm Platz,
            # also kurze Namen, kleinere Schrift und je Pad die freie Richtung (Modul, LED-Ring)
            ref = fp.GetReference()
            name = val.GetText() if ref in PWR_COL else TOP_NAME.get(fp.GetValue(), fp.GetValue())
            dx, dy = ((1, 0) if ref in EXT_ROW else (-1, 0) if ref in AUX_ROW else (0, 1) if ref == "TP11"
                      else (0, -1) if ref == "TP21" else (1, 0))
            top = pcbnew.PCB_TEXT(board)
            top.SetText(name)
            top.SetLayer(pcbnew.F_SilkS)
            top.SetMirrored(False)
            top.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))     # JLCPCB: mindestens 0,8 mm
            top.SetTextThickness(mm(0.15))
            off = 1.55 if ref in PWR_COL else 1.0 + 0.3 * len(name) if dx else 1.3 if dy > 0 else 1.4
            top.SetPosition(pcbnew.VECTOR2I(pos.x + dx * mm(off), pos.y + dy * mm(off)))
            board.Add(top)

board.Save(OUT)
print("gespeichert", OUT, "| Durchkontaktierungen:", nvias, "| fehlgeschlagen:", failed)
