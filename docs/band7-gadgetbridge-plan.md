# Zepp-OS-Uhren als Eingabegerät – Plan

> **Stand 05.11.2026 – umgesetzt und am Band 7 im Einsatz:** Gadgetbridge-Fork mit
> Mini-App-Messaging und PebbleKit-Fassade (P1, P3), Band-App mit Zählen, Puffer und
> Doppeltipp-Schnellzählen (P6), Ciggie-Counter-Empfänger (P7), Ziffernblatt mit Pause und
> Tagesmenge (P6b), Stand fürs Ziffernblatt auch über den Wetter-Kanal von Gadgetbridge.
> **Verworfen:** Messung von Puls/Blutsauerstoff vor/nach dem Rauchen (zurückgebaut,
> Andreas braucht sie nicht). **Offen:** Upstream-Beitrag (Codeberg #3266, Konto fehlt),
> Doppel-Quittungen der Fassade aufräumen, Side Service (P2/P4/P5), HA-Watch-App (eigenes
> Projekt). Erfahrungen und Fallstricke: [zepp-os-band7-tricks.md](zepp-os-band7-tricks.md).
> Der Rest dieses Dokuments ist der ursprüngliche Plan.

Stand: 01.11.2026 · Ziel: Amazfit Band 7 (und andere Zepp-OS-Uhren) als weiteres
Eingabegerät für Ciggie Counter – über Gadgetbridge, ohne Zepp-App, ohne Cloud.

Der große Wurf dabei: Gadgetbridge lernt, was bisher nur die Zepp-App kann –
**Mini-Apps auf der Uhr dürfen mit dem Handy reden.** Davon profitieren alle
Gadgetbridge-Nutzer (Codeberg-Issue
[#3266](https://codeberg.org/Freeyourgadget/Gadgetbridge/issues/3266), offen seit 2023).
Ciggie Counter ist nur die erste Anwendung; eine Home-Assistant-App für die Uhr
(Lampen, Szenen) wäre die nächste.

## Ausgangslage (geprüft am Quellcode)

| Was | Stand in Gadgetbridge `master` |
|---|---|
| Mini-Apps installieren (`.zab`/`.zpk`) | geht – aber nur `device.zip` wird behalten, der Handy-Teil (`app-side`) verworfen (`ZeppOsFwHelper.handleZabPackage`) |
| Nachrichten Uhr → Handy (Endpunkt `0x00a0`, Befehl `CMD_JS`) | ignoriert: `ZeppOsAppsService.handleJsPayload` loggt nur „not implemented“ |
| Side Service (JS auf dem Handy), Settings Storage, Einstellungsseiten | fehlt |
| Internetzugriff für Uhren-Apps (`fetch`) | fehlt; Gadgetbridge hat bewusst keine INTERNET-Berechtigung (Internet Helper als Zusatz-App geplant) |

### Vorarbeiten anderer, auf denen wir aufbauen

- **José Rebelo** (Gadgetbridge-Hauptentwickler), Zweig
  [`jr-zepp-os-js`](https://codeberg.org/joserebelo/Gadgetbridge/src/branch/jr-zepp-os-js)
  (Juli 2023, 4 Commits, ~3 300 Zeilen): Nachrichten, Settings Storage, Fetch-Proxy,
  Einstellungsseite in einer WebView. Selbstauskunft: „kind-of working, slightly
  unstable“. Bekannte Schwächen im Code: feste App-ID/Ports in Antworten, WebView
  wird nach der ersten Nachricht entfernt, Verzögerungen per `postDelayed(1000)`.
- **ysfchn**, [zepplin](https://codeberg.org/ysfchn/zepplin) (AGPLv3, aktiv bis
  Okt. 2026): freie Nachbildung von Side Service + Settings-UI in JavaScript mit
  austauschbaren „Peers“ (Anbindung an die Gastgeber-App) – eine
  Gadgetbridge-Anbindung ist genau dieser vorgesehene Erweiterungspunkt.
  Dokumentiert auch das Bluetooth-Nachrichtenformat (`zepplin/webview/ble.py`).
  ysfchn hat in #3266 angeboten zu helfen, sucht jemanden für die Java-Seite.

### Nachrichtenformat (Endpunkt `0x00a0`)

Die Nachricht beginnt direkt am ersten Byte; das Flag-Byte 1 (App) ist zugleich der
Endpunkt-Befehl `CMD_JS`. 16 Byte Kopf, Little Endian: `flag u8` (0 = Runtime, 1 = App) · `version u8` ·
`type u16` (1 SHAKE, 2 CLOSE, 3 HEART, 4 DATA, 5 DATA_WITH_SYSTEM_TOOL, 6 LOG) ·
`port1 u16` · `port2 u16` · `appId u32` · `extra u32` · danach Nutzdaten
(max. 3 600 Byte pro Nachricht). Mini-Apps legen darüber meist ein eigenes
Protokoll (Zepp-Beispiel `shared/message.js`, Bibliothek ZML).

## Architektur

```
 Uhr (Zepp OS)                 Gadgetbridge (Handy)                     Empfänger
┌──────────────┐  BLE 0x00a0  ┌───────────────────────────────┐
│ Mini-App     │─────────────▶│ ZeppOsAppsService             │
│ (device)     │◀─────────────│  ├ Transport: SHAKE/DATA/…    │
└──────────────┘              │  ├ App hat app-side?          │
                              │  │  ja → Side-Service-Host ───┼─▶ JS der App (zepplin-Laufzeit,
                              │  │       (WebView je App)     │    messaging, settingsStorage,
                              │  │                            │    fetch nur mit Internet Helper)
                              │  └ nein → PebbleKit-Fassade ──┼─▶ Android-Apps per PebbleKit
                              │            (nur freigegebene  │    (Ciggie Counter, HA-Brücke,
                              │             Apps, abschaltbar)│     Tasker …) – und zurück
                              └───────────────────────────────┘
```

Zwei Wege für zwei Arten von Apps:

1. **Vorhandene Zepp-Mini-Apps mit Side Service** laufen wie mit der Zepp-App
   (Kompatibilität, Hauptwunsch aus #3266).
2. **PebbleKit-Fassade** („virtuelle Pebble“, P3) für Apps ohne Side Service:
   Gadgetbridge reicht Nachrichten im PebbleKit-Android-Format an andere Apps weiter
   und nimmt Antworten entgegen. Das ist der einfache Weg für eigene Integrationen –
   Ciggie Counter braucht kein JavaScript auf dem Handy und bedient Pebble und Zepp OS
   mit einem Empfänger. Abschaltbar, standardmäßig aus.

## Arbeitspakete

Reihenfolge (entschieden 01.11.2026): P1 → P3 → P6 → P7 → P8; P2/P4/P5 (vorhandene
Zepp-Apps mit Side Service) danach, möglichst gemeinsam mit ysfchn.

### P1 – Gadgetbridge: Transport (Grundlage für alles)
- Kopf parsen/bauen als eigene Klasse mit Unit-Tests (Testdaten aus zepplin/José).
- SHAKE beantworten (richtige App-ID/Ports aus der Anfrage, nicht fest verdrahtet),
  CLOSE, HEART, DATA, LOG (Uhren-Logs ins Gadgetbridge-Log – hilft App-Entwicklern
  enorm, Band 7 zeigt sonst nur „gelben Bildschirm“).
- Größenbegrenzung/Stückelung, Verhalten bei Verbindungsabbruch.

### P2 – Gadgetbridge: Handy-Teil der App aufheben
- Beim Installieren von `.zab` den `app-side`-Teil je App-ID im App-Cache ablegen;
  beim Löschen der App entfernen. Anzeige in der App-Verwaltung („hat Side Service“).

### P3 – Gadgetbridge: PebbleKit-Fassade („virtuelle Pebble“)
- Entschieden 01.11.2026: keine eigene Intent-Schnittstelle, sondern Zepp-OS-Mini-Apps
  sehen für Android-Apps aus wie Pebble-Apps (PebbleKit Android, wie
  `PebbleKitSupport`): `com.getpebble.action.app.RECEIVE`/`SEND`/`ACK`/`NACK`.
- App-ID → UUID `%08x-0000-0000-0000-000000000000` (wie die App-Verwaltung schon).
- Nutzdaten der Mini-App = PebbleDictionary-JSON (`[{key,type,length,value}]`,
  UTF-8); die Uhren-App schreibt/liest dieses Format.
- Abschaltbar, standardmäßig aus (PebbleKit-Broadcasts sind für alle Apps lesbar).
- Vorteil: bekanntes Protokoll, fertige Bibliotheken; Ciggie Counter braucht einen
  Empfänger für Pebble und Zepp OS.

### P4 – Gadgetbridge: Side-Service-Host
- Unsichtbare WebView je laufender App, sauberer Lebenszyklus (SHAKE startet,
  CLOSE/Trennung beendet), keine `postDelayed`-Krücken.
- zepplin-Laufzeit als „gadgetbridge“-Peer einbinden (Absprache mit ysfchn:
  gebautes Bündel ins Repo oder Build-Schritt).
- Settings Storage dauerhaft je App/Gerät; Fetch nur über Internet Helper.

### P5 – Gadgetbridge: Einstellungsseiten der Apps (später)
- zepplin-Settings-UI in einer Activity; Einstieg aus der App-Verwaltung.

### P6 – Ciggie Counter für die Uhr
- Zepp-OS-1.0-App (Band 7: 194×368, Touch), Design nach der Projekt-Palette.
- Großer Knopf „gestempelt“, Tageszähler, letzte Zeit; Einträge mit eindeutiger ID
  und Zeitstempel puffern (auch ohne Handy), senden, erst nach Quittung löschen –
  passt zu Abgleich v2.
- Bau mit freien Werkzeugen (zmake/zepplin), nicht mit der Zepp-CLI.
- Veröffentlichung: GitHub-Release `.zab`, später evtl. Zepp-App-Store.

### P6b – Eigenes Ziffernblatt (Wunsch 01.11.2026)
- Ziffernblatt im Projekt-Design mit Tagesmenge; Tippfläche öffnet die Zähl-App.
- Offen: ob ein Ziffernblatt auf Zepp OS 1.0 den Stand der App lesen kann (getrennte
  Ablagen) – am Band prüfen; sonst nur Tippfläche zur App.

### P7 – Ciggie Counter Android
- PebbleKit-Empfänger (gilt für Pebble und Zepp OS), Einträge per ID entdoppeln, Quittung zurück,
  Tageszähler an die Uhr. Einstellung „Uhr (Gadgetbridge)“.

### P8 – Dokumentation und Upstream
- Pull Requests an Gadgetbridge in kleinen, prüfbaren Stücken (P1 → P2 → P3 → P4 →
  P5), jeweils mit Tests und Changelog-Eintrag.
- Wiki-Seite „Zepp OS: Mini-App-Kommunikation“ (Protokoll, PebbleKit-Fassade, Beispiel).
- README/Stores von Ciggie Counter ergänzen.

### Später – Pebble
- Pebble braucht keine Gadgetbridge-Erweiterung: Gadgetbridge kann PebbleKit JS und
  (experimentell) PebbleKit Android schon. Darum den Empfang in P7 allgemein als
  „Uhr-Eingabe“ bauen; eine Pebble-Uhren-App und ein zweiter Empfänger kommen dann
  günstig dazu – dank der PebbleKit-Fassade (P3) mit demselben Empfänger.

### Danach – Home Assistant auf der Uhr
- Eigene Mini-App (Lampen/Szenen/Skripte als Kacheln) über die PebbleKit-Fassade an eine
  kleine Android-Brücke oder über Side Service + Internet Helper direkt an HA.
  Entscheidung, wenn P3/P4 stehen.

## Test und Betrieb

- Eigenes Gadgetbridge als Build-Variante `nightly` (Paket
  `nodomain.freeyourgadget.gadgetbridge.nightly`) – liegt neben dem installierten
  Gadgetbridge. Das Band kann aber nur mit einem verbunden sein: zum Testen in der
  Nightly koppeln (Auth-Key aus dem bisherigen Gadgetbridge übernehmen), danach zurück.
- Werkzeuge: JDK 21 (portabel unter `~/.jdks`), Android SDK vorhanden.

## Offene Entscheidungen

- Codeberg-Konto für Fork und Pull Requests.
- Früh in #3266 melden (José, ysfchn), damit niemand doppelt arbeitet und P4 mit
  zepplin abgestimmt ist.
- Lizenz: Gadgetbridge und zepplin sind AGPLv3; die Uhren-App von Ciggie Counter
  folgt der Lizenz des Hauptprojekts.

## Risiken

- Verhalten auf Zepp OS 1.0 (Band 7) vs. 2.x/3.x unterscheidet sich; ohne weitere
  Uhren nur auf dem Band 7 testbar.
- Josés Notiz „instabil beim Neustart“ – Ursache unbekannt, P1/P4 müssen das klären.
- Annahme durch die Gadgetbridge-Maintainer ist nicht garantiert; bis dahin
  eigener Build.
