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
        raise RuntimeError(f"Expected snippet not found in {rel}: {old[:100]!r}")
    write(rel, text.replace(old, new, count))


# Dedicated official/public live TV page. It never embeds unauthorized IPTV lists.
write("app/src/main/kotlin/dev/limitedio/pipetv/ui/OpenChannelsPage.kt", r'''package dev.limitedio.pipetv.ui

import android.content.Context
import android.os.SystemClock
import dev.limitedio.pipetv.Bg
import dev.limitedio.pipetv.data.Item
import dev.limitedio.pipetv.data.Yt
import dev.limitedio.pipetv.i18n.S

/**
 * Brazilian open/public TV streams discovered from the broadcasters' own YouTube presence.
 * Only trusted uploader names and live-labelled streams are accepted; no third-party IPTV lists.
 */
class OpenChannelsPage(c: Context) : Grid(c, {
    if (S.cur.code == "pt") "Canais Abertos · transmissões oficiais" else "Open TV · official streams"
}) {
    private data class Source(val query: String, val uploaders: List<String>)

    private val sources = listOf(
        Source("TV Brasil ao vivo", listOf("tv brasil")),
        Source("CanalGov ao vivo", listOf("canalgov", "canal gov")),
        Source("TV Senado ao vivo", listOf("tv senado")),
        Source("Câmara dos Deputados ao vivo", listOf("câmara dos deputados", "camara dos deputados")),
        Source("TV Cultura ao vivo", listOf("tv cultura", "cultura")),
        Source("TV Justiça ao vivo", listOf("tv justiça", "tv justica")),
    )

    private var loadedAt = 0L
    private var ask = 0

    init {
        cols = 3
        upExit = true
        busy = true
        onRetry = { loadedAt = 0; load(true) }
    }

    fun enter() {
        if (loadedAt == 0L || SystemClock.uptimeMillis() - loadedAt > 300_000L) load(false)
    }

    private fun norm(s: String) = java.text.Normalizer.normalize(s.lowercase(), java.text.Normalizer.Form.NFD)
        .replace(Regex("\\p{Mn}+"), "")

    private fun trusted(item: Item, src: Source): Boolean {
        if (item.kind != Item.VIDEO) return false
        val uploader = norm(item.by)
        val title = norm(item.title)
        val official = src.uploaders.map(::norm).any { name -> uploader == name || uploader.contains(name) }
        val looksLive = item.isLive || title.contains("ao vivo") || title.contains("live")
        return official && looksLive
    }

    private fun load(force: Boolean) {
        if (!force && busy) return
        val token = ++ask
        busy = items.isEmpty(); loading = !busy; message = if (busy) {
            if (S.cur.code == "pt") "Buscando transmissões oficiais…" else "Finding official live streams…"
        } else null
        invalidate()
        Bg.io({
            val tasks = sources.map { src ->
                { runCatching { Yt.search(src.query, "videos").items.firstOrNull { trusted(it, src) } }.getOrNull() }
            }
            Bg.par(tasks).filterNotNull().distinctBy { it.id }
        }) { result ->
            if (token != ask) return@io
            loadedAt = SystemClock.uptimeMillis()
            busy = false; loading = false
            val list = result.orEmpty()
            items = list
            message = when {
                result == null -> if (S.cur.code == "pt") "Não foi possível consultar os canais." else "Couldn't check channels."
                list.isEmpty() -> if (S.cur.code == "pt") "Nenhuma transmissão oficial disponível agora." else "No official live stream available now."
                else -> null
            }
            invalidate()
        }
    }
}
''')

# Pages: add Open Channels between Music and Popular.
pages = "app/src/main/kotlin/dev/limitedio/pipetv/ui/Pages.kt"
replace(pages, '    val music = MusicPage(c)\n    val popular = PopularPage(c)\n', '    val music = MusicPage(c)\n    val openChannels = OpenChannelsPage(c)\n    val popular = PopularPage(c)\n')
replace(pages, '    val views: List<View> = listOf(home, search, music, popular, favs, history, settings)\n', '    val views: List<View> = listOf(home, search, music, openChannels, popular, favs, history, settings)\n')
replace(pages, '        music.picks(pick, menu); popular.picks(pick, menu); favs.picks(pick, menu)\n', '        music.picks(pick, menu); openChannels.onPick = pick; openChannels.onMenu = menu; popular.picks(pick, menu); favs.picks(pick, menu)\n')
replace(pages, '''            2 -> music.enter()\n            3 -> popular.enter()\n            4 -> favs.enter()\n            5 -> history.reload()\n''', '''            2 -> music.enter()\n            3 -> openChannels.enter()\n            4 -> popular.enter()\n            5 -> favs.enter()\n            6 -> history.reload()\n''')
replace(pages, 'fun back(i: Int): Boolean = when (i) { 1 -> search.back(); 2 -> music.back(); 3 -> popular.back(); 4 -> favs.back(); 6 -> closeSub(); else -> false }', 'fun back(i: Int): Boolean = when (i) { 1 -> search.back(); 2 -> music.back(); 4 -> popular.back(); 5 -> favs.back(); 7 -> closeSub(); else -> false }')
replace(pages, 'listOf(home, music.grid, popular.grid, favs.grid)', 'listOf(home, music.grid, openChannels, popular.grid, favs.grid)')
replace(pages, 'is Grid -> v.focused(); is MusicPage -> v.grid.focused();', 'is Grid -> v.focused(); is MusicPage -> v.grid.focused();')
# OpenChannelsPage inherits Grid, so the existing `is Grid` branch already covers focus/lit/key.

# Add a simple TV icon.
icons = "app/src/main/kotlin/dev/limitedio/pipetv/ui/Icons.kt"
replace(icons, 'const val SHIFT = 7; const val MUSIC = 8', 'const val SHIFT = 7; const val MUSIC = 8; const val TV = 9')
replace(icons, '            MUSIC -> {\n', '''            TV -> {\n                RowRect.set(cx - r, cy - r * .7f, cx + r, cy + r * .65f)\n                c.drawRoundRect(RowRect, r * .15f, r * .15f, p)\n                c.drawLine(cx - r * .35f, cy + r, cx + r * .35f, cy + r, p)\n                c.drawLine(cx, cy + r * .65f, cx, cy + r, p)\n            }\n            MUSIC -> {\n''')

# Navigation: add Canais Abertos and shift Exit.
nav = "app/src/main/kotlin/dev/limitedio/pipetv/ui/Nav.kt"
replace(nav,
    '    private val tabs get() = listOf(S.t(K.HOME) to Icons.HOME, S.t(K.SEARCH) to Icons.SEARCH, S.t(K.T_MUSIC) to Icons.MUSIC, S.t(K.POPULAR) to Icons.TREND,\n        S.t(K.FAVORITES) to Glyphs.FAV, S.t(K.HISTORY) to Icons.HISTORY, S.t(K.SETTINGS) to Icons.SETTINGS, S.t(K.EXIT) to Glyphs.EXIT)\n',
    '    private val tabs get() = listOf(S.t(K.HOME) to Icons.HOME, S.t(K.SEARCH) to Icons.SEARCH, S.t(K.T_MUSIC) to Icons.MUSIC,\n        (if (S.cur.code == "pt") "Canais Abertos" else "Open TV") to Icons.TV, S.t(K.POPULAR) to Icons.TREND,\n        S.t(K.FAVORITES) to Glyphs.FAV, S.t(K.HISTORY) to Icons.HISTORY, S.t(K.SETTINGS) to Icons.SETTINGS, S.t(K.EXIT) to Glyphs.EXIT)\n')
replace(nav, 'pill.to(if (v) 7f else sel.toFloat())', 'pill.to(if (v) 8f else sel.toFloat())')
replace(nav, 'val on = if (exit) i == 7 else i == sel', 'val on = if (exit) i == 8 else i == sel')

# Remote navigation: 8 pages (0..7) plus Exit.
controls = "app/src/main/kotlin/dev/limitedio/pipetv/ui/Controls.kt"
replace(controls, 'else if (root.tab < 6) root.show(root.tab + 1) else root.nav.exit = true', 'else if (root.tab < 7) root.show(root.tab + 1) else root.nav.exit = true')

print("Vórtise TV open channels patch applied successfully")
