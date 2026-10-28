# Telink TLSR8258 Dev-Board (TLSR8258DK48, C1T139A30) – Kurzfassung

> Stand 28.10.2026. Allgemein nutzbar, Erfahrungen aus dem Superascher-Projekt.
> Quellen: TC BLE SDK (`vendor/common/boards/C1T139A30.h`), TLSR8253/8258-Datenblatt, eigene Tests.
> Die offizielle Board-Beschreibung („TLSR8258DK48 EVK Specification“) gibt es bei
> [fcc.report](https://fcc.report/FCC-ID/OEOTLSR8258DK48D/4223590.pdf), im Browser öffnen.
> **Offen** = nicht belegt, bitte nachtragen.

## Kennung

| | |
|---|---|
| Aufdruck | `TLSR8258DK48 C1T139A30_V1.2 2018-10-18` |
| Chip | **TLSR8258F512** (QFN48), Telink-Familie **B85**, 512 KB Flash, BLE 5 / 2,4 GHz |
| Im SDK | `CHIP_TYPE_825x`, Board `BOARD_825X_EVK_C1T139A30` (Board-Datei `C1T139A30.h`) |
| Bezeichnung im Handel | TLSR8258DK48D (Board einzeln), TLSR8258DK48D-KIT (mit Programmer) |

## Belegung laut SDK (Board-Datei)

| Funktion | Pins | Hinweis |
|---|---|---|
| **4 Taster** als 2×2-Matrix | Treiber PB4, PB5 · Abfrage PB2, PB3 | Wecken aus dem Schlaf über die Treiber-Pins |
| **4 LEDs** | PD2 blau, PD3 grün, PD4 weiß, PD5 rot | aktiv High |
| Debug-Ausgabe (printf, UART TX) | PB1 | im SDK `UART_PRINT_DEBUG_ENABLE` |
| Batteriespannung messen | PB7 (ADC) | im SDK `APP_BATT_CHECK_ENABLE` |
| Debug-GPIOs (Logikanalysator) | PD0, PD1, PD6, PD7, PA2–PA4, PB0, PC0, PC1, PB6, PB7, PC4–PC7 | im SDK `DEBUG_GPIO_ENABLE` |
| Flashen/Debuggen | **SWS** | an SWM des Telink-Programmers |

## Jumper und Stiftleisten

**Offen – Belegung aus der EVK-Spezifikation nachtragen.** Üblich bei Telink-EVKs (nicht geprüft):

- Stiftleisten führen alle GPIOs (PA…PD) heraus.
- Jumper verbinden Board-Bauteile (LEDs, Taster) mit den Chip-Pins. Gezogen → Pin frei für eigene Hardware.
- Jumper zur Wahl der Versorgung (USB oder extern).
- Jumper in der Versorgung des Chips → hier ein Multimeter einschleifen, um den **Ruhestrom** zu messen. Die Board-LEDs und der USB-Teil verfälschen sonst die Messung.

| Jumper / Leiste | Funktion |
|---|---|
| … | (nachtragen) |

## Versorgung und Flashen

- Versorgung über die **USB-Buchse des Boards**. Deren USB-Datenleitungen gehen an den Chip und funktionieren nur mit passender Firmware (zum Flashen nicht nutzbar).
- Flashen über den **Telink-Programmer** (siehe `Telink-Programmer.md`): GND–GND, SWM–SWS. VCC vom Programmer nur, wenn das Board nicht per USB versorgt wird.
- Läuft auf dem Board eine Firmware mit Deep Sleep (z. B. jede BLE-Firmware mit Stromsparen), vor dem Flashen **Activate** (`ac`), sonst „Swire error“.

## Chip-Eckdaten (Datenblatt TLSR8253/8258)

| | |
|---|---|
| Versorgung | 1,8–3,6 V |
| Tiefschlaf, Wecken per GPIO | 0,4 µA |
| Tiefschlaf mit RAM-Erhalt + 32k-Timer | 1,5–1,9 µA |
| Senden 0 dBm / Empfangen | 4,8 mA / 5,3 mA |
| Wecken | jeder GPIO, 32-kHz-Timer, Komparator (aus jedem Tiefschlaf) |
| Flash-Belegung im SDK (512 KB) | Firmware ab 0x00000, OTA ab 0x20000, MAC 0x76000, Kalibrierung 0x77000, SMP 0x78000 |

## Software

- **SDK:** TC BLE SDK (github.com/telink-semi/tc_ble_sdk), Beispiele unter `vendor/`. Für den Einstieg `acl_peripheral_demo`, das schon auf dieses Board eingestellt ist.
- **Toolchain:** TC32-GCC (`tc32-elf-gcc` 4.5.1), über die Telink-VS-Code-Extension installierbar.
- **Bauen ohne IDE** und Flashen: siehe Skripte im Superascher-Projekt (`firmware/build_b85.sh`, `firmware/flash_b85.sh`).

## Superascher-Projekt

- Taster = Ersatz für den Stempel, grüne LED = Druck erkannt, blaue LED = Abgleich mit dem Handy fertig.
- Für Strommessungen der Superascher-Firmware ist das Board wegen LEDs/USB-Teil nur eingeschränkt geeignet. Genauer misst man am E104-Modul.
