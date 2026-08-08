#!/usr/bin/env bash
# Launch YouTube Subtitle Downloader from a development checkout.
#
# Double-click friendly: it resolves its own location, so it works from the
# project root or from a copy/symlink placed anywhere (e.g. the Desktop).
# No installation is required — the package is imported from ./src.
#
# Usage:
#   ./launch.sh          # run the GUI
#   ./launch.sh --cli    # run the command line interface
set -euo pipefail

# Resolve the real location of this script (follows symlinks), so the project
# root is found no matter where the launcher was double-clicked from.
SOURCE="${BASH_SOURCE[0]}"
while [[ -L "$SOURCE" ]]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ "$SOURCE" != /* ]] && SOURCE="$DIR/$SOURCE"
done
PROJECT_ROOT="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
SRC_DIR="$PROJECT_ROOT/src"

if [[ ! -d "$SRC_DIR/youtube_subtitle_downloader" ]]; then
    echo "error: no se encontró el paquete en $SRC_DIR" >&2
    echo "Coloca este lanzador dentro del proyecto (junto a run.py) o junto a una copia del código fuente." >&2
    read -r -p "Pulsa Enter para cerrar..."
    exit 1
fi

cd "$PROJECT_ROOT"

if [[ "${1:-}" == "--cli" ]]; then
    PYTHONPATH="$SRC_DIR${PYTHONPATH:+:$PYTHONPATH}" exec python3 -m youtube_subtitle_downloader.cli "${@:2}"
fi

# Keep the terminal open on failure so the error is visible (the GUI branch
# cannot exec, or the error would close the terminal immediately).
if PYTHONPATH="$SRC_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 -m youtube_subtitle_downloader; then
    :
else
    status=$?
    echo
    echo "La aplicación terminó con un error (código $status)." >&2
    read -r -p "Pulsa Enter para cerrar..."
    exit "$status"
fi
