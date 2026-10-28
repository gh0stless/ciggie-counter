<?php

declare(strict_types=1);

namespace OCA\CigaretteCounter\Service;

use OCP\IConfig;
use Psr\Log\LoggerInterface;

/**
 * Meldet Erinnerungen an einen Home-Assistant-Webhook. Welcher Lautsprecher,
 * welche Stimme (Piper) und ob überhaupt abgespielt wird, entscheidet die
 * Automation in HA - die App schickt nur den Text.
 */
class HomeAssistantNotifier {
    private IConfig $config;
    private LoggerInterface $logger;
    private string $lastError = '';

    public function __construct(IConfig $config, LoggerInterface $logger) {
        $this->config = $config;
        $this->logger = $logger;
    }

    public function getWebhookUrl(string $uid): string {
        return $this->config->getUserValue($uid, 'cigarettecounter', 'ha_webhook_url', '');
    }

    public function setWebhookUrl(string $uid, ?string $url): void {
        $url = trim((string)$url);
        if ($url === '') {
            $this->config->deleteUserValue($uid, 'cigarettecounter', 'ha_webhook_url');
            return;
        }
        // Nur http(s) - der Server ruft diese URL selbst auf.
        if (!preg_match('#^https?://#i', $url)) {
            throw new \InvalidArgumentException('Webhook-URL muss mit http:// oder https:// beginnen.');
        }
        $this->config->setUserValue($uid, 'cigarettecounter', 'ha_webhook_url', $url);
    }

    /**
     * @return bool true, wenn HA den Aufruf angenommen hat (bzw. keine URL gesetzt ist: false)
     */
    public function notify(string $uid, string $message): bool {
        $url = $this->getWebhookUrl($uid);
        if ($url === '') {
            return false;
        }

        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
            CURLOPT_POSTFIELDS => json_encode(['message' => $message]),
            CURLOPT_RETURNTRANSFER => true,
            // Ein nicht erreichbares HA darf den Cron-Job nicht aufhalten.
            CURLOPT_CONNECTTIMEOUT => 3,
            CURLOPT_TIMEOUT => 5,
        ]);
        curl_exec($ch);
        $status = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        curl_close($ch);

        if ($status < 200 || $status >= 300) {
            $this->lastError = $status === 0 ? $error : ('HTTP ' . $status);
            if (str_contains($error, 'resolve host') && str_contains($url, '.local')) {
                // mDNS (.local) funktioniert im Nextcloud-Docker-Container nicht.
                $this->lastError .= ' – .local-Namen gehen im Container nicht, die IP-Adresse von Home Assistant verwenden.';
            }
            $this->logger->warning(
                'Home-Assistant-Webhook für ' . $uid . ' fehlgeschlagen: HTTP ' . $status . ($error !== '' ? ' (' . $error . ')' : ''),
                ['app' => 'cigarettecounter']
            );
            return false;
        }
        $this->lastError = '';
        return true;
    }

    public function getLastError(): string {
        return $this->lastError;
    }
}
