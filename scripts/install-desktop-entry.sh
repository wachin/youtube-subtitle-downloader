#!/usr/bin/env bash
# Install (or refresh) the user-level desktop launcher for the application.
#
# The packaged template (packaging/youtube-subtitle-downloader.desktop) uses
# `Exec=youtube-subtitle-downloader` (the installed entry point). For
# development, this script regenerates a user-level copy that runs the
# project's `run.py` directly, so no installation is required.
#
# Usage:
#   scripts/install-desktop-entry.sh [path-to-project]
#
# Defaults to the repository root (the parent of this script).
set -euo pipefail

PROJECT_ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
TEMPLATE="$PROJECT_ROOT/packaging/youtube-subtitle-downloader.desktop"
TARGET_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
TARGET="$TARGET_DIR/youtube-subtitle-downloader.desktop"

if [[ ! -f "$TEMPLATE" ]]; then
    echo "error: template not found: $TEMPLATE" >&2
    exit 1
fi

mkdir -p "$TARGET_DIR"

# Replace the packaged Exec line with a direct run.py invocation and drop
# TryExec (the entry point is not installed in a development checkout).
sed \
    -e "s|^Exec=.*|Exec=python3 $PROJECT_ROOT/run.py|" \
    -e '/^TryExec=.*/d' \
    "$TEMPLATE" > "$TARGET"

echo "installed: $TARGET"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$TARGET_DIR"
    echo "desktop database updated."
fi
