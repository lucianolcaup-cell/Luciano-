from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src")


def write(rel: str, text: str):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


# v0.1.11: Open Channels only. Music/player code is intentionally untouched.
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
    private data class Source(
        val key: String,
        val queries: List<String>,
        val aliases: List<String>,
        val group: Int,
        val priority: Int = 0,
    )
    private data class GroupCache(val items: List<Item>, val at: Long)
    private data class SourceCache(val item: Item, val at: Long)

    private fun labels() = if (S.cur.code == "pt")
        listOf("Todos", "Notícias", "Públicos", "Cultura", "Geral", "Esportes", "Religiosos")
    else listOf("All", "News", "Public", "Culture", "General", "Sports", "Religious")

    private val sources = listOf(
        Source("cnn", listOf("CNN Brasil ao vivo", "CNN Brasil live", "CNN Brasil agora"), listOf("cnn brasil", "cnn"), 1, 100),
        Source("recordnews", listOf("Record News ao vivo", "Record News live"), listOf("record news"), 1, 95),
        Source("bandnews", listOf("BandNews TV ao vivo", "BandNews ao vivo"), listOf("bandnews tv", "bandnews"), 1, 90),
        Source("jovempan", listOf("Jovem Pan News ao vivo", "Jovem Pan News live"), listOf("jovem pan news", "jovem pan"), 1, 85),
        Source("uolnews", listOf("UOL News ao vivo", "UOL ao vivo agora"), listOf("uol news", "uol"), 1, 80),

        Source("tvbrasil", listOf("TV Brasil ao vivo", "TV Brasil live"), listOf("tv brasil"), 2, 100),
        Source("canalgov", listOf("CanalGov ao vivo", "Canal Gov ao vivo"), listOf("canalgov", "canal gov"), 2, 90),
        Source("tvsenado", listOf("TV Senado ao vivo", "Senado ao vivo"), listOf("tv senado", "senado"), 2, 85),
        Source("camara", listOf("Câmara dos Deputados ao vivo", "TV Câmara ao vivo"), listOf("camara dos deputados", "câmara dos deputados", "tv camara", "tv câmara"), 2, 80),
        Source("tvjustica", listOf("TV Justiça ao vivo", "TV Justica ao vivo"), listOf("tv justica", "tv justiça"), 2, 75),

        Source("tvcultura", listOf("TV Cultura ao vivo", "Cultura ao vivo"), listOf("tv cultura", "cultura"), 3, 100),
        Source("futura", listOf("Canal Futura ao vivo", "Futura ao vivo"), listOf("canal futura", "futura"), 3, 80),

        Source("band", listOf("Band ao vivo", "Band Jornalismo ao vivo"), listOf("band jornalismo", "band"), 4, 100),
        Source("sbt", listOf("SBT ao vivo", "SBT live"), listOf("sbt"), 4, 90),
        Source("redetv", listOf("RedeTV ao vivo", "Rede TV ao vivo"), listOf("redetv", "rede tv"), 4, 85),
        Source("tvgazeta", listOf("TV Gazeta ao vivo", "Gazeta ao vivo"), listOf("tv gazeta", "gazeta"), 4, 75),

        Source("cazetv", listOf("CazéTV ao vivo", "CazeTV ao vivo"), listOf("cazetv", "caze tv"), 5, 100),
        Source("olimpico", listOf("Canal Olímpico do Brasil ao vivo", "Canal Olimpico do Brasil ao vivo"), listOf("canal olimpico do brasil", "olimpico do brasil"), 5, 85),
        Source("wsl", listOf("World Surf League live", "WSL live"), listOf("world surf league", "wsl"), 5, 75),

        Source("aparecida", listOf("TV Aparecida ao vivo", "Aparecida ao vivo"), listOf("tv aparecida", "aparecida"), 6, 100),
        Source("redevida", listOf("Rede Vida ao vivo", "RedeVida ao vivo"), listOf("rede vida", "redevida"), 6, 90),
    )

    val grid = Grid(c) { labels()[chips.sel] }.apply { upExit = true }
    private val chips = ChannelChips(c) { labels() }

    // Stale-while-revalidate: fast return from cache, silent refresh later.
    private val groupCache = HashMap<Int, GroupCache>()
    private val sourceCache = HashMap<String, SourceCache>()
    private val groupFreshMs = 120_000L
    private val groupUsableMs = 900_000L
    private val sourceFreshMs = 600_000L

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
        val uploader = norm(item.by)
        val title = norm(item.title)
        return src.aliases.map(::norm).any { alias ->
            uploader.contains(alias) || title.contains(alias)
        }
    }

    private fun liveCue(item: Item): Int {
        if (item.isLive) return 100
        val t = norm(item.title)
        var score = 0
        if ("ao vivo" in t || "live" in t) score += 40
        if ("24h" in t || "24 horas" in t) score += 25
        if ("agora" in t || "now" in t) score += 10
        return score
    }

    private fun metadataLive(item: Item): Boolean = runCatching {
        val info = Yt.stream(item.url)
        info.streamType == StreamType.LIVE_STREAM || info.streamType == StreamType.AUDIO_LIVE_STREAM
    }.getOrDefault(false)

    private fun discover(src: Source): Item? {
        val candidates = LinkedHashMap<String, Item>()

        // Primary query first; alternate queries only when needed.
        for ((index, query) in src.queries.withIndex()) {
            val found = runCatching { Yt.search(query, "videos").items }.getOrDefault(emptyList())
                .filter { trusted(it, src) }
                .sortedByDescending(::liveCue)
                .take(8)
            found.forEach { candidates.putIfAbsent(it.id, it) }

            candidates.values.firstOrNull { it.isLive }?.let { return it }
            if (index == 0 && candidates.values.any { liveCue(it) >= 40 }) break
        }

        val ranked = candidates.values.sortedByDescending(::liveCue)
        ranked.firstOrNull { it.isLive }?.let { return it }

        // Metadata extraction is expensive; validate only the strongest live-looking results.
        return ranked.filter { liveCue(it) >= 25 }.take(3).firstOrNull(::metadataLive)
    }

    private fun selectedSources(group: Int): List<Source> =
        (if (group == 0) sources else sources.filter { it.group == group })
            .sortedByDescending { it.priority }

    private fun show(group: Int, force: Boolean) {
        val now = SystemClock.uptimeMillis()
        val token = ++generation
        val selected = selectedSources(group)

        if (selected.isEmpty()) {
            grid.items = emptyList(); grid.busy = false; grid.loading = false; grid.message = noLive(); grid.invalidate(); return
        }

        val cachedGroup = groupCache[group]
        if (!force && cachedGroup != null && now - cachedGroup.at < groupFreshMs) {
            grid.items = cachedGroup.items
            grid.busy = false; grid.loading = false
            grid.message = if (cachedGroup.items.isEmpty()) noLive() else null
            grid.invalidate(); return
        }

        val found = LinkedHashMap<String, Item>()
        var showedCached = false

        // Keep a usable stale group visible while refreshing in background.
        if (!force && cachedGroup != null && now - cachedGroup.at < groupUsableMs && cachedGroup.items.isNotEmpty()) {
            cachedGroup.items.forEach { found[it.id] = it }
            grid.items = found.values.toList(); grid.busy = false; grid.loading = false; grid.message = null
            grid.invalidate(); showedCached = true
        }

        val pending = ArrayList<Source>()
        selected.forEach { src ->
            val hit = if (!force) sourceCache[src.key] else null
            if (hit != null && now - hit.at < sourceFreshMs) {
                if (found.putIfAbsent(hit.item.id, hit.item) == null) {
                    grid.items = found.values.toList(); grid.busy = false; grid.loading = false; grid.message = null; grid.invalidate()
                }
            } else pending += src
        }

        if (pending.isEmpty()) {
            val items = found.values.toList()
            groupCache[group] = GroupCache(items, now)
            grid.items = items; grid.busy = false; grid.loading = false
            grid.message = if (items.isEmpty()) noLive() else null
            grid.invalidate(); return
        }

        if (found.isEmpty() && !showedCached) {
            grid.items = emptyList(); grid.busy = true; grid.loading = true
            grid.message = if (S.cur.code == "pt") "Buscando canais oficiais ao vivo…" else "Finding official live channels…"
            grid.invalidate()
        } else {
            // Results are already useful. Do not keep the screen visually spinning while refresh continues.
            grid.busy = false; grid.loading = false; grid.message = null; grid.invalidate()
        }

        var finished = 0
        pending.forEach { src ->
            Bg.io({ discover(src) }) { item ->
                if (token != generation) return@io
                finished++

                if (item != null) {
                    sourceCache[src.key] = SourceCache(item, SystemClock.uptimeMillis())
                    if (found.putIfAbsent(item.id, item) == null) {
                        grid.items = found.values.toList()
                        grid.busy = false; grid.loading = false; grid.message = null
                        grid.invalidate()
                    }
                }

                if (finished >= pending.size) {
                    val items = found.values.toList()
                    groupCache[group] = GroupCache(items, SystemClock.uptimeMillis())
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
                fill.shader = android.graphics.LinearGradient(
                    rect.left, 0f, rect.right, 0f,
                    Ui.ACCENT, if (lit) Ui.ACCENT2 else Ui.ACCENT,
                    android.graphics.Shader.TileMode.CLAMP,
                )
                c.drawRoundRect(rect, rect.height() / 2, rect.height() / 2, fill)
            } else c.drawRoundRect(rect, rect.height() / 2, rect.height() / 2, face)
            text.color = if (i == sel) 0xFF0A0B14.toInt() else Ui.TEXT
            Txt.draw(c, label, rect.left, rect.centerY() + Ui.u(9), rect.width(), text, true)
            x += w + gap
        }
    }
}
''')

print("VórticeTv v0.1.11 open channels performance patch applied")
