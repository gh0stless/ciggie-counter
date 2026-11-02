"""Fertigungsdaten fuer JLCPCB: Gerber + Bohrdaten (ZIP), Stueckliste (BOM) und Bestueckungsliste (CPL).
Aufruf (normales Python 3): python gen_fab.py ../buttbin_carrier
Ausgabe in <projekt>/fertigung/. Testpunkte (TP*) sind nur Kupfer und fehlen in BOM und CPL, ebenso Teile in SELF (von Hand geloetet).
"""
import csv
import glob
import os
import shutil
import subprocess
import sys
import zipfile

PROJ = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "../buttbin_carrier")
NAME = "buttbin_carrier"
PCB, SCH = os.path.join(PROJ, NAME + ".kicad_pcb"), os.path.join(PROJ, NAME + ".kicad_sch")
OUT = os.path.join(PROJ, "fertigung")
GERB = os.path.join(OUT, "gerber")
LAYERS = "F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts"
# von Hand geloetet, nicht von JLCPCB bestueckt; die BOM dient dann als Einkaufsliste bei LCSC.
# Leer lassen, wenn JLCPCB alles bestuecken soll.
SELF = ()


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

# BOM: Comment, Designator, Footprint, LCSC
tmp_bom, tmp_pos = os.path.join(OUT, "_bom.csv"), os.path.join(OUT, "_pos.csv")
run("sch", "export", "bom", "--fields", "Reference,Value,Footprint,LCSC", "--labels", "Ref,Value,Footprint,LCSC",
    "--group-by", "Value,Footprint,LCSC", "-o", tmp_bom, SCH)
rows = []
for r in csv.DictReader(open(tmp_bom, encoding="utf-8")):
    if r["Ref"].startswith("TP") or r["Ref"] in SELF:
        continue
    rows.append([r["Value"], r["Ref"], r["Footprint"].split(":")[-1], r["LCSC"]])
with open(os.path.join(OUT, NAME + "_bom.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC"])
    w.writerows(rows)
missing = [r[1] for r in rows if not r[3]]

# CPL: Designator, Mid X, Mid Y, Layer, Rotation (Drehungen gegen die JLCPCB-Vorschau pruefen)
run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "-o", tmp_pos, PCB)
with open(os.path.join(OUT, NAME + "_cpl.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for r in csv.DictReader(open(tmp_pos, encoding="utf-8")):
        if r["Ref"].startswith("TP") or r["Ref"] in SELF:
            continue
        w.writerow([r["Ref"], r["PosX"] + "mm", r["PosY"] + "mm", "Top" if r["Side"] == "top" else "Bottom", r["Rot"]])
os.remove(tmp_bom)
os.remove(tmp_pos)

print("geschrieben:", OUT)
if SELF:
    print("selbst bestuecken:", ", ".join(SELF))
if missing:
    print("ohne LCSC-Nummer:", ", ".join(missing))
