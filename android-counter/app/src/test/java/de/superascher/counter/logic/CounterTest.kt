package de.superascher.counter.logic

import de.superascher.counter.data.Settings
import org.junit.Assert.assertEquals
import org.junit.Test
import java.time.ZoneId
import java.time.ZonedDateTime

/** Pausen aus der Tagesmenge: fester Zeitpunkt "erlaubt ab", Grund-Pause nach der Wachzeit. */
class CounterTest {
    private val zone = ZoneId.of("Europe/Berlin")
    private val counter = Counter(Settings(intervalMode = "computed", dailyTarget = 3, wakeHours = 4.0), zone)

    private fun at(hhmm: String): Long =
        ZonedDateTime.of(2026, 11, 9, hhmm.take(2).toInt(), hhmm.takeLast(2).toInt(), 0, 0, zone).toEpochSecond()

    @Test
    fun allowedFromIsFixed() {
        // 08:00 erste, Wachzeit bis 12:00, noch 2 übrig: (08:00 * 2 + 12:00) / 3 = 09:20
        val entries = listOf(at("0800"))
        assertEquals(at("0920"), counter.allowedFrom(entries, at("0800")))
        assertEquals(at("0920"), counter.allowedFrom(entries, at("0900")))
    }

    @Test
    fun overTargetGivesLongButFinitePause() {
        // 4 von 3 geraucht, letzte 10:00: Rest gilt als 1 -> Mitte bis Tagesende 12:00
        val entries = listOf(at("0800"), at("0830"), at("0900"), at("1000"))
        assertEquals(at("1100"), counter.allowedFrom(entries, at("1000")))
    }

    @Test
    fun afterWakingTimeTheBasicBreakApplies() {
        // nach 12:00 geraucht: Grund-Pause 4 h / 3 = 80 min, nicht fast sofort
        val entries = listOf(at("0800"), at("1230"))
        assertEquals(at("1350"), counter.allowedFrom(entries, at("1230")))
        assertEquals(80.0, counter.intervalMinutes(entries, at("1300"))!!, 0.001)
    }
}
