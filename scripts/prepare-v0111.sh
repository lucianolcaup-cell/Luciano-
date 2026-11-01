#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-src}"
BRANDING="${2:-branding-repo}"

cd "$ROOT"
sed -i 's/applicationId = "dev.limitedio.pipetv"/applicationId = "br.com.luciano.noutubetv"/' app/build.gradle.kts
sed -i 's/android:label="PipeTv"/android:label="VórticeTv"/' app/src/main/AndroidManifest.xml
rm -f app/src/main/res/drawable-xhdpi/icon.png app/src/main/res/drawable-xhdpi/banner.png
base64 -d "../$BRANDING/branding/vortise_icon.b64" > app/src/main/res/drawable-xhdpi/icon.jpg
python3 - <<'PY'
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
out = Path('app/src/main/res/drawable-xhdpi/banner.jpg')
icon = Image.open('app/src/main/res/drawable-xhdpi/icon.jpg').convert('RGB').resize((118,118), Image.Resampling.LANCZOS)
banner = Image.new('RGB',(320,180),(2,6,20)); banner.paste(icon,(8,31)); draw=ImageDraw.Draw(banner)
f1=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',25)
f2=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',9)
f3=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
draw.text((135,49),'VÓRTICETV',font=f1,fill=(242,244,248))
draw.text((136,88),'VIDEO • MUSIC • STREAMING',font=f2,fill=(20,220,245))
draw.line((136,112,304,112),fill=(112,55,255),width=2)
draw.text((136,123),'ANDROID TV',font=f3,fill=(185,190,210))
banner.save(out,quality=92,optimize=True)
PY
cd ..

python3 - <<'PY'
from pathlib import Path
for name, marker in [('vortise_v012.py','root.tab < 5'),('vortise_v012_channels.py','root.tab < 6')]:
    p=Path('branding-repo/patches')/name
    lines=p.read_text(encoding='utf-8').splitlines()
    lines=[x for x in lines if not ('replace(controls' in x and marker in x)]
    p.write_text('\n'.join(lines)+'\n',encoding='utf-8')
PY

for patch in \
  vortise_v012.py \
  vortise_v012_channels.py \
  vortise_music_free_v012.py \
  vortise_voice_v013.py \
  vortise_music_playback_v014.py \
  vortise_music_search_v014.py \
  vortise_channels_v014.py \
  vortise_voice_keyboard_v015.py \
  vortise_music_genre_albums_v016.py \
  vortise_music_stability_v016.py \
  vortise_music_no_restart_v016.py \
  vortise_channels_live_v016.py \
  vortise_movies_player_v017.py \
  vortise_video_smooth_v017.py \
  vortise_v0110_runtime_stability.py \
  vortise_channels_perf_v0111.py \
  vortise_popular_br_v0111.py
do
  python3 "$BRANDING/patches/$patch" "$ROOT"
done

python3 - <<'PY'
from pathlib import Path
controls=Path('src/app/src/main/kotlin/dev/limitedio/pipetv/ui/Controls.kt')
s=controls.read_text(encoding='utf-8')
old='root.tab < 5'
if old not in s: raise SystemExit('Controls navigation threshold not found')
controls.write_text(s.replace(old,'root.tab < 7',1),encoding='utf-8')

engine=Path('src/app/src/main/kotlin/dev/limitedio/pipetv/media/Engine.kt')
s=engine.read_text(encoding='utf-8')
if 'import dev.limitedio.pipetv.Bg' not in s:
    s=s.replace('import dev.limitedio.pipetv.App\n','import dev.limitedio.pipetv.App\nimport dev.limitedio.pipetv.Bg\n',1)
engine.write_text(s,encoding='utf-8')

grid=Path('src/app/src/main/kotlin/dev/limitedio/pipetv/ui/Grid.kt')
s=grid.read_text(encoding='utf-8')
if 'open class Grid(' not in s: s=s.replace('class Grid(','open class Grid(',1)
grid.write_text(s,encoding='utf-8')

nav=Path('src/app/src/main/kotlin/dev/limitedio/pipetv/ui/Nav.kt')
nav.write_text(nav.read_text(encoding='utf-8').replace('Txt.draw(c, "PipeTv",','Txt.draw(c, "VórticeTv",'),encoding='utf-8')
settings=Path('src/app/src/main/kotlin/dev/limitedio/pipetv/ui/Settings.kt')
settings.write_text(settings.read_text(encoding='utf-8').replace('"PipeTv ${Updater.current} · LimitedIO"','"VórticeTv ${Updater.current} · base PipeTV/LimitedIO"'),encoding='utf-8')
for lang in ['Pt.kt','En.kt']:
    p=Path('src/app/src/main/kotlin/dev/limitedio/pipetv/i18n/lang')/lang
    p.write_text(p.read_text(encoding='utf-8').replace('PipeTv','VórticeTv'),encoding='utf-8')
PY

chmod +x "$ROOT/gradlew"

echo 'VórticeTv v0.1.11 preparation complete'
