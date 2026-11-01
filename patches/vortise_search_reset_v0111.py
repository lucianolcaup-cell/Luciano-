from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src")
REL = "app/src/main/kotlin/dev/limitedio/pipetv/ui/search/SearchPage.kt"
P = ROOT / REL
s = P.read_text(encoding="utf-8")

old = '''    fun enter() { bindVoice() }
'''
new = '''    fun enter() {
        bindVoice()
        // A new visit to Search always starts clean. Keep stored history/recents,
        // but never leave the previous typed query or result grid on screen.
        Bg.main.removeCallbacks(ask)
        Bg.main.removeCallbacks(refilter)
        setText("")
        showList(true)
        setZone(0)
        relayout()
    }
'''

if old not in s:
    raise RuntimeError("SearchPage.enter() signature not found after voice patch")
P.write_text(s.replace(old, new, 1), encoding="utf-8")
print("VórticeTv v0.1.11 Search reset patch applied")
