# Ciggie-Counter-Ziffernblatt für Zepp-OS-Uhren

Uhrzeit, Datum, Akku, Schritte, Puls, Stress, Schlaf der letzten Nacht und unten die Pause: „23 min / ab 14:35“, danach „frei“,
dazu die Tagesmenge. Im Always-on-Display bleiben Uhrzeit und Pause.

Ziel: Amazfit Band 7 (Zepp OS 1.0, 194 × 368). Die Werte stammen aus der Band-App
[../watch-app/](../watch-app/), die sie im systemweiten Zwischenspeicher ablegt
(`hmFS.SysProGetChars('ciggie')`). Ein Ziffernblatt darf auf Zepp OS 1.0 nicht selbst mit
dem Handy sprechen. Zusätzlich schickt die Ciggie-App ihren Stand über den Wetter-Kanal von
Gadgetbridge (Einstellung „Ziffernblatt aktuell halten“), dann ist das Ziffernblatt auch nach
Zählen am Handy oder Butt Bin sofort aktuell; es nimmt den neueren der beiden Stände
(Details in [../watch-app/README.md](../watch-app/README.md#ziffernblatt)).

## Bauen

Wie die Band-App (siehe deren README, auch die Warnung zu `zeppos-app-utils`):

```sh
npm install
npm run build
```

`dist/*.zab` in Gadgetbridge über den Datei-Installer aufs Band, dann am Band auswählen.

Doppeltipp auf den Ciggie-Kasten zählt eine Zigarette (die Band-App öffnet sich kurz, zählt und kehrt zurück).

Texte vorerst nur deutsch.

Erfahrungen und Fallstricke: [docs/zepp-os-band7-tricks.md](../docs/zepp-os-band7-tricks.md).
