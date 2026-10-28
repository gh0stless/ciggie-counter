<?php

declare(strict_types=1);

namespace OCA\CigaretteCounter\Service;

use Minishlink\WebPush\Subscription;
use Minishlink\WebPush\VAPID;
use Minishlink\WebPush\WebPush;
use OCP\Files\IAppData;
use OCP\Files\NotFoundException;
use OCP\IConfig;
use Psr\Log\LoggerInterface;

/**
 * Eigenes Web Push (VAPID), unabhängig von der offiziellen Nextcloud-App und
 * ihrem Push-Relay - läuft direkt aus unserem PWA-Service-Worker heraus.
 */
class PushSubscriptionService {
    private const SUBSCRIPTIONS_FOLDER = 'push-subscriptions';

    private IAppData $appData;
    private IConfig $config;
    private LoggerInterface $logger;

    public function __construct(IAppData $appData, IConfig $config, LoggerInterface $logger) {
        $this->appData = $appData;
        $this->config = $config;
        $this->logger = $logger;
    }

    public function getVapidPublicKey(): string {
        $keys = $this->getOrCreateVapidKeys();
        return $keys['publicKey'];
    }

    private function getOrCreateVapidKeys(): array {
        $public = $this->config->getAppValue('cigarettecounter', 'vapid_public_key', '');
        $private = $this->config->getAppValue('cigarettecounter', 'vapid_private_key', '');

        if ($public !== '' && $private !== '') {
            return ['publicKey' => $public, 'privateKey' => $private];
        }

        $keys = VAPID::createVapidKeys();
        $this->config->setAppValue('cigarettecounter', 'vapid_public_key', $keys['publicKey']);
        $this->config->setAppValue('cigarettecounter', 'vapid_private_key', $keys['privateKey']);
        return $keys;
    }

    /**
     * @return string[] alle Nutzer-IDs mit mindestens einem Push-Abo
     */
    public function listUserIdsWithSubscriptions(): array {
        try {
            $folder = $this->appData->getFolder(self::SUBSCRIPTIONS_FOLDER);
        } catch (NotFoundException $e) {
            return [];
        }

        $uids = [];
        foreach ($folder->getDirectoryListing() as $file) {
            $name = $file->getName();
            if (str_ends_with($name, '.json')) {
                $uids[] = substr($name, 0, -strlen('.json'));
            }
        }
        return $uids;
    }

    /**
     * @return array<int, array{endpoint: string, keys: array{p256dh: string, auth: string}}>
     */
    public function loadSubscriptions(string $uid): array {
        try {
            $folder = $this->appData->getFolder(self::SUBSCRIPTIONS_FOLDER);
            $file = $folder->getFile($uid . '.json');
            $data = json_decode($file->getContent(), true);
            return is_array($data) ? $data : [];
        } catch (NotFoundException $e) {
            return [];
        }
    }

    /**
     * @param array<int, array> $subscriptions
     */
    private function saveSubscriptions(string $uid, array $subscriptions): void {
        try {
            $folder = $this->appData->getFolder(self::SUBSCRIPTIONS_FOLDER);
        } catch (NotFoundException $e) {
            $folder = $this->appData->newFolder(self::SUBSCRIPTIONS_FOLDER);
        }

        try {
            $file = $folder->getFile($uid . '.json');
        } catch (NotFoundException $e) {
            $file = $folder->newFile($uid . '.json');
        }
        $file->putContent(json_encode(array_values($subscriptions)));
    }

    public function addSubscription(string $uid, array $subscription): void {
        $subscriptions = $this->loadSubscriptions($uid);
        foreach ($subscriptions as $existing) {
            if ($existing['endpoint'] === $subscription['endpoint']) {
                return;
            }
        }
        $subscriptions[] = $subscription;
        $this->saveSubscriptions($uid, $subscriptions);
    }

    public function removeSubscriptionByEndpoint(string $uid, string $endpoint): void {
        $subscriptions = array_values(array_filter(
            $this->loadSubscriptions($uid),
            fn (array $s) => $s['endpoint'] !== $endpoint
        ));
        $this->saveSubscriptions($uid, $subscriptions);
    }

    public function sendToUser(string $uid, string $title, string $body): void {
        $subscriptions = $this->loadSubscriptions($uid);
        if (empty($subscriptions)) {
            return;
        }

        $keys = $this->getOrCreateVapidKeys();
        $webPush = new WebPush([
            'VAPID' => [
                'subject' => 'mailto:admin@localhost',
                'publicKey' => $keys['publicKey'],
                'privateKey' => $keys['privateKey'],
            ],
        ]);

        $payload = json_encode(['title' => $title, 'body' => $body]);
        $expired = [];

        foreach ($subscriptions as $sub) {
            $subscription = Subscription::create($sub);
            try {
                $report = $webPush->sendOneNotification($subscription, $payload);
                if (!$report->isSuccess() && $report->isSubscriptionExpired()) {
                    $expired[] = $sub['endpoint'];
                }
            } catch (\Throwable $e) {
                $this->logger->warning('Push an ' . $uid . ' fehlgeschlagen: ' . $e->getMessage(), ['app' => 'cigarettecounter']);
            }
        }

        foreach ($expired as $endpoint) {
            $this->removeSubscriptionByEndpoint($uid, $endpoint);
        }
    }
}
