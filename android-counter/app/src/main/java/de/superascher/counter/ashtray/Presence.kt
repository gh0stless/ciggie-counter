package de.superascher.counter.ashtray

import android.Manifest
import android.annotation.SuppressLint
import android.app.AlarmManager
import android.app.PendingIntent
import android.bluetooth.BluetoothManager
import android.bluetooth.le.BluetoothLeScanner
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.ParcelUuid
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.OutOfQuotaPolicy
import androidx.work.WorkManager
import de.superascher.counter.data.AppState
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Sofort-Abgleich: Android filtert im Bluetooth-Chip auf die Superascher-UUID und weckt die App,
 * sobald der Ascher wirbt, auch wenn sie nicht läuft. Nach einem Stempeldruck wirbt der Ascher
 * 30 s lang schnell (Firmware app_adv.c), der Zählerstand steht in den Manufacturer Data.
 * Ist er höher als der eigene Stand, startet sofort ein Abgleich.
 *
 * Android verwirft den Scan bei Neustart und Bluetooth aus/an und stuft ihn nach rund 30 Minuten
 * herunter ("downgraded scan", dann kommen kaum noch Treffer). Deshalb erneuert ein genauer Wecker
 * ihn alle 20 Minuten; der 15-Minuten-Takt von [AshtrayWorker] wird im Ruhemodus zu oft verschoben.
 */
@SuppressLint("MissingPermission") // Berechtigungen werden in register() geprüft
object Presence {
    /** Company ID 0xFFFF (Test-ID) aus der Firmware, danach u32 Zählerstand little endian */
    private const val COMPANY_ID = 0xFFFF

    const val ACTION_REFRESH = "de.superascher.counter.SCAN_REFRESH"
    private const val REFRESH_MS = 20 * 60_000L

    fun register(context: Context) {
        if (AppState(context).ashtrayAddress == null) return unregister(context)
        if (context.checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN) != PackageManager.PERMISSION_GRANTED) return
        scheduleRefresh(context)
        val scanner = scanner(context) ?: return
        val pi = pendingIntent(context)
        runCatching { scanner.stopScan(pi) } // keine doppelten Registrierungen
        val filter = ScanFilter.Builder().setServiceUuid(ParcelUuid(AshtrayBle.SERVICE)).build()
        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_POWER)
            .setCallbackType(ScanSettings.CALLBACK_TYPE_ALL_MATCHES)
            .build()
        runCatching { scanner.startScan(listOf(filter), settings, pi) }
    }

    fun unregister(context: Context) {
        context.getSystemService(AlarmManager::class.java).cancel(refreshIntent(context))
        if (context.checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN) != PackageManager.PERMISSION_GRANTED) return
        runCatching { scanner(context)?.stopScan(pendingIntent(context)) }
    }

    /** Zählerstand aus dem Werbepaket, null wenn nicht enthalten. */
    fun countOf(result: ScanResult): Long? {
        val data = result.scanRecord?.getManufacturerSpecificData(COMPANY_ID) ?: return null
        if (data.size < 4) return null
        return ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN).int.toLong() and 0xFFFFFFFFL
    }

    private fun scheduleRefresh(context: Context) {
        val am = context.getSystemService(AlarmManager::class.java)
        val at = System.currentTimeMillis() + REFRESH_MS
        if (am.canScheduleExactAlarms()) {
            am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, refreshIntent(context))
        } else {
            am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, refreshIntent(context))
        }
    }

    private fun refreshIntent(context: Context): PendingIntent = PendingIntent.getBroadcast(
        context, ACTION_REFRESH.hashCode(),
        Intent(context, de.superascher.counter.reminder.ReminderReceiver::class.java).setAction(ACTION_REFRESH),
        PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
    )

    private fun scanner(context: Context): BluetoothLeScanner? =
        context.getSystemService(BluetoothManager::class.java).adapter?.bluetoothLeScanner

    // FLAG_MUTABLE: Android hängt die Scan-Ergebnisse als Extras an
    private fun pendingIntent(context: Context): PendingIntent = PendingIntent.getBroadcast(
        context, 0, Intent(context, PresenceReceiver::class.java),
        PendingIntent.FLAG_MUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
    )

    /** Abgleich sofort anstoßen; läuft schon einer, kommt kein zweiter dazu. */
    fun syncNow(context: Context) {
        WorkManager.getInstance(context).enqueueUniqueWork(
            "ashtray-now", ExistingWorkPolicy.KEEP,
            OneTimeWorkRequestBuilder<AshtrayWorker>()
                .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
                .build(),
        )
    }
}

/** Empfängt die Treffer des Hintergrund-Scans. */
class PresenceReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val results = intent.getParcelableArrayListExtra(
            BluetoothLeScanner.EXTRA_LIST_SCAN_RESULT, ScanResult::class.java,
        ) ?: return
        val state = AppState(context)
        val address = state.ashtrayAddress ?: return
        val newest = results.filter { it.device.address == address }.mapNotNull { Presence.countOf(it) }.maxOrNull()
            ?: return
        if (newest <= state.ashtrayNextSeq) return
        // Sofort nur bei neuem Zählerstand; scheitert der Abgleich, nicht bei jedem
        // Werbepaket (1/s) erneut, sondern höchstens alle 5 Minuten
        val now = System.currentTimeMillis()
        if (newest > state.ashtrayTriggerCount || now - state.ashtrayTriggerAt > 5 * 60_000) {
            state.ashtrayTriggerCount = newest
            state.ashtrayTriggerAt = now
            Presence.syncNow(context)
        }
    }
}
