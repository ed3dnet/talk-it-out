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

echo "==> Installing runtime system dependencies..."
dnf install -y wl-clipboard ydotool ffmpeg-free portaudio

echo "==> All dependencies installed successfully!"
