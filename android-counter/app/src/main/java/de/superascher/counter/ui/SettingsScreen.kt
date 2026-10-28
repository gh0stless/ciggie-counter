package de.superascher.counter.ui

import android.Manifest
import android.app.AlarmManager
import android.content.Intent
import android.provider.Settings as AndroidSettings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalResources
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import de.superascher.counter.R
import de.superascher.counter.ashtray.AshtrayBle
import de.superascher.counter.ashtray.AshtraySync
import de.superascher.counter.ashtray.Background
import de.superascher.counter.data.AppState
import de.superascher.counter.data.EntryStore
import de.superascher.counter.data.Settings
import de.superascher.counter.reminder.CalendarSummary
import de.superascher.counter.reminder.Reminders
import kotlinx.coroutines.launch
import java.text.DateFormat
import java.text.DecimalFormatSymbols
import java.text.NumberFormat
import java.util.Date

/** Dezimalzahl in der Schreibweise der Gerätesprache (Eingabe akzeptiert Punkt und Komma). */
private fun decimal(v: Double) = v.toString().removeSuffix(".0").replace('.', DecimalFormatSymbols.getInstance().decimalSeparator)

@Composable
fun SettingsScreen(initial: Settings, modifier: Modifier, onSave: (Settings) -> Unit) {
    val context = LocalContext.current
    val res = LocalResources.current
    var cost by remember { mutableStateOf(initial.costPerCigarette?.let { decimal(it) } ?: "") }
    var dayStart by remember { mutableStateOf(initial.dayStartHour.toString()) }
    var mode by remember { mutableStateOf(initial.intervalMode) }
    var target by remember { mutableStateOf(initial.dailyTarget?.toString() ?: "") }
    var wake by remember { mutableStateOf(decimal(initial.wakeHours)) }
    var fixed by remember { mutableStateOf(initial.fixedIntervalMinutes?.toString() ?: "") }
    var nextAllowed by remember { mutableStateOf(initial.nextAllowedReminder) }
    var countCheck by remember { mutableStateOf(initial.countCheckReminder) }
    var countCheckMin by remember { mutableStateOf(initial.countCheckMinutes.toString()) }
    var calendar by remember { mutableStateOf(initial.calendarSummary) }
    var ha by remember { mutableStateOf(initial.haWebhookUrl) }
    var ncUrl by remember { mutableStateOf(initial.ncUrl) }
    var ncUser by remember { mutableStateOf(initial.ncUser) }
    var ncPassword by remember { mutableStateOf(initial.ncAppPassword) }
    var saved by remember { mutableStateOf(false) }

    val calendarPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
        calendar = CalendarSummary.hasPermission(context)
    }

    fun num(s: String) = s.trim().replace(',', '.').toDoubleOrNull()

    Column(
        modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(stringResource(R.string.tab_settings), style = MaterialTheme.typography.headlineSmall)

        Section(stringResource(R.string.section_general))
        NumberField(stringResource(R.string.cost_per_cigarette, NumberFormat.getCurrencyInstance().currency?.symbol ?: "€"), cost) { cost = it }
        NumberField(stringResource(R.string.day_start), dayStart) { dayStart = it }
        Hint(stringResource(R.string.day_start_hint))

        Section(stringResource(R.string.section_breaks))
        listOf("computed" to R.string.mode_computed, "fixed" to R.string.mode_fixed, "off" to R.string.mode_off).forEach { (key, label) ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                RadioButton(selected = mode == key, onClick = { mode = key })
                Text(stringResource(label))
            }
        }
        if (mode == "computed") {
            NumberField(stringResource(R.string.daily_target), target) { target = it }
            NumberField(stringResource(R.string.wake_hours), wake) { wake = it }
            Hint(stringResource(R.string.computed_hint))
        }
        if (mode == "fixed") NumberField(stringResource(R.string.fixed_minutes), fixed) { fixed = it }

        Section(stringResource(R.string.section_reminders))
        SwitchRow(stringResource(R.string.reminder_next_allowed), nextAllowed) { nextAllowed = it }
        SwitchRow(stringResource(R.string.reminder_count_check), countCheck) { countCheck = it }
        if (countCheck) NumberField(stringResource(R.string.count_check_every), countCheckMin) { countCheckMin = it }
        val alarms = context.getSystemService(AlarmManager::class.java)
        if (!alarms.canScheduleExactAlarms()) {
            Hint(stringResource(R.string.exact_alarm_hint))
            OutlinedButton(onClick = {
                context.startActivity(Intent(AndroidSettings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM))
            }) { Text(stringResource(R.string.exact_alarm_button)) }
        }

        Section(stringResource(R.string.section_calendar))
        SwitchRow(stringResource(R.string.calendar_switch), calendar) { on ->
            if (on && !CalendarSummary.hasPermission(context)) {
                calendarPermission.launch(arrayOf(Manifest.permission.READ_CALENDAR, Manifest.permission.WRITE_CALENDAR))
            } else {
                calendar = on
            }
        }
        Hint(stringResource(R.string.calendar_hint))

        Section(stringResource(R.string.section_ha))
        OutlinedTextField(ha, { ha = it }, Modifier.fillMaxWidth(), singleLine = true,
            label = { Text(stringResource(R.string.webhook_url)) },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri))
        Hint(stringResource(R.string.ha_hint))
        if (ha.startsWith("http")) {
            OutlinedButton(onClick = { Reminders.sendToHomeAssistant(ha.trim(), res.getString(R.string.ha_test_message)) }) {
                Text(stringResource(R.string.ha_test_button))
            }
        }

        NextcloudSection(ncUrl, ncUser, ncPassword, { ncUrl = it }, { ncUser = it }, { ncPassword = it })

        Button(onClick = {
            onSave(Settings(
                costPerCigarette = num(cost),
                dayStartHour = num(dayStart)?.toInt()?.coerceIn(0, 23) ?: 0,
                intervalMode = mode,
                dailyTarget = num(target)?.toInt(),
                wakeHours = num(wake)?.takeIf { it in 1.0..24.0 } ?: 18.0,
                fixedIntervalMinutes = num(fixed)?.toInt(),
                nextAllowedReminder = nextAllowed,
                countCheckReminder = countCheck,
                countCheckMinutes = num(countCheckMin)?.toInt()?.coerceAtLeast(1) ?: 10,
                calendarSummary = calendar,
                haWebhookUrl = ha,
                ncUrl = ncUrl,
                ncUser = ncUser,
                ncAppPassword = ncPassword,
            ))
            saved = true
        }, Modifier.fillMaxWidth()) { Text(stringResource(if (saved) R.string.saved else R.string.save)) }

        AshtraySection()
        DangerZone()
    }
}

@Composable
private fun AshtraySection() {
    val context = LocalContext.current
    val res = LocalResources.current
    val state = remember { AppState(context) }
    val scope = rememberCoroutineScope()
    var address by remember { mutableStateOf(state.ashtrayAddress) }
    var status by remember { mutableStateOf(ashtrayStatus(res, state)) }
    var busy by remember { mutableStateOf(false) }

    val btPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {}

    fun run(message: Int, block: suspend () -> Unit) {
        if (context.checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            btPermission.launch(arrayOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT))
            return
        }
        scope.launch {
            busy = true
            status = res.getString(message)
            try { block() } catch (e: Exception) { status = res.getString(R.string.error, e.message) }
            busy = false
        }
    }

    Section(stringResource(R.string.section_ashtray))
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(stringResource(R.string.ashtray_intro))
            TextButton(onClick = { openInfo(context) }) { Text(stringResource(R.string.ashtray_info_link)) }
            Text(address?.let { stringResource(R.string.paired, it) } ?: stringResource(R.string.not_paired))
            if (status.isNotEmpty()) Text(status, style = MaterialTheme.typography.bodySmall)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(enabled = !busy, onClick = {
                    run(R.string.ashtray_searching) {
                        val found = AshtrayBle.scan(context)
                        if (found == null) {
                            status = res.getString(R.string.ashtray_not_found)
                        } else {
                            state.ashtrayAddress = found
                            state.ashtrayNextSeq = -1 // erster Abgleich übernimmt keine alten Ereignisse
                            address = found
                            Background.schedule(context) // registriert auch den Hintergrund-Scan
                            AshtraySync.sync(context)
                            status = ashtrayStatus(res, state)
                        }
                    }
                }) { Text(stringResource(if (address == null) R.string.pair else R.string.pair_again)) }
                if (address != null) {
                    OutlinedButton(enabled = !busy, onClick = {
                        run(R.string.syncing) { AshtraySync.sync(context); status = ashtrayStatus(res, state) }
                    }) { Text(stringResource(R.string.sync_now)) }
                    TextButton(enabled = !busy, onClick = {
                        state.ashtrayAddress = null
                        de.superascher.counter.ashtray.Presence.unregister(context)
                        address = null
                        status = ""
                        Background.schedule(context)
                    }) { Text(stringResource(R.string.unpair)) }
                }
            }
        }
    }
}

private fun ashtrayStatus(res: android.content.res.Resources, state: AppState): String {
    if (state.ashtrayLastSync == 0L) return ""
    val time = DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(Date(state.ashtrayLastSync))
    return res.getString(R.string.last_sync, time, state.ashtrayStatus)
}

@Composable
private fun DangerZone() {
    val context = LocalContext.current
    var step by remember { mutableIntStateOf(0) }
    Section(stringResource(R.string.section_data))
    Hint(stringResource(R.string.data_hint))
    TextButton(onClick = { step = 1 }) { Text(stringResource(R.string.delete_all), color = MaterialTheme.colorScheme.error) }
    if (step > 0) {
        AlertDialog(
            onDismissRequest = { step = 0 },
            title = { Text(stringResource(if (step == 1) R.string.delete_all_title else R.string.delete_all_confirm_title)) },
            text = { Text(stringResource(if (step == 1) R.string.delete_all_text else R.string.delete_all_confirm_text)) },
            confirmButton = {
                TextButton(onClick = {
                    if (step == 1) step = 2 else {
                        EntryStore.get(context).deleteAll()
                        Reminders.reschedule(context)
                        step = 0
                    }
                }) { Text(stringResource(if (step == 1) R.string.next else R.string.delete_final), color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = { TextButton(onClick = { step = 0 }) { Text(stringResource(R.string.cancel)) } },
        )
    }
}

@Composable
private fun Section(title: String) =
    Text(title, style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(top = 16.dp))

@Composable
private fun Hint(text: String) = Text(text, style = MaterialTheme.typography.bodySmall)

@Composable
private fun NumberField(label: String, value: String, onChange: (String) -> Unit) =
    OutlinedTextField(value, onChange, Modifier.fillMaxWidth(), singleLine = true,
        label = { Text(label) },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal))

@Composable
private fun SwitchRow(label: String, checked: Boolean, onChange: (Boolean) -> Unit) =
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(label, Modifier.weight(1f))
        Switch(checked, onChange)
    }

@Composable
private fun NextcloudSection(
    url: String, user: String, password: String,
    onUrl: (String) -> Unit, onUser: (String) -> Unit, onPassword: (String) -> Unit,
) {
    val context = LocalContext.current
    val res = LocalResources.current
    val state = remember { AppState(context) }
    val scope = rememberCoroutineScope()
    var status by remember { mutableStateOf(ncStatus(res, state)) }

    Section(stringResource(R.string.section_nc))
    Hint(stringResource(R.string.nc_hint))
    OutlinedTextField(url, onUrl, Modifier.fillMaxWidth(), singleLine = true,
        label = { Text(stringResource(R.string.nc_server)) },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri))
    OutlinedTextField(user, onUser, Modifier.fillMaxWidth(), singleLine = true, label = { Text(stringResource(R.string.nc_user)) })
    OutlinedTextField(password, onPassword, Modifier.fillMaxWidth(), singleLine = true,
        label = { Text(stringResource(R.string.nc_password)) },
        visualTransformation = androidx.compose.ui.text.input.PasswordVisualTransformation())
    if (url.isNotBlank() && !Settings.validUrl(url)) {
        Text(stringResource(R.string.nc_url_invalid), color = MaterialTheme.colorScheme.error)
    }
    Hint(stringResource(R.string.nc_password_hint))
    if (status.isNotEmpty()) Text(status, style = MaterialTheme.typography.bodySmall)
    if (Settings.validUrl(url) && user.isNotEmpty() && password.isNotEmpty()) {
        OutlinedButton(onClick = {
            scope.launch {
                status = res.getString(R.string.nc_checking)
                status = try {
                    kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
                        de.superascher.counter.sync.Nextcloud.test(
                            context, Settings(ncUrl = url.trim(), ncUser = user.trim(), ncAppPassword = password.trim())
                        )
                    }
                    res.getString(R.string.nc_ok)
                } catch (e: Exception) {
                    res.getString(R.string.error, e.message)
                }
            }
        }) { Text(stringResource(R.string.nc_test)) }
    }
}

private fun ncStatus(res: android.content.res.Resources, state: AppState): String {
    if (state.ncLastSync == 0L) return ""
    val time = DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(Date(state.ncLastSync))
    return res.getString(R.string.nc_last, time, state.ncStatus)
}
