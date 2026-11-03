package de.superascher.counter.watch

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
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
 */
class WatchReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != ACTION_RECEIVE) return
        if (uuidOf(intent) != APP_UUID) return
        val values = parse(intent.getStringExtra("msg_data") ?: return) ?: return

        when (values[KEY_CMD]) {
            "entry" -> {
                val id = values[KEY_ID] as? String ?: return
                val ts = (values[KEY_TIME] as? Number)?.toLong() ?: return
                Reminders.count(context, ts, SOURCE, announce = true, id = id)
                reply(context, "ack", id)
            }
            "hello" -> reply(context, "state", null)
            "measure" -> {
                val id = values[KEY_ID] as? String ?: return
                val phase = values[KEY_PHASE] as? String ?: return
                fun num(key: Int) = (values[key] as? Number)?.toInt() ?: 0
                val ts = (values[KEY_TIME] as? Number)?.toLong() ?: return
                EntryStore.get(context).addMeasurement(id, phase, ts, num(KEY_HR), num(KEY_SPO2), num(KEY_STRESS))
                replyMeasured(context, id, phase)
            }
        }
    }

    private fun reply(context: Context, cmd: String, id: String?) {
        val counter = Counter(Settings.load(context))
        val entries = EntryStore.get(context).entries.value
        val today = counter.onDay(entries, counter.today())
        val dict = JSONArray()
        dict.put(item(KEY_CMD, cmd))
        if (id != null) dict.put(item(KEY_ID, id))
        dict.put(item(KEY_TODAY, today.size))
        dict.put(item(KEY_LAST, today.maxOrNull() ?: 0L))
        dict.put(item(KEY_NEXT, counter.allowedFrom(entries) ?: 0L))

        context.sendBroadcast(Intent(ACTION_SEND).apply {
            putExtra("uuid", APP_UUID)
            putExtra("transaction_id", -1)
            putExtra("msg_data", dict.toString())
        })
    }

    private fun replyMeasured(context: Context, id: String, phase: String) {
        val dict = JSONArray().put(item(KEY_CMD, "mack")).put(item(KEY_ID, id)).put(item(KEY_PHASE, phase))
        context.sendBroadcast(Intent(ACTION_SEND).apply {
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
        /** Messung: "before" / "after", Puls, Blutsauerstoff (%), Stress; 0 = nicht gemessen */
        const val KEY_PHASE = 6
        const val KEY_HR = 7
        const val KEY_SPO2 = 8
        const val KEY_STRESS = 9
    }
}
