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

# Umriss
Y_FLAT = R_BOARD - 1.0       # Abflachung unten: Pogo-Pin-Klemme fuers Programmieren, Verdrehschutz

def outline_pts(shrink=0.0, step=2.0):
    """Kreis mit Abflachung bei y = Y_FLAT, um shrink nach innen versetzt (Platinenkoordinaten)."""
    r, yf = R_BOARD - shrink, Y_FLAT - shrink
    a0 = math.degrees(math.asin(yf / r))      # Winkel, an dem der Kreis die Gerade trifft
    pts, a = [], a0
    while a < 180 - a0:
        a += step
        aa = min(a, 180 - a0)
        pts.append((r * math.cos(math.radians(aa)), r * math.sin(math.radians(aa))))
    a = 180 - a0
    while a < 360 + a0 - step:
        a += step
        pts.append((r * math.cos(math.radians(a)), r * math.sin(math.radians(a))))
    # Bogen geht oben herum; Gerade unten schliesst die Form
    return [(x, y) for x, y in pts if y <= yf + 1e-6] + [(r * math.cos(math.radians(a0)), yf)]

def inside(x, y, margin):
    return math.hypot(x, y) <= R_BOARD - margin and y <= Y_FLAT - margin

edge = pcbnew.PCB_SHAPE(board)
edge.SetShape(pcbnew.SHAPE_T_POLY)
edge.SetPolyPoints([pcbnew.VECTOR2I(mm(CX + x), mm(CY + y)) for x, y in outline_pts()])
edge.SetLayer(pcbnew.Edge_Cuts)
edge.SetWidth(mm(0.1))
board.Add(edge)

# ------------------------------------------------------------------ Platzierung
put("U4", 0, 0, 0)                 # Antenne zeigt nach oben (-y)
put("SW1", 0, 1.0, 0, bottom=True)  # Stempel-Taster (KSC6) unten mittig, Platine schwimmt auf der Feder
R_LED = R_BOARD - 1.6              # LED-Ring am Rand, unter dem Leuchtring
for k in range(9):
    th = -90 + 40 * k              # Bildschirmwinkel, y nach unten
    side = -9.5 if 0 < th < 90 else 9.5   # an der Abflachung den Widerstand nach oben setzen
    for ref, dth in (("D%d" % (k + 1), 0.0), ("R%d" % (k + 1), side)):
        a = math.radians(th + dth)
        put(ref, R_LED * math.cos(a), R_LED * math.sin(a), -(th + dth + 90))

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

placed = {False: [rect_of(fps[r]) for r in fps if r == "U4" or r[0] in "DR"],
          True: [rect_of(fps["SW1"])]}

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
            if math.hypot(x, y) > rmax or y > Y_FLAT - 3.5:
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

# oben: Pufferkondensatoren dicht am Versorgungs-Pin des Moduls
for ref in ("C8", "C3", "C2", "C1"):
    autoplace(ref, pad_pos("U4", "8"))
# unten: Entprell-C am Taster, Litzen-Pads der Zelle, Programmier-Pads
# Programmier-Reihe VBAT, SWS, GND, RST im Raster 2,54 mm, 2 mm vor der Abflachung (Pogo-Pin-Klemme)
for i, ref in enumerate(("TP5", "TP6", "TP7", "TP8")):
    put(ref, (i - 1.5) * 2.54, Y_FLAT - 2.0, 0, bottom=True)
    placed[True].append(rect_of(fps[ref]))
autoplace("C9", pad_pos("SW1", "1"), bottom=True)
# Erweiterungs-Reihe VBAT, GND, SDA, SCL, BTN2, PUMP: senkrecht am Rand, Raster 2,54 mm
EXT = ("TP17", "TP18", "TP13", "TP14", "TP15", "TP16")
for i, ref in enumerate(EXT):
    put(ref, -12.0, -4.0 + i * 2.54, 0, bottom=True)
    placed[True].append(rect_of(fps[ref], 0.3))
autoplace("TP1", (-7.5, 11.0), bottom=True)
autoplace("TP2", (11.0, 5.0), bottom=True)
# externer Taster: zwei Pads nebeneinander links unten, Litzen gehen zum Rand
autoplace("TP11", (10.0, 7.5), bottom=True)
autoplace("TP12", (10.0, 10.0), bottom=True)
for ref, tgt in [("TP9", ("U4", "22")), ("TP10", ("U4", "21"))]:
    autoplace(ref, pad_pos(*tgt), bottom=True)

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
        for L, lay in enumerate(LAYERS):
            if pad.IsOnLayer(lay):
                mark_rect(L, x0 - INFL, y0 - INFL, x1 + INFL, y1 + INFL, val)
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
VIA_CHECK = 3   # Zellen Radius, die fuer eine Durchkontaktierung frei sein muessen

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
    via_r = VIA_D / 2 + CLEAR + TRACK / 2
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
    return len(vias)

def net_span(plist):
    xs = [ix for core in plist for _, cells in core for ix, _ in cells]
    ys = [iy for core in plist for _, cells in core for _, iy in cells]
    return max(xs) - min(xs) + max(ys) - min(ys)

order = sorted((n for n in terminals if len(terminals[n]) > 1 and n != "GND"), key=lambda n: net_span(terminals[n]))
order.append("GND")
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
        src = tree if net != "GND" else tree
        path = route(nid, src, targets, box)
        if not path:
            failed.append(net)
            print("NICHT VERLEGT:", net, "(%d Pads offen)" % len(rest))
            break
        k = targets[path[-1]]
        nvias += commit(net, path)
        tree |= set(path)
        for L, cells in rest[k]:
            tree |= {(L, ix, iy) for ix, iy in cells}
        rest.pop(k)
    print("verlegt:", net) if net not in failed else None

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
            val.SetPosition(pcbnew.VECTOR2I(pos.x, pos.y - mm(1.3 + 0.35 * len(fp.GetValue()))))
        else:
            # neben das Pad, zur Aussenseite der Platine (Erweiterungs-Reihe: nach innen, sonst abgeschnitten)
            side = -1 if pos.x < mm(100) else 1
            if fp.GetReference() in EXT:
                side = -side
            val.SetPosition(pcbnew.VECTOR2I(pos.x + side * mm(1.2 + 0.35 * len(fp.GetValue())), pos.y))

board.Save(OUT)
print("gespeichert", OUT, "| Durchkontaktierungen:", nvias, "| fehlgeschlagen:", failed)
