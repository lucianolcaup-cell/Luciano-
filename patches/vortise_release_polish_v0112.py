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


# 1) Prefer Brazilian Portuguese / Portuguese audio tracks automatically.
audio = "app/src/main/kotlin/dev/limitedio/pipetv/media/Audio.kt"
rw(audio,
'''object AudioOpts {
    private fun best(g: List<AudioStream>) = g.sortedWith(compareByDescending<AudioStream> { it.format == MediaFormat.M4A }
        .thenByDescending { it.averageBitrate }).first()
''',
'''object AudioOpts {
    private fun best(g: List<AudioStream>) = g.sortedWith(compareByDescending<AudioStream> { it.format == MediaFormat.M4A }
        .thenByDescending { it.averageBitrate }).first()

    private fun languageRank(s: AudioStream): Int {
        val tag = s.audioLocale?.toLanguageTag()?.lowercase(Locale.ROOT).orEmpty()
        return when {
            tag == "pt-br" -> 0
            tag.startsWith("pt") -> 1
            s.audioTrackType == AudioTrackType.ORIGINAL -> 2
            else -> 3
        }
    }
''')
rw(audio,
'''        if (groups.size > 1) {
            return groups.values.map { AudioOpt(name(best(it)), best(it)) }.sortedBy { if (it.label.endsWith(S.t(K.AUDIO_ORIGINAL))) 0 else 1 }
        }
''',
'''        if (groups.size > 1) {
            return groups.values
                .map { best(it) }
                .map { AudioOpt(name(it), it) }
                .sortedWith(compareBy<AudioOpt> { languageRank(it.stream) }
                    .thenByDescending { it.stream.format == MediaFormat.M4A }
                    .thenByDescending { it.stream.averageBitrate })
        }
''')


# 2) Search in Portuguese: prefer localized spoken content without doubling normal requests.
# If the localized query returns no result, immediately fall back to the exact original query.
search = "app/src/main/kotlin/dev/limitedio/pipetv/ui/search/SearchData.kt"
rw(search,
'''    fun suggestions(q: String) {
        val t = ++token
        Bg.io({ Yt.suggestions(q) }) { r -> if (t == token && r != null && !results) { suggest.recent = false; suggest.items = r.take(8) } }
    }

    fun search(q: String, filter: String) {
''',
'''    fun suggestions(q: String) {
        val t = ++token
        Bg.io({ Yt.suggestions(q) }) { r -> if (t == token && r != null && !results) { suggest.recent = false; suggest.items = r.take(8) } }
    }

    private fun preferredQuery(q: String, filter: String): String {
        if (S.cur.code != "pt" || filter.startsWith("music_") || filter.contains("channel", true)) return q
        val normalized = q.lowercase()
        val explicitLanguage = listOf(
            "português", "portugues", "pt-br", "brasileiro", "brasileira", "dublado", "dublada",
            "inglês", "ingles", "espanhol", "francês", "frances", "legendado", "legendada"
        ).any { normalized.contains(it) }
        return if (explicitLanguage) q else "$q português"
    }

    fun search(q: String, filter: String) {
''')
rw(search,
'''        val t = ++token
        Bg.io({ Yt.search(q, filter) }) { r ->
''',
'''        val t = ++token
        val networkQuery = preferredQuery(q, filter)
        Bg.io({
            val preferred = Yt.search(networkQuery, filter)
            if (networkQuery != q && (preferred == null || preferred.items.isEmpty())) Yt.search(q, filter) else preferred
        }) { r ->
''')


# 3) Music <-> video transition: immediately free the old decoder/network stream when changing mode.
# Same-mode transitions keep the previous content until the new stream is ready.
session = "app/src/main/kotlin/dev/limitedio/pipetv/media/Session.kt"
rw(session,
'''        pending = it; expand = expandWhenReady
        val openingMusic = nextMusic; nextMusic = false
        val t = ++token
        changed()
''',
'''        pending = it; expand = expandWhenReady
        val openingMusic = nextMusic; nextMusic = false
        val switchingMediaMode = item != null && musicMode != openingMusic
        if (switchingMediaMode) {
            Progress.save()
            SponsorBlock.reset()
            Engine.exo.stop()
            Engine.frame = false
        }
        val t = ++token
        changed()
''')

print("VórticeTv v0.1.12 release polish applied")
