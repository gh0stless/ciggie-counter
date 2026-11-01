# Home Assistant

Home Assistant is supported by its own integration: **[gh0stless/ciggie-counter-ha](https://github.com/gh0stless/ciggie-counter-ha)** (installable via HACS).

- Runs standalone in Home Assistant, or syncs with this Nextcloud app (address, user, app password in the integration's options).
- Sensors, count button, mute switch, reminders as events, blueprints for TTS/Telegram announcements and for voice (Assist)/Telegram commands.
- The Android app can sync with Home Assistant directly, like with Nextcloud.

The webhook announcements, the YAML package with REST sensors and the old blueprints that used to live here were removed with Nextcloud app 0.10.0 – the integration replaces all of them.
