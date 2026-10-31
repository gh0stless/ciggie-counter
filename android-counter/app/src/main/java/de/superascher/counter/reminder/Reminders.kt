package de.superascher.counter.reminder

import android.Manifest
import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import de.superascher.counter.R
import de.superascher.counter.data.AppState
import de.superascher.counter.data.EntryStore
import de.superascher.counter.data.Settings
import de.superascher.counter.logic.Counter
import de.superascher.counter.sync.Nextcloud
import de.superascher.counter.ui.MainActivity

/**
 * Erinnerungen wie in der Nextcloud-App (PushReminderJob / CountCheckReminderJob),
 * hier per AlarmManager statt Cron. Nach jeder Änderung an Einträgen oder Einstellungen [reschedule].
 */
object Reminders {
    private const val CHANNEL = "reminders"
    private const val ACTION_NEXT_ALLOWED = "de.superascher.counter.NEXT_ALLOWED"
    private const val ACTION_COUNT_CHECK = "de.superascher.counter.COUNT_CHECK"
    const val ACTION_COUNT = "de.superascher.counter.COUNT"

    /**
     * Eine Zigarette zählen (Knopf, Nachtragen, Benachrichtigung, Butt Bin).
     * Sprachansagen über Home Assistant macht die Nextcloud-App, wenn der Eintrag dort ankommt.
     * [announce] = false, wenn der Aufrufer mehrere Einträge auf einmal bringt und selbst einmal ansagt.
     */
    fun count(context: Context, ts: Long = Counter.nowSeconds(), source: String = "manual", announce: Boolean = true) {
        val nc = Settings.load(context).ncEnabled
        EntryStore.get(context).add(ts, source, forward = nc)
        if (nc) Nextcloud.kick(context)
        // Wer gerade zählt, braucht keine "Alle gezählt?"-Erinnerung: Takt beginnt neu
        AppState(context).lastCountCheckAt = Counter.nowSeconds()
        reschedule(context)
        if (announce) announceCount(context, ts)
    }

    /** "Cigarette number 12 counted." auf dem Handy, nur für Einträge des heutigen Zähltags. */
    fun announceCount(context: Context, ts: Long) {
        val settings = Settings.load(context)
        if (!settings.speakCount) return
        val counter = Counter(settings)
        val today = counter.today()
        if (counter.logicalDate(ts) != today) return
        val number = counter.onDay(EntryStore.get(context).entries.value, today).count { it <= ts }
        Speech.say(context, R.string.speech_counted, number)
    }

    /** Einen Eintrag löschen, bei eingeschalteter Nextcloud auch dort. */
    fun delete(context: Context, ts: Long) {
        val nc = Settings.load(context).ncEnabled
        EntryStore.get(context).delete(ts, forward = nc)
        if (nc) Nextcloud.kick(context)
        reschedule(context)
    }

    fun reschedule(context: Context) {
        val settings = Settings.load(context)
        val state = AppState(context)
        val entries = EntryStore.get(context).entries.value
        val now = Counter.nowSeconds()

        val next = Counter(settings).allowedFrom(entries, now)
        val last = entries.lastOrNull()
        if (next != null && next < now - 15 * 60) {
            state.lastNotifiedFor = last ?: 0 // längst erlaubt (z. B. nach Neustart): nicht nachträglich melden
        }
        if ((settings.nextAllowedReminder || settings.nextAllowedSpeak) && next != null && last != state.lastNotifiedFor) {
            setAlarm(context, ACTION_NEXT_ALLOWED, maxOf(next, now + 1))
        } else {
            cancelAlarm(context, ACTION_NEXT_ALLOWED)
        }

        if (settings.countCheckReminder || settings.countCheckSpeak) {
            val base = state.lastCountCheckAt.takeIf { it > 0 } ?: now
            setAlarm(context, ACTION_COUNT_CHECK, maxOf(base + settings.countCheckMinutes * 60L, now + 60))
        } else {
            cancelAlarm(context, ACTION_COUNT_CHECK)
        }
    }

    fun createChannel(context: Context) {
        context.getSystemService(NotificationManager::class.java).createNotificationChannel(
            NotificationChannel(CHANNEL, context.getString(R.string.channel_reminders), NotificationManager.IMPORTANCE_DEFAULT)
                .apply { description = context.getString(R.string.channel_reminders_desc) }
        )
    }

    /** [onDone]: nach einer eventuellen Ansage (der Empfänger hält den Prozess so lange wach). */
    internal fun fire(context: Context, action: String, onDone: () -> Unit = {}) {
        var speech: Int? = null
        val state = AppState(context)
        val settings = Settings.load(context)
        when (action) {
            ACTION_NEXT_ALLOWED -> {
                val entries = EntryStore.get(context).entries.value
                val last = entries.lastOrNull() ?: return onDone()
                val next = Counter(settings).allowedFrom(entries) ?: return onDone()
                // einmal pro Pause melden, erst merken, dann melden: nie doppelt
                if (last != state.lastNotifiedFor && next <= Counter.nowSeconds()) {
                    state.lastNotifiedFor = last
                    if (settings.nextAllowedReminder) notify(context, 1, context.getString(R.string.msg_next_allowed))
                    if (settings.nextAllowedSpeak) speech = R.string.msg_next_allowed
                }
            }
            ACTION_COUNT_CHECK -> {
                state.lastCountCheckAt = Counter.nowSeconds()
                if (settings.countCheckReminder) notify(context, 2, context.getString(R.string.msg_count_check))
                if (settings.countCheckSpeak) speech = R.string.msg_count_check
            }
        }
        reschedule(context)
        speech?.let { Speech.say(context, it, onDone = onDone) } ?: onDone()
    }

    private fun notify(context: Context, id: Int, message: String) {
        if (context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) {
            val open = PendingIntent.getActivity(
                context, 0, Intent(context, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE,
            )
            val count = PendingIntent.getBroadcast(
                context, 10, Intent(context, ReminderReceiver::class.java).setAction(ACTION_COUNT),
                PendingIntent.FLAG_IMMUTABLE,
            )
            val n = android.app.Notification.Builder(context, CHANNEL)
                .setSmallIcon(android.R.drawable.ic_popup_reminder)
                .setContentTitle(context.getString(R.string.app_name))
                .setContentText(message)
                .setContentIntent(open)
                .setAutoCancel(true)
                .addAction(android.app.Notification.Action.Builder(null, context.getString(R.string.action_counted), count).build())
                .build()
            context.getSystemService(NotificationManager::class.java).notify(id, n)
        }
    }

    private fun pending(context: Context, action: String) = PendingIntent.getBroadcast(
        context, action.hashCode(), Intent(context, ReminderReceiver::class.java).setAction(action),
        PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
    )

    private fun setAlarm(context: Context, action: String, atSeconds: Long) {
        val am = context.getSystemService(AlarmManager::class.java)
        val at = atSeconds * 1000
        // Genaue Wecker nur mit Erlaubnis (Android 14+ fragt nach), sonst ungenau (ein paar Minuten später)
        if (am.canScheduleExactAlarms()) {
            am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pending(context, action))
        } else {
            am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pending(context, action))
        }
    }

    private fun cancelAlarm(context: Context, action: String) =
        context.getSystemService(AlarmManager::class.java).cancel(pending(context, action))
}

/** Wecker, "+1" aus der Benachrichtigung und Neustart des Handys. */
class ReminderReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        when (val action = intent.action) {
            Reminders.ACTION_COUNT -> {
                Reminders.count(context)
                context.getSystemService(NotificationManager::class.java).cancelAll()
            }
            Intent.ACTION_BOOT_COMPLETED, AlarmManager.ACTION_SCHEDULE_EXACT_ALARM_PERMISSION_STATE_CHANGED -> {
                Reminders.reschedule(context)
                de.superascher.counter.ashtray.Presence.register(context)
            }
            de.superascher.counter.ashtray.Presence.ACTION_REFRESH -> de.superascher.counter.ashtray.Presence.register(context)
            null -> Unit
            else -> {
                // Ansage läuft asynchron: Prozess wach halten, bis sie fertig ist (Android friert sonst ein)
                val pending = goAsync()
                Reminders.fire(context, action) { pending.finish() }
            }
        }
    }
}
