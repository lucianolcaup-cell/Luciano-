# NouTube TV — Android TV compatibility build

Private sideload build prepared from the open-source **NouTube 0.7.4** project.

## Base

- Upstream: https://github.com/nonbili/NouTube
- Pinned commit: `a2eeb7be1f3261a4bc717e009e49300372545d95`
- Upstream license: GNU AGPL v3

NouTube already provides YouTube + YouTube Music, ad blocking, background playback and local library/history features. This branch does not replace the upstream project; it applies a small Android TV compatibility layer during CI.

## Changes applied by this branch

- Adds Android TV / Google TV launcher category (`LEANBACK_LAUNCHER`).
- Declares touchscreen as optional and Leanback support.
- Forces the main activity to landscape and allows resizing.
- Renames the launcher label to **NouTube TV**.
- Adds D-pad focus navigation for the wrapped YouTube / YouTube Music web interfaces.
- Adds a strong focus indicator for TV viewing distance.
- Produces an installable release APK signed with the standard debug key for private sideloading.
- Preserves the original NouTube package/source and rebuilds from the pinned upstream commit.

## Build output

GitHub Actions uploads an artifact named `NouTube-TV-v0.1-APK` containing the generated APKs and SHA-256 checksums.

For a typical Android TV, prefer `arm64-v8a`. If the TV runs a 32-bit Android userspace, use `armeabi-v7a`.

## Important

This is an unofficial compatibility build. YouTube/Google can change their web interfaces at any time, so ad blocking or remote navigation may require future maintenance.

The corresponding source is the pinned upstream source plus `scripts/patch_noutube_tv.py` in this branch, as required by the upstream AGPL license.
