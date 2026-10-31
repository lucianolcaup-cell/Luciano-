from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src")

voice = ROOT / "app/src/main/kotlin/dev/limitedio/pipetv/ui/input/Voice.kt"
voice.parent.mkdir(parents=True, exist_ok=True)
voice.write_text(r'''package dev.limitedio.pipetv.ui.input

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import dev.limitedio.pipetv.Bg
import dev.limitedio.pipetv.i18n.S

/**
 * VórticeTv voice search tuned for Android TV remotes and TV microphones.
 * - Explicit pt-BR locale when the UI is Portuguese.
 * - Longer speech window for users speaking from the sofa.
 * - Reuses a useful partial transcript instead of throwing it away on timeout/no-match.
 * - One controlled retry for common transient recognizer errors.
 */
object Voice {
    var active = false; private set
    var level = 0f; private set
    var partial = ""; private set
    var onState: () -> Unit = {}
    var onResult: (String) -> Unit = {}
    var onFail: (Boolean) -> Unit = {}

    private var rec: SpeechRecognizer? = null
    private var ctx: Context? = null
    private var retries = 0
    private var heardSpeech = false
    private var generation = 0

    fun available(c: Context) = SpeechRecognizer.isRecognitionAvailable(c)

    fun start(c: Context) {
        ctx = c
        retries = 0
        generation++
        begin(generation)
    }

    private fun begin(token: Int) {
        if (token != generation) return
        val c = ctx ?: return
        destroyRecognizer(false)
        partial = ""
        level = 0f
        heardSpeech = false
        active = true
        onState()

        val r = try {
            SpeechRecognizer.createSpeechRecognizer(c)
        } catch (_: Throwable) {
            active = false
            onState()
            onFail(false)
            return
        }
        rec = r
        r.setRecognitionListener(Listener)

        val language = when (S.cur.code.lowercase()) {
            "pt", "pt-br" -> "pt-BR"
            "en", "en-us" -> "en-US"
            "es", "es-es" -> "es-ES"
            else -> S.cur.code
        }

        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE, language)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, language)
            .putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            .putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 5)
            .putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 3_000L)
            .putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1_800L)
            .putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 1_200L)

        try {
            r.startListening(intent)
        } catch (_: Throwable) {
            destroyRecognizer(true)
            onFail(false)
        }
    }

    fun stop() {
        generation++
        retries = 0
        destroyRecognizer(true)
    }

    private fun destroyRecognizer(notify: Boolean) {
        runCatching { rec?.cancel() }
        runCatching { rec?.destroy() }
        rec = null
        if (active) {
            active = false
            if (notify) onState()
        }
    }

    private fun finishWith(text: String?) {
        val result = text?.trim().orEmpty()
        destroyRecognizer(true)
        if (result.isNotEmpty()) onResult(result) else onFail(true)
    }

    private fun retryOrFail(error: Int) {
        val usefulPartial = partial.trim()
        if (usefulPartial.length >= 2 && error in setOf(
                SpeechRecognizer.ERROR_NO_MATCH,
                SpeechRecognizer.ERROR_SPEECH_TIMEOUT,
                SpeechRecognizer.ERROR_SERVER,
                SpeechRecognizer.ERROR_NETWORK_TIMEOUT,
                SpeechRecognizer.ERROR_NETWORK
            )) {
            finishWith(usefulPartial)
            return
        }

        val transient = error == SpeechRecognizer.ERROR_NO_MATCH ||
            error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT ||
            error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY ||
            error == SpeechRecognizer.ERROR_SERVER ||
            error == SpeechRecognizer.ERROR_NETWORK_TIMEOUT

        if (transient && retries < 1) {
            retries++
            val token = generation
            destroyRecognizer(true)
            Bg.main.postDelayed({ begin(token) }, 450L)
            return
        }

        destroyRecognizer(true)
        onFail(error == SpeechRecognizer.ERROR_NO_MATCH || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT)
    }

    private object Listener : RecognitionListener {
        override fun onReadyForSpeech(params: Bundle?) {
            level = 0.05f
            onState()
        }

        override fun onBeginningOfSpeech() {
            heardSpeech = true
            onState()
        }

        override fun onRmsChanged(rmsdB: Float) {
            // TV microphones often report low RMS values. This mapping gives useful visual feedback
            // without changing the recognizer's own threshold.
            level = ((rmsdB + 8f) / 16f).coerceIn(0f, 1f)
            onState()
        }

        override fun onPartialResults(bundle: Bundle) {
            first(bundle)?.takeIf { it.isNotBlank() }?.let { partial = it }
            onState()
        }

        override fun onResults(bundle: Bundle) {
            val result = first(bundle)?.takeIf { it.isNotBlank() } ?: partial.takeIf { it.isNotBlank() }
            finishWith(result)
        }

        override fun onError(error: Int) = retryOrFail(error)
        override fun onBufferReceived(buffer: ByteArray?) {}
        override fun onEndOfSpeech() {
            if (heardSpeech) onState()
        }
        override fun onEvent(eventType: Int, params: Bundle?) {}

        private fun first(bundle: Bundle): String? =
            bundle.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                ?.firstOrNull { it.isNotBlank() }
    }
}
''', encoding="utf-8")

print("VórticeTv v0.1.3 voice patch applied successfully")
