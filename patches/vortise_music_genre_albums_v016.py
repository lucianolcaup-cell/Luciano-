from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src")
REL = "app/src/main/kotlin/dev/limitedio/pipetv/ui/MusicPage.kt"
P = ROOT / REL
s = P.read_text(encoding="utf-8")


def replace(old: str, new: str, count: int = 1):
    global s
    if old not in s:
        raise RuntimeError(f"Expected snippet not found in {REL}: {old[:140]!r}")
    s = s.replace(old, new, count)

# Genre navigation becomes album-first, matching a TV music-service mental model:
# Genre -> albums/artists -> album tracks. No isolated-song grid on genre entry.
replace(
'''        genres.onPick = { i ->
            search.query = ""; search.invalidate()
            heading = genreNames()[i]
            load(genreQueries()[i], "music_songs")
            setZone(3)
        }
''',
'''        genres.onPick = { i ->
            search.query = ""; search.invalidate()
            types.select(2)
            heading = if (S.cur.code == "pt") "${genreNames()[i]} · Álbuns" else "${genreNames()[i]} · Albums"
            load("${genreQueries()[i]} álbuns", "music_albums")
            setZone(3)
        }
''')

# Retry the exact last album/genre request instead of falling back to a generic tab.
replace(
'''    private var request = 0
''',
'''    private var request = 0
    private var lastQuery = ""
    private var lastFilter = "music_albums"
''')

replace(
'''        grid.onRetry = { if (search.query.isBlank()) loadDefault(types.sel) else runSearch(search.query) }
''',
'''        grid.onRetry = {
            if (lastQuery.isNotBlank()) load(lastQuery, lastFilter)
            else if (search.query.isBlank()) loadDefault(types.sel)
            else runSearch(search.query)
        }
''')

replace(
'''    private fun load(query: String, filter: String) {
        val t = ++request
''',
'''    private fun load(query: String, filter: String) {
        lastQuery = query
        lastFilter = filter
        val t = ++request
''')

# Let genre selection visually move the top content selector to Álbuns without firing
# its normal generic onChange callback.
replace(
'''private class MusicTypeBar(c: Context, private val labels: () -> List<String>) : AnimView(c) {
    var sel = 0; private set; var lit = false; var onChange: (Int) -> Unit = {}
''',
'''private class MusicTypeBar(c: Context, private val labels: () -> List<String>) : AnimView(c) {
    var sel = 0; private set; var lit = false; var onChange: (Int) -> Unit = {}
    fun select(i: Int) { sel = i.coerceIn(0, 3); invalidate() }
''')

# Clarify the hierarchy in the Music header.
replace(
'''        val sub = if (S.cur.code == "pt") "Artistas, músicas, álbuns e gêneros · pesquisa por voz" else "Artists, songs, albums and genres · voice search"
''',
'''        val sub = if (S.cur.code == "pt") "Gêneros por álbuns e artistas · pesquisa por texto ou voz" else "Genres by albums and artists · text or voice search"
''')

P.write_text(s, encoding="utf-8")
print("VórticeTv v0.1.6 Music genre-albums patch applied")
