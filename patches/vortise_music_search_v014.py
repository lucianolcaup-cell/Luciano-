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

shutil.copyfile(REPO / "templates/MusicPage_v014.kt", ROOT / "app/src/main/kotlin/dev/limitedio/pipetv/ui/MusicPage.kt")

search = "app/src/main/kotlin/dev/limitedio/pipetv/ui/search/SearchPage.kt"
rw(search,
   '        Voice.onResult = { post { setText(it); submit(it) } }\n        Voice.onState = { keyboard.listening = Voice.active; orb.visibility = if (Voice.active) VISIBLE else GONE; orb.invalidate(); keyboard.invalidate() }\n',
   '        bindVoice()\n')
rw(search,
   '    fun picks(pick: (Item) -> Unit, menu: (Item) -> Unit) { grid.onPick = pick; grid.onMenu = menu }\n',
   '    private fun bindVoice() {\n        Voice.onResult = { post { setText(it); submit(it) } }\n        Voice.onState = { keyboard.listening = Voice.active; orb.visibility = if (Voice.active) VISIBLE else GONE; orb.invalidate(); keyboard.invalidate() }\n    }\n\n    fun enter() { bindVoice() }\n\n    fun picks(pick: (Item) -> Unit, menu: (Item) -> Unit) { grid.onPick = pick; grid.onMenu = menu }\n')

pages = "app/src/main/kotlin/dev/limitedio/pipetv/ui/Pages.kt"
rw(pages,
   '            0 -> if (homeAt == 0L || SystemClock.uptimeMillis() - homeAt > 600_000) loadHome()\n            2 -> music.enter()\n',
   '            0 -> if (homeAt == 0L || SystemClock.uptimeMillis() - homeAt > 600_000) loadHome()\n            1 -> search.enter()\n            2 -> music.enter()\n')

root = "app/src/main/kotlin/dev/limitedio/pipetv/ui/Root.kt"
rw(root,
   '        pages.search.onVoice = { voice() }\n',
   '        pages.search.onVoice = { voice() }\n        pages.music.onVoice = { voiceMusic() }\n')
rw(root,
   '    fun voice() { show(1); if (Voice.available(context)) askMic() else toast.show(S.t(K.VOICE_NA)) }\n',
   '    fun voice() { show(1); if (Voice.available(context)) askMic() else toast.show(S.t(K.VOICE_NA)) }\n    fun voiceMusic() { if (Voice.available(context)) askMic() else toast.show(S.t(K.VOICE_NA)) }\n')

print("Vortice Music v0.1.4 search patch applied")
