#!/usr/bin/env python3
"""Simple development launcher (no installation required).

Usage:

    python3 run.py

The package lives in the ``src/`` layout, so this script puts ``src`` on the
Python path and starts the application. For a globally installed command use
``pip install -e .`` which provides ``youtube-subtitle-downloader``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the src-layout package importable without installing it.
_SRC = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(_SRC))

from youtube_subtitle_downloader.app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
