<?php

declare(strict_types=1);

namespace OCA\CigaretteCounter\BackgroundJob;

use OCA\CigaretteCounter\Service\EntryService;
use OCA\CigaretteCounter\Service\PushSubscriptionService;
use OCP\AppFramework\Utility\ITimeFactory;
use OCP\BackgroundJob\TimedJob;

/**
 * Prüft minütlich (begrenzt durch die tatsächliche Cron-Taktung des Systems,
 * i.d.R. alle paar Minuten) pro Nutzer, ob die berechnete Pausenzeit
 * ("nextAllowedAt") gerade abgelaufen ist, und schickt dann genau einmal
 * eine Erinnerung per Web Push (Browser/PWA). Ansagen über Home Assistant
 * macht die HA-Integration "Ciggie Counter".
 */
class PushReminderJob extends TimedJob {
    private const MESSAGE = 'Du darfst jetzt wieder eine rauchen.';

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

        foreach ($this->entryService->listUserIdsWithEntries() as $uid) {
            // Ansagen über Home Assistant macht die HA-Integration selbst
            if (!$this->entryService->isNextAllowedReminderEnabled($uid)) {
                continue;
            }

            $entries = $this->entryService->loadEntries($uid);
            $nextAllowedAt = $this->entryService->getNextAllowedAt($uid, $entries);
            if ($nextAllowedAt === null) {
                continue;
            }

            $target = new \DateTime($nextAllowedAt);
            if ($target > $now) {
                continue;
            }

            if ($this->entryService->getLastNotifiedFor($uid) === $nextAllowedAt) {
                continue;
            }

            // Erst merken, dann senden: hängt HA oder der Push-Dienst, soll
            // der nächste Cron-Lauf nicht noch einmal ansagen.
            $this->entryService->setLastNotifiedFor($uid, $nextAllowedAt);
            // Stumm: Erinnerung gilt als erledigt, kommt also nach dem Einschalten nicht nach
            if ($this->entryService->isMuted($uid)) {
                continue;
            }
            $this->pushService->sendToUser($uid, 'Zigarettenzähler', self::MESSAGE);
        }
    }
}
