# Debian packaging notes

This project is designed with future Debian packaging in mind (roadmap
section 41):

- No code is downloaded/executed at runtime.
- No `sudo`, no modification of system packages, no `/usr` writes.
- Dependencies are declared in `pyproject.toml` / `requirements.txt`.
- License is GPL-3.0-or-later (see `LICENSE`).

## Debian package names (Debian 13 / trixie)

```bash
sudo apt install python3 python3-pyqt6 python3-pip ffmpeg python3-yt-dlp
```

`python3-pyqt6` and `python3-yt-dlp` are available in Debian trixie
(verified `python3-pyqt6 6.9.0-2`).

## Desktop entry

The Freedesktop launcher template lives at
`packaging/youtube-subtitle-downloader.desktop` and must be installed to
`/usr/share/applications/` at build time:

```bash
install -Dm644 packaging/youtube-subtitle-downloader.desktop \
    /usr/share/applications/youtube-subtitle-downloader.desktop
```

It uses the ``youtube-subtitle-downloader`` entry point installed by the
package (``Terminal=false``), and the icon name matches the SVG installed in
the hicolor theme. Validate changes with ``desktop-file-validate``.

## Application icon

The bundled logo (`src/youtube_subtitle_downloader/resources/icons/
youtube-subtitle-downloader.svg`) should be installed into the Freedesktop
icon theme at build time:

```bash
install -Dm644 src/youtube_subtitle_downloader/resources/icons/youtube-subtitle-downloader.svg \
    /usr/share/icons/hicolor/scalable/apps/youtube-subtitle-downloader.svg
```

Run `gtk-update-icon-cache` on the hicolor theme afterwards (the Debian
`hicolor-icon-theme` package ships the theme indexes). The same icon name
(`youtube-subtitle-downloader`) is used by the application itself, so the
window and tray icons match the launcher icon.

## Placeholders

A real `debian/` control directory (`control`, `rules`, `copyright`, ...)
should be generated with `dh_make` + `debuild` or a tool such as
`cargo-deb`-like helpers for Python. This folder currently documents the
intended approach; the packaging metadata will be completed before a release.
