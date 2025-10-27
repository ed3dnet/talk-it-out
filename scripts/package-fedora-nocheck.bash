#!/usr/bin/env bash
# pattern: Imperative Shell (orchestrates RPM packaging)
#
# Purpose: Build RPM package WITHOUT dependency checking (for local testing)
# Usage: bash scripts/package-fedora-nocheck.bash
#
# WARNING: This skips %generate_buildrequires phase. Only use for local testing.
# CI should use the normal package-fedora.bash script.

set -euo pipefail

# Extract version from pyproject.toml
VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)

if [[ -z "$VERSION" ]]; then
    echo "ERROR: Could not extract version from pyproject.toml"
    exit 1
fi

echo "==> Building talk-it-out version $VERSION (NO DEPENDENCY CHECK)"

# Clean any previous build artifacts
echo "==> Cleaning previous build artifacts..."
rm -rf dist/ build/ *.egg-info

# Create Python source distribution using PEP 517 build system
echo "==> Creating source distribution..."
/usr/bin/python3 -m build --sdist

# Setup RPM build tree if it doesn't exist
if [[ ! -d ~/rpmbuild ]]; then
    echo "==> Setting up RPM build tree..."
    rpmdev-setuptree
fi

# Copy source tarball to RPM SOURCES directory
echo "==> Copying source tarball to ~/rpmbuild/SOURCES/..."
cp dist/talk_it_out-${VERSION}.tar.gz ~/rpmbuild/SOURCES/talk_it_out-${VERSION}.tar.gz

# Copy spec file to RPM SPECS directory
echo "==> Copying spec file to ~/rpmbuild/SPECS/..."
cp packaging/rpm/talk-it-out.spec ~/rpmbuild/SPECS/

# Build RPM with dynamic version override, skipping %check phase
# This bypasses the two-pass dependency resolution for local testing
echo "==> Building RPM package (skipping %generate_buildrequires)..."
rpmbuild -D "pypi_version ${VERSION}" --nocheck --nodeps -ba ~/rpmbuild/SPECS/talk-it-out.spec

echo ""
echo "==> Build complete!"
echo "    Binary RPM: ~/rpmbuild/RPMS/noarch/talk-it-out-${VERSION}-1.*.noarch.rpm"
echo "    Source RPM: ~/rpmbuild/SRPMS/talk-it-out-${VERSION}-1.*.src.rpm"
echo ""
echo "WARNING: This RPM was built without dependency checking."
echo "It may be missing dependencies. Use only for testing!"
