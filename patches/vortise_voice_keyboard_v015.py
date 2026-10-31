from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src")


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def replace(rel, old, new, count=1):
    s = read(rel)
    if old not in s:
        raise RuntimeError(f"Expected snippet not found in {rel}: {old[:120]!r}")
    write(rel, s.replace(old, new, count))


# 1) Portuguese TV keyboard in alphabetical order, as requested for remote control use.
layouts = "app/src/main/kotlin/dev/limitedio/pipetv/ui/input/Layouts.kt"
replace(
    layouts,
    'Layout("pt", "Português", listOf("qwertyuiop", "asdfghjklç", "zxcvbnmáéãõ")),',
    'Layout("pt", "Português", listOf("abcdefg", "hijklmn", "opqrstu", "vwxyzç", "áéíóúãõâêô")),',
)

# 2) Stronger Android TV voice recognizer flow. SpeechRecognizer owns the physical mic gain,
# so software cannot safely amplify the remote microphone; we improve capture tolerance,
# retries and result selection instead.
voice = "app/src/main/kotlin/dev/limitedio/pipetv/ui/input/Voice.kt"
write(voice, r'''package dev.limitedio.pipetv.ui.input

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import dev.limitedio.pipetv.Bg
import dev.limitedio.pipetv.i18n.S

/** VórticeTv voice search tuned for Android TV remotes / far-field microphones. */
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
    private var generation = 0
    private var bestPartial = ""

    fun available(c: Context) = SpeechRecognizer.isRecognitionAvailable(c)

    fun start(c: Context) {
        ctx = c.applicationContext
        retries = 0
        generation++
        begin(generation, 0L)
    }

    private fun begin(token: Int, delay: Long) {
        if (token != generation) return
        if (delay > 0) {
            Bg.main.postDelayed({ begin(token, 0L) }, delay)
            return
        }
        val c = ctx ?: return
        destroyRecognizer(false)
        partial = ""
        bestPartial = ""
        level = 0f
        active = true
        onState()

        val r = try { SpeechRecognizer.createSpeechRecognizer(c) } catch (_: Throwable) {
            active = false; onState(); onFail(false); return
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
            .putExtra(RecognizerIntent.EXTRA_ONLY_RETURN_LANGUAGE_PREFERENCE, false)
            .putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            .putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 8)
            // Longer windows are important with TV remotes several metres away.
            .putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 5_000L)
            .putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 2_800L)
            .putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 2_000L)

        try { r.startListening(intent) } catch (_: Throwable) {
            destroyRecognizer(true); onFail(false)
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

    private fun finish(text: String?) {
        val result = text?.trim().orEmpty()
        destroyRecognizer(true)
        if (result.length >= 2) onResult(result) else onFail(true)
    }

    private fun retryOrFail(error: Int) {
        val useful = bestPartial.trim().ifEmpty { partial.trim() }
        if (useful.length >= 2 && error in setOf(
                SpeechRecognizer.ERROR_NO_MATCH,
                SpeechRecognizer.ERROR_SPEECH_TIMEOUT,
                SpeechRecognizer.ERROR_SERVER,
                SpeechRecognizer.ERROR_NETWORK_TIMEOUT,
                SpeechRecognizer.ERROR_NETWORK
            )) {
            finish(useful)
            return
        }

        val transient = error == SpeechRecognizer.ERROR_NO_MATCH ||
            error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT ||
            error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY ||
            error == SpeechRecognizer.ERROR_SERVER ||
            error == SpeechRecognizer.ERROR_NETWORK_TIMEOUT ||
            error == SpeechRecognizer.ERROR_NETWORK

        // Two retries: first fast, second slightly longer to let the remote / recognizer recover.
        if (transient && retries < 2) {
            retries++
            val token = generation
            destroyRecognizer(true)
            begin(token, if (retries == 1) 350L else 800L)
            return
        }

        destroyRecognizer(true)
        onFail(error == SpeechRecognizer.ERROR_NO_MATCH || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT)
    }

    private object Listener : RecognitionListener {
        override fun onReadyForSpeech(params: Bundle?) {
            level = 0.08f
            onState()
        }

        override fun onBeginningOfSpeech() {
            level = maxOf(level, 0.12f)
            onState()
        }

        override fun onRmsChanged(rmsdB: Float) {
            // Visual mapping for low-RMS TV microphones. Does not fake recognition gain.
            level = ((rmsdB + 12f) / 18f).coerceIn(0f, 1f)
            onState()
        }

        override fun onPartialResults(bundle: Bundle) {
            val candidates = results(bundle)
            val value = candidates.maxByOrNull { it.trim().length }?.trim().orEmpty()
            if (value.isNotEmpty()) {
                partial = value
                if (value.length >= bestPartial.length) bestPartial = value
            }
            onState()
        }

        override fun onResults(bundle: Bundle) {
            val candidates = results(bundle)
            val scores = bundle.getFloatArray(SpeechRecognizer.CONFIDENCE_SCORES)
            val picked = when {
                !scores.isNullOrEmpty() && candidates.isNotEmpty() -> candidates.indices
                    .maxByOrNull { scores.getOrElse(it) { -1f } }
                    ?.let { candidates[it] }
                candidates.isNotEmpty() -> candidates.maxByOrNull { it.trim().length }
                else -> null
            }
            finish(picked?.takeIf { it.isNotBlank() } ?: bestPartial.takeIf { it.isNotBlank() })
        }

        override fun onError(error: Int) = retryOrFail(error)
        override fun onBufferReceived(buffer: ByteArray?) {}
        override fun onEndOfSpeech() { onState() }
        override fun onEvent(eventType: Int, params: Bundle?) {}

        private fun results(bundle: Bundle): List<String> =
            bundle.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                ?.filter { it.isNotBlank() }
                .orEmpty()
    }
}
''')

# 3) Brand the generic search hint as VórticeTv in Portuguese.
pt = "app/src/main/kotlin/dev/limitedio/pipetv/i18n/lang/Pt.kt"
s = read(pt)
s = s.replace('K.SEARCH_HINT to "Pesquisar no YouTube"', 'K.SEARCH_HINT to "Pesquisar no VórticeTv"')
write(pt, s)

print("VórticeTv v0.1.5 voice + alphabetical PT keyboard patch applied")
