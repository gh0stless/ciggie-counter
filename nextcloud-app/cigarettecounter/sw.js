// Service Worker nur für Web-Push-Benachrichtigungen.
//
// Bewusst KEIN 'fetch'-Handler: Ein reiner Durchreicher (respondWith(fetch(...)))
// brachte nichts (kein Offline-Caching) und war die wahrscheinliche Ursache dafür,
// dass Klicks/Anfragen nach einer Weile den Browser gar nicht mehr verließen, bis
// man F5 drückte. Aktuelle Browser brauchen ihn auch nicht mehr, um die Seite als
// installierbare App (PWA) zu erkennen.
self.addEventListener('install', function () {
    self.skipWaiting();
});

self.addEventListener('activate', function (event) {
    event.waitUntil(self.clients.claim());
});

self.addEventListener('push', function (event) {
    var data = { title: 'Zigarettenzähler', body: 'Erinnerung' };
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data.body = event.data.text();
        }
    }
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/apps/cigarettecounter/icon/192',
            badge: '/apps/cigarettecounter/icon/192'
        })
    );
});

// Tippen auf die Benachrichtigung: vorhandenes App-Fenster nach vorn holen statt
// jedes Mal ein neues zu öffnen.
self.addEventListener('notificationclick', function (event) {
    event.notification.close();
    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (list) {
            for (var i = 0; i < list.length; i++) {
                if (list[i].url.indexOf('/apps/cigarettecounter/') !== -1 && 'focus' in list[i]) {
                    return list[i].focus();
                }
            }
            return self.clients.openWindow('/apps/cigarettecounter/');
        })
    );
});
