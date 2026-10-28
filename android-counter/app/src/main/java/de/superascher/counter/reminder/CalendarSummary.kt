package de.superascher.counter.reminder

import android.Manifest
import android.content.ContentValues
import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import android.provider.CalendarContract.Calendars
import android.provider.CalendarContract.Events
import de.superascher.counter.R
import de.superascher.counter.data.EntryStore
import de.superascher.counter.data.Settings
import de.superascher.counter.logic.Counter
import java.time.LocalDate
import java.time.ZoneOffset

/**
 * Tageszusammenfassung "🚬 N Zigaretten" als ganztägiger Termin, wie DailySummaryJob in Nextcloud.
 * Eigener lokaler Kalender auf dem Handy (wird nicht synchronisiert). Läuft stündlich, schreibt
 * den abgeschlossenen Vortag (nach eigener Tageswechsel-Stunde) und aktualisiert vorhandene Termine.
 */
object CalendarSummary {
    private const val ACCOUNT = "Ciggie Counter"
    /** Kalender aus der Zeit vor der Umbenennung wird weiterbenutzt. */
    private const val LEGACY_ACCOUNT = "Zigarettenzähler"

    fun sync(context: Context) {
        val settings = Settings.load(context)
        if (!settings.calendarSummary || !hasPermission(context)) return
        val counter = Counter(settings)
        val yesterday = counter.today().minusDays(1)
        val count = counter.onDay(EntryStore.get(context).entries.value, yesterday).size
        upsert(context, calendarId(context), yesterday, count)
    }

    fun hasPermission(context: Context) =
        context.checkSelfPermission(Manifest.permission.WRITE_CALENDAR) == PackageManager.PERMISSION_GRANTED &&
            context.checkSelfPermission(Manifest.permission.READ_CALENDAR) == PackageManager.PERMISSION_GRANTED

    private fun asSyncAdapter(uri: Uri, account: String = ACCOUNT): Uri = uri.buildUpon()
        .appendQueryParameter(android.provider.CalendarContract.CALLER_IS_SYNCADAPTER, "true")
        .appendQueryParameter(Calendars.ACCOUNT_NAME, account)
        .appendQueryParameter(Calendars.ACCOUNT_TYPE, android.provider.CalendarContract.ACCOUNT_TYPE_LOCAL)
        .build()

    private fun calendarId(context: Context): Long {
        val cr = context.contentResolver
        val name = context.getString(R.string.app_name)
        cr.query(
            Calendars.CONTENT_URI, arrayOf(Calendars._ID, Calendars.ACCOUNT_NAME, Calendars.CALENDAR_DISPLAY_NAME),
            "${Calendars.ACCOUNT_NAME} IN (?, ?) AND ${Calendars.ACCOUNT_TYPE} = ?",
            arrayOf(ACCOUNT, LEGACY_ACCOUNT, android.provider.CalendarContract.ACCOUNT_TYPE_LOCAL), null,
        )?.use {
            if (it.moveToFirst()) {
                val id = it.getLong(0)
                if (it.getString(2) != name) {
                    cr.update(
                        asSyncAdapter(android.content.ContentUris.withAppendedId(Calendars.CONTENT_URI, id), it.getString(1)),
                        ContentValues().apply { put(Calendars.CALENDAR_DISPLAY_NAME, name) }, null, null,
                    )
                }
                return id
            }
        }

        val values = ContentValues().apply {
            put(Calendars.ACCOUNT_NAME, ACCOUNT)
            put(Calendars.ACCOUNT_TYPE, android.provider.CalendarContract.ACCOUNT_TYPE_LOCAL)
            put(Calendars.NAME, ACCOUNT)
            put(Calendars.CALENDAR_DISPLAY_NAME, name)
            put(Calendars.CALENDAR_COLOR, 0xFF8D6E63.toInt())
            put(Calendars.CALENDAR_ACCESS_LEVEL, Calendars.CAL_ACCESS_OWNER)
            put(Calendars.OWNER_ACCOUNT, ACCOUNT)
            put(Calendars.VISIBLE, 1)
            put(Calendars.SYNC_EVENTS, 1)
        }
        return cr.insert(asSyncAdapter(Calendars.CONTENT_URI), values)!!.lastPathSegment!!.toLong()
    }

    private fun upsert(context: Context, calendarId: Long, day: LocalDate, count: Int) {
        val cr = context.contentResolver
        val start = day.atStartOfDay(ZoneOffset.UTC).toInstant().toEpochMilli() // ganztägig = UTC-Mitternacht
        val title = context.resources.getQuantityString(R.plurals.calendar_title, count, count)
        val existing = cr.query(
            Events.CONTENT_URI, arrayOf(Events._ID, Events.TITLE),
            "${Events.CALENDAR_ID} = ? AND ${Events.DTSTART} = ? AND ${Events.DELETED} = 0",
            arrayOf(calendarId.toString(), start.toString()), null,
        )?.use { if (it.moveToFirst()) it.getLong(0) to it.getString(1) else null }

        if (existing != null) {
            if (existing.second != title) {
                cr.update(
                    android.content.ContentUris.withAppendedId(Events.CONTENT_URI, existing.first),
                    ContentValues().apply { put(Events.TITLE, title) }, null, null,
                )
            }
            return
        }
        cr.insert(Events.CONTENT_URI, ContentValues().apply {
            put(Events.CALENDAR_ID, calendarId)
            put(Events.TITLE, title)
            put(Events.DTSTART, start)
            put(Events.DTEND, start + 24 * 3600 * 1000L)
            put(Events.ALL_DAY, 1)
            put(Events.EVENT_TIMEZONE, "UTC")
        })
    }
}
