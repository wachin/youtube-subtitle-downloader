"""Optional command line interface.

The GUI remains the priority (roadmap section 53); this small CLI reuses the
same services layer so behaviour stays consistent.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .models.subtitle import SubtitleKind
from .services.downloader import download_one
from .services.settings_service import SettingsService
from .services.ytdlp_service import BROWSERS, YtDlpService, friendly_error
from .utils.filenames import DEFAULT_TEMPLATE
from .utils.logging import setup_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="youtube-subtitle-downloader-cli",
        description="Download YouTube subtitles using yt-dlp (GUI is the priority).",
    )
    parser.add_argument("url", help="YouTube URL to process")
    parser.add_argument(
        "-l",
        "--lang",
        action="append",
        default=[],
        help="Language code(s) to download (repeatable). Defaults to the original language.",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["srt", "vtt", "ttml", "json3", "original"],
        default="srt",
        help="Output subtitle format (default: srt).",
    )
    parser.add_argument("-o", "--output", default=None, help="Destination folder.")
    parser.add_argument(
        "--txt", action="store_true", help="Also create a clean TXT file."
    )
    parser.add_argument(
        "--txt-mode",
        choices=["continuous", "paragraphs", "lines"],
        default="continuous",
        help="TXT layout mode (default: continuous).",
    )
    parser.add_argument(
        "--cookies-browser",
        choices=list(BROWSERS),
        default=None,
        help="Read cookies from a browser (yt-dlp --cookies-from-browser).",
    )
    parser.add_argument("--cookies-file", default=None, help="Path to a cookies.txt file.")
    parser.add_argument("--template", default=DEFAULT_TEMPLATE, help="File name template.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging()

    settings = SettingsService()
    if args.cookies_browser:
        settings.set_cookies_browser(args.cookies_browser)
    if args.cookies_file:
        settings.set_cookies_file(args.cookies_file)

    service = YtDlpService(settings)
    if not service.is_available():
        print("yt-dlp is not available.", file=sys.stderr)
        return 2

    try:
        raw = service.get_raw_info(args.url)
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(friendly_error(exc, args.url), file=sys.stderr)
        return 1

    info = service.to_video_info(raw, args.url)
    if not info.tracks:
        print("No subtitles found for this video.", file=sys.stderr)
        return 1

    tracks = _select_tracks(info, args.lang)
    if not tracks:
        print("None of the requested languages are available.", file=sys.stderr)
        return 1

    outdir = Path(args.output) if args.output else Path(settings.output_dir())
    try:
        outdir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"Cannot create destination folder: {exc}", file=sys.stderr)
        return 1

    downloaded = 0
    for track in tracks:
        result = download_one(
            service,
            track,
            video_title=info.title,
            video_id=info.video_id,
            fmt=args.format,
            template=args.template,
            outdir=str(outdir),
            txt_enabled=args.txt,
            txt_mode=args.txt_mode,
        )
        if result.ok:
            downloaded += 1
            print(f"Saved: {result.path}")
        else:
            print(f"Failed ({track.language_code}): {result.error}", file=sys.stderr)

    print(f"{downloaded} subtitle(s) downloaded to {outdir}.")
    return 0 if downloaded else 1


def _select_tracks(info, languages: list[str]) -> list:
    if languages:
        tracks = []
        for code in languages:
            track = info.find_track(code, SubtitleKind.MANUAL) or info.find_track(
                code, SubtitleKind.AUTOMATIC
            )
            if track:
                tracks.append(track)
        return tracks
    original = next((t for t in info.tracks if t.is_original), None)
    if original:
        return [original]
    english = info.find_track("en", SubtitleKind.MANUAL) or info.find_track(
        "en", SubtitleKind.AUTOMATIC
    )
    if english:
        return [english]
    return info.tracks[:1]


if __name__ == "__main__":
    sys.exit(main())
