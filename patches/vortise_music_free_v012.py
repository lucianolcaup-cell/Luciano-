from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src")


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def replace(rel, old, new, count=1):
    text = read(rel)
    if old not in text:
        raise RuntimeError(f"Expected snippet not found in {rel}: {old[:120]!r}")
    write(rel, text.replace(old, new, count))


# Vórtice Music: dedicated TV-first music home, inspired by familiar streaming-music navigation
# but with its own Vórtice identity and no copied third-party branding.
write("app/src/main/kotlin/dev/limitedio/pipetv/ui/MusicPage.kt", r'''package dev.limitedio.pipetv.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Shader
import android.view.KeyEvent
import android.view.ViewGroup
import dev.limitedio.pipetv.Bg
import dev.limitedio.pipetv.data.Item
import dev.limitedio.pipetv.data.Store
import dev.limitedio.pipetv.data.Yt
import dev.limitedio.pipetv.i18n.S
import dev.limitedio.pipetv.media.Session

/**
 * Vórtice Music — TV-first music browser backed by YouTube Music extraction.
 * Selecting an item arms audio-only playback when a direct audio stream exists.
 */
class MusicPage(c: Context) : ViewGroup(c) {
    private val filters = listOf("music_songs", "music_videos", "music_albums", "music_playlists")
    private fun names() = if (S.cur.code == "pt") listOf("Músicas", "Clipes", "Álbuns", "Playlists") else listOf("Songs", "Videos", "Albums", "Playlists")
    private fun queries() = if (S.cur.code == "pt") listOf("músicas em alta Brasil", "clipes oficiais Brasil", "lançamentos Brasil", "hits Brasil") else listOf("top songs", "official music videos", "new releases", "top hits")

    val grid = Grid(c) { names()[chips.sel] }.apply { upExit = true }
    private val chips = MusicChips(c) { names() }
    private val cache = HashMap<Int, List<Item>>()
    private var onChips = true; private var on = true; private var ask = 0

    private val titlePaint = Ui.paint(Ui.TEXT, 48f, true)
    private val subPaint = Ui.paint(Ui.DIM, 24f)
    private val pillText = Ui.paint(0xFF071018.toInt(), 19f, true)
    private val glow = Paint(Paint.ANTI_ALIAS_FLAG)
    private val pill = Paint(Paint.ANTI_ALIAS_FLAG)
    private val rr = RectF()

    init {
        setWillNotDraw(false)
        addView(grid); addView(chips)
        chips.onChange = { show(it) }
        grid.onRetry = { show(chips.sel, true) }
    }

    fun picks(pick: (Item) -> Unit, menu: (Item) -> Unit) {
        grid.onPick = { item -> Session.armMusic(); pick(item) }
        grid.onMenu = menu
    }

    fun enter() { onChips = true; refresh(); if (cache[chips.sel] == null) show(chips.sel) }
    fun reset() { cache.clear(); show(chips.sel, true) }
    fun back(): Boolean { if (onChips) return false; onChips = true; refresh(); return true }

    private fun show(i: Int, force: Boolean = false) {
        val t = ++ask
        if (!force) cache[i]?.let { grid.message = null; grid.items = it; grid.busy = false; return }
        grid.items = emptyList(); grid.message = null; grid.busy = true
        Bg.io({ Yt.search(queries()[i], filters[i]).items }) { r ->
            if (t != ask) return@io
            val seen = Store.entries().associate { e -> e.item.id to e.fraction }
            val l = (r ?: emptyList()).onEach { it.progress = seen[it.id] ?: 0f }
            if (r != null) cache[i] = l
            grid.message = when {
                r == null -> if (S.cur.code == "pt") "Não foi possível carregar o Vórtice Music." else "Couldn't load Vórtice Music."
                l.isEmpty() -> if (S.cur.code == "pt") "Nenhum resultado musical." else "No music results."
                else -> null
            }
            grid.items = l; grid.busy = false; grid.invalidate()
        }
    }

    fun lit(v: Boolean) { on = v; refresh() }
    private fun refresh() { grid.lit = on && !onChips; chips.lit = on && onChips; grid.invalidate(); chips.invalidate(); invalidate() }

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

    override fun onDraw(c: Canvas) {
        super.onDraw(c)
        glow.shader = LinearGradient(0f, 0f, width * .72f, Ui.u(210), Ui.ACCENT2, 0x00000000, Shader.TileMode.CLAMP)
        glow.alpha = 48
        c.drawRect(0f, 0f, width.toFloat(), Ui.u(210), glow)
        Txt.draw(c, "Vórtice Music", Ui.u(32), Ui.u(70), width - Ui.u(64), titlePaint)
        val sub = if (S.cur.code == "pt") "Música sem anúncios · áudio contínuo · feito para sua TV" else "Ad-free music · continuous audio · made for your TV"
        Txt.draw(c, sub, Ui.u(34), Ui.u(108), width - Ui.u(260), subPaint)

        rr.set(width - Ui.u(210), Ui.u(37), width - Ui.u(34), Ui.u(82))
        pill.shader = LinearGradient(rr.left, 0f, rr.right, 0f, Ui.ACCENT, Ui.ACCENT2, Shader.TileMode.CLAMP)
        c.drawRoundRect(rr, rr.height()/2, rr.height()/2, pill)
        val badge = if (S.cur.code == "pt") "SEM ANÚNCIOS" else "AD-FREE"
        Txt.draw(c, badge, rr.left, rr.centerY() + Ui.u(7), rr.width(), pillText, true)
    }

    override fun onLayout(ch: Boolean, l: Int, t: Int, r: Int, b: Int) {
        val chipTop = Ui.u(125).toInt()
        val chipBottom = Ui.u(205).toInt()
        chips.layout(0, chipTop, r - l, chipBottom)
        grid.layout(0, chipBottom, r - l, b - t)
    }
}

private class MusicChips(c: Context, private val labels: () -> List<String>) : AnimView(c) {
    var sel = 0; private set
    var lit = false
    var onChange: (Int) -> Unit = {}
    private val text = Ui.paint(Ui.TEXT, 26f, true)
    private val face = Ui.paint(Ui.SURFACE)
    private val fill = Paint(Paint.ANTI_ALIAS_FLAG)
    private val r = RectF()

    fun key(code: Int): Boolean {
        val d = when (code) { KeyEvent.KEYCODE_DPAD_LEFT -> -1; KeyEvent.KEYCODE_DPAD_RIGHT -> 1; else -> return false }
        val n = sel + d
        if (n !in 0..3) return false
        sel = n; invalidate(); onChange(sel); return true
    }

    override fun render(c: Canvas, dt: Float) {
        val pad = Ui.u(32); val w = (width - pad * 2) / 4f
        for (i in 0 until 4) {
            val x = pad + Ui.mx(i * w, w, width - pad * 2)
            r.set(x + Ui.u(5), Ui.u(10), x + w - Ui.u(5), height - Ui.u(10))
            c.drawRoundRect(r, r.height()/2, r.height()/2, face)
        }
        val px = pad + Ui.mx(sel * w, w, width - pad * 2)
        r.set(px + Ui.u(5), Ui.u(10), px + w - Ui.u(5), height - Ui.u(10))
        fill.shader = LinearGradient(r.left, 0f, r.right, 0f, Ui.ACCENT, if (lit) Ui.ACCENT2 else Ui.ACCENT, Shader.TileMode.CLAMP)
        c.drawRoundRect(r, r.height()/2, r.height()/2, fill)
        labels().forEachIndexed { i, label ->
            val x = pad + Ui.mx(i * w, w, width - pad * 2)
            text.color = if (i == sel) 0xFF0A0B14.toInt() else Ui.TEXT
            Txt.draw(c, label, x, height/2f + Ui.u(9), w, text, true)
        }
    }
}
''')

# Audio-only media source for Vórtice Music. Falls back to normal A/V if an item exposes no audio stream.
sources = "app/src/main/kotlin/dev/limitedio/pipetv/media/Sources.kt"
replace(
    sources,
    '    fun build(info: StreamInfo, maxH: Int, combinedOnly: Boolean, pick: AudioStream?): MediaSource {\n',
    '''    fun buildAudio(info: StreamInfo, pick: AudioStream?): MediaSource {\n        val live = info.streamType == StreamType.LIVE_STREAM || info.streamType == StreamType.AUDIO_LIVE_STREAM\n        if (live && info.hlsUrl.isNotEmpty())\n            return HlsMediaSource.Factory(http).createMediaSource(MediaItem.fromUri(info.hlsUrl))\n        val audio = info.audioStreams.filter { it.isUrl }\n            .sortedWith(compareByDescending<AudioStream> { it.format == MediaFormat.M4A }.thenByDescending { it.averageBitrate })\n        val selected = pick?.takeIf { it.isUrl } ?: audio.firstOrNull()\n        return if (selected != null) prog(selected.content) else build(info, 720, false, pick)\n    }\n\n    fun build(info: StreamInfo, maxH: Int, combinedOnly: Boolean, pick: AudioStream?): MediaSource {\n'''
)

# Session remembers whether the item was launched from Vórtice Music.
session = "app/src/main/kotlin/dev/limitedio/pipetv/media/Session.kt"
replace(session, '    var manualHeight: Int? = null; private set\n', '    var manualHeight: Int? = null; private set\n    var musicMode = false; private set\n    private var nextMusic = false\n')
replace(session, '    fun changed() = onChange() ; fun noExpand() { expand = false }\n', '    fun changed() = onChange() ; fun noExpand() { expand = false }\n    fun armMusic() { nextMusic = true }\n')
replace(session, '    private class Opened(val info: StreamInfo, val related: List<Item>, val resume: Long)\n', '    private class Opened(val info: StreamInfo, val related: List<Item>, val resume: Long, val music: Boolean)\n')
replace(
    session,
    '        pending = it; expand = expandWhenReady\n        val t = ++token\n',
    '        pending = it; expand = expandWhenReady\n        val openingMusic = nextMusic; nextMusic = false\n        val t = ++token\n'
)
replace(
    session,
    '            Opened(si, Yt.related(si), Store.entries().firstOrNull { e -> e.item.id == it.id }?.resume ?: 0L)\n',
    '            Opened(si, Yt.related(si), Store.entries().firstOrNull { e -> e.item.id == it.id }?.resume ?: 0L, openingMusic)\n'
)
replace(
    session,
    '        item = it; info = o.info; related = o.related; cap = 2160; safe = 0; manualHeight = null\n',
    '        item = it; info = o.info; related = o.related; cap = 2160; safe = 0; manualHeight = null; musicMode = o.music\n'
)
replace(
    session,
    '        Engine.exo.setMediaSource(Sources.build(si, if (safe > 0) minOf(height, 720) else height, safe > 1, audios.getOrNull(audioIdx)?.stream), start)\n',
    '        val source = if (musicMode) Sources.buildAudio(si, audios.getOrNull(audioIdx)?.stream) else Sources.build(si, if (safe > 0) minOf(height, 720) else height, safe > 1, audios.getOrNull(audioIdx)?.stream)\n        Engine.exo.setMediaSource(source, start)\n'
)
replace(
    session,
    '    fun next() { related.firstOrNull { !Store.seen(it.id) && it.id != item?.id }?.let { open(it) } }\n',
    '    fun next() { related.firstOrNull { !Store.seen(it.id) && it.id != item?.id }?.let { if (musicMode) armMusic(); open(it) } }\n'
)
replace(
    session,
    '        Progress.save(); token++; item = null; pending = null; info = null; Progress.cancel(); SponsorBlock.reset(); Recovery.reset(); Subs.select(null)\n',
    '        Progress.save(); token++; item = null; pending = null; info = null; musicMode = false; nextMusic = false; Progress.cancel(); SponsorBlock.reset(); Recovery.reset(); Subs.select(null)\n'
)

# SponsorBlock can operate during audio-only music playback even though no video frame is rendered.
sb = "app/src/main/kotlin/dev/limitedio/pipetv/media/SponsorBlock.kt"
replace(sb, 'p.playbackState == Player.STATE_READY && Engine.frame && Playback.seekable', 'p.playbackState == Player.STATE_READY && (Engine.frame || Session.musicMode) && Playback.seekable')

print("Vórtice Music Free patch applied successfully")
