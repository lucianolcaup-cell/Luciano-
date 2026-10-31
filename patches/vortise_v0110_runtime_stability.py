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


# -----------------------------------------------------------------------------
# Vórtice Music: album view isolated from the global video click path.
# The normal VIDEO branch in Opener stays unchanged.
# -----------------------------------------------------------------------------
write("app/src/main/kotlin/dev/limitedio/pipetv/ui/MusicAlbumPage.kt", r'''package dev.limitedio.pipetv.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.LinearGradient
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Shader
import android.view.KeyEvent
import dev.limitedio.pipetv.Bg
import dev.limitedio.pipetv.data.Item
import dev.limitedio.pipetv.data.Paged
import dev.limitedio.pipetv.data.YtPages
import dev.limitedio.pipetv.i18n.S

/** Album page: cover at left and one scrollable vertical track list at right. */
class MusicAlbumPage(c: Context, private val url: String) : AnimView(c), Screen {
    var onPlay: (List<Item>, Int) -> Unit = { _, _ -> }
    private var title = if (S.cur.code == "pt") "Álbum" else "Album"
    private var by = ""
    private var cover = ""
    private var tracks: List<Item> = emptyList()
    private var paged: Paged<Item>? = null
    private var idx = 0
    private var enabled = true
    private var busy = true
    private var failed = false
    private var loadingMore = false
    private val scroll = spring(0f, 200f, 28f)
    private val titlePaint = Ui.paint(Ui.TEXT, 44f, true)
    private val byPaint = Ui.paint(Ui.ACCENT2, 24f, true)
    private val rowText = Ui.paint(Ui.TEXT, 27f, true)
    private val rowSub = Ui.paint(Ui.DIM, 20f)
    private val dim = Ui.paint(Ui.DIM, 24f)
    private val face = Ui.paint(Ui.SURFACE)
    private val ring = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; strokeWidth = Ui.u(4) }
    private val pic = Paint(Paint.ANTI_ALIAS_FLAG)
    private val matrix = Matrix()
    private val rect = RectF()
    private val rowH get() = Ui.u(74)
    private val listTop get() = Ui.u(122)

    init {
        Img.listen { invalidate() }
        load()
    }

    private fun load() {
        busy = true; failed = false; invalidate()
        Bg.io({ YtPages.playlist(url) }) { p ->
            if (p == null) {
                busy = false; failed = true; invalidate(); return@io
            }
            title = p.name; by = p.by; cover = p.thumb; paged = p.videos
            tracks = p.videos.items.filter { it.kind == Item.VIDEO }.distinctBy { it.id }
            busy = false; failed = false; idx = 0
            if (height > 0) refocus()
            invalidate()
            if (tracks.isEmpty() && p.videos.hasMore) loadMore()
        }
    }

    private fun loadMore() {
        val p = paged ?: return
        if (!p.hasMore || loadingMore) return
        loadingMore = true
        val before = p.items.size
        Bg.io({ p.loadMore() }) { result ->
            loadingMore = false
            if (result != null) {
                val add = p.items.drop(before).filter { it.kind == Item.VIDEO }
                if (add.isNotEmpty()) tracks = (tracks + add).distinctBy { it.id }
            }
            invalidate()
        }
    }

    private fun refocus() {
        if (height <= 0 || tracks.isEmpty()) { scroll.target = 0f; return }
        val visible = (height - listTop - Ui.u(36)).coerceAtLeast(rowH)
        val y = idx * rowH
        if (y < scroll.target) scroll.target = y
        if (y + rowH > scroll.target + visible) scroll.target = y + rowH - visible
        if (idx >= tracks.size - 3) loadMore()
    }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        if (h > 0) refocus()
    }

    private fun fmt(sec: Long): String {
        if (sec <= 0) return ""
        val m = sec / 60; val s = sec % 60
        return "%d:%02d".format(m, s)
    }

    override fun render(c: Canvas, dt: Float) {
        if (width <= 0 || height <= 0) return
        val pad = Ui.u(34)
        val availableCover = (height - Ui.u(180)).coerceAtLeast(Ui.u(140))
        val coverSize = minOf(Ui.u(340), availableCover)
        Txt.draw(c, title, pad, Ui.u(60), width - Ui.u(80), titlePaint)
        if (by.isNotBlank()) Txt.draw(c, by, pad, Ui.u(94), width - Ui.u(80), byPaint)

        rect.set(pad, listTop, pad + coverSize, listTop + coverSize)
        c.drawRoundRect(rect, Ui.u(22), Ui.u(22), face)
        if (cover.isNotBlank()) Img.get(cover, 600)?.let { p ->
            if (p.bmp.width > 0 && p.bmp.height > 0 && rect.width() > 0 && rect.height() > 0) {
                val scale = maxOf(rect.width() / p.bmp.width, rect.height() / p.bmp.height)
                matrix.setScale(scale, scale)
                matrix.postTranslate(rect.left - (p.bmp.width * scale - rect.width()) / 2, rect.top - (p.bmp.height * scale - rect.height()) / 2)
                p.shader.setLocalMatrix(matrix); pic.shader = p.shader
                c.drawRoundRect(rect, Ui.u(22), Ui.u(22), pic)
            }
        }

        val lx = rect.right + Ui.u(34)
        val right = width - Ui.u(30)
        if (right <= lx) return
        if (busy) {
            Txt.draw(c, if (S.cur.code == "pt") "Carregando álbum…" else "Loading album…", lx, listTop + Ui.u(54), right - lx, dim)
            return
        }
        if (failed) {
            Txt.draw(c, if (S.cur.code == "pt") "Não foi possível abrir este álbum. OK para tentar novamente." else "Couldn't open this album. Press OK to retry.", lx, listTop + Ui.u(54), right - lx, dim)
            return
        }
        if (tracks.isEmpty()) {
            Txt.draw(c, if (S.cur.code == "pt") "Nenhuma faixa encontrada." else "No tracks found.", lx, listTop + Ui.u(54), right - lx, dim)
            return
        }

        c.save()
        c.clipRect(lx, listTop, right, height.toFloat() - Ui.u(20))
        c.translate(0f, -scroll.value)
        tracks.forEachIndexed { i, item ->
            val y = listTop + i * rowH
            rect.set(lx, y + Ui.u(4), right - Ui.u(16), y + rowH - Ui.u(4))
            c.drawRoundRect(rect, Ui.u(16), Ui.u(16), face)
            if (enabled && i == idx) {
                ring.shader = LinearGradient(rect.left, 0f, rect.right, 0f, Ui.ACCENT, Ui.ACCENT2, Shader.TileMode.CLAMP)
                c.drawRoundRect(rect, Ui.u(16), Ui.u(16), ring)
            }
            Txt.draw(c, "${i + 1}", rect.left + Ui.u(18), rect.centerY() + Ui.u(9), Ui.u(38), rowSub)
            val tx = rect.left + Ui.u(58)
            Txt.draw(c, Txt.fit(rowText, item.title, rect.width() - Ui.u(150)), tx, rect.centerY() + Ui.u(3), rect.width() - Ui.u(150), rowText)
            val d = fmt(item.dur)
            if (d.isNotEmpty()) Txt.draw(c, d, rect.right - Ui.u(90), rect.centerY() + Ui.u(8), Ui.u(74), rowSub, true)
        }
        c.restore()
        Scrollbar.draw(c, width.toFloat(), listTop, height - Ui.u(22), tracks.size * rowH, (height - listTop).toFloat(), scroll.value, enabled)
    }

    override fun key(code: Int, repeat: Int): Boolean {
        if (busy) return true
        if (failed) {
            if (code == KeyEvent.KEYCODE_DPAD_CENTER || code == KeyEvent.KEYCODE_ENTER) { load(); return true }
            return false
        }
        if (tracks.isEmpty()) return false
        when (code) {
            KeyEvent.KEYCODE_DPAD_UP -> if (idx > 0) { idx--; refocus() } else return false
            KeyEvent.KEYCODE_DPAD_DOWN -> if (idx < tracks.lastIndex) { idx++; refocus() } else { loadMore(); return true }
            KeyEvent.KEYCODE_DPAD_CENTER, KeyEvent.KEYCODE_ENTER -> onPlay(tracks, idx)
            else -> return false
        }
        invalidate(); return true
    }

    override fun lit(on: Boolean) { enabled = on; invalidate() }
    override fun focused(): Item? = tracks.getOrNull(idx)
}
''')

session = "app/src/main/kotlin/dev/limitedio/pipetv/media/Session.kt"
rw(session,
'''    fun changed() = onChange() ; fun noExpand() { expand = false }
    fun armMusic() { nextMusic = true }
''',
'''    fun changed() = onChange() ; fun noExpand() { expand = false }
    fun armMusic() { nextMusic = true }
    fun takeMusicAlbumArm(): Boolean { val armed = nextMusic; if (armed) nextMusic = false; return armed }
    private var musicQueue: List<Item> = emptyList()
    private var musicIndex = -1
    fun setMusicQueue(items: List<Item>, index: Int) {
        val q = items.filter { it.kind == Item.VIDEO }
        if (q.isEmpty()) return
        musicQueue = q
        musicIndex = index.coerceIn(0, q.lastIndex)
        armMusic()
    }
''')

rw(session,
'''    fun ended() { item?.let { Store.progress(it.id, Engine.exo.duration, Engine.exo.duration) }; if (Prefs.autoplay) next() }

    fun next() { related.firstOrNull { !Store.seen(it.id) && it.id != item?.id }?.let { if (musicMode) armMusic(); open(it) } }
''',
'''    fun ended() {
        item?.let { Store.progress(it.id, Engine.exo.duration, Engine.exo.duration) }
        if (musicMode && musicQueue.isNotEmpty()) next() else if (Prefs.autoplay) next()
    }

    fun next() {
        if (musicMode && musicQueue.isNotEmpty()) {
            val nextIndex = musicIndex + 1
            if (nextIndex in musicQueue.indices) {
                musicIndex = nextIndex; armMusic(); open(musicQueue[nextIndex]); return
            }
        }
        related.firstOrNull { !Store.seen(it.id) && it.id != item?.id }?.let { if (musicMode) armMusic(); open(it) }
    }
''')

rw(session,
'''        Progress.save(); token++; item = null; pending = null; info = null; musicMode = false; longForm = false; nextMusic = false; Progress.cancel(); SponsorBlock.reset(); Recovery.reset(); Subs.select(null)
''',
'''        Progress.save(); token++; item = null; pending = null; info = null; musicMode = false; longForm = false; nextMusic = false; musicQueue = emptyList(); musicIndex = -1; Progress.cancel(); SponsorBlock.reset(); Recovery.reset(); Subs.select(null)
''')

opener = "app/src/main/kotlin/dev/limitedio/pipetv/ui/Opener.kt"
rw(opener,
'import dev.limitedio.pipetv.i18n.S\n',
'import dev.limitedio.pipetv.i18n.S\nimport dev.limitedio.pipetv.media.Session\n')
rw(opener,
'''            Item.PLAYLIST -> playlist(it.url)
''',
'''            Item.PLAYLIST -> if (Session.takeMusicAlbumArm()) musicAlbum(it.url) else playlist(it.url)
''')
rw(opener,
'''    private fun playlist(url: String) = show(ChannelPage(root.context) {
''',
'''    private fun musicAlbum(url: String) = show(MusicAlbumPage(root.context, url).apply {
        onPlay = { tracks, index ->
            if (index in tracks.indices) {
                Session.setMusicQueue(tracks, index)
                root.controls.play(tracks[index])
            }
        }
    })

    private fun playlist(url: String) = show(ChannelPage(root.context) {
''')


# -----------------------------------------------------------------------------
# Canais Abertos: bounded requests on the existing fixed Bg pool, progressive results.
# No cached-thread-pool fan-out and no generic player/navigation changes.
# -----------------------------------------------------------------------------
write("app/src/main/kotlin/dev/limitedio/pipetv/ui/OpenChannelsPage.kt", r'''package dev.limitedio.pipetv.ui

import android.content.Context
import android.os.SystemClock
import android.view.KeyEvent
import android.view.ViewGroup
import dev.limitedio.pipetv.Bg
import dev.limitedio.pipetv.data.Item
import dev.limitedio.pipetv.data.Yt
import dev.limitedio.pipetv.i18n.S
import org.schabi.newpipe.extractor.stream.StreamType
import java.text.Normalizer

class OpenChannelsPage(c: Context) : ViewGroup(c) {
    private data class Source(val query: String, val aliases: List<String>, val group: Int)
    private data class CacheEntry(val items: List<Item>, val at: Long)

    private fun labels() = if (S.cur.code == "pt")
        listOf("Todos", "Notícias", "Públicos", "Cultura", "Geral", "Esportes", "Religiosos")
    else listOf("All", "News", "Public", "Culture", "General", "Sports", "Religious")

    private val sources = listOf(
        Source("CNN Brasil ao vivo agora", listOf("cnn brasil"), 1),
        Source("BandNews TV ao vivo agora", listOf("bandnews tv", "bandnews"), 1),
        Source("Record News ao vivo agora", listOf("record news"), 1),
        Source("UOL News ao vivo agora", listOf("uol news", "uol"), 1),
        Source("Jovem Pan News ao vivo agora", listOf("jovem pan news", "jovem pan"), 1),
        Source("TV Brasil ao vivo agora", listOf("tv brasil"), 2),
        Source("CanalGov ao vivo agora", listOf("canalgov", "canal gov"), 2),
        Source("TV Senado ao vivo agora", listOf("tv senado"), 2),
        Source("Câmara dos Deputados ao vivo agora", listOf("camara dos deputados", "câmara dos deputados"), 2),
        Source("TV Justiça ao vivo agora", listOf("tv justica", "tv justiça"), 2),
        Source("TV Cultura ao vivo agora", listOf("tv cultura", "cultura"), 3),
        Source("Canal Futura ao vivo agora", listOf("canal futura", "futura"), 3),
        Source("Band ao vivo agora", listOf("band jornalismo", "band"), 4),
        Source("SBT ao vivo agora", listOf("sbt"), 4),
        Source("RedeTV ao vivo agora", listOf("redetv", "rede tv"), 4),
        Source("TV Gazeta ao vivo agora", listOf("tv gazeta", "gazeta"), 4),
        Source("World Surf League live now", listOf("world surf league", "wsl"), 5),
        Source("Canal Olímpico do Brasil ao vivo", listOf("canal olimpico do brasil", "olimpico do brasil"), 5),
        Source("CazéTV ao vivo agora", listOf("cazetv", "caze tv"), 5),
        Source("TV Aparecida ao vivo agora", listOf("tv aparecida"), 6),
        Source("Rede Vida ao vivo agora", listOf("rede vida", "redevida"), 6),
    )

    val grid = Grid(c) { labels()[chips.sel] }.apply { upExit = true }
    private val chips = ChannelChips(c) { labels() }
    private val cache = HashMap<Int, CacheEntry>()
    private val ttl = 60_000L
    private var onChips = true
    private var enabled = true
    private var generation = 0

    init {
        addView(grid); addView(chips)
        chips.onChange = { show(it, false) }
        grid.onRetry = { show(chips.sel, true) }
    }

    fun picks(pick: (Item) -> Unit, menu: (Item) -> Unit) { grid.onPick = pick; grid.onMenu = menu }
    fun enter() { onChips = true; refresh(); show(chips.sel, false) }
    fun back(): Boolean { if (onChips) return false; onChips = true; refresh(); return true }
    fun lit(v: Boolean) { enabled = v; refresh() }

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

    private fun refresh() {
        grid.lit = enabled && !onChips; chips.lit = enabled && onChips
        grid.invalidate(); chips.invalidate()
    }

    private fun norm(s: String): String = Normalizer.normalize(s.lowercase(), Normalizer.Form.NFD)
        .replace(Regex("\\p{Mn}+"), "").replace(Regex("[^a-z0-9 ]"), " ")
        .replace(Regex("\\s+"), " ").trim()

    private fun trusted(item: Item, src: Source): Boolean {
        if (item.kind != Item.VIDEO) return false
        val uploader = norm(item.by); val title = norm(item.title)
        return src.aliases.map(::norm).any { a -> uploader.contains(a) || (uploader.isBlank() && title.contains(a)) }
    }

    private fun metadataLive(item: Item): Boolean = runCatching {
        val i = Yt.stream(item.url)
        i.streamType == StreamType.LIVE_STREAM || i.streamType == StreamType.AUDIO_LIVE_STREAM
    }.getOrDefault(false)

    private fun discover(src: Source): Item? {
        val candidates = runCatching { Yt.search(src.query, "videos").items }.getOrDefault(emptyList())
            .filter { trusted(it, src) }
        candidates.firstOrNull { it.isLive }?.let { return it }
        return candidates.take(2).firstOrNull(::metadataLive)
    }

    private fun show(group: Int, force: Boolean) {
        val now = SystemClock.uptimeMillis()
        if (!force) cache[group]?.takeIf { now - it.at < ttl }?.let {
            grid.items = it.items; grid.message = if (it.items.isEmpty()) noLive() else null
            grid.busy = false; grid.loading = false; grid.invalidate(); return
        }
        val token = ++generation
        val selected = if (group == 0) sources else sources.filter { it.group == group }
        val found = LinkedHashMap<String, Item>()
        var finished = 0
        grid.items = emptyList(); grid.busy = true; grid.loading = true
        grid.message = if (S.cur.code == "pt") "Buscando canais oficiais ao vivo…" else "Finding official live channels…"
        grid.invalidate()

        if (selected.isEmpty()) { grid.busy = false; grid.loading = false; grid.message = noLive(); return }
        selected.forEach { src ->
            Bg.io({ discover(src) }) { item ->
                if (token != generation) return@io
                finished++
                if (item != null && found.putIfAbsent(item.id, item) == null) {
                    grid.items = found.values.toList(); grid.busy = false; grid.message = null; grid.invalidate()
                }
                if (finished >= selected.size) {
                    val items = found.values.toList()
                    cache[group] = CacheEntry(items, SystemClock.uptimeMillis())
                    grid.items = items; grid.busy = false; grid.loading = false
                    grid.message = if (items.isEmpty()) noLive() else null
                    grid.invalidate()
                }
            }
        }
    }

    private fun noLive() = if (S.cur.code == "pt")
        "Nenhuma transmissão oficial ao vivo encontrada agora. Pressione OK para atualizar."
    else "No official live stream found right now. Press OK to refresh."

    override fun onLayout(changed: Boolean, l: Int, t: Int, r: Int, b: Int) {
        val hh = Ui.u(130).toInt(); chips.layout(0, Ui.u(20).toInt(), r - l, hh); grid.layout(0, hh, r - l, b - t)
    }
}

private class ChannelChips(c: Context, private val labels: () -> List<String>) : AnimView(c) {
    var sel = 0; private set
    var lit = false
    var onChange: (Int) -> Unit = {}
    private val text = Ui.paint(Ui.TEXT, 27f, true)
    private val face = Ui.paint(Ui.SURFACE)
    private val fill = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG)
    private val rect = android.graphics.RectF()
    fun key(code: Int): Boolean {
        val next = sel + when (code) { KeyEvent.KEYCODE_DPAD_LEFT -> -1; KeyEvent.KEYCODE_DPAD_RIGHT -> 1; else -> return false }
        if (next !in labels().indices) return false
        sel = next; onChange(sel); invalidate(); return true
    }
    override fun render(c: android.graphics.Canvas, dt: Float) {
        val list = labels(); val pad = Ui.u(28); val gap = Ui.u(10); val widths = list.map { text.measureText(it) + Ui.u(48) }; var x = pad
        list.forEachIndexed { i, label ->
            val w = widths[i]; rect.set(x, Ui.u(14), x + w, height - Ui.u(14))
            if (i == sel) { fill.shader = android.graphics.LinearGradient(rect.left, 0f, rect.right, 0f, Ui.ACCENT, if (lit) Ui.ACCENT2 else Ui.ACCENT, android.graphics.Shader.TileMode.CLAMP); c.drawRoundRect(rect, rect.height()/2, rect.height()/2, fill) }
            else c.drawRoundRect(rect, rect.height()/2, rect.height()/2, face)
            text.color = if (i == sel) 0xFF0A0B14.toInt() else Ui.TEXT
            Txt.draw(c, label, rect.left, rect.centerY() + Ui.u(9), rect.width(), text, true); x += w + gap
        }
    }
}
''')


# -----------------------------------------------------------------------------
# Em alta: explicit query per category; keep Films pagination untouched.
# -----------------------------------------------------------------------------
pop = "app/src/main/kotlin/dev/limitedio/pipetv/ui/PopularPage.kt"
rw(pop,
'''        Bg.io({ Feed.topic(S.t(topics[i]), i == 0) }) { r ->
            if (t != ask) return@io
            val l = mark(r ?: emptyList())
            if (r != null) cache[i] = l
''',
'''        Bg.io({
            if (i == 0) Feed.trending() else {
                val q = when (i) {
                    1 -> if (S.cur.code == "pt") "música em alta Brasil" else "trending music"
                    2 -> if (S.cur.code == "pt") "jogos em alta Brasil" else "trending gaming"
                    3 -> if (S.cur.code == "pt") "notícias Brasil hoje" else "news today"
                    4 -> if (S.cur.code == "pt") "esportes Brasil hoje" else "sports today"
                    6 -> if (S.cur.code == "pt") "ciência educação Brasil" else "science education"
                    7 -> if (S.cur.code == "pt") "comédia Brasil" else "comedy"
                    8 -> if (S.cur.code == "pt") "ao vivo agora Brasil" else "live now"
                    else -> S.t(topics[i])
                }
                val direct = runCatching { Yt.search(q, "videos").items }.getOrDefault(emptyList())
                if (direct.isNotEmpty()) direct else runCatching { Yt.search(S.t(topics[i]), "videos").items }.getOrDefault(emptyList())
            }
        }) { r ->
            if (t != ask) return@io
            val l = mark(r ?: emptyList()).filter { it.kind == Item.VIDEO }
            if (r != null && l.isNotEmpty()) cache[i] = l
''')


# Sponsor/self-promo skipping stays enabled but never seeks beyond data already buffered.
sb = "app/src/main/kotlin/dev/limitedio/pipetv/media/SponsorBlock.kt"
rw(sb,
'''                if (startupSafe && end > pos && (end != lastEnd || now - lastSkip > 1800)) {
                    lastEnd = end; lastSkip = now; p.seekTo(end.coerceAtMost(Playback.duration))
                }
''',
'''                val target = end.coerceAtMost(Playback.duration)
                val bufferedSafe = p.bufferedPosition >= target + 500L
                if (startupSafe && bufferedSafe && target > pos && (target != lastEnd || now - lastSkip > 1800)) {
                    lastEnd = target; lastSkip = now; p.seekTo(target)
                }
''')

print("VórticeTv v0.1.10 runtime-safe fixes applied")
