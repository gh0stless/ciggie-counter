# Home Assistant integration

Home Assistant talks to the **Nextcloud app** `cigarettecounter`, not to the phone. That way it works no matter where the phone is (guest Wi-Fi, mobile data), and the browser, the Android app, the Butt Bin and voice commands all share one state.

The YAML files and their UI texts are in German; entity names and sentences can be changed in the blueprint inputs.

| File | What it does |
|---|---|
| `cigcounter_announce_blueprint.yaml` | Speaks Nextcloud's messages via TTS (and optionally Telegram): reminders and “12. Zigarette gezählt.” after every entry. Triggered by a webhook. |
| `cigcounter_package.yaml` | REST sensors (today, month, year, cost, next allowed, break length) and `rest_command.cigcounter_add`. |
| `cigcounter_assist_blueprint.yaml` | Count and ask by voice (Assist) or Telegram command. Needs the package. |
| `cigcounter_dashboard.yaml` | Dashboard view (needs [Mushroom cards](https://github.com/piitaya/lovelace-mushroom) from HACS). Needs the package. |

## 1. Announcements (Nextcloud → Home Assistant)

1. Import `cigcounter_announce_blueprint.yaml` (Settings → Automations & scenes → Blueprints → Import, or copy it to `config/blueprints/automation/`).
2. Create an automation from it. Pick a secret **webhook ID** (a long random string; it works like a password), your TTS engine (e.g. Piper) and the speaker. Night schedule, do-not-disturb switch, persons at home and Telegram targets are optional.
3. In the Nextcloud app (⚙ Settings) enter the webhook URL
   `http://<HA-IP>:8123/api/webhook/<webhook ID>`
   Use the **IP address**: `.local` names never resolve inside the Nextcloud Docker container.
4. Switch on what should be announced: “Nächste erlaubt”, “Hast du alle gezählt?” and/or “Ansage bei jeder Eingabe”, then save. “🔊 Ansage testen” sends a test message.

The trigger is `local_only`, so Nextcloud and Home Assistant must be in the same network. Home Assistant answers every webhook call with HTTP 200, even for an unknown ID; check the automation trace if nothing is spoken.

## 2. Sensors, voice and dashboard (Home Assistant → Nextcloud)

1. Create an app password in Nextcloud (Settings → Security) and add to `secrets.yaml`:

   ```yaml
   cigcounter_today_url: https://<nextcloud>/index.php/apps/cigarettecounter/api/today
   cigcounter_add_url:   https://<nextcloud>/index.php/apps/cigarettecounter/api/add
   cigcounter_user:      <nextcloud user>
   cigcounter_password:  <app password>
   ```

2. Copy `cigcounter_package.yaml` to `config/packages/` (packages must be enabled: `homeassistant: packages: !include_dir_named packages`) and restart Home Assistant.
3. Import `cigcounter_assist_blueprint.yaml` and create an automation from it. Default sentences are German (“Zigarette zählen”, “wie viele Zigaretten heute”, “darf ich rauchen” …) and can be changed in the inputs.
4. Optional: add `cigcounter_dashboard.yaml` as a new dashboard view (raw configuration editor).

If “Ansage bei jeder Eingabe” is on, counting by voice is announced by Nextcloud as well, in addition to Assist's own answer.
