from pathlib import Path
import re
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src")


def load(rel: str):
    p = ROOT / rel
    return p, p.read_text(encoding="utf-8")


def save(p: Path, s: str):
    p.write_text(s, encoding="utf-8")

# -----------------------------------------------------------------------------
# 1) Manual quality must be authoritative.
# Clear any prior automatic safe-mode cap (720/480/360) before reloading.
# -----------------------------------------------------------------------------
p, s = load("app/src/main/kotlin/dev/limitedio/pipetv/media/Session.kt")
old = '    fun pickHeight(height: Int?) { manualHeight = height; cap = 2160; reload(); changed() }\n'
new = '''    fun pickHeight(height: Int?) {
        manualHeight = height
        cap = 2160
        safe = 0
        Recovery.reset()
        reload()
        changed()
    }
'''
if old not in s:
    raise RuntimeError("Session.pickHeight() not found")
s = s.replace(old, new, 1)
# Reset the visible measured resolution whenever a source is re-prepared.
needle = '''        Engine.frame = false
'''
if needle not in s:
    raise RuntimeError("Session.start Engine.frame reset not found")
s = s.replace(needle, '''        Engine.frame = false
        Engine.resetVideoSize()
''', 1)
save(p, s)

# -----------------------------------------------------------------------------
# 2) Do not silently downgrade a manually selected 1440p/2160p stream.
# For manual quality, refresh expiring URLs at the same height; normal/default
# quality keeps the existing staged fallback for smooth playback.
# -----------------------------------------------------------------------------
p, s = load("app/src/main/kotlin/dev/limitedio/pipetv/media/Recovery.kt")
pattern = re.compile(
    r'''    /\*\* Long buffering: recover in bounded stages instead of leaving an infinite spinner\. \*/\n'''
    r'''    fun onStall\(\) \{.*?\n    \}\n''',
    re.S,
)
m = pattern.search(s)
if not m:
    raise RuntimeError("Recovery.onStall() bounded-stage implementation not found")
replacement = '''    /** Long buffering: recover without lying about a manually selected quality. */
    fun onStall() {
        if (Session.musicMode || Session.info == null || failed) return
        Bg.main.removeCallbacks(stable)

        // Manual 1440p/2160p is explicit user intent. Never keep the menu on 4K while
        // secretly forcing a 720p safe stream. Refresh the URL at the same quality first.
        if (Session.manualHeight != null) {
            stallStage++
            when (stallStage) {
                1, 2 -> refresh()
                else -> {
                    failed = true
                    Engine.exo.pause()
                    Session.changed()
                }
            }
            return
        }

        val pos = Engine.exo.currentPosition.coerceAtLeast(0L)
        stallStage++
        when (stallStage) {
            1 -> {
                Session.safe = maxOf(Session.safe, 2)
                Session.cap = minOf(Session.cap, 720)
                Session.start(pos)
            }
            2 -> refresh()
            3 -> {
                Session.safe = maxOf(Session.safe, 2)
                Session.cap = minOf(Session.cap, 480)
                Session.start(pos)
            }
            4 -> refresh()
            5 -> {
                Session.safe = maxOf(Session.safe, 2)
                Session.cap = minOf(Session.cap, 360)
                Session.start(pos)
            }
            else -> {
                failed = true
                Engine.exo.pause()
                Session.changed()
            }
        }
    }
'''
s = s[:m.start()] + replacement + s[m.end():]
save(p, s)

# -----------------------------------------------------------------------------
# 3) Track what ExoPlayer actually renders so the quality menu can confirm it.
# -----------------------------------------------------------------------------
p, s = load("app/src/main/kotlin/dev/limitedio/pipetv/media/Engine.kt")
needle = '''    @Volatile var aspect = 16f / 9f; private set
'''
if needle not in s:
    raise RuntimeError("Engine aspect field not found")
s = s.replace(needle, '''    @Volatile var aspect = 16f / 9f; private set
    @Volatile var videoHeight = 0; private set
    fun resetVideoSize() { videoHeight = 0 }
''', 1)
needle = '''            if (size.width > 0 && size.height > 0) {
                val ar = size.width * size.pixelWidthHeightRatio / size.height
'''
if needle not in s:
    raise RuntimeError("Engine onVideoSizeChanged block not found")
s = s.replace(needle, '''            if (size.width > 0 && size.height > 0) {
                videoHeight = size.height
                val ar = size.width * size.pixelWidthHeightRatio / size.height
''', 1)
save(p, s)

# -----------------------------------------------------------------------------
# 4) Player menu: selection applies immediately; show measured playback height.
# -----------------------------------------------------------------------------
p, s = load("app/src/main/kotlin/dev/limitedio/pipetv/ui/PlayerMenu.kt")
old = '''            StepRow({ S.t(K.QUALITY) }, { if (S.cur.code == "pt") "Somente neste vídeo" else "This video only" },
'''
new = '''            StepRow({ S.t(K.QUALITY) }, {
                when {
                    Engine.videoHeight > 0 && S.cur.code == "pt" -> "Em reprodução: ${Engine.videoHeight}p"
                    Engine.videoHeight > 0 -> "Playing: ${Engine.videoHeight}p"
                    S.cur.code == "pt" -> "Aplicação imediata · somente neste vídeo"
                    else -> "Applies immediately · this video only"
                }
            },
'''
if old not in s:
    raise RuntimeError("PlayerMenu quality StepRow not found")
s = s.replace(old, new, 1)
save(p, s)

print("VórticeTv v0.1.11 manual 4K authority + actual resolution indicator applied")
