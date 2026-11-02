"""Fertigungsdaten fuer JLCPCB: Gerber + Bohrdaten als ZIP, auf Wunsch auch BOM und CPL fuer die Bestueckung.
Aufruf (normales Python 3):  python gen_fab.py ../buttbin_carrier [--bestueckung]
Ausgabe in <projekt>/fertigung/. Ohne --bestueckung nur das Gerber-ZIP (Platine selbst loeten).
Testpunkte (TP*) sind nur Kupfer und fehlen in BOM und CPL.
"""
import csv
import glob
import os
import shutil
import subprocess
import sys
import zipfile

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
ASSEMBLY = "--bestueckung" in sys.argv
PROJ = os.path.abspath(ARGS[0] if ARGS else "../buttbin_carrier")
NAME = "buttbin_carrier"
PCB, SCH = os.path.join(PROJ, NAME + ".kicad_pcb"), os.path.join(PROJ, NAME + ".kicad_sch")
OUT = os.path.join(PROJ, "fertigung")
GERB = os.path.join(OUT, "gerber")
LAYERS = "F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts"


def kicad_cli():
    cands = [os.environ.get("KICAD_CLI", ""), shutil.which("kicad-cli") or "",
             os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "KiCad", "10.0", "bin", "kicad-cli.exe"),
             r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    raise SystemExit("kicad-cli nicht gefunden: KICAD_CLI setzen")


def run(*args):
    subprocess.run([CLI, *args], check=True, stdout=subprocess.DEVNULL)


CLI = kicad_cli()
shutil.rmtree(GERB, ignore_errors=True)
os.makedirs(GERB)

# Gerber + Bohrdaten -> ZIP (so wie JLCPCB es hochgeladen haben will)
run("pcb", "export", "gerbers", "--layers", LAYERS, "--no-protel-ext", "-o", GERB + os.sep, PCB)
run("pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th", "-o", GERB + os.sep, PCB)
zpath = os.path.join(OUT, NAME + "_gerber.zip")
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(glob.glob(os.path.join(GERB, "*"))):
        z.write(f, os.path.basename(f))
bom_path, cpl_path = os.path.join(OUT, NAME + "_bom.csv"), os.path.join(OUT, NAME + "_cpl.csv")

if not ASSEMBLY:
    for p in (bom_path, cpl_path):                    # alte Bestueckungsdaten nicht liegen lassen
        if os.path.exists(p):
            os.remove(p)
    print("geschrieben:", zpath)
    sys.exit(0)

# BOM: Comment, Designator, Footprint, LCSC
tmp_bom, tmp_pos = os.path.join(OUT, "_bom.csv"), os.path.join(OUT, "_pos.csv")
run("sch", "export", "bom", "--fields", "Reference,Value,Footprint,LCSC", "--labels", "Ref,Value,Footprint,LCSC",
    "--group-by", "Value,Footprint,LCSC", "-o", tmp_bom, SCH)
rows = []
for r in csv.DictReader(open(tmp_bom, encoding="utf-8")):
    if r["Ref"].startswith("TP"):
        continue
    rows.append([r["Value"], r["Ref"], r["Footprint"].split(":")[-1], r["LCSC"]])
with open(bom_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC"])
    w.writerows(rows)
missing = [r[1] for r in rows if not r[3]]

# CPL: Designator, Mid X, Mid Y, Layer, Rotation (Drehungen gegen die JLCPCB-Vorschau pruefen)
run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "-o", tmp_pos, PCB)
with open(cpl_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for r in csv.DictReader(open(tmp_pos, encoding="utf-8")):
        if r["Ref"].startswith("TP"):
            continue
        w.writerow([r["Ref"], r["PosX"] + "mm", r["PosY"] + "mm", "Top" if r["Side"] == "top" else "Bottom", r["Rot"]])
os.remove(tmp_bom)
os.remove(tmp_pos)

print("geschrieben:", OUT)
if missing:
    print("ohne LCSC-Nummer:", ", ".join(missing))
