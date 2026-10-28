package de.superascher.counter.ui

import android.Manifest
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import de.superascher.counter.R
import de.superascher.counter.data.EntryStore
import de.superascher.counter.data.Settings
import de.superascher.counter.reminder.Reminders

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent { AppTheme { AppScreen() } }
    }

    override fun onResume() {
        super.onResume()
        // Beim Öffnen den Stand der anderen Geräte holen
        if (Settings.load(this).ncEnabled) de.superascher.counter.sync.Nextcloud.kick(this)
    }
}

@Composable
private fun AppTheme(content: @Composable () -> Unit) {
    val context = LocalContext.current
    val colors = if (isSystemInDarkTheme()) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
    MaterialTheme(colorScheme = colors, content = content)
}

@Composable
private fun AppScreen() {
    val context = LocalContext.current
    val entries by EntryStore.get(context).entries.collectAsStateWithLifecycle()
    var settings by remember { mutableStateOf(Settings.load(context)) }
    var tab by remember { mutableIntStateOf(0) }

    val notificationPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) {}
    LaunchedEffect(Unit) { notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS) }

    Scaffold(
        bottomBar = {
            NavigationBar {
                listOf("🚬" to R.string.tab_counter, "📊" to R.string.tab_stats, "⚙️" to R.string.tab_settings).forEachIndexed { i, (icon, label) ->
                    NavigationBarItem(
                        selected = tab == i,
                        onClick = { tab = i },
                        icon = { Text(icon) },
                        label = { Text(stringResource(label)) },
                    )
                }
            }
        },
    ) { padding ->
        val modifier = Modifier.padding(padding)
        when (tab) {
            0 -> HomeScreen(entries, settings, modifier, onOpenAshtray = { tab = 2 })
            1 -> StatsScreen(entries, settings, modifier)
            else -> SettingsScreen(settings, modifier) { updated ->
                Settings.save(context, updated)
                settings = updated
                Reminders.reschedule(context)
                de.superascher.counter.ashtray.Background.schedule(context) // startet ggf. auch die Nextcloud-Übertragung
            }
        }
    }
}
