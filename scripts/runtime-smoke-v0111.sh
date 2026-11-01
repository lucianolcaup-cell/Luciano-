#!/bin/sh
set -u

PKG='br.com.luciano.noutubetv'
ACT='dev.limitedio.pipetv.MainActivity'
APK='out/VorticeTv-v0.1.11-TESTE.apk'
LOG='out/runtime-smoke-log.txt'

capture_and_fail() {
  reason="$1"
  echo "$reason" >&2
  adb logcat -d -v time > "$LOG" || true
  echo '===== VÓRTICETV FATAL EXCEPTION =====' >&2
  grep -A 80 'FATAL EXCEPTION' "$LOG" >&2 || true
  echo '===== VÓRTICETV PROCESS / CRASH LINES =====' >&2
  grep -E -A 25 -B 10 'AndroidRuntime|FATAL EXCEPTION|Process: br.com.luciano.noutubetv|Force finishing|has died|CRASH' "$LOG" >&2 || true
  exit 1
}

alive() {
  pid="$(adb shell pidof "$PKG" 2>/dev/null | tr -d '\r' || true)"
  [ -n "$pid" ]
}

start_app() {
  adb shell am force-stop "$PKG"
  adb shell am start -W -n "$PKG/$ACT" || exit 1
  sleep 10
  alive || capture_and_fail 'App morreu logo após abrir'
}

adb install -r "$APK" || exit 1
adb logcat -c

# Canais Abertos.
start_app
adb shell input keyevent 23
sleep 4
alive || capture_and_fail 'App morreu após o primeiro OK'
adb shell input keyevent 21
sleep 1
adb shell input keyevent 20
adb shell input keyevent 20
adb shell input keyevent 20
adb shell input keyevent 22
sleep 15
alive || capture_and_fail 'App morreu durante carregamento de Canais Abertos'

# Music: entra no gênero, abre o primeiro álbum e tenta iniciar a primeira faixa.
# Este fluxo valida que abrir álbum não herda contexto de Filme/vídeo.
start_app
adb shell input keyevent 21
sleep 1
adb shell input keyevent 20
adb shell input keyevent 20
adb shell input keyevent 22
sleep 10
alive || capture_and_fail 'App morreu ao entrar no Music'
adb shell input keyevent 20
adb shell input keyevent 20
adb shell input keyevent 23
sleep 12
alive || capture_and_fail 'App morreu ao buscar álbuns por gênero'
adb shell input keyevent 23
sleep 8
alive || capture_and_fail 'App morreu ao abrir um álbum do Music'
adb shell input keyevent 23
sleep 8
alive || capture_and_fail 'App morreu ao tocar faixa de um álbum'

# Filmes: navega até Popular e seleciona Filmes; não pode permanecer num estado fatal/travado.
start_app
adb shell input keyevent 21
sleep 1
adb shell input keyevent 20
adb shell input keyevent 20
adb shell input keyevent 20
adb shell input keyevent 20
adb shell input keyevent 22
sleep 8
alive || capture_and_fail 'App morreu ao entrar em Popular'
adb shell input keyevent 22
adb shell input keyevent 22
adb shell input keyevent 22
adb shell input keyevent 22
adb shell input keyevent 22
sleep 15
alive || capture_and_fail 'App morreu durante carregamento da aba Filmes'

# Reprodução de vídeo em Em alta — regressão do crash corrigido na v0.1.10.
start_app
adb shell input keyevent 23
sleep 4
alive || capture_and_fail 'App morreu após OK no ciclo de vídeo'
adb shell input keyevent 21
sleep 1
adb shell input keyevent 20
adb shell input keyevent 20
adb shell input keyevent 20
adb shell input keyevent 20
adb shell input keyevent 22
sleep 8
alive || capture_and_fail 'App morreu ao entrar em Em alta'
adb shell input keyevent 23
sleep 2
alive || capture_and_fail 'App morreu ao ativar a grade de Em alta'
adb shell input keyevent 23
sleep 8
alive || capture_and_fail 'App morreu ao selecionar um vídeo em Em alta'

adb logcat -d -v time > "$LOG" || true
if grep -A 24 'FATAL EXCEPTION' "$LOG" | grep -q "$PKG"; then
  capture_and_fail 'FATAL EXCEPTION detectada mesmo com processo ativo'
fi

echo 'RUNTIME_SMOKE_OK'
