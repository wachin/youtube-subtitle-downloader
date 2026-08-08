# Architecture

The application follows a **model / service / worker / UI** separation so that
the GUI, the business logic and the yt-dlp backend can evolve independently.

```
src/youtube_subtitle_downloader/
├── app.py                 # QApplication bootstrap (org/app names, logging, i18n)
├── __main__.py            # python -m youtube_subtitle_downloader
├── cli.py                 # optional CLI reusing the services layer
├── models/                # dataclasses shared everywhere
│   ├── subtitle.py        # SubtitleTrack, SubtitleCue, SubtitleKind, languages
│   └── video.py           # VideoInfo, PlaylistInfo, PlaylistEntry, DownloadResult
├── services/              # no Qt widgets here; testable without a GUI
│   ├── ytdlp_service.py   # ALL yt-dlp interaction lives here (section 24)
│   ├── subtitle_service.py# parsing / conversion / de-duplication / TXT
│   ├── downloader.py      # shared per-track download logic (worker + CLI)
│   └── settings_service.py# QSettings + JSON history
├── workers/               # QThread subclasses with cooperative cancellation
│   ├── base_worker.py     # BaseWorker (cancel flag, signals)
│   ├── video_info_worker.py
│   ├── download_worker.py
│   └── preview_worker.py
├── ui/                    # PyQt6 widgets
│   ├── main_window.py
│   ├── subtitle_table_model.py
│   ├── preview_dialog.py
│   ├── settings_dialog.py
│   ├── about_dialog.py
│   ├── history_dialog.py
│   ├── playlist_dialog.py
│   └── download_complete_dialog.py
├── utils/                 # paths, filenames, logging
├── i18n/                  # QTranslator setup (English is the primary language)
└── resources/translations # .ts/.qm workflow notes (Spanish planned)
```

## Concurrency

Heavy yt-dlp operations never run on the GUI thread. Each operation runs in a
`QThread` subclass (`workers/`) that emits signals consumed by the main
window. Cancellation is cooperative: a flag is checked between units of work;
`QThread.terminate()` is never used.

## Subtitle pipeline

1. `YtDlpService.get_raw_info()` returns structured data from
   `YoutubeDL.extract_info()` (no shell parsing, no regex on CLI output).
2. `build_tracks()` turns `subtitles` / `automatic_captions` into
   `SubtitleTrack` objects.
3. `downloader.download_one()` fetches the raw data with `ydl.urlopen()`.
4. The real format is **detected from the content** (YouTube sometimes serves
   its new "pb3" JSON even when a track advertises SRT).
5. `subtitle_service` parses SRT / VTT / TTML / JSON3 into `SubtitleCue`s and
   serializes them into the requested output format.
6. `clean_incremental()` merges the overlapping incremental automatic
   captions, then `cues_to_txt()` produces the clean TXT file.

## Error handling

`friendly_error()` in `ytdlp_service` maps yt-dlp exceptions (private video,
removed video, age restriction, sign-in required, network errors, invalid
URL) to user friendly messages. Technical details go to the rotating log.

## Testing

Pure logic (parsing, de-duplication, filenames, track building, GUI smoke
tests offscreen) lives under `tests/`. No real YouTube calls are made during
unit tests — fixtures are used instead.
