#!/usr/bin/env bash
# pattern: Imperative Shell (orchestrates RPM packaging)
#
# Purpose: Build RPM package for Fedora from current source tree
# Usage: bash scripts/package-fedora.bash
#
# This script:
# 1. Extracts version from pyproject.toml
# 2. Creates proper Python sdist tarball
# 3. Sets up RPM build environment
# 4. Builds RPM with dynamic version

set -euo pipefail

# Extract version from pyproject.toml
# Reads the line: version = "0.1.0" and extracts just the version number
VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)

if [[ -z "$VERSION" ]]; then
    echo "ERROR: Could not extract version from pyproject.toml"
    exit 1
fi

echo "==> Building talk-it-out version $VERSION"

# Clean any previous build artifacts
echo "==> Cleaning previous build artifacts..."
rm -rf dist/ build/ *.egg-info

# Create Python source distribution using PEP 517 build system
# This creates a proper sdist with all metadata (PKG-INFO, etc.)
# Use system Python (/usr/bin/python3) to ensure build module is available
echo "==> Creating source distribution..."
/usr/bin/python3 -m build --sdist

# Setup RPM build tree if it doesn't exist
if [[ ! -d ~/rpmbuild ]]; then
    echo "==> Setting up RPM build tree..."
    rpmdev-setuptree
fi

# Copy source tarball to RPM SOURCES directory
echo "==> Copying source tarball to ~/rpmbuild/SOURCES/..."
cp dist/talk_it_out-${VERSION}.tar.gz ~/rpmbuild/SOURCES/talk-it-out-${VERSION}.tar.gz

# Copy spec file to RPM SPECS directory
echo "==> Copying spec file to ~/rpmbuild/SPECS/..."
cp packaging/rpm/talk-it-out.spec ~/rpmbuild/SPECS/

# Build RPM with dynamic version override
# The -D flag defines the pypi_version macro at build time,
# overriding the hardcoded value in the spec file
echo "==> Building RPM package..."
rpmbuild -D "pypi_version ${VERSION}" -ba ~/rpmbuild/SPECS/talk-it-out.spec

echo ""
echo "==> Build complete!"
echo "    Binary RPM: ~/rpmbuild/RPMS/noarch/talk-it-out-${VERSION}-1.*.noarch.rpm"
echo "    Source RPM: ~/rpmbuild/SRPMS/talk-it-out-${VERSION}-1.*.src.rpm"
