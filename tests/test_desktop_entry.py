"""Tests for the Freedesktop launcher template (packaging/*.desktop)."""

import configparser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DESKTOP_FILE = PROJECT_ROOT / "packaging" / "youtube-subtitle-downloader.desktop"


def _read_entry() -> dict[str, str]:
    """Parse the .desktop template and return its [Desktop Entry] section.

    ``ConfigParser`` lowercases option names by default; the .desktop spec
    uses case-sensitive keys, so ``optionxform`` keeps the original casing.
    """
    parser = configparser.ConfigParser()
    parser.optionxform = str  # type: ignore[method-assign]
    assert parser.read(DESKTOP_FILE) == [str(DESKTOP_FILE)]
    return dict(parser["Desktop Entry"])


def test_desktop_template_exists() -> None:
    assert DESKTOP_FILE.is_file()


def test_desktop_template_required_keys() -> None:
    entry = _read_entry()
    for key in ("Type", "Name", "Exec", "Icon", "Terminal", "Categories"):
        assert entry.get(key), f"missing required key {key}"
    assert entry["Type"] == "Application"
    assert entry["Terminal"] == "false"


def test_desktop_template_icon_matches_bundled_svg() -> None:
    icon = _read_entry()["Icon"]
    assert icon
    svg = (
        PROJECT_ROOT
        / "src"
        / "youtube_subtitle_downloader"
        / "resources"
        / "icons"
        / f"{icon}.svg"
    )
    assert svg.is_file(), f"icon {icon!r} does not match any bundled SVG"


def test_desktop_template_exec_matches_entry_point() -> None:
    # The packaged template must launch the installed entry point.
    assert _read_entry()["Exec"] == "youtube-subtitle-downloader"


def test_desktop_template_try_exec_matches_entry_point() -> None:
    # The menu may hide the entry when the binary is not installed.
    assert _read_entry()["TryExec"] == "youtube-subtitle-downloader"


def test_desktop_template_single_main_category() -> None:
    """The spec allows exactly one main category (e.g. AudioVideo)."""
    categories = _read_entry()["Categories"].rstrip(";").split(";")
    main_categories = {
        "AudioVideo",
        "Audio",
        "Video",
        "Development",
        "Education",
        "Game",
        "Graphics",
        "Network",
        "Office",
        "Science",
        "Settings",
        "System",
        "Utility",
    }
    assert len([c for c in categories if c in main_categories]) == 1
