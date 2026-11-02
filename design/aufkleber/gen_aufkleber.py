"""Kleiner Aufkleber fuer den Knauf: "Butt Bin(TM)" / "by crazy-midi.de" auf transparenter Folie.

Schreibt je Druckfarbe ein SVG mit der Schrift als Pfaden (druckt ohne installierte Schrift) und ein
PNG mit transparentem Hintergrund zur Ansicht. Aufruf: python gen_aufkleber.py
Schriften: Arial Black (Name) und Bahnschrift (Zeile darunter), beide von Windows.
"""
import os

import matplotlib
matplotlib.use("Agg")
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path
from matplotlib.textpath import TextPath

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
WIDTH = 30.0          # Breite des Aufklebers in mm
MARGIN = 1.0          # Rand um den Text in mm (Schnittkante)
COLORS = {"weiss": "#ffffff", "schwarz": "#000000"}   # weiss: fuer die schwarze Haube (Weissdruck)

name = TextPath((0, 0), "Butt Bin", size=10, prop=FontProperties(fname=os.path.join(FONTS, "ariblk.ttf")))
# Variante zur Ansicht: kleines vorangestelltes Zeichen (z. B. AUFKLEBER_PREFIX=i -> "iButt Bin"), eigene Dateien
PREFIX = os.environ.get("AUFKLEBER_PREFIX", "")
SUFFIX = "_" + PREFIX if PREFIX else ""
if PREFIX:
    pre = TextPath((0, 0), PREFIX, size=8.0, prop=FontProperties(fname=os.path.join(FONTS, "arialbd.ttf")))
    pw = pre.vertices[:, 0].max() + 0.5
    name = Path.make_compound_path(pre, Path(name.vertices + (pw, 0), name.codes))
tm = TextPath((0, 0), "TM", size=3.6, prop=FontProperties(fname=os.path.join(FONTS, "arialbd.ttf")))
by = TextPath((0, 0), "by crazy-midi.de", size=4.6, prop=FontProperties(fname=os.path.join(FONTS, "bahnschrift.ttf")))


def extents(p):
    v = p.vertices
    return v[:, 0].min(), v[:, 1].min(), v[:, 0].max(), v[:, 1].max()


def moved(p, dx, dy):
    return Path(p.vertices + (dx, dy), p.codes)


# Anordnung in Schrift-Einheiten: Name oben, TM hochgestellt dahinter, Zeile darunter rechtsbuendig
nx0, ny0, nx1, ny1 = extents(name)
tm = moved(tm, nx1 + 0.4 - extents(tm)[0], ny1 - extents(tm)[3])
bx0, by0, bx1, by1 = extents(by)
line_w = extents(tm)[2] - nx0
by = moved(by, nx0 + line_w - bx1, ny0 - 2.2 - by1)
parts = [name, tm, by]
x0 = min(extents(p)[0] for p in parts); y0 = min(extents(p)[1] for p in parts)
x1 = max(extents(p)[2] for p in parts); y1 = max(extents(p)[3] for p in parts)
scale = (WIDTH - 2 * MARGIN) / (x1 - x0)
height = (y1 - y0) * scale + 2 * MARGIN


def svg_path(p):
    """Pfad in mm, y nach unten (SVG)."""
    out, i = [], 0
    verts, codes = p.vertices, p.codes
    while i < len(verts):
        c = codes[i]
        pt = lambda k: "%.3f %.3f" % (MARGIN + (verts[k][0] - x0) * scale, MARGIN + (y1 - verts[k][1]) * scale)
        if c == Path.MOVETO:
            out.append("M" + pt(i)); i += 1
        elif c == Path.LINETO:
            out.append("L" + pt(i)); i += 1
        elif c == Path.CURVE3:
            out.append("Q" + pt(i) + " " + pt(i + 1)); i += 2
        elif c == Path.CURVE4:
            out.append("C" + pt(i) + " " + pt(i + 1) + " " + pt(i + 2)); i += 3
        elif c == Path.CLOSEPOLY:
            out.append("Z"); i += 1
        else:
            i += 1
    return " ".join(out)


d = " ".join(svg_path(p) for p in parts)
for key, color in COLORS.items():
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" viewBox="0 0 %.2f %.2f">\n'
           '  <!-- Butt Bin Aufkleber, %s auf transparenter Folie; Schnittkante = Rechteck mit runden Ecken -->\n'
           '  <rect x="0.15" y="0.15" width="%.2f" height="%.2f" rx="1.2" fill="none" stroke="#ff00ff" '
           'stroke-width="0.1" id="Schnittkontur"/>\n'
           '  <path fill="%s" fill-rule="nonzero" d="%s"/>\n</svg>\n'
           % (WIDTH, height, WIDTH, height, key, WIDTH - 0.3, height - 0.3, color, d))
    with open(os.path.join(HERE, "buttbin_aufkleber%s_%s.svg" % (SUFFIX, key)), "w", encoding="utf-8") as f:
        f.write(svg)

# Vorschau als PNG (transparent), 600 dpi
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.transforms import Affine2D
for key, color in COLORS.items():
    fig = plt.figure(figsize=(WIDTH / 25.4, height / 25.4), dpi=600)
    ax = fig.add_axes((0, 0, 1, 1)); ax.set_axis_off()
    ax.set_xlim(0, WIDTH); ax.set_ylim(0, height)
    tr = Affine2D().translate(-x0, -y0).scale(scale).translate(MARGIN, MARGIN)
    for p in parts:
        ax.add_patch(PathPatch(tr.transform_path(p), facecolor=color, edgecolor="none"))
    fig.savefig(os.path.join(HERE, "buttbin_aufkleber%s_%s.png" % (SUFFIX, key)), transparent=True)
    plt.close(fig)
print("Aufkleber %.1f x %.1f mm" % (WIDTH, height))
