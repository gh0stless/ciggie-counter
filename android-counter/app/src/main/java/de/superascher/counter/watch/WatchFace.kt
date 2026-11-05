package de.superascher.counter.watch

import android.content.Context
import android.content.Intent
import de.superascher.counter.data.AppState
import de.superascher.counter.data.EntryStore
import de.superascher.counter.data.Settings
import de.superascher.counter.logic.Counter
import org.json.JSONObject

/**
 * Stand fürs Ciggie-Counter-Ziffernblatt über den Wetter-Kanal von Gadgetbridge
 * ([Settings.watchfaceWeather]). Die Band-App erreicht das Handy nur, solange sie offen ist;
 * Wetter dagegen gibt Gadgetbridge jederzeit ans Band weiter, den Ortsnamen sofort.
 * Ortsname: "CC|Zähltag (JJJJMMTT)|heute|letzte|nächste|Zeitpunkt|Tageswechsel-Stunde",
 * Zeiten in Unix-Sekunden.
 * Das Ziffernblatt nimmt den neueren Stand von Wetter und Band-App (watchface/README.md).
 */
object WatchFace {
    private const val ACTION_WEATHER = "nodomain.freeyourgadget.gadgetbridge.ACTION_GENERIC_WEATHER"

    /**
     * Nach jeder Änderung aufrufen; sendet nur, wenn sich der Stand geändert hat.
     * [force]: trotzdem senden (Schalter eingeschaltet, App geöffnet: Gadgetbridge oder das Band
     * können den Stand inzwischen verloren haben).
     */
    fun push(context: Context, force: Boolean = false) {
        val settings = Settings.load(context)
        if (!settings.watchfaceWeather) return
        val counter = Counter(settings)
        val entries = EntryStore.get(context).entries.value
        val today = counter.onDay(entries, counter.today())
        // Zähltag der App (Tageswechsel-Stunde geht mit, Band und Ziffernblatt rechnen genauso)
        val day = counter.today().let { it.year * 10000 + it.monthValue * 100 + it.dayOfMonth }
        val counts = listOf(day, today.size, today.maxOrNull() ?: 0L, counter.allowedFrom(entries) ?: 0L).joinToString("|")
        val state = "$counts|${settings.dayStartHour}"

        val appState = AppState(context)
        if (!force && state == appState.watchfaceSent) return
        val now = Counter.nowSeconds()
        val weather = JSONObject()
            .put("timestamp", now)
            .put("location", "CC|$counts|$now|${settings.dayStartHour}")
            // die Wetter-App des Bandes zeigt so wenigstens die Tagesmenge als Temperatur
            .put("currentTemp", 273 + today.size)
            .put("todayMinTemp", 273)
            .put("todayMaxTemp", 273 + today.size)
            .put("currentCondition", "Ciggie Counter")
        val intent = Intent(ACTION_WEATHER).putExtra("WeatherJson", weather.toString())
        // Android 8+: Manifest-Empfänger nur gezielt erreichbar, also an jeden Gadgetbridge einzeln
        val receivers = context.packageManager.queryBroadcastReceivers(intent, 0)
        for (r in receivers) {
            context.sendBroadcast(Intent(intent).setClassName(r.activityInfo.packageName, r.activityInfo.name))
        }
        if (receivers.isNotEmpty()) appState.watchfaceSent = state
    }
}
