from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel: str, text: str):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def rw(rel: str, old: str, new: str, count: int = 1):
    s = read(rel)
    if old not in s:
        raise RuntimeError(f"Expected snippet not found in {rel}: {old[:180]!r}")
    write(rel, s.replace(old, new, count))


# 1) Filmes: use NewPipeExtractor pagination instead of stopping at the first result page.
# The Grid is already virtualised and already draws a right-side Scrollbar, so it can safely
# hold a few hundred lightweight Item objects while thumbnails are decoded only as needed.
write("app/src/main/kotlin/dev/limitedio/pipetv/ui/PopularPage.kt", r'''package dev.limitedio.pipetv.ui

import android.content.Context
import android.view.KeyEvent
import android.view.ViewGroup
import dev.limitedio.pipetv.Bg
import dev.limitedio.pipetv.data.Feed
import dev.limitedio.pipetv.data.Item
import dev.limitedio.pipetv.data.Paged
import dev.limitedio.pipetv.data.Store
import dev.limitedio.pipetv.data.Yt
import dev.limitedio.pipetv.i18n.K
import dev.limitedio.pipetv.i18n.S

/** Popular videos. Filmes uses deep progressive pagination with the standard right scrollbar. */
class PopularPage(c: Context) : ViewGroup(c) {
    private val topics = listOf(K.TRENDING, K.T_MUSIC, K.T_GAMING, K.T_NEWS, K.T_SPORTS, K.T_MOVIES, K.T_LEARN, K.T_COMEDY, K.T_LIVE)
    private val MOVIES = 5
    private val MOVIE_LIMIT = 600

    val grid = Grid(c) { "" }.apply { upExit = true }
    private val chips = TopicChips(c, topics)
    private val cache = HashMap<Int, List<Item>>()
    private var onChips = false; private var on = true; private var ask = 0

    private var moviePages: MutableList<Paged<Item>> = mutableListOf()
    private var moviePageCursor = 0
    private val movieIds = LinkedHashSet<String>()

    init {
        addView(grid); addView(chips)
        chips.onChange = { show(it) }
        grid.onRetry = { show(chips.sel, true) }
        grid.onMore = { if (chips.sel == MOVIES) loadMoreMovies() }
    }

    fun picks(pick: (Item) -> Unit, menu: (Item) -> Unit) { grid.onPick = pick; grid.onMenu = menu }

    fun enter() { onChips = true; refresh(); if (cache[chips.sel] == null) show(chips.sel) }
    fun reset() {
        cache.clear(); moviePages.clear(); movieIds.clear(); moviePageCursor = 0
        show(chips.sel, true)
    }
    fun back(): Boolean {
        if (onChips) return false
        onChips = true; refresh(); return true
    }

    private fun mark(l: List<Item>): List<Item> {
        val seen = Store.entries().associate { e -> e.item.id to e.fraction }
        return l.onEach { it.progress = seen[it.id] ?: 0f }
    }

    private fun show(i: Int, force: Boolean = false) {
        if (i == MOVIES) { showMovies(force); return }
        val t = ++ask
        if (!force) cache[i]?.let { grid.message = null; grid.items = it; grid.loading = false; return }
        grid.items = emptyList(); grid.message = null; grid.busy = true; grid.loading = false
        Bg.io({ Feed.topic(S.t(topics[i]), i == 0) }) { r ->
            if (t != ask) return@io
            val l = mark(r ?: emptyList())
            if (r != null) cache[i] = l
            grid.message = if (r == null) S.t(K.LOAD_FAILED) else if (l.isEmpty()) S.t(K.NO_RESULTS) else null
            grid.items = l; grid.busy = false
        }
    }

    private fun movieQueries() = if (S.cur.code == "pt") listOf(
        "filme completo dublado",
        "filme completo português",
        "filmes brasileiros completos",
        "filme completo HD"
    ) else listOf(
        "full movie",
        "full movies HD",
        "classic full movie",
        "free full movie"
    )

    /** Keeps real long-form videos and removes trailers, shorts and live streams. */
    private fun movieCandidate(it: Item): Boolean =
        it.kind == Item.VIDEO && !it.isLive && it.dur >= 35L * 60L

    private fun mergeFirstPages(pages: List<Paged<Item>>): List<Item> {
        val rows = pages.map { p -> p.items.filter(::movieCandidate) }
        val out = LinkedHashMap<String, Item>()
        val max = rows.maxOfOrNull { it.size } ?: 0
        for (i in 0 until max) for (row in rows) row.getOrNull(i)?.let { out.putIfAbsent(it.id, it) }
        return out.values.take(MOVIE_LIMIT)
    }

    private fun showMovies(force: Boolean) {
        val t = ++ask
        if (!force) cache[MOVIES]?.let {
            grid.message = null; grid.items = it; grid.loading = false; grid.busy = false; return
        }
        moviePages.clear(); movieIds.clear(); moviePageCursor = 0
        grid.items = emptyList(); grid.message = null; grid.loading = false; grid.busy = true
        Bg.io({
            Bg.par(movieQueries().map { q -> { runCatching { Yt.search(q, "videos") }.getOrNull() } }).filterNotNull()
        }) { got ->
            if (t != ask) return@io
            moviePages = got.orEmpty().toMutableList()
            val initial = mark(mergeFirstPages(moviePages))
            initial.forEach { movieIds.add(it.id) }
            cache[MOVIES] = initial
            grid.message = when {
                got == null -> S.t(K.LOAD_FAILED)
                initial.isEmpty() -> S.t(K.NO_RESULTS)
                else -> null
            }
            grid.items = initial; grid.busy = false; grid.loading = false
        }
    }

    /** Prefetches more pages when focus approaches the end. The Grid remains virtualised. */
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

    fun lit(v: Boolean) { on = v; refresh() }
    private fun refresh() { grid.lit = on && !onChips; chips.lit = on && onChips; grid.invalidate(); chips.invalidate() }

    fun key(code: Int): Boolean {
        if (!onChips) {
            if (grid.key(code)) return true
            if (code == KeyEvent.KEYCODE_DPAD_UP) { onChips = true; refresh(); return true }
            return false
        }
        if (chips.key(code)) return true
        if (code == KeyEvent.KEYCODE_DPAD_DOWN || code == KeyEvent.KEYCODE_DPAD_CENTER || code == KeyEvent.KEYCODE_ENTER) {
            onChips = false; refresh(); return true
        }
        return false
    }

    override fun onLayout(ch: Boolean, l: Int, t: Int, r: Int, b: Int) {
        val hh = Ui.u(130).toInt()
        chips.layout(0, Ui.u(20).toInt(), r - l, hh); grid.layout(0, hh, r - l, b - t)
    }
}
''')

# 2) Long-form flag. Movies get a healthier startup/rebuffer cushion, without changing normal clips.
session = "app/src/main/kotlin/dev/limitedio/pipetv/media/Session.kt"
rw(session,
'''    var musicMode = false; private set
    private var nextMusic = false
''',
'''    var musicMode = false; private set
    var longForm = false; private set
    private var nextMusic = false
''')
rw(session,
'''        item = it; info = o.info; related = o.related; cap = 2160; safe = 0; manualHeight = null; musicMode = o.music
''',
'''        item = it; info = o.info; related = o.related; cap = 2160; safe = 0; manualHeight = null; musicMode = o.music
        longForm = !musicMode && o.info.duration >= 35L * 60L
''')

# Direct extracted media already bypasses YouTube's platform ad player. For long-form films we do
# not run SponsorBlock seeks because a large seek near startup can destabilise separate A/V streams.
rw(session,
'''        if (!musicMode) SponsorBlock.load(it.id)
        Progress.schedule()
''',
'''        if (!musicMode && !longForm) SponsorBlock.load(it.id)
        Progress.schedule()
''')
rw(session,
'''        Progress.save(); token++; item = null; pending = null; info = null; musicMode = false; nextMusic = false; Progress.cancel(); SponsorBlock.reset(); Recovery.reset(); Subs.select(null)
''',
'''        Progress.save(); token++; item = null; pending = null; info = null; musicMode = false; longForm = false; nextMusic = false; Progress.cancel(); SponsorBlock.reset(); Recovery.reset(); Subs.select(null)
''')

# 3) Long-form playback: wait for a real cushion before starting/resuming.
engine = "app/src/main/kotlin/dev/limitedio/pipetv/media/Engine.kt"
rw(engine,
'''        override fun shouldStartPlayback(parameters: LoadControl.Parameters): Boolean {
            if (!Session.musicMode) return base.shouldStartPlayback(parameters)
            val requiredUs = if (parameters.rebuffering) 8_000_000L else 5_000_000L
            return parameters.bufferedDurationUs >= requiredUs || parameters.bufferedDurationUs == androidx.media3.common.C.TIME_UNSET
        }
''',
'''        override fun shouldStartPlayback(parameters: LoadControl.Parameters): Boolean {
            if (!Session.musicMode && !Session.longForm) return base.shouldStartPlayback(parameters)
            val requiredUs = if (parameters.rebuffering) 8_000_000L else 5_000_000L
            return parameters.bufferedDurationUs >= requiredUs || parameters.bufferedDurationUs == androidx.media3.common.C.TIME_UNSET
        }
''')

# 4) Infinite-buffer recovery for video. Instead of endlessly spinning, progressively move to
# a combined A/V stream, refresh expiring URLs and lower only this video's temporary cap.
recovery = "app/src/main/kotlin/dev/limitedio/pipetv/media/Recovery.kt"
rw(recovery,
'''    private var tries = 0
    private var musicFloor = 0L
    private val retry = Runnable { refresh() }
''',
'''    private var tries = 0
    private var musicFloor = 0L
    private var stallStage = 0
    private val retry = Runnable { refresh() }
    private val stable = Runnable {
        if (!Session.musicMode && Engine.exo.isPlaying && Engine.exo.playbackState == androidx.media3.common.Player.STATE_READY) stallStage = 0
    }
''')
rw(recovery,
'''    fun onSuccess() {
        if (tries == 0 && !failed) return
        tries = 0; failed = false; Bg.main.removeCallbacks(retry); Session.changed()
    }
''',
'''    fun onSuccess() {
        if (!Session.musicMode) {
            Bg.main.removeCallbacks(stable)
            Bg.main.postDelayed(stable, 30_000L)
        }
        if (tries == 0 && !failed) return
        tries = 0; failed = false; Bg.main.removeCallbacks(retry); Session.changed()
    }
''')
rw(recovery,
'''    fun reset() { tries = 0; failed = false; musicFloor = 0L; Bg.main.removeCallbacks(retry) }
''',
'''    fun reset() {
        tries = 0; failed = false; musicFloor = 0L; stallStage = 0
        Bg.main.removeCallbacks(retry); Bg.main.removeCallbacks(stable)
    }
''')

# Replace the previous one-step quality reduction stall handler.
old_stall = '''    /** Long buffering on the normal profile: step down without touching the user's global preference. */
    fun onStall() {
        if (Session.musicMode || Session.info == null || Session.manualHeight != null || (Prefs.quality > 1080 && Prefs.quality != 0)) return
        val next = when { Session.height > 720 -> 720; Session.height > 480 -> 480; Session.height > 360 -> 360; else -> return }
        Session.cap = next
        Session.start(Engine.exo.currentPosition.coerceAtLeast(0L))
    }
'''
new_stall = '''    /** Long buffering: recover in bounded stages instead of leaving an infinite spinner. */
    fun onStall() {
        if (Session.musicMode || Session.info == null || failed) return
        Bg.main.removeCallbacks(stable)
        val pos = Engine.exo.currentPosition.coerceAtLeast(0L)
        stallStage++
        when (stallStage) {
            1 -> {
                // Separate 1080p video+audio URLs can throttle on long-form content. Prefer a
                // single progressive A/V stream when YouTube exposes one; keep this override local.
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
rw(recovery, old_stall, new_stall)

print("VórticeTv v0.1.7 movies + long-form player patch applied")
