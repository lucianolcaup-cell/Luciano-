from pathlib import Path
import shutil
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src")
REPO = Path(__file__).resolve().parents[1]

def rw(rel, old, new, count=1):
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    if old not in s:
        raise RuntimeError(f"Expected snippet not found in {rel}: {old[:100]!r}")
    p.write_text(s.replace(old, new, count), encoding="utf-8")

shutil.copyfile(REPO / "templates/OpenChannelsPage_v014.kt", ROOT / "app/src/main/kotlin/dev/limitedio/pipetv/ui/OpenChannelsPage.kt")

pages = "app/src/main/kotlin/dev/limitedio/pipetv/ui/Pages.kt"
rw(pages, '        music.picks(pick, menu); openChannels.onPick = pick; openChannels.onMenu = menu; popular.picks(pick, menu); favs.picks(pick, menu)\n',
          '        music.picks(pick, menu); openChannels.picks(pick, menu); popular.picks(pick, menu); favs.picks(pick, menu)\n')
rw(pages, 'fun back(i: Int): Boolean = when (i) { 1 -> search.back(); 2 -> music.back(); 4 -> popular.back(); 5 -> favs.back(); 7 -> closeSub(); else -> false }',
          'fun back(i: Int): Boolean = when (i) { 1 -> search.back(); 2 -> music.back(); 3 -> openChannels.back(); 4 -> popular.back(); 5 -> favs.back(); 7 -> closeSub(); else -> false }')
rw(pages, 'listOf(home, music.grid, openChannels, popular.grid, favs.grid)',
          'listOf(home, music.grid, openChannels.grid, popular.grid, favs.grid)')
rw(pages, 'is Grid -> v.focused(); is MusicPage -> v.grid.focused();',
          'is Grid -> v.focused(); is MusicPage -> v.grid.focused(); is OpenChannelsPage -> v.grid.focused();')
rw(pages,
   'is Grid -> { v.lit = on; v.invalidate() }; is SearchPage -> v.lit(on); is MusicPage -> v.lit(on); is FavsPage -> v.lit(on); is PopularPage -> v.lit(on);',
   'is Grid -> { v.lit = on; v.invalidate() }; is SearchPage -> v.lit(on); is MusicPage -> v.lit(on); is OpenChannelsPage -> v.lit(on); is FavsPage -> v.lit(on); is PopularPage -> v.lit(on);')
rw(pages,
   'is Grid -> v.key(code); is MusicPage -> v.key(code); is PopularPage -> v.key(code);',
   'is Grid -> v.key(code); is MusicPage -> v.key(code); is OpenChannelsPage -> v.key(code); is PopularPage -> v.key(code);')

print("VorticeTv v0.1.4 categorized open channels patch applied")
