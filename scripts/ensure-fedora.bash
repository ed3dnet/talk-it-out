#!/usr/bin/env bash
# pattern: Imperative Shell (handles system package installation)
#
# Purpose: Install all dependencies needed to build packages with NFPM on Fedora
# Usage: sudo bash scripts/ensure-fedora.bash

set -euo pipefail

echo "==> Installing Python build tools..."
dnf install -y python3-devel python3-pip

echo "==> Installing system library development headers..."
dnf install -y ffmpeg-free-devel portaudio-devel

echo "==> Installing system runtime dependencies..."
dnf install -y wl-clipboard ydotool ffmpeg-free portaudio

echo "==> Installing NFPM..."
# Download and install NFPM from GitHub releases
NFPM_VERSION="2.42.0"
NFPM_URL="https://github.com/goreleaser/nfpm/releases/download/v${NFPM_VERSION}/nfpm_${NFPM_VERSION}_Linux_x86_64.tar.gz"

curl -L "$NFPM_URL" -o /tmp/nfpm.tar.gz
tar -xzf /tmp/nfpm.tar.gz -C /tmp nfpm
install -m 0755 /tmp/nfpm /usr/local/bin/nfpm
rm -f /tmp/nfpm.tar.gz /tmp/nfpm

echo "==> Verifying NFPM installation..."
nfpm --version

echo "==> All dependencies installed successfully!"
