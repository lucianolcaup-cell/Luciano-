#!/usr/bin/env python3
from pathlib import Path

path = Path("upstream/android/app/build.gradle")
text = path.read_text(encoding="utf-8")

old = "ext.abiCodes = [x86:1, x86_64:2, 'armeabi-v7a':3, 'arm64-v8a': 4]"
new = "ext.abiCodes = ['armeabi-v7a':3, 'arm64-v8a':4]"

if old not in text:
    raise SystemExit("Linha ext.abiCodes esperada não encontrada; build interrompida por segurança.")

path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("ABIs de TV configuradas: armeabi-v7a, arm64-v8a")
