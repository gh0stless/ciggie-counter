package de.superascher.counter.data

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.UUID

/**
 * Alle gerauchten Zigaretten als Zeitstempel (Unix-Sekunden), aufsteigend sortiert.
 * Wie in der Nextcloud-App ereignisbasiert: Statistiken werden immer aus den Einträgen berechnet.
 *
 * Abgleich v2 (Nextcloud ab 0.9.11): jeder Eintrag hat eine ID, gelöschte bleiben als Löschmarke
 * (deleted = 1) stehen, dirty = 1 heißt "noch nicht an Nextcloud gemeldet", ha_dirty = 1
 * "noch nicht zusätzlich an Home Assistant gemeldet" (Settings.haAlsoNotify).
 *
 * Dazu die alte Warteschlange (Tabelle outbox) für Nextcloud-Versionen ohne v2 und für den
 * einmaligen Umstieg; im v2-Betrieb wird sie nach jedem Abgleich geleert.
 */
class EntryStore private constructor(context: Context) :
    SQLiteOpenHelper(context, "entries.db", null, 5) {

    data class Op(val id: Long, val op: String, val ts: Long)

    /** Ein Eintrag mit ID für den Abgleich v2 */
    data class Record(val id: String, val ts: Long, val source: String, val deleted: Boolean)

    private val _entries = MutableStateFlow(load())
    val entries: StateFlow<List<Long>> = _entries.asStateFlow()

    override fun onCreate(db: SQLiteDatabase) {
        // source: "manual" (Knopf/Nachtragen), "ashtray" (Superascher) oder "watch" (Uhr über Gadgetbridge)
        db.execSQL("CREATE TABLE entries (ts INTEGER NOT NULL, source TEXT NOT NULL DEFAULT 'manual')")
        db.execSQL("CREATE INDEX entries_ts ON entries(ts)")
        onUpgrade(db, 1, 2)
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        if (oldVersion < 2) {
            // op: "add" oder "del"
            db.execSQL("CREATE TABLE outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, op TEXT NOT NULL, ts INTEGER NOT NULL)")
        }
        if (oldVersion < 3) {
            db.execSQL("ALTER TABLE entries ADD COLUMN id TEXT")
            db.execSQL("ALTER TABLE entries ADD COLUMN deleted INTEGER NOT NULL DEFAULT 0")
            db.execSQL("ALTER TABLE entries ADD COLUMN dirty INTEGER NOT NULL DEFAULT 0")
            // vorhandene Einträge bekommen eine zufällige ID (UUID-Form)
            db.execSQL(
                "UPDATE entries SET id = lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || " +
                    "substr(hex(randomblob(2)), 2) || '-' || hex(randomblob(2)) || '-' || hex(randomblob(6)))"
            )
            db.execSQL("CREATE INDEX entries_id ON entries(id)")
        }
        if (oldVersion < 4) {
            db.execSQL("ALTER TABLE entries ADD COLUMN ha_dirty INTEGER NOT NULL DEFAULT 0")
        }
        if (oldVersion < 5) {
            // Messungen der Uhr vor/nach einer Zigarette (Band 7, wieder entfernt); die Tabelle
            // bleibt, weil sich die Datenbankversion nicht zurücknehmen lässt
            db.execSQL(
                "CREATE TABLE measurements (entry_id TEXT NOT NULL, phase TEXT NOT NULL, ts INTEGER NOT NULL, " +
                    "hr INTEGER NOT NULL, spo2 INTEGER NOT NULL, stress INTEGER NOT NULL, PRIMARY KEY (entry_id, phase))"
            )
        }
    }

    /**
     * [id]: Eintrags-ID einer Quelle, die selbst IDs vergibt (Uhr); ein schon bekannter Eintrag
     * wird dann nicht noch einmal angelegt. Ergebnis: ob ein neuer Eintrag entstanden ist.
     * [notifyHa]: zusätzlich an Home Assistant melden.
     */
    @Synchronized
    fun add(ts: Long, source: String = "manual", forward: Boolean = false, id: String? = null, notifyHa: Boolean = false): Boolean {
        if (id != null && exists(id)) return false
        writableDatabase.run {
            beginTransaction()
            try {
                insert("entries", null, ContentValues().apply {
                    put("id", id ?: UUID.randomUUID().toString())
                    put("ts", ts)
                    put("source", source)
                    put("dirty", if (forward) 1 else 0)
                    put("ha_dirty", if (notifyHa) 1 else 0)
                })
                if (forward) enqueue(this, "add", ts)
                setTransactionSuccessful()
            } finally {
                endTransaction()
            }
        }
        _entries.value = load()
        return true
    }

    /** Auch gelöschte Einträge zählen als bekannt, damit eine Wiederholung sie nicht zurückholt. */
    fun exists(id: String): Boolean =
        readableDatabase.rawQuery("SELECT 1 FROM entries WHERE id = ? LIMIT 1", arrayOf(id)).use { it.moveToFirst() }

    /** Löscht genau einen Eintrag mit diesem Zeitstempel. */
    @Synchronized
    fun delete(ts: Long, forward: Boolean = false, notifyHa: Boolean = false) {
        writableDatabase.run {
            beginTransaction()
            try {
                // Löschmarke statt Löschen, damit andere Geräte es per Abgleich erfahren
                execSQL(
                    "UPDATE entries SET deleted = 1, dirty = ?, ha_dirty = ? WHERE rowid = " +
                        "(SELECT rowid FROM entries WHERE ts = ? AND deleted = 0 LIMIT 1)",
                    arrayOf(if (forward) 1 else 0, if (notifyHa) 1 else 0, ts),
                )
                if (forward) {
                    // Noch nicht gesendet? Dann einfach nicht senden, statt hinzufügen und wieder löschen
                    val pendingAdd = compileStatement(
                        "SELECT id FROM outbox WHERE op = 'add' AND ts = ? ORDER BY id DESC LIMIT 1"
                    ).apply { bindLong(1, ts) }.runCatching { simpleQueryForLong() }.getOrNull()
                    if (pendingAdd != null) delete("outbox", "id = ?", arrayOf(pendingAdd.toString()))
                    else enqueue(this, "del", ts)
                }
                setTransactionSuccessful()
            } finally {
                endTransaction()
            }
        }
        _entries.value = load()
    }

    /** Nur lokal; Nextcloud bleibt bewusst unverändert. */
    @Synchronized
    fun deleteAll() {
        writableDatabase.delete("entries", null, null)
        writableDatabase.delete("measurements", null, null)
        _entries.value = emptyList()
    }

    /**
     * Stand vom Server übernehmen (mehrere Geräte). Noch nicht gesendete eigene Änderungen
     * bleiben obendrauf erhalten, die Herkunft (Knopf/Superascher) bekannter Einträge auch.
     */
    @Synchronized
    fun replaceFromServer(server: List<Long>) {
        writableDatabase.run {
            beginTransaction()
            try {
                val sources = rawQuery("SELECT ts, source FROM entries", null).use { c ->
                    buildMap { while (c.moveToNext()) put(c.getLong(0), c.getString(1)) }
                }
                delete("entries", null, null)
                fun insertEntry(ts: Long) = insert("entries", null, ContentValues().apply {
                    put("id", UUID.randomUUID().toString())
                    put("ts", ts)
                    put("source", sources[ts] ?: "server")
                })
                server.forEach { insertEntry(it) }
                for (op in pendingOps()) {
                    if (op.op == "add") insertEntry(op.ts)
                    else execSQL(
                        "DELETE FROM entries WHERE rowid = (SELECT rowid FROM entries WHERE ts = ? AND deleted = 0 LIMIT 1)",
                        arrayOf(op.ts),
                    )
                }
                setTransactionSuccessful()
            } finally {
                endTransaction()
            }
        }
        _entries.value = load()
    }

    /** Abgleich v2: noch nicht gemeldete Einträge und Löschmarken */
    @Synchronized
    fun dirtyRecords(): List<Record> =
        readableDatabase.rawQuery("SELECT id, ts, source, deleted FROM entries WHERE dirty = 1", null).use { c ->
            List(c.count) { c.moveToNext(); Record(c.getString(0), c.getLong(1), c.getString(2), c.getInt(3) == 1) }
        }

    /** Noch zusätzlich an Home Assistant zu meldende Einträge und Löschmarken */
    @Synchronized
    fun haDirtyRecords(): List<Record> =
        readableDatabase.rawQuery("SELECT id, ts, source, deleted FROM entries WHERE ha_dirty = 1", null).use { c ->
            List(c.count) { c.moveToNext(); Record(c.getString(0), c.getLong(1), c.getString(2), c.getInt(3) == 1) }
        }

    @Synchronized
    fun markHaClean(sent: Collection<Record>) {
        writableDatabase.run {
            beginTransaction()
            try {
                // nur im gemeldeten Zustand: inzwischen gelöscht = Löschmarke muss noch hinterher
                sent.forEach {
                    update("entries", ContentValues().apply { put("ha_dirty", 0) }, "id = ? AND deleted = ?",
                        arrayOf(it.id, if (it.deleted) "1" else "0"))
                }
                setTransactionSuccessful()
            } finally {
                endTransaction()
            }
        }
    }

    @Synchronized
    fun markClean(ids: Collection<String>) {
        writableDatabase.run {
            beginTransaction()
            try {
                ids.forEach { update("entries", ContentValues().apply { put("dirty", 0) }, "id = ?", arrayOf(it)) }
                setTransactionSuccessful()
            } finally {
                endTransaction()
            }
        }
    }

    /**
     * Abgleich v2, Änderungen vom Server übernehmen: unbekannte Einträge anlegen, Löschmarken
     * anwenden (gelöscht bleibt gelöscht). Eigene, noch nicht gemeldete Änderungen bleiben.
     * Ergebnis: Zeitstempel der neu angelegten Einträge.
     */
    @Synchronized
    fun mergeFromServer(records: List<Record>): List<Long> {
        if (records.isEmpty()) return emptyList()
        val added = mutableListOf<Long>()
        writableDatabase.run {
            beginTransaction()
            try {
                for (r in records) {
                    val known = compileStatement("SELECT count(*) FROM entries WHERE id = ?")
                        .apply { bindString(1, r.id) }.simpleQueryForLong() > 0
                    if (known) {
                        if (r.deleted) update("entries", ContentValues().apply { put("deleted", 1) }, "id = ?", arrayOf(r.id))
                    } else if (!r.deleted) {
                        insert("entries", null, ContentValues().apply {
                            put("id", r.id)
                            put("ts", r.ts)
                            put("source", r.source)
                        })
                        added += r.ts
                    }
                }
                setTransactionSuccessful()
            } finally {
                endTransaction()
            }
        }
        _entries.value = load()
        return added
    }

    /** Einmaliger Umstieg auf v2: lokalen Stand komplett durch den Server-Stand (mit IDs) ersetzen. */
    @Synchronized
    fun replaceAllFromServer(records: List<Record>) {
        writableDatabase.run {
            beginTransaction()
            try {
                val sources = rawQuery("SELECT ts, source FROM entries", null).use { c ->
                    buildMap { while (c.moveToNext()) put(c.getLong(0), c.getString(1)) }
                }
                delete("entries", null, null)
                for (r in records) if (!r.deleted) insert("entries", null, ContentValues().apply {
                    put("id", r.id)
                    put("ts", r.ts)
                    // Herkunft (Knopf/Butt Bin) bekannter Einträge behalten
                    put("source", sources[r.ts] ?: r.source)
                })
                delete("outbox", null, null)
                setTransactionSuccessful()
            } finally {
                endTransaction()
            }
        }
        _entries.value = load()
    }

    @Synchronized
    fun pendingOps(): List<Op> =
        readableDatabase.rawQuery("SELECT id, op, ts FROM outbox ORDER BY id", null).use { c ->
            List(c.count) { c.moveToNext(); Op(c.getLong(0), c.getString(1), c.getLong(2)) }
        }

    @Synchronized
    fun removeOp(id: Long) {
        writableDatabase.delete("outbox", "id = ?", arrayOf(id.toString()))
    }

    @Synchronized
    fun clearOps() {
        writableDatabase.delete("outbox", null, null)
    }

    private fun enqueue(db: SQLiteDatabase, op: String, ts: Long) {
        db.insert("outbox", null, ContentValues().apply {
            put("op", op)
            put("ts", ts)
        })
    }

    private fun load(): List<Long> =
        readableDatabase.rawQuery("SELECT ts FROM entries WHERE deleted = 0 ORDER BY ts", null).use { c ->
            List(c.count) { c.moveToNext(); c.getLong(0) }
        }

    companion object {
        @Volatile
        private var instance: EntryStore? = null

        fun get(context: Context): EntryStore =
            instance ?: synchronized(this) {
                instance ?: EntryStore(context.applicationContext).also { instance = it }
            }
    }
}
