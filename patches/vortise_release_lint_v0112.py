from pathlib import Path
import re
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


def ensure_import(rel: str, anchor: str, imp: str):
    s = read(rel)
    if imp not in s:
        if anchor not in s:
            raise RuntimeError(f"Import anchor not found in {rel}: {anchor!r}")
        s = s.replace(anchor, anchor + imp, 1)
        write(rel, s)


# API 21 compatibility: Html.fromHtml(mode) and contentLengthLong were added in API 24.
subs = "app/src/main/kotlin/dev/limitedio/pipetv/media/Subs.kt"
ensure_import(subs, "import android.text.Html\n", "import android.os.Build\n")
s = read(subs)
plain_pattern = re.compile(r"    private fun plain\(s: String\).*?\n\n    private fun parse", re.S)
if not plain_pattern.search(s):
    raise RuntimeError("Subs.plain() block not found")
plain_impl = r'''    private fun plain(s: String): String {
        val src = s.replace(Regex("<br\\s*/?>"), "\n").replace(Regex("<[^>]+>"), "")
        @Suppress("DEPRECATION")
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            Html.fromHtml(src, Html.FROM_HTML_MODE_LEGACY).toString().trim()
        } else {
            Html.fromHtml(src).toString().trim()
        }
    }

    private fun parse'''
s = plain_pattern.sub(lambda _: plain_impl, s, count=1)
write(subs, s)

ytpages = "app/src/main/kotlin/dev/limitedio/pipetv/data/YtPages.kt"
ensure_import(ytpages, "import android.text.Html\n", "import android.os.Build\n")
s = read(ytpages)
plain_desc = re.compile(r"    fun plain\(d: Description\?\): String = when \{.*?\n    \}\n\n    fun channel", re.S)
if not plain_desc.search(s):
    raise RuntimeError("YtPages.plain() block not found")
yt_impl = '''    fun plain(d: Description?): String = when {
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

    fun channel'''
s = plain_desc.sub(lambda _: yt_impl, s, count=1)
write(ytpages, s)

updater = "app/src/main/kotlin/dev/limitedio/pipetv/update/Updater.kt"
ensure_import(updater, "import java.net.URL\n", "import android.os.Build\n")
s = read(updater)
old_fetch = '        val out = file ?: return; val c = open(url); val total = c.contentLengthLong.takeIf { it > 0 } ?: size.coerceAtLeast(1)\n'
if old_fetch in s:
    s = s.replace(old_fetch, '''        val out = file ?: return; val c = open(url)
        @Suppress("DEPRECATION")
        val reportedLength = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) c.contentLengthLong else c.contentLength.toLong()
        val total = reportedLength.takeIf { it > 0 } ?: size.coerceAtLeast(1)
''', 1)
elif "val reportedLength = if (Build.VERSION.SDK_INT" not in s:
    raise RuntimeError("Updater content length block not found")
write(updater, s)

# These TV views intentionally refit children immediately after dynamic state changes.
# Document the intentional direct onLayout call at the class level; behavior stays unchanged.
for rel, declaration in [
    ("app/src/main/kotlin/dev/limitedio/pipetv/ui/detail/ChannelPage.kt", "class ChannelPage("),
    ("app/src/main/kotlin/dev/limitedio/pipetv/ui/MusicPage.kt", "class MusicPage("),
    ("app/src/main/kotlin/dev/limitedio/pipetv/ui/search/SearchPage.kt", "class SearchPage("),
    ("app/src/main/kotlin/dev/limitedio/pipetv/ui/Stage.kt", "class Stage("),
]:
    s = read(rel)
    if "import android.annotation.SuppressLint\n" not in s:
        package_line_end = s.find("\n", s.find("package ")) + 1
        s = s[:package_line_end] + "\nimport android.annotation.SuppressLint\n" + s[package_line_end:]
    tag = '@SuppressLint("WrongCall")\n'
    if tag + declaration not in s:
        if declaration not in s:
            raise RuntimeError(f"Class declaration not found in {rel}: {declaration}")
        s = s.replace(declaration, tag + declaration, 1)
    write(rel, s)

# Media3 1.5.1 exposes these APIs under UnstableApi. Explicitly opt in at state-owning objects.
for rel, declaration in [
    ("app/src/main/kotlin/dev/limitedio/pipetv/media/Engine.kt", "object Engine {"),
    ("app/src/main/kotlin/dev/limitedio/pipetv/media/Sources.kt", "object Sources {"),
    ("app/src/main/kotlin/dev/limitedio/pipetv/media/Session.kt", "object Session {"),
]:
    s = read(rel)
    annotation = "@androidx.annotation.OptIn(androidx.media3.common.util.UnstableApi::class)\n"
    if annotation not in s:
        if declaration not in s:
            raise RuntimeError(f"Media3 owner declaration not found in {rel}: {declaration}")
        s = s.replace(declaration, annotation + declaration, 1)
    write(rel, s)

# Remove impossible null check: Yt.search returns a Paged instance, not nullable.
search = "app/src/main/kotlin/dev/limitedio/pipetv/ui/search/SearchData.kt"
s = read(search)
s = s.replace('if (networkQuery != q && (preferred == null || preferred.items.isEmpty())) Yt.search(q, filter) else preferred',
              'if (networkQuery != q && preferred.items.isEmpty()) Yt.search(q, filter) else preferred')
write(search, s)

print("VórticeTv v0.1.12 API21 + Lint compatibility patch applied")
