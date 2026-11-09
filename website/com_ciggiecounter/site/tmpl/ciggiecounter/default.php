<?php

/**
 * @package     CrazyMidi.Site
 * @subpackage  com_ciggiecounter
 *
 * @copyright   (C) 2026 crazy-midi.de
 * @license     GPL-3.0-or-later
 */

defined('_JEXEC') or die;

use Joomla\CMS\Factory;
use Joomla\CMS\Uri\Uri;

/** @var \CrazyMidi\Component\Ciggiecounter\Site\View\Ciggiecounter\HtmlView $this */

// Follows Joomla's resolved language (language filter + switcher), like com_desktopkatze:
// German for a German tag, English for everyone else.
$tag  = Factory::getApplication()->getLanguage()->getTag();
$lang = (stripos($tag, 'de') === 0) ? 'de' : 'en';
$img  = Uri::root(true) . '/media/com_ciggiecounter/img/';

$repo    = 'https://github.com/gh0stless/ciggie-counter';
$haRepo  = 'https://github.com/gh0stless/ciggie-counter-ha';
$mail    = 'info@crazy-midi.de';

$copy = [
    'de' => [
        'eyebrow'     => 'Android · Nextcloud · Home Assistant · Open Source',
        'slogan'      => 'Kaffee · Kippchen · Kacken',
        'lede'        => 'Zähl deine Zigaretten, erkenne deine Muster und plane deine Pausen – ohne Werbung, ohne Konto, ohne Tracking.',
        'cta_beta'    => 'Betatester werden',
        'cta_github'  => 'Download auf GitHub',
        'meta'        => ['kostenlos & quelloffen', 'ohne Google-Dienste', 'Deutsch & Englisch'],
        'alt_hero1'   => 'Ciggie Counter: Zählerseite mit der Tagesmenge, der nächsten erlaubten Zigarette und dem +1-Knopf',
        'alt_hero2'   => 'Ciggie Counter: Statistik mit Tages-, Monats- und Jahreswerten',

        'beta_badge'  => 'Gesucht',
        'beta_h2'     => 'Betatester für den Play Store',
        'beta_intro'  => 'Ciggie Counter soll in den Google Play Store. Vorher verlangt Google einen geschlossenen Test: <strong>mindestens 12 Tester, 14 Tage am Stück</strong>. Wer mitmacht, hat die App vor allen anderen und hilft, die letzten Fehler zu finden.',
        'beta_play_h' => 'Über den Play Store testen',
        'beta_play'   => [
            'Mail an <a href="mailto:%MAIL%?subject=Beta%20Ciggie%20Counter">%MAIL%</a> mit dem Betreff „Beta Ciggie Counter“ und der Gmail-Adresse deines Play-Store-Kontos.',
            'Sobald der Test startet, bekommst du einen Einladungslink und installierst die App ganz normal aus dem Play Store.',
            'App 14 Tage installiert lassen, ab und zu zählen, Auffälliges melden. Mehr ist es nicht.',
        ],
        'beta_free_h' => 'Ohne Google',
        'beta_free'   => 'Kein Play Store auf dem Handy (z. B. GrapheneOS, LineageOS)? Die fertige, signierte APK gibt es auf <a href="%REPO%/releases">GitHub</a>, bald auch bei IzzyOnDroid. Rückmeldungen gern per Mail oder als <a href="%REPO%/issues">GitHub-Issue</a>.',
        'beta_note'   => 'Für Googles 12-Tester-Regel zählen leider nur Tester über den Play Store. Deine Adresse nutze ich nur für die Einladung zum Test.',

        'feat_kicker' => 'Was die App kann',
        'feat_h2'     => 'Einfach zählen. Den Rest rechnet sie.',
        'feat_intro'  => 'Ein Tipp auf +1 genügt. Ciggie Counter merkt sich die Uhrzeit und macht daraus Statistik, Pausen und Erinnerungen.',
        'features'    => [
            ['➕', 'Zählen mit einem Tipp', 'Großer +1-Knopf, vergessene Zigaretten lassen sich nachtragen und Fehler löschen.'],
            ['⏱️', 'Pausen planen', 'Feste Pause oder aus deinem Tagesziel berechnet: Die App zeigt, ab wann die nächste „erlaubt“ ist.'],
            ['🔔', 'Erinnerungen', '„Du darfst wieder“ und „Hast du alle gezählt?“ als Benachrichtigung oder Ansage.'],
            ['📊', 'Statistik', 'Heute, Woche, Monat, Jahr, Tageszeiten und Kosten, mit Tagesziel zum Vergleich.'],
            ['📅', 'Tagesrückblick', 'Auf Wunsch landet jeder Tag als Zusammenfassung in deinem Kalender.'],
            ['🔒', 'Deine Daten bleiben bei dir', 'Alles liegt auf dem Gerät. Kein Konto, keine Werbung, keine Google-Dienste nötig.'],
        ],

        'shots_kicker'=> 'Screenshots',
        'shots_h2'    => 'So sieht es aus',
        'shots'       => ['Zähler', 'Statistik', 'Verlauf über Monate', 'Einstellungen', 'Butt Bin koppeln'],

        'dev_kicker'  => 'Ein Stand auf allen Geräten',
        'dev_h2'      => 'Zählen, wo du gerade bist',
        'dev_intro'   => 'Jeder Teil funktioniert allein. Zusammen gleichen sie sich ab: Zählst du auf dem Handy, steht die Zahl auch in Nextcloud, in Home Assistant und am Handgelenk.',
        'devices'     => [
            ['nextcloud-1.jpg', 'Nextcloud-App', true, 'Eigene Web-App für deine Nextcloud, auch als PWA. Sie ist die Drehscheibe für mehrere Geräte und kann über Home Assistant Ansagen machen.'],
            ['', 'Home Assistant', true, 'Integration über HACS: Sensoren fürs Dashboard, Zählen per Knopf oder Sprachbefehl, Ansagen über deine Lautsprecher. Sie zählt auch ganz ohne Nextcloud.'],
            ['', 'Amazfit Band 7', false, 'Zählen am Handgelenk, Ziffernblatt mit Pause und Tagesmenge. Mehr dazu unten.'],
            ['', 'Butt Bin', false, 'Der Aschenbecher, der mitzählt. Mehr dazu gleich unten.'],
        ],
        'tag_ok'      => 'fertig',
        'tag_dev'     => 'in Arbeit',

        'band_kicker' => 'Am Handgelenk · experimentell',
        'band_h2'     => 'Amazfit Band 7: ein Blick genügt',
        'band_intro'  => 'Ein günstiges Fitnessband wird zur Fernbedienung für Ciggie Counter. Das eigene Ziffernblatt zeigt, wie lange die Pause noch dauert, und gezählt wird direkt am Handgelenk.',
        'band_list'   => [
            'Ziffernblatt mit Countdown, Uhrzeit der nächsten und Tagesmenge',
            'Doppeltipp aufs Ziffernblatt zählt eine Zigarette',
            'Band-App mit großem +1-Knopf; ohne Verbindung wird vorgemerkt und später nachgeholt',
            'Dazu Akku, Schritte, Puls, Stress und Schlaf',
            'Verbindung über Gadgetbridge: ohne Hersteller-App, ohne Hersteller-Cloud',
        ],
        'band_note'   => 'Noch experimentell: Das Band braucht eine angepasste Gadgetbridge-Version, die noch nicht veröffentlicht ist.',
        'alt_band'    => 'Amazfit Band 7 am Handgelenk mit dem Ciggie-Counter-Ziffernblatt: 35 Minuten Pause, nächste ab 07:43, heute 6',

        'bin_kicker'  => 'Hardware · Prototyp',
        'bin_h2'      => 'Butt Bin: der Aschenbecher, der mitzählt',
        'bin_intro'   => 'Ein Drehaschenbecher mit Drücker. Jede Zigarette, die du ausdrückst, wird gezählt, ganz ohne Handy in der Hand.',
        'bin_list'    => [
            'Zählt jeden Druck auf den Drücker und speichert ihn mit Uhrzeit',
            'Funktioniert auch, wenn das Handy nicht in der Nähe ist',
            'Gibt die Einträge per Bluetooth LE an die App weiter',
            'Leuchtring im Knauf, Knopfzelle für Jahre',
            'Offene Hardware: Schaltplan und Firmware im Repository',
        ],
        'bin_note'    => 'Der Butt Bin ist noch in Entwicklung. Die Bilder sind Design-Renderings.',
        'alt_bin'     => 'Butt Bin: Drehaschenbecher mit rot-schwarzem Knauf auf dem Drücker',
        'alt_bins'    => 'Drei Farbvarianten des Butt Bin von oben',
        'bin_caption' => 'Drei Farbvarianten (Renderings)',

        'dl_kicker'   => 'Downloads & Quellcode',
        'dl_h2'       => 'Selbst ausprobieren',
        'links'       => [
            ['%REPO%/releases', 'Android-App (APK)', 'Signierte Releases auf GitHub · Android 13+'],
            ['%REPO%', 'Quellcode', 'App, Nextcloud-App, Firmware und Hardware · GPL-3.0'],
            ['%HAREPO%', 'Home-Assistant-Integration', 'Über HACS als benutzerdefiniertes Repository'],
            ['%REPO%/tree/main/nextcloud-app/cigarettecounter', 'Nextcloud-App', 'Zum Selbst-Installieren, Store-Eintrag folgt'],
        ],

        'foot_health' => 'Ciggie Counter macht keine Werbung fürs Rauchen. Die App hilft dir, dein Rauchen zu sehen und Pausen einzuhalten. Wenn du aufhören willst, findest du Unterstützung bei deiner Ärztin oder deinem Arzt und unter <a href="https://www.rauchfrei-info.de" rel="noopener">rauchfrei-info.de</a>.',
        'foot_contact'=> 'Fragen, Ideen, Fehler: <a href="mailto:%MAIL%">%MAIL%</a>',
    ],
    'en' => [
        'eyebrow'     => 'Android · Nextcloud · Home Assistant · Open source',
        'slogan'      => 'Coffee · Ciggie · Crap',
        'lede'        => 'Count your cigarettes, see your patterns and pace your breaks, without ads, accounts or tracking.',
        'cta_beta'    => 'Become a beta tester',
        'cta_github'  => 'Download on GitHub',
        'meta'        => ['free & open source', 'no Google services', 'English & German'],
        'alt_hero1'   => 'Ciggie Counter: counter screen with today\'s count, the next allowed cigarette and the +1 button',
        'alt_hero2'   => 'Ciggie Counter: statistics with daily, monthly and yearly figures',

        'beta_badge'  => 'Wanted',
        'beta_h2'     => 'Beta testers for Google Play',
        'beta_intro'  => 'Ciggie Counter is heading for the Google Play Store. Before that, Google requires a closed test: <strong>at least 12 testers for 14 days in a row</strong>. Join in, get the app before everyone else and help catch the last bugs.',
        'beta_play_h' => 'Test via Google Play',
        'beta_play'   => [
            'Send an email to <a href="mailto:%MAIL%?subject=Beta%20Ciggie%20Counter">%MAIL%</a> with the subject “Beta Ciggie Counter” and the Gmail address of your Play Store account.',
            'When the test starts you get an invitation link and install the app from the Play Store as usual.',
            'Keep the app installed for 14 days, count now and then, report anything odd. That\'s all.',
        ],
        'beta_free_h' => 'Without Google',
        'beta_free'   => 'No Play Store on your phone (e.g. GrapheneOS, LineageOS)? The signed APK is on <a href="%REPO%/releases">GitHub</a>, soon on IzzyOnDroid as well. Feedback is welcome by email or as a <a href="%REPO%/issues">GitHub issue</a>.',
        'beta_note'   => 'Sadly only testers via Google Play count towards Google\'s 12-tester rule. Your address is only used to invite you to the test.',

        'feat_kicker' => 'What it does',
        'feat_h2'     => 'Just count. It does the maths.',
        'feat_intro'  => 'One tap on +1 is all it takes. Ciggie Counter stores the time and turns it into statistics, breaks and reminders.',
        'features'    => [
            ['➕', 'Count with one tap', 'A big +1 button; add forgotten cigarettes later, delete mistakes.'],
            ['⏱️', 'Pace your breaks', 'A fixed break or one computed from your daily target: the app shows when the next one is “allowed”.'],
            ['🔔', 'Reminders', '“You may smoke again” and “Did you count them all?” as a notification or spoken.'],
            ['📊', 'Statistics', 'Today, week, month, year, time of day and cost, with your daily target for comparison.'],
            ['📅', 'Daily summary', 'Optionally every day ends up as a summary in your calendar.'],
            ['🔒', 'Your data stays yours', 'Everything stays on the device. No account, no ads, no Google services needed.'],
        ],

        'shots_kicker'=> 'Screenshots',
        'shots_h2'    => 'How it looks',
        'shots'       => ['Counter', 'Statistics', 'History over months', 'Settings', 'Pairing the Butt Bin'],

        'dev_kicker'  => 'One count on every device',
        'dev_h2'      => 'Count wherever you are',
        'dev_intro'   => 'Every part works on its own. Together they stay in sync: count on your phone and the number shows up in Nextcloud, in Home Assistant and on your wrist.',
        'devices'     => [
            ['nextcloud-1.jpg', 'Nextcloud app', true, 'A web app for your own Nextcloud, also as a PWA. It is the hub for several devices and can make announcements through Home Assistant.'],
            ['', 'Home Assistant', true, 'Integration via HACS: sensors for your dashboard, count with any button or voice command, announcements on your speakers. It also counts without Nextcloud.'],
            ['', 'Amazfit Band 7', false, 'Count on your wrist, a watch face with break and daily count. More below.'],
            ['', 'Butt Bin', false, 'The ashtray that counts along. More about it below.'],
        ],
        'tag_ok'      => 'ready',
        'tag_dev'     => 'in progress',

        'band_kicker' => 'On your wrist · experimental',
        'band_h2'     => 'Amazfit Band 7: one glance is enough',
        'band_intro'  => 'A cheap fitness band becomes a remote control for Ciggie Counter. Its own watch face shows how long the break still lasts, and you count right on your wrist.',
        'band_list'   => [
            "Watch face with countdown, time of the next one and today's count",
            'Double-tap the watch face to count a cigarette',
            'Band app with a big +1 button; without a connection entries are queued and sent later',
            'Plus battery, steps, heart rate, stress and sleep',
            'Connected via Gadgetbridge: no vendor app, no vendor cloud',
        ],
        'band_note'   => 'Still experimental: the band needs a modified Gadgetbridge build that is not published yet.',
        'alt_band'    => 'Amazfit Band 7 on a wrist with the Ciggie Counter watch face: 35 minutes break, next one from 07:43, 6 today',

        'bin_kicker'  => 'Hardware · prototype',
        'bin_h2'      => 'Butt Bin: the ashtray that counts along',
        'bin_intro'   => 'A spin ashtray with a plunger. Every cigarette you stub out gets counted, no phone in your hand needed.',
        'bin_list'    => [
            'Counts every press of the plunger and stores it with the time',
            'Works even when your phone is not around',
            'Hands the entries to the app via Bluetooth LE',
            'Light ring in the knob, a coin cell lasts for years',
            'Open hardware: schematic and firmware in the repository',
        ],
        'bin_note'    => 'The Butt Bin is still in development. The pictures are design renders.',
        'alt_bin'     => 'Butt Bin: spin ashtray with a red and black knob on the plunger',
        'alt_bins'    => 'Three Butt Bin colour schemes from above',
        'bin_caption' => 'Three colour schemes (renders)',

        'dl_kicker'   => 'Downloads & source code',
        'dl_h2'       => 'Try it yourself',
        'links'       => [
            ['%REPO%/releases', 'Android app (APK)', 'Signed releases on GitHub · Android 13+'],
            ['%REPO%', 'Source code', 'App, Nextcloud app, firmware and hardware · GPL-3.0'],
            ['%HAREPO%', 'Home Assistant integration', 'Via HACS as a custom repository'],
            ['%REPO%/tree/main/nextcloud-app/cigarettecounter', 'Nextcloud app', 'Install it yourself, app store entry to follow'],
        ],

        'foot_health' => 'Ciggie Counter does not promote smoking. It helps you see how much you smoke and keep your breaks. If you want to quit, your doctor or your national quitline can help.',
        'foot_contact'=> 'Questions, ideas, bugs: <a href="mailto:%MAIL%">%MAIL%</a>',
    ],
];

$t = $copy[$lang];

// fill in links; texts above are our own HTML
$fill = static function (string $s) use ($repo, $haRepo, $mail): string {
    return str_replace(['%REPO%', '%HAREPO%', '%MAIL%'], [$repo, $haRepo, $mail], $s);
};
$e = static function (string $s): string {
    return htmlspecialchars($s, ENT_QUOTES, 'UTF-8');
};
?>
<div class="cc-page" lang="<?php echo $lang; ?>">

<header class="cc-hero">
  <div class="cc-wrap cc-hero-grid">
    <div>
      <span class="cc-eyebrow"><?php echo $e($t['eyebrow']); ?></span>
      <h1>Ciggie Counter</h1>
      <p class="cc-slogan"><?php echo $e($t['slogan']); ?></p>
      <p class="cc-lede"><?php echo $e($t['lede']); ?></p>
      <div class="cc-cta">
        <a class="cc-btn cc-btn-primary" href="#beta"><?php echo $e($t['cta_beta']); ?></a>
        <a class="cc-btn cc-btn-ghost" href="<?php echo $repo; ?>/releases" rel="noopener"><?php echo $e($t['cta_github']); ?></a>
      </div>
      <div class="cc-meta">
        <?php foreach ($t['meta'] as $m) : ?><span><?php echo $e($m); ?></span><?php endforeach; ?>
      </div>
    </div>
    <div class="cc-hero-shots">
      <div class="cc-phone"><img src="<?php echo $img; ?>app-<?php echo $lang; ?>-1.jpg" width="405" height="900" alt="<?php echo $e($t['alt_hero1']); ?>"></div>
      <div class="cc-phone"><img src="<?php echo $img; ?>app-<?php echo $lang; ?>-2.jpg" width="405" height="900" alt="<?php echo $e($t['alt_hero2']); ?>" loading="lazy"></div>
    </div>
  </div>
</header>
<div class="cc-flag" aria-hidden="true"><span></span><span></span><span></span></div>

<section class="cc-section" id="beta">
  <div class="cc-wrap">
    <div class="cc-beta">
      <div class="cc-beta-head">
        <span class="cc-badge"><?php echo $e($t['beta_badge']); ?></span>
        <h2><?php echo $e($t['beta_h2']); ?></h2>
      </div>
      <p><?php echo $t['beta_intro']; ?></p>
      <div class="cc-beta-grid">
        <div class="cc-beta-way">
          <h3><?php echo $e($t['beta_play_h']); ?></h3>
          <ol class="cc-beta-steps">
            <?php foreach ($t['beta_play'] as $step) : ?><li><?php echo $fill($step); ?></li><?php endforeach; ?>
          </ol>
          <a class="cc-btn cc-btn-primary" href="mailto:<?php echo $mail; ?>?subject=Beta%20Ciggie%20Counter"><?php echo $e($t['cta_beta']); ?></a>
        </div>
        <div class="cc-beta-way">
          <h3><?php echo $e($t['beta_free_h']); ?></h3>
          <p><?php echo $fill($t['beta_free']); ?></p>
        </div>
      </div>
      <p class="cc-small"><?php echo $e($t['beta_note']); ?></p>
    </div>
  </div>
</section>

<section class="cc-section alt">
  <div class="cc-wrap">
    <span class="cc-kicker"><?php echo $e($t['feat_kicker']); ?></span>
    <h2><?php echo $e($t['feat_h2']); ?></h2>
    <p class="cc-intro"><?php echo $e($t['feat_intro']); ?></p>
    <div class="cc-features">
      <?php foreach ($t['features'] as [$icon, $title, $text]) : ?>
      <div class="cc-card">
        <div class="cc-icon" aria-hidden="true"><?php echo $icon; ?></div>
        <h3><?php echo $e($title); ?></h3>
        <p><?php echo $e($text); ?></p>
      </div>
      <?php endforeach; ?>
    </div>
  </div>
</section>

<section class="cc-section">
  <div class="cc-wrap">
    <span class="cc-kicker"><?php echo $e($t['shots_kicker']); ?></span>
    <h2><?php echo $e($t['shots_h2']); ?></h2>
    <div class="cc-shots">
      <?php foreach ($t['shots'] as $i => $caption) : ?>
      <figure>
        <div class="cc-phone"><img src="<?php echo $img; ?>app-<?php echo $lang; ?>-<?php echo $i + 1; ?>.jpg" width="405" height="900" alt="<?php echo $e($caption); ?>" loading="lazy"></div>
        <figcaption><?php echo $e($caption); ?></figcaption>
      </figure>
      <?php endforeach; ?>
    </div>
  </div>
</section>

<section class="cc-section alt">
  <div class="cc-wrap">
    <span class="cc-kicker"><?php echo $e($t['dev_kicker']); ?></span>
    <h2><?php echo $e($t['dev_h2']); ?></h2>
    <p class="cc-intro"><?php echo $e($t['dev_intro']); ?></p>
    <div class="cc-devices">
      <?php foreach ($t['devices'] as [$pic, $title, $ready, $text]) : ?>
      <div class="cc-card cc-device<?php echo $pic ? '' : ' cc-device-noimg'; ?>">
        <?php if ($pic) : ?><div class="cc-phone"><img src="<?php echo $img . $pic; ?>" width="506" height="900" alt="<?php echo $e($title); ?>" loading="lazy"></div><?php endif; ?>
        <div>
          <h3><?php echo $e($title); ?><span class="cc-tag<?php echo $ready ? ' ok' : ''; ?>"><?php echo $e($ready ? $t['tag_ok'] : $t['tag_dev']); ?></span></h3>
          <p><?php echo $e($text); ?></p>
        </div>
      </div>
      <?php endforeach; ?>
    </div>
  </div>
</section>

<section class="cc-section" id="band7">
  <div class="cc-wrap">
    <div class="cc-bin-grid cc-band-grid">
      <div>
        <span class="cc-kicker"><?php echo $e($t['band_kicker']); ?></span>
        <h2><?php echo $e($t['band_h2']); ?></h2>
        <p class="cc-intro" style="margin-bottom:18px"><?php echo $e($t['band_intro']); ?></p>
        <ul class="cc-bin-list">
          <?php foreach ($t['band_list'] as $li) : ?><li><?php echo $e($li); ?></li><?php endforeach; ?>
        </ul>
        <p class="cc-small"><?php echo $e($t['band_note']); ?></p>
      </div>
      <div class="cc-band-photo"><img src="<?php echo $img; ?>band7-watchface.jpg" width="780" height="880" alt="<?php echo $e($t['alt_band']); ?>" loading="lazy"></div>
    </div>
  </div>
</section>

<section class="cc-section alt" id="butt-bin">
  <div class="cc-wrap">
    <div class="cc-bin-grid">
      <div class="cc-bin-photo"><img src="<?php echo $img; ?>buttbin-hero.jpg" width="736" height="900" alt="<?php echo $e($t['alt_bin']); ?>" loading="lazy"></div>
      <div>
        <span class="cc-kicker"><?php echo $e($t['bin_kicker']); ?></span>
        <h2><?php echo $e($t['bin_h2']); ?></h2>
        <p class="cc-intro" style="margin-bottom:18px"><?php echo $e($t['bin_intro']); ?></p>
        <ul class="cc-bin-list">
          <?php foreach ($t['bin_list'] as $li) : ?><li><?php echo $e($li); ?></li><?php endforeach; ?>
        </ul>
        <p class="cc-small"><?php echo $e($t['bin_note']); ?></p>
      </div>
    </div>
    <div class="cc-wide-photo"><img src="<?php echo $img; ?>buttbin-colours.jpg" width="1400" height="749" alt="<?php echo $e($t['alt_bins']); ?>" loading="lazy"></div>
    <p class="cc-caption"><?php echo $e($t['bin_caption']); ?></p>
  </div>
</section>

<section class="cc-section">
  <div class="cc-wrap">
    <span class="cc-kicker"><?php echo $e($t['dl_kicker']); ?></span>
    <h2><?php echo $e($t['dl_h2']); ?></h2>
    <div class="cc-links" style="margin-top:24px">
      <?php foreach ($t['links'] as [$href, $title, $sub]) : ?>
      <a class="cc-link" href="<?php echo $fill($href); ?>" rel="noopener"><strong><?php echo $e($title); ?></strong><span><?php echo $e($sub); ?></span></a>
      <?php endforeach; ?>
    </div>
  </div>
</section>

<div class="cc-flag" aria-hidden="true"><span></span><span></span><span></span></div>
<footer class="cc-foot">
  <div class="cc-wrap">
    <p><?php echo $t['foot_health']; ?></p>
    <p><?php echo $fill($t['foot_contact']); ?></p>
  </div>
</footer>

</div>
