# Ciggie Counter & Butt Bin

Count your cigarettes, see your patterns, pace yourself, without ads, accounts or tracking.

<p>
  <img src="design/Design%20%231.jpg" width="49%" alt="Butt Bin design: a brushed steel ashtray with a red glitter plunger knob that lights up, the knob also shown upside down with its USB-C charging port">
  <img src="design/Concept%20%231.jpg" width="49%" alt="Butt Bin concept: a brushed steel ashtray with a counter display and a plunger button">
</p>

*Butt Bin design studies (AI-generated renders, not the real prototype yet).*

This repository contains three parts that work on their own or together:

| Part | Folder | What it does |
|---|---|---|
| **Ciggie Counter** (Android app) | [`android-counter/`](android-counter/) | Counter with +1 button, history, statistics, break timer, reminders, optional calendar summary and Nextcloud sync. English and German. |
| **Butt Bin** (hardware, prototype) | [`firmware/`](firmware/) | An ashtray with a plunger that counts every cigarette you stub out, stores it with a timestamp and hands it to the app via Bluetooth LE, even when the phone was away. |
| **Nextcloud app** `cigarettecounter` | [`nextcloud-app/cigarettecounter/`](nextcloud-app/cigarettecounter/) | Self-hosted web app/PWA with the same counting logic; lets several devices (phone, tablet) share one state. |

More about the Butt Bin: <https://crazy-midi.de>

## Ciggie Counter (Android)

- Android 13 or newer, no Google Play Services needed (runs fine on GrapheneOS).
- All data stays on the device. Optional: your own Nextcloud with the `cigarettecounter` app, which can also send voice announcements to Home Assistant.
- Permissions are only used when the matching feature is switched on: notifications (reminders), exact alarms (punctual reminders), calendar (daily summary), Bluetooth scan/connect without location (Butt Bin), internet (Nextcloud).

### Build

```sh
cd android-counter
./gradlew assembleDebug        # app/build/outputs/apk/debug/app-debug.apk
./gradlew assembleRelease      # signed only if android-counter/keystore.properties exists
```

Requires JDK 17+ (e.g. the one bundled with Android Studio) and the Android SDK.

### Translations

All texts are in `android-counter/app/src/main/res/values/strings.xml` (English) and `values-de/strings.xml` (German). A new language only needs a translated copy in `values-<code>/`.

## Butt Bin (firmware)

Prototype on a Telink TLSR825x (dev board TLSR8258DK48, target module Ebyte E104-BT12LSP with TLSR8253).

- Counts plunger presses, stores them with time in a flash ring buffer, works without a phone nearby.
- Advertises the current count; the app wakes up via a background Bluetooth scan and fetches new events within seconds.
- Low-power: deep sleep with RAM retention between events.

Building needs the [Telink TC BLE SDK](https://github.com/telink-semi/tc_ble_sdk) (V4.0.2.5) in `firmware/tc_ble_sdk/` and the TC32 toolchain, see `firmware/build_b85.sh` and `firmware/flash_b85.sh`. Short German notes on the chips and tools are in [`datasheets/`](datasheets/).

The firmware is derived from the SDK example `acl_peripheral_demo`; files taken from the SDK keep their Apache-2.0 headers.

A first schematic draft for the board (Ai-Thinker TB-03F module powered directly from a CR2450 coin cell, roughly 2–4 years per cell, plunger switch and red/green status LEDs that light a ring under a cast resin knob) is in [`hardware/kicad/buttbin_carrier/`](hardware/kicad/buttbin_carrier/) (KiCad 10, not yet laid out or built).

## Nextcloud app

Install by copying `nextcloud-app/cigarettecounter/` to your Nextcloud `apps/` (or `custom_apps/`) folder, run `composer install --no-dev` inside it and enable the app. The Android app talks to it with an app password (Settings → Security). It can announce reminders and every counted cigarette ("12. Zigarette gezählt") through a Home Assistant webhook; blueprints, sensors and a setup guide are in [`nextcloud-app/homeassistant/`](nextcloud-app/homeassistant/).

## License

- Project: [GNU GPL v3](LICENSE)
- Nextcloud app: [GNU AGPL v3](nextcloud-app/cigarettecounter/LICENSE)
- Files from the Telink SDK: Apache-2.0 (see file headers)

This is a hobby project. It is not a medical product and does not give health advice.
