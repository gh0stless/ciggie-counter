<?php

declare(strict_types=1);

namespace OCA\CigaretteCounter\Controller;

use OCP\AppFramework\Controller;
use OCP\AppFramework\Http;
use OCP\AppFramework\Http\DataDisplayResponse;
use OCP\AppFramework\Http\TemplateResponse;
use OCP\IRequest;
use OCP\IURLGenerator;
use OCP\Util;

class PageController extends Controller {
    private IURLGenerator $urlGenerator;

    public function __construct(string $appName, IRequest $request, IURLGenerator $urlGenerator) {
        parent::__construct($appName, $request);
        $this->urlGenerator = $urlGenerator;
    }

    /**
     * @NoAdminRequired
     * @NoCSRFRequired
     */
    public function index(): TemplateResponse {
        Util::addScript($this->appName, 'main');
        Util::addStyle($this->appName, 'style');

        $manifestUrl = $this->urlGenerator->linkToRoute($this->appName . '.page.manifest');
        $iconUrl = $this->urlGenerator->linkToRoute($this->appName . '.page.icon', ['size' => '192']);

        Util::addHeader('link', ['rel' => 'manifest', 'href' => $manifestUrl]);
        Util::addHeader('link', ['rel' => 'apple-touch-icon', 'href' => $iconUrl]);
        Util::addHeader('meta', ['name' => 'apple-mobile-web-app-capable', 'content' => 'yes']);
        Util::addHeader('meta', ['name' => 'mobile-web-app-capable', 'content' => 'yes']);
        Util::addHeader('meta', ['name' => 'theme-color', 'content' => '#1a1a1a']);

        return new TemplateResponse($this->appName, 'index');
    }

    /**
     * PWA-Manifest wird bewusst über einen echten Controller ausgeliefert statt
     * als statische Datei per linkTo(): auf dieser Nextcloud-Instanz (34.0.3)
     * liefert Apache Dateien im App-Ordner NICHT mehr direkt aus (anders als
     * frühere Annahme aus der GlobalRandom-App, siehe deren HANDOVER.md -
     * dort inzwischen vermutlich ebenfalls stillschweigend kaputt).
     *
     * Manifest, Service Worker und Icons sind öffentlich (@PublicPage): sie enthalten
     * nichts Persönliches, werden aber teils OHNE Login-Cookie abgerufen - das Icon
     * einer Push-Benachrichtigung vom Betriebssystem, Service-Worker-Updates auch
     * bei abgelaufener Sitzung. Mit Login-Pflicht gab es dort 401.
     *
     * @PublicPage
     * @NoCSRFRequired
     */
    public function manifest(): DataDisplayResponse {
        $content = file_get_contents(__DIR__ . '/../../manifest.webmanifest');
        return new DataDisplayResponse($content, Http::STATUS_OK, [
            'Content-Type' => 'application/manifest+json',
        ]);
    }

    /**
     * @PublicPage
     * @NoCSRFRequired
     */
    public function serviceWorker(): DataDisplayResponse {
        $content = file_get_contents(__DIR__ . '/../../sw.js');
        return new DataDisplayResponse($content, Http::STATUS_OK, [
            'Content-Type' => 'application/javascript',
            // Browser soll bei jedem Laden auf eine neue Version prüfen.
            'Cache-Control' => 'no-cache',
        ]);
    }

    /**
     * @PublicPage
     * @NoCSRFRequired
     */
    public function icon(string $size): DataDisplayResponse {
        $files = ['192' => 'icon-192.png', '512' => 'icon-512.png'];
        if (!isset($files[$size])) {
            return new DataDisplayResponse('', Http::STATUS_NOT_FOUND);
        }
        $content = file_get_contents(__DIR__ . '/../../img/' . $files[$size]);
        return new DataDisplayResponse($content, Http::STATUS_OK, [
            'Content-Type' => 'image/png',
        ]);
    }
}
