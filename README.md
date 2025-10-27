# talk-it-out

Voice-to-text for Linux using Whisper AI. Press a keyboard shortcut, speak, release to paste.

## Features

- **Two modes**: CLI (terminal) or GUI (system tray with visual indicator)
- **Whisper AI transcription**: Offline, private speech recognition
- **Wayland native**: Built for modern Linux desktop (KDE Plasma, GNOME, etc.)
- **Configurable**: Choose AI models, languages, keyboard shortcuts
- **GPU accelerated**: Automatic CUDA detection with CPU fallback

## Installation

### System Requirements

**Required packages:**

```bash
# Fedora/RHEL
sudo dnf install wl-clipboard ydotool ffmpeg-free-devel
sudo systemctl enable --now ydotoold

# Debian/Ubuntu
sudo apt install wl-clipboard ydotool libavformat-dev libavcodec-dev libavutil-dev
sudo systemctl enable --now ydotoold

# Arch
sudo pacman -S wl-clipboard ffmpeg
yay -S ydotool-git  # AUR
sudo systemctl enable --now ydotoold
```

**User permissions:**

```bash
# Required for keyboard monitoring
sudo usermod -a -G input $USER
```

**Log out and log back in** for group membership to take effect.

### Installing talk-it-out

**From package (recommended):**

```bash
# Fedora
sudo dnf install ./talk-it-out-0.1.0-1.x86_64.rpm

# Ubuntu/Debian
sudo apt install ./talk-it-out_0.1.0_amd64.deb
```

**From PyPI:**

```bash
# Install with uv (recommended)
uv pip install talk-it-out

# Or with pip
pip install talk-it-out
```

### GPU Acceleration (Optional)

By default, talk-it-out uses CPU for transcription. For faster processing with NVIDIA GPUs:

**Requirements:**
- NVIDIA GPU with CUDA support
- CUDA 12.x
- cuBLAS for CUDA 12
- cuDNN 9 for CUDA 12

**Installation options:**

1. **Docker** (easiest):
   ```bash
   docker run --gpus all nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04
   ```

2. **pip packages** (Linux):
   ```bash
   pip install nvidia-cublas-cu12 nvidia-cudnn-cu12==9.*
   export LD_LIBRARY_PATH=`python3 -c 'import nvidia.cublas.lib; import nvidia.cudnn.lib; print(f"{os.path.dirname(nvidia.cublas.lib.__file__)}:{os.path.dirname(nvidia.cudnn.lib.__file__)}")'`
   ```

3. **Manual install**: Follow [NVIDIA's official installation guide](https://developer.nvidia.com/cuda-downloads)

**Configuration:**
```toml
[whisper]
device = "cuda"  # Force CUDA (auto-detects by default)
```

If CUDA libraries are not found, talk-it-out automatically falls back to CPU.

## Usage

### GUI Mode (Recommended)

```bash
talk-it-out gui
```

Shows a visual indicator and system tray icon:

- **Red indicator**: Recording (brightness shows voice volume)
- **Blue pulsing indicator**: Transcribing
- **Hidden**: Idle
- **System tray**: Right-click to quit
- **Notifications**: Errors shown as desktop notifications

**Default shortcut**: Meta+Alt (hold to record, release to transcribe and paste)

### CLI Mode

```bash
talk-it-out run
```

Runs in terminal with the same keyboard shortcuts.

### First Run

On first startup, Whisper will download the AI model (~809MB for default "turbo" model). This happens once and requires internet connection. Subsequent runs use the cached model offline.

## Configuration

Config file location: `~/.config/talk-it-out/config.toml`

### Quick Setup

Edit configuration:
```bash
talk-it-out config-edit
```

Minimal configuration example:
```toml
[keys.combos]
record_for_paste = [["KEY_LEFTMETA", "KEY_LEFTALT"]]

[whisper]
model = "turbo"      # tiny, base, small, turbo, medium, large
language = "en"      # Language code or "" for auto-detect

[output]
strategy = "wl-clip-simplepaste"
```

### Keyboard Shortcuts

Define shortcuts using evdev key names:

```toml
[keys.combos]
record_for_paste = [
    ["KEY_LEFTMETA", "KEY_LEFTALT"],    # Left Meta + Alt
    ["KEY_RIGHTMETA", "KEY_RIGHTALT"],  # Right Meta + Alt
]
```

Common key names: `KEY_LEFTMETA`, `KEY_LEFTALT`, `KEY_LEFTCTRL`, `KEY_LEFTSHIFT`

### Whisper Models

Choose model size in config (tradeoff between speed and accuracy):

- `tiny` - Fastest, lowest accuracy (~140MB)
- `base` - Fast, reasonable accuracy (~140MB)
- `small` - Good balance (~466MB)
- `turbo` - Best balance, **recommended** (~809MB)
- `medium` - Higher accuracy, slower (~1.5GB)
- `large` - Best accuracy, slowest (~3GB)

### Advanced Settings

```toml
[whisper]
model = "turbo"
language = "en"              # Language code or "" for auto-detect
device = "auto"              # "auto", "cuda", or "cpu"
compute_type = "auto"        # "auto", "int8", "float16", "float32"
beam_size = 5                # Search quality (1-10, higher = better but slower)
vad_filter = true            # Skip silence during transcription

[output.wl-clip]
targets = ["clipboard", "primary"]  # Which clipboards to populate
ydotool_socket = ""                 # Custom socket path (usually auto-detected)

[audio]
sample_rate = 16000
channels = 1
device = ""                  # Empty = default microphone

[logging]
level = "INFO"               # DEBUG, INFO, WARNING, ERROR
```

## Troubleshooting

### No combo events detected

- Verify input group membership: `groups | grep input`
- Reboot after adding to input group
- Check config syntax: `talk-it-out config-edit`

### Permission errors

- Ensure you're in the `input` group
- Reboot required after adding to group
- Check `/dev/input/event*` permissions

### Paste not working

**Verify dependencies:**
```bash
which wl-copy wl-paste ydotool
systemctl status ydotoold  # Should show "active (running)"
```

**Test clipboard manually:**
```bash
echo "test" | wl-copy
wl-paste  # Should output "test"
```

**Test ydotool:**
```bash
ydotool key 28:1 28:0  # Should send Enter key
```

**If paste still doesn't work:**

Some applications require different clipboard targets. Try:
```toml
[output.wl-clip]
targets = ["clipboard"]  # or ["primary"]
```

GNOME Terminal and some terminals prefer `primary` selection.

### Model download fails

First run requires internet to download Whisper model. If download fails:

1. Check internet connection
2. Verify firewall allows HTTPS to huggingface.co
3. For corporate networks, check proxy settings

**Python 3.13 users on Fedora 42:**
If you see SSL errors during model download, this is a known issue with Python 3.13 + OpenSSL 3.5. The application includes a workaround that should resolve this automatically.

### ydotool socket issues

Check socket exists and is accessible:
```bash
ls -l /run/ydotool/socket
# or
ls -l $YDOTOOL_SOCKET
```

If socket is in a different location, configure it:
```toml
[output.wl-clip]
ydotool_socket = "/path/to/socket"
```

## Platform Compatibility

**Primary support:**
- KDE Plasma Wayland
- GNOME Wayland
- Other Wayland compositors

**Requirements:**
- Wayland compositor
- D-Bus session bus (for notifications in GUI mode)

**X11 support:**
- Works with `QT_QPA_PLATFORM=xcb` environment variable

## License

This project is licensed under the GNU General Public License v3.0 or later (GPLv3+).

See [LICENSE](LICENSE) file for details.

Copyright (C) 2025 Ed Ropple

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
