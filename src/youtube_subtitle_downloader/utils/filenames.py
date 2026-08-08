"""Safe filename generation and user-friendly templates.

The goal is to never write outside the target directory: filenames are
sanitized so path traversal (``../``, absolute paths, drive letters) and
filesystem-invalid characters are removed.
"""

from __future__ import annotations

import re

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MULTI_SPACE = re.compile(r"\s+")

#: Friendly presets offered in the GUI (section 12 of the roadmap).
PRESET_TEMPLATES: dict[str, str] = {
    "Title - Language": "%(title)s - %(language)s",
    "Title [ID] - Language": "%(title)s [%(id)s] - %(language)s",
    "ID - Language": "%(id)s - %(language)s",
}

DEFAULT_TEMPLATE = "%(title)s [%(id)s].%(language)s.%(ext)s"


def sanitize_filename(name: str, max_length: int = 200, replacement: str = "-") -> str:
    """Make ``name`` safe to use as a single file name.

    Invalid characters, leading/trailing dots and spaces, and ``..``
    sequences (which could enable path traversal) are removed.
    """
    cleaned = _INVALID_CHARS.sub(replacement, name)
    cleaned = cleaned.replace("..", ".").strip().strip(".")
    while ".." in cleaned:
        cleaned = cleaned.replace("..", ".")
    cleaned = _MULTI_SPACE.sub(" ", cleaned).strip()
    if not cleaned:
        cleaned = "untitled"
    return cleaned[:max_length].rstrip(" .")


def render_template(
    template: str,
    *,
    title: str,
    video_id: str,
    language: str,
    ext: str,
) -> str:
    """Render a user template (``%(title)s`` style) into a safe file name."""
    values = {
        "title": sanitize_filename(title),
        "id": sanitize_filename(video_id),
        "language": sanitize_filename(language),
        "ext": sanitize_filename(ext),
    }
    try:
        rendered = template % values
    except (KeyError, ValueError, TypeError):
        # Unknown placeholders: substitute the ones we know and keep the rest.
        rendered = template
        for key, value in values.items():
            rendered = rendered.replace(f"%({key})s", value)
    return sanitize_filename(rendered)


def subtitle_file_name(
    template: str,
    *,
    title: str,
    video_id: str,
    language: str,
    ext: str,
) -> str:
    """File name for a subtitle (or clean TXT) download."""
    return render_template(
        template,
        title=title,
        video_id=video_id,
        language=language,
        ext=ext,
    )
