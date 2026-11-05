package de.superascher.counter.watch

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Handler
import android.os.Looper
import de.superascher.counter.data.EntryStore
import de.superascher.counter.data.Settings
import de.superascher.counter.logic.Counter
import de.superascher.counter.reminder.Reminders
import org.json.JSONArray
import org.json.JSONObject

/**
 * Eingaben von der Uhr. Gadgetbridge reicht Nachrichten der Ciggie-Counter-Uhren-App im
 * PebbleKit-Format weiter (bei Zepp OS über die PebbleKit-Fassade, bei Pebble direkt).
 * Protokoll: watch-app/README.md.
 *
 * Ab Android 14 nur von Gadgetbridge: Die Fassade teilt ihre Identität mit
 * ([getSentFromPackage]), andere Apps könnten sonst Einträge einschleusen. Die Antwort geht
 * gezielt an diesen Absender, nicht als offener Rundruf.
 */
class WatchReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != ACTION_RECEIVE) return
        val sender = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            sentFromPackage?.takeIf { it.startsWith(GADGETBRIDGE) } ?: return
        } else {
            null
        }
        if (uuidOf(intent) != APP_UUID) return
        val values = parse(intent.getStringExtra("msg_data") ?: return) ?: return

        when (values[KEY_CMD]) {
            "entry" -> {
                val id = values[KEY_ID] as? String ?: return
                val ts = (values[KEY_TIME] as? Number)?.toLong() ?: return
                val isNew = !EntryStore.get(context).exists(id)
                Reminders.count(context, ts, SOURCE, announce = false, id = id)
                reply(context, "ack", id, sender)
                if (isNew) announceSoon(context, ts, goAsync())
            }
            "hello" -> reply(context, "state", null, sender)
        }
    }

    private fun reply(context: Context, cmd: String, id: String?, sender: String?) {
        val counter = Counter(Settings.load(context))
        val entries = EntryStore.get(context).entries.value
        val today = counter.onDay(entries, counter.today())
        val dict = JSONArray()
        dict.put(item(KEY_CMD, cmd))
        if (id != null) dict.put(item(KEY_ID, id))
        dict.put(item(KEY_TODAY, today.size))
        dict.put(item(KEY_LAST, today.maxOrNull() ?: 0L))
        dict.put(item(KEY_NEXT, counter.allowedFrom(entries) ?: 0L))
        dict.put(item(KEY_DAY_START, Settings.load(context).dayStartHour))

        context.sendBroadcast(Intent(ACTION_SEND).apply {
            if (sender != null) setPackage(sender)
            putExtra("uuid", APP_UUID)
            putExtra("transaction_id", -1)
            putExtra("msg_data", dict.toString())
        })
    }

    private fun item(key: Int, value: Any): JSONObject = JSONObject().apply {
        put("key", key)
        when (value) {
            is String -> {
                put("type", "string")
                put("length", value.length + 1)
            }
            else -> {
                put("type", "int")
                put("length", 4)
            }
        }
        put("value", value)
    }

    private fun uuidOf(intent: Intent): String? =
        (intent.getStringExtra("uuid") ?: intent.getSerializableExtra("uuid")?.toString())?.lowercase()

    private fun parse(json: String): Map<Int, Any>? = try {
        val array = JSONArray(json)
        (0 until array.length()).associate { i ->
            val o = array.getJSONObject(i)
            o.getInt("key") to o.get("value")
        }
    } catch (e: Exception) {
        null
    }

    companion object {
        private const val GADGETBRIDGE = "nodomain.freeyourgadget.gadgetbridge"

        // Mehrere Einträge auf einmal (die Uhr war außer Reichweite) nur einmal ansagen
        private const val ANNOUNCE_DELAY_MS = 1500L
        private val handler = Handler(Looper.getMainLooper())
        private val waiting = mutableListOf<PendingResult>()
        private var newest = 0L
        private var announcement: Runnable? = null

        private fun announceSoon(context: Context, ts: Long, pending: PendingResult) {
            val app = context.applicationContext
            synchronized(waiting) {
                waiting += pending
                newest = maxOf(newest, ts)
                announcement?.let { handler.removeCallbacks(it) }
                announcement = Runnable {
                    val done: List<PendingResult>
                    val at: Long
                    synchronized(waiting) {
                        done = waiting.toList()
                        waiting.clear()
                        at = newest
                        newest = 0L
                        announcement = null
                    }
                    Reminders.announceCount(app, at)
                    done.forEach { it.finish() }
                }.also { handler.postDelayed(it, ANNOUNCE_DELAY_MS) }
            }
        }

        const val ACTION_RECEIVE = "com.getpebble.action.app.RECEIVE"
        const val ACTION_SEND = "com.getpebble.action.app.SEND"

        /** App-ID 1077701 der Uhren-App, wie Gadgetbridge sie als PebbleKit-UUID abbildet */
        const val APP_UUID = "001071c5-0000-0000-0000-000000000000"

        const val SOURCE = "watch"

        const val KEY_CMD = 0
        const val KEY_ID = 1
        const val KEY_TIME = 2
        const val KEY_TODAY = 3
        const val KEY_LAST = 4
        /** Nächste erlaubt ab (Unix-Sekunden), 0 = keine Pause eingestellt */
        const val KEY_NEXT = 5
        /** Tageswechsel-Stunde der App, damit Band und Ziffernblatt denselben Zähltag nehmen */
        const val KEY_DAY_START = 6
    }
}
