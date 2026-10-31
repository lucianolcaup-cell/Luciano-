from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src")


def rw(rel: str, old: str, new: str, count: int = 1):
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    if old not in s:
        raise RuntimeError(f"Expected snippet not found in {rel}: {old[:180]!r}")
    p.write_text(s.replace(old, new, count), encoding="utf-8")

# Runtime fix: do not wrap Media3 LoadControl using Kotlin interface delegation.
# Media3 1.5.1 calls getBackBufferDurationUs() while constructing ExoPlayer; the delegated
# wrapper can fall through to the interface's unimplemented default and crash the Activity.
# Use the official DefaultLoadControl implementation directly and tune it through its Builder.
engine = "app/src/main/kotlin/dev/limitedio/pipetv/media/Engine.kt"
p = ROOT / engine
s = p.read_text(encoding="utf-8")
start = s.find("    private class VorticeLoadControl(")
end = s.find("    fun configureAudioUsage", start)
if start < 0 or end < 0:
    raise RuntimeError("VorticeLoadControl block not found in Engine.kt")
s = s[:start] + s[end:]
s = s.replace("import androidx.media3.exoplayer.LoadControl\n", "")
old_load = "        val load = VorticeLoadControl()\n"
new_load = '''        val load = DefaultLoadControl.Builder()
            .setBufferDurationsMs(30_000, 120_000, 5_000, 8_000)
            .setBackBuffer(0, false)
            .setPrioritizeTimeOverSizeThresholds(true)
            .build()
'''
if old_load not in s:
    raise RuntimeError("VorticeLoadControl construction not found in Engine.kt")
s = s.replace(old_load, new_load, 1)
p.write_text(s, encoding="utf-8")

# Do not restart a video for a short Wi-Fi hiccup. Let the enlarged official buffer recover first.
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

print("VórticeTv v0.1.10 Media3 LoadControl crash fix + smoothness patch applied")
