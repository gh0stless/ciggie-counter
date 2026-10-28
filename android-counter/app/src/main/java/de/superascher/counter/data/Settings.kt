package de.superascher.counter.data

import android.content.Context
import android.content.SharedPreferences
import androidx.core.content.edit

/** Einstellungen, Bedeutung wie in der Nextcloud-App (nextcloud-app/PROJEKT.md §6). */
data class Settings(
    val costPerCigarette: Double? = null,
    /** Zähltag beginnt um diese Stunde (0–23), davor zählt zum Vortag. */
    val dayStartHour: Int = 0,
    /** "computed" = Intervall aus Tagesziel, "fixed" = feste Minuten, "off" = kein Pacing */
    val intervalMode: String = "computed",
    val dailyTarget: Int? = null,
    val wakeHours: Double = 18.0,
    val fixedIntervalMinutes: Int? = null,
    val nextAllowedReminder: Boolean = true,
    /** Standard aus: alle paar Minuten nachzufragen ist für neue Nutzer zu aufdringlich */
    val countCheckReminder: Boolean = false,
    val countCheckMinutes: Int = 10,
    val calendarSummary: Boolean = false,
    val haWebhookUrl: String = "",
    /** Optional: eigene Nextcloud mit der App "cigarettecounter" (nextcloud-app/) */
    val ncUrl: String = "",
    val ncUser: String = "",
    /** App-Passwort (Nextcloud: Einstellungen > Sicherheit), nicht das Login-Passwort */
    val ncAppPassword: String = "",
) {
    val ncEnabled: Boolean
        get() = validUrl(ncUrl) && ncUser.isNotEmpty() && ncAppPassword.isNotEmpty()

    companion object {
        /** Nur http:// oder https:// mit Hostnamen (fängt Tippfehler wie "htttps://" ab). */
        fun validUrl(url: String): Boolean =
            Regex("^https?://[^/\\s]+.*").matches(url.trim())

        private fun prefs(context: Context): SharedPreferences =
            context.getSharedPreferences("settings", Context.MODE_PRIVATE)

        fun load(context: Context): Settings = prefs(context).run {
            Settings(
                costPerCigarette = getString("cost", null)?.toDoubleOrNull(),
                dayStartHour = getInt("day_start_hour", 0),
                intervalMode = getString("interval_mode", "computed") ?: "computed",
                dailyTarget = getInt("daily_target", 0).takeIf { it > 0 },
                wakeHours = getFloat("wake_hours", 18f).toDouble(),
                fixedIntervalMinutes = getInt("fixed_interval", 0).takeIf { it > 0 },
                nextAllowedReminder = getBoolean("next_allowed_reminder", true),
                countCheckReminder = getBoolean("count_check", false),
                countCheckMinutes = getInt("count_check_minutes", 10),
                calendarSummary = getBoolean("calendar_summary", false),
                haWebhookUrl = getString("ha_webhook", "") ?: "",
                ncUrl = getString("nc_url", "") ?: "",
                ncUser = getString("nc_user", "") ?: "",
                ncAppPassword = getString("nc_app_password", "") ?: "",
            )
        }

        fun save(context: Context, s: Settings) = prefs(context).edit {
            putString("cost", s.costPerCigarette?.toString())
            putInt("day_start_hour", s.dayStartHour.coerceIn(0, 23))
            putString("interval_mode", s.intervalMode)
            putInt("daily_target", s.dailyTarget ?: 0)
            putFloat("wake_hours", s.wakeHours.toFloat())
            putInt("fixed_interval", s.fixedIntervalMinutes ?: 0)
            putBoolean("next_allowed_reminder", s.nextAllowedReminder)
            putBoolean("count_check", s.countCheckReminder)
            putInt("count_check_minutes", s.countCheckMinutes.coerceAtLeast(1))
            putBoolean("calendar_summary", s.calendarSummary)
            putString("ha_webhook", s.haWebhookUrl.trim())
            putString("nc_url", s.ncUrl.trim().trimEnd('/'))
            putString("nc_user", s.ncUser.trim())
            putString("nc_app_password", s.ncAppPassword.trim())
        }
    }
}

/** Zustand, den die App selbst führt (nicht vom Nutzer eingestellt). */
class AppState(context: Context) {
    private val sp = context.getSharedPreferences("state", Context.MODE_PRIVATE)

    /** Für welches "nächste erlaubt" schon benachrichtigt wurde (nicht doppelt melden). */
    var lastNotifiedFor: Long
        get() = sp.getLong("last_notified_for", 0)
        set(v) = sp.edit { putLong("last_notified_for", v) }

    /** Letzte Zähl-Erinnerung oder letzter Eintrag, Takt der "Alle gezählt?"-Erinnerung. */
    var lastCountCheckAt: Long
        get() = sp.getLong("last_count_check_at", 0)
        set(v) = sp.edit { putLong("last_count_check_at", v) }

    // Superascher (optional)
    var ashtrayAddress: String?
        get() = sp.getString("ashtray_address", null)
        set(v) = sp.edit { putString("ashtray_address", v) }

    /** Nächste noch nicht übernommene Ereignisnummer des Aschers, -1 = noch nie abgeglichen */
    var ashtrayNextSeq: Long
        get() = sp.getLong("ashtray_next_seq", -1)
        set(v) = sp.edit { putLong("ashtray_next_seq", v) }

    var ashtrayLastSync: Long
        get() = sp.getLong("ashtray_last_sync", 0)
        set(v) = sp.edit { putLong("ashtray_last_sync", v) }

    var ashtrayStatus: String
        get() = sp.getString("ashtray_status", "") ?: ""
        set(v) = sp.edit { putString("ashtray_status", v) }

    /** Hintergrund-Scan: zuletzt angestoßener Zählerstand und Zeitpunkt (Bremse bei Fehlern) */
    var ashtrayTriggerCount: Long
        get() = sp.getLong("ashtray_trigger_count", -1)
        set(v) = sp.edit { putLong("ashtray_trigger_count", v) }

    var ashtrayTriggerAt: Long
        get() = sp.getLong("ashtray_trigger_at", 0)
        set(v) = sp.edit { putLong("ashtray_trigger_at", v) }

    // Nextcloud (optional)
    var ncLastSync: Long
        get() = sp.getLong("nc_last_sync", 0)
        set(v) = sp.edit { putLong("nc_last_sync", v) }

    var ncStatus: String
        get() = sp.getString("nc_status", "") ?: ""
        set(v) = sp.edit { putString("nc_status", v) }
}
