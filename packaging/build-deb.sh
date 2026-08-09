#!/usr/bin/env bash
# Build the installable .deb package for youtube-subtitle-downloader.
#
# The staged approach (dpkg-deb --build) keeps the layout fully under our
# control: the Python package goes into /usr/lib/python3/dist-packages, the
# /usr/bin entry points are small wrappers, and the icon + .desktop launcher
# follow the Freedesktop conventions.
#
# Usage:
#   packaging/build-deb.sh          # writes dist/youtube-subtitle-downloader_<ver>_all.deb
#   VERSION=0.2.0 packaging/build-deb.sh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_PKG="$PROJECT_ROOT/src/youtube_subtitle_downloader"
VERSION="${VERSION:-$(sed -n 's/^__version__ = "\([^"]*\)"/\1/p' "$SRC_PKG/__init__.py" | head -n 1)}"
if [[ -z "$VERSION" ]]; then
    echo "error: no se pudo determinar la versión (¿cambió __init__.py?) — usa VERSION=x.y.z" >&2
    exit 1
fi
PACKAGE="youtube-subtitle-downloader"
PY_MODULE="youtube_subtitle_downloader"
ARCH="all"
DEB="${PACKAGE}_${VERSION}_${ARCH}.deb"
OUT_DIR="$PROJECT_ROOT/dist"

echo "==> Building $PACKAGE $VERSION (arch=$ARCH)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# -- filesystem layout -------------------------------------------------------
DEST_PKG="$STAGE/usr/lib/python3/dist-packages/$PY_MODULE"
mkdir -p \
    "$DEST_PKG" \
    "$STAGE/usr/bin" \
    "$STAGE/usr/share/applications" \
    "$STAGE/usr/share/icons/hicolor/scalable/apps" \
    "$STAGE/usr/share/doc/$PACKAGE" \
    "$STAGE/DEBIAN"

# Python package (keep resources; drop caches and tests).
cp -r "$SRC_PKG"/. "$DEST_PKG"/
find "$DEST_PKG" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$DEST_PKG" -name '*.pyc' -delete

# /usr/bin entry points (thin wrappers; the package import path is standard).
cat > "$STAGE/usr/bin/youtube-subtitle-downloader" <<'EOF'
#!/bin/sh
exec python3 -m youtube_subtitle_downloader "$@"
EOF
cat > "$STAGE/usr/bin/youtube-subtitle-downloader-cli" <<'EOF'
#!/bin/sh
exec python3 -m youtube_subtitle_downloader.cli "$@"
EOF
chmod 755 "$STAGE/usr/bin/youtube-subtitle-downloader" \
    "$STAGE/usr/bin/youtube-subtitle-downloader-cli"

# Icon + desktop launcher (from the templates we keep in packaging/).
cp "$PROJECT_ROOT/packaging/youtube-subtitle-downloader.desktop" \
    "$STAGE/usr/share/applications/"
cp "$PROJECT_ROOT/src/youtube_subtitle_downloader/resources/icons/youtube-subtitle-downloader.svg" \
    "$STAGE/usr/share/icons/hicolor/scalable/apps/"

# Documentation. The copyright file references the common GPL-3 license
# (Debian policy: do not embed the full license text; /usr/share/common-
# licenses/GPL-3 is installed by the base system).
cp "$PROJECT_ROOT/packaging/debian/copyright" "$STAGE/usr/share/doc/$PACKAGE/copyright"
cp "$PROJECT_ROOT/packaging/debian/changelog" "$STAGE/usr/share/doc/$PACKAGE/changelog"
gzip -9 -n -f "$STAGE/usr/share/doc/$PACKAGE/changelog"

# -- DEBIAN metadata ----------------------------------------------------------
# packaging/debian/control is the single source of truth for the package
# metadata; fill in the version and the computed installed size here.
INSTALLED_SIZE="$(du -sk "$STAGE/usr" | cut -f1)"
sed \
    -e "s/^Version:.*/Version: $VERSION/" \
    -e "s/^Installed-Size:.*/Installed-Size: $INSTALLED_SIZE/" \
    "$PROJECT_ROOT/packaging/debian/control" > "$STAGE/DEBIAN/control"

cp "$PROJECT_ROOT/packaging/debian/postinst" "$STAGE/DEBIAN/postinst"
cp "$PROJECT_ROOT/packaging/debian/postrm" "$STAGE/DEBIAN/postrm"
chmod 755 "$STAGE/DEBIAN/postinst" "$STAGE/DEBIAN/postrm"

# -- normalise permissions (Debian policy) -------------------------------------
find "$STAGE" -type d -exec chmod 755 {} +
find "$STAGE" -type f -exec chmod 644 {} +
chmod 755 "$STAGE/usr/bin/youtube-subtitle-downloader" \
    "$STAGE/usr/bin/youtube-subtitle-downloader-cli" \
    "$STAGE/DEBIAN/postinst" "$STAGE/DEBIAN/postrm"

# -- build --------------------------------------------------------------------
mkdir -p "$OUT_DIR"
dpkg-deb --build --root-owner-group "$STAGE" "$OUT_DIR/$DEB" >/dev/null
echo "==> Built $OUT_DIR/$DEB"
echo "    size: $(du -h "$OUT_DIR/$DEB" | cut -f1)"
