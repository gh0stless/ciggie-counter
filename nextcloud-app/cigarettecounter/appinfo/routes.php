<?php

declare(strict_types=1);

return [
    'routes' => [
        [
            'name' => 'page#index',
            'url' => '/',
            'verb' => 'GET',
        ],
        [
            'name' => 'page#manifest',
            'url' => '/manifest.webmanifest',
            'verb' => 'GET',
        ],
        [
            'name' => 'page#serviceWorker',
            'url' => '/sw.js',
            'verb' => 'GET',
        ],
        [
            'name' => 'page#icon',
            'url' => '/icon/{size}',
            'verb' => 'GET',
        ],
        [
            'name' => 'api#today',
            'url' => '/api/today',
            'verb' => 'GET',
        ],
        [
            'name' => 'api#add',
            'url' => '/api/add',
            'verb' => 'POST',
        ],
        [
            'name' => 'api#entries',
            'url' => '/api/entries',
            'verb' => 'GET',
        ],
        [
            'name' => 'api#remove',
            'url' => '/api/entries/{ts}',
            'verb' => 'DELETE',
        ],
        [
            'name' => 'api#settings',
            'url' => '/api/settings',
            'verb' => 'GET',
        ],
        [
            'name' => 'api#updateSettings',
            'url' => '/api/settings',
            'verb' => 'POST',
        ],
        [
            'name' => 'api#vapidPublicKey',
            'url' => '/api/vapid-public-key',
            'verb' => 'GET',
        ],
        [
            'name' => 'api#pushSubscribe',
            'url' => '/api/push-subscribe',
            'verb' => 'POST',
        ],
        [
            'name' => 'api#resetAll',
            'url' => '/api/reset',
            'verb' => 'POST',
        ],
        [
            'name' => 'api#haTest',
            'url' => '/api/ha-test',
            'verb' => 'POST',
        ],
    ],
];
