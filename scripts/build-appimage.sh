#!/bin/bash
# Build Orbio AppImage
# Requires: appimagetool, python3, pip

set -e

APP_NAME="Orbio"
APP_VERSION="0.1.0"
APP_DIR="AppDir"

echo "Building Orbio AppImage v${APP_VERSION}..."

# Clean previous build
rm -rf "${APP_DIR}" "${APP_NAME}-${APP_VERSION}-x86_64.AppImage"

# Create AppDir structure
mkdir -p "${APP_DIR}/usr/bin"
mkdir -p "${APP_DIR}/usr/lib/python3/dist-packages"
mkdir -p "${APP_DIR}/usr/share/applications"
mkdir -p "${APP_DIR}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${APP_DIR}/usr/share/metainfo"

# Copy application
cp -r ../orbio "${APP_DIR}/usr/lib/python3/dist-packages/"

# Create launcher script
cat > "${APP_DIR}/usr/bin/orbio" << 'LAUNCHER'
#!/bin/bash
export PYTHONPATH="${APPDIR}/usr/lib/python3/dist-packages:${PYTHONPATH}"
exec python3 -m orbio "$@"
LAUNCHER
chmod +x "${APP_DIR}/usr/bin/orbio"

# Desktop file
cp ../flatpak/org.orbio.Browser.desktop "${APP_DIR}/usr/share/applications/"
cp ../flatpak/org.orbio.Browser.desktop "${APP_DIR}/"

# Icon
cp ../orbio/assets/orbio_logo.png "${APP_DIR}/usr/share/icons/hicolor/256x256/apps/org.orbio.Browser.png"
cp ../orbio/assets/orbio_logo.png "${APP_DIR}/orbio.png"

# Metainfo
cp ../flatpak/org.orbio.Browser.metainfo.xml "${APP_DIR}/usr/share/metainfo/"

# AppRun
cat > "${APP_DIR}/AppRun" << 'APPRUN'
#!/bin/bash
SELF=$(readlink -f "$0")
export APPDIR=$(dirname "$SELF")
export PATH="${APPDIR}/usr/bin:${PATH}"
export PYTHONPATH="${APPDIR}/usr/lib/python3/dist-packages:${PYTHONPATH}"
exec python3 -m orbio "$@"
APPRUN
chmod +x "${APP_DIR}/AppRun"

# Build AppImage (requires appimagetool in PATH)
if command -v appimagetool &> /dev/null; then
    appimagetool "${APP_DIR}" "${APP_NAME}-${APP_VERSION}-x86_64.AppImage"
    echo "Built: ${APP_NAME}-${APP_VERSION}-x86_64.AppImage"
else
    echo "appimagetool not found. Install from https://github.com/AppImage/appimagetool"
    echo "AppDir created at: ${APP_DIR}/"
fi
