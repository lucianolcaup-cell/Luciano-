#!/usr/bin/env python3
import re
from pathlib import Path

build_gradle = Path("upstream/android/app/build.gradle")
text = build_gradle.read_text(encoding="utf-8")

old = "ext.abiCodes = [x86:1, x86_64:2, 'armeabi-v7a':3, 'arm64-v8a': 4]"
new = "ext.abiCodes = ['armeabi-v7a':3, 'arm64-v8a':4]"

if old not in text:
    raise SystemExit("Linha ext.abiCodes esperada não encontrada; build interrompida por segurança.")

build_gradle.write_text(text.replace(old, new, 1), encoding="utf-8")

gradle_properties = Path("upstream/android/gradle.properties")
props = gradle_properties.read_text(encoding="utf-8")
pattern = re.compile(r"(?m)^reactNativeArchitectures=.*$")

if not pattern.search(props):
    raise SystemExit("reactNativeArchitectures não encontrado em gradle.properties; build interrompida por segurança.")

props = pattern.sub("reactNativeArchitectures=armeabi-v7a,arm64-v8a", props, count=1)
gradle_properties.write_text(props, encoding="utf-8")

print("ABIs de TV configuradas de ponta a ponta: armeabi-v7a, arm64-v8a")
