# Packaging Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create RPM and DEB packaging for talk-it-out to enable native installation on Fedora/RHEL and Debian/Ubuntu distributions.

**Architecture:** Separate RPM and DEB packaging with shared .desktop file, using modern build systems (pyproject-rpm-macros for RPM, dh-python for DEB) that auto-detect Python dependencies from pyproject.toml.

**Tech Stack:** RPM spec files, Debian packaging (control/rules/changelog), FreeDesktop .desktop specification

**Scope:** 5 phases - CI setup, directory structure, RPM packaging, Debian packaging, documentation

**Codebase verified:** 2025-01-26

---

## Phase 0: Set up GitHub Actions CI for package builds

### Task 1: Create GitHub Actions workflow for package builds

**Files:**
- Create: `.github/workflows/build-packages.yml`

**Step 1: Create workflow directory**

```bash
mkdir -p .github/workflows
```

**Step 2: Create package build workflow**

```yaml
name: Build Linux Packages

on:
  push:
    tags:
      - 'v*.*.*'
  pull_request:
    paths:
      - 'packaging/**'
      - 'pyproject.toml'
      - 'src/**'

jobs:
  build-rpm:
    name: Build RPM on Fedora
    runs-on: ubuntu-latest
    container:
      image: fedora:42
    steps:
      - uses: actions/checkout@v4

      - name: Install build tools
        run: |
          dnf install -y rpm-build rpmdevtools python3-devel
          dnf install -y pyproject-rpm-macros python3-build python3-pip

      - name: Prepare RPM build environment
        run: |
          rpmdev-setuptree
          VERSION="${{ github.ref_name }}"
          if [[ "$VERSION" == refs/pull/* ]]; then
            VERSION="0.1.0"  # Use version from pyproject.toml for PRs
          else
            VERSION="${VERSION#v}"  # Remove 'v' prefix from tags
          fi
          cp packaging/rpm/talk-it-out.spec ~/rpmbuild/SPECS/
          tar --transform="s,^,talk-it-out-${VERSION}/," \
              -czf ~/rpmbuild/SOURCES/talk-it-out-${VERSION}.tar.gz \
              --exclude=.git --exclude=.github \
              --exclude=packaging/debian .

      - name: Build RPM
        run: rpmbuild -ba ~/rpmbuild/SPECS/talk-it-out.spec

      - name: Upload RPM artifacts
        uses: actions/upload-artifact@v4
        with:
          name: rpm-fedora-42
          path: ~/rpmbuild/RPMS/noarch/*.rpm
          retention-days: 30

  build-deb:
    name: Build DEB on Ubuntu ${{ matrix.ubuntu_version }}
    runs-on: ubuntu-latest
    strategy:
      matrix:
        ubuntu_version: ['24.04', '25.10']
    container:
      image: ubuntu:${{ matrix.ubuntu_version }}
    steps:
      - uses: actions/checkout@v4

      - name: Install build tools
        run: |
          apt-get update
          apt-get install -y debhelper dh-python python3-all python3-setuptools python3-build
          # pybuild-plugin-pyproject for modern pyproject.toml support
          apt-get install -y pybuild-plugin-pyproject || true

      - name: Copy debian packaging to project root
        run: cp -r packaging/debian .

      - name: Build DEB package
        run: dpkg-buildpackage -us -uc -b

      - name: Upload DEB artifacts
        uses: actions/upload-artifact@v4
        with:
          name: deb-ubuntu-${{ matrix.ubuntu_version }}
          path: ../*.deb
          retention-days: 30

  release:
    name: Create GitHub Release
    needs: [build-rpm, build-deb]
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/v')
    permissions:
      contents: write
    steps:
      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: packages

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: packages/**/*.{rpm,deb}
          generate_release_notes: true
          draft: false
          prerelease: ${{ contains(github.ref, '-rc') || contains(github.ref, '-beta') }}
```

**Step 3: Verify workflow syntax**

Run: `cat .github/workflows/build-packages.yml`
Expected: File displays correctly

**Step 4: Commit**

```bash
git add .github/workflows/build-packages.yml
git commit -m "ci: add GitHub Actions workflow for RPM and DEB package builds"
```

---

### Task 2: Add CI documentation to packaging README

**Files:**
- Modify: `packaging/README.md`

**Step 1: Add CI section to packaging README**

Add this section after "Directory Structure":

```markdown
## Continuous Integration

GitHub Actions automatically builds packages on:
- **Pull requests**: Validates packaging changes build successfully
- **Version tags**: Builds and attaches packages to GitHub releases

**Supported platforms:**
- Fedora 42 (RPM)
- Ubuntu 24.04, 25.10 (DEB)

**To trigger a release:**
```bash
git tag v0.2.0
git push origin v0.2.0
```

Packages will be built and attached to the release at: `https://github.com/ed3dnet/talk-it-out/releases`

**Workflow file:** `.github/workflows/build-packages.yml`
```

**Step 2: Verify updated README**

Run: `git diff packaging/README.md`
Expected: Shows CI section added

**Step 3: Commit**

```bash
git add packaging/README.md
git commit -m "docs: add CI documentation to packaging README"
```

---

## Phase 1: Create packaging directory structure and .desktop file

### Task 1: Create packaging directory structure

**Files:**
- Create: `packaging/`
- Create: `packaging/rpm/`
- Create: `packaging/debian/`
- Create: `packaging/common/`

**Step 1: Create directory structure**

```bash
mkdir -p packaging/rpm packaging/debian packaging/common
```

**Step 2: Verify structure**

Run: `tree packaging -L 2`
Expected:
```
packaging
├── common
├── debian
└── rpm
```

**Step 3: Commit**

```bash
git add packaging/
git commit -m "chore: add packaging directory structure"
```

---

### Task 2: Create .desktop file for GUI mode

**Files:**
- Create: `packaging/common/talk-it-out.desktop`

**Step 1: Create .desktop file**

```desktop
[Desktop Entry]
Type=Application
Name=Talk It Out
GenericName=Voice to Text
Comment=Voice-to-text for Linux using Whisper AI
Exec=talk-it-out gui
Icon=talk-it-out
Terminal=false
Categories=Utility;AudioVideo;Audio;
Keywords=speech;voice;whisper;transcription;dictation;
StartupNotify=true
```

**Step 2: Verify .desktop file syntax**

Run: `desktop-file-validate packaging/common/talk-it-out.desktop`
Expected: No errors (command exits with 0)

**Step 3: Commit**

```bash
git add packaging/common/talk-it-out.desktop
git commit -m "feat: add .desktop file for GUI mode"
```

---

### Task 3: Create README for packaging directory

**Files:**
- Create: `packaging/README.md`

**Step 1: Create packaging README**

```markdown
# Packaging

Distribution packages for talk-it-out.

## Structure

- `common/` - Shared files across package formats (.desktop file, etc.)
- `rpm/` - RPM packaging for Fedora/RHEL
- `debian/` - DEB packaging for Debian/Ubuntu

## Building

See subdirectory READMEs for platform-specific build instructions:
- [RPM packaging](rpm/README.md)
- [Debian packaging](debian/README.md)

## Version Management

Version is managed in `pyproject.toml`. Package build scripts read from there.
```

**Step 2: Verify README**

Run: `cat packaging/README.md`
Expected: File content displays correctly

**Step 3: Commit**

```bash
git add packaging/README.md
git commit -m "docs: add packaging README"
```

---

## Phase 2: Create RPM spec file with system dependencies

### Task 1: Create RPM spec file

**Files:**
- Create: `packaging/rpm/talk-it-out.spec`

**Step 1: Create spec file with metadata and dependencies**

```spec
# pattern: Imperative Shell (handles packaging/installation)
%global pypi_name talk-it-out
%global pypi_version 0.1.0

Name:           %{pypi_name}
Version:        %{pypi_version}
Release:        1%{?dist}
Summary:        Voice-to-text for Linux using Whisper AI

License:        GPL-3.0-or-later
URL:            https://github.com/ed3dnet/talk-it-out
Source0:        %{pypi_name}-%{version}.tar.gz

BuildArch:      noarch

# Build dependencies
BuildRequires:  python3-devel >= 3.13
BuildRequires:  python3-pip
BuildRequires:  python3-setuptools
BuildRequires:  pyproject-rpm-macros

# System library build dependencies
BuildRequires:  ffmpeg-free-devel
BuildRequires:  portaudio-devel

# Runtime system dependencies
Requires:       wl-clipboard
Requires:       ydotool >= 1.0
Requires:       ffmpeg-free
Requires:       portaudio
Requires:       python3 >= 3.13

# Python dependencies automatically detected via %pyproject_buildrequires
%{?python_enable_dependency_generator}

%description
Voice-to-text for Linux using Whisper AI. Press a keyboard shortcut, speak,
release to paste. Supports both CLI and GUI modes with Qt6 system tray
integration.

%prep
%autosetup -n %{pypi_name}-%{version}

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files talk_it_out

# Install .desktop file
install -D -m 0644 packaging/common/talk-it-out.desktop \
    %{buildroot}%{_datadir}/applications/talk-it-out.desktop

%check
%pyproject_check_import

%files -f %{pyproject_files}
%license LICENSE
%doc README.md
%{_bindir}/talk-it-out
%{_datadir}/applications/talk-it-out.desktop

%changelog
* Sun Jan 26 2025 Ed Ropple <ed@edropple.com> - 0.1.0-1
- Initial RPM release
- CLI and GUI modes for voice-to-text transcription
- Whisper AI integration with GPU acceleration support
- Wayland native with wl-clipboard and ydotool
```

**Step 2: Verify spec file syntax**

Run: `rpmspec -P packaging/rpm/talk-it-out.spec > /dev/null`
Expected: No syntax errors (exit code 0)

Note: This may fail if rpmspec is not installed. That's expected on non-RPM systems.

**Step 3: Commit**

```bash
git add packaging/rpm/talk-it-out.spec
git commit -m "feat: add RPM spec file for Fedora/RHEL packaging"
```

---

### Task 2: Create RPM build README

**Files:**
- Create: `packaging/rpm/README.md`

**Step 1: Create RPM packaging documentation**

```markdown
# RPM Packaging (Fedora/RHEL)

Build RPM packages for Fedora and RHEL-based distributions.

## Prerequisites

**Fedora/RHEL:**
```bash
sudo dnf install rpm-build rpmdevtools python3-devel pyproject-rpm-macros
sudo dnf install ffmpeg-free-devel portaudio-devel
```

## Building from Source

### 1. Create source tarball

From project root:

```bash
python3 -m build --sdist
cp dist/talk-it-out-0.1.0.tar.gz ~/rpmbuild/SOURCES/
```

### 2. Build RPM

```bash
rpmbuild -ba packaging/rpm/talk-it-out.spec
```

Output:
- SRPM: `~/rpmbuild/SRPMS/talk-it-out-0.1.0-1.*.src.rpm`
- RPM: `~/rpmbuild/RPMS/noarch/talk-it-out-0.1.0-1.*.noarch.rpm`

### 3. Install

```bash
sudo dnf install ~/rpmbuild/RPMS/noarch/talk-it-out-0.1.0-1.*.noarch.rpm
```

## Testing the Package

After installation:

```bash
# Test CLI mode
talk-it-out run --help

# Test GUI mode
talk-it-out gui

# Verify .desktop file installed
desktop-file-validate /usr/share/applications/talk-it-out.desktop
```

## Version Updates

1. Update version in `pyproject.toml`
2. Update `%global pypi_version` in spec file
3. Add entry to `%changelog` section
4. Rebuild

## System Dependencies

The spec file requires:
- `wl-clipboard` - Wayland clipboard integration
- `ydotool` - Keyboard input simulation
- `ffmpeg-free` - Audio codec support (patent-safe version)
- `portaudio` - Audio input capture

Python dependencies are automatically detected from `pyproject.toml`.
```

**Step 2: Verify README**

Run: `cat packaging/rpm/README.md`
Expected: File content displays correctly

**Step 3: Commit**

```bash
git add packaging/rpm/README.md
git commit -m "docs: add RPM packaging build instructions"
```

---

## Phase 3: Create Debian packaging files

### Task 1: Create debian/control file

**Files:**
- Create: `packaging/debian/control`

**Step 1: Create control file with metadata and dependencies**

```
Source: talk-it-out
Section: utils
Priority: optional
Maintainer: Ed Ropple <ed@edropple.com>
Build-Depends: debhelper-compat (= 13),
               dh-python,
               python3-all (>= 3.13),
               python3-setuptools,
               python3-pip,
               wl-clipboard,
               ydotool,
               libavformat-dev,
               libavcodec-dev,
               libavutil-dev,
               portaudio19-dev
Standards-Version: 4.6.0
Homepage: https://github.com/ed3dnet/talk-it-out

Package: talk-it-out
Architecture: all
Depends: ${python3:Depends},
         ${shlibs:Depends},
         ${misc:Depends},
         wl-clipboard,
         ydotool,
         ffmpeg,
         portaudio19,
         python3 (>= 3.13)
Description: Voice-to-text for Linux using Whisper AI
 Voice-to-text for Linux using Whisper AI. Press a keyboard shortcut,
 speak, release to paste.
 .
 Features:
  - Two modes: CLI (terminal) or GUI (system tray with visual indicator)
  - Whisper AI transcription: Offline, private speech recognition
  - Wayland native: Built for modern Linux desktop
  - Configurable: Choose AI models, languages, keyboard shortcuts
  - GPU accelerated: Automatic CUDA detection with CPU fallback
```

**Step 2: Verify control file syntax**

Run: `cat packaging/debian/control`
Expected: File displays correctly with proper formatting

**Step 3: Commit**

```bash
git add packaging/debian/control
git commit -m "feat: add Debian control file"
```

---

### Task 2: Create debian/rules file

**Files:**
- Create: `packaging/debian/rules`

**Step 1: Create rules file for pybuild**

```makefile
#!/usr/bin/make -f

%:
	dh $@ --with python3 --buildsystem=pybuild

override_dh_auto_install:
	dh_auto_install
	# Install .desktop file
	install -D -m 0644 packaging/common/talk-it-out.desktop \
		debian/talk-it-out/usr/share/applications/talk-it-out.desktop
```

**Step 2: Make rules executable**

Run: `chmod +x packaging/debian/rules`
Expected: File becomes executable

**Step 3: Commit**

```bash
git add packaging/debian/rules
git commit -m "feat: add Debian rules file"
```

---

### Task 3: Create debian/changelog

**Files:**
- Create: `packaging/debian/changelog`

**Step 1: Create changelog with initial release**

```
talk-it-out (0.1.0-1) unstable; urgency=low

  * Initial Debian release
  * CLI and GUI modes for voice-to-text transcription
  * Whisper AI integration with GPU acceleration support
  * Wayland native with wl-clipboard and ydotool

 -- Ed Ropple <ed@edropple.com>  Sun, 26 Jan 2025 00:00:00 +0000
```

**Step 2: Verify changelog format**

Run: `dpkg-parsechangelog -l packaging/debian/changelog`
Expected: Parses successfully and outputs version info

Note: This may fail if dpkg-dev is not installed. That's expected on non-Debian systems.

**Step 3: Commit**

```bash
git add packaging/debian/changelog
git commit -m "feat: add Debian changelog"
```

---

### Task 4: Create debian/compat file

**Files:**
- Create: `packaging/debian/compat`

**Step 1: Create compat file**

```
13
```

**Step 2: Verify file**

Run: `cat packaging/debian/compat`
Expected: Outputs "13"

**Step 3: Commit**

```bash
git add packaging/debian/compat
git commit -m "feat: add Debian compat level 13"
```

---

### Task 5: Create debian/copyright file

**Files:**
- Create: `packaging/debian/copyright`

**Step 1: Create copyright file**

```
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: talk-it-out
Upstream-Contact: Ed Ropple <ed@edropple.com>
Source: https://github.com/ed3dnet/talk-it-out

Files: *
Copyright: 2025 Ed Ropple <ed@edropple.com>
License: GPL-3.0-or-later

License: GPL-3.0-or-later
 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 .
 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 GNU General Public License for more details.
 .
 You should have received a copy of the GNU General Public License
 along with this program. If not, see <https://www.gnu.org/licenses/>.
 .
 On Debian systems, the complete text of the GNU General Public License
 version 3 can be found in "/usr/share/common-licenses/GPL-3".
```

**Step 2: Verify file**

Run: `cat packaging/debian/copyright`
Expected: File displays correctly

**Step 3: Commit**

```bash
git add packaging/debian/copyright
git commit -m "feat: add Debian copyright file"
```

---

### Task 6: Create Debian build README

**Files:**
- Create: `packaging/debian/README.md`

**Step 1: Create Debian packaging documentation**

```markdown
# Debian Packaging (Debian/Ubuntu)

Build DEB packages for Debian and Ubuntu-based distributions.

## Prerequisites

**Debian/Ubuntu:**
```bash
sudo apt install debhelper dh-python python3-all python3-setuptools python3-pip
sudo apt install wl-clipboard ydotool libavformat-dev libavcodec-dev libavutil-dev portaudio19-dev
```

## Building from Source

### 1. Prepare source directory

From project root:

```bash
# Copy debian packaging files to project root
cp -r packaging/debian .

# Build source package
dpkg-buildpackage -us -uc -S
```

### 2. Build DEB package

```bash
dpkg-buildpackage -us -uc -b
```

Output: `../talk-it-out_0.1.0-1_all.deb`

### 3. Install

```bash
sudo dpkg -i ../talk-it-out_0.1.0-1_all.deb
sudo apt-get install -f  # Install dependencies if needed
```

## Testing the Package

After installation:

```bash
# Test CLI mode
talk-it-out run --help

# Test GUI mode
talk-it-out gui

# Verify .desktop file installed
desktop-file-validate /usr/share/applications/talk-it-out.desktop
```

## Version Updates

1. Update version in `pyproject.toml`
2. Add new entry to `debian/changelog` using `dch` tool:
   ```bash
   dch --newversion 0.2.0-1 "Release version 0.2.0"
   ```
3. Rebuild

## System Dependencies

The control file requires:
- `wl-clipboard` - Wayland clipboard integration
- `ydotool` - Keyboard input simulation
- `ffmpeg` - Audio codec support
- `portaudio19` - Audio input capture

Python dependencies are automatically detected via dh-python from `pyproject.toml`.
```

**Step 2: Verify README**

Run: `cat packaging/debian/README.md`
Expected: File content displays correctly

**Step 3: Commit**

```bash
git add packaging/debian/README.md
git commit -m "docs: add Debian packaging build instructions"
```

---

## Phase 4: Enhance packaging documentation

### Task 1: Enhance packaging README with comprehensive information

**Files:**
- Modify: `packaging/README.md`

**Step 1: Replace README with comprehensive documentation**

Replace the existing content with:

```markdown
# Packaging

Distribution packages for talk-it-out supporting RPM (Fedora/RHEL) and DEB (Debian/Ubuntu) formats.

## Directory Structure

```
packaging/
├── README.md                  # This file
├── common/
│   └── talk-it-out.desktop   # Shared .desktop file (FreeDesktop standard)
├── rpm/
│   ├── talk-it-out.spec      # RPM spec file
│   └── README.md             # RPM build instructions
└── debian/
    ├── control               # Package metadata and dependencies
    ├── rules                 # Build rules (pybuild)
    ├── changelog             # Debian changelog format
    ├── compat                # Debhelper compatibility level (13)
    ├── copyright             # Machine-readable copyright
    └── README.md             # DEB build instructions
```

## Overview

### RPM Packaging (Fedora/RHEL)

- **Build system**: pyproject-rpm-macros (modern Python packaging)
- **Auto-detection**: Python dependencies from pyproject.toml via %pyproject_buildrequires
- **System deps**: wl-clipboard, ydotool, ffmpeg-free, portaudio
- **Architecture**: noarch (pure Python)
- **Details**: See [rpm/README.md](rpm/README.md)

### Debian Packaging (Debian/Ubuntu)

- **Build system**: dh-python + pybuild (standard Debian Python packaging)
- **Auto-detection**: Python dependencies via ${python3:Depends}
- **System deps**: wl-clipboard, ydotool, ffmpeg, portaudio19
- **Architecture**: all (pure Python)
- **Details**: See [debian/README.md](debian/README.md)

### Shared Components

- **.desktop file** in `common/`: Used by both RPM and DEB for application launcher integration
- **Version source of truth**: `pyproject.toml` [project.version]
- **License**: GPLv3+ (declared in both package formats)

## Building

See format-specific READMEs for detailed build instructions:
- [RPM Build Instructions](rpm/README.md)
- [Debian Build Instructions](debian/README.md)

## Testing Packages Locally

### Test RPM Package

After building:

```bash
# Install
sudo dnf install ~/rpmbuild/RPMS/noarch/talk-it-out-0.1.0-1.*.noarch.rpm

# Verify installation
which talk-it-out
talk-it-out --help

# Test CLI mode
talk-it-out run --help

# Test GUI mode (requires X11/Wayland session)
talk-it-out gui

# Verify .desktop file
desktop-file-validate /usr/share/applications/talk-it-out.desktop
ls -l /usr/share/applications/talk-it-out.desktop

# Check system dependencies
rpm -q wl-clipboard ydotool ffmpeg-free portaudio

# Uninstall
sudo dnf remove talk-it-out
```

### Test DEB Package

After building:

```bash
# Install
sudo dpkg -i ../talk-it-out_0.1.0-1_all.deb
sudo apt-get install -f  # Install any missing dependencies

# Verify installation
which talk-it-out
talk-it-out --help

# Test CLI mode
talk-it-out run --help

# Test GUI mode (requires X11/Wayland session)
talk-it-out gui

# Verify .desktop file
desktop-file-validate /usr/share/applications/talk-it-out.desktop
ls -l /usr/share/applications/talk-it-out.desktop

# Check system dependencies
dpkg -l wl-clipboard ydotool ffmpeg portaudio19

# Uninstall
sudo apt-get remove talk-it-out
```

## Version Management

Version is managed in `pyproject.toml` as the single source of truth.

**When releasing a new version:**

1. **Update pyproject.toml:**
   ```toml
   [project]
   version = "0.2.0"
   ```

2. **Update RPM spec file** (`packaging/rpm/talk-it-out.spec`):
   ```spec
   %global pypi_version 0.2.0

   %changelog
   * Mon Feb 03 2025 Ed Ropple <ed@edropple.com> - 0.2.0-1
   - Release version 0.2.0
   - [List specific changes]
   ```

3. **Update Debian changelog:**
   ```bash
   cd packaging
   dch --newversion 0.2.0-1 "Release version 0.2.0"
   # Edit debian/changelog to add specific changes
   ```

4. **Rebuild both packages** following format-specific instructions

## Dependencies

### System Dependencies

Both package formats require these system libraries:

| Fedora/RHEL | Debian/Ubuntu | Purpose |
|-------------|---------------|---------|
| wl-clipboard | wl-clipboard | Wayland clipboard integration |
| ydotool | ydotool | Keyboard input simulation |
| ffmpeg-free | ffmpeg | Audio codec support |
| portaudio | portaudio19 | Audio input capture |

### Python Dependencies

Auto-detected from `pyproject.toml` [project.dependencies]:
- typer, structlog, tomli-w, evdev
- numpy, scipy, sounddevice
- faster-whisper
- pyqt6

## Common Issues

### RPM: Missing build dependencies

```bash
sudo dnf install rpm-build rpmdevtools python3-devel pyproject-rpm-macros
sudo dnf install ffmpeg-free-devel portaudio-devel
```

### DEB: Missing build dependencies

```bash
sudo apt install debhelper dh-python python3-all python3-setuptools python3-pip
sudo apt install wl-clipboard ydotool libavformat-dev libavcodec-dev libavutil-dev portaudio19-dev
```

### .desktop file validation fails

Verify FreeDesktop specification compliance:
```bash
desktop-file-validate packaging/common/talk-it-out.desktop
```

### Python dependencies not auto-detected

Ensure `pyproject.toml` has populated `[project.dependencies]` section.

## Future Distribution Channels

### COPR (Fedora Community Packages)

For wider Fedora/RHEL distribution:
- Automated builds on Fedora releases
- User installation: `dnf copr enable <user>/talk-it-out`

### PPA (Ubuntu Personal Package Archive)

For wider Ubuntu distribution:
- Launchpad-hosted builds
- User installation: `add-apt-repository ppa:<user>/talk-it-out`

### Flatpak

Potential cross-distro distribution:
- **Current blocker**: wl-clipboard access in sandbox requires portal configuration
- **Benefit**: Cross-distro, handles all dependencies including Python runtime
- Not prioritized due to clipboard integration complexity
```

**Step 2: Verify enhanced README**

Run: `cat packaging/README.md`
Expected: File displays correctly with all sections

**Step 3: Commit**

```bash
git add packaging/README.md
git commit -m "docs: enhance packaging README with comprehensive documentation"
```

---
