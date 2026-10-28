<?php

declare(strict_types=1);

namespace OCA\CigaretteCounter\BackgroundJob;

use OCA\CigaretteCounter\Service\EntryService;
use OCA\CigaretteCounter\Service\HomeAssistantNotifier;
use OCA\CigaretteCounter\Service\PushSubscriptionService;
use OCP\AppFramework\Utility\ITimeFactory;
use OCP\BackgroundJob\TimedJob;

/**
 * Prüft minütlich pro Nutzer, ob laut dessen eigenem (in den Einstellungen
 * konfigurierbaren) Erinnerungsintervall wieder eine "Hast du alle
 * Zigaretten gezählt?"-Erinnerung fällig ist - per Web Push und, falls
 * eingerichtet, als Ansage über den Home-Assistant-Webhook. Die Job-Taktung
 * (setInterval) ist nur die Prüf-Frequenz, nicht das Erinnerungsintervall.
 */
class CountCheckReminderJob extends TimedJob {
    private const MESSAGE = 'Hast du alle Zigaretten gezählt?';

    private EntryService $entryService;
    private PushSubscriptionService $pushService;
    private HomeAssistantNotifier $haNotifier;

    public function __construct(
        ITimeFactory $time,
        EntryService $entryService,
        PushSubscriptionService $pushService,
        HomeAssistantNotifier $haNotifier
    ) {
        parent::__construct($time);
        $this->setInterval(60);
        $this->entryService = $entryService;
        $this->pushService = $pushService;
        $this->haNotifier = $haNotifier;
    }

    protected function run($argument): void {
        $now = new \DateTime();

        // Nutzer mit Push-Abo ODER eingetragenem HA-Webhook.
        $uids = array_unique(array_merge(
            $this->pushService->listUserIdsWithSubscriptions(),
            $this->entryService->listUserIdsWithEntries()
        ));

        foreach ($uids as $uid) {
            if (!$this->entryService->isCountCheckEnabled($uid)) {
                continue;
            }

            $hasPush = !empty($this->pushService->loadSubscriptions($uid));
            $hasHa = $this->haNotifier->getWebhookUrl($uid) !== '';
            if (!$hasPush && !$hasHa) {
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
            if ($hasPush) {
                $this->pushService->sendToUser($uid, 'Zigarettenzähler', self::MESSAGE);
            }
            if ($hasHa) {
                $this->haNotifier->notify($uid, self::MESSAGE);
            }
        }
    }
}
