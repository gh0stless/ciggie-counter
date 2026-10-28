package de.superascher.counter.ui

import android.app.DatePickerDialog
import android.app.TimePickerDialog
import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import de.superascher.counter.R
import de.superascher.counter.data.AppState
import de.superascher.counter.data.EntryStore
import de.superascher.counter.data.Settings
import de.superascher.counter.logic.Counter
import de.superascher.counter.reminder.Reminders
import kotlinx.coroutines.delay
import java.time.Instant
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle
import java.text.NumberFormat

/** Uhrzeit in der Schreibweise der Gerätesprache (14:05 bzw. 2:05 PM). */
fun formatTime(ts: Long): String =
    DateTimeFormatter.ofLocalizedTime(FormatStyle.SHORT).format(Instant.ofEpochSecond(ts).atZone(ZoneId.systemDefault()))

/** Infoseite zum Butt Bin im Browser öffnen. */
fun openInfo(context: android.content.Context) =
    context.startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse(context.getString(R.string.info_url))))

/** Betrag in der Währung der Gerätesprache. */
fun formatMoney(value: Double): String = NumberFormat.getCurrencyInstance().format(value)

@Composable
fun HomeScreen(entries: List<Long>, settings: Settings, modifier: Modifier, onOpenAshtray: () -> Unit) {
    val context = LocalContext.current
    val counter = remember(settings) { Counter(settings) }
    var now by remember { mutableLongStateOf(Counter.nowSeconds()) }
    LaunchedEffect(Unit) {
        while (true) {
            delay(15_000)
            now = Counter.nowSeconds()
        }
    }
    var toDelete by remember { mutableStateOf<Long?>(null) }

    val today = counter.today(now)
    val todayEntries = counter.onDay(entries, today)
    val yesterdayEntries = counter.onDay(entries, today.minusDays(1))

    Column(
        modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(stringResource(R.string.today), style = MaterialTheme.typography.titleMedium)
        Text("${todayEntries.size}", fontSize = 72.sp, fontWeight = FontWeight.Bold)
        Text(buildString {
            append(stringResource(R.string.yesterday_count, yesterdayEntries.size))
            settings.costPerCigarette?.let { append("  ·  " + stringResource(R.string.cost_today, formatMoney(todayEntries.size * it))) }
        })

        PacingInfo(counter, entries, now)

        Button(
            onClick = {
                Reminders.count(context)
                now = Counter.nowSeconds()
            },
            shape = CircleShape,
            modifier = Modifier.size(180.dp),
        ) { Text("+1", fontSize = 48.sp) }

        TextButton(onClick = { pickPastTime(context) }) { Text(stringResource(R.string.add_past)) }

        if (todayEntries.isNotEmpty() || yesterdayEntries.isNotEmpty()) {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    History(stringResource(R.string.today), todayEntries) { toDelete = it }
                    if (yesterdayEntries.isNotEmpty()) {
                        Spacer(Modifier.size(8.dp))
                        History(stringResource(R.string.yesterday), yesterdayEntries) { toDelete = it }
                    }
                }
            }
        }

        if (AppState(context).ashtrayAddress == null) {
            Card(
                Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer),
            ) {
                Column(Modifier.padding(16.dp)) {
                    Text(stringResource(R.string.tip_title), fontWeight = FontWeight.Bold)
                    Text(stringResource(R.string.tip_text))
                    Row {
                        TextButton(onClick = { openInfo(context) }) { Text(stringResource(R.string.learn_more)) }
                        TextButton(onClick = onOpenAshtray) { Text(stringResource(R.string.pair)) }
                    }
                }
            }
        }
    }

    toDelete?.let { ts ->
        AlertDialog(
            onDismissRequest = { toDelete = null },
            title = { Text(stringResource(R.string.delete_entry_title)) },
            text = { Text(stringResource(R.string.delete_entry_text, stringResource(R.string.time_clock, formatTime(ts)))) },
            confirmButton = {
                TextButton(onClick = {
                    Reminders.delete(context, ts)
                    toDelete = null
                }) { Text(stringResource(R.string.delete)) }
            },
            dismissButton = { TextButton(onClick = { toDelete = null }) { Text(stringResource(R.string.cancel)) } },
        )
    }
}

@Composable
private fun PacingInfo(counter: Counter, entries: List<Long>, now: Long) {
    val interval = counter.intervalMinutes(entries, now) ?: return
    val next = counter.nextAllowedAt(entries, now)
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            when {
                next == null -> Text(stringResource(R.string.pacing_interval, interval.toInt()))
                next <= now -> Text(stringResource(R.string.pacing_allowed), fontWeight = FontWeight.Bold)
                else -> {
                    Text(stringResource(R.string.pacing_next, stringResource(R.string.time_clock, formatTime(next))), fontWeight = FontWeight.Bold)
                    Text(stringResource(R.string.pacing_remaining, ((next - now + 59) / 60).toInt(), interval.toInt()))
                }
            }
        }
    }
}

@Composable
private fun History(title: String, items: List<Long>, onDelete: (Long) -> Unit) {
    Text(title, style = MaterialTheme.typography.titleSmall)
    HorizontalDivider()
    items.asReversed().forEach { ts ->
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(stringResource(R.string.time_clock, formatTime(ts)), Modifier.weight(1f))
            TextButton(onClick = { onDelete(ts) }) { Text("×") }
        }
    }
}

/** Datum und Uhrzeit wählen, Zukunft ist nicht erlaubt (wie in der Nextcloud-App). */
private fun pickPastTime(context: android.content.Context) {
    val now = LocalDateTime.now()
    DatePickerDialog(context, { _, y, m, d ->
        TimePickerDialog(context, { _, h, min ->
            val chosen = LocalDateTime.of(y, m + 1, d, h, min)
            if (chosen.isAfter(LocalDateTime.now())) {
                Toast.makeText(context, R.string.future_time, Toast.LENGTH_SHORT).show()
            } else {
                Reminders.count(context, chosen.atZone(ZoneId.systemDefault()).toEpochSecond())
            }
        }, now.hour, now.minute, android.text.format.DateFormat.is24HourFormat(context)).show()
    }, now.year, now.monthValue - 1, now.dayOfMonth).apply {
        datePicker.maxDate = System.currentTimeMillis()
    }.show()
}
