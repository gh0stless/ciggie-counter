# Ciggie Counter für Zepp-OS-Uhren

Zählt am Handgelenk: großer „+1“-Knopf, Tageszähler, Uhrzeit der letzten. Einträge werden
auf dem Band gepuffert (auch ohne Handy) und erst gelöscht, wenn die Ciggie-Counter-App
sie bestätigt hat.

Ziel: Amazfit Band 7 (Zepp OS 1.0, 194 × 368). Verbindung zum Handy über
**Gadgetbridge mit PebbleKit-Fassade** (eigener Fork, siehe
[docs/band7-gadgetbridge-plan.md](../docs/band7-gadgetbridge-plan.md)) – keine Zepp-App nötig.

## Bauen

```sh
npm install
npm run build
```

Ergebnis: `dist/*.zab`, in Gadgetbridge über den Datei-Installer aufs Band.

`zeus-cli` 1.9.3 verweist auf sein mitgeliefertes Modul `zeppos-app-utils` mit einem
Pfad ohne `file:` – npm findet es deshalb nicht. Das `postinstall`-Skript kopiert das
mitgelieferte Modul an seinen Platz. **Nicht** `npm install zeppos-app-utils` ausführen:
das gleichnamige Paket im öffentlichen npm-Verzeichnis stammt nicht von Zepp.

## Protokoll

Für Android-Apps sieht die Band-App aus wie eine Pebble-App mit der UUID
`001071c5-0000-0000-0000-000000000000` (App-ID 1077701). Nachrichten sind
PebbleKit-Dictionaries.

| Schlüssel | Bedeutung |
|---|---|
| 0 | Befehl (Text) |
| 1 | Eintrags-ID (UUID, wie Abgleich v2) |
| 2 | Zeitpunkt (Unix-Sekunden) |
| 3 | Anzahl heute |
| 4 | Zeitpunkt der letzten (Unix-Sekunden) |
| 5 | Nächste erlaubt ab (Unix-Sekunden, 0 = keine Pause eingestellt) |

Band → Handy

- `hello` – App geöffnet, bitte Stand schicken
- `entry` + 1 + 2 – eine Zigarette; wird wiederholt, bis sie quittiert ist

Handy → Band

- `ack` + 1 + 3 (+ 4, 5) – Eintrag übernommen (Duplikate per ID verwerfen, trotzdem quittieren)
- `state` + 3 + 4 + 5 – aktueller Stand, Antwort auf `hello`

## Schnellzählen

Doppeltipp aufs Ziffernblatt öffnet `page/index` mit dem Parameter `count`: Die Seite zählt
sofort (Vibration), wartet auf die Quittung des Handys und kehrt dann zum Ziffernblatt zurück,
ohne Quittung nach 8 Sekunden. Unquittiertes bleibt vorgemerkt und wird später gesendet.

## Ziffernblatt

Das Ziffernblatt in [../watchface/](../watchface/) bekommt den Stand aus zwei Quellen und
nimmt den neueren (Zeitpunkt am Ende):

- Band-App: systemweiter Zwischenspeicher,
  `hmFS.SysProSetChars('ciggie', 'Tag|heute|letzte|nächste|Zeitpunkt')`, Tag als JJJJMMTT.
- Handy über den **Wetter-Kanal** von Gadgetbridge (Einstellung „Ziffernblatt aktuell
  halten“): Die Ciggie-App schickt nach jeder Änderung
  `nodomain.freeyourgadget.gadgetbridge.ACTION_GENERIC_WEATHER` mit dem Ortsnamen
  `CC|Tag|heute|letzte|nächste|Zeitpunkt`; Gadgetbridge gibt den Ortsnamen sofort ans Band,
  das Ziffernblatt liest ihn über `hmSensor.id.WEATHER`. So ist es auch aktuell, wenn am
  Handy oder am Butt Bin gezählt wird und die Band-App zu ist. Das Wetter des Bandes ist
  damit belegt.

## Hinweise

- Die App-ID ist vorläufig selbst gewählt; für eine Veröffentlichung im Zepp-Store
  vergibt die Zepp-Entwicklerseite eine eigene.

Erfahrungen und Fallstricke mit Zepp OS 1.0 auf dem Band 7: [docs/zepp-os-band7-tricks.md](../docs/zepp-os-band7-tricks.md).
