package de.superascher.counter.ashtray

import android.annotation.SuppressLint
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.os.ParcelUuid
import de.superascher.counter.R
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.withTimeout
import kotlinx.coroutines.withTimeoutOrNull
import java.io.IOException
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.UUID

/**
 * GATT-Client für den Butt Bin (Superascher, Firmware firmware/superascher, Profil siehe hardware-handover.md).
 * Ablauf wie firmware/tools/iashtray_sync.py: verbinden, Uhr stellen, Ereignisse ab Startnummer holen.
 */
@SuppressLint("MissingPermission") // Berechtigungen prüft der Aufrufer
object AshtrayBle {
    val SERVICE: UUID = UUID.fromString("15770001-0f39-460f-8588-44afa8137b74")
    private val COUNT: UUID = UUID.fromString("15770002-0f39-460f-8588-44afa8137b74")
    private val TIME: UUID = UUID.fromString("15770003-0f39-460f-8588-44afa8137b74")
    private val EVENTS: UUID = UUID.fromString("15770004-0f39-460f-8588-44afa8137b74")
    private val CCC: UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")
    private const val SEQ_TIME_UNKNOWN = 0x80000000L

    /** Ein Stempeldruck. [unixTime] = null: Zeit unbekannt (Uhr war nicht gestellt). */
    data class Event(val seq: Long, val unixTime: Long?)

    data class Result(val count: Long, val events: List<Event>)

    /** Sucht den Ascher anhand der Service-UUID, liefert seine Adresse oder null. */
    suspend fun scan(context: Context, timeoutMs: Long = 10_000): String? {
        val scanner = context.getSystemService(BluetoothManager::class.java).adapter?.bluetoothLeScanner
            ?: throw IOException(context.getString(R.string.bt_off))
        val found = CompletableDeferred<String>()
        val callback = object : ScanCallback() {
            override fun onScanResult(callbackType: Int, result: ScanResult) {
                found.complete(result.device.address)
            }

            override fun onScanFailed(errorCode: Int) {
                found.completeExceptionally(IOException(context.getString(R.string.bt_scan_failed, errorCode)))
            }
        }
        val filter = ScanFilter.Builder().setServiceUuid(ParcelUuid(SERVICE)).build()
        val settings = ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build()
        scanner.startScan(listOf(filter), settings, callback)
        try {
            return withTimeoutOrNull(timeoutMs) { found.await() }
        } finally {
            scanner.stopScan(callback)
        }
    }

    /**
     * Verbindet, stellt die Uhr und holt die Ereignisse.
     * [fromSeq] bekommt den Zählerstand des Geräts und liefert die gewünschte Startnummer.
     */
    suspend fun sync(context: Context, address: String, fromSeq: (count: Long) -> Long): Result =
        withTimeout(45_000) {
            val adapter = context.getSystemService(BluetoothManager::class.java).adapter
                ?: throw IOException(context.getString(R.string.bt_missing))
            val link = Link(context)
            val gatt = adapter.getRemoteDevice(address)
                .connectGatt(context, false, link, BluetoothDevice.TRANSPORT_LE)
            try {
                link.connected.await()
                link.step("Dienstsuche") { gatt.discoverServices() }
                val service = gatt.getService(SERVICE) ?: throw IOException(context.getString(R.string.bt_no_service))
                fun ch(uuid: UUID) = service.getCharacteristic(uuid) ?: throw IOException("Characteristic $uuid fehlt")

                val count = u32(link.step("Count lesen") { gatt.readCharacteristic(ch(COUNT)) })
                val now = le32(System.currentTimeMillis() / 1000)
                link.step("Uhr stellen") { gatt.writeCharacteristic(ch(TIME), now, WRITE) == WRITE_OK }

                val events = ch(EVENTS)
                gatt.setCharacteristicNotification(events, true)
                val ccc = events.getDescriptor(CCC) ?: throw IOException("CCC fehlt")
                link.step("Events abonnieren") {
                    gatt.writeDescriptor(ccc, BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE) == WRITE_OK
                }
                val from = le32(fromSeq(count))
                link.step("Abgleich anfordern") { gatt.writeCharacteristic(events, from, WRITE) == WRITE_OK }

                val list = mutableListOf<Event>()
                while (true) {
                    val data = link.notifications.receive()
                    if (data.size == 4) break // Endemarke = Gesamtzahl
                    val buf = ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN)
                    while (buf.remaining() >= 8) {
                        val seq = buf.int.toLong() and 0xFFFFFFFFL
                        val time = buf.int.toLong() and 0xFFFFFFFFL
                        list += if (seq and SEQ_TIME_UNKNOWN != 0L) Event(seq and SEQ_TIME_UNKNOWN.inv(), null)
                        else Event(seq, time)
                    }
                }
                Result(count, list)
            } finally {
                gatt.disconnect()
                gatt.close()
            }
        }

    private const val OK = BluetoothGatt.GATT_SUCCESS
    private const val WRITE = BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
    /** Rückgabe von writeCharacteristic/writeDescriptor (API 33) */
    private const val WRITE_OK = android.bluetooth.BluetoothStatusCodes.SUCCESS

    /** Wandelt die Callbacks in nacheinander abwartbare Schritte (GATT erlaubt nur eine Operation gleichzeitig). */
    private class Link(private val context: Context) : BluetoothGattCallback() {
        val connected = CompletableDeferred<Unit>()
        val notifications = Channel<ByteArray>(Channel.UNLIMITED)
        private var pending: CompletableDeferred<Pair<Int, ByteArray?>>? = null
        private var lost: IOException? = null

        /** Wartet erst vorbereiten, dann Operation starten, dann auf den Callback warten. */
        suspend fun step(what: String, start: () -> Boolean): ByteArray {
            val result = CompletableDeferred<Pair<Int, ByteArray?>>()
            synchronized(this) {
                lost?.let { throw it }
                pending = result
            }
            if (!start()) throw IOException("$what nicht gestartet")
            val (status, value) = result.await()
            if (status != OK) throw IOException("$what fehlgeschlagen (Status $status)")
            return value ?: ByteArray(0)
        }

        @Synchronized
        private fun done(status: Int, value: ByteArray?) {
            pending?.complete(status to value)
            pending = null
        }

        override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
            if (newState == BluetoothProfile.STATE_CONNECTED && status == OK) {
                connected.complete(Unit)
                return
            }
            val e = IOException(context.getString(R.string.bt_disconnected, status))
            synchronized(this) {
                lost = e
                pending?.completeExceptionally(e)
            }
            connected.completeExceptionally(e)
            notifications.close(e)
        }

        override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) = done(status, null)

        override fun onCharacteristicRead(g: BluetoothGatt, c: BluetoothGattCharacteristic, value: ByteArray, status: Int) =
            done(status, value)

        override fun onCharacteristicWrite(g: BluetoothGatt, c: BluetoothGattCharacteristic, status: Int) =
            done(status, null)

        override fun onDescriptorWrite(g: BluetoothGatt, d: BluetoothGattDescriptor, status: Int) =
            done(status, null)

        override fun onCharacteristicChanged(g: BluetoothGatt, c: BluetoothGattCharacteristic, value: ByteArray) {
            if (c.uuid == EVENTS) notifications.trySend(value)
        }
    }

    private fun u32(b: ByteArray): Long =
        ByteBuffer.wrap(b).order(ByteOrder.LITTLE_ENDIAN).int.toLong() and 0xFFFFFFFFL

    private fun le32(v: Long): ByteArray =
        ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(v.toInt()).array()
}
