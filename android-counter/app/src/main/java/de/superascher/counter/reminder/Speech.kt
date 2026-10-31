package de.superascher.counter.reminder

import android.content.Context
import android.content.res.Configuration
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import java.util.Locale

/**
 * Sprachausgabe auf dem Handy über die System-Engine (z. B. GrapheneOS Speech Services).
 * In der Sprache des Handys, wenn die App sie spricht (Englisch, Deutsch) und die Engine eine
 * Stimme dafür hat. Sonst Englisch: eine englische Stimme bringt jede Engine mit.
 */
object Speech {
    private val APP_LANGUAGES = setOf("en", "de")

    /** [onDone] kommt nach dem Sprechen oder bei einem Fehler, genau einmal. */
    fun say(context: Context, textRes: Int, vararg args: Any, onDone: () -> Unit = {}) {
        val app = context.applicationContext
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
}
