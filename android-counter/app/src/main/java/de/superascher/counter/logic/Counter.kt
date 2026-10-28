package de.superascher.counter.logic

import de.superascher.counter.data.Settings
import java.time.Instant
import java.time.LocalDate
import java.time.YearMonth
import java.time.ZoneId
import kotlin.math.max
import kotlin.math.roundToLong

/**
 * Tages-, Monats- und Jahreszählung sowie Pacing, portiert aus der Nextcloud-App (EntryService.php).
 * [entries] sind Unix-Sekunden, aufsteigend sortiert.
 */
class Counter(
    private val settings: Settings,
    private val zone: ZoneId = ZoneId.systemDefault(),
) {
    /** Logischer Tag: Uhrzeit vor der Tageswechsel-Stunde zählt zum Vortag (auch bei Zeitumstellung eindeutig). */
    fun logicalDate(ts: Long): LocalDate {
        val local = Instant.ofEpochSecond(ts).atZone(zone)
        return if (local.hour < settings.dayStartHour) local.toLocalDate().minusDays(1) else local.toLocalDate()
    }

    fun today(now: Long = nowSeconds()): LocalDate = logicalDate(now)

    fun onDay(entries: List<Long>, day: LocalDate): List<Long> = entries.filter { logicalDate(it) == day }

    fun countMonth(entries: List<Long>, month: YearMonth): Int =
        entries.count { YearMonth.from(logicalDate(it)) == month }

    fun countYear(entries: List<Long>, year: Int): Int = entries.count { logicalDate(it).year == year }

    /** Anzahl pro logischem Tag für die letzten [days] Tage (ältester zuerst, heute zuletzt). */
    fun perDay(entries: List<Long>, days: Int, now: Long = nowSeconds()): List<Pair<LocalDate, Int>> {
        val today = today(now)
        val counts = entries.groupingBy { logicalDate(it) }.eachCount()
        return (days - 1 downTo 0).map { today.minusDays(it.toLong()) }.map { it to (counts[it] ?: 0) }
    }

    /** Anzahl pro Monat für die letzten [months] Monate (ältester zuerst). */
    fun perMonth(entries: List<Long>, months: Int, now: Long = nowSeconds()): List<Pair<YearMonth, Int>> {
        val current = YearMonth.from(today(now))
        val counts = entries.groupingBy { YearMonth.from(logicalDate(it)) }.eachCount()
        return (months - 1 downTo 0).map { current.minusMonths(it.toLong()) }.map { it to (counts[it] ?: 0) }
    }

    /**
     * Minuten bis zur nächsten erlaubten Zigarette, null = kein Pacing eingestellt.
     * "computed": Vor der ersten Zigarette des Tages Wachzeit ÷ Ziel, danach wird das
     * verbleibende Kontingent über die verbleibende Wachzeit (ab der ersten Zigarette) verteilt.
     */
    fun intervalMinutes(entries: List<Long>, now: Long = nowSeconds()): Double? {
        when (settings.intervalMode) {
            "fixed" -> return settings.fixedIntervalMinutes?.takeIf { it > 0 }?.toDouble()
            "off" -> return null
        }
        val target = settings.dailyTarget?.takeIf { it > 0 } ?: return null
        val wakeSeconds = settings.wakeHours * 3600
        val todayEntries = onDay(entries, today(now))
        if (todayEntries.isEmpty()) return wakeSeconds / target / 60

        // Bei erreichtem Ziel mit Rest 1 weiterrechnen, damit immer ein Intervall angezeigt wird
        val remaining = max(target - todayEntries.size, 1)
        val dayEnd = todayEntries.first() + wakeSeconds.toLong()
        val remainingSeconds = (dayEnd - now).takeIf { it > 0 } ?: 60
        return remainingSeconds.toDouble() / remaining / 60
    }

    /** Zeitpunkt (Unix-Sekunden), ab dem die nächste Zigarette "erlaubt" ist, null = kein Pacing. */
    fun nextAllowedAt(entries: List<Long>, now: Long = nowSeconds()): Long? {
        val minutes = intervalMinutes(entries, now) ?: return null
        val last = entries.lastOrNull() ?: return null
        return last + (minutes * 60).roundToLong()
    }

    /**
     * Ab wann die nächste Zigarette tatsächlich erlaubt ist (für den Wecker).
     * Im Modus "computed" rückt [nextAllowedAt] mit der Zeit näher, weil die Restzeit schrumpft:
     * next(t) = last + (dayEnd − t) / rest. Erlaubt ist ab dem Schnittpunkt next(t) = t.
     */
    fun allowedFrom(entries: List<Long>, now: Long = nowSeconds()): Long? {
        val last = entries.lastOrNull() ?: return null
        if (settings.intervalMode != "computed") return nextAllowedAt(entries, now)
        val target = settings.dailyTarget?.takeIf { it > 0 } ?: return null
        val wakeSeconds = (settings.wakeHours * 3600).toLong()
        val todayEntries = onDay(entries, today(now))
        if (todayEntries.isEmpty()) return last + wakeSeconds / target

        val remaining = max(target - todayEntries.size, 1)
        val dayEnd = todayEntries.first() + wakeSeconds
        if (dayEnd <= now) return last + 60L / remaining
        return (last * remaining + dayEnd) / (remaining + 1)
    }

    companion object {
        fun nowSeconds(): Long = System.currentTimeMillis() / 1000
    }
}
