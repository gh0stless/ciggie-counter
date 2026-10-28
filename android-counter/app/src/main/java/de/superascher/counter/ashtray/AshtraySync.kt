package de.superascher.counter.ashtray

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import de.superascher.counter.R
import de.superascher.counter.data.AppState
import de.superascher.counter.reminder.CalendarSummary
import de.superascher.counter.reminder.Reminders
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

/**
 * Optional: Zigaretten vom Butt Bin (Superascher) übernehmen. Gleiche Buchführung wie die Bridge-App
 * (android/): Ereignisnummer erst nach dem Speichern weiterzählen, Ereignisse ohne Uhrzeit verwerfen,
 * beim ersten Abgleich keine alten Ereignisse übernehmen.
 */
object AshtraySync {
    private val lock = Mutex()

    suspend fun sync(context: Context): String = lock.withLock {
        val state = AppState(context)
        val address = state.ashtrayAddress ?: return context.getString(R.string.ashtray_none_paired)
        val status = try {
            if (context.checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) {
                context.getString(R.string.bt_permission_missing)
            } else {
                withContext(Dispatchers.IO) { syncNow(context, state, address) }
            }
        } catch (e: Exception) {
            context.getString(R.string.error, e.message ?: e.javaClass.simpleName)
        }
        state.ashtrayLastSync = System.currentTimeMillis()
        state.ashtrayStatus = status
        status
    }

    private suspend fun syncNow(context: Context, state: AppState, address: String): String {
        var first = false
        val result = AshtrayBle.sync(context, address) { count ->
            when {
                state.ashtrayNextSeq < 0 -> { first = true; count }
                count < state.ashtrayNextSeq -> 0 // Ascher zurückgesetzt
                else -> state.ashtrayNextSeq
            }
        }
        if (first) {
            state.ashtrayNextSeq = result.count
            return context.getString(R.string.ashtray_first_sync)
        }
        if (result.count < state.ashtrayNextSeq) state.ashtrayNextSeq = 0

        var added = 0
        var dropped = 0
        for (event in result.events.sortedBy { it.seq }) {
            if (event.seq < state.ashtrayNextSeq) continue
            val time = event.unixTime
            if (time == null) dropped++ else {
                Reminders.count(context, time, "ashtray")
                added++
            }
            state.ashtrayNextSeq = event.seq + 1
        }
        state.ashtrayNextSeq = maxOf(state.ashtrayNextSeq, result.count)
        return buildString {
            val res = context.resources
            append(if (added == 0) context.getString(R.string.ashtray_nothing_new) else res.getQuantityString(R.plurals.ashtray_added, added, added))
            if (dropped > 0) append(res.getQuantityString(R.plurals.ashtray_dropped, dropped, dropped))
        }
    }
}

/** Stündlich: Kalender-Zusammenfassung; alle 15 Minuten: Butt Bin (falls gekoppelt). */
class AshtrayWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        AshtraySync.sync(applicationContext)
        Presence.register(applicationContext) // Android verwirft den Scan z. B. bei Bluetooth aus/an
        return Result.success()
    }
}

class CalendarWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        runCatching { CalendarSummary.sync(applicationContext) }
        return Result.success()
    }
}

object Background {
    fun schedule(context: Context) {
        val wm = WorkManager.getInstance(context)
        wm.enqueueUniquePeriodicWork(
            "calendar", ExistingPeriodicWorkPolicy.KEEP,
            PeriodicWorkRequestBuilder<CalendarWorker>(1, TimeUnit.HOURS).build(),
        )
        if (AppState(context).ashtrayAddress != null) {
            wm.enqueueUniquePeriodicWork(
                "ashtray", ExistingPeriodicWorkPolicy.KEEP,
                PeriodicWorkRequestBuilder<AshtrayWorker>(15, TimeUnit.MINUTES).build(),
            )
        } else {
            wm.cancelUniqueWork("ashtray")
        }
        Presence.register(context)
        if (de.superascher.counter.data.Settings.load(context).ncEnabled) {
            de.superascher.counter.sync.Nextcloud.kick(context)
        }
    }
}
