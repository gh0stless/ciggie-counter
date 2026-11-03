package de.superascher.counter.sync

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.OutOfQuotaPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import de.superascher.counter.R
import de.superascher.counter.data.AppState
import de.superascher.counter.data.EntryStore
import de.superascher.counter.data.Settings
import de.superascher.counter.reminder.Reminders
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.time.Instant
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Base64
import java.util.concurrent.TimeUnit

/**
 * Optionale eigene Nextcloud mit der App "cigarettecounter" (nextcloud-app/PROJEKT.md §5).
 *
 * Senden: jedes Hinzufügen/Löschen geht über die Warteschlange (EntryStore.outbox) an den Server.
 * Holen (ab Server-App 0.9.3, GET /api/entries): danach übernimmt das Gerät die komplette Liste
 * vom Server, so sehen mehrere Geräte (z. B. Handy und Tablet) denselben Stand.
 * Ältere Server ohne diese Schnittstelle: nur Senden.
 */
object Nextcloud {
    /** Wie PHP format('c') in der Nextcloud-App: Löschen funktioniert nur mit genau diesem Text. */
    private val ISO = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssxxx")

    private class NotFound : IOException("nicht gefunden")

    fun isoOf(ts: Long): String = ISO.format(Instant.ofEpochSecond(ts).atZone(ZoneId.systemDefault()))

    /** Abgleich anstoßen (sofort, sobald Netz da ist) und den 15-Minuten-Takt sicherstellen. */
    fun kick(context: Context) {
        val network = Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()
        val wm = WorkManager.getInstance(context)
        wm.enqueueUniqueWork(
            "nextcloud-now", ExistingWorkPolicy.APPEND_OR_REPLACE,
            // expedited: im Ruhemodus nicht minutenlang aufschieben (sonst kommt z. B. die
            // "Alle gezählt?"-Erinnerung vom Server, obwohl schon gezählt wurde)
            OneTimeWorkRequestBuilder<NextcloudWorker>().setConstraints(network)
                .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST).build(),
        )
        wm.enqueueUniquePeriodicWork(
            "nextcloud", ExistingPeriodicWorkPolicy.KEEP,
            PeriodicWorkRequestBuilder<NextcloudWorker>(15, TimeUnit.MINUTES).setConstraints(network).build(),
        )
    }

    /** Abgleich: v2 (IDs, nur Änderungen) ab Server-App 0.9.11, sonst der alte Weg. */
    fun sync(context: Context): String {
        val settings = Settings.load(context)
        if (!settings.syncEnabled) return context.getString(R.string.nc_not_configured)
        syncDeviceState(context, settings)
        syncRules(context, settings)
        return syncV2(context, settings)
            ?: if (settings.syncTarget == Settings.SYNC_HOME_ASSISTANT) throw IOException(context.getString(R.string.ha_integration_missing))
            else syncLegacy(context, settings)
    }

    private class V2(val rev: Long, val records: List<EntryStore.Record>)

    private fun getV2(context: Context, settings: Settings, since: Long): V2? {
        val json = try {
            JSONObject(request(context, settings, "GET", "/api/v2/entries?since=$since", null))
        } catch (e: NotFound) {
            return null
        }
        val arr = json.getJSONArray("entries")
        return V2(json.getLong("rev"), List(arr.length()) {
            val o = arr.getJSONObject(it)
            EntryStore.Record(
                o.getString("id"), OffsetDateTime.parse(o.getString("ts")).toEpochSecond(),
                o.optString("source", "server"), o.optBoolean("deleted"),
            )
        })
    }

    /** null = Server kennt v2 nicht (ältere Nextcloud-App) */
    private fun syncV2(context: Context, settings: Settings): String? {
        val store = EntryStore.get(context)
        val state = AppState(context)
        val res = context.resources
        var sent = 0
        if (state.syncRev < 0) {
            // Umstieg: Server muss v2 können, sonst alter Weg
            getV2(context, settings, 0) ?: return null
            // noch Ungesendetes aus der alten Warteschlange vorher abliefern, dann Server-Stand mit IDs übernehmen
            sent = flushLegacyOutbox(context, settings, store)
            val all = getV2(context, settings, 0) ?: return null
            store.replaceAllFromServer(all.records)
            state.syncRev = all.rev
        } else {
            val dirty = store.dirtyRecords()
            if (dirty.isNotEmpty()) {
                val body = JSONObject().put("entries", JSONArray().apply {
                    dirty.forEach {
                        put(JSONObject().put("id", it.id).put("ts", isoOf(it.ts)).put("source", it.source).put("deleted", it.deleted))
                    }
                })
                try {
                    request(context, settings, "POST", "/api/v2/entries", body.toString(), json = true)
                } catch (e: NotFound) {
                    return null
                }
                store.markClean(dirty.map { it.id })
                sent = dirty.size
            }
            val changes = getV2(context, settings, state.syncRev) ?: return null
            store.mergeFromServer(changes.records)
            state.syncRev = changes.rev
        }
        store.clearOps() // im v2-Betrieb erledigt
        Reminders.reschedule(context)
        val total = store.entries.value.size
        return buildString {
            if (sent > 0) append(res.getQuantityString(R.plurals.nc_sent, sent, sent) + ", ")
            append(res.getQuantityString(R.plurals.nc_from_server, total, total))
        }
    }

    private fun flushLegacyOutbox(context: Context, settings: Settings, store: EntryStore): Int {
        var sent = 0
        while (true) {
            val op = store.pendingOps().firstOrNull() ?: break
            try {
                if (op.op == "add") request(context, settings, "POST", "/api/add", "timestamp=" + enc(isoOf(op.ts)))
                else request(context, settings, "DELETE", "/api/entries/" + enc(isoOf(op.ts)), null)
            } catch (e: NotFound) {
                throw IOException(context.getString(R.string.nc_app_missing))
            }
            store.removeOp(op.id)
            sent++
        }
        return sent
    }

    /**
     * Regeln (Settings.sameRules) abgleichen, mit Nextcloud ab Server-App 0.11.0 bzw. der
     * HA-Integration ab 0.3.0: die jüngste Änderung gilt. Ältere Server: nichts tun.
     */
    private fun syncRules(context: Context, settings: Settings) {
        val server = try {
            JSONObject(request(context, settings, "GET", "/api/v2/settings", null))
        } catch (e: NotFound) {
            return
        }
        val serverAt = server.optLong("updatedAt")
        if (serverAt > settings.rulesUpdatedAt) {
            fun double(key: String) = if (server.isNull(key)) null else server.getDouble(key)
            fun int(key: String) = if (server.isNull(key)) null else server.getInt(key)
            Settings.save(context, settings.copy(
                costPerCigarette = double("costPerCigarette"),
                dayStartHour = int("dayStartHour") ?: 0,
                intervalMode = server.optString("intervalMode", "computed"),
                dailyTarget = int("dailyTarget"),
                wakeHours = double("wakeHours") ?: 18.0,
                fixedIntervalMinutes = int("fixedIntervalMinutes"),
                countCheckMinutes = int("countCheckIntervalMinutes") ?: 10,
                rulesUpdatedAt = serverAt,
            ))
            Reminders.reschedule(context)
        } else if (settings.rulesUpdatedAt > serverAt) {
            val body = JSONObject()
                .put("updatedAt", settings.rulesUpdatedAt)
                .put("costPerCigarette", settings.costPerCigarette ?: JSONObject.NULL)
                .put("dayStartHour", settings.dayStartHour)
                .put("intervalMode", settings.intervalMode)
                .put("dailyTarget", settings.dailyTarget ?: JSONObject.NULL)
                .put("wakeHours", settings.wakeHours)
                .put("fixedIntervalMinutes", settings.fixedIntervalMinutes ?: JSONObject.NULL)
                .put("countCheckIntervalMinutes", settings.countCheckMinutes)
            request(context, settings, "POST", "/api/v2/settings", body.toString(), json = true)
        }
    }

    /** Batterie des Butt Bin melden, Stumm-Schalter holen (ab Server-App 0.9.10). */
    private fun syncDeviceState(context: Context, settings: Settings) {
        val state = AppState(context)
        if (state.ashtrayBattery >= 0 && state.ashtrayBatteryAt > state.ashtrayBatterySentAt) {
            val at = state.ashtrayBatteryAt
            runCatching {
                request(context, settings, "POST", "/api/ashtray", "battery=${state.ashtrayBattery}&at=" + enc(isoOf(at / 1000)))
                state.ashtrayBatterySentAt = at
            }
        }
        runCatching { state.muted = JSONObject(request(context, settings, "GET", "/api/mute", null)).getBoolean("muted") }
    }

    /** Alter Weg (Server-App vor 0.9.11): Warteschlange senden, dann komplette Liste übernehmen. */
    private fun syncLegacy(context: Context, settings: Settings): String {
        val store = EntryStore.get(context)
        var sent = 0
        while (true) {
            val op = store.pendingOps().firstOrNull() ?: break
            try {
                if (op.op == "add") request(context, settings, "POST", "/api/add", "timestamp=" + enc(isoOf(op.ts)))
                else request(context, settings, "DELETE", "/api/entries/" + enc(isoOf(op.ts)), null)
            } catch (e: NotFound) {
                throw IOException(context.getString(R.string.nc_app_missing))
            }
            store.removeOp(op.id)
            sent++
        }

        val server = try {
            JSONObject(request(context, settings, "GET", "/api/entries", null)).getJSONArray("entries")
        } catch (e: NotFound) {
            return if (sent == 0) context.getString(R.string.nc_all_sent) else context.resources.getQuantityString(R.plurals.nc_sent, sent, sent)
        }
        val list = List(server.length()) { OffsetDateTime.parse(server.getString(it)).toEpochSecond() }
        store.replaceFromServer(list)
        Reminders.reschedule(context)
        val res = context.resources
        return buildString {
            if (sent > 0) append(res.getQuantityString(R.plurals.nc_sent, sent, sent) + ", ")
            append(res.getQuantityString(R.plurals.nc_from_server, list.size, list.size))
        }
    }

    /**
     * Aktueller Stumm-Zustand direkt vom Server (kurzer Timeout, für den Moment einer Erinnerung).
     * Ohne Nextcloud oder ohne Netz gilt der zuletzt bekannte Stand.
     */
    fun currentMuted(context: Context): Boolean {
        val settings = Settings.load(context)
        val state = AppState(context)
        if (settings.syncEnabled) {
            runCatching {
                state.muted = JSONObject(request(context, settings, "GET", "/api/mute", null, timeoutMs = 3_000)).getBoolean("muted")
            }
        }
        return state.muted
    }

    /** Stumm-Schalter in der App: lokal sofort, an Nextcloud im Hintergrund (nicht im UI-Thread aufrufen). */
    fun setMuted(context: Context, muted: Boolean) {
        AppState(context).muted = muted
        val settings = Settings.load(context)
        val body = "muted=" + if (muted) "1" else "0"
        if (settings.syncEnabled) runCatching { request(context, settings, "POST", "/api/mute", body) }
        if (settings.haNotifyEnabled) runCatching { request(context, settings.asHomeAssistant(), "POST", "/api/mute", body) }
    }

    /**
     * Zusätzlich zu Nextcloud: neue Einträge und Löschmarken sofort an Home Assistant, damit die
     * Integration gleich ansagt und ihre Erinnerungen neu rechnet, statt erst nach ihrem Abgleich.
     * Nur Senden; den Stand holt das Gerät weiter von Nextcloud.
     */
    fun notifyHomeAssistant(context: Context): String {
        val settings = Settings.load(context)
        if (!settings.haNotifyEnabled) return ""
        val store = EntryStore.get(context)
        val dirty = store.haDirtyRecords()
        if (dirty.isEmpty()) return context.getString(R.string.nc_all_sent)
        val body = JSONObject().put("entries", JSONArray().apply {
            dirty.forEach {
                put(JSONObject().put("id", it.id).put("ts", isoOf(it.ts)).put("source", it.source).put("deleted", it.deleted))
            }
        })
        try {
            request(context, settings.asHomeAssistant(), "POST", "/api/v2/entries", body.toString(), json = true)
        } catch (e: NotFound) {
            throw IOException(context.getString(R.string.ha_integration_missing))
        }
        store.markHaClean(dirty)
        return context.resources.getQuantityString(R.plurals.nc_sent, dirty.size, dirty.size)
    }

    fun kickHomeAssistant(context: Context) {
        val network = Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()
        WorkManager.getInstance(context).enqueueUniqueWork(
            "homeassistant-now", ExistingWorkPolicy.APPEND_OR_REPLACE,
            OneTimeWorkRequestBuilder<HomeAssistantWorker>().setConstraints(network)
                .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST).build(),
        )
    }

    private fun Settings.asHomeAssistant() = copy(syncTarget = Settings.SYNC_HOME_ASSISTANT)

    /** Zugangsdaten prüfen (GET /api/today). */
    fun test(context: Context, settings: Settings) {
        request(context, settings, "GET", "/api/today", null)
    }

    private fun enc(s: String) = URLEncoder.encode(s, "UTF-8").replace("+", "%20")

    private fun request(
        context: Context, settings: Settings, method: String, path: String, body: String?, timeoutMs: Int = 0,
        json: Boolean = false,
    ): String {
        val ha = settings.syncTarget == Settings.SYNC_HOME_ASSISTANT
        // Gleiche Schnittstelle, andere Adresse: Nextcloud /index.php/apps/cigarettecounter/api/…,
        // Home Assistant /api/ciggie_counter/… (index.php funktioniert auch ohne "hübsche" URLs)
        val url = if (ha) URL(settings.haUrl.trimEnd('/') + "/api/ciggie_counter" + path.removePrefix("/api"))
        else URL(settings.ncUrl.trimEnd('/') + "/index.php/apps/cigarettecounter" + path)
        val auth = if (ha) "Bearer ${settings.haToken}"
        else "Basic " + Base64.getEncoder().encodeToString("${settings.ncUser}:${settings.ncAppPassword}".toByteArray())
        val conn = url.openConnection() as HttpURLConnection
        try {
            conn.requestMethod = method
            conn.connectTimeout = if (timeoutMs > 0) timeoutMs else 10_000
            conn.readTimeout = if (timeoutMs > 0) timeoutMs else 15_000
            conn.instanceFollowRedirects = false // Umleitung zur Login-Seite = Anmeldung fehlgeschlagen
            conn.setRequestProperty("Authorization", auth)
            conn.setRequestProperty("Accept", "application/json")
            conn.setRequestProperty("OCS-APIRequest", "true") // sonst verlangt Nextcloud ein CSRF-Token (HTTP 412)
            if (body != null) {
                conn.doOutput = true
                conn.setRequestProperty("Content-Type", if (json) "application/json" else "application/x-www-form-urlencoded")
                conn.outputStream.use { it.write(body.toByteArray()) }
            }
            return when (val code = conn.responseCode) {
                200 -> conn.inputStream.bufferedReader().use { it.readText() }
                401 -> throw IOException(context.getString(if (ha) R.string.ha_auth_rejected else R.string.nc_auth_rejected))
                404 -> throw NotFound()
                else -> throw IOException(context.getString(R.string.nc_http, code))
            }
        } finally {
            conn.disconnect()
        }
    }
}

class NextcloudWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val state = AppState(applicationContext)
        state.ncStatus = try {
            withContext(Dispatchers.IO) { Nextcloud.sync(applicationContext) }
        } catch (e: Exception) {
            applicationContext.getString(R.string.nc_retry, e.message ?: e.javaClass.simpleName)
        }
        state.ncLastSync = System.currentTimeMillis()
        return Result.success()
    }
}

/** Zusätzliche Meldung an Home Assistant; ohne Erfolg ein paar neue Versuche, danach kommt es über Nextcloud an. */
class HomeAssistantWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val state = AppState(applicationContext)
        state.haLastNotify = System.currentTimeMillis()
        return try {
            state.haNotifyStatus = withContext(Dispatchers.IO) { Nextcloud.notifyHomeAssistant(applicationContext) }
            Result.success()
        } catch (e: Exception) {
            state.haNotifyStatus = applicationContext.getString(R.string.nc_retry, e.message ?: e.javaClass.simpleName)
            if (runAttemptCount < 3) Result.retry() else Result.success()
        }
    }
}
