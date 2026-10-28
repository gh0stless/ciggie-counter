package de.superascher.counter.data

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Alle gerauchten Zigaretten als Zeitstempel (Unix-Sekunden), aufsteigend sortiert.
 * Wie in der Nextcloud-App ereignisbasiert: Statistiken werden immer aus den Einträgen berechnet.
 *
 * Dazu die Warteschlange für die optionale Nextcloud-Weiterleitung (Tabelle outbox):
 * jedes Hinzufügen/Löschen bei eingeschalteter Nextcloud, abgearbeitet von NextcloudWorker.
 */
class EntryStore private constructor(context: Context) :
    SQLiteOpenHelper(context, "entries.db", null, 2) {

    data class Op(val id: Long, val op: String, val ts: Long)

    private val _entries = MutableStateFlow(load())
    val entries: StateFlow<List<Long>> = _entries.asStateFlow()

    override fun onCreate(db: SQLiteDatabase) {
        // source: "manual" (Knopf/Nachtragen) oder "ashtray" (Superascher)
        db.execSQL("CREATE TABLE entries (ts INTEGER NOT NULL, source TEXT NOT NULL DEFAULT 'manual')")
        db.execSQL("CREATE INDEX entries_ts ON entries(ts)")
        onUpgrade(db, 1, 2)
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        if (oldVersion < 2) {
            // op: "add" oder "del"
            db.execSQL("CREATE TABLE outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, op TEXT NOT NULL, ts INTEGER NOT NULL)")
        }
    }

    @Synchronized
    fun add(ts: Long, source: String = "manual", forward: Boolean = false) {
        writableDatabase.run {
            beginTransaction()
            try {
                insert("entries", null, ContentValues().apply {
                    put("ts", ts)
                    put("source", source)
                })
                if (forward) enqueue(this, "add", ts)
                setTransactionSuccessful()
            } finally {
                endTransaction()
            }
        }
        _entries.value = load()
    }

    /** Löscht genau einen Eintrag mit diesem Zeitstempel. */
    @Synchronized
    fun delete(ts: Long, forward: Boolean = false) {
        writableDatabase.run {
            beginTransaction()
            try {
                execSQL(
                    "DELETE FROM entries WHERE rowid = (SELECT rowid FROM entries WHERE ts = ? LIMIT 1)",
                    arrayOf(ts),
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
                    put("ts", ts)
                    put("source", sources[ts] ?: "server")
                })
                server.forEach { insertEntry(it) }
                for (op in pendingOps()) {
                    if (op.op == "add") insertEntry(op.ts)
                    else execSQL(
                        "DELETE FROM entries WHERE rowid = (SELECT rowid FROM entries WHERE ts = ? LIMIT 1)",
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
        readableDatabase.rawQuery("SELECT ts FROM entries ORDER BY ts", null).use { c ->
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
