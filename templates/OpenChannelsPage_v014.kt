package dev.limitedio.pipetv.ui

import android.content.Context
import android.view.KeyEvent
import android.view.ViewGroup
import dev.limitedio.pipetv.Bg
import dev.limitedio.pipetv.data.Item
import dev.limitedio.pipetv.data.Yt
import dev.limitedio.pipetv.i18n.S
import java.text.Normalizer

/** Official/public live-TV discovery grouped for Android TV. */
class OpenChannelsPage(c: Context) : ViewGroup(c) {
    private data class Source(val query: String, val aliases: List<String>, val group: Int)

    private fun labels() = if (S.cur.code == "pt")
        listOf("Todos", "Notícias", "Públicos", "Cultura", "Geral", "Religiosos")
    else listOf("All", "News", "Public", "Culture", "General", "Religious")

    private val sources = listOf(
        Source("CNN Brasil ao vivo", listOf("cnn brasil"), 1),
        Source("Record News ao vivo", listOf("record news"), 1),
        Source("Jovem Pan News ao vivo", listOf("jovem pan news", "jovem pan"), 1),
        Source("BandNews TV ao vivo", listOf("bandnews tv", "bandnews"), 1),

        Source("TV Brasil ao vivo", listOf("tv brasil"), 2),
        Source("CanalGov ao vivo", listOf("canalgov", "canal gov"), 2),
        Source("TV Senado ao vivo", listOf("tv senado"), 2),
        Source("Câmara dos Deputados ao vivo", listOf("camara dos deputados", "câmara dos deputados"), 2),
        Source("TV Justiça ao vivo", listOf("tv justica", "tv justiça"), 2),

        Source("TV Cultura ao vivo", listOf("tv cultura", "cultura"), 3),
        Source("TV Escola ao vivo", listOf("tv escola"), 3),

        Source("SBT ao vivo", listOf("sbt"), 4),
        Source("Band ao vivo", listOf("band", "band jornalismo"), 4),
        Source("RedeTV ao vivo", listOf("redetv", "rede tv"), 4),

        Source("TV Aparecida ao vivo", listOf("tv aparecida"), 5),
        Source("Rede Vida ao vivo", listOf("rede vida", "redevida"), 5),
    )

    val grid = Grid(c) { labels()[chips.sel] }.apply { upExit = true; busy = true }
    private val chips = ChannelChips(c) { labels() }
    private val cache = HashMap<Int, List<Item>>()
    private var onChips = true
    private var on = true
    private var ask = 0

    init {
        addView(grid); addView(chips)
        chips.onChange = { show(it, false) }
        grid.onRetry = { show(chips.sel, true) }
    }

    fun picks(pick: (Item) -> Unit, menu: (Item) -> Unit) {
        grid.onPick = pick; grid.onMenu = menu
    }

    fun enter() {
        onChips = true; refresh()
        if (cache[chips.sel] == null) show(chips.sel, false)
    }

    fun back(): Boolean {
        if (onChips) return false
        onChips = true; refresh(); return true
    }

    fun lit(v: Boolean) { on = v; refresh() }

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
        grid.lit = on && !onChips; chips.lit = on && onChips
        grid.invalidate(); chips.invalidate()
    }

    private fun norm(s: String): String = Normalizer.normalize(s.lowercase(), Normalizer.Form.NFD)
        .replace(Regex("\\p{Mn}+"), "")
        .replace(Regex("[^a-z0-9 ]"), " ")
        .replace(Regex("\\s+"), " ")
        .trim()

    private fun trusted(item: Item, src: Source): Boolean {
        if (item.kind != Item.VIDEO) return false
        val uploader = norm(item.by)
        val title = norm(item.title)
        val aliases = src.aliases.map(::norm)
        val officialUploader = aliases.any { a -> uploader == a || uploader.startsWith(a) || uploader.contains(a) }
        val titleMatches = aliases.any { a -> title.contains(a) }
        return officialUploader || (uploader.isBlank() && titleMatches)
    }

    private fun liveScore(item: Item): Int {
        val t = norm(item.title)
        return when {
            item.isLive -> 4
            "ao vivo" in t || "live" in t -> 3
            "24h" in t || "24 horas" in t -> 2
            "agora" in t -> 1
            else -> 0
        }
    }

    private fun discover(src: Source): Item? {
        val list = runCatching { Yt.search(src.query, "videos").items }.getOrDefault(emptyList())
        val official = list.filter { trusted(it, src) }
        return official.maxByOrNull(::liveScore)?.takeIf { liveScore(it) > 0 }
            ?: official.firstOrNull()
    }

    private fun show(group: Int, force: Boolean) {
        val t = ++ask
        if (!force) cache[group]?.let { grid.message = null; grid.items = it; grid.busy = false; return }
        grid.items = emptyList(); grid.message = if (S.cur.code == "pt") "Buscando transmissões oficiais…" else "Finding official streams…"; grid.busy = true
        val selected = if (group == 0) sources else sources.filter { it.group == group }
        Bg.io({
            Bg.par(selected.map { src -> { discover(src) } }).filterNotNull().distinctBy { it.id }
        }) { result ->
            if (t != ask) return@io
            val items = result.orEmpty()
            cache[group] = items
            grid.message = when {
                result == null -> if (S.cur.code == "pt") "Não foi possível consultar os canais." else "Couldn't check channels."
                items.isEmpty() -> if (S.cur.code == "pt") "Nenhum canal oficial disponível nesta categoria agora." else "No official channel available in this category now."
                else -> null
            }
            grid.items = items; grid.busy = false; grid.invalidate()
        }
    }

    override fun onLayout(changed: Boolean, l: Int, t: Int, r: Int, b: Int) {
        val hh = Ui.u(130).toInt()
        chips.layout(0, Ui.u(20).toInt(), r - l, hh)
        grid.layout(0, hh, r - l, b - t)
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
        val next = sel + when (code) {
            KeyEvent.KEYCODE_DPAD_LEFT -> -1
            KeyEvent.KEYCODE_DPAD_RIGHT -> 1
            else -> return false
        }
        if (next !in labels().indices) return false
        sel = next; onChange(sel); invalidate(); return true
    }

    override fun render(c: android.graphics.Canvas, dt: Float) {
        val list = labels(); val pad = Ui.u(28); val gap = Ui.u(10)
        val widths = list.map { text.measureText(it) + Ui.u(48) }
        var x = pad
        list.forEachIndexed { i, label ->
            val w = widths[i]
            rect.set(x, Ui.u(14), x + w, height - Ui.u(14))
            if (i == sel) {
                fill.shader = android.graphics.LinearGradient(rect.left, 0f, rect.right, 0f, Ui.ACCENT, if (lit) Ui.ACCENT2 else Ui.ACCENT, android.graphics.Shader.TileMode.CLAMP)
                c.drawRoundRect(rect, rect.height()/2, rect.height()/2, fill)
            } else c.drawRoundRect(rect, rect.height()/2, rect.height()/2, face)
            text.color = if (i == sel) 0xFF0A0B14.toInt() else Ui.TEXT
            Txt.draw(c, label, rect.left, rect.centerY() + Ui.u(9), rect.width(), text, true)
            x += w + gap
        }
    }
}
