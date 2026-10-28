<?php

declare(strict_types=1);

namespace OCA\CigaretteCounter\Service;

use OCA\DAV\CalDAV\CalDavBackend;
use OCP\IConfig;
use Psr\Log\LoggerInterface;

/**
 * Schreibt die Tagessumme als ganztägigen Kalendereintrag. Zielkalender ist pro
 * Nutzer wählbar: der eigene "Zigarettenzähler"-Kalender (Standard, wird bei
 * Bedarf angelegt), ein anderer eigener Kalender oder gar keiner.
 *
 * Nutzt OCA\DAV\CalDAV\CalDavBackend direkt (interne API der core-App "dav",
 * nicht Teil von OCP) - bewusster Kompromiss statt CalDAV-HTTP-Roundtrip.
 */
class CalendarSyncService {
    public const DEFAULT_CALENDAR_URI = 'zigarettenzaehler';
    public const NO_CALENDAR = 'none';
    private const DEFAULT_CALENDAR_DISPLAYNAME = 'Zigarettenzähler';

    private CalDavBackend $calDavBackend;
    private IConfig $config;
    private LoggerInterface $logger;

    public function __construct(CalDavBackend $calDavBackend, IConfig $config, LoggerInterface $logger) {
        $this->calDavBackend = $calDavBackend;
        $this->config = $config;
        $this->logger = $logger;
    }

    public function getCalendarUri(string $uid): string {
        return $this->config->getUserValue($uid, 'cigarettecounter', 'calendar_uri', self::DEFAULT_CALENDAR_URI);
    }

    /**
     * @throws \InvalidArgumentException wenn der Kalender nicht zu den eigenen des Nutzers gehört
     */
    public function setCalendarUri(string $uid, ?string $uri): void {
        $uri = trim((string)$uri);
        if ($uri === '' || $uri === self::DEFAULT_CALENDAR_URI) {
            $this->config->deleteUserValue($uid, 'cigarettecounter', 'calendar_uri');
            return;
        }
        if ($uri !== self::NO_CALENDAR && !array_key_exists($uri, $this->listOwnCalendars($uid))) {
            throw new \InvalidArgumentException('Unbekannter Kalender.');
        }
        $this->config->setUserValue($uid, 'cigarettecounter', 'calendar_uri', $uri);
    }

    /**
     * Eigene (nicht geteilte) Kalender des Nutzers, die Termine aufnehmen können.
     *
     * @return array<string, string> uri => Anzeigename
     */
    public function listOwnCalendars(string $uid): array {
        $principalUri = 'principals/users/' . $uid;
        $result = [];
        foreach ($this->calDavBackend->getCalendarsForUser($principalUri) as $calendar) {
            if (!$this->isOwnCalendar($calendar, $principalUri)) {
                continue; // freigegebener Kalender eines anderen Nutzers
            }
            if ($calendar['uri'] === 'contact_birthdays') {
                continue; // von Nextcloud verwalteter Geburtstagskalender
            }
            $components = $calendar['{urn:ietf:params:xml:ns:caldav}supported-calendar-component-set'] ?? null;
            if ($components !== null && method_exists($components, 'getValue') && !in_array('VEVENT', $components->getValue(), true)) {
                continue; // reine Aufgabenliste o.ä.
            }
            $result[$calendar['uri']] = (string)($calendar['{DAV:}displayname'] ?? $calendar['uri']);
        }
        return $result;
    }

    public function syncDay(string $uid, \DateTimeInterface $day, int $count): void {
        $uri = $this->getCalendarUri($uid);
        if ($uri === self::NO_CALENDAR) {
            return;
        }

        $principalUri = 'principals/users/' . $uid;
        $calendarId = $this->findCalendarId($principalUri, $uri);
        if ($calendarId === null) {
            if ($uri !== self::DEFAULT_CALENDAR_URI) {
                // gewählter Kalender wurde inzwischen gelöscht - nicht stillschweigend anlegen
                $this->logger->warning('Zigarettenzähler: Kalender "' . $uri . '" von ' . $uid . ' existiert nicht mehr, Tageseintrag übersprungen.', ['app' => 'cigarettecounter']);
                return;
            }
            $calendarId = (int)$this->calDavBackend->createCalendar($principalUri, self::DEFAULT_CALENDAR_URI, [
                '{DAV:}displayname' => self::DEFAULT_CALENDAR_DISPLAYNAME,
                'components' => 'VEVENT',
            ]);
        }

        $objectUri = 'cigcounter-' . $day->format('Y-m-d') . '.ics';
        $ics = $this->buildIcs($objectUri, $day, $count);

        $existing = $this->calDavBackend->getCalendarObject($calendarId, $objectUri);
        if ($existing === null) {
            $this->calDavBackend->createCalendarObject($calendarId, $objectUri, $ics);
        } else {
            $this->calDavBackend->updateCalendarObject($calendarId, $objectUri, $ics);
        }
    }

    private function findCalendarId(string $principalUri, string $uri): ?int {
        foreach ($this->calDavBackend->getCalendarsForUser($principalUri) as $calendar) {
            if ($calendar['uri'] === $uri && $this->isOwnCalendar($calendar, $principalUri)) {
                return (int)$calendar['id'];
            }
        }
        return null;
    }

    /**
     * Eigener statt freigegebener Kalender. Vergleicht nur das letzte Pfadsegment,
     * weil CalDavBackend den Principal je nach Endpoint unterschiedlich formatiert
     * (principals/users/<uid> vs. principals/<uid>) - ein exakter Vergleich würde
     * sonst den Standard-Kalender bei jedem Lauf neu anlegen.
     */
    private function isOwnCalendar(array $calendar, string $principalUri): bool {
        $owner = (string)($calendar['principaluri'] ?? '');
        return basename($owner) === basename($principalUri);
    }

    private function buildIcs(string $objectUri, \DateTimeInterface $day, int $count): string {
        $dateStr = $day->format('Ymd');
        $nextDay = (clone $day)->modify('+1 day')->format('Ymd');
        $now = (new \DateTime('now', new \DateTimeZone('UTC')))->format('Ymd\THis\Z');
        $summary = '🚬 ' . $count . ' Zigarette' . ($count === 1 ? '' : 'n');

        return implode("\r\n", [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//CigaretteCounter//DE',
            'BEGIN:VEVENT',
            'UID:' . $objectUri,
            'DTSTAMP:' . $now,
            'DTSTART;VALUE=DATE:' . $dateStr,
            'DTEND;VALUE=DATE:' . $nextDay,
            'SUMMARY:' . $summary,
            'TRANSP:TRANSPARENT',
            'END:VEVENT',
            'END:VCALENDAR',
            '',
        ]);
    }
}
