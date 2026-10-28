<?php

declare(strict_types=1);

namespace OCA\CigaretteCounter\BackgroundJob;

use OCA\CigaretteCounter\Service\CalendarSyncService;
use OCA\CigaretteCounter\Service\EntryService;
use OCP\AppFramework\Utility\ITimeFactory;
use OCP\BackgroundJob\TimedJob;

/**
 * Läuft stündlich, schreibt/aktualisiert dabei immer die Zigarettenzahl des
 * GESTRIGEN, abgeschlossenen Tages in den Kalender. Kein exaktes
 * "genau um 24:00"-Scheduling nötig: durch das Upsert (gleiche UID pro Tag)
 * ist jeder Lauf idempotent, und nachträgliche Korrekturen von gestern
 * werden spätestens eine Stunde später nachgezogen.
 */
class DailySummaryJob extends TimedJob {
    private EntryService $entryService;
    private CalendarSyncService $calendarSync;

    public function __construct(
        ITimeFactory $time,
        EntryService $entryService,
        CalendarSyncService $calendarSync
    ) {
        parent::__construct($time);
        $this->setInterval(3600);
        $this->entryService = $entryService;
        $this->calendarSync = $calendarSync;
    }

    protected function run($argument): void {
        foreach ($this->entryService->listUserIdsWithEntries() as $uid) {
            // "Gestern" nach dem eigenen Tageswechsel des Nutzers: bei z.B. 4 Uhr
            // gilt ein Tag erst ab 4:00 als abgeschlossen, und Zigaretten bis 3:59
            // landen noch im Kalendereintrag des Vortags.
            $h = $this->entryService->getDayStartHour($uid);
            $tz = $this->entryService->getUserTimeZone($uid);
            $dayPrefix = $this->entryService->currentLogicalDate($h, $tz, -1);
            $entries = $this->entryService->loadEntries($uid);
            $count = $this->entryService->countForDay($entries, $dayPrefix, $h, $tz);
            $this->calendarSync->syncDay($uid, new \DateTime($dayPrefix), $count);
        }
    }
}
