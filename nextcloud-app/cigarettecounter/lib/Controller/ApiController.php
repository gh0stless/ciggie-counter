<?php

declare(strict_types=1);

namespace OCA\CigaretteCounter\Controller;

use OCA\CigaretteCounter\Service\CalendarSyncService;
use OCA\CigaretteCounter\Service\EntryService;
use OCA\CigaretteCounter\Service\HomeAssistantNotifier;
use OCA\CigaretteCounter\Service\PushSubscriptionService;
use OCP\AppFramework\Controller;
use OCP\AppFramework\Http\JSONResponse;
use OCP\IRequest;
use OCP\IUserSession;

class ApiController extends Controller {
    private EntryService $entryService;
    private PushSubscriptionService $pushService;
    private HomeAssistantNotifier $haNotifier;
    private CalendarSyncService $calendarSync;
    private string $userId;

    public function __construct(
        string $appName,
        IRequest $request,
        EntryService $entryService,
        PushSubscriptionService $pushService,
        HomeAssistantNotifier $haNotifier,
        CalendarSyncService $calendarSync,
        IUserSession $userSession
    ) {
        parent::__construct($appName, $request);
        $this->entryService = $entryService;
        $this->pushService = $pushService;
        $this->haNotifier = $haNotifier;
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
            'todayCost' => $costPerCigarette !== null ? round($todayCount * $costPerCigarette, 2) : null,
        ]);
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
        $this->announceCount($entries, $ts);

        return $this->today();
    }

    /**
     * "12. Zigarette gezählt" an Home Assistant. Kommt für Einträge aus Web-App und
     * Handy-App (die schickt jeden Eintrag hierher), auch wenn das Handy HA selbst
     * nicht erreicht (Gäste-WLAN, mobil). Nur für frische Einträge des heutigen
     * Zähltags - Nachträge und ein später nachgereichter Rückstau bleiben still.
     *
     * @param string[] $entries
     */
    private function announceCount(array $entries, string $ts): void {
        if (!$this->entryService->isCountAnnounceEnabled($this->userId)) {
            return;
        }
        $time = (new \DateTimeImmutable($ts))->getTimestamp();
        if ($time < time() - 10 * 60) {
            return;
        }
        $h = $this->entryService->getDayStartHour($this->userId);
        $tz = $this->entryService->getUserTimeZone($this->userId);
        $today = $this->entryService->currentLogicalDate($h, $tz);
        if ($this->entryService->logicalDate($ts, $h, $tz) !== $today) {
            return;
        }
        $number = count(array_filter($entries, fn (string $e) =>
            $this->entryService->logicalDate($e, $h, $tz) === $today
            && (new \DateTimeImmutable($e))->getTimestamp() <= $time));
        $this->haNotifier->notify($this->userId, $number . '. Zigarette gezählt.');
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
        $entries = array_values(array_filter($entries, fn (string $existing) => $existing !== $ts));
        $this->entryService->saveEntries($this->userId, $entries);

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
            'countAnnounceEnabled' => $this->entryService->isCountAnnounceEnabled($this->userId),
            'haWebhookUrl' => $this->haNotifier->getWebhookUrl($this->userId),
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
        ?string $haWebhookUrl = null,
        ?string $dayStartHour = null,
        ?string $calendarUri = null,
        ?string $countAnnounceEnabled = null
    ): JSONResponse {
        try {
            $this->haNotifier->setWebhookUrl($this->userId, $haWebhookUrl);
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
            $dayStartHour,
            $countAnnounceEnabled
        );
        return $this->settings();
    }

    /**
     * Schickt eine Test-Ansage an den gespeicherten Home-Assistant-Webhook.
     *
     * @NoAdminRequired
     */
    public function haTest(): JSONResponse {
        if ($this->haNotifier->getWebhookUrl($this->userId) === '') {
            return new JSONResponse(['ok' => false, 'error' => 'Keine Webhook-URL gespeichert.'], 400);
        }
        $ok = $this->haNotifier->notify($this->userId, 'Test vom Zigarettenzähler.');
        return new JSONResponse(
            ['ok' => $ok, 'error' => $ok ? null : $this->haNotifier->getLastError()],
            $ok ? 200 : 502
        );
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
