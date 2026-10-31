(function () {
    'use strict';

    var countEl = document.getElementById('cigcounter-count');
    var costEl = document.getElementById('cigcounter-cost');
    var monthEl = document.getElementById('cigcounter-month-count');
    var yearEl = document.getElementById('cigcounter-year-count');
    var nextEl = document.getElementById('cigcounter-next');
    var intervalInfoEl = document.getElementById('cigcounter-interval-info');
    var addBtn = document.getElementById('cigcounter-addbtn');
    var historyEl = document.getElementById('cigcounter-history');

    var settingsToggle = document.getElementById('cigcounter-settings-toggle');
    var settingsPanel = document.getElementById('cigcounter-settings');
    var settingsSave = document.getElementById('cigcounter-settings-save');
    var settingCostInput = document.getElementById('cigcounter-setting-cost');
    var settingTargetInput = document.getElementById('cigcounter-setting-target');
    var settingWakeHoursInput = document.getElementById('cigcounter-setting-wake-hours');
    var modeComputedRadio = document.getElementById('cigcounter-mode-computed');
    var modeFixedRadio = document.getElementById('cigcounter-mode-fixed');
    var settingFixedIntervalInput = document.getElementById('cigcounter-setting-fixed-interval');
    var computedIntervalEl = document.getElementById('cigcounter-computed-interval');
    var pushEnableBtn = document.getElementById('cigcounter-push-enable');
    var pushStatusEl = document.getElementById('cigcounter-push-status');
    var resetBtn = document.getElementById('cigcounter-reset-btn');
    var settingNextAllowedEnabledInput = document.getElementById('cigcounter-setting-next-allowed-enabled');
    var settingCountCheckEnabledInput = document.getElementById('cigcounter-setting-countcheck-enabled');
    var settingCountAnnounceInput = document.getElementById('cigcounter-setting-count-announce-enabled');
    var settingHaNextAllowedInput = document.getElementById('cigcounter-setting-ha-next-allowed-enabled');
    var settingHaCountCheckInput = document.getElementById('cigcounter-setting-ha-countcheck-enabled');
    var settingCountCheckIntervalInput = document.getElementById('cigcounter-setting-countcheck-interval');
    var settingHaWebhookInput = document.getElementById('cigcounter-setting-ha-webhook');
    var settingDayStartInput = document.getElementById('cigcounter-setting-day-start');
    var settingCalendarSelect = document.getElementById('cigcounter-setting-calendar');
    var haTestBtn = document.getElementById('cigcounter-ha-test');
    var haStatusEl = document.getElementById('cigcounter-ha-status');

    var backdateToggle = document.getElementById('cigcounter-backdate-toggle');
    var backdateForm = document.getElementById('cigcounter-backdate-form');
    var backdateInput = document.getElementById('cigcounter-backdate-input');
    var backdateConfirm = document.getElementById('cigcounter-backdate-confirm');

    var nextAlertTimer = null;
    var countCheckTimer = null;
    var nextAllowedReminderEnabled = true;
    var countCheckInitialized = false;
    var AUTO_REFRESH_MS = 5 * 60 * 1000;
    var STALE_AFTER_HIDDEN_MS = 60 * 1000;
    var hiddenSince = null;

    // Nextclouds CSRF-Token (OC.requestToken) wird bei lange offener Seite
    // nicht immer zuverlässig erneuert - ein Klick scheint dann "nichts zu
    // tun", weil der POST serverseitig abgelehnt wird. Statt dass man das
    // erst merken und manuell neu laden muss, laden wir automatisch neu:
    // beim Wiederöffnen nach einer Pause, alle 5 Minuten als Sicherheitsnetz,
    // und sofort, wenn ein Request tatsächlich fehlschlägt.
    function isPanelOpenForEditing() {
        return !settingsPanel.hidden || !backdateForm.hidden;
    }

    function forceReload() {
        window.location.reload();
    }

    function reloadIfStale() {
        if (document.visibilityState === 'visible' && !isPanelOpenForEditing()) {
            forceReload();
        }
    }

    function apiUrl(path) {
        return OC.generateUrl('/apps/cigarettecounter/api' + path);
    }

    function headers(extra) {
        var h = { 'requesttoken': OC.requestToken };
        if (extra) {
            for (var k in extra) { h[k] = extra[k]; }
        }
        return h;
    }

    function formatTime(iso) {
        var d = new Date(iso);
        var hh = String(d.getHours()).padStart(2, '0');
        var mm = String(d.getMinutes()).padStart(2, '0');
        return hh + ':' + mm;
    }

    function formatInterval(minutes) {
        var m = Math.round(minutes);
        if (m < 60) {
            return m + ' Min.';
        }
        var h = Math.floor(m / 60);
        var rest = m % 60;
        return h + 'h' + (rest ? ' ' + rest + 'min' : '');
    }

    // Ob ein Eintrag zum heutigen Zähltag gehört, entscheidet der Server
    // (Tageswechsel-Stunde) - hier nicht nachrechnen.
    function renderHistory(recent, recentToday) {
        var todaySet = {};
        (recentToday || []).forEach(function (ts) { todaySet[ts] = true; });
        historyEl.innerHTML = '';
        recent.forEach(function (ts) {
            var row = document.createElement('div');
            row.className = 'cigcounter-entry' + (todaySet[ts] ? '' : ' cigcounter-entry-old');

            var time = document.createElement('span');
            time.className = 'cigcounter-entry-time';
            time.textContent = formatTime(ts);
            row.appendChild(time);

            var del = document.createElement('button');
            del.className = 'cigcounter-entry-del';
            del.type = 'button';
            del.title = 'Eintrag löschen';
            del.textContent = '×';
            del.addEventListener('click', function () {
                removeEntry(ts);
            });
            row.appendChild(del);

            historyEl.appendChild(row);
        });
    }

    // Kurzer, generierter Signalton statt einer Audio-Datei (quick & dirty).
    function playBeep() {
        try {
            var Ctx = window.AudioContext || window.webkitAudioContext;
            var ctx = new Ctx();
            var osc = ctx.createOscillator();
            var gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.value = 880;
            gain.gain.setValueAtTime(0.2, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
            osc.start();
            osc.stop(ctx.currentTime + 0.6);
        } catch (e) {
            // Kein Audio verfügbar - nicht kritisch.
        }
    }

    function notifyAllowedAgain() {
        if (!nextAllowedReminderEnabled) {
            return;
        }
        playBeep();
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('Zigarettenzähler', {
                body: 'Du darfst jetzt wieder eine rauchen.',
                icon: OC.generateUrl('/apps/cigarettecounter/icon/192')
            });
        }
    }

    function scheduleCountCheck(enabled, intervalMinutes) {
        if (countCheckTimer) {
            clearTimeout(countCheckTimer);
            countCheckTimer = null;
        }
        if (!enabled) {
            return;
        }
        var ms = Math.max(intervalMinutes, 1) * 60 * 1000;
        countCheckTimer = setTimeout(function () {
            playBeep();
            if ('Notification' in window && Notification.permission === 'granted') {
                new Notification('Zigarettenzähler', {
                    body: 'Hast du alle Zigaretten gezählt?',
                    icon: OC.generateUrl('/apps/cigarettecounter/icon/192')
                });
            }
            scheduleCountCheck(enabled, intervalMinutes);
        }, ms);
    }

    function scheduleNextAlert(nextAllowedAt) {
        if (nextAlertTimer) {
            clearTimeout(nextAlertTimer);
            nextAlertTimer = null;
        }
        if (!nextAllowedAt) {
            nextEl.textContent = '';
            return;
        }

        var target = new Date(nextAllowedAt).getTime();
        var now = Date.now();
        var delay = target - now;

        nextEl.textContent = 'Nächste erlaubt: ' + formatTime(nextAllowedAt);

        if (delay <= 0) {
            return;
        }
        // setTimeout ist auf ca. 24 Tage begrenzt - für unseren Fall (max. Stunden) unkritisch.
        nextAlertTimer = setTimeout(function () {
            notifyAllowedAgain();
            nextEl.textContent = 'Du darfst jetzt wieder eine rauchen';
        }, delay);
    }

    function updateFromData(data) {
        countEl.textContent = data.todayCount;
        monthEl.textContent = data.monthCount;
        yearEl.textContent = data.yearCount;
        renderHistory(data.recent, data.recentToday);

        costEl.textContent = (data.todayCost !== null && data.todayCost !== undefined)
            ? data.todayCost.toFixed(2) + ' € heute'
            : '';

        if (data.intervalMinutes) {
            var label = data.intervalMode === 'fixed' ? 'Festes Intervall' : 'Errechnetes Intervall';
            intervalInfoEl.textContent = label + ': ' + formatInterval(data.intervalMinutes);
        } else {
            intervalInfoEl.textContent = '';
        }

        nextAllowedReminderEnabled = !!data.nextAllowedReminderEnabled;

        if (!countCheckInitialized) {
            countCheckInitialized = true;
            scheduleCountCheck(!!data.countCheckEnabled, data.countCheckIntervalMinutes);
        }

        scheduleNextAlert(data.nextAllowedAt);
    }

    function refresh() {
        fetch(apiUrl('/today'), { headers: headers() })
            .then(function (r) { return r.json(); })
            .then(updateFromData)
            .catch(function () {
                countEl.textContent = '?';
            });
    }

    function addEntry(timestamp) {
        addBtn.disabled = true;
        var params = new URLSearchParams();
        if (timestamp) {
            params.set('timestamp', timestamp);
        }

        fetch(apiUrl('/add'), {
            method: 'POST',
            headers: headers({ 'Content-Type': 'application/x-www-form-urlencoded' }),
            body: params.toString()
        })
            .then(function (r) {
                if (!r.ok) {
                    // Sehr wahrscheinlich ein abgelaufenes CSRF-Token nach
                    // langer offener Seite - neu laden behebt das zuverlässig.
                    forceReload();
                    return Promise.reject(new Error('request failed: ' + r.status));
                }
                return r.json();
            })
            .then(function (data) {
                updateFromData(data);
                // Lokale Zähl-Erinnerung ab dieser Eingabe neu starten (wie der Server-Job).
                scheduleCountCheck(!!data.countCheckEnabled, data.countCheckIntervalMinutes);
            })
            .catch(function () {
                // forceReload() wurde oben schon angestoßen, falls das die Ursache war.
            })
            .finally(function () {
                addBtn.disabled = false;
            });
    }

    function removeEntry(ts) {
        fetch(apiUrl('/entries/' + encodeURIComponent(ts)), {
            method: 'DELETE',
            headers: headers()
        })
            .then(function (r) { return r.json(); })
            .then(updateFromData);
    }

    function loadSettingsIntoForm() {
        fetch(apiUrl('/settings'), { headers: headers() })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                settingCostInput.value = data.costPerCigarette !== null ? data.costPerCigarette : '';
                settingTargetInput.value = data.dailyTarget !== null ? data.dailyTarget : '';
                settingFixedIntervalInput.value = data.fixedIntervalMinutes !== null ? data.fixedIntervalMinutes : '';
                settingWakeHoursInput.value = data.wakeHours;
                settingNextAllowedEnabledInput.checked = !!data.nextAllowedReminderEnabled;
                settingCountCheckEnabledInput.checked = !!data.countCheckEnabled;
                settingCountCheckIntervalInput.value = data.countCheckIntervalMinutes;
                settingCountAnnounceInput.checked = !!data.countAnnounceEnabled;
                settingHaNextAllowedInput.checked = !!data.haNextAllowedEnabled;
                settingHaCountCheckInput.checked = !!data.haCountCheckEnabled;
                settingHaWebhookInput.value = data.haWebhookUrl || '';
                settingDayStartInput.value = data.dayStartHour;
                settingCalendarSelect.innerHTML = '';
                (data.calendars || []).forEach(function (c) {
                    var opt = document.createElement('option');
                    opt.value = c.uri;
                    opt.textContent = c.name;
                    settingCalendarSelect.appendChild(opt);
                });
                settingCalendarSelect.value = data.calendarUri;
                haStatusEl.textContent = '';
                computedIntervalEl.textContent = data.intervalMinutes
                    ? '→ aktuell errechnet: ' + formatInterval(data.intervalMinutes)
                    : '→ noch kein Wert (Ziel eintragen und speichern)';
                if (data.intervalMode === 'fixed') {
                    modeFixedRadio.checked = true;
                } else {
                    modeComputedRadio.checked = true;
                }
            });
    }

    function saveSettings() {
        var mode = modeFixedRadio.checked ? 'fixed' : 'computed';
        var params = new URLSearchParams();
        params.set('costPerCigarette', settingCostInput.value);
        params.set('dailyTarget', settingTargetInput.value);
        params.set('intervalMode', mode);
        params.set('fixedIntervalMinutes', settingFixedIntervalInput.value);
        params.set('wakeHours', settingWakeHoursInput.value);
        params.set('nextAllowedReminderEnabled', settingNextAllowedEnabledInput.checked ? '1' : '0');
        params.set('countCheckEnabled', settingCountCheckEnabledInput.checked ? '1' : '0');
        params.set('countCheckIntervalMinutes', settingCountCheckIntervalInput.value);
        params.set('countAnnounceEnabled', settingCountAnnounceInput.checked ? '1' : '0');
        params.set('haNextAllowedEnabled', settingHaNextAllowedInput.checked ? '1' : '0');
        params.set('haCountCheckEnabled', settingHaCountCheckInput.checked ? '1' : '0');
        params.set('haWebhookUrl', settingHaWebhookInput.value);
        params.set('dayStartHour', settingDayStartInput.value);
        // Nur mitschicken, wenn die Liste geladen ist - sonst würde ein leerer Wert
        // die Auswahl auf den Standard zurücksetzen.
        if (settingCalendarSelect.options.length > 0) {
            params.set('calendarUri', settingCalendarSelect.value);
        }

        return fetch(apiUrl('/settings'), {
            method: 'POST',
            headers: headers({ 'Content-Type': 'application/x-www-form-urlencoded' }),
            body: params.toString()
        })
            .then(function (r) {
                return r.json().then(function (data) {
                    if (!r.ok) {
                        throw new Error(data.error || ('Speichern fehlgeschlagen (HTTP ' + r.status + ')'));
                    }
                    return data;
                });
            })
            .then(function () {
                scheduleCountCheck(settingCountCheckEnabledInput.checked, parseInt(settingCountCheckIntervalInput.value, 10) || 10);
                refresh();
            });
    }

    function testHomeAssistant() {
        haStatusEl.textContent = 'Speichere und sende Test-Ansage …';
        haTestBtn.disabled = true;
        // Erst speichern, damit genau die eingetragene URL getestet wird.
        saveSettings()
            .then(function () {
                return fetch(apiUrl('/ha-test'), { method: 'POST', headers: headers() });
            })
            .then(function (r) {
                return r.json().then(function (data) {
                    haStatusEl.textContent = data.ok
                        ? 'Ansage verschickt – kam sie aus dem Lautsprecher?'
                        : 'Fehlgeschlagen: ' + (data.error || ('HTTP ' + r.status));
                });
            })
            .catch(function (err) {
                haStatusEl.textContent = 'Fehlgeschlagen: ' + err.message;
            })
            .finally(function () {
                haTestBtn.disabled = false;
            });
    }

    // Base64url (wie von PushManager.subscribe erwartet) -> Uint8Array.
    function urlBase64ToUint8Array(base64String) {
        var padding = '='.repeat((4 - base64String.length % 4) % 4);
        var base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
        var rawData = window.atob(base64);
        var outputArray = new Uint8Array(rawData.length);
        for (var i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    function enablePush() {
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
            pushStatusEl.textContent = 'Push wird von diesem Browser nicht unterstützt.';
            return;
        }

        pushStatusEl.textContent = 'Aktiviere …';

        Notification.requestPermission().then(function (permission) {
            if (permission !== 'granted') {
                pushStatusEl.textContent = 'Benachrichtigungen wurden nicht erlaubt.';
                return;
            }

            var step = 'Service Worker';
            navigator.serviceWorker.ready
                .then(function (registration) {
                    // Vorhandenes Abo wiederverwenden: ein zweiter Klick soll nicht
                    // erneut beim Push-Dienst des Browsers anfragen müssen.
                    step = 'vorhandenes Abo prüfen';
                    return registration.pushManager.getSubscription().then(function (existing) {
                        if (existing) {
                            return existing;
                        }
                        step = 'Schlüssel vom Server holen';
                        return fetch(apiUrl('/vapid-public-key'), { headers: headers() })
                            .then(function (r) { return r.json(); })
                            .then(function (data) {
                                step = 'beim Push-Dienst des Browsers anmelden';
                                return registration.pushManager.subscribe({
                                    userVisibleOnly: true,
                                    applicationServerKey: urlBase64ToUint8Array(data.publicKey)
                                });
                            });
                    });
                })
                .then(function (subscription) {
                    step = 'Abo auf dem Server speichern';
                    return fetch(apiUrl('/push-subscribe'), {
                        method: 'POST',
                        headers: headers({ 'Content-Type': 'application/json' }),
                        body: JSON.stringify(subscription.toJSON())
                    });
                })
                .then(function (r) {
                    if (!r.ok) {
                        throw new Error('HTTP ' + r.status);
                    }
                    pushStatusEl.textContent = 'Push-Erinnerungen sind aktiv.';
                })
                .catch(function (err) {
                    pushStatusEl.textContent = 'Aktivierung fehlgeschlagen (' + step + '): ' + err.message;
                });
        });
    }

    function resetAll() {
        var sure = window.confirm(
            'Wirklich ALLE gespeicherten Zigaretten-Einträge unwiderruflich löschen?\n\n' +
            'Das kann nicht rückgängig gemacht werden.'
        );
        if (!sure) {
            return;
        }
        var reallySure = window.confirm('Letzte Sicherheitsabfrage: Wirklich alles löschen?');
        if (!reallySure) {
            return;
        }

        resetBtn.disabled = true;
        fetch(apiUrl('/reset'), {
            method: 'POST',
            headers: headers()
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                updateFromData(data);
                settingsPanel.hidden = true;
            })
            .finally(function () {
                resetBtn.disabled = false;
            });
    }

    function toLocalDatetimeValue(date) {
        var pad = function (n) { return String(n).padStart(2, '0'); };
        return date.getFullYear() + '-' + pad(date.getMonth() + 1) + '-' + pad(date.getDate()) +
            'T' + pad(date.getHours()) + ':' + pad(date.getMinutes());
    }

    backdateToggle.addEventListener('click', function () {
        backdateForm.hidden = !backdateForm.hidden;
        if (!backdateForm.hidden) {
            backdateInput.value = toLocalDatetimeValue(new Date());
        }
    });

    backdateConfirm.addEventListener('click', function () {
        if (!backdateInput.value) {
            return;
        }
        addEntry(backdateInput.value);
        backdateForm.hidden = true;
    });

    settingsToggle.addEventListener('click', function () {
        var willShow = settingsPanel.hidden;
        settingsPanel.hidden = !willShow;
        if (willShow) {
            loadSettingsIntoForm();
        }
    });

    settingsSave.addEventListener('click', function () {
        saveSettings()
            .then(function () {
                settingsPanel.hidden = true;
            })
            .catch(function (err) {
                haStatusEl.textContent = err.message;
            });
    });
    haTestBtn.addEventListener('click', testHomeAssistant);
    pushEnableBtn.addEventListener('click', enablePush);
    resetBtn.addEventListener('click', resetAll);
    addBtn.addEventListener('click', function () { addEntry(); });

    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }

    document.addEventListener('visibilitychange', function () {
        if (document.visibilityState === 'hidden') {
            hiddenSince = Date.now();
            return;
        }
        // 'visible': Seite/PWA wurde (wieder-)geöffnet. Nach einer kurzen
        // Pause (z.B. kurz zum Sperrbildschirm und zurück) nicht neu laden -
        // erst wenn die Seite eine Weile im Hintergrund war.
        if (hiddenSince !== null && (Date.now() - hiddenSince) >= STALE_AFTER_HIDDEN_MS) {
            reloadIfStale();
        }
        hiddenSince = null;
    });

    setInterval(reloadIfStale, AUTO_REFRESH_MS);

    refresh();

    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register(OC.generateUrl('/apps/cigarettecounter/sw.js'), {
            scope: OC.generateUrl('/apps/cigarettecounter/')
        }).catch(function () {
            // PWA-Installierbarkeit ist ein Bonus, kein Blocker.
        });
    }
})();
