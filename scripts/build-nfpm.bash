#!/usr/bin/env bash
# pattern: Imperative Shell (orchestrates NFPM packaging)
#
# Purpose: Build both RPM and DEB packages using NFPM from current source
# Usage: bash scripts/build-nfpm.bash
#
# This script:
# 1. Extracts version from pyproject.toml
# 2. Creates staging directory with proper layout
# 3. Bundles all Python dependencies using uv
# 4. Creates wrapper script for execution
# 5. Generates both RPM and DEB packages with nfpm

set -euo pipefail

# Extract version from pyproject.toml
VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)

if [[ -z "$VERSION" ]]; then
    echo "ERROR: Could not extract version from pyproject.toml"
    exit 1
fi

echo "==> Building talk-it-out version $VERSION"

# Clean previous artifacts
echo "==> Cleaning previous build artifacts..."
rm -rf staging/ dist/ build/ *.egg-info *.deb *.rpm

# Create staging directory structure
echo "==> Creating staging directory structure..."
mkdir -p staging/usr/bin
mkdir -p staging/usr/lib/talk-it-out
mkdir -p staging/usr/share/applications

# Build Python wheel
echo "==> Building Python wheel..."
uv build --wheel --out-dir dist/

# Install the application + all dependencies to staging area
# Install from the current directory to ensure full dependency resolution
echo "==> Installing Python application and dependencies to staging..."
uv pip install --target staging/usr/lib/talk-it-out \
    --python /usr/bin/python3 \
    .

# Create wrapper script that sets PYTHONPATH
echo "==> Creating wrapper script..."
cat > staging/usr/bin/talk-it-out << 'EOF'
#!/bin/sh
# Wrapper script for talk-it-out
# Sets PYTHONPATH to bundled dependencies and executes main module
export PYTHONPATH=/usr/lib/talk-it-out${PYTHONPATH:+:$PYTHONPATH}
exec python3 -m talk_it_out.main "$@"
EOF
chmod +x staging/usr/bin/talk-it-out

# Create desktop file
echo "==> Creating desktop file..."
cat > staging/usr/share/applications/talk-it-out.desktop << EOF
[Desktop Entry]
Type=Application
Name=Talk It Out
Comment=Voice-to-text using Whisper AI
Exec=talk-it-out gui
Icon=audio-input-microphone
Terminal=false
Categories=Utility;Audio;Qt;
Keywords=voice;speech;transcription;whisper;dictation;
EOF

# Generate DEB package
echo "==> Generating DEB package..."
VERSION=$VERSION nfpm package --packager deb --config nfpm.yaml

# Generate RPM package
echo "==> Generating RPM package..."
VERSION=$VERSION nfpm package --packager rpm --config nfpm.yaml

echo ""
echo "==> Build complete!"
echo "    DEB package: $(ls -1 talk-it-out_${VERSION}_amd64.deb 2>/dev/null || echo 'not found')"
echo "    RPM package: $(ls -1 talk-it-out-${VERSION}-1.x86_64.rpm 2>/dev/null || echo 'not found')"
echo ""
echo "Test installation:"
echo "  Fedora: sudo dnf install -y ./talk-it-out-${VERSION}-1.x86_64.rpm"
echo "  Ubuntu: sudo apt install -y ./talk-it-out_${VERSION}_amd64.deb"
