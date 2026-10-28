<?php
/** @var array $_ */
?>
<div id="cigcounter-app">
    <button id="cigcounter-settings-toggle" class="cigcounter-settings-toggle" type="button" title="Einstellungen">⚙</button>

    <div class="cigcounter-count" id="cigcounter-count">–</div>
    <div class="cigcounter-label">heute</div>
    <div class="cigcounter-cost" id="cigcounter-cost"></div>

    <div class="cigcounter-periods">
        <div class="cigcounter-period">
            <div class="cigcounter-period-value" id="cigcounter-month-count">–</div>
            <div class="cigcounter-period-label">Monat</div>
        </div>
        <div class="cigcounter-period">
            <div class="cigcounter-period-value" id="cigcounter-year-count">–</div>
            <div class="cigcounter-period-label">Jahr</div>
        </div>
    </div>

    <button id="cigcounter-addbtn" class="cigcounter-addbtn" type="button">
        + Zigarette
    </button>

    <button id="cigcounter-backdate-toggle" class="cigcounter-backdate-toggle" type="button">🕐 nachträglich hinzufügen</button>

    <div class="cigcounter-backdate-form" id="cigcounter-backdate-form" hidden>
        <input type="datetime-local" id="cigcounter-backdate-input">
        <button id="cigcounter-backdate-confirm" class="cigcounter-addbtn cigcounter-settings-save" type="button">Eintragen</button>
    </div>

    <div class="cigcounter-next" id="cigcounter-next"></div>
    <div class="cigcounter-interval-info" id="cigcounter-interval-info"></div>

    <div class="cigcounter-settings" id="cigcounter-settings" hidden>
        <label>
            Kosten pro Zigarette (€)
            <input type="number" id="cigcounter-setting-cost" step="0.01" min="0" inputmode="decimal">
        </label>
        <label>
            Tageswechsel um (Uhr, 0–23)
            <input type="number" id="cigcounter-setting-day-start" step="1" min="0" max="23" inputmode="numeric">
        </label>
        <div class="cigcounter-push-status">z.B. 4 = Zigaretten bis 3:59 Uhr zählen noch zum Vortag.</div>

        <label>
            Kalender für die Tageszusammenfassung
            <select id="cigcounter-setting-calendar"></select>
        </label>
        <div class="cigcounter-push-status">Gilt ab dem nächsten abgeschlossenen Tag; bisherige Einträge bleiben im alten Kalender.</div>

        <hr class="cigcounter-settings-divider">

        <div class="cigcounter-interval-mode">
            <label class="cigcounter-radio-label">
                <input type="radio" name="cigcounter-interval-mode" id="cigcounter-mode-computed" value="computed">
                Intervall aus Tagesmenge berechnen
            </label>
            <label>
                Angestrebte Gesamtmenge pro Tag
                <input type="number" id="cigcounter-setting-target" step="1" min="1" inputmode="numeric">
            </label>
            <label>
                Wachzeit pro Tag (Stunden)
                <input type="number" id="cigcounter-setting-wake-hours" step="0.5" min="1" max="24" inputmode="decimal">
            </label>
            <div class="cigcounter-computed-interval" id="cigcounter-computed-interval"></div>

            <label class="cigcounter-radio-label">
                <input type="radio" name="cigcounter-interval-mode" id="cigcounter-mode-fixed" value="fixed">
                Festes Intervall vorgeben
            </label>
            <label>
                Minuten zwischen Zigaretten
                <input type="number" id="cigcounter-setting-fixed-interval" step="1" min="1" inputmode="numeric">
            </label>
        </div>

        <hr class="cigcounter-settings-divider">

        <label class="cigcounter-radio-label">
            <input type="checkbox" id="cigcounter-setting-next-allowed-enabled">
            "Nächste erlaubt"-Erinnerung aktiv
        </label>

        <label class="cigcounter-radio-label">
            <input type="checkbox" id="cigcounter-setting-countcheck-enabled">
            Erinnerung "Hast du alle gezählt?" aktiv
        </label>
        <label>
            Erinnerungsintervall (Minuten)
            <input type="number" id="cigcounter-setting-countcheck-interval" step="1" min="1" inputmode="numeric">
        </label>

        <hr class="cigcounter-settings-divider">

        <label>
            Home-Assistant-Webhook (Sprachansage beider Erinnerungen)
            <input type="url" id="cigcounter-setting-ha-webhook" placeholder="http://<HA-IP>:8123/api/webhook/…" autocomplete="off">
        </label>
        <button id="cigcounter-ha-test" class="cigcounter-addbtn cigcounter-settings-save" type="button">🔊 Ansage testen</button>
        <div class="cigcounter-push-status" id="cigcounter-ha-status"></div>

        <button id="cigcounter-settings-save" class="cigcounter-addbtn cigcounter-settings-save" type="button">Speichern</button>
        <button id="cigcounter-push-enable" class="cigcounter-addbtn cigcounter-settings-save" type="button">🔔 Push-Erinnerungen aktivieren</button>
        <div class="cigcounter-push-status" id="cigcounter-push-status"></div>

        <hr class="cigcounter-settings-divider">

        <button id="cigcounter-reset-btn" class="cigcounter-reset-btn" type="button">🗑 Alle Daten unwiderruflich löschen</button>
    </div>

    <div class="cigcounter-history" id="cigcounter-history"></div>
</div>
