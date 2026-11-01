from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel: str, text: str):
    (ROOT / rel).write_text(text, encoding="utf-8")


def rw(rel: str, old: str, new: str, count: int = 1):
    s = read(rel)
    if old not in s:
        raise RuntimeError(f"Expected snippet not found in {rel}: {old[:180]!r}")
    write(rel, s.replace(old, new, count))

# -----------------------------------------------------------------------------
# Music: separate "this item opens an album" from "this item plays audio-only".
# This prevents stale playback context (including Movies) from affecting album routing.
# -----------------------------------------------------------------------------
music = "app/src/main/kotlin/dev/limitedio/pipetv/ui/MusicPage.kt"
rw(music,
'''    fun picks(pick: (Item) -> Unit, menu: (Item) -> Unit) {
        grid.onPick = { item -> Session.armMusic(); pick(item) }
        grid.onMenu = menu
    }
''',
'''    fun picks(pick: (Item) -> Unit, menu: (Item) -> Unit) {
        grid.onPick = { item ->
            if (item.kind == Item.PLAYLIST) Session.armMusicAlbum() else Session.armMusic()
            pick(item)
        }
        grid.onMenu = menu
    }
''')

session = "app/src/main/kotlin/dev/limitedio/pipetv/media/Session.kt"
rw(session,
'''    fun changed() = onChange() ; fun noExpand() { expand = false }
    fun armMusic() { nextMusic = true }
    fun takeMusicAlbumArm(): Boolean { val armed = nextMusic; if (armed) nextMusic = false; return armed }
''',
'''    fun changed() = onChange() ; fun noExpand() { expand = false }
    private var nextMusicAlbum = false
    fun armMusic() { nextMusic = true }
    fun armMusicAlbum() { nextMusicAlbum = true }
    fun takeMusicAlbumArm(): Boolean {
        val armed = nextMusicAlbum
        nextMusicAlbum = false
        return armed
    }
''')

rw(session,
'''        Progress.save(); token++; item = null; pending = null; info = null; musicMode = false; longForm = false; nextMusic = false; musicQueue = emptyList(); musicIndex = -1; Progress.cancel(); SponsorBlock.reset(); Recovery.reset(); Subs.select(null)
''',
'''        Progress.save(); token++; item = null; pending = null; info = null; musicMode = false; longForm = false; nextMusic = false; nextMusicAlbum = false; musicQueue = emptyList(); musicIndex = -1; Progress.cancel(); SponsorBlock.reset(); Recovery.reset(); Subs.select(null)
''')

# -----------------------------------------------------------------------------
# Movies: never leave the UI visually locked forever if extractor/network stalls.
# The worker may still finish later and replace the message with real results.
# -----------------------------------------------------------------------------
pop = "app/src/main/kotlin/dev/limitedio/pipetv/ui/PopularPage.kt"
rw(pop,
'''        moviePages.clear(); movieIds.clear(); moviePageCursor = 0
        grid.items = emptyList(); grid.message = null; grid.loading = false; grid.busy = true
        Bg.io({
''',
'''        moviePages.clear(); movieIds.clear(); moviePageCursor = 0
        grid.items = emptyList(); grid.message = null; grid.loading = false; grid.busy = true
        Bg.main.postDelayed({
            if (t == ask && chips.sel == MOVIES && grid.busy) {
                grid.busy = false
                grid.loading = false
                grid.message = if (S.cur.code == "pt")
                    "A busca de filmes está demorando. Pressione OK para tentar novamente."
                else "Movie search is taking longer than expected. Press OK to retry."
                grid.invalidate()
            }
        }, 12_000L)
        Bg.io({
''')

# When switching away from Movies, clear any visual loading state immediately.
rw(pop,
'''    private fun show(i: Int, force: Boolean = false) {
        if (i == MOVIES) { showMovies(force); return }
        val t = ++ask
''',
'''    private fun show(i: Int, force: Boolean = false) {
        if (i == MOVIES) { showMovies(force); return }
        grid.loading = false
        val t = ++ask
''')

print("VórticeTv v0.1.11 context isolation patch applied")
