<?php

declare(strict_types=1);

namespace OCA\CigaretteCounter\Controller;

use OCA\CigaretteCounter\Service\CalendarSyncService;
use OCA\CigaretteCounter\Service\EntryService;
use OCA\CigaretteCounter\Service\PushSubscriptionService;
use OCP\AppFramework\Controller;
use OCP\AppFramework\Http\JSONResponse;
use OCP\IRequest;
use OCP\IUserSession;

class ApiController extends Controller {
    private EntryService $entryService;
    private PushSubscriptionService $pushService;
    private CalendarSyncService $calendarSync;
    private string $userId;

    public function __construct(
        string $appName,
        IRequest $request,
        EntryService $entryService,
        PushSubscriptionService $pushService,
        CalendarSyncService $calendarSync,
        IUserSession $userSession
    ) {
        parent::__construct($appName, $request);
        $this->entryService = $entryService;
        $this->pushService = $pushService;
        $this->calendarSync = $calendarSync;
        $this->userId = $userSession->getUser()->getUID();
    }

    /**
     * @NoAdminRequired
     */
    public function today(): JSONResponse {
        $entries = $this->entryService->loadEntries($this->userId);
        $h = $this->entryService->getDayStartHour($this->userId);
        $tz = $this->entryService->getUserTimeZone($this->userId);
        $todayPrefix = $this->entryService->currentLogicalDate($h, $tz);
        $yesterdayPrefix = $this->entryService->currentLogicalDate($h, $tz, -1);
        $todayCount = $this->entryService->countForPrefix($entries, $todayPrefix, $h, $tz);
        $monthCount = $this->entryService->countForPrefix($entries, substr($todayPrefix, 0, 7), $h, $tz);
        $yearCount = $this->entryService->countForPrefix($entries, substr($todayPrefix, 0, 4), $h, $tz);

        // Verlaufsanzeige: nur heute + gestern, neueste zuerst - ältere Tage
        // stehen ohnehin schon im Kalender (Tages-Zusammenfassung).
        // Tag nach logischem Datum (Tageswechsel-Stunde), nicht nach Kalenderdatum.
        $recent = [];
        $recentToday = [];
        foreach (array_reverse($entries) as $ts) {
            $d = $this->entryService->logicalDate($ts, $h, $tz);
            if ($d === $todayPrefix) {
                $recent[] = $ts;
                $recentToday[] = $ts;
            } elseif ($d === $yesterdayPrefix) {
                $recent[] = $ts;
            }
        }

        $costPerCigarette = $this->entryService->getCostPerCigarette($this->userId);

        return new JSONResponse([
            'todayCount' => $todayCount,
            'monthCount' => $monthCount,
            'yearCount' => $yearCount,
            'recent' => $recent,
            // Welche der recent-Einträge zum (logischen) heutigen Tag gehören -
            // das Frontend rechnet den Tageswechsel so nicht selbst nach.
            'recentToday' => $recentToday,
            'dayStartHour' => $h,
            'costPerCigarette' => $costPerCigarette,
            'dailyTarget' => $this->entryService->getDailyTarget($this->userId),
            'intervalMode' => $this->entryService->getIntervalMode($this->userId),
            'fixedIntervalMinutes' => $this->entryService->getFixedIntervalMinutes($this->userId),
            'wakeHours' => $this->entryService->getWakeHours($this->userId),
            'intervalMinutes' => $this->entryService->getIntervalMinutes($this->userId),
            'nextAllowedAt' => $this->entryService->getNextAllowedAt($this->userId, $entries),
            'countCheckEnabled' => $this->entryService->isCountCheckEnabled($this->userId),
            'countCheckIntervalMinutes' => $this->entryService->getCountCheckIntervalMinutes($this->userId),
            'nextAllowedReminderEnabled' => $this->entryService->isNextAllowedReminderEnabled($this->userId),
            'muted' => $this->entryService->isMuted($this->userId),
            // Butt Bin: kompletter Gerätestatus (siehe ashtray()), Batterie zusätzlich direkt
            'ashtray' => $ashtray = $this->entryService->getAshtrayState($this->userId),
            'ashtrayBattery' => $ashtray['battery'],
            'todayCost' => $costPerCigarette !== null ? round($todayCount * $costPerCigarette, 2) : null,
        ]);
    }

    /**
     * Stumm-Schalter, gedacht für Home Assistant (REST-Switch: GET = Zustand, POST = setzen)
     * und die Handy-App. Antwort immer {"muted": bool}.
     *
     * @NoAdminRequired
     */
    public function mute(): JSONResponse {
        return new JSONResponse(['muted' => $this->entryService->isMuted($this->userId)]);
    }

    /**
     * @param string|null $muted "1"/"true"/"on" = stumm, alles andere = wieder an
     *
     * @NoAdminRequired
     */
    public function setMute(?string $muted = null): JSONResponse {
        $this->entryService->setMuted($this->userId, in_array(strtolower((string)$muted), ['1', 'true', 'on'], true));
        return $this->mute();
    }

    /**
     * Gerätestatus des Butt Bin (Batterie, Firmware, spätere Sensoren). Felder siehe
     * EntryService::ASHTRAY_FIELDS, unbekannte Werte sind null.
     *
     * @NoAdminRequired
     */
    public function ashtray(): JSONResponse {
        return new JSONResponse($this->entryService->getAshtrayState($this->userId));
    }

    /**
     * Teil-Update durch die Handy-App: nur mitgeschickte, bekannte Felder werden übernommen.
     * Optional "at" = Zeitpunkt der Messung (ISO), sonst jetzt.
     *
     * @NoAdminRequired
     */
    public function updateAshtray(): JSONResponse {
        $params = $this->request->getParams();
        try {
            $time = (new \DateTimeImmutable($params['at'] ?? 'now'))->format('c');
        } catch (\Exception $e) {
            $time = date('c');
        }
        return new JSONResponse($this->entryService->updateAshtrayState($this->userId, $params, $time));
    }

    /**
     * Abgleich v2, Abholen: Datensätze (id, ts, source, deleted, rev) mit rev > since.
     * Antwort {"rev": aktueller Stand, "entries": [...]}; "rev" beim nächsten Mal als since schicken.
     *
     * @NoAdminRequired
     */
    public function entriesV2(int $since = 0): JSONResponse {
        return new JSONResponse($this->entryService->recordsSince($this->userId, max(0, $since)));
    }

    /**
     * Abgleich v2, Senden: JSON {"entries": [{"id", "ts", "source", "deleted"}, ...]}.
     * Neue, frische Einträge wirken wie /api/add (Zähl-Erinnerung neu, Ansage).
     *
     * @NoAdminRequired
     */
    public function pushEntriesV2(): JSONResponse {
        $incoming = $this->request->getParam('entries');
        if (!is_array($incoming)) {
            return new JSONResponse(['error' => 'entries fehlt'], 400);
        }
        $result = $this->entryService->mergeRecords($this->userId, $incoming);
        if ($result['added'] !== []) {
            $newest = max(array_map(fn (string $ts) => (new \DateTimeImmutable($ts))->getTimestamp(), $result['added']));
            if ($newest >= time() - 10 * 60) {
                $this->entryService->setLastCountCheckAt($this->userId, (new \DateTime())->format('c'));
            }
        }
        return new JSONResponse(['rev' => $result['rev'], 'accepted' => $result['accepted']]);
    }

    /**
     * Abgleich der Regeln (Kosten, Tageswechsel, Pausen, Takt der Zähl-Erinnerung) zwischen
     * Geräten. Wie gemeldet wird (Push, HA, Handy), bleibt pro Gerät und gehört nicht dazu.
     * Antwort mit "updatedAt" (Unix-Sekunden, 0 = nie geändert); es gilt die jüngste Änderung.
     *
     * @NoAdminRequired
     */
    public function rulesV2(): JSONResponse {
        return new JSONResponse($this->entryService->getRules($this->userId));
    }

    /**
     * JSON wie bei GET plus "updatedAt" des Absenders. Ältere Stände als der des Servers werden
     * nicht übernommen; die Antwort ist immer der gültige Stand.
     *
     * @NoAdminRequired
     */
    public function pushRulesV2(): JSONResponse {
        $rules = $this->request->getParams();
        if (!isset($rules['updatedAt']) || !is_numeric($rules['updatedAt'])) {
            return new JSONResponse(['error' => 'updatedAt fehlt'], 400);
        }
        $this->entryService->mergeRules($this->userId, $rules);
        return new JSONResponse($this->entryService->getRules($this->userId));
    }

    /**
     * @NoAdminRequired
     */
    public function resetAll(): JSONResponse {
        $this->entryService->resetAll($this->userId);
        return $this->today();
    }

    /**
     * @param string|null $timestamp optionaler ISO-Zeitstempel, um nachträglich
     * (rückwirkend) einen Eintrag anzulegen statt "jetzt". Ungültige oder
     * zukünftige Werte werden ignoriert - dann zählt der aktuelle Zeitpunkt.
     *
     * @NoAdminRequired
     */
    public function add(?string $timestamp = null): JSONResponse {
        $entries = $this->entryService->loadEntries($this->userId);
        $ts = $this->resolveTimestamp($timestamp);
        $entries[] = $ts;
        $this->entryService->saveEntries($this->userId, $entries);
        // Wer gerade zählt, braucht keine "Hast du alle gezählt?"-Erinnerung:
        // das Erinnerungsintervall läuft ab jetzt neu.
        $this->entryService->setLastCountCheckAt($this->userId, (new \DateTime())->format('c'));

        return $this->today();
    }

    private function resolveTimestamp(?string $timestamp): string {
        if ($timestamp !== null && $timestamp !== '') {
            try {
                // Das datetime-local-Feld liefert eine Uhrzeit ohne Zeitzone ("2026-10-18T01:30").
                // Als Ortszeit des Nutzers lesen - PHP im Container läuft in UTC.
                $dt = new \DateTime($timestamp, $this->entryService->getUserTimeZone($this->userId));
                if ($dt->getTimestamp() <= time() + 60) {
                    return $dt->format('c');
                }
            } catch (\Exception $e) {
                // ungültiges Format - fällt auf "jetzt" zurück
            }
        }
        return date('c');
    }

    /**
     * Alle Einträge (ISO-8601 mit Offset, chronologisch), für die Handy-App auf mehreren Geräten.
     *
     * @NoAdminRequired
     */
    public function entries(): JSONResponse {
        return new JSONResponse(['entries' => $this->entryService->loadEntries($this->userId)]);
    }

    /**
     * @NoAdminRequired
     */
    public function remove(string $ts): JSONResponse {
        $entries = $this->entryService->loadEntries($this->userId);
        // Nur einen Eintrag entfernen: mehrere Zigaretten in derselben Sekunde sind möglich
        $pos = array_search($ts, $entries, true);
        if ($pos !== false) {
            array_splice($entries, $pos, 1);
            $this->entryService->saveEntries($this->userId, $entries);
        }

        return $this->today();
    }

    /**
     * @NoAdminRequired
     */
    public function settings(): JSONResponse {
        return new JSONResponse([
            'costPerCigarette' => $this->entryService->getCostPerCigarette($this->userId),
            'dailyTarget' => $this->entryService->getDailyTarget($this->userId),
            'intervalMode' => $this->entryService->getIntervalMode($this->userId),
            'fixedIntervalMinutes' => $this->entryService->getFixedIntervalMinutes($this->userId),
            'wakeHours' => $this->entryService->getWakeHours($this->userId),
            'intervalMinutes' => $this->entryService->getIntervalMinutes($this->userId),
            'countCheckEnabled' => $this->entryService->isCountCheckEnabled($this->userId),
            'countCheckIntervalMinutes' => $this->entryService->getCountCheckIntervalMinutes($this->userId),
            'nextAllowedReminderEnabled' => $this->entryService->isNextAllowedReminderEnabled($this->userId),
            'dayStartHour' => $this->entryService->getDayStartHour($this->userId),
            'calendarUri' => $this->calendarSync->getCalendarUri($this->userId),
            'calendars' => $this->calendarOptions(),
        ]);
    }

    /**
     * Auswahlliste für den Zielkalender: eigener "Zigarettenzähler"-Kalender
     * (auch wenn er noch nicht existiert), die übrigen eigenen Kalender, "keiner".
     *
     * @return array<int, array{uri: string, name: string}>
     */
    private function calendarOptions(): array {
        $options = [['uri' => CalendarSyncService::DEFAULT_CALENDAR_URI, 'name' => 'Zigarettenzähler (eigener Kalender, Standard)']];
        foreach ($this->calendarSync->listOwnCalendars($this->userId) as $uri => $name) {
            if ($uri !== CalendarSyncService::DEFAULT_CALENDAR_URI) {
                $options[] = ['uri' => $uri, 'name' => $name];
            }
        }
        $options[] = ['uri' => CalendarSyncService::NO_CALENDAR, 'name' => 'Kein Kalender (Tageszusammenfassung aus)'];
        return $options;
    }

    /**
     * @NoAdminRequired
     */
    public function updateSettings(
        ?string $costPerCigarette = null,
        ?string $dailyTarget = null,
        ?string $intervalMode = null,
        ?string $fixedIntervalMinutes = null,
        ?string $wakeHours = null,
        ?string $countCheckEnabled = null,
        ?string $countCheckIntervalMinutes = null,
        ?string $nextAllowedReminderEnabled = null,
        ?string $dayStartHour = null,
        ?string $calendarUri = null
    ): JSONResponse {
        try {
            if ($calendarUri !== null) {
                $this->calendarSync->setCalendarUri($this->userId, $calendarUri);
            }
        } catch (\InvalidArgumentException $e) {
            return new JSONResponse(['error' => $e->getMessage()], 400);
        }

        $this->entryService->setSettings(
            $this->userId,
            $costPerCigarette,
            $dailyTarget,
            $intervalMode,
            $fixedIntervalMinutes,
            $wakeHours,
            $countCheckEnabled,
            $countCheckIntervalMinutes,
            $nextAllowedReminderEnabled,
            $dayStartHour
        );
        return $this->settings();
    }

    /**
     * @NoAdminRequired
     * @NoCSRFRequired
     */
    public function vapidPublicKey(): JSONResponse {
        return new JSONResponse(['publicKey' => $this->pushService->getVapidPublicKey()]);
    }

    /**
     * @NoAdminRequired
     */
    public function pushSubscribe(?string $endpoint = null, ?array $keys = null): JSONResponse {
        if ($endpoint === null || $keys === null || !isset($keys['p256dh'], $keys['auth'])) {
            return new JSONResponse(['error' => 'invalid subscription'], 400);
        }

        $this->pushService->addSubscription($this->userId, [
            'endpoint' => $endpoint,
            'keys' => [
                'p256dh' => $keys['p256dh'],
                'auth' => $keys['auth'],
            ],
        ]);

        return new JSONResponse(['ok' => true]);
    }
}
