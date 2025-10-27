#!/usr/bin/env bash
# pattern: Imperative Shell (handles system package installation)
#
# Purpose: Install all dependencies needed to build RPM packages on Fedora
# Usage: sudo bash scripts/ensure-fedora.bash

set -euo pipefail

echo "==> Installing RPM build tools..."
dnf install -y rpm-build rpmdevtools python3-devel

echo "==> Installing Python packaging tools..."
dnf install -y pyproject-rpm-macros python3-build

echo "==> Installing system library development headers..."
dnf install -y ffmpeg-free-devel portaudio-devel

echo "==> Installing system runtime dependencies..."
dnf install -y wl-clipboard ydotool ffmpeg-free portaudio

echo "==> Installing Python dependencies from Fedora repos..."
dnf install -y python3-typer python3-tomli-w python3-evdev \
              python3-numpy python3-scipy python3-pyqt6

echo "==> All dependencies installed successfully!"
