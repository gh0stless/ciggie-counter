# Zepp OS 1.0 auf dem Amazfit Band 7: Programmier-Tricks

Gesammelt beim Bau der Band-App ([../watch-app/](../watch-app/)) und des Ziffernblatts
([../watchface/](../watchface/)), November 2026. Gerät: Amazfit Band 7, Firmware 1.11.0.1,
gekoppelt mit Gadgetbridge (ohne Zepp-App). Alles hier ist am Gerät ausprobiert, sofern nicht
anders vermerkt.

## Gerät und Projekt

- Band 7 = Zepp OS **1.0**, Bildschirm 194 × 368 px, `designWidth: 194`.
- `deviceSource` 252 / 253 / 254 eintragen. Das internationale Band 7 meldet 254; 252 und 253
  sind vermutlich China-Varianten.
- App-IDs sind vorläufig selbst gewählt: 1077701 Band-App, 1077703 Ziffernblatt,
  1077702 reserviert für die HA-Watch-App. Für den Zepp-Store vergibt die Entwicklerseite eigene.

## Bauen mit zeus-cli

- `@zeppos/zeus-cli` 1.9.3 lokal per npm, `npm run build` ergibt `dist/*.zab`.
- zeus findet sein mitgeliefertes Modul `zeppos-app-utils` nicht: Die Abhängigkeit steht als
  `private-modules/zeppos-app-utils` ohne `file:` drin, npm liest das als GitHub-Kurzform.
  Abhilfe: `postinstall` kopiert das mitgelieferte Modul nach `node_modules/` (siehe
  `package.json`).
- **Nie** `npm install zeppos-app-utils`: Das gleichnamige Paket im öffentlichen npm-Verzeichnis
  stammt nicht von Zepp (Maintainer guhuatai, 2022).
- Symbol mindestens 96 px, sonst Warnung.
- Vorlagen für Ziffernblätter liegen in
  `node_modules/@zeppos/zeus-cli/private-modules/zeppos-app-utils/dist/public/template/os1.0/watchface/`.
  Ziffernblatt: `appType: "watchface"`, Modul `watchface` mit `path`, `main: 1`.

## Installieren über Gadgetbridge

- Datei-Installer in Gadgetbridge nimmt `.zab` für Apps **und** Ziffernblätter.
- Das zab-Format neuerer zeus-Versionen (ab 1.7) hat `deviceSource` nur noch in
  `device.zip/app.json`. Gadgetbridge brauchte dafür eine Korrektur (eigener Fork, Commit
  `aa0ee8f8f`), sonst „nicht kompatibel“.
- Gleiche App-ID = Update, die alte Fassung wird ersetzt.
- Datei aufs Handy mit adb; in Git Bash `MSYS_NO_PATHCONV=1` setzen, sonst wird `/sdcard/…`
  in einen Windows-Pfad umgeschrieben.
- **„Logdateien schreiben“ in Gadgetbridge ausgeschaltet lassen.** Solange es an war, startete
  das Band 7 beim bloßen Tragen mehrmals neu; nach dem Abschalten nicht mehr (03.11.2026).
  Die Ursache ist nicht geklärt. Zum Fehlersuchen nur kurz einschalten.
- Nur **ein** Gadgetbridge darf mit dem Band verbunden sein. Hängen zwei dran (z. B. F-Droid-
  Version und eigener Build), bekommt der eigene keine Aktivitätsdaten und zeigt das Band rot.

## Zeit: JavaScript rechnet in China-Zeit

`Date` auf dem Band rechnet **immer in UTC+8**, egal welche Zeitzone eingestellt ist.
`Date.now()` stimmt (Unix-Zeit), aber `getHours()`, `getDate()` usw. liefern chinesische
Ortszeit. Folgen ohne Korrektur: Uhrzeiten 7 Stunden falsch (MEZ), Tageswechsel um 17:00.

Die echte Ortszeit kennt nur der Uhr-Sensor. Verschiebung daraus ableiten:

```js
const clock = hmSensor.createSensor(hmSensor.id.TIME)
const local = Date.UTC(clock.year, clock.month - 1, clock.day, clock.hour, clock.minute, clock.second) / 1000
const offset = Math.round((local - Math.floor(Date.now() / 1000)) / 60) * 60
// Ortszeit eines Zeitpunkts: new Date((t + offset) * 1000).getUTCHours() usw.
```

Umgesetzt als `localDate()` in `watch-app/lib/store.js`.

## Daten zwischen App und Ziffernblatt

- Ein Ziffernblatt kann auf Zepp OS 1.0 nicht selbst mit dem Handy sprechen.
- Austausch über den **systemweiten Zwischenspeicher**: Die App schreibt
  `hmFS.SysProSetChars('ciggie', '…')`, das Ziffernblatt liest `hmFS.SysProGetChars('ciggie')`.
  Funktioniert über App-Grenzen hinweg. Der Inhalt ist nach einem Neustart des Bandes weg.
- Der Stand ist nur so aktuell wie die letzte Verbindung der App. Das Ziffernblatt muss mit
  „noch nichts da“ umgehen können.

## Ziffernblatt

- **Handy → Ziffernblatt ohne offene App: Wetter-Kanal.** Eine Android-App schickt
  `nodomain.freeyourgadget.gadgetbridge.ACTION_GENERIC_WEATHER` mit Extra `WeatherJson`
  (`{"timestamp", "location", "currentTemp" in Kelvin, …}`) gezielt an Gadgetbridges
  `GenericWeatherReceiver`. Gadgetbridge setzt den Ort sofort am Band (Zepp OS:
  `CMD_SET_DEFAULT_LOCATION` mit dem Ortsnamen), das Band holt dann das Wetter per HTTP.
  Das Ziffernblatt liest den Ortsnamen unverändert über
  `hmSensor.createSensor(hmSensor.id.WEATHER).getForecastWeather().cityName`. Am Band
  bestätigt 03.11.2026; belegt das Wetter.

- Aktualisieren: `clock.addEventListener(clock.event.MINUTEEND, update)` plus
  `hmUI.createWidget(hmUI.widget.WIDGET_DELEGATE, { resume_call: update })` für das Aufwecken.
- Sensoren: `hmSensor.id.BATTERY` (`current`), `STEP` (`current`), `HEART` (`last`),
  `STRESS` (`current`, liefert oft 0 = gerade kein Wert), `SLEEP` (`getTotalTime()` in Minuten).
- **Absturz mit Neustart des Bandes:** Event-Listener auf Puls (`heart.event.LAST`) und Stress
  (`hmSensor.event.CHANGE`), möglicherweise auch `stress.getTodayByHour()`, ließen das Band beim
  Antippen des Ziffernblatts abstürzen. Sensoren deshalb nur im Minuten-Takt und beim Aufwecken
  lesen, jeden Sensor in eigenem `try`.
- Always-on-Display: `show_level: hmUI.show_level.ONLY_NORMAL | hmUI.show_level.ONAL_AOD`
  (so geschrieben, „ONAL“) für Widgets, die auch im AOD stehen; Hintergrund nur `ONLY_NORMAL`.
- `alpha` an `FILL_RECT` wird ignoriert: Eine „unsichtbare“ Tipp-Fläche wird deckend gemalt und
  verdeckt alles darunter. Tipps stattdessen an die sichtbaren Widgets hängen:
  `widget.addEventListener(hmUI.event.CLICK_UP, fn)`.
- Doppeltipp gibt es nicht fertig: zwei `CLICK_UP` innerhalb von 500 ms selbst erkennen.
- App aus dem Ziffernblatt starten: `hmApp.startApp({ appid: 1077701, url: 'page/index' })`.

## Messen auf Abruf (aus einer App)

Ausprobiert mit einer Probe-App am 03.11.2026. Puls-, Blutsauerstoff- und Stress-Sensor haben
`start()` und `stop()`; damit misst das Band sofort, nicht erst nach seinem eigenen Zeitplan.

- Werte per Timer abfragen (z. B. jede Sekunde), keine Event-Listener (siehe Absturz oben).
- **Blutsauerstoff** (`hmSensor.id.SPO2`): Rote LED leuchtet 15–20 s, nach etwa 14 s steht ein
  neuer Wert in `current`. Fertig ist die Messung, wenn sich `time` ändert; `retcode` blieb
  dabei unverändert 2 und taugt nicht als Fertig-Meldung.
- **Stress** (`hmSensor.id.STRESS`): **nicht per `start()` messen.** Nach `start()` springen
  `current` und `time` auf 0; nach gut 2 Minuten ohne Ergebnis startete das Band neu. Stress
  errechnet die Firmware über längere Zeit (Herzratenvariabilität); nur `current` lesen
  (0 = gerade kein Wert).
- **Puls** (`hmSensor.id.HEART`): Nach `start()` misst das Band (grüne LED), aber `current`
  bleibt ohne Event-Listener 0. Die fertige Messung steht in `last`: warten, bis sich `last`
  ändert (etwa 12 s), sonst den bisherigen `last` als jüngsten Wert nehmen.
- Nach der Messung und in `onDestroy` immer `stop()` aufrufen, sonst misst das Band weiter.
- Bildschirm während der Messung anlassen: `hmSetting.setBrightScreen(Sekunden)`.
  **Nicht** `hmSetting.setBrightScreenCancel()` zum Beenden nehmen: Das schaltet den
  Bildschirm sofort aus und schließt damit die App. Stattdessen `setBrightScreen(20)` für
  eine kurze Restzeit; `setBrightScreenCancel()` nur in `onDestroy`.
- App mit Parameter starten: `hmApp.startApp({ appid, url: 'page/index', param: 'count' })`,
  die Seite bekommt ihn in `onInit(param)`. Zurück zum Ziffernblatt mit `hmApp.goBack()`.

## Verbindung zum Handy (Mini-App-Nachrichten)

- `hmBle.createConnect(cb)`, `hmBle.send(buf, len)`, `hmBle.disConnect()`.
- Rahmen: 16 Byte Kopf, Little Endian, ab Byte 0: flag u8 (1 = App), version u8 (1), type u16
  (1 SHAKE, 2 CLOSE, 3 HEART, 4 DATA, 6 LOG), port1 u16, port2 u16, appId u32, extra u32,
  danach die Nutzdaten (höchstens 3584 Byte).
- Ablauf: Band schickt SHAKE mit port2 = 0 und als Nutzdaten das untere Byte der App-ID.
  Gadgetbridge antwortet mit Port 1004. Danach nimmt das Band nur DATA mit genau diesem Port an.
- Gadgetbridge reicht die Nutzdaten über die PebbleKit-Fassade als PebbleKit-Dictionary-JSON an
  Android-Apps weiter (UUID `%08x-0000-0000-0000-000000000000` aus der App-ID). Siehe
  [band7-gadgetbridge-plan.md](band7-gadgetbridge-plan.md) und `watch-app/README.md`.
- Das Handy erreicht die Band-App nur, solange sie geöffnet ist.

## Sonstiges

- Text ist sicher als ASCII; JSON vor dem Senden byteweise umwandeln (`charCodeAt(i) & 0x7f`).
- Dateien der App: `hmFS.open/read/write/stat` mit relativem Namen, liegen im App-eigenen Bereich.
- Vibration: `hmSensor.createSensor(hmSensor.id.VIBRATE)`, `scene = 25`, `start()`.
- Wiederholung: `timer.createTimer(delay, period, fn)` / `timer.stopTimer(t)`.
- Workouts lassen sich nicht um eigene Typen erweitern, das legt die Firmware fest.
