"""Tests for track building from raw yt-dlp info structures."""

from youtube_subtitle_downloader.models.subtitle import SubtitleKind
from youtube_subtitle_downloader.models.video import VideoInfo
from youtube_subtitle_downloader.services.ytdlp_service import YtDlpService

# A stub settings object: build_tracks/to_video_info do not use settings.
_FAKE_SETTINGS = object()


def make_service() -> YtDlpService:
    return YtDlpService(_FAKE_SETTINGS)


def _fake_info() -> dict:
    return {
        "id": "W2nxqwzsy3A",
        "title": "Example video",
        "channel": "Example Channel",
        "duration": 125,
        "upload_date": "20240101",
        "thumbnail": "https://example.com/thumb.jpg",
        "subtitles": {},
        "automatic_captions": {
            "es-orig": [
                {"ext": "vtt", "name": "Spanish (Original)", "url": "http://x/es-orig.vtt"},
                {"ext": "srt"},
            ],
            "es": [
                {"ext": "vtt", "name": "Spanish", "url": "http://x/es.vtt"},
                {"ext": "srt"},
                {"ext": "ttml"},
            ],
            "en": [
                {"ext": "vtt", "name": "English", "url": "http://x/en.vtt"},
                {"ext": "json3"},
            ],
            "pt-BR": [{"ext": "vtt"}],
        },
    }


def test_build_tracks_manual_and_automatic():
    service = make_service()
    tracks = service.build_tracks(_fake_info())
    kinds = {t.kind for t in tracks}
    assert SubtitleKind.AUTOMATIC in kinds
    # No manual subtitles in this fixture: automatic only (roadmap section 58).
    assert SubtitleKind.MANUAL not in kinds
    assert tracks


def test_automatic_captions_survive_no_manual_subtitles():
    """The classic 'has no subtitles' case still yields usable tracks."""
    service = make_service()
    info = service.to_video_info(_fake_info(), "https://youtu.be/W2nxqwzsy3A")
    assert len(info.manual_tracks) == 0
    assert len(info.automatic_tracks) >= 4


def test_original_track_detection():
    service = make_service()
    tracks = service.build_tracks(_fake_info())
    original = next(t for t in tracks if t.language_code == "es-orig")
    assert original.is_original
    assert original.base_code == "es"
    assert "Original" in original.display_name
    plain = next(t for t in tracks if t.language_code == "es")
    assert not plain.is_original


def test_formats_ordered_with_supported_first():
    service = make_service()
    tracks = service.build_tracks(_fake_info())
    en = next(t for t in tracks if t.language_code == "en")
    assert en.formats[0] == "vtt"
    assert "json3" in en.formats


def test_find_track_by_code_and_kind():
    service = make_service()
    info = service.to_video_info(_fake_info(), "https://youtu.be/W2nxqwzsy3A")
    track = info.find_track("es", SubtitleKind.AUTOMATIC)
    assert track is not None
    assert track.language_code == "es"
    # base code matches -orig requests too
    track = info.find_track("es", SubtitleKind.AUTOMATIC)
    assert track is not None
    assert info.find_track("zz", SubtitleKind.AUTOMATIC) is None


def test_video_info_properties():
    service = make_service()
    info = service.to_video_info(_fake_info(), "https://youtu.be/W2nxqwzsy3A")
    assert info.formatted_duration == "2:05"
    assert info.formatted_upload_date == "2024-01-01"
    assert info.video_id == "W2nxqwzsy3A"
