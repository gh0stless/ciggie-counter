package de.superascher.counter.reminder

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import java.util.Locale

/**
 * Sprachausgabe auf dem Handy über die System-Engine (z. B. GrapheneOS Speech Services).
 * Bewusst immer Englisch: eine englische Stimme bringt jede Engine mit, eine deutsche nicht.
 */
object Speech {
    fun say(context: Context, text: String) {
        lateinit var tts: TextToSpeech
        tts = TextToSpeech(context.applicationContext) { status ->
            if (status != TextToSpeech.SUCCESS || tts.setLanguage(Locale.US) < TextToSpeech.LANG_AVAILABLE) {
                tts.shutdown()
                return@TextToSpeech
            }
            // Engine nach dem Sprechen wieder freigeben, jede Ansage hat ihre eigene
            tts.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) = Unit
                override fun onDone(utteranceId: String?) = tts.shutdown()
                @Deprecated("Deprecated in Java")
                override fun onError(utteranceId: String?) = tts.shutdown()
            })
            tts.speak(text, TextToSpeech.QUEUE_ADD, null, "count")
        }
    }
}
