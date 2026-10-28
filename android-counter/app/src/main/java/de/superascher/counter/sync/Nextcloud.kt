package de.superascher.counter.sync

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
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
            OneTimeWorkRequestBuilder<NextcloudWorker>().setConstraints(network).build(),
        )
        wm.enqueueUniquePeriodicWork(
            "nextcloud", ExistingPeriodicWorkPolicy.KEEP,
            PeriodicWorkRequestBuilder<NextcloudWorker>(15, TimeUnit.MINUTES).setConstraints(network).build(),
        )
    }

    /** Ausstehende Änderungen senden (bricht beim ersten Fehler ab, Reihenfolge bleibt), dann Stand holen. */
    fun sync(context: Context): String {
        val settings = Settings.load(context)
        if (!settings.ncEnabled) return context.getString(R.string.nc_not_configured)
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

    /** Zugangsdaten prüfen (GET /api/today). */
    fun test(context: Context, settings: Settings) {
        request(context, settings, "GET", "/api/today", null)
    }

    private fun enc(s: String) = URLEncoder.encode(s, "UTF-8").replace("+", "%20")

    private fun request(context: Context, settings: Settings, method: String, path: String, body: String?): String {
        // index.php im Pfad funktioniert auch ohne "hübsche" URLs
        val url = URL(settings.ncUrl.trimEnd('/') + "/index.php/apps/cigarettecounter" + path)
        val auth = Base64.getEncoder().encodeToString("${settings.ncUser}:${settings.ncAppPassword}".toByteArray())
        val conn = url.openConnection() as HttpURLConnection
        try {
            conn.requestMethod = method
            conn.connectTimeout = 10_000
            conn.readTimeout = 15_000
            conn.instanceFollowRedirects = false // Umleitung zur Login-Seite = Anmeldung fehlgeschlagen
            conn.setRequestProperty("Authorization", "Basic $auth")
            conn.setRequestProperty("Accept", "application/json")
            conn.setRequestProperty("OCS-APIRequest", "true") // sonst verlangt Nextcloud ein CSRF-Token (HTTP 412)
            if (body != null) {
                conn.doOutput = true
                conn.setRequestProperty("Content-Type", "application/x-www-form-urlencoded")
                conn.outputStream.use { it.write(body.toByteArray()) }
            }
            return when (val code = conn.responseCode) {
                200 -> conn.inputStream.bufferedReader().use { it.readText() }
                401 -> throw IOException(context.getString(R.string.nc_auth_rejected))
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
