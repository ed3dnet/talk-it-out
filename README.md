# talk-it-out

Voice-to-text utility for Linux/KDE Plasma using Whisper.

## Status

**Phase 1 (CLI Framework): Complete**

The CLI application framework is implemented with:
- Configuration management (TOML)
- Structured logging (structlog)
- Signal handling with cleanup timeout
- Permission checks for input group
- Subcommands: `run`, `config-edit`

**Phase 2 (Keyboard Monitoring): Complete**

Keyboard event monitoring is implemented with:
- Multi-device keyboard monitoring via evdev
- Key combination detection with explicit evdev key names
- Per-device state isolation (paired press/release events)
- Queue-based event emission
- Graceful error handling (device disconnection, permissions)

**Phase 3 (Audio Recording): Complete**

Audio recording is implemented with:
- PortAudio dependency detection with helpful install messages
- Microphone recording via sounddevice library
- WAV file output to temporary location (`/tmp`)
- Integration with keyboard combo events (press to start, release to stop)
- Audio validation (minimum duration, format checks)
- Graceful error handling for all audio failures
- Manual testing guide in `docs/MANUAL_TESTING.md`

Audio is recorded at 16kHz mono (Whisper-compatible format).

**Phase 4 (Whisper Transcription): Complete**

Whisper transcription is integrated:
- faster-whisper library integration
- GPU/CPU auto-detection with fallback
- Configurable model size, language, and parameters
- Audio transcription pipeline with logging
- Comprehensive unit tests for all components
- Debug audio saving toggle for verification

**Next:** Phase 5 will add clipboard integration for text pasting.

## Installation

### Prerequisites

**System packages:**

**Output dependencies (wl-clip-simplepaste strategy):**

```bash
# Fedora/RHEL
sudo dnf install wl-clipboard ydotool
sudo systemctl enable --now ydotoold

# Debian/Ubuntu
sudo apt install wl-clipboard ydotool
sudo systemctl enable --now ydotoold

# Arch
sudo pacman -S wl-clipboard
yay -S ydotool-git  # AUR
sudo systemctl enable --now ydotoold
```

Required for clipboard operations and keystroke injection on Wayland.

**Note:** ydotoold daemon must be running. Verify with `systemctl status ydotoold`.

**Audio processing dependencies:**

```bash
# Fedora/RHEL
sudo dnf install ffmpeg-free-devel

# Debian/Ubuntu
sudo apt install libavformat-dev libavcodec-dev libavutil-dev

# Arch
sudo pacman -S ffmpeg
```

Required for faster-whisper's audio processing capabilities (libavformat, libavcodec, libavutil).

**User permissions:**

```bash
# Add user to input group (required for keyboard monitoring)
sudo usermod -a -G input $USER
# Log out and log back in for group membership to take effect
```

### Development Setup

```bash
# Install dependencies
uv pip install -e .

# Run application
python -m talk_it_out.main run

# Or use installed command
talk-it-out run
```

## Usage

### CLI Mode (default)

```bash
talk-it-out run
```

Runs in terminal with keyboard shortcuts for voice-to-text.

**Options:**

```bash
# Override log level
talk-it-out run --log-level DEBUG

# Use custom config
talk-it-out run --config /path/to/config.toml
```

### GUI Mode

```bash
talk-it-out gui
```

Runs with visual indicator and system tray:

- **Floating indicator**: Shows workflow state
  - Red pill: Recording (brightness varies with voice volume)
  - Blue pill (pulsing): Transcribing
  - Hidden: Idle

- **System tray**: Right-click icon → Quit to exit

- **Desktop notifications**: Errors shown as notifications

**Requirements:**
- Wayland compositor (KDE Plasma, GNOME, etc.)
- D-Bus session bus for notifications

**Platform compatibility:**
- Primary: KDE Plasma Wayland
- Works on: GNOME Wayland, other Wayland compositors
- X11: Works with `QT_QPA_PLATFORM=xcb`

### Edit Configuration

```bash
# Opens ~/.config/talk-it-out/config.toml in $EDITOR
talk-it-out config-edit
```

## Whisper Transcription

Audio recorded via keyboard combo is automatically transcribed using faster-whisper.

**First Run Setup:**
- On first startup, the Whisper model will download (~809MB for turbo)
- Download happens once, subsequent runs use cached model
- Requires internet connection for initial download only

**Model Selection:**

Edit `~/.config/talk-it-out/config.toml`:

- `tiny` - Fastest, lowest accuracy (~140MB)
- `base` - Fast, reasonable accuracy (~140MB)
- `small` - Good balance (~466MB)
- `turbo` - Best balance, recommended (~809MB) - **Default**
- `medium` - Higher accuracy, slower (~1.5GB)
- `large` - Best accuracy, slowest (~3GB)

**GPU Acceleration:**

If CUDA is available, transcription automatically uses GPU with float16 precision. CPU fallback uses int8 for memory efficiency.

Check device selection:
```bash
uv run python -m talk_it_out.main run --log-level INFO
# Look for: "transcriber_initialized" log with device info
```

**Debug Audio Saving:**

Enable WAV file saving for verification:
```toml
[whisper]
save_debug_audio = true
```

WAV files saved to `/tmp/recording_*.wav` for playback with `aplay` or `ffplay`.

## Configuration

Config location: `~/.config/talk-it-out/config.toml`

```toml
[keys.combos]
record_for_paste = [
    ["KEY_LEFTMETA", "KEY_LEFTALT"],
]

[audio]
sample_rate = 16000
channels = 1
device = ""

[whisper]
model = "turbo"              # Model size: tiny, base, small, medium, large, turbo
language = "en"              # Language code (e.g., "en", "es", "fr") or "" for auto-detect
device = "auto"              # Device: "auto", "cuda", "cpu"
compute_type = "auto"        # Precision: "auto", "int8", "float16", "float32"
beam_size = 5                # Search breadth (1-10, higher = better but slower)
vad_filter = true            # Voice activity detection (skip silence)
save_debug_audio = false     # Save WAV files to /tmp for debugging

[output]
strategy = "wl-clip-simplepaste"

# Optional: Advanced wl-clip settings (defaults shown)
# [output.wl-clip]
# targets = ["clipboard", "primary"]  # Which clipboards to populate
# ydotool_socket = ""  # Custom socket path (empty = use $YDOTOOL_SOCKET or default)

[logging]
level = "INFO"  # DEBUG, INFO, WARNING, ERROR
```

### Configuration Overrides

The config file uses a **two-layer system**: your config file contains only overrides, and internal defaults fill in the rest.

**Minimal config (recommended):**
```toml
[keys.combos]
record_for_paste = [["KEY_LEFTMETA", "KEY_LEFTALT"]]

[whisper]
model = "turbo"
language = "en"

[output]
strategy = "wl-clip-simplepaste"
```

**What you can override:**
- `[whisper]`: Only specify `model` and `language` if you want different defaults
- `[output.wl-clip]`: Only needed if you want to customize clipboard targets
- `[audio]`, `[logging]`: Omit entirely to use defaults

Advanced settings (beam_size, vad_filter, compute_type) have working defaults via internal config merge.

### Key Combinations

Key combinations use explicit evdev key names. Multiple alternatives can be defined:

```toml
[keys.combos]
record_for_paste = [
    ["KEY_LEFTMETA", "KEY_LEFTALT"],
    ["KEY_RIGHTMETA", "KEY_RIGHTALT"],
]
quick_note = [
    ["KEY_LEFTCTRL", "KEY_N"],
]
```

Valid key names come from `evdev.ecodes` (e.g., `KEY_LEFTMETA`, `KEY_LEFTALT`, `KEY_LEFTCTRL`, `KEY_LEFTSHIFT`).

Each combo is detected when all keys in any alternative are pressed together on the same device.

## Keyboard Monitoring

The application monitors all keyboard input devices for configured key combinations.

### How It Works

1. **Device Scanning:** On startup, scans `/dev/input/event*` for devices with keyboard capability (EV_KEY)
2. **Event Processing:** Monitors all keyboards simultaneously using efficient `select()` system call
3. **Per-Device State:** Each keyboard maintains independent state for proper press/release pairing
4. **Queue-Based Events:** Combo activations are emitted to a queue for asynchronous processing

### Requirements

- User must be in `input` group: `sudo usermod -aG input $USER`
- Reboot required after adding to group
- At least one keyboard device with EV_KEY capability

### Troubleshooting

**No combo events detected:**
- Verify user in input group: `groups | grep input`
- Check devices found: Run with `--log-level DEBUG`
- Verify config syntax: `uv run python -m talk_it_out.main config-edit`

**Permission denied errors:**
- Ensure input group membership
- Reboot after group change
- Check `/dev/input/event*` permissions

**Device not found:**
- Check physical keyboard is connected
- Verify device has EV_KEY capability: `evtest` (install with `sudo dnf install evtest`)
- Look for "keyboard_device_opened" logs at DEBUG level

**Paste not working:**
- Verify dependencies installed: `which wl-copy wl-paste ydotool`
- Check ydotoold daemon: `systemctl status ydotoold` (should be active)
- Test clipboard manually:
  ```bash
  echo "test" | wl-copy
  wl-paste  # Should output "test"
  ```
- Test ydotool manually: `ydotool key 28:1 28:0` (should send Enter key)
- Check logs with `--log-level DEBUG` for detailed paste operation info
- Some applications expect different paste shortcuts - Shift+Insert is most compatible

**Clipboard targets:**
- If paste doesn't work in your application, try different targets in config:
  ```toml
  [output.wl-clip]
  targets = ["clipboard"]  # or ["primary"] or both
  ```
- GNOME Terminal and some terminals prefer `primary` selection

**ydotool socket issues:**
- Check socket exists: `ls -l /run/ydotool/socket` (or value of $YDOTOOL_SOCKET)
- Verify permissions: Socket must be readable/writable by your user
- Custom socket in config:
  ```toml
  [output.wl-clip]
  ydotool_socket = "/path/to/custom/socket"
  ```

### Manual Testing

See [`tests/manual/CHECKLIST.md`](tests/manual/CHECKLIST.md) for comprehensive test procedures covering:
- Basic combo activation
- Press/release event pairing
- Multiple rapid presses
- Clean shutdown
- Multiple keyboards (if available)
- Invalid config detection
- Debug logging verification

## Development

### Run Tests

```bash
# Unit tests
pytest tests/framework/ -v

# Integration tests (CLI framework)
./tests/integration/test_cli_framework.sh

# Output tests (clipboard tests run single-threaded)
pytest tests/output/ -v

# Clipboard tests only (must run single-threaded to avoid race conditions)
pytest -m clipboard -n 0 -v
```

**Note:** Clipboard tests use real wl-clipboard and must run single-threaded (`-n 0`) to avoid race conditions on global clipboard state.

### Project Structure

```
src/talk_it_out/
   main.py                    # Typer CLI app
   framework/
      config.py              # Configuration management
      logging_setup.py       # Logging configuration
      permissions.py         # Permission checks
      signals.py             # Signal handling
   commands/
       config_edit.py         # Config edit command
```

## License

[To be determined]
