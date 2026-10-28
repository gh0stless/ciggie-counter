<?php

declare(strict_types=1);

namespace OCA\CigaretteCounter\Service;

use OCP\Files\IAppData;
use OCP\Files\NotFoundException;
use OCP\Files\SimpleFS\ISimpleFile;
use OCP\IConfig;

/**
 * Zentrale Ablage für Zigaretten-Einträge (ein JSON-Array pro Nutzer in
 * IAppData) und die Zeitplanungs-Einstellungen (Kosten/Ziel), bewusst ohne
 * SQL-Migration. Wird von ApiController und den Hintergrund-Jobs
 * (Kalender-Sync, Push-Erinnerung) gemeinsam genutzt.
 */
class EntryService {
    private const DEFAULT_WAKE_HOURS = 18.0;
    private const ENTRIES_FOLDER = 'entries';
    private const NOTIFY_STATE_FOLDER = 'notify-state';

    private IAppData $appData;
    private IConfig $config;

    public function __construct(IAppData $appData, IConfig $config) {
        $this->appData = $appData;
        $this->config = $config;
    }

    /**
     * @return string[] alle Nutzer-IDs, die mindestens eine Entries-Datei haben
     */
    public function listUserIdsWithEntries(): array {
        try {
            $folder = $this->appData->getFolder(self::ENTRIES_FOLDER);
        } catch (NotFoundException $e) {
            return [];
        }

        $uids = [];
        foreach ($folder->getDirectoryListing() as $file) {
            $name = $file->getName();
            if (str_starts_with($name, 'entries-') && str_ends_with($name, '.json')) {
                $uids[] = substr($name, strlen('entries-'), -strlen('.json'));
            }
        }
        return $uids;
    }

    /**
     * @return string[] ISO8601-Zeitstempel, älteste zuerst
     */
    public function loadEntries(string $uid): array {
        $fileName = 'entries-' . $uid . '.json';
        try {
            $folder = $this->appData->getFolder(self::ENTRIES_FOLDER);
        } catch (NotFoundException $e) {
            $folder = $this->appData->newFolder(self::ENTRIES_FOLDER);
        }

        try {
            /** @var ISimpleFile $file */
            $file = $folder->getFile($fileName);
            $data = json_decode($file->getContent(), true);
            return is_array($data) ? $data : [];
        } catch (NotFoundException $e) {
            return [];
        }
    }

    /**
     * @param string[] $entries
     */
    public function saveEntries(string $uid, array $entries): void {
        $fileName = 'entries-' . $uid . '.json';
        try {
            $folder = $this->appData->getFolder(self::ENTRIES_FOLDER);
        } catch (NotFoundException $e) {
            $folder = $this->appData->newFolder(self::ENTRIES_FOLDER);
        }

        // Nach echtem Unix-Timestamp sortieren, nicht als String - reiner
        // String-Vergleich liefert an Tagen mit Zeitumstellung (unterschiedliche
        // UTC-Offsets innerhalb desselben Tages) die falsche Reihenfolge.
        usort($entries, fn (string $a, string $b) => (new \DateTime($a))->getTimestamp() <=> (new \DateTime($b))->getTimestamp());

        try {
            $file = $folder->getFile($fileName);
        } catch (NotFoundException $e) {
            $file = $folder->newFile($fileName);
        }
        $file->putContent(json_encode(array_values($entries)));
    }

    /**
     * Stunde, zu der ein neuer "Zähltag" beginnt (0 = Mitternacht). Bei z.B. 4
     * zählt eine Zigarette um 1:30 noch zum Vortag.
     */
    public function getDayStartHour(string $uid): int {
        $h = (int)$this->config->getUserValue($uid, 'cigarettecounter', 'day_start_hour', '0');
        return ($h >= 0 && $h <= 23) ? $h : 0;
    }

    /**
     * Zeitzone des Nutzers: persönliche Nextcloud-Einstellung, sonst Server-Vorgabe
     * (default_timezone), sonst Europe/Berlin. Wichtig: PHP im Nextcloud-Container
     * läuft in UTC - ohne diese Umrechnung kippte der Zähltag 2 h zu spät (Sommerzeit).
     */
    public function getUserTimeZone(string $uid): \DateTimeZone {
        $candidates = [
            $this->config->getUserValue($uid, 'core', 'timezone', ''),
            (string)$this->config->getSystemValue('default_timezone', ''),
            'Europe/Berlin',
        ];
        foreach ($candidates as $name) {
            if ($name === '') {
                continue;
            }
            try {
                return new \DateTimeZone($name);
            } catch (\Exception $e) {
                // ungültiger Name - nächsten Kandidaten versuchen
            }
        }
        return new \DateTimeZone('UTC');
    }

    /**
     * Logisches Datum (Y-m-d) eines lokalen Zeitpunkts: liegt die lokale Uhrzeit vor
     * der Tageswechsel-Stunde, gehört er zum Vortag. Rechnet mit der Uhrzeit statt mit
     * Stunden-Subtraktion, damit auch Tage mit Zeitumstellung eindeutig sind.
     */
    private function logicalDateOf(\DateTimeImmutable $local, int $dayStartHour): \DateTimeImmutable {
        $day = $local->setTime(0, 0);
        return ((int)$local->format('G') < $dayStartHour) ? $day->modify('-1 day') : $day;
    }

    /**
     * Logisches Datum (Y-m-d) eines gespeicherten Zeitstempels in der Zeitzone des Nutzers.
     */
    public function logicalDate(string $ts, int $dayStartHour, \DateTimeZone $tz): string {
        $local = (new \DateTimeImmutable($ts))->setTimezone($tz);
        return $this->logicalDateOf($local, $dayStartHour)->format('Y-m-d');
    }

    /**
     * Heutiges logisches Datum, optional um $daysOffset Tage verschoben (-1 = gestern).
     */
    public function currentLogicalDate(int $dayStartHour, \DateTimeZone $tz, int $daysOffset = 0): string {
        $d = $this->logicalDateOf(new \DateTimeImmutable('now', $tz), $dayStartHour);
        if ($daysOffset !== 0) {
            $d = $d->modify(($daysOffset > 0 ? '+' : '') . $daysOffset . ' days');
        }
        return $d->format('Y-m-d');
    }

    /**
     * @param string[] $entries
     */
    public function countForDay(array $entries, string $dayPrefix, int $dayStartHour, \DateTimeZone $tz): int {
        return $this->countForPrefix($entries, $dayPrefix, $dayStartHour, $tz);
    }

    /**
     * Zählt Einträge, deren logisches Datum mit $prefix beginnt
     * ('2026-10-17' = Tag, '2026-10' = Monat, '2026' = Jahr).
     *
     * @param string[] $entries
     */
    public function countForPrefix(array $entries, string $prefix, int $dayStartHour, \DateTimeZone $tz): int {
        return count(array_filter($entries, function (string $ts) use ($prefix, $dayStartHour, $tz) {
            return str_starts_with($this->logicalDate($ts, $dayStartHour, $tz), $prefix);
        }));
    }

    public function resetAll(string $uid): void {
        $this->saveEntries($uid, []);
    }

    public function getCostPerCigarette(string $uid): ?float {
        $raw = $this->config->getUserValue($uid, 'cigarettecounter', 'cost_per_cigarette', '');
        return $raw === '' ? null : (float)$raw;
    }

    public function getDailyTarget(string $uid): ?int {
        $raw = $this->config->getUserValue($uid, 'cigarettecounter', 'daily_target', '');
        return $raw === '' ? null : (int)$raw;
    }

    /**
     * 'computed' (aus Tagesmenge / Wachzeit-Fenster) oder 'fixed' (fest vorgegebene Minutenzahl).
     */
    public function getIntervalMode(string $uid): string {
        $raw = $this->config->getUserValue($uid, 'cigarettecounter', 'interval_mode', 'computed');
        return $raw === 'fixed' ? 'fixed' : 'computed';
    }

    public function getFixedIntervalMinutes(string $uid): ?int {
        $raw = $this->config->getUserValue($uid, 'cigarettecounter', 'fixed_interval_minutes', '');
        return $raw === '' ? null : (int)$raw;
    }

    public function getWakeHours(string $uid): float {
        $raw = $this->config->getUserValue($uid, 'cigarettecounter', 'wake_hours', '');
        return $raw === '' ? self::DEFAULT_WAKE_HOURS : (float)$raw;
    }

    public function setSettings(
        string $uid,
        ?string $costPerCigarette,
        ?string $dailyTarget,
        ?string $intervalMode = null,
        ?string $fixedIntervalMinutes = null,
        ?string $wakeHours = null,
        ?string $countCheckEnabled = null,
        ?string $countCheckIntervalMinutes = null,
        ?string $nextAllowedReminderEnabled = null,
        ?string $dayStartHour = null
    ): void {
        if ($dayStartHour !== null && $dayStartHour !== '' && (int)$dayStartHour >= 0 && (int)$dayStartHour <= 23) {
            $this->config->setUserValue($uid, 'cigarettecounter', 'day_start_hour', (string)(int)$dayStartHour);
        } else {
            $this->config->deleteUserValue($uid, 'cigarettecounter', 'day_start_hour');
        }

        if ($costPerCigarette !== null && $costPerCigarette !== '') {
            $this->config->setUserValue($uid, 'cigarettecounter', 'cost_per_cigarette', (string)(float)$costPerCigarette);
        } else {
            $this->config->deleteUserValue($uid, 'cigarettecounter', 'cost_per_cigarette');
        }

        if ($dailyTarget !== null && $dailyTarget !== '') {
            $this->config->setUserValue($uid, 'cigarettecounter', 'daily_target', (string)(int)$dailyTarget);
        } else {
            $this->config->deleteUserValue($uid, 'cigarettecounter', 'daily_target');
        }

        $this->config->setUserValue($uid, 'cigarettecounter', 'interval_mode', $intervalMode === 'fixed' ? 'fixed' : 'computed');

        if ($fixedIntervalMinutes !== null && $fixedIntervalMinutes !== '') {
            $this->config->setUserValue($uid, 'cigarettecounter', 'fixed_interval_minutes', (string)(int)$fixedIntervalMinutes);
        } else {
            $this->config->deleteUserValue($uid, 'cigarettecounter', 'fixed_interval_minutes');
        }

        if ($wakeHours !== null && $wakeHours !== '') {
            $this->config->setUserValue($uid, 'cigarettecounter', 'wake_hours', (string)(float)$wakeHours);
        } else {
            $this->config->deleteUserValue($uid, 'cigarettecounter', 'wake_hours');
        }

        $this->config->setUserValue($uid, 'cigarettecounter', 'count_check_enabled', $countCheckEnabled === '1' ? '1' : '0');

        if ($countCheckIntervalMinutes !== null && $countCheckIntervalMinutes !== '') {
            $this->config->setUserValue($uid, 'cigarettecounter', 'count_check_interval_minutes', (string)(int)$countCheckIntervalMinutes);
        } else {
            $this->config->deleteUserValue($uid, 'cigarettecounter', 'count_check_interval_minutes');
        }

        $this->config->setUserValue($uid, 'cigarettecounter', 'next_allowed_reminder_enabled', $nextAllowedReminderEnabled === '1' ? '1' : '0');
    }

    /**
     * Im 'computed'-Modus dynamisch: verbleibendes Tageskontingent wird über
     * die verbleibende Zeit bis zum Ende des Wachzeit-Fensters (verankert an
     * der ersten Zigarette des Tages) verteilt. Wer also z.B. zwei Zigaretten
     * hintereinander raucht, verbraucht Kontingent schneller als geplant -
     * das Intervall für den Rest des Tages wird dadurch automatisch länger,
     * damit das Tagesziel trotzdem eingehalten werden kann. Vor der ersten
     * Zigarette des Tages gilt der statische Ausgangswert (Wachzeit/Ziel).
     */
    public function getIntervalMinutes(string $uid): ?float {
        if ($this->getIntervalMode($uid) === 'fixed') {
            $fixed = $this->getFixedIntervalMinutes($uid);
            return ($fixed !== null && $fixed > 0) ? (float)$fixed : null;
        }

        $target = $this->getDailyTarget($uid);
        if ($target === null || $target <= 0) {
            return null;
        }

        $wakeSeconds = $this->getWakeHours($uid) * 3600;
        $dayStartHour = $this->getDayStartHour($uid);
        $tz = $this->getUserTimeZone($uid);
        $today = $this->currentLogicalDate($dayStartHour, $tz);
        $todayEntries = array_values(array_filter(
            $this->loadEntries($uid),
            fn (string $ts) => $this->logicalDate($ts, $dayStartHour, $tz) === $today
        ));

        // Bei erreichtem/überschrittenem Tagesziel trotzdem einen (dann stark
        // gestreckten) Wert liefern statt null - Intervall wird immer angezeigt.
        $remaining = max($target - count($todayEntries), 1);

        if (empty($todayEntries)) {
            // Noch keine Zigarette heute: statischer Ausgangswert.
            return ($wakeSeconds / $target) / 60;
        }

        $dayStart = new \DateTime($todayEntries[0]);
        $dayEnd = (clone $dayStart)->modify('+' . (int)$wakeSeconds . ' seconds');
        $remainingSeconds = $dayEnd->getTimestamp() - time();
        if ($remainingSeconds <= 0) {
            // Wachzeit-Fenster rechnerisch schon vorbei, trotzdem sinnvoll spreizen.
            $remainingSeconds = 60;
        }

        return ($remainingSeconds / $remaining) / 60;
    }

    /**
     * @param string[] $entries
     */
    public function getNextAllowedAt(string $uid, array $entries): ?string {
        $intervalMinutes = $this->getIntervalMinutes($uid);
        if ($intervalMinutes === null || empty($entries)) {
            return null;
        }
        $last = end($entries);
        $next = new \DateTime($last);
        $next->modify('+' . (int)round($intervalMinutes * 60) . ' seconds');
        return $next->format('c');
    }

    private function loadNotifyState(string $uid): array {
        try {
            $folder = $this->appData->getFolder(self::NOTIFY_STATE_FOLDER);
            $file = $folder->getFile($uid . '.json');
            $data = json_decode($file->getContent(), true);
            return is_array($data) ? $data : [];
        } catch (NotFoundException $e) {
            return [];
        }
    }

    private function saveNotifyState(string $uid, array $state): void {
        try {
            $folder = $this->appData->getFolder(self::NOTIFY_STATE_FOLDER);
        } catch (NotFoundException $e) {
            $folder = $this->appData->newFolder(self::NOTIFY_STATE_FOLDER);
        }

        try {
            $file = $folder->getFile($uid . '.json');
        } catch (NotFoundException $e) {
            $file = $folder->newFile($uid . '.json');
        }
        $file->putContent(json_encode($state));
    }

    /**
     * Merkt sich, für welchen "nextAllowedAt"-Zeitpunkt zuletzt eine
     * Push-Erinnerung verschickt wurde, damit der stündliche Job nicht bei
     * jedem Lauf erneut pusht.
     */
    public function getLastNotifiedFor(string $uid): ?string {
        return $this->loadNotifyState($uid)['lastNotifiedFor'] ?? null;
    }

    public function setLastNotifiedFor(string $uid, string $nextAllowedAt): void {
        $state = $this->loadNotifyState($uid);
        $state['lastNotifiedFor'] = $nextAllowedAt;
        $this->saveNotifyState($uid, $state);
    }

    /**
     * Merkt sich den letzten Zeitpunkt der "Hast du alle gezählt?"-Erinnerung,
     * damit der Job unabhängig von seiner eigenen (systemweiten) Taktung das
     * pro Nutzer eingestellte Erinnerungsintervall einhalten kann.
     */
    public function getLastCountCheckAt(string $uid): ?string {
        return $this->loadNotifyState($uid)['lastCountCheckAt'] ?? null;
    }

    public function setLastCountCheckAt(string $uid, string $iso): void {
        $state = $this->loadNotifyState($uid);
        $state['lastCountCheckAt'] = $iso;
        $this->saveNotifyState($uid, $state);
    }

    public function isCountCheckEnabled(string $uid): bool {
        return $this->config->getUserValue($uid, 'cigarettecounter', 'count_check_enabled', '1') !== '0';
    }

    public function getCountCheckIntervalMinutes(string $uid): int {
        $raw = (int)$this->config->getUserValue($uid, 'cigarettecounter', 'count_check_interval_minutes', '10');
        return $raw > 0 ? $raw : 10;
    }

    public function isNextAllowedReminderEnabled(string $uid): bool {
        return $this->config->getUserValue($uid, 'cigarettecounter', 'next_allowed_reminder_enabled', '1') !== '0';
    }
}
