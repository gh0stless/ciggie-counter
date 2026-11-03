package de.superascher.counter.reminder

import android.app.NotificationManager
import android.content.Context
import android.content.res.Configuration
import android.media.AudioManager
import android.media.ToneGenerator
import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import java.util.Locale

/**
 * Sprachausgabe auf dem Handy über die System-Engine (z. B. GrapheneOS Speech Services).
 * In der Sprache des Handys, wenn die App sie spricht (Englisch, Deutsch) und die Engine eine
 * Stimme dafür hat. Sonst Englisch: eine englische Stimme bringt jede Engine mit.
 * Schweigt bei "Nicht stören": Ansagen laufen über die Medienlautstärke, die Android dabei
 * standardmäßig durchlässt (Benachrichtigungen stellt Android selbst stumm).
 */
object Speech {
    private val APP_LANGUAGES = setOf("en", "de")

    /** [onDone] kommt nach dem Sprechen oder bei einem Fehler, genau einmal. */
    fun say(context: Context, textRes: Int, vararg args: Any, onDone: () -> Unit = {}) {
        val app = context.applicationContext
        if (isDoNotDisturb(app)) return onDone()
        lateinit var tts: TextToSpeech
        val finished = java.util.concurrent.atomic.AtomicBoolean(false)
        fun finish() {
            if (finished.compareAndSet(false, true)) {
                tts.shutdown()
                onDone()
            }
        }
        tts = TextToSpeech(app) { status ->
            if (status != TextToSpeech.SUCCESS) {
                finish()
                return@TextToSpeech
            }
            val device = app.resources.configuration.locales[0]
            val locale = when {
                device.language in APP_LANGUAGES && tts.setLanguage(device) >= TextToSpeech.LANG_AVAILABLE -> device
                tts.setLanguage(Locale.US) >= TextToSpeech.LANG_AVAILABLE -> Locale.US
                else -> {
                    finish()
                    return@TextToSpeech
                }
            }
            // Text in derselben Sprache wie die Stimme, auch wenn die App-Oberfläche anders ist
            val config = Configuration(app.resources.configuration).apply { setLocale(locale) }
            val text = app.createConfigurationContext(config).getString(textRes, *args)
            // Engine nach dem Sprechen wieder freigeben, jede Ansage hat ihre eigene
            tts.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) = Unit
                override fun onDone(utteranceId: String?) = finish()
                @Deprecated("Deprecated in Java")
                override fun onError(utteranceId: String?) = finish()
            })
            if (tts.speak(text, TextToSpeech.QUEUE_ADD, null, "speech") != TextToSpeech.SUCCESS) finish()
        }
    }

    /**
     * Kurzer Quittungston über die Medienlautstärke wie die Ansagen. Auch bei "Nicht stören":
     * man hat gerade selbst gezählt und will nur wissen, dass es angekommen ist.
     */
    fun ack(context: Context) {
        val tone = runCatching { ToneGenerator(AudioManager.STREAM_MUSIC, 60) }.getOrNull() ?: return
        tone.startTone(ToneGenerator.TONE_PROP_ACK, 150)
        Handler(Looper.getMainLooper()).postDelayed({ tone.release() }, 400)
    }

    /** "Nicht stören" bzw. ein Modus wie "Schlafenszeit" ist aktiv (keine Berechtigung nötig). */
    fun isDoNotDisturb(context: Context): Boolean =
        when (context.getSystemService(NotificationManager::class.java).currentInterruptionFilter) {
            NotificationManager.INTERRUPTION_FILTER_ALL, NotificationManager.INTERRUPTION_FILTER_UNKNOWN -> false
            else -> true
        }
}
