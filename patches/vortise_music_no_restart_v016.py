from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src")


def rw(rel: str, old: str, new: str, count: int = 1):
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    if old not in s:
        raise RuntimeError(f"Expected snippet not found in {rel}: {old[:180]!r}")
    p.write_text(s.replace(old, new, count), encoding="utf-8")

# Root cause of repeated/stuttering lyrics in audio-only mode:
# Progress.watchFrames() treats 'no rendered video frame' as a decoder failure and calls
# Recovery.noPicture(), which restarts the source after 3.5s. In Music there is intentionally
# no video frame, so the watchdog must never run.
progress = "app/src/main/kotlin/dev/limitedio/pipetv/media/Progress.kt"
rw(
    progress,
'''    fun watchFrames() {
        val t = Session.token; val si = Session.info ?: return
''',
'''    fun watchFrames() {
        if (Session.musicMode) {
            dog?.let(Bg.main::removeCallbacks)
            dog = null
            return
        }
        val t = Session.token; val si = Session.info ?: return
''')

# Defensive guard: even if noPicture() is called from another future code path, it may not
# restart an audio-only Music source.
recovery = "app/src/main/kotlin/dev/limitedio/pipetv/media/Recovery.kt"
rw(
    recovery,
'''    fun noPicture() {
        if (Session.safe >= 2) return onError()
''',
'''    fun noPicture() {
        if (Session.musicMode) return
        if (Session.safe >= 2) return onError()
''')

# Music errors should refresh the direct audio URL at the exact position rather than executing
# the video quality fallback first. This avoids unnecessary source restarts and backward jumps.
rw(
    recovery,
'''    fun onError() {
        tries++
        if (tries == 1 && lowerQuality()) return
''',
'''    fun onError() {
        tries++
        if (Session.musicMode) {
            if (tries <= 2) return refresh()
            failed = true; Session.changed()
            Bg.main.removeCallbacks(retry); Bg.main.postDelayed(retry, minOf(30_000L, 3_000L * tries))
            return
        }
        if (tries == 1 && lowerQuality()) return
''')

# Preserve the furthest known playback position across a Music refresh so a retry cannot seek
# backwards because of a stale currentPosition sample.
rw(
    recovery,
'''    private var tries = 0
    private val retry = Runnable { refresh() }
''',
'''    private var tries = 0
    private var musicFloor = 0L
    private val retry = Runnable { refresh() }
''')
rw(
    recovery,
'''    fun reset() { tries = 0; failed = false; Bg.main.removeCallbacks(retry) }
''',
'''    fun reset() { tries = 0; failed = false; musicFloor = 0L; Bg.main.removeCallbacks(retry) }
''')
rw(
    recovery,
'''        val it = Session.item ?: return; val pos = Engine.exo.currentPosition; val t = Session.token
''',
'''        val it = Session.item ?: return
        val current = Engine.exo.currentPosition.coerceAtLeast(0L)
        if (Session.musicMode) musicFloor = maxOf(musicFloor, current)
        val pos = if (Session.musicMode) musicFloor else current
        val t = Session.token
''')

print("VórticeTv v0.1.6 Music no-restart patch applied")
