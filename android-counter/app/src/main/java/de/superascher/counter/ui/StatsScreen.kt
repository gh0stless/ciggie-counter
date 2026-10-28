package de.superascher.counter.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import de.superascher.counter.R
import de.superascher.counter.data.Settings
import de.superascher.counter.logic.Counter
import java.time.Instant
import java.time.YearMonth
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

@Composable
fun StatsScreen(entries: List<Long>, settings: Settings, modifier: Modifier) {
    val counter = remember(settings) { Counter(settings) }
    val now = Counter.nowSeconds()
    val today = counter.today(now)
    val last30 = remember(entries, settings) { counter.perDay(entries, 30, now) }
    val last12 = remember(entries, settings) { counter.perMonth(entries, 12, now) }
    val byHour = remember(entries) {
        val since = now - 30 * 86400L
        val counts = IntArray(24)
        entries.filter { it >= since }.forEach { counts[Instant.ofEpochSecond(it).atZone(ZoneId.systemDefault()).hour]++ }
        counts.toList()
    }
    val month = counter.countMonth(entries, YearMonth.from(today))
    val year = counter.countYear(entries, today.year)
    // Durchschnitt nur über abgeschlossene Tage (heute zählt noch)
    val avg7 = last30.dropLast(1).takeLast(7).map { it.second }.average()
    val avg30 = last30.dropLast(1).map { it.second }.average()
    val cost = settings.costPerCigarette

    Column(
        modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(stringResource(R.string.tab_stats), style = MaterialTheme.typography.headlineSmall)
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            StatCard(stringResource(R.string.this_month), "$month", cost?.let { formatMoney(month * it) }, Modifier.weight(1f))
            StatCard(stringResource(R.string.this_year), "$year", cost?.let { formatMoney(year * it) }, Modifier.weight(1f))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            StatCard(stringResource(R.string.avg_7), format1(avg7), stringResource(R.string.per_day), Modifier.weight(1f))
            StatCard(stringResource(R.string.avg_30), format1(avg30), stringResource(R.string.per_day), Modifier.weight(1f))
        }

        val dayLabel = DateTimeFormatter.ofPattern(stringResource(R.string.chart_day_pattern))
        ChartCard(stringResource(R.string.last_30_days), stringResource(R.string.dashed_target)) {
            BarChart(
                values = last30.map { it.second },
                labels = last30.mapIndexed { i, (d, _) -> if (i % 7 == 2 || i == 29) dayLabel.format(d) else "" },
                guide = settings.dailyTarget,
            )
        }
        val monthLabel = DateTimeFormatter.ofPattern("MMM")
        ChartCard(stringResource(R.string.last_12_months), null) {
            BarChart(values = last12.map { it.second }, labels = last12.map { monthLabel.format(it.first) })
        }
        ChartCard(stringResource(R.string.time_of_day), null) {
            BarChart(values = byHour, labels = (0..23).map { if (it % 6 == 0) "$it h" else "" })
        }
    }
}

private fun format1(v: Double) = if (v.isNaN()) "–" else String.format(Locale.getDefault(), "%.1f", v)

@Composable
private fun StatCard(title: String, value: String, sub: String?, modifier: Modifier) {
    Card(modifier) {
        Column(Modifier.padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.labelLarge)
            Text(value, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            sub?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
        }
    }
}

@Composable
private fun ChartCard(title: String, note: String?, content: @Composable () -> Unit) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            note?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
            content()
        }
    }
}

/** Einfaches Balkendiagramm; [guide] = optionale gestrichelte Linie (z. B. Tagesziel). */
@Composable
private fun BarChart(values: List<Int>, labels: List<String>, guide: Int? = null) {
    val bar = MaterialTheme.colorScheme.primary
    val line = MaterialTheme.colorScheme.error
    val max = maxOf(values.maxOrNull() ?: 0, guide ?: 0, 1)
    Canvas(Modifier.fillMaxWidth().height(140.dp).padding(top = 8.dp)) {
        val slot = size.width / values.size
        val gap = slot * 0.2f
        values.forEachIndexed { i, v ->
            val h = size.height * v / max
            drawRect(bar, Offset(i * slot + gap / 2, size.height - h), Size(slot - gap, h))
        }
        guide?.let {
            val y = size.height - size.height * it / max
            drawLine(line, Offset(0f, y), Offset(size.width, y), 3f,
                pathEffect = PathEffect.dashPathEffect(floatArrayOf(12f, 8f)))
        }
        drawLine(Color.Gray, Offset(0f, size.height), Offset(size.width, size.height), 2f)
    }
    Row(Modifier.fillMaxWidth()) {
        labels.forEach { Text(it, Modifier.weight(1f), style = MaterialTheme.typography.labelSmall, maxLines = 1, softWrap = false) }
    }
}
