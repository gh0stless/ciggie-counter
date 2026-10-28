# Telink-Programmer (Burning EVK) – Kurzfassung

> Stand 28.10.2026. Allgemein für Telink-Chips nutzbar, Erfahrungen aus dem Superascher-Projekt.
> Quelle u. a.: BDT User Guide `AN-18101200-E10` (liegt im BDT-Paket unter `doc/`), Telink-Forum.
> **Offen** = nicht belegt, bitte nachtragen.

## Was ist das?

Programmier- und Debug-Adapter von Telink („Burning EVK“, laut BDT-Handbuch basierend auf **TLSR8266ET56**).
Er spricht mit dem Zielchip über den Telink-Eindrahtbus **Swire** (Programmer-Pin **SWM** → Ziel-Pin **SWS**).
Kunststoffgehäuse mit Aufschrift „Telink“, USB-A-Buchse, 12-polige Pfostenleiste, 4 LEDs, 2 Taster.

| | |
|---|---|
| USB-Kennung am PC | `VID_248A` `PID_5320` |
| Generationen | **V3.0** (älter, unterstützt fast alle Telink-Chips) und **V5.0** (neuer). Beide können B85 (TLSR825x/827x/8359/8355), B87, B91/B92, TC321x … In BDT wählt man die Version von Hand, die SDK-Doku empfiehlt „Programmer V1.0 ~ V3.0“ |
| Software | **BDT** (Burning and Debugging Tool), Windows, z. B. `release_v5.9.5` |

## Anschlüsse

| Anschluss | Zweck |
|---|---|
| USB-A-Buchse | Verbindung zum PC. Laut BDT-Handbuch können Zielboards mit eigenem USB (z. B. Telink-Dongle) auch direkt per USB am Programmer geflasht werden |
| 12-polige Pfostenleiste | Swire zum Zielboard: **SWM**, **GND**, **VCC (3,3 V)**. **Offen: genaue Pinbelegung der Leiste** |
| 4 LEDs | Laut Handbuch blinkt beim Anstecken an den PC eine Kontrollleuchte einmal (= erkannt). **Offen: Bedeutung der einzelnen LEDs** |
| 2 Taster (einer „RST“) | **Offen: Funktion.** „RST“ setzt vermutlich den Programmer selbst zurück |

## Verkabelung zum Zielboard

| Programmer | Zielboard |
|---|---|
| SWM | SWS |
| GND | GND |
| VCC 3,3 V | VCC – **nur**, wenn das Ziel keine eigene Versorgung hat. Nie zwei Versorgungen gegeneinander |

**Vorsicht:** SWS nicht versehentlich an 3V3 legen. Im Telink-Forum berichtet jemand, dass sich der Chip danach nicht mehr aktivieren und flashen ließ.

## Software einrichten

1. BDT ist enthalten in der **Telink-VS-Code-Extension** („Telink Development Tool“ + „Telink Flash Tool“, Bereich *Development Tools → BDT*), landet unter `%USERPROFILE%\.Telink_Tools\BDT\`. Alternativ einzeln von telink-semi.com.
2. Die grafische Oberfläche ist `Telink BDT.exe`, die Kommandozeile ist `config\Cmd_download_tool.exe`.
3. **Programmer-Firmware aktualisieren** (einmalig, falls Fehler `0x1001` kommt): in der BDT-Oberfläche die Upgrade-Funktion öffnen (Handbuch: „Read FW Version“ → „Load…“ → „Upgrade“), Firmware aus `config\fw\` (z. B. `Firmware_v5.3.bin`). Während des Updates nicht abziehen.

## Kommandozeile (`Cmd_download_tool.exe`)

Allgemein: `Cmd_download_tool.exe <Geräte-ID> <Chip> <Befehl> …` (Chip z. B. `B85`, `B87`, `TL721X`)

| Befehl | Bedeutung |
|---|---|
| `all` | angeschlossene Programmer mit Device-ID auflisten |
| `1 B85 ac` | **Activate**: Chip anhalten (nötig, wenn die Firmware im Deep Sleep ist, sonst „Swire error“) |
| `1 B85 lf 0 0` | Flash-Schutz aufheben (scheitert manchmal, Schreiben klappt trotzdem) |
| `1 B85 wf 0 -i "C:\pfad\firmware.bin"` | Firmware ab Adresse 0 schreiben |
| `1 B85 rf 70000 -s 64` | 64 Byte Flash ab 0x70000 lesen (`-o datei.bin` zum Speichern) |
| `1 B85 rst -f` | Chip zurücksetzen (Firmware startet) |
| `1 B85 fi` | Flash-Infos (MID, Sperrstatus) |
| `1 B85 pc` | Programmzähler lesen (wo hängt die Firmware?) |
| `wc/rc`, `wa/ra` | RAM/Register bzw. Analog-Register schreiben/lesen |

Bewährte Reihenfolge zum Flashen: `ac` → `lf 0 0` (Fehler ignorieren) → `wf` → `rst -f`.

## Fehlermeldungen (beobachtet)

| Meldung | Ursache / Abhilfe |
|---|---|
| Windows: „Unbekanntes USB-Gerät (Fehler beim Anfordern einer Gerätebeschreibung)“ | Programmer nicht richtig erkannt → anderes Kabel/anderen USB-Port, direkt am PC statt am Hub, neu anstecken |
| `No device available!` | Programmer nicht verbunden bzw. nicht erkannt |
| `Error<0x1001>: EVK command not supported, please update the firmware` | Programmer-Firmware zu alt für das BDT → Firmware-Upgrade (siehe oben) |
| `TC32 EVK: Swire error` / `Error<0x1002>` | Ziel antwortet nicht: Chip im Deep Sleep → erst `ac`; sonst Verkabelung SWM/SWS/GND prüfen, Ziel kurz stromlos machen und sofort flashen |
| `Swire ok` + `Error<0x1101>: DUT command execute error` beim `lf` | Entsperren schlug fehl, Schreiben (`wf`) funktionierte trotzdem |

## Superascher-Projekt

Skript `firmware/flash_b85.sh [projekt] [device-id]` erledigt `ac` → `lf` → `wf` → `rst` (ohne ID: listet die Programmer).
