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


# API 21 compatibility: Html.fromHtml(mode) and contentLengthLong were added in API 24.
subs = "app/src/main/kotlin/dev/limitedio/pipetv/media/Subs.kt"
rw(subs, "import android.text.Html\n", "import android.text.Html\nimport android.os.Build\n")
rw(subs,
'''    private fun plain(s: String) = Html.fromHtml(s.replace(Regex("<br\\s*/?>"), "\\n").replace(Regex("<[^>]+>"), ""), Html.FROM_HTML_MODE_LEGACY).toString().trim()
''',
'''    private fun plain(s: String): String {
        val src = s.replace(Regex("<br\\s*/?>"), "\\n").replace(Regex("<[^>]+>"), "")
        @Suppress("DEPRECATION")
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            Html.fromHtml(src, Html.FROM_HTML_MODE_LEGACY).toString().trim()
        } else {
            Html.fromHtml(src).toString().trim()
        }
    }
''')

ytpages = "app/src/main/kotlin/dev/limitedio/pipetv/data/YtPages.kt"
rw(ytpages, "import android.text.Html\n", "import android.text.Html\nimport android.os.Build\n")
rw(ytpages,
'''    fun plain(d: Description?): String = when {
        d == null -> ""
        d.type == Description.HTML -> Html.fromHtml(d.content, Html.FROM_HTML_MODE_LEGACY).toString().trim()
        else -> d.content.trim()
    }
''',
'''    fun plain(d: Description?): String = when {
        d == null -> ""
        d.type == Description.HTML -> {
            @Suppress("DEPRECATION")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                Html.fromHtml(d.content, Html.FROM_HTML_MODE_LEGACY).toString().trim()
            } else {
                Html.fromHtml(d.content).toString().trim()
            }
        }
        else -> d.content.trim()
    }
''')

updater = "app/src/main/kotlin/dev/limitedio/pipetv/update/Updater.kt"
rw(updater, "import java.net.URL\n", "import java.net.URL\nimport android.os.Build\n")
rw(updater,
'''        val out = file ?: return; val c = open(url); val total = c.contentLengthLong.takeIf { it > 0 } ?: size.coerceAtLeast(1)
''',
'''        val out = file ?: return; val c = open(url)
        @Suppress("DEPRECATION")
        val reportedLength = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) c.contentLengthLong else c.contentLength.toLong()
        val total = reportedLength.takeIf { it > 0 } ?: size.coerceAtLeast(1)
''')

# These custom TV views deliberately perform an immediate child refit after dynamic state changes.
# Keep the proven runtime behavior and document the intentional onLayout invocation for Lint.
for rel, declaration in [
    ("app/src/main/kotlin/dev/limitedio/pipetv/ui/detail/ChannelPage.kt", "class ChannelPage("),
    ("app/src/main/kotlin/dev/limitedio/pipetv/ui/MusicPage.kt", "class MusicPage("),
    ("app/src/main/kotlin/dev/limitedio/pipetv/ui/search/SearchPage.kt", "class SearchPage("),
    ("app/src/main/kotlin/dev/limitedio/pipetv/ui/Stage.kt", "class Stage("),
]:
    s = read(rel)
    if "import android.annotation.SuppressLint\n" not in s:
        marker = "\n\nimport "
        pos = s.find(marker)
        if pos < 0:
            raise RuntimeError(f"Import section not found in {rel}")
        s = s[:pos+2] + "import android.annotation.SuppressLint\n" + s[pos+2:]
    if f"@SuppressLint(\"WrongCall\")\n{declaration}" not in s:
        if declaration not in s:
            raise RuntimeError(f"Class declaration not found in {rel}: {declaration}")
        s = s.replace(declaration, f"@SuppressLint(\"WrongCall\")\n{declaration}", 1)
    write(rel, s)

# Media3 1.5.1 intentionally exposes several player-building APIs under UnstableApi.
# Explicitly opt in at the smallest state-owning objects instead of suppressing the lint error.
for rel, declaration in [
    ("app/src/main/kotlin/dev/limitedio/pipetv/media/Engine.kt", "object Engine {"),
    ("app/src/main/kotlin/dev/limitedio/pipetv/media/Sources.kt", "object Sources {"),
    ("app/src/main/kotlin/dev/limitedio/pipetv/media/Session.kt", "object Session {"),
]:
    s = read(rel)
    annotation = "@androidx.annotation.OptIn(markerClass = [androidx.media3.common.util.UnstableApi::class])\n"
    if annotation not in s:
        if declaration not in s:
            raise RuntimeError(f"Media3 owner declaration not found in {rel}: {declaration}")
        s = s.replace(declaration, annotation + declaration, 1)
    write(rel, s)

# Remove a compiler warning introduced by the localized-search patch: Yt.search is non-null.
search = "app/src/main/kotlin/dev/limitedio/pipetv/ui/search/SearchData.kt"
s = read(search)
s = s.replace('if (networkQuery != q && (preferred == null || preferred.items.isEmpty())) Yt.search(q, filter) else preferred',
              'if (networkQuery != q && preferred.items.isEmpty()) Yt.search(q, filter) else preferred')
write(search, s)

print("VórticeTv v0.1.12 API21 + Lint compatibility patch applied")
