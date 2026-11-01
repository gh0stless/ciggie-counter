package de.superascher.counter.ui

import android.Manifest
import android.os.Bundle
import androidx.activity.ComponentActivity
import kotlinx.coroutines.delay
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.foundation.layout.Box
import androidx.compose.animation.fadeOut
import androidx.compose.animation.core.tween
import androidx.compose.animation.EnterTransition
import androidx.compose.animation.AnimatedVisibility
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import de.superascher.counter.R
import de.superascher.counter.data.EntryStore
import de.superascher.counter.data.Settings
import de.superascher.counter.reminder.Reminders

private const val SPLASH_MS = 2000L

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            AppTheme {
                // Startbildschirm nur beim Kaltstart, nicht nach Drehen oder Rückkehr aus dem Hintergrund
                var splash by rememberSaveable { mutableStateOf(true) }
                LaunchedEffect(Unit) {
                    delay(SPLASH_MS)
                    splash = false
                }
                Box {
                    AppScreen()
                    AnimatedVisibility(splash, enter = EnterTransition.None, exit = fadeOut(tween(400))) { Splash() }
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // Beim Öffnen den Stand der anderen Geräte holen
        if (Settings.load(this).syncEnabled) de.superascher.counter.sync.Nextcloud.kick(this)
    }
}

/**
 * Feste Farben aus der Projekt-Flagge (design/brand-flag.jpg): Espresso, Kaffee, Filter, Papier, Asche.
 * Bewusst immer dunkel und ohne Material-You-Farben, damit App, Web-App und Icon gleich aussehen.
 */
internal object Brand {
    val Espresso = Color(0xFF2D0800)
    val Kaffee = Color(0xFF590F02)
    val Filter = Color(0xFFF9A948)
    val Papier = Color(0xFFFFFFFF)
    val Asche = Color(0xFFA1A1A1)
    // Zwischenstufen für Flächen zwischen Espresso und Kaffee
    val Roast1 = Color(0xFF3A0B01)
    val Roast2 = Color(0xFF470D02)
}

private val BrandColors = darkColorScheme(
    primary = Brand.Filter,
    onPrimary = Brand.Espresso,
    primaryContainer = Brand.Kaffee,
    onPrimaryContainer = Brand.Papier,
    secondary = Brand.Asche,
    onSecondary = Brand.Espresso,
    secondaryContainer = Brand.Kaffee,
    onSecondaryContainer = Brand.Papier,
    tertiary = Brand.Filter,
    onTertiary = Brand.Espresso,
    background = Brand.Espresso,
    onBackground = Brand.Papier,
    surface = Brand.Espresso,
    onSurface = Brand.Papier,
    surfaceVariant = Brand.Roast2,
    onSurfaceVariant = Brand.Asche,
    surfaceContainerLowest = Brand.Espresso,
    surfaceContainerLow = Brand.Roast1,
    surfaceContainer = Brand.Roast1,
    surfaceContainerHigh = Brand.Roast2,
    surfaceContainerHighest = Brand.Kaffee,
    outline = Brand.Asche,
    outlineVariant = Brand.Roast2,
)

@Composable
private fun AppTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = BrandColors, content = content)
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
                // Andere Nextcloud oder anderer Nutzer: beim nächsten Abgleich den Server-Stand komplett übernehmen
                if (updated.syncTarget != settings.syncTarget || updated.haUrl.trim().trimEnd('/') != settings.haUrl ||
                    updated.ncUrl.trim().trimEnd('/') != settings.ncUrl || updated.ncUser.trim() != settings.ncUser) {
                    de.superascher.counter.data.AppState(context).syncRev = -1
                }
                Settings.save(context, updated)
                settings = updated
                Reminders.reschedule(context)
                de.superascher.counter.ashtray.Background.schedule(context) // startet ggf. auch die Nextcloud-Übertragung
            }
        }
    }
}
