"""Tests for the yt-dlp update check (roadmap section 40)."""

import io
import json

from youtube_subtitle_downloader.services import ytdlp_service
from youtube_subtitle_downloader.services.ytdlp_service import (
    _version_key,
    check_update,
    latest_version,
)


class _FakeResponse:
    """Minimal file-like object standing in for an HTTP response."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def close(self) -> None:
        pass


def _fake_urlopen(payload: dict):
    def urlopen(request, timeout=None):  # noqa: ARG001
        return _FakeResponse(json.dumps(payload).encode())
    return urlopen


# --------------------------------------------------------------------------
# latest_version
# --------------------------------------------------------------------------


def test_latest_version_parses_tag(monkeypatch):
    monkeypatch.setattr(
        ytdlp_service.urllib.request,
        "urlopen",
        _fake_urlopen({"tag_name": "2026.07.04"}),
    )
    assert latest_version() == "2026.07.04"


def test_latest_version_strips_v_prefix(monkeypatch):
    monkeypatch.setattr(
        ytdlp_service.urllib.request,
        "urlopen",
        _fake_urlopen({"tag_name": "v2026.07.04"}),
    )
    assert latest_version() == "2026.07.04"


def test_latest_version_network_error_returns_none(monkeypatch):
    def raise_error(request, timeout=None):  # noqa: ARG001
        raise OSError("no network")

    monkeypatch.setattr(ytdlp_service.urllib.request, "urlopen", raise_error)
    assert latest_version() is None


def test_latest_version_malformed_response_returns_none(monkeypatch):
    def bad_json(request, timeout=None):  # noqa: ARG001
        return _FakeResponse(b"not json")

    monkeypatch.setattr(ytdlp_service.urllib.request, "urlopen", bad_json)
    assert latest_version() is None


def test_latest_version_missing_tag_returns_none(monkeypatch):
    monkeypatch.setattr(
        ytdlp_service.urllib.request,
        "urlopen",
        _fake_urlopen({"name": "something"}),
    )
    assert latest_version() is None


# --------------------------------------------------------------------------
# check_update
# --------------------------------------------------------------------------


def test_check_update_available(monkeypatch):
    monkeypatch.setattr(ytdlp_service, "latest_version", lambda: "2026.07.04")
    monkeypatch.setattr(ytdlp_service, "version", lambda: "2026.07.03")
    available, latest = check_update()
    assert available is True
    assert latest == "2026.07.04"


def test_check_update_up_to_date(monkeypatch):
    monkeypatch.setattr(ytdlp_service, "latest_version", lambda: "2026.07.04")
    monkeypatch.setattr(ytdlp_service, "version", lambda: "2026.07.04")
    available, latest = check_update()
    assert available is False
    assert latest == "2026.07.04"


def test_check_update_unreachable(monkeypatch):
    monkeypatch.setattr(ytdlp_service, "latest_version", lambda: None)
    available, latest = check_update()
    assert available is False
    assert latest is None


def test_check_update_installed_unknown(monkeypatch):
    monkeypatch.setattr(ytdlp_service, "latest_version", lambda: "2026.07.04")
    monkeypatch.setattr(ytdlp_service, "version", lambda: None)
    available, latest = check_update()
    assert available is False
    assert latest == "2026.07.04"


# --------------------------------------------------------------------------
# version comparison helper
# --------------------------------------------------------------------------


def test_version_key_compares_numerically():
    assert _version_key("2026.07.04") == (2026, 7, 4)
    assert _version_key("2026.7.4") == (2026, 7, 4)
    assert _version_key("2026.07.04") == _version_key("2026.7.4")
    assert _version_key("2026.07.04.123456") > _version_key("2026.07.04")


def test_check_update_with_version_tuples(monkeypatch):
    monkeypatch.setattr(ytdlp_service, "latest_version", lambda: "2026.8.1")
    monkeypatch.setattr(ytdlp_service, "version", lambda: "2026.07.04")
    available, _ = check_update()
    assert available is True


def test_reads_from_github_api(monkeypatch):
    """The request targets the GitHub releases endpoint with a User-Agent."""
    captured: list[object] = []

    def spy(request, timeout=None):  # noqa: ARG001
        captured.append(request)
        return _FakeResponse(json.dumps({"tag_name": "2026.07.04"}).encode())

    monkeypatch.setattr(ytdlp_service.urllib.request, "urlopen", spy)
    assert latest_version() == "2026.07.04"
    assert captured
    request = captured[0]
    assert "api.github.com" in request.full_url
    headers = {k.lower(): v for k, v in request.headers.items()}
    assert headers.get("user-agent") == "youtube-subtitle-downloader"


def test_worker_importable():
    from youtube_subtitle_downloader.workers.update_worker import (  # noqa: F401
        UpdateCheckWorker,
    )
