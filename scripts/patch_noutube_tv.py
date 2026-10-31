#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ANDROID_NS = "http://schemas.android.com/apk/res/android"
ET.register_namespace("android", ANDROID_NS)
A = f"{{{ANDROID_NS}}}"

TV_NAV = r'''

function installTvNavigation() {
  const root = window as Window & typeof globalThis & { __noutubeTvNavigationInit?: boolean }
  if (root.__noutubeTvNavigationInit) return
  root.__noutubeTvNavigationInit = true

  const style = document.createElement('style')
  style.id = '_noutube_tv_focus_style'
  style.textContent = `
    :focus-visible {
      outline: 4px solid #ffffff !important;
      outline-offset: 3px !important;
      border-radius: 6px !important;
    }
  `
  ;(document.head || document.documentElement).appendChild(style)

  const selector = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'textarea:not([disabled])',
    'select:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
    '[role="button"]',
    '[role="link"]',
    '[role="tab"]',
  ].join(',')

  const visible = (el: HTMLElement) => {
    const rect = el.getBoundingClientRect()
    const style = window.getComputedStyle(el)
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none'
  }

  const focusables = () => Array.from(document.querySelectorAll<HTMLElement>(selector)).filter(visible)

  const center = (el: HTMLElement) => {
    const r = el.getBoundingClientRect()
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 }
  }

  const focusNearest = (key: string) => {
    const items = focusables()
    if (!items.length) return false

    const active = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const activeInList = active ? items.includes(active) : false
    const origin = activeInList && active ? center(active) : { x: window.innerWidth / 2, y: window.innerHeight / 2 }

    let best: HTMLElement | null = null
    let bestScore = Number.POSITIVE_INFINITY

    for (const item of items) {
      if (item === active) continue
      const p = center(item)
      const dx = p.x - origin.x
      const dy = p.y - origin.y

      let primary = 0
      let secondary = 0
      if (key === 'ArrowRight') {
        if (dx <= 8) continue
        primary = dx
        secondary = Math.abs(dy)
      } else if (key === 'ArrowLeft') {
        if (dx >= -8) continue
        primary = -dx
        secondary = Math.abs(dy)
      } else if (key === 'ArrowDown') {
        if (dy <= 8) continue
        primary = dy
        secondary = Math.abs(dx)
      } else if (key === 'ArrowUp') {
        if (dy >= -8) continue
        primary = -dy
        secondary = Math.abs(dx)
      }

      const score = primary * 10 + secondary
      if (score < bestScore) {
        bestScore = score
        best = item
      }
    }

    if (!best && !activeInList) {
      best = items
        .map((item) => ({ item, p: center(item) }))
        .sort((a, b) => {
          const da = Math.hypot(a.p.x - origin.x, a.p.y - origin.y)
          const db = Math.hypot(b.p.x - origin.x, b.p.y - origin.y)
          return da - db
        })[0]?.item ?? null
    }

    if (!best) return false
    best.focus({ preventScroll: true })
    best.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' })
    return true
  }

  document.addEventListener(
    'keydown',
    (event) => {
      const key = event.key
      if (key === 'Enter') {
        const active = document.activeElement
        if (active instanceof HTMLElement && active !== document.body && !active.matches('input, textarea')) {
          active.click()
          event.preventDefault()
        }
        return
      }

      if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(key)) return

      const active = document.activeElement
      if (active instanceof HTMLElement && active.matches('input, textarea, select')) return

      if (focusNearest(key)) event.preventDefault()
    },
    true,
  )
}
'''


def patch_source(root: Path) -> None:
    main_ts = root / "content" / "main.ts"
    text = main_ts.read_text(encoding="utf-8")

    if "installTvNavigation()" not in text:
        marker = "  installWatchNavigation()\n"
        if marker not in text:
            raise RuntimeError("Não foi possível localizar installWatchNavigation() em content/main.ts")
        text = text.replace(marker, marker + "  installTvNavigation()\n", 1)

    if "function installTvNavigation() {" not in text:
        text += TV_NAV

    main_ts.write_text(text, encoding="utf-8")


def add_feature(manifest: ET.Element, name: str, required: str = "false") -> None:
    for node in manifest.findall("uses-feature"):
        if node.get(A + "name") == name:
            node.set(A + "required", required)
            return
    node = ET.Element("uses-feature")
    node.set(A + "name", name)
    node.set(A + "required", required)
    app = manifest.find("application")
    children = list(manifest)
    if app is None:
        manifest.append(node)
    else:
        manifest.insert(children.index(app), node)


def patch_manifest(root: Path) -> None:
    manifest_path = root / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
    if not manifest_path.exists():
        raise RuntimeError(f"Manifest não encontrado: {manifest_path}")

    tree = ET.parse(manifest_path)
    manifest = tree.getroot()

    add_feature(manifest, "android.software.leanback", "false")
    add_feature(manifest, "android.hardware.touchscreen", "false")

    app = manifest.find("application")
    if app is None:
        raise RuntimeError("Elemento <application> não encontrado")
    app.set(A + "banner", "@mipmap/ic_launcher")

    main_activity = None
    main_filter = None
    for activity in list(app.findall("activity")) + list(app.findall("activity-alias")):
        for intent_filter in activity.findall("intent-filter"):
            has_main = any(action.get(A + "name") == "android.intent.action.MAIN" for action in intent_filter.findall("action"))
            if has_main:
                main_activity = activity
                main_filter = intent_filter
                break
        if main_activity is not None:
            break

    if main_activity is None or main_filter is None:
        raise RuntimeError("Activity principal com ACTION_MAIN não encontrada")

    categories = {c.get(A + "name") for c in main_filter.findall("category")}
    if "android.intent.category.LEANBACK_LAUNCHER" not in categories:
        cat = ET.SubElement(main_filter, "category")
        cat.set(A + "name", "android.intent.category.LEANBACK_LAUNCHER")

    if main_activity.tag == "activity":
        main_activity.set(A + "screenOrientation", "landscape")
        main_activity.set(A + "resizeableActivity", "true")

    tree.write(manifest_path, encoding="utf-8", xml_declaration=True)


def patch_strings(root: Path) -> None:
    strings_path = root / "android" / "app" / "src" / "main" / "res" / "values" / "strings.xml"
    if not strings_path.exists():
        raise RuntimeError(f"strings.xml não encontrado: {strings_path}")

    tree = ET.parse(strings_path)
    resources = tree.getroot()
    found = False
    for item in resources.findall("string"):
        if item.get("name") == "app_name":
            item.text = "NouTube TV"
            found = True
            break
    if not found:
        item = ET.SubElement(resources, "string")
        item.set("name", "app_name")
        item.text = "NouTube TV"
    tree.write(strings_path, encoding="utf-8", xml_declaration=True)


def patch_gradle(root: Path) -> None:
    gradle_path = root / "android" / "app" / "build.gradle"
    text = gradle_path.read_text(encoding="utf-8")

    if "signingConfig signingConfigs.debug // NouTube TV private sideload build" not in text:
        pattern = re.compile(r"(?m)^(\s*)release\s*\{\s*$")
        match = pattern.search(text)
        if not match:
            raise RuntimeError("Bloco release não encontrado em android/app/build.gradle")
        indent = match.group(1) + "    "
        insert = match.group(0) + "\n" + indent + "signingConfig signingConfigs.debug // NouTube TV private sideload build"
        text = text[: match.start()] + insert + text[match.end() :]

    gradle_path.write_text(text, encoding="utf-8")


def patch_android(root: Path) -> None:
    patch_manifest(root)
    patch_strings(root)
    patch_gradle(root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--phase", choices=["source", "android", "all"], default="all")
    args = parser.parse_args()

    root = args.root.resolve()
    if args.phase in ("source", "all"):
        patch_source(root)
    if args.phase in ("android", "all"):
        patch_android(root)


if __name__ == "__main__":
    main()
