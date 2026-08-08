"""Entry point for ``python -m youtube_subtitle_downloader``."""

import sys

from .app import main

if __name__ == "__main__":
    sys.exit(main())
