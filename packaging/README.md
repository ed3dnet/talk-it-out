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
