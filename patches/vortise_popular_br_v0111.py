from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel: str, text: str):
    p = ROOT / rel
    p.write_text(text, encoding="utf-8")


def rw(rel: str, old: str, new: str, count: int = 1):
    s = read(rel)
    if old not in s:
        raise RuntimeError(f"Expected snippet not found in {rel}: {old[:180]!r}")
    write(rel, s.replace(old, new, count))

# YouTube no longer exposes one general public Trending page. Use the remaining
# official category kiosks, forced to pt-BR / BR only for these extractors.
yt = "app/src/main/kotlin/dev/limitedio/pipetv/data/Yt.kt"
rw(yt,
'''    fun trending(): List<Item> {
        init()
        val url = svc.kioskList.getListLinkHandlerFactoryByType("Trending").fromId("Trending").url
        return YtMap.items(KioskInfo.getInfo(svc, url).relatedItems)
    }
''',
'''    fun trending(): List<Item> {
        init()
        return runCatching { kioskBrazil("live") }.getOrDefault(emptyList())
    }

    /** One of YouTube's remaining official category kiosks, explicitly localized to Brazil. */
    fun kioskBrazil(id: String): List<Item> {
        init()
        val extractor = svc.kioskList.getExtractorById(id, null)
        extractor.forceLocalization(Localization("pt", "BR"))
        extractor.forceContentCountry(ContentCountry("BR"))
        extractor.fetchPage()
        return YtMap.items(KioskInfo.getInfo(extractor).relatedItems)
    }
''')

feed = "app/src/main/kotlin/dev/limitedio/pipetv/data/Feed.kt"
rw(feed,
'''    fun trending(): List<Item> =
        runCatching { Yt.trending() }.getOrNull()?.takeIf { it.isNotEmpty() } ?: Yt.search("trending now").items
''',
'''    fun trending(): List<Item> = popularBrazil()

    /**
     * Best public equivalent of "what Brazil is watching now" after YouTube removed
     * the single general Trending page: merge the official Brazil-localized trend
     * kiosks while preserving each chart's own order and removing duplicates.
     */
    fun popularBrazil(): List<Item> {
        val ids = listOf("trending_music", "trending_gaming", "trending_movies_and_shows", "live")
        val lists = ids.mapNotNull { id ->
            runCatching { Yt.kioskBrazil(id).filter { it.kind == Item.VIDEO } }
                .getOrNull()?.takeIf { it.isNotEmpty() }
        }
        if (lists.isEmpty()) return emptyList()

        val out = LinkedHashMap<String, Item>()
        val max = lists.maxOfOrNull { it.size } ?: 0
        for (i in 0 until max) {
            for (list in lists) list.getOrNull(i)?.let { out.putIfAbsent(it.id, it) }
            if (out.size >= 100) break
        }
        return out.values.take(100)
    }
''')

# First Popular tab must use the Brazil chart composite, not a text search.
pop = "app/src/main/kotlin/dev/limitedio/pipetv/ui/PopularPage.kt"
rw(pop,
'''            if (i == 0) Feed.trending() else {
''',
'''            if (i == 0) Feed.popularBrazil() else {
''')

print("VórticeTv v0.1.11 Popular Brasil patch applied")
