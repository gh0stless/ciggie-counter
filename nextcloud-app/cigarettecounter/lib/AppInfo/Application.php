<?php

declare(strict_types=1);

namespace OCA\CigaretteCounter\AppInfo;

// Nextcloud lädt den Composer-Autoloader einer App nicht von selbst - ohne
// diese Zeile wirft jede Klasse aus vendor/ (hier: minishlink/web-push)
// "Class ... not found", sobald sie tatsächlich gebraucht wird.
require_once __DIR__ . '/../../vendor/autoload.php';

use OCA\CigaretteCounter\BackgroundJob\CountCheckReminderJob;
use OCA\CigaretteCounter\BackgroundJob\DailySummaryJob;
use OCA\CigaretteCounter\BackgroundJob\PushReminderJob;
use OCP\AppFramework\App;
use OCP\AppFramework\Bootstrap\IBootContext;
use OCP\AppFramework\Bootstrap\IBootstrap;
use OCP\AppFramework\Bootstrap\IRegistrationContext;
use OCP\BackgroundJob\IJobList;

class Application extends App implements IBootstrap {
    public const APP_ID = 'cigarettecounter';

    public function __construct() {
        parent::__construct(self::APP_ID);
    }

    public function register(IRegistrationContext $context): void {
        // Keine eigenen Services/Events/Middleware nötig.
    }

    public function boot(IBootContext $context): void {
        $jobList = $context->getAppContainer()->get(IJobList::class);
        if (!$jobList->has(DailySummaryJob::class, null)) {
            $jobList->add(DailySummaryJob::class);
        }
        if (!$jobList->has(PushReminderJob::class, null)) {
            $jobList->add(PushReminderJob::class);
        }
        if (!$jobList->has(CountCheckReminderJob::class, null)) {
            $jobList->add(CountCheckReminderJob::class);
        }
    }
}
