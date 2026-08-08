"""Tests for safe filename generation and templates."""

from youtube_subtitle_downloader.utils.filenames import (
    DEFAULT_TEMPLATE,
    PRESET_TEMPLATES,
    render_template,
    sanitize_filename,
    subtitle_file_name,
)


def test_sanitize_removes_invalid_characters():
    name = sanitize_filename('weird:<">/\\|?*chars')
    assert "/" not in name
    assert "\\" not in name
    assert ":" not in name
    assert name.strip()


def test_sanitize_blocks_path_traversal():
    name = sanitize_filename("../../etc/passwd")
    assert name == "etc-passwd" or "/" not in name and ".." not in name


def test_sanitize_empty_becomes_untitled():
    assert sanitize_filename("   ") == "untitled"


def test_render_template():
    name = render_template(
        "%(title)s [%(id)s].%(language)s.%(ext)s",
        title="My Video: Part 1",
        video_id="abc123",
        language="es",
        ext="srt",
    )
    assert name == "My Video- Part 1 [abc123].es.srt"
    assert "/" not in name


def test_render_template_ignores_unknown_placeholders():
    name = render_template(
        "%(title)s %(unknown)s",
        title="Hello",
        video_id="id",
        language="en",
        ext="srt",
    )
    assert name == "Hello %(unknown)s"


def test_presets_are_rendereable():
    for template in PRESET_TEMPLATES.values():
        name = subtitle_file_name(
            template,
            title="Title / with slashes",
            video_id="VID123",
            language="es-orig",
            ext="vtt",
        )
        assert name
        assert "/" not in name


def test_default_template_available():
    assert "%(title)s" in DEFAULT_TEMPLATE
