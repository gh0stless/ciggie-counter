# Veröffentlichung: Stores und Kanäle

Arbeitsliste für die Veröffentlichung. Öffentlicher Entwicklername überall: **gh0stless (crazy-midi.de)**, Webseite https://crazy-midi.de, Quelltext https://github.com/gh0stless/ciggie-counter.

| Kanal | Stand |
|---|---|
| GitHub Releases | v1.0.0 vorhanden; v1.0.3 anlegen (Schritt 1) |
| IzzyOnDroid | Metadaten, Screenshots und Icon liegen in `fastlane/`; Antrag stellen (Schritt 2) |
| Home Assistant | Blueprints mit Import-Knopf in `nextcloud-app/homeassistant/README.md`; Forenbeitrag (Schritt 3) |
| F-Droid (Haupt-Repo) | vorbereitet, siehe unten |
| Nextcloud App Store | vorbereitet, siehe unten |
| Google Play | zurückgestellt, siehe unten |

## 1. GitHub-Release

Jede Version braucht einen Tag `vX.Y.Z` auf dem Commit, aus dem die APK gebaut wurde. IzzyOnDroid holt die APK aus dem Release, F-Droid baut aus dem Tag.

```sh
# im Projektordner, APK vorher mit ./gradlew assembleRelease (android-counter/) bauen
gh release create v1.0.3 \
  "android-counter/app/build/outputs/apk/release/app-release.apk#ciggie-counter-1.0.3.apk" \
  --title "Ciggie Counter 1.0.3" \
  --notes-file fastlane/metadata/android/en-US/changelogs/4.txt
```

Release-Notizen = `fastlane/metadata/android/en-US/changelogs/<versionCode>.txt`. Für jede neue Version: `versionCode`/`versionName` in `android-counter/app/build.gradle.kts` erhöhen, Changelogs `<versionCode>.txt` in `en-US` und `de-DE` anlegen.

## 2. IzzyOnDroid

Voraussetzungen (erfüllt): freie Lizenz (GPL-3.0), nur freie Bibliotheken (AndroidX), kein Tracking, signierte APK im GitHub-Release, `dependenciesInfo` abgeschaltet, Fastlane-Metadaten mit Screenshots und Icon im Repo.

Antrag: GitLab-Konto anlegen, dann neues Issue unter https://gitlab.com/IzzyOnDroid/repo/-/issues mit der Vorlage „Request for inclusion“. Text:

```text
Ciggie Counter – https://github.com/gh0stless/ciggie-counter

Package: de.crazymidi.ciggiecounter
License: GPL-3.0
APK: GitHub releases (signed, one APK per release)
Metadata: fastlane/metadata/android (en-US, de-DE, with screenshots and icon)
Author: gh0stless (crazy-midi.de)

Cigarette counter: +1 button, history, statistics, break timer, reminders
("You may smoke again", "Did you count them all?"), optional calendar summary,
optional sync with a self-hosted Nextcloud app, optional Bluetooth LE ashtray
("Butt Bin", DIY hardware in the same repo). No account, no ads, no tracking,
works without Google Play Services. English and German.

Permissions and why:
- POST_NOTIFICATIONS, SCHEDULE_EXACT_ALARM: reminders at the right time
- RECEIVE_BOOT_COMPLETED: re-arm reminders after reboot
- BLUETOOTH_SCAN (neverForLocation) / BLUETOOTH_CONNECT: only if a Butt Bin is paired, no location access
- READ_CALENDAR / WRITE_CALENDAR: only if the daily calendar summary is enabled
- INTERNET: only if Nextcloud sync is configured

Anti-features: none known. The optional Nextcloud sync talks to the user's own server only.
```

Vor dem Absenden die Berechtigungen mit `android-counter/app/src/main/AndroidManifest.xml` abgleichen.

## 3. Home Assistant (Blueprint Exchange)

HACS nimmt keine Blueprints. Blueprints werden im Forum geteilt: https://community.home-assistant.io/c/blueprints-exchange/53 (Forenkonto nötig). Ein Beitrag pro Blueprint, Import-Knopf wie in `nextcloud-app/homeassistant/README.md`. Vorschlag für den Ankündigungs-Blueprint:

```markdown
# 🚬 Cigarette counter: TTS & Telegram announcements (Nextcloud)

Speaks reminders of the self-hosted cigarette counter
([Nextcloud app + Android app](https://github.com/gh0stless/ciggie-counter))
via TTS and optionally Telegram: "You may smoke again", "Did you count them all?"
and "Cigarette number 12 counted" after every entry.

[import button from nextcloud-app/homeassistant/README.md]

- Trigger: local webhook (the Nextcloud app sends `{"message": "..."}`)
- Any TTS engine (e.g. Piper) and media player
- Optional: night schedule, do-not-disturb switch, only when someone is home,
  Telegram targets (muted at night if you like)

Texts of the blueprint and the messages are German for now.
Setup: https://github.com/gh0stless/ciggie-counter/tree/main/nextcloud-app/homeassistant
```

Der zweite Blueprint (Sprache & Telegram) braucht `cigcounter_package.yaml` und lohnt einen eigenen Beitrag erst, wenn die Texte englisch sind.

Später möglich: eine echte Integration (Python, `custom_components/`) für HACS, die die Nextcloud-API direkt abfragt, statt Paket + Blueprints. Eigenes Projekt, eigenes Repo.

## Vorbereitet für später

### F-Droid (Haupt-Repo)

F-Droid baut selbst aus dem Quelltext. Nach der Aufnahme bei IzzyOnDroid einen Merge Request auf https://gitlab.com/fdroid/fdroiddata mit `metadata/de.crazymidi.ciggiecounter.yml`, Entwurf:

```yaml
Categories:
  - Sports & Health
License: GPL-3.0-only
AuthorName: gh0stless (crazy-midi.de)
WebSite: https://crazy-midi.de
SourceCode: https://github.com/gh0stless/ciggie-counter
IssueTracker: https://github.com/gh0stless/ciggie-counter/issues
Changelog: https://github.com/gh0stless/ciggie-counter/releases

AutoName: Ciggie Counter

RepoType: git
Repo: https://github.com/gh0stless/ciggie-counter.git

Builds:
  - versionName: 1.0.3
    versionCode: 4
    commit: v1.0.3
    subdir: android-counter/app
    gradle:
      - yes

AutoUpdateMode: Version
UpdateCheckMode: Tags
CurrentVersion: 1.0.3
CurrentVersionCode: 4
```

Offen: Lizenz-Angabe im Code prüfen (`GPL-3.0-only` oder `-or-later`); ohne reproduzierbaren Build signiert F-Droid mit eigenem Schlüssel, Nutzer können dann nicht zwischen F-Droid- und GitHub-APK wechseln.

### Nextcloud App Store

1. Englische Oberfläche: Texte in `templates/` und `js/` auf `$l->t()` / `t('cigarettecounter', …)` umstellen, deutsche Übersetzung in `l10n/de.json` (und `de_DE`).
2. `info.xml`: englischer `<summary>`/`<description>`, `<website>`, `<bugs>`, `<repository>`, `<screenshot>`-URLs (Raw-Links auf GitHub), Autor ist schon gesetzt.
3. Zertifikat beantragen: Schlüssel + CSR erzeugen (`openssl req -nodes -newkey rsa:4096 -keyout cigarettecounter.key -out cigarettecounter.csr -subj "/CN=cigarettecounter"`), CSR per Pull Request an https://github.com/nextcloud/app-certificate-requests. **Schlüssel nie ins Repo**, wie der Android-Keystore unter `C:\Users\andre\Keys`.
4. Archiv bauen (`cigarettecounter/` inkl. `vendor/`, ohne Entwicklerdateien), mit `occ integrity:sign-app` signieren, `.tar.gz` als GitHub-Release-Asset hochladen, im Store mit Signatur registrieren.
5. Bekannte Schwäche: Der Kalender-Abgleich nutzt die interne `CalDavBackend`-Klasse, die sich zwischen Nextcloud-Versionen ändern kann. Nach jedem Major-Update testen.

Lizenz: Nextcloud-App `agpl` (info.xml), Rest des Repos GPL-3.0. Vor dem Store-Eintrag eine `LICENSE`/`COPYING` in `nextcloud-app/cigarettecounter/` ablegen.

### Google Play (zurückgestellt)

- Entwicklerkonto (einmalig 25 $), Identitätsprüfung mit echtem Namen; je nach Kontoart werden Land bzw. Adresse angezeigt. Entwicklername frei wählbar.
- Neue Privatkonten: geschlossener Test mit mindestens 20 Testern über 14 Tage vor der Veröffentlichung.
- Nötig: Datenschutzerklärung (URL, z. B. auf crazy-midi.de), Formular „Datensicherheit“, Inhaltsbewertung, App-Bundle (`./gradlew bundleRelease`), Feature-Grafik 1024×500.
- `SCHEDULE_EXACT_ALARM` ist erlaubt; für Bluetooth-Scan im Hintergrund kann Google eine Begründung verlangen.
