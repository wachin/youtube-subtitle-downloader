# Debian packaging

This project ships a working `.deb` build script that follows Debian policy:

- No code is downloaded/executed at runtime.
- No `sudo`, no modification of system packages, no `/usr` writes during the
  build (the staging tree is assembled under a temp directory).
- Dependencies are declared in `DEBIAN/control` (generated from
  `packaging/debian/control`).
- License is GPL-3.0-or-later (see `LICENSE`); the package's `copyright`
  file references `/usr/share/common-licenses/GPL-3` as Debian policy
  requires.

## Building the package

```bash
packaging/build-deb.sh
```

This writes `dist/youtube-subtitle-downloader_<version>_all.deb` (the version
comes from `src/youtube_subtitle_downloader/__init__.py`; override with
`VERSION=...`). The script uses a deterministic staging layout and
`dpkg-deb --build --root-owner-group`.

### What the package contains

- `/usr/lib/python3/dist-packages/youtube_subtitle_downloader/` — the Python
  package (including `resources/translations/*.qm` and the bundled logo).
- `/usr/bin/youtube-subtitle-downloader` and
  `/usr/bin/youtube-subtitle-downloader-cli` — thin wrappers that run
  `python3 -m youtube_subtitle_downloader[.cli]`.
- `/usr/share/applications/youtube-subtitle-downloader.desktop` — the
  launcher (from `packaging/youtube-subtitle-downloader.desktop`).
- `/usr/share/icons/hicolor/scalable/apps/youtube-subtitle-downloader.svg` —
  the application logo.
- `/usr/share/doc/youtube-subtitle-downloader/` — `copyright` and gzipped
  `changelog`.
- `DEBIAN/postinst` + `DEBIAN/postrm` refresh the icon theme and the desktop
  database after install/remove.

### Dependencies (Debian 13 / trixie, also fine on MX)

`python3` (>= 3.9), `python3-pyqt6`, `python3-pyqt6.qtsvg` (required to load
the SVG logo), `yt-dlp` (or `python3-yt-dlp` on pure Debian), plus
`ffmpeg` as a recommendation.

```bash
sudo apt install python3 python3-pyqt6 python3-pyqt6.qtsvg yt-dlp ffmpeg
```

## Installing / removing

```bash
sudo dpkg -i dist/youtube-subtitle-downloader_0.1.0_all.deb
# or: sudo apt install ./dist/youtube-subtitle-downloader_0.1.0_all.deb
sudo dpkg -r youtube-subtitle-downloader
```

## Validating

```bash
lintian dist/youtube-subtitle-downloader_0.1.0_all.deb
dpkg-deb --info dist/youtube-subtitle-downloader_0.1.0_all.deb
dpkg-deb --contents dist/youtube-subtitle-downloader_0.1.0_all.deb
```

The remaining lintian warnings (`no-manual-page`,
`initial-upload-closes-no-bugs`) are informational for this first release.

## Note on dh_make / debuild

A full source-package flow (`dh_make` + `debuild`) is possible, but the
staged `dpkg-deb` approach above produces the same installable artifact with
much less machinery and no build-time network access. The `debian/` files in
this directory are kept as the single source of truth for control metadata,
scripts and changelog.
