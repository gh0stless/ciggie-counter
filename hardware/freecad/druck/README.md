# Butt Bin Knauf – Druckteile

Die Dateien werden von `../knauf.py` erzeugt (`freecadcmd knauf.py`). Bitte nicht von Hand ändern.
Es gibt jede Datei als STL für den Druckdienst und als STEP zum Weiterbearbeiten.

| Teil | Datei | Material | Volumen |
|---|---|---|---|
| Unterteil | `Knauf_Unterteil` | MJF/SLS PA12, eingefärbt (rot oder schwarz) | ca. 48 cm³ |
| Leuchtring | `Leuchtband` | Klares Resin (SLA), innen nicht geschliffen | ca. 6 cm³ |
| Haube | `Knauf_Haube` | MJF/SLS PA12, eingefärbt | ca. 6 cm³ |

Der Knauf hat Ø 44 mm und ist mit Button etwa 80 mm hoch. Auf dem Value-Drehascher kommt alles
zusammen auf etwa 160 mm.

## Aufbau

- **Unterteil:**
  - Unten der Schacht über den Original-Griff, ausgekleidet mit einem Silikonschlauch 21 × 16 mm,
    30 mm lang.
  - Darüber das Fach für den CR2450-Halter mit Drehdeckel.
  - Darüber die Tasche für die Platine. Sie hat den Umriss der Platine mit beiden Abflachungen und
    gibt damit Lage und Verdrehschutz vor.
  - Oben das Innengewinde M40 × 1,5.
- **Platine:**
  - Sie liegt auf einem 0,8 mm breiten Rand.
  - Eine Nase (Ø 1,3 mm) unten rechts greift ins Loch H1.
  - Eine **Nylon-Schraube M2 × 5** geht durch das Loch H2 über der Antenne in den Dom (Kernloch Ø 1,6 mm).
    Keine Metallschraube nehmen, sie verstimmt die Antenne.
- **Leuchtring:**
  - Er ist das Verbindungsstück, mit einem Außengewinde unten (ins Unterteil) und einem oben (in die
    Haube).
  - Dazwischen liegt das sichtbare Band, 5 mm hoch.
  - Unten sitzen sechs kleine Nasen direkt über den LEDs und leiten das Licht in den Ring.
- **Haube:**
  - Unten das Innengewinde.
  - Oben die Platte mit dem 30-mm-Loch für den Retro+-Button S30. Der Button schnappt von oben ein.

## Zusammenbau und Zellenwechsel

1. Den CR2450-Halter in sein Fach legen. Die Litzen hoch zu den Pads B+ und B− führen und dort anlöten.
2. Die Platine in die Tasche legen, sodass die Nase ins Loch greift, und mit der Nylon-Schraube festschrauben.
3. Den Ring ins Unterteil schrauben.
4. Die Button-Litzen an BTN und GND löten, den Button in die Haube drücken und die Haube auf den Ring
   schrauben.

Zum Zellenwechsel schraubt man Haube und Ring zusammen vom Unterteil ab, löst die Schraube und hebt
die Platine an. Die Litzen brauchen dafür genug Spiel.

Ein Gewinde braucht gut 3 Umdrehungen. Dabei verdrillen sich die Button-Litzen. Deshalb weiche
Silikonlitze nehmen und ausreichend lang lassen.

## Noch nachmessen, wenn die Teile da sind

Die folgenden Maße stehen oben in `knauf.py`. Danach `knauf.py` neu laufen lassen.

- **Retro+-Button:** Gehäuse, Höhe und Klemmbereich der Schnappnasen (`BTN_*`, `PANEL_T`).
- **CR2450-Halter:** Höhe und Fahnen (`HOLDER_*`, `TAB_*`).
- **Silikonschlauch:** Wandstärke (`SLEEVE_T`).
- **Gewindespiel `TH_CLR`:** 0,2 mm passt für MJF und Resin. Bei einem anderen Verfahren beim
  Druckdienst nachfragen.
