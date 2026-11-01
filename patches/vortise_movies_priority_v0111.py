from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src")
REL = "app/src/main/kotlin/dev/limitedio/pipetv/ui/PopularPage.kt"
P = ROOT / REL
s = P.read_text(encoding="utf-8")


def replace(old: str, new: str, count: int = 1):
    global s
    if old not in s:
        raise RuntimeError(f"Expected snippet not found in {REL}: {old[:180]!r}")
    s = s.replace(old, new, count)

# Paging of long movie catalogs must never compete with opening the selected movie.
replace(
'''    private var moviePages: MutableList<Paged<Item>> = mutableListOf()
    private var moviePageCursor = 0
    private val movieIds = LinkedHashSet<String>()
''',
'''    private var moviePages: MutableList<Paged<Item>> = mutableListOf()
    private var moviePageCursor = 0
    private val movieIds = LinkedHashSet<String>()
    @Volatile private var moviePagingPaused = false
    private var movieLoadSerial = 0
''')

replace(
'''    fun picks(pick: (Item) -> Unit, menu: (Item) -> Unit) { grid.onPick = pick; grid.onMenu = menu }

    fun enter() { onChips = true; refresh(); if (cache[chips.sel] == null) show(chips.sel) }
''',
'''    fun picks(pick: (Item) -> Unit, menu: (Item) -> Unit) {
        grid.onPick = { item ->
            if (chips.sel == MOVIES) {
                // Give the selected movie full priority over catalog pagination.
                moviePagingPaused = true
                movieLoadSerial++
                grid.loading = false
                grid.busy = false
                grid.invalidate()
            }
            pick(item)
        }
        grid.onMenu = menu
    }

    fun enter() {
        moviePagingPaused = false
        onChips = true; refresh(); if (cache[chips.sel] == null) show(chips.sel)
    }
''')

replace(
'''    private fun show(i: Int, force: Boolean = false) {
        if (i == MOVIES) { showMovies(force); return }
        grid.loading = false
        val t = ++ask
''',
'''    private fun show(i: Int, force: Boolean = false) {
        if (i == MOVIES) { showMovies(force); return }
        moviePagingPaused = true
        movieLoadSerial++
        grid.loading = false
        val t = ++ask
''')

replace(
'''    private fun showMovies(force: Boolean) {
        val t = ++ask
''',
'''    private fun showMovies(force: Boolean) {
        moviePagingPaused = false
        movieLoadSerial++
        val t = ++ask
''')

old = '''    /** Prefetches more pages when focus approaches the end. The Grid remains virtualised. */
    private fun loadMoreMovies() {
        if (grid.loading || moviePages.isEmpty()) return
        val current = cache[MOVIES].orEmpty()
        if (current.size >= MOVIE_LIMIT || moviePages.none { it.hasMore }) return
        val t = ask
        grid.loading = true
        Bg.io({
            val out = ArrayList<Item>()
            var rounds = 0
            val maxRounds = minOf(16, moviePages.size * 4)
            while (out.size < 36 && rounds < maxRounds && moviePages.any { it.hasMore }) {
                val p = moviePages[moviePageCursor % moviePages.size]
                moviePageCursor = (moviePageCursor + 1) % moviePages.size
                rounds++
                if (!p.hasMore) continue
                val page = runCatching { p.loadMore() }.getOrDefault(emptyList())
                page.filterTo(out, ::movieCandidate)
            }
            out
        }) { got ->
            if (t != ask) return@io
            val room = (MOVIE_LIMIT - current.size).coerceAtLeast(0)
            val unique = got.orEmpty().filter { movieIds.add(it.id) }.take(room)
            val marked = mark(unique)
            if (marked.isNotEmpty()) {
                cache[MOVIES] = current + marked
                grid.append(marked)
            }
            grid.loading = false; grid.invalidate()
        }
    }
'''
new = '''    /**
     * Prefetches a small bounded batch only when the user is still browsing.
     * Selecting a movie invalidates this batch immediately, so extractor/network resources
     * are reserved for opening the chosen film instead of continuing catalog discovery.
     */
    private fun loadMoreMovies() {
        if (grid.loading || moviePages.isEmpty() || moviePagingPaused) return
        val current = cache[MOVIES].orEmpty()
        if (current.size >= MOVIE_LIMIT || moviePages.none { it.hasMore }) return

        val t = ask
        val serial = ++movieLoadSerial
        grid.loading = true

        // Small debounce: if the user reaches the bottom and immediately presses OK,
        // no extra catalog request is started at all.
        Bg.main.postDelayed({
            if (serial != movieLoadSerial || moviePagingPaused || chips.sel != MOVIES) {
                if (serial == movieLoadSerial) grid.loading = false
                return@postDelayed
            }

            Bg.io({
                val out = ArrayList<Item>()
                var rounds = 0
                // Bounded to at most three extractor page requests per batch.
                while (out.size < 18 && rounds < 3 && moviePages.any { it.hasMore }) {
                    if (moviePagingPaused || serial != movieLoadSerial) break
                    val p = moviePages[moviePageCursor % moviePages.size]
                    moviePageCursor = (moviePageCursor + 1) % moviePages.size
                    rounds++
                    if (!p.hasMore) continue
                    val page = runCatching { p.loadMore() }.getOrDefault(emptyList())
                    if (moviePagingPaused || serial != movieLoadSerial) break
                    page.filterTo(out, ::movieCandidate)
                }
                out
            }) { got ->
                if (t != ask || serial != movieLoadSerial || moviePagingPaused || chips.sel != MOVIES) {
                    if (serial == movieLoadSerial) grid.loading = false
                    return@io
                }
                val latest = cache[MOVIES].orEmpty()
                val room = (MOVIE_LIMIT - latest.size).coerceAtLeast(0)
                val unique = got.orEmpty().filter { movieIds.add(it.id) }.take(room)
                val marked = mark(unique)
                if (marked.isNotEmpty()) {
                    cache[MOVIES] = latest + marked
                    grid.append(marked)
                }
                grid.loading = false
                grid.invalidate()
            }
        }, 300L)
    }
'''
replace(old, new)

P.write_text(s, encoding="utf-8")
print("VórticeTv v0.1.11 movie selection priority patch applied")
