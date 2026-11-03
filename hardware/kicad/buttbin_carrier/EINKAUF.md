# Butt Bin Rev 0.8 – Einkaufsliste

Die Platine (Rev 0.8, Ø 34 mm, 2 Lagen, 1,6 mm) ist bei JLCPCB ohne Bestückung bestellt.
Die Bauteile werden von Hand gelötet. Die Mengen reichen für 10 Geräte, mit Reserve, weil 0603-Teile
beim Löten gern wegspringen. Zum Hochladen in den Reichelt-Warenkorb:
[reichelt_10_geraete.csv](reichelt_10_geraete.csv) (Artikel-Nr.;Menge, UTF-8).

## Reichelt

| Teil | Bestücken | Reichelt-Artikel | Hersteller / Typ | je Platine | bestellen | ca. Stückpreis |
|---|---|---|---|---|---|---|
| LED rot 0603 | D1, D4 | [LED EL 0603 RT](https://www.reichelt.de/de/de/shop/produkt/led_smd_1608_0603_rot_180_mcd_120_-156256) | Everlight 19-213/R6C-AQ1R2B, 624 nm | 2 | 25 | 0,05 € |
| LED gelb 0603 | D2, D5 | [LED EL 0603 GE](https://www.reichelt.de/de/de/shop/produkt/led_smd_1608_0603_gelb_180_mcd_120_-156259) | Everlight 19-213/Y2C-CQ2R2L/3T, 590 nm | 2 | 25 | 0,04 € |
| LED grün 0603 | D3, D6 | [LED EL 0603 GR1](https://www.reichelt.de/de/de/shop/produkt/led_smd_1608_0603_gruen_112_mcd_120_-156254) | Everlight 19-213/G6C-AP1Q2/3T, 565 nm | 2 | 25 | 0,07 € |
| Widerstand 330 Ω 0603 | R1–R6 | [SMD-0603 330](https://www.reichelt.de/de/de/shop/produkt/smd-widerstand_0603_330_ohm_100_mw_1_-89424) | Yageo, 1 % | 6 | 100 | 0,006 € ab 100 |
| Kondensator 100 nF 0603 | C3, C8, C9 | [WAL 0603B104K500](https://www.reichelt.de/de/de/shop/produkt/smd-kerko_0603_100_nf_50v_10_x7r_mlcc-346769) | Walsin, X7R 50 V | 3 | 40 | 0,02 € |
| Kondensator 10 µF 0603 | C2 | [CL10A106KQ8NNNC](https://www.reichelt.de/de/de/shop/produkt/mlcc_0603_10_f_6_3v_x5r_-10_-429034) | Samsung, X5R 6,3 V | 1 | 15 | 0,10 € |
| Kondensator 100 µF 1206 | C1 | [GRM31CR60J107M](https://www.reichelt.de/de/de/shop/produkt/mlcc_1206_100_f_6_3_v_-20_x5r-409218) | Murata, X5R 6,3 V | 1 | 12 | 0,13 € |
| Knopfzelle CR2450 | Halter im Unterteil | CR 2450 VAR 4X (4er-Pack) | Varta Lithium 3 V | 1 | 3 Packs = 12 | |

Zusammen etwa 9 € plus Versand.

- Die rote LED gibt es nur noch in begrenzter Stückzahl. Ersatz:
  [Huiyuan 0603R1C-KHA-C](https://www.reichelt.de/de/de/shop/produkt/led_smd_0603_rot_140_mcd_120_-361532),
  635 nm.
- Dazu 20 × [SMD-0603 1,0K](https://www.reichelt.de/de/de/shop/produkt/smd-widerstand_0603_1_0_kohm_100_mw_1_-89430),
  falls die LEDs zu hell sind (dann etwa 1 mA statt 2,5–3 mA).

## Woanders

- **Modul TB-03F**, Arcade-Button Retro+ S30, Halter CR2450 mit Drehdeckel, Silikonschlauch 21 × 16 mm,
  Pogo-Klemme 4-polig: bei AliExpress bestellt.
- **Nylon-Schraube M2** (6–8 mm) für das Loch über der Antenne: Reichelt hat keine. Ein Sortiment
  bei AliExpress kostet etwa 2 €. Metall nicht nehmen, das verstimmt die Antenne.
- **Litze** (dünn, sehr flexibel, z. B. 0,14 mm²) für Zelle und Button.

## Warum diese Teile

- **LEDs:** Alle drei Farben sind AlGaInP-LEDs aus einer Serie und brauchen höchstens 2,3–2,4 V. Damit
  leuchten sie an der Knopfzelle bis fast leer gleich hell. Smaragdgrün (520 nm) bräuchte etwa 3 V und
  bleibt an der CR2450 dunkel.
- **330 Ω:** etwa 2,5–3 mA je LED. Dunkler geht über die PWM in der Firmware. Die LEDs kosten trotzdem
  kaum Laufzeit, nur etwa 35 mAh im Jahr bei 30 Zählungen am Tag. Die Firmware sollte nie alle 6 LEDs
  gleichzeitig voll einschalten (etwa 18 mA), sonst bricht die Zelle beim Funken ein.
- **C1 keramisch statt Elko:** Ein Elko hätte mehr Leckstrom als das ganze Gerät im Schlaf.

## Beim Löten und Programmieren

- Die LED-Kathode (Markierung) zeigt zum Widerstand. Im Bestückungsdruck stimmt die Ausrichtung mit
  dem Footprint überein.
- Die Litzen an B+ und B− nicht vertauschen: Es gibt keinen Verpolschutz.
- Programmieren nie mit eingelegter Zelle **und** VBAT vom Programmer zugleich. Sonst lädt der
  Programmer die Lithium-Zelle. Entweder die Zelle herausnehmen oder den VBAT-Stift der Klemme frei
  lassen.
