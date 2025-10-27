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
