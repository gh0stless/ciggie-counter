# Ebyte E104-BT12LSP – Kurzfassung

> Quelle: `E104-BT12LSP_Datasheet_CN_V1.6.pdf` (Ebyte, V1.6 vom 13.12.2023, nur Chinesisch).
> Zusammengefasst am 28.10.2026 für den Superascher. Im Zweifel gilt das PDF.

## Überblick

| | |
|---|---|
| Chip | **Telink TLSR8253F512** (B85-Familie, 512 KB Flash) – im TC BLE SDK als **B85** |
| Bauform | SMD, **19 × 13 mm**, 26 Halbloch-Pads, Raster **1,27 mm** |
| Antenne | PCB-Antenne auf dem Modul (ca. 50 Ω), Freifeld bis ca. 60 m |
| Quarz | 24 MHz |
| Ab Werk | Ebyte-Firmware „SIG Mesh, Low Power Node“ mit UART-Befehlen (115200 8N1). Wird für den Superascher **überflasht** |
| Varianten | E104-BT12**N**SP = Mesh-Knoten, E104-BT12**L**SP = Low-Power-Knoten, E104-BT12**U**SP = Gateway (gleiche Hardware-Basis) |

## Elektrische Daten

| Parameter | Min | Typ | Max | Hinweis |
|---|---|---|---|---|
| Versorgung VCC | 1,9 V | 3,3 V | 3,6 V | **über 3,6 V dauerhaft zerstört**; ≥ 3,3 V für volle Sendeleistung |
| Logikpegel | | 3,3 V | | **kein 5-V-TTL** anschließen |
| Sendestrom | | 21 mA | | bei +10 dBm |
| Empfangsstrom | | 6,1 mA | | |
| Schlafstrom | | 13,3 µA | | Angabe für Ebytes Firmware |
| Sendeleistung | | | +10 dBm | |
| Empfindlichkeit | | −96 dBm | | bei 1 Mbit/s |
| Betriebstemperatur | −40 °C | | +80/85 °C | |

## Pinbelegung

Pad 1–9 an der einen Längsseite, 10–17 an der Schmalseite gegenüber der Antenne, 18–26 an der anderen Längsseite. Die Antenne liegt am freien Ende ohne Pads. Maßzeichnung: PDF Seite 5.

| Pad | Name | Richtung | Funktion laut Datenblatt | Verwendung im Superascher |
|---|---|---|---|---|
| 1 | GND | – | Masse | **GND** |
| 2 | PWM1 | Ausgang | PWM, grüner Kanal (HSL-Modell) | frei, GPIO unbekannt |
| 3 | PWM2 | Ausgang | PWM, roter Kanal | frei, GPIO unbekannt |
| 4 | NC | – | nicht belegt | – |
| 5 | NC | – | nicht belegt | – |
| 6 | **DIO1** | Eingang | Schalteingang = **PA0**, weckt aus dem Schlaf | **Stempel-Schalter** gegen GND |
| 7 | **DIO2** | Eingang | Schalteingang = **PA1**, weckt aus dem Schlaf | **LED** (als Ausgang, mit Vorwiderstand) |
| 8 | NC | – | nicht belegt | – |
| 9 | NC | – | nicht belegt | – |
| 10 | SWM | – | „nicht relevant“ | nicht nötig |
| 11 | **SWS** | – | Single-Wire-Debug | **Flashen:** an SWM des Telink-Programmers |
| 12 | NC | – | nicht belegt | – |
| 13 | LINK | – | Statusausgang der Ebyte-Firmware | frei |
| 14 | NC | – | nicht belegt | – |
| 15 | PWM3 | Ausgang | PWM, blauer Kanal | frei, GPIO unbekannt |
| 16 | NC | – | nicht belegt | – |
| 17 | TXD | Ausgang | UART senden | optional: Debug-Ausgabe |
| 18 | RXD | Eingang | UART empfangen | optional |
| 19 | **VCC** | – | Versorgung 1,9–3,6 V | **3,3 V / LiPo über LDO** |
| 20 | GND | – | Masse | **GND** |
| 21–24 | NC | – | nicht belegt | – |
| 25 | **RST** | Eingang | Reset, **low-aktiv** | optional (Taster/Programmer) |
| 26 | GND | – | Masse | **GND** |

Die GPIO-Namen von PWM1–3, TXD/RXD und LINK nennt das Datenblatt nicht. Bei Bedarf durchmessen oder im TLSR8253-Datenblatt anhand der Pad-Lage zuordnen.

## Minimalbeschaltung

- **VCC (19) und GND (1/20/26)**, Keramik-Kondensator direkt an VCC (im Ebyte-Schaltplan „C9“, Wert nicht angegeben; üblich 100 nF + 10 µF).
- **Flashen:** SWS (11), GND, ggf. VCC zum Programmer. Wie beim Dev-Board: Activate (`ac`), dann schreiben (`firmware/flash_b85.sh`).
- **Stempel:** Schalter von PA0 (6) nach GND, interner Pull-up in der Firmware.
- **LED:** PA1 (7) → Vorwiderstand ca. 1 kΩ → LED → GND (ca. 1–2 mA).

## Hinweise aus dem Datenblatt

- **Nicht in ein Metallgehäuse einbauen**, das verkürzt die Reichweite stark. Im Superascher deshalb in den Kunststoffknauf, Antenne über dem Edelstahl.
- Unter dem Modul keine Leiterbahnen führen, Masse durchgehend.
- Abstand zu Störquellen halten (Schaltregler, USB 3.0, andere 2,4-GHz-Funkstrecken).
- Stabile, saubere Versorgung, Verpolung zerstört das Modul.
- Ab Werk haben **alle Module dieselbe MAC-Adresse** `4C:4A:48:6C:14:18`. Bei mehreren Aschern eine eigene MAC setzen (der SDK liest sie aus dem Flash ab 0x76000).
- Reflow-Löten: bleifrei Spitze 230–250 °C, 30–90 s über 217 °C.

## Werks-Firmware (nur zur Info)

UART 115200 8N1, Hex-Rahmen `Länge | 0xC0 | Opcode | Daten`. Beispiele: `02 C0 06` = Werkseinstellungen, `02 C0 07` = MAC lesen, `02 C0 08` = Firmware-Version. Nach dem Überflashen mit eigener Firmware ist das alles weg.
