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

## Placeholders

A real `debian/` control directory (`control`, `rules`, `copyright`, ...)
should be generated with `dh_make` + `debuild` or a tool such as
`cargo-deb`-like helpers for Python. This folder currently documents the
intended approach; the packaging metadata will be completed before a release.
