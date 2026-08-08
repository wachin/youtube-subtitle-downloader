"""Tests for the double-click launcher script (launch.sh)."""

import stat
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = PROJECT_ROOT / "launch.sh"


def test_launcher_exists() -> None:
    assert LAUNCHER.is_file()


def test_launcher_is_executable() -> None:
    mode = LAUNCHER.stat().st_mode
    assert mode & stat.S_IXUSR, "launch.sh must be executable (chmod +x)"


def test_launcher_has_shebang() -> None:
    first_line = LAUNCHER.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("#!/usr/bin/env bash")


def test_launcher_imports_package_from_src() -> None:
    """The launcher must point at the src/ layout, not an installed copy."""
    content = LAUNCHER.read_text(encoding="utf-8")
    assert "SRC_DIR=\"$PROJECT_ROOT/src\"" in content
    # The package is imported from the src/ layout via PYTHONPATH and -m.
    assert "python3 -m youtube_subtitle_downloader" in content
    assert "PYTHONPATH=\"$SRC_DIR" in content


def test_launcher_supports_cli_mode() -> None:
    content = LAUNCHER.read_text(encoding="utf-8")
    assert "--cli" in content


def test_launcher_self_locating() -> None:
    """The launcher resolves its own location (works from any directory)."""
    content = LAUNCHER.read_text(encoding="utf-8")
    assert "BASH_SOURCE[0]" in content
    assert "readlink" in content
