from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src")


def rw(rel: str, old: str, new: str, count: int = 1):
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    if old not in s:
        raise RuntimeError(f"Expected snippet not found in {rel}: {old[:180]!r}")
    p.write_text(s.replace(old, new, count), encoding="utf-8")

# More headroom for ordinary video playback. Direct extracted streams keep platform ads out;
# this patch only changes buffering/recovery behaviour.
engine = "app/src/main/kotlin/dev/limitedio/pipetv/media/Engine.kt"
rw(engine,
'''        private val base: LoadControl = DefaultLoadControl.Builder()
            .setBufferDurationsMs(20_000, 90_000, 1_500, 3_500)
            .setPrioritizeTimeOverSizeThresholds(true)
            .build()
''',
'''        private val base: LoadControl = DefaultLoadControl.Builder()
            .setBufferDurationsMs(30_000, 120_000, 2_500, 6_000)
            .setPrioritizeTimeOverSizeThresholds(true)
            .build()
''')

# Music keeps its dedicated cushion. Long-form video gets a larger startup/rebuffer margin.
rw(engine,
'''        override fun shouldStartPlayback(parameters: LoadControl.Parameters): Boolean {
            if (!Session.musicMode && !Session.longForm) return base.shouldStartPlayback(parameters)
            val requiredUs = if (parameters.rebuffering) 8_000_000L else 5_000_000L
            return parameters.bufferedDurationUs >= requiredUs || parameters.bufferedDurationUs == androidx.media3.common.C.TIME_UNSET
        }
''',
'''        override fun shouldStartPlayback(parameters: LoadControl.Parameters): Boolean {
            if (!Session.musicMode && !Session.longForm) return base.shouldStartPlayback(parameters)
            val requiredUs = when {
                Session.musicMode && parameters.rebuffering -> 8_000_000L
                Session.musicMode -> 5_000_000L
                Session.longForm && parameters.rebuffering -> 12_000_000L
                else -> 8_000_000L
            }
            return parameters.bufferedDurationUs >= requiredUs || parameters.bufferedDurationUs == androidx.media3.common.C.TIME_UNSET
        }
''')

# Do not restart a video for a short Wi-Fi hiccup. Let the enlarged buffer recover first.
rw(engine,
'''            if (state == Player.STATE_BUFFERING && exo.playWhenReady) Bg.main.postDelayed(stallFallback, 7_000)
''',
'''            if (state == Player.STATE_BUFFERING && exo.playWhenReady) Bg.main.postDelayed(stallFallback, if (Session.longForm) 12_000L else 10_000L)
''')

# More tolerant HTTP read window for long videos / unstable Wi-Fi. This does not increase RAM use.
sources = "app/src/main/kotlin/dev/limitedio/pipetv/media/Sources.kt"
rw(sources,
'''        .setConnectTimeoutMs(15_000).setReadTimeoutMs(20_000)
''',
'''        .setConnectTimeoutMs(20_000).setReadTimeoutMs(30_000)
''')

print("VórticeTv v0.1.7 video smoothness patch applied")
