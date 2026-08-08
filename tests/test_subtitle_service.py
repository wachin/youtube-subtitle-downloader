"""Tests for subtitle parsing, conversion, de-duplication and TXT."""

import pytest

from youtube_subtitle_downloader.models.subtitle import SubtitleCue
from youtube_subtitle_downloader.services.subtitle_service import (
    SubtitleParseError,
    clean_incremental,
    convert_cues,
    cues_to_srt,
    cues_to_txt,
    detect_format,
    parse_json3,
    parse_srt,
    parse_subtitles,
    parse_ttml,
    parse_vtt,
)


def make_cues() -> list[SubtitleCue]:
    return [
        SubtitleCue(0.0, 1.0, ["Hello, welcome to this video."]),
        SubtitleCue(1.5, 2.5, ["Today we are going to learn."]),
        SubtitleCue(3.0, 4.0, ["See you next time."]),
    ]


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


SRT_SAMPLE = """1
00:00:01,000 --> 00:00:04,000
Hola, bienvenidos a este video.

2
00:00:03,500 --> 00:00:07,000
bienvenidos a este video. Hoy vamos

3
00:00:07,500 --> 00:00:10,000
a aprender algo nuevo
"""


def test_parse_srt():
    cues = parse_srt(SRT_SAMPLE)
    assert len(cues) == 3
    assert cues[0].start == pytest.approx(1.0)
    assert cues[0].end == pytest.approx(4.0)
    assert cues[0].text == "Hola, bienvenidos a este video."
    assert cues[2].text == "a aprender algo nuevo"


VTT_SAMPLE = """WEBVTT

00:00:01.000 --> 00:00:04.000 align:start position:0%
Hello <c>world</c>

NOTE this is a comment
that spans lines

00:00:05.000 --> 00:00:07.000
Second cue
"""


def test_parse_vtt():
    cues = parse_vtt(VTT_SAMPLE)
    assert len(cues) == 2
    assert cues[0].text == "Hello world"
    assert cues[0].start == pytest.approx(1.0)
    assert cues[1].text == "Second cue"


TTML_SAMPLE = """<?xml version="1.0" encoding="utf-8"?>
<tt xmlns="http://www.w3.org/ns/ttml">
  <body>
    <div>
      <p begin="00:00:01.000" end="00:00:03.000">First <span>line</span></p>
      <p begin="5s" end="8s">Second line</p>
    </div>
  </body>
</tt>
"""


def test_parse_ttml():
    cues = parse_ttml(TTML_SAMPLE)
    assert len(cues) == 2
    assert cues[0].text == "First line"
    assert cues[0].start == pytest.approx(1.0)
    assert cues[1].start == pytest.approx(5.0)
    assert cues[1].end == pytest.approx(8.0)


JSON3_SAMPLE = """{
  "events": [
    {"tStartMs": 1000, "dDurationMs": 2000, "segs": [{"utf8": "Hello"}]},
    {"tStartMs": 3000, "dDurationMs": 0, "segs": [{"utf8": "World"}]}
  ]
}
"""


def test_parse_json3():
    cues = parse_json3(JSON3_SAMPLE)
    assert len(cues) == 2
    assert cues[0].text == "Hello"
    assert cues[0].start == pytest.approx(1.0)
    # No duration and no next event: end == start.
    assert cues[1].end == pytest.approx(3.0)


def test_parse_dispatcher():
    cues = parse_subtitles(SRT_SAMPLE, "srt")
    assert len(cues) == 3
    with pytest.raises(SubtitleParseError):
        parse_subtitles("whatever", "unknown")


def test_detect_format_from_content():
    assert detect_format("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHi") == "vtt"
    assert detect_format('{"events": []}') == "json3"
    assert detect_format("1\n00:00:01,000 --> 00:00:02,000\nHi") == "srt"
    assert detect_format("<?xml version=\"1.0\"?><tt></tt>") == "ttml"
    assert detect_format("plain text") is None


def test_pb3_json_parses_as_json3():
    # YouTube's "pb3" wire format is JSON with events + segs (like JSON3).
    pb3 = '{"wireMagic": "pb3", "events": [{"tStartMs": 100, "segs": [{"utf8": "Hola"}]}]}'
    cues = parse_json3(pb3)
    assert len(cues) == 1
    assert cues[0].text == "Hola"


# --------------------------------------------------------------------------
# Serialization round trips
# --------------------------------------------------------------------------


def test_srt_round_trip():
    cues = make_cues()
    text = cues_to_srt(cues)
    parsed = parse_srt(text)
    assert [c.text for c in parsed] == [c.text for c in cues]
    assert parsed[0].start == pytest.approx(cues[0].start)
    assert parsed[-1].end == pytest.approx(cues[-1].end)


def test_convert_cues_all_formats():
    cues = make_cues()
    for fmt in ("srt", "vtt", "ttml", "json3"):
        content = convert_cues(cues, fmt)
        assert content.strip()
    # ttml output must remain parseable
    assert len(parse_ttml(convert_cues(cues, "ttml"))) == 3
    with pytest.raises(ValueError):
        convert_cues(cues, "docx")


# --------------------------------------------------------------------------
# Incremental caption de-duplication (roadmap section 49)
# --------------------------------------------------------------------------


INCREMENTAL = [
    SubtitleCue(0.0, 1.0, ["Hola"]),
    SubtitleCue(0.5, 1.5, ["Hola amigos"]),
    SubtitleCue(1.0, 2.0, ["Hola amigos bienvenidos"]),
    SubtitleCue(1.5, 2.5, ["amigos bienvenidos al canal"]),
]


def test_clean_incremental_merges_youtube_captions():
    merged = clean_incremental(INCREMENTAL)
    assert merged[-1].text == "Hola amigos bienvenidos al canal"
    # The intermediate duplicates must be absorbed into a single cue.
    assert len(merged) == 1


def test_txt_continuous_uses_cleaned_text():
    text = cues_to_txt(INCREMENTAL, mode="continuous")
    assert "Hola amigos bienvenidos al canal" in text
    assert "Hola Hola" not in text


def test_clean_incremental_is_not_too_aggressive():
    cues = [
        SubtitleCue(0.0, 1.0, ["Hello world"]),
        SubtitleCue(10.0, 11.0, ["Hello again"]),  # far in time: legit repeat
    ]
    merged = clean_incremental(cues)
    assert len(merged) == 2
    assert merged[-1].text == "Hello again"


def test_txt_modes():
    cues = make_cues()
    lines = cues_to_txt(cues, mode="lines")
    assert lines.count("\n") >= 3
    paragraphs = cues_to_txt(cues, mode="paragraphs")
    assert paragraphs.strip()
    continuous = cues_to_txt(cues, mode="continuous")
    assert "Hello, welcome" in continuous
    assert "\n\n" not in continuous.strip()
