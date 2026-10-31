from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src")

def rw(rel, old, new, count=1):
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    if old not in s:
        raise RuntimeError(f"Expected snippet not found in {rel}: {old[:100]!r}")
    p.write_text(s.replace(old, new, count), encoding="utf-8")

# Audio-only mode never renders a video frame. Treat READY audio as ready instead of
# showing an endless spinner over the album artwork.
stage = "app/src/main/kotlin/dev/limitedio/pipetv/ui/Stage.kt"
rw(stage, 'import android.view.ViewGroup\n', 'import android.view.ViewGroup\nimport androidx.media3.common.Player\n')
rw(stage,
   '    override val animating get() = Session.active && !Engine.frame\n',
   '    private val musicReady get() = Session.musicMode && Engine.exo.playbackState == Player.STATE_READY\n    override val animating get() = Session.active && !Engine.frame && !musicReady\n')
rw(stage,
   '        if (Engine.frame) return\n',
   '        if (Engine.frame) return\n        val readyAudio = musicReady\n')
rw(stage,
   '        c.drawRect(0f, 0f, w, h, shade)\n        val s = minOf(Ui.u(44), h * .16f)\n        Spinner.draw(c, w / 2, h * .42f, s, 1f)\n        if (h > Ui.u(300)) Txt.draw(c, Txt.fit(text, S.f(K.OPENING, it.title), w - Ui.u(160)), 0f, h * .42f + s + Ui.u(60), w, text, true)\n',
   '        shade.alpha = if (readyAudio) 72 else 153\n        c.drawRect(0f, 0f, w, h, shade)\n        if (readyAudio) return\n        val s = minOf(Ui.u(44), h * .16f)\n        Spinner.draw(c, w / 2, h * .42f, s, 1f)\n        if (h > Ui.u(300)) Txt.draw(c, Txt.fit(text, S.f(K.OPENING, it.title), w - Ui.u(160)), 0f, h * .42f + s + Ui.u(60), w, text, true)\n')

# Video stall fallback must not restart an audio-only music stream.
recovery = "app/src/main/kotlin/dev/limitedio/pipetv/media/Recovery.kt"
rw(recovery,
   '        if (Session.info == null || Session.manualHeight != null || (Prefs.quality > 1080 && Prefs.quality != 0)) return\n',
   '        if (Session.musicMode || Session.info == null || Session.manualHeight != null || (Prefs.quality > 1080 && Prefs.quality != 0)) return\n')

# Give continuous audio more headroom. Music bitrates are small, so this costs little memory
# but reduces rebuffering on Wi-Fi jitter. Startup remains quick.
engine = "app/src/main/kotlin/dev/limitedio/pipetv/media/Engine.kt"
rw(engine,
   '        val load = DefaultLoadControl.Builder().setBufferDurationsMs(12_000, 45_000, 1_500, 3_000).setPrioritizeTimeOverSizeThresholds(true).build()\n',
   '        val load = DefaultLoadControl.Builder().setBufferDurationsMs(20_000, 75_000, 1_500, 3_500).setPrioritizeTimeOverSizeThresholds(true).build()\n')

print("Vortice Music v0.1.4 playback patch applied")
