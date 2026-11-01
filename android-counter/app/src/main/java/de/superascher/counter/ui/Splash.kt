package de.superascher.counter.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import de.superascher.counter.R

/** Anteil der Bildschirmhöhe, an dem das Zigaretten-Band liegt (wie in der Flagge knapp über der Mitte). */
private const val BAND_TOP = 0.52f
private const val BAND_HEIGHT = 0.045f

/**
 * Startbildschirm im Look der Projekt-Flagge (design/brand-flag.jpg): oben Kaffee mit drei Rauten
 * und App-Namen, dann die Zigarette als Band, unten Espresso mit dem Slogan. Wird von [MainActivity]
 * kurz über der App eingeblendet.
 */
@Composable
fun Splash() {
    Box(Modifier.fillMaxSize()) {
        Canvas(Modifier.fillMaxSize()) {
            val w = size.width
            val h = size.height
            val bandTop = h * BAND_TOP
            val bandH = h * BAND_HEIGHT
            drawRect(Brand.Kaffee, Offset.Zero, Size(w, bandTop))
            drawRect(Brand.Espresso, Offset(0f, bandTop + bandH), Size(w, h - bandTop - bandH))
            // Zigarette: Filter | Papier | Asche, Proportionen wie in der Flagge
            drawRect(Brand.Filter, Offset(0f, bandTop), Size(w * 0.285f, bandH))
            drawRect(Brand.Papier, Offset(w * 0.285f, bandTop), Size(w * 0.573f, bandH))
            drawRect(Brand.Asche, Offset(w * 0.858f, bandTop), Size(w * 0.142f, bandH))
            // Drei Rauten oben links
            val r = w * 0.085f
            val gap = r * 0.18f
            fun diamond(cx: Float, cy: Float) = drawPath(
                Path().apply {
                    moveTo(cx, cy - r); lineTo(cx + r, cy); lineTo(cx, cy + r); lineTo(cx - r, cy); close()
                },
                Brand.Papier,
            )
            val x0 = w * 0.2f
            val y0 = h * 0.14f
            diamond(x0, y0)
            diamond(x0 + r + gap, y0 + r + gap)
            diamond(x0, y0 + 2 * (r + gap))
        }
        Column(
            Modifier.fillMaxWidth().fillMaxSize().padding(horizontal = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Bottom,
        ) {
            Text(
                stringResource(R.string.app_name),
                color = Brand.Papier, fontSize = 34.sp, fontWeight = FontWeight.Bold,
            )
            Box(Modifier.padding(top = 8.dp, bottom = 64.dp)) {
                Text(
                    stringResource(R.string.slogan),
                    color = Brand.Filter, fontSize = 20.sp, textAlign = TextAlign.Center,
                )
            }
        }
    }
}
