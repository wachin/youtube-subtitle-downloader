"""Subtitle parsing, conversion, de-duplication and plain-text generation.

This module is intentionally independent from Qt and yt-dlp so that it can be
unit-tested and improved separately (roadmap sections 9, 10, 48 and 49).
"""

from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET

from ..models.subtitle import SubtitleCue

SUPPORTED_EXTENSIONS = ("srt", "vtt", "ttml", "json3")
#: Preferred source formats used when the requested output format is not
#: available for a given track and a conversion is needed.
_SOURCE_PRIORITY = ("vtt", "srt", "ttml", "json3")

_TIMESTAMP = re.compile(
    r"(\d{1,3}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*"
    r"(\d{1,3}):(\d{2}):(\d{2})[,.](\d{1,3})"
)


class SubtitleParseError(Exception):
    """Raised when subtitle content cannot be parsed."""


def _to_seconds(h: int, m: int, s: int, ms: int) -> float:
    return h * 3600 + m * 60 + s + ms / 1000.0


def _strip_tags(text: str) -> str:
    """Remove HTML/VTT tags and unescape entities."""
    return html.unescape(re.sub(r"<[^>]+>", "", text))


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# --------------------------------------------------------------------------
# Parsers
# --------------------------------------------------------------------------


def parse_srt(text: str) -> list[SubtitleCue]:
    """Parse SRT content into cues."""
    cues: list[SubtitleCue] = []
    for block in re.split(r"\r?\n\r?\n", text.replace("\ufeff", "")):
        lines = [line for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        ts_line = next((line for line in lines if "-->" in line), None)
        if ts_line is None:
            continue
        match = _TIMESTAMP.match(ts_line.strip())
        if not match:
            continue
        start = _to_seconds(*[int(match.group(i)) for i in (1, 2, 3, 4)])
        end = _to_seconds(*[int(match.group(i)) for i in (5, 6, 7, 8)])
        index = lines.index(ts_line)
        body = [_strip_tags(line) for line in lines[index + 1 :] if line.strip()]
        if body:
            cues.append(SubtitleCue(start, end, body))
    return cues


def parse_vtt(text: str) -> list[SubtitleCue]:
    """Parse WebVTT content into cues."""
    text = text.replace("\ufeff", "")
    lines = text.splitlines()
    cues: list[SubtitleCue] = []
    index = 0
    total = len(lines)
    while index < total:
        line = lines[index].strip()
        if not line or "WEBVTT" in line or line.startswith(("STYLE", "REGION")):
            index += 1
            continue
        if line.startswith("NOTE"):
            # Comment block: skip until a blank line.
            while index < total and lines[index].strip():
                index += 1
            continue
        if "-->" in line:
            match = _TIMESTAMP.match(line)
            if match:
                start = _to_seconds(*[int(match.group(i)) for i in (1, 2, 3, 4)])
                end = _to_seconds(*[int(match.group(i)) for i in (5, 6, 7, 8)])
                index += 1
                body: list[str] = []
                while (
                    index < total
                    and lines[index].strip()
                    and not lines[index].strip().startswith("NOTE")
                ):
                    body.append(_strip_tags(lines[index].strip()))
                    index += 1
                if body:
                    cues.append(SubtitleCue(start, end, body))
                continue
        index += 1
    return cues


def _parse_clock(value: str) -> float | None:
    """Parse a TTML clock value into seconds (or None)."""
    value = value.strip()
    match = re.match(r"(\d+):(\d{2}):(\d{2})[.,](\d{1,3})", value)
    if match:
        return _to_seconds(*[int(match.group(i)) for i in (1, 2, 3, 4)])
    match = re.match(r"(\d+):(\d{2})[.,](\d{1,3})", value)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2)) + int(match.group(3)) / 1000.0
    match = re.match(r"(\d+(?:\.\d+)?)\s*(h|m|s|ms)", value)
    if match:
        number = float(match.group(1))
        unit = match.group(2)
        multipliers = {"h": 3600, "m": 60, "s": 1, "ms": 0.001}
        return number * multipliers[unit]
    try:
        return float(value)
    except ValueError:
        return None


def parse_ttml(text: str) -> list[SubtitleCue]:
    """Parse TTML (XML) content into cues."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise SubtitleParseError(f"Invalid TTML/XML content: {exc}") from exc

    cues: list[SubtitleCue] = []
    for element in root.iter():
        if element.tag.split("}")[-1] != "p":
            continue
        begin = _parse_clock(element.get("begin", ""))
        end = _parse_clock(element.get("end", ""))
        if begin is None or end is None:
            continue
        body = _clean_text("".join(element.itertext()))
        if body:
            cues.append(SubtitleCue(begin, end, [body]))
    return cues


def parse_json3(text: str) -> list[SubtitleCue]:
    """Parse JSON3 content into cues."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SubtitleParseError(f"Invalid JSON3 content: {exc}") from exc

    events = data.get("events") or []
    cues: list[SubtitleCue] = []
    for position, event in enumerate(events):
        start_ms = int(event.get("tStartMs") or 0)
        duration_ms = int(event.get("dDurationMs") or 0)
        if duration_ms <= 0 and position + 1 < len(events):
            next_start = int(events[position + 1].get("tStartMs") or start_ms)
            duration_ms = max(0, next_start - start_ms)
        text = _clean_text(
            "".join(segment.get("utf8", "") for segment in event.get("segs") or [])
        )
        if text:
            cues.append(
                SubtitleCue(
                    start_ms / 1000.0,
                    (start_ms + duration_ms) / 1000.0,
                    [text],
                )
            )
    return cues


_PARSERS = {
    "srt": parse_srt,
    "vtt": parse_vtt,
    "ttml": parse_ttml,
    "json3": parse_json3,
}


def detect_format(text: str) -> str | None:
    """Detect the subtitle format from its content, or None when unsure.

    YouTube sometimes serves its new ASR "pb3" wire format (a JSON document
    with an ``events`` list) regardless of the extension advertised by yt-dlp,
    so detecting from the content is more reliable than trusting the URL.
    """
    stripped = text.lstrip("\ufeff \t\r\n")
    if stripped.startswith("WEBVTT"):
        return "vtt"
    if stripped.startswith("<?xml") or stripped.startswith("<tt"):
        return "ttml"
    if stripped.startswith("{"):
        return "json3"
    if "-->" in stripped[:2000] or re.match(
        r"^\d{1,3}\s*\n?\d{1,3}:\d{2}:\d{2}[,.]\d{1,3}", stripped
    ):
        return "srt"
    return None


def parse_subtitles(content: str, source_ext: str) -> list[SubtitleCue]:
    """Parse subtitle content given its source extension."""
    ext = (source_ext or "").lower()
    parser = _PARSERS.get(ext)
    if parser is None:
        raise SubtitleParseError(f"Unsupported source format: {source_ext!r}")
    return parser(content)


# --------------------------------------------------------------------------
# Serializers
# --------------------------------------------------------------------------


def _format_ts(seconds: float, separator: str = ",") -> str:
    total = max(0, int(round(seconds * 1000)))
    hours, rem = divmod(total, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def cues_to_srt(cues: list[SubtitleCue]) -> str:
    """Serialize cues to SRT."""
    blocks: list[str] = []
    for number, cue in enumerate(cues, start=1):
        blocks.append(
            f"{number}\n{_format_ts(cue.start)} --> {_format_ts(cue.end)}\n"
            + "\n".join(cue.lines)
        )
    return "\n\n".join(blocks) + "\n"


def cues_to_vtt(cues: list[SubtitleCue]) -> str:
    """Serialize cues to WebVTT."""
    lines = ["WEBVTT", ""]
    for cue in cues:
        lines.append(f"{_format_ts(cue.start, '.')} --> {_format_ts(cue.end, '.')}")
        lines.extend(cue.lines)
        lines.append("")
    return "\n".join(lines)


def cues_to_ttml(cues: list[SubtitleCue], language: str = "und") -> str:
    """Serialize cues to TTML (a minimal but valid document)."""
    paragraphs = "\n".join(
        f'<p begin="{_format_ts(cue.start, ".")}" end="{_format_ts(cue.end, ".")}">'
        f'{"<br/>".join(html.escape(line) for line in cue.lines)}</p>'
        for cue in cues
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<tt xmlns="http://www.w3.org/ns/ttml" '
        'xmlns:tts="http://www.w3.org/ns/ttml#styling" '
        f'xml:lang="{html.escape(language)}">\n'
        "<body><div>\n"
        f"{paragraphs}\n"
        "</div></body>\n</tt>\n"
    )


def cues_to_json3(cues: list[SubtitleCue]) -> str:
    """Serialize cues to JSON3."""
    events = [
        {
            "tStartMs": int(cue.start * 1000),
            "dDurationMs": max(0, int((cue.end - cue.start) * 1000)),
            "segs": [{"utf8": f"{line}\n"} for line in cue.lines],
        }
        for cue in cues
    ]
    return json.dumps({"events": events}, ensure_ascii=False, indent=2) + "\n"


_SERIALIZERS = {
    "srt": cues_to_srt,
    "vtt": cues_to_vtt,
    "ttml": cues_to_ttml,
    "json3": cues_to_json3,
}


def convert_cues(cues: list[SubtitleCue], output_ext: str, language: str = "und") -> str:
    """Serialize cues to the requested output format."""
    serializer = _SERIALIZERS.get((output_ext or "").lower())
    if serializer is None:
        raise ValueError(f"Unsupported output format: {output_ext!r}")
    if output_ext == "ttml":
        return serializer(cues, language=language)
    return serializer(cues)


# --------------------------------------------------------------------------
# Incremental caption de-duplication and plain text
# --------------------------------------------------------------------------


def _words(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def _overlap_length(previous: list[str], current: list[str]) -> int:
    """Longest k such that ``previous[-k:] == current[:k]``."""
    best = 0
    limit = min(len(previous), len(current))
    for k in range(1, limit + 1):
        if previous[-k:] == current[:k]:
            best = k
    return best


def clean_incremental(
    cues: list[SubtitleCue],
    *,
    max_gap: float = 1.2,
    min_overlap: int = 2,
) -> list[SubtitleCue]:
    """Merge the incremental repetitions of YouTube automatic captions.

    YouTube auto captions are often emitted as growing phrases::

        Hola
        Hola amigos
        Hola amigos bienvenidos
        amigos bienvenidos al canal

    which should become::

        Hola amigos bienvenidos al canal

    The merge is conservative: it only strips an overlapping prefix when the
    cues overlap in time (``max_gap``) and the overlap is meaningful
    (``min_overlap`` words, or a short incremental addition), so legitimate
    repetitions of the speaker are not removed.
    """
    merged: list[SubtitleCue] = []
    for cue in cues:
        words = _words(cue.text)
        if not words:
            continue
        if merged:
            previous = merged[-1]
            gap = cue.start - previous.end
            overlap = _overlap_length(_words(previous.text), words)
            incremental = overlap >= min_overlap or (
                overlap >= 1 and len(words) <= len(_words(previous.text)) + 1
            )
            if overlap and incremental and gap <= max_gap:
                remaining = words[overlap:]
                if remaining:
                    merged[-1] = SubtitleCue(
                        previous.start,
                        max(previous.end, cue.end),
                        previous.lines + [" ".join(remaining)],
                    )
                continue  # merged (or fully absorbed) into the previous cue
        merged.append(cue)
    return merged


def cues_to_txt(cues: list[SubtitleCue], mode: str = "continuous") -> str:
    """Generate clean plain text from cues.

    ``mode`` is one of ``continuous``, ``paragraphs`` or ``lines``.
    Incremental repetitions are removed first.
    """
    cleaned = clean_incremental(cues)
    if mode == "lines":
        return "\n".join(cue.text for cue in cleaned) + "\n"
    if mode == "paragraphs":
        paragraphs: list[str] = []
        current: list[str] = []
        previous_end: float | None = None
        for cue in cleaned:
            if previous_end is not None and cue.start - previous_end > 2.5 and current:
                paragraphs.append(" ".join(current))
                current = []
            current.append(cue.text)
            previous_end = cue.end
        if current:
            paragraphs.append(" ".join(current))
        return "\n\n".join(paragraphs) + "\n"
    # continuous
    return _clean_text(" ".join(cue.text for cue in cleaned)) + "\n"
