#!/bin/bash
# Build Orbio .deb package
# Requires: dpkg-deb

set -e

APP_NAME="orbio"
APP_VERSION="0.1.0"
ARCH="amd64"
PKG_DIR="${APP_NAME}_${APP_VERSION}_${ARCH}"

echo "Building Orbio .deb package v${APP_VERSION}..."

# Clean
rm -rf "${PKG_DIR}" "${PKG_DIR}.deb"

# Create package structure
mkdir -p "${PKG_DIR}/DEBIAN"
mkdir -p "${PKG_DIR}/usr/bin"
mkdir -p "${PKG_DIR}/usr/lib/python3/dist-packages"
mkdir -p "${PKG_DIR}/usr/share/applications"
mkdir -p "${PKG_DIR}/usr/share/icons/hicolor/256x256/apps"

# Control file
cat > "${PKG_DIR}/DEBIAN/control" << EOF
Package: ${APP_NAME}
Version: ${APP_VERSION}
Section: web
Priority: optional
Architecture: ${ARCH}
Depends: python3 (>= 3.12), python3-pyqt6, python3-pyqt6.qtwebengine
Maintainer: FireRam <fireram87@github.com>
Description: Privacy-first browser with radial UI
 Orbio is a privacy-first Linux browser that breaks the rectangular
 UI paradigm with radial tab management, arc navigation, built-in
 tracker/ad blocking, and a theme engine.
Homepage: https://github.com/FireRam87/Orbio
EOF

# Copy application
cp -r ../orbio "${PKG_DIR}/usr/lib/python3/dist-packages/"

# Launcher script
cat > "${PKG_DIR}/usr/bin/orbio" << 'LAUNCHER'
#!/bin/bash
exec python3 -m orbio "$@"
LAUNCHER
chmod +x "${PKG_DIR}/usr/bin/orbio"

# Desktop file
sed 's|Icon=org.orbio.Browser|Icon=orbio|' ../flatpak/org.orbio.Browser.desktop > "${PKG_DIR}/usr/share/applications/orbio.desktop"

# Icon
cp ../orbio/assets/orbio_logo.png "${PKG_DIR}/usr/share/icons/hicolor/256x256/apps/orbio.png"

# Build
dpkg-deb --build "${PKG_DIR}"
echo "Built: ${PKG_DIR}.deb"
