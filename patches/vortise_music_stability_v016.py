from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src")


def rw(rel: str, old: str, new: str, count: int = 1):
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    if old not in s:
        raise RuntimeError(f"Expected snippet not found in {rel}: {old[:160]!r}")
    p.write_text(s.replace(old, new, count), encoding="utf-8")

# 1) Prefer a stable, TV-friendly audio bitrate for Music. Direct audio remains ad-free because
# playback uses the extracted media stream, not the YouTube web player/ad pipeline.
sources = "app/src/main/kotlin/dev/limitedio/pipetv/media/Sources.kt"
rw(
    sources,
'''        val audio = info.audioStreams.filter { it.isUrl }
            .sortedWith(compareByDescending<AudioStream> { it.format == MediaFormat.M4A }.thenByDescending { it.averageBitrate })
        val selected = pick?.takeIf { it.isUrl } ?: audio.firstOrNull()
''',
'''        val audio = info.audioStreams.filter { it.isUrl }
        val m4a = audio.filter { it.format == MediaFormat.M4A }
        // 192 kbps is already transparent for TV listening and is substantially more tolerant
        // of Wi-Fi jitter than blindly taking the largest available stream.
        val stable = m4a.filter { it.averageBitrate in 1..192_000 }.maxByOrNull { it.averageBitrate }
            ?: m4a.maxByOrNull { it.averageBitrate }
            ?: audio.filter { it.averageBitrate in 1..192_000 }.maxByOrNull { it.averageBitrate }
            ?: audio.maxByOrNull { it.averageBitrate }
        val selected = pick?.takeIf { it.isUrl } ?: stable
''')

# 2) Music must not run SponsorBlock seeks. Platform ads are already absent on the direct stream;
# keeping SponsorBlock active here can only introduce avoidable seeks in a continuous audio session.
session = "app/src/main/kotlin/dev/limitedio/pipetv/media/Session.kt"
rw(
    session,
'''        SponsorBlock.load(it.id)
        Progress.schedule()
''',
'''        if (!musicMode) SponsorBlock.load(it.id)
        Progress.schedule()
''')

# Music always plays at natural speed even if the user previously changed video speed.
rw(
    session,
'''        Engine.exo.playbackParameters = PlaybackParameters(Prefs.speed)
        Engine.exo.prepare(); Engine.exo.playWhenReady = true
''',
'''        Engine.exo.playbackParameters = PlaybackParameters(if (musicMode) 1f else Prefs.speed)
        Engine.configureAudioUsage(musicMode)
        Engine.exo.prepare(); Engine.exo.playWhenReady = true
''')

# 3) Dynamic load control: videos keep their quick start, while Music waits for a healthier
# audio cushion before first playback / after any rebuffer. This specifically targets micro-stalls.
engine = "app/src/main/kotlin/dev/limitedio/pipetv/media/Engine.kt"
rw(engine,
'''import androidx.media3.exoplayer.DefaultLoadControl
''',
'''import androidx.media3.exoplayer.DefaultLoadControl
import androidx.media3.exoplayer.LoadControl
''')

rw(engine,
'''object Engine {
''',
'''object Engine {
    private class VorticeLoadControl(
        private val base: LoadControl = DefaultLoadControl.Builder()
            .setBufferDurationsMs(20_000, 90_000, 1_500, 3_500)
            .setPrioritizeTimeOverSizeThresholds(true)
            .build()
    ) : LoadControl by base {
        override fun shouldStartPlayback(parameters: LoadControl.Parameters): Boolean {
            if (!Session.musicMode) return base.shouldStartPlayback(parameters)
            val requiredUs = if (parameters.rebuffering) 8_000_000L else 5_000_000L
            return parameters.bufferedDurationUs >= requiredUs || parameters.bufferedDurationUs == androidx.media3.common.C.TIME_UNSET
        }
    }

    fun configureAudioUsage(music: Boolean) {
        exo.setAudioAttributes(
            AudioAttributes.Builder()
                .setContentType(if (music) C.AUDIO_CONTENT_TYPE_MUSIC else C.AUDIO_CONTENT_TYPE_MOVIE)
                .setUsage(C.USAGE_MEDIA)
                .build(),
            true
        )
    }
''')

# Replace the previous generic load-control instance with the dynamic one.
rw(
    engine,
'''        val load = DefaultLoadControl.Builder().setBufferDurationsMs(20_000, 75_000, 1_500, 3_500).setPrioritizeTimeOverSizeThresholds(true).build()
''',
'''        val load = VorticeLoadControl()
''')

print("VórticeTv v0.1.6 Music stability patch applied")
