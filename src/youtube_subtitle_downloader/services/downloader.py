"""Shared logic to write subtitle files (used by the worker and the CLI)."""

from __future__ import annotations

from pathlib import Path

from ..models.subtitle import SubtitleTrack
from ..models.video import DownloadResult
from ..utils.filenames import subtitle_file_name
from ..utils.logging import get_logger
from .subtitle_service import (
    SUPPORTED_EXTENSIONS,
    SubtitleParseError,
    convert_cues,
    cues_to_txt,
    detect_format,
    parse_subtitles,
)
from .ytdlp_service import YtDlpService, decode_subtitle_bytes, friendly_error

log = get_logger()

#: Preferred source formats when the requested one is not available.
_SOURCE_PRIORITY = ("vtt", "srt", "ttml", "json3")


def pick_source_ext(track: SubtitleTrack, wanted: str) -> str | None:
    """Pick the extension to fetch from the network for a wanted output.

    * ``original`` -> first available format;
    * wanted format available -> itself;
    * otherwise the best parseable format we can convert from.
    """
    if wanted == "original":
        return track.formats[0] if track.formats else None
    if wanted in track.formats:
        return wanted
    for fmt in _SOURCE_PRIORITY:
        if fmt in track.formats:
            return fmt
    return track.formats[0] if track.formats else None


def download_one(
    service: YtDlpService,
    track: SubtitleTrack,
    *,
    video_title: str,
    video_id: str,
    fmt: str,
    template: str,
    outdir: str,
    txt_enabled: bool = False,
    txt_mode: str = "continuous",
) -> DownloadResult:
    """Fetch one subtitle track and write the requested files to ``outdir``.

    Returns a :class:`DownloadResult`; never raises for per-track failures.
    """
    result = DownloadResult(
        ok=False,
        video_title=video_title,
        language_code=track.base_code,
        language_name=track.display_name,
    )
    outdir_path = Path(outdir)
    fallback_ext = pick_source_ext(track, fmt)
    if fallback_ext is None:
        result.error = "No downloadable formats for this track."
        return result

    try:
        data = service.fetch_subtitle_content(track)

        if fmt == "original":
            ext = detect_format(decode_subtitle_bytes(data)) or fallback_ext
            name = subtitle_file_name(
                template,
                title=video_title,
                video_id=video_id,
                language=track.base_code,
                ext=ext,
            )
            path = outdir_path / name
            path.write_bytes(data)
            result.ok = True
            result.path = str(path)
            return result

        text = decode_subtitle_bytes(data)
        # YouTube may serve its "pb3" JSON even when the track advertises srt;
        # detect the real format from the content before parsing.
        source_ext = detect_format(text) or fallback_ext
        if source_ext not in SUPPORTED_EXTENSIONS:
            result.error = f"Unsupported source format: {source_ext}"
            return result

        cues = parse_subtitles(text, source_ext)
        content = convert_cues(cues, fmt, language=track.base_code)
        name = subtitle_file_name(
            template,
            title=video_title,
            video_id=video_id,
            language=track.base_code,
            ext=fmt,
        )
        path = outdir_path / name
        path.write_text(content, encoding="utf-8")
        result.ok = True
        result.path = str(path)

        if txt_enabled:
            txt = cues_to_txt(cues, txt_mode)
            txt_name = subtitle_file_name(
                template,
                title=video_title,
                video_id=video_id,
                language=track.base_code,
                ext="txt",
            )
            (outdir_path / txt_name).write_text(txt, encoding="utf-8")
        return result
    except SubtitleParseError as exc:
        result.error = str(exc)
    except Exception as exc:  # noqa: BLE001 - report friendly message
        result.error = friendly_error(exc)
        log.exception("Failed to download subtitle %s", track.language_code)
    return result
