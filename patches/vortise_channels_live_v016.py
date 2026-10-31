from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src")
REL = "app/src/main/kotlin/dev/limitedio/pipetv/ui/OpenChannelsPage.kt"
P = ROOT / REL
s = P.read_text(encoding="utf-8")


def replace(old: str, new: str, count: int = 1):
    global s
    if old not in s:
        raise RuntimeError(f"Expected snippet not found in {REL}: {old[:180]!r}")
    s = s.replace(old, new, count)

# Live validation uses StreamInfo.streamType, not only words such as 'ao vivo' in a title.
replace(
'import java.text.Normalizer\n',
'import java.text.Normalizer\nimport android.os.SystemClock\nimport org.schabi.newpipe.extractor.stream.StreamType\n')

replace(
'''        listOf("Todos", "Notícias", "Públicos", "Cultura", "Geral", "Religiosos")
    else listOf("All", "News", "Public", "Culture", "General", "Religious")
''',
'''        listOf("Todos", "Notícias", "Públicos", "Cultura", "Geral", "Esportes", "Religiosos")
    else listOf("All", "News", "Public", "Culture", "General", "Sports", "Religious")
''')

replace(
'''        Source("CNN Brasil ao vivo", listOf("cnn brasil"), 1),
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
''',
'''        Source("CNN Brasil AO VIVO", listOf("cnn brasil"), 1),
        Source("Record News AO VIVO", listOf("record news"), 1),
        Source("Jovem Pan News AO VIVO", listOf("jovem pan news", "jovem pan"), 1),
        Source("BandNews TV AO VIVO", listOf("bandnews tv", "bandnews"), 1),
        Source("UOL News AO VIVO", listOf("uol news", "uol"), 1),

        Source("TV Brasil AO VIVO", listOf("tv brasil"), 2),
        Source("CanalGov AO VIVO", listOf("canalgov", "canal gov"), 2),
        Source("TV Senado AO VIVO", listOf("tv senado"), 2),
        Source("Câmara dos Deputados AO VIVO", listOf("camara dos deputados", "câmara dos deputados"), 2),
        Source("TV Justiça AO VIVO", listOf("tv justica", "tv justiça"), 2),

        Source("TV Cultura AO VIVO", listOf("tv cultura", "cultura"), 3),
        Source("TV Escola AO VIVO", listOf("tv escola"), 3),
        Source("Canal Futura AO VIVO", listOf("canal futura", "futura"), 3),

        Source("Band Jornalismo transmissão ao vivo", listOf("band jornalismo", "band"), 4),
        Source("SBT AO VIVO", listOf("sbt"), 4),
        Source("RedeTV AO VIVO", listOf("redetv", "rede tv"), 4),
        Source("TV Gazeta AO VIVO", listOf("tv gazeta", "gazeta"), 4),
        Source("Record TV AO VIVO", listOf("record tv", "record"), 4),

        Source("World Surf League LIVE", listOf("world surf league", "wsl"), 5),
        Source("Canal Olímpico do Brasil AO VIVO", listOf("canal olimpico do brasil", "olimpico do brasil"), 5),
        Source("CazéTV AO VIVO", listOf("cazetv", "caze tv"), 5),

        Source("TV Aparecida AO VIVO", listOf("tv aparecida"), 6),
        Source("Rede Vida AO VIVO", listOf("rede vida", "redevida"), 6),
''')

# Live results must expire quickly. A forever cache made the screen diverge from YouTube as soon
# as a live started/stopped while the app process remained open.
replace(
'''    private val cache = HashMap<Int, List<Item>>()
''',
'''    private data class CacheEntry(val items: List<Item>, val at: Long)
    private val cache = HashMap<Int, CacheEntry>()
    private val cacheTtlMs = 90_000L
''')

replace(
'''        if (cache[chips.sel] == null) show(chips.sel, false)
''',
'''        show(chips.sel, false)
''')

# Never accept a recording just because its title contains a channel name. Validate live state
# against the extracted stream metadata.
replace(
'''    private fun discover(src: Source): Item? {
        val list = runCatching { Yt.search(src.query, "videos").items }.getOrDefault(emptyList())
        val official = list.filter { trusted(it, src) }
        return official.maxByOrNull(::liveScore)?.takeIf { liveScore(it) > 0 }
            ?: official.firstOrNull()
    }
''',
'''    private fun actuallyLive(item: Item): Boolean = runCatching {
        val info = Yt.stream(item.url)
        info.streamType == StreamType.LIVE_STREAM || info.streamType == StreamType.AUDIO_LIVE_STREAM
    }.getOrDefault(false)

    private fun discover(src: Source): Item? {
        val variants = buildList {
            add(src.query)
            src.aliases.firstOrNull()?.let { add("$it ao vivo agora") }
            src.aliases.firstOrNull()?.let { add("$it live now") }
        }.distinct()
        val candidates = variants.flatMap { q ->
            runCatching { Yt.search(q, "videos").items }.getOrDefault(emptyList())
        }.distinctBy { it.id }
            .filter { trusted(it, src) }
            .filter { liveScore(it) > 0 }
            .sortedByDescending(::liveScore)

        // Verify up to the strongest candidates. This rejects old recordings titled "AO VIVO".
        return candidates.take(4).firstOrNull(::actuallyLive)
    }
''')

replace(
'''        if (!force) cache[group]?.let { grid.message = null; grid.items = it; grid.busy = false; return }
''',
'''        if (!force) cache[group]?.takeIf { SystemClock.uptimeMillis() - it.at < cacheTtlMs }?.let {
            grid.message = null; grid.items = it.items; grid.busy = false; grid.invalidate(); return
        }
''')

replace(
'''            cache[group] = items
''',
'''            cache[group] = CacheEntry(items, SystemClock.uptimeMillis())
''')

P.write_text(s, encoding="utf-8")
print("VórticeTv v0.1.6 live channels fidelity patch applied")
