# YouTube Subtitle Downloader

A complete desktop application written in **Python 3 + PyQt6** that lets you
download subtitles from YouTube using [**yt-dlp**](https://github.com/yt-dlp/yt-dlp),
aimed mainly at Linux (Debian, Ubuntu, MX Linux and derivatives).

You do not need to know the command line: paste a video URL, inspect the
available subtitles, select one or more languages and download them.

> The primary language of the application is **English**. Spanish translation
> (via Qt Linguist) is planned as the first additional language.

<!-- Add a screenshot of the main window here once available: ![Screenshot](docs/screenshot.png) -->

## Features

- Fetch video info and thumbnails without freezing the GUI (background threads).
- List **manual** and **automatic** subtitles in separate tabs with a search box.
- Distinguish the original language (`es-orig`, `en-orig`, ...) with a badge.
- Select one, several or all languages; filters for manual/automatic only.
- Download in **SRT**, **VTT**, **TTML**, **JSON3** or the **original** format.
- Create a **clean TXT file** that removes the incremental repetitions of
  YouTube automatic captions (three layouts: continuous, paragraphs, one line
  per subtitle).
- Download **multiple languages in one operation** with per-track progress.
- Subtitle **preview** window with search, copy and save.
- Optional **history** of processed videos (can be disabled).
- Optional **cookies** support (from browser or `cookies.txt`) for restricted videos.
- Drag & drop URLs, paste from clipboard, playlist detection (MVP).
- System theme aware, keyboard shortcuts, tooltips, optional CLI.
- No telemetry; everything runs locally.

## Requirements

- Python 3.9+ (tested on 3.13)
- PyQt6
- yt-dlp
- FFmpeg (optional; only used when the chosen format needs conversion)

## Installation

### From the repository (development)

```bash
sudo apt install python3 python3-pyqt6 python3-pip ffmpeg
python3 -m pip install --user yt-dlp   # or install python3-yt-dlp from Debian
```

Create a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Run the application:

```bash
python3 run.py
```

(also works without installing: `PYTHONPATH=src python3 -m youtube_subtitle_downloader`).

After `pip install -e .` you can also use the installed command:

```bash
youtube-subtitle-downloader
```

## Usage

1. Paste a YouTube URL (or drag & drop it onto the window).
2. Press **Analyze** (or Enter).
3. Check the languages you want — the tabs filter between *All*,
   *Subtitles* (manual) and *Automatic*.
4. Choose the format, the TXT option, the destination folder and the file
   name template.
5. Press **Download selected**.

Shortcuts: `Ctrl+L` URL · `Ctrl+F` search · `Ctrl+D` download · `Ctrl+,`
settings · `Ctrl+Q` quit.

### Command line

A small CLI is included (the GUI remains the priority):

```bash
youtube-subtitle-downloader-cli URL --lang es-orig --format srt --txt
```

## Formats

- **SRT** / **VTT** / **TTML** / **JSON3**: generated from the best source
  format available (the app converts between formats when needed).
- **Original**: the subtitle data exactly as provided by yt-dlp.

## Automatic captions

Many videos have no manual subtitles while still providing automatic
captions (yt-dlp may even report `has no subtitles` in that case). This
application always uses the structured `automatic_captions` data, so those
tracks are shown and downloadable normally.

## Clean text

The *clean TXT* option produces only what is spoken: no sequence numbers, no
timestamps, no tags, no metadata. The incremental repetitions YouTube
automatic captions introduce are removed conservatively (overlapping cues are
merged only when they overlap in time), so legitimate repetitions are kept.

## Privacy

- URLs are sent only to the servers required by YouTube/yt-dlp to fetch content.
- Files are saved locally; there is **no telemetry**.
- The optional history (dates, titles, URLs) is stored locally in the user
  data folder and can be disabled in *Settings → Privacy*.

## Cookies

Some videos require authentication. You can enable cookies via
*Tools → Settings → YouTube*:

- **Cookies from browser** — uses yt-dlp's `--cookies-from-browser`.
- **Cookies file** — a Netscape-format `cookies.txt`.

Cookie contents are never read, stored or logged by this application.

## Troubleshooting

- **“yt-dlp was not found”** — install yt-dlp with your package manager or
  follow the [official instructions](https://github.com/yt-dlp/yt-dlp#installation).
- **Restricted videos** — enable cookies (see above).
- **Missing formats** — some tracks only offer a subset of formats; the app
  converts from the best available source when possible.
- Technical details are written to the rotating log under the user data
  folder (`~/.local/share/youtube-subtitle-downloader/logs/app.log`).

## Development

```bash
pip install -e ".[dev]"
python -m pytest
```

The project uses `ruff`, `black` and `mypy` for style and typing (development
dependencies only — end users do not need them).

Architecture notes are in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Translations

English is the primary language. Spanish is the first planned translation,
using Qt Linguist (`pylupdate6` → `.ts` → `lrelease` → `.qm`). See
[`src/youtube_subtitle_downloader/resources/translations/README.md`](src/youtube_subtitle_downloader/resources/translations/README.md).

## Packaging

Debian packaging notes live in [`packaging/debian/README.md`](packaging/debian/README.md).
The project is designed to follow Debian policy (no runtime downloads, no
system modification, declared dependencies).

## License

**GPL-3.0-or-later** — see [LICENSE](LICENSE).

This application uses **yt-dlp** to communicate with YouTube. It is not
affiliated with YouTube or Google.
