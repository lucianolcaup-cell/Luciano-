#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-src}"
BRANDING="${2:-branding-repo}"

bash "$BRANDING/scripts/prepare-v0111.sh" "$ROOT" "$BRANDING"
python3 "$BRANDING/patches/vortise_release_polish_v0112.py" "$ROOT"

echo 'VórticeTv v0.1.12 FINAL preparation complete'
