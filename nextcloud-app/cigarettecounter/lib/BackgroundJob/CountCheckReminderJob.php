<?php

declare(strict_types=1);

namespace OCA\CigaretteCounter\BackgroundJob;

use OCA\CigaretteCounter\Service\EntryService;
use OCA\CigaretteCounter\Service\PushSubscriptionService;
use OCP\AppFramework\Utility\ITimeFactory;
use OCP\BackgroundJob\TimedJob;

/**
 * Prüft minütlich pro Nutzer, ob laut dessen eigenem (in den Einstellungen
 * konfigurierbaren) Erinnerungsintervall wieder eine "Hast du alle
 * Zigaretten gezählt?"-Erinnerung fällig ist - per Web Push (Browser/PWA).
 * Ansagen über Home Assistant macht die HA-Integration "Ciggie Counter". Die Job-Taktung
 * (setInterval) ist nur die Prüf-Frequenz, nicht das Erinnerungsintervall.
 */
class CountCheckReminderJob extends TimedJob {
    private const MESSAGE = 'Hast du alle Zigaretten gezählt?';

    private EntryService $entryService;
    private PushSubscriptionService $pushService;

    public function __construct(
        ITimeFactory $time,
        EntryService $entryService,
        PushSubscriptionService $pushService
    ) {
        parent::__construct($time);
        $this->setInterval(60);
        $this->entryService = $entryService;
        $this->pushService = $pushService;
    }

    protected function run($argument): void {
        $now = new \DateTime();

        // Nur Browser-/PWA-Push; Ansagen über Home Assistant macht die HA-Integration selbst
        $uids = $this->pushService->listUserIdsWithSubscriptions();

        foreach ($uids as $uid) {
            if (!$this->entryService->isCountCheckEnabled($uid)
                || empty($this->pushService->loadSubscriptions($uid))) {
                continue;
            }

            $intervalMinutes = $this->entryService->getCountCheckIntervalMinutes($uid);
            $lastAt = $this->entryService->getLastCountCheckAt($uid);
            if ($lastAt !== null) {
                $elapsedMinutes = ($now->getTimestamp() - (new \DateTime($lastAt))->getTimestamp()) / 60;
                if ($elapsedMinutes < $intervalMinutes) {
                    continue;
                }
            }

            // Erst merken, dann senden: hängt HA, soll der nächste Lauf nicht doppelt ansagen.
            $this->entryService->setLastCountCheckAt($uid, $now->format('c'));
            // Stumm: Takt läuft still weiter, nach dem Einschalten kommt nichts sofort nach
            if ($this->entryService->isMuted($uid)) {
                continue;
            }
            $this->pushService->sendToUser($uid, 'Zigarettenzähler', self::MESSAGE);
        }
    }
}
