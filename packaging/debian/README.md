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
