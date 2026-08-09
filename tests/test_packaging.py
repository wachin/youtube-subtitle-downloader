"""Tests for the Debian packaging metadata and build script."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PACKAGING = PROJECT_ROOT / "packaging"
DEBIAN = PACKAGING / "debian"


# -- build script -----------------------------------------------------------
def test_build_script_exists_and_executable() -> None:
    script = PACKAGING / "build-deb.sh"
    assert script.is_file()
    assert script.stat().st_mode & 0o111  # executable


def test_build_script_has_shebang() -> None:
    first = (PACKAGING / "build-deb.sh").read_text(encoding="utf-8").splitlines()[0]
    assert first == "#!/usr/bin/env bash"


def test_build_script_uses_python_module_name() -> None:
    """The installed Python dir must use underscores (import name)."""
    content = (PACKAGING / "build-deb.sh").read_text(encoding="utf-8")
    assert "PY_MODULE=\"youtube_subtitle_downloader\"" in content
    assert "dist-packages/$PY_MODULE" in content


def test_build_script_uses_root_owner_group() -> None:
    content = (PACKAGING / "build-deb.sh").read_text(encoding="utf-8")
    assert "--root-owner-group" in content


# -- control metadata ---------------------------------------------------------
def test_control_lists_real_dependencies() -> None:
    control = (DEBIAN / "control").read_text(encoding="utf-8")
    for dep in ("python3", "python3-pyqt6", "python3-pyqt6.qtsvg"):
        assert dep in control, f"missing dependency {dep}"
    # Portable across MX (yt-dlp) and pure Debian (python3-yt-dlp).
    assert "yt-dlp | python3-yt-dlp" in control


def test_control_architecture_all() -> None:
    control = (DEBIAN / "control").read_text(encoding="utf-8")
    assert "Architecture: all" in control


def test_copyright_references_common_license() -> None:
    """Debian policy: the copyright file must not embed the full GPL text."""
    copyright_file = (DEBIAN / "copyright").read_text(encoding="utf-8")
    assert "common-licenses/GPL-3" in copyright_file
    # A short licence grant paragraph is fine; the *complete* GPL-3 text
    # (which starts with this distinctive heading) must not be embedded.
    assert "GNU GENERAL PUBLIC LICENSE\n Version 3" not in copyright_file


def test_postinst_and_postrm_refresh_databases() -> None:
    for script in ("postinst", "postrm"):
        content = (DEBIAN / script).read_text(encoding="utf-8")
        assert "gtk-update-icon-cache" in content
        assert "update-desktop-database" in content


def test_changelog_matches_version() -> None:
    changelog = (DEBIAN / "changelog").read_text(encoding="utf-8")
    assert "youtube-subtitle-downloader (0.1.0-1)" in changelog


def test_control_is_a_template_with_placeholders() -> None:
    """build-deb.sh fills in version/size; the source file keeps placeholders."""
    control = (DEBIAN / "control").read_text(encoding="utf-8")
    assert "Version: %%VERSION%%" in control
    assert "Installed-Size: %%INSTALLED_SIZE%%" in control


# -- consistency with the desktop template ------------------------------------
def test_desktop_exec_matches_bin_wrapper() -> None:
    """The packaged .desktop must call the /usr/bin entry point name."""
    desktop = (PACKAGING / "youtube-subtitle-downloader.desktop").read_text(
        encoding="utf-8"
    )
    assert "Exec=youtube-subtitle-downloader" in desktop
    assert "TryExec=youtube-subtitle-downloader" in desktop
