# Audio Recording Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add audio recording capability triggered by keyboard combos, saving WAV files for manual verification

**Architecture:** Direct integration - AudioRecorder called synchronously from event loop, chunks accumulated in memory, WAV saved on stop

**Tech Stack:** sounddevice (PortAudio wrapper), scipy (WAV writing), numpy (array operations), structlog (logging)

**Scope:** 7 phases (Phase 0 + 6 phases from original design - complete Phase 3: Audio Recording)

**Codebase verified:** 2025-10-25

---

## Phase 0: Audio Device Selection Command

### Task 1: Add device enumeration helpers (Functional Core)

**Files:**
- Modify: `src/talk_it_out/framework/audio.py` (add device helpers)
- Modify: `tests/framework/test_audio.py` (add device helper tests)

**Step 1: Write the failing test**

Add to `tests/framework/test_audio.py`:

```python
def test_find_device_by_name_returns_none_for_nonexistent():
    """Should return None if device name not found."""
    # Arrange - name that definitely doesn't exist
    nonexistent_name = "ZZZZZ_NONEXISTENT_DEVICE_12345"

    # Act
    result = audio.find_device_by_name(nonexistent_name)

    # Assert
    assert result is None


def test_find_device_by_name_matches_substring():
    """Should match device names by substring (case-insensitive)."""
    # This test requires actual audio hardware, so we just verify function signature
    # Real testing happens in manual tests
    import inspect
    sig = inspect.signature(audio.find_device_by_name)

    assert 'name' in sig.parameters
    assert sig.return_annotation != inspect.Signature.empty
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/framework/test_audio.py::test_find_device_by_name_returns_none_for_nonexistent -v`
Expected: FAIL with "AttributeError: module 'talk_it_out.framework.audio' has no attribute 'find_device_by_name'"

**Step 3: Write minimal implementation**

Add to `src/talk_it_out/framework/audio.py`:

```python
def find_device_by_name(name: str) -> Optional[tuple[int, dict]]:
    """Find audio input device by name substring matching.

    Args:
        name: Device name or substring to search for (case-insensitive)

    Returns:
        (device_index, device_info) if found, None otherwise

    Note:
        Requires sounddevice to be imported. Returns None if sounddevice
        not available or device not found.
    """
    try:
        import sounddevice as sd
    except ImportError:
        return None

    devices = sd.query_devices()
    for idx, device in enumerate(devices):
        # Only consider input devices
        if device['max_input_channels'] > 0:
            # Case-insensitive substring matching
            if name.lower() in device['name'].lower():
                return (idx, device)

    return None
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/framework/test_audio.py -v`
Expected: PASS (all tests including new ones)

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/audio.py tests/framework/test_audio.py
git commit -m "feat: add device name search helper"
```

---

### Task 2: Implement select-audio-device command

**Files:**
- Create: `src/talk_it_out/commands/select_audio_device.py`
- Modify: `src/talk_it_out/main.py` (add command)

**Step 1: Implement the command**

Create `src/talk_it_out/commands/select_audio_device.py`:

```python
# pattern: Imperative Shell
# Interactive audio device selection command

import sys
import sounddevice as sd
from pathlib import Path
from talk_it_out.framework import config, config_io


def select_audio_device() -> int:
    """Interactive audio device selection.

    Lists all available input devices and prompts user to select one.
    Updates config file with selected device.

    Returns:
        0 on success, 1 on error
    """
    try:
        # Get all devices and default
        devices = sd.query_devices()
        default_device = sd.query_devices(kind='input')
        default_idx = default_device.get('index')

        # Filter input devices
        input_devices = []
        for idx, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                is_default = " (current system default)" if idx == default_idx else ""
                input_devices.append((idx, device, is_default))

        if not input_devices:
            print("❌ No input devices found", file=sys.stderr)
            return 1

        # Display menu
        print("\nAvailable audio input devices:\n")
        print("  0: System default")

        for menu_idx, (dev_idx, device, is_default) in enumerate(input_devices, start=1):
            print(
                f"  {menu_idx}: {device['name']} "
                f"({device['max_input_channels']} channels, "
                f"{int(device['default_samplerate'])} Hz){is_default}"
            )

        # Get user selection
        print()
        try:
            selection = int(input("Select device number: "))
        except (ValueError, EOFError):
            print("❌ Invalid selection", file=sys.stderr)
            return 1

        # Process selection
        if selection == 0:
            # System default - remove device from config or set to empty string
            selected_name = ""
            print("\n✓ Selected: System default")
        elif 1 <= selection <= len(input_devices):
            # Specific device - store device name
            _, device, _ = input_devices[selection - 1]
            selected_name = device['name']
            print(f"\n✓ Selected: {selected_name}")
        else:
            print(f"❌ Invalid selection: {selection}", file=sys.stderr)
            return 1

        # Load current config
        config_path = config.get_config_path()
        cfg = config_io.load_config(config_path)

        # Update device setting
        cfg["audio"]["device"] = selected_name

        # Save config
        config_io.save_config(config_path, cfg)
        print(f"\n✓ Configuration updated: {config_path}")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
```

**Step 2: Add command to main.py**

Modify `src/talk_it_out/main.py` to add the new command after `config_edit`:

```python
@app.command()
def select_audio_device():
    """Select audio input device interactively."""
    from talk_it_out.commands.select_audio_device import select_audio_device
    sys.exit(select_audio_device())
```

**Step 3: Manual verification**

```bash
# List available devices and select one
uv run python -m talk_it_out.main select-audio-device

# Expected output:
# Available audio input devices:
#
#   0: System default
#   1: HDA Intel PCH: ALC662 rev1 Analog (2 channels, 44100 Hz) (current system default)
#   2: USB Audio Device (2 channels, 48000 Hz)
#
# Select device number: 1
#
# ✓ Selected: HDA Intel PCH: ALC662 rev1 Analog
# ✓ Configuration updated: /home/user/.config/talk-it-out/config.toml

# Verify config was updated
cat ~/.config/talk-it-out/config.toml | grep device
```

**Step 4: Commit**

```bash
git add src/talk_it_out/commands/select_audio_device.py src/talk_it_out/main.py
git commit -m "feat: add select-audio-device command"
```

---

### Task 3: Update AudioRecorder to resolve device names

**Files:**
- Modify: `src/talk_it_out/framework/audio_io.py` (implement in Phase 3)

**Note:** This will be integrated into Phase 3 Task 2 (AudioRecorder implementation).

When initializing AudioRecorder, if `device` is a non-empty string (device name), search for matching device:

```python
def __init__(self, sample_rate: int, channels: int, device: str = ""):
    """Initialize audio recorder.

    Args:
        sample_rate: Sample rate in Hz (16000 for Whisper)
        channels: Number of channels (1 for mono, 2 for stereo)
        device: Device name (empty string = default device)
    """
    self.sample_rate = sample_rate
    self.channels = channels

    # Resolve device name to index/object
    if device:
        # Search for device by name
        from talk_it_out.framework import audio
        result = audio.find_device_by_name(device)
        if result is None:
            log.warning("audio_device_not_found",
                       device_name=device,
                       message=f"Device '{device}' not found, using system default")
            self.device = None
        else:
            device_idx, device_info = result
            self.device = device_idx
            log.debug("audio_device_resolved",
                     device_name=device,
                     device_index=device_idx)
    else:
        # Empty string means system default
        self.device = None

    # ... rest of __init__
```

**No separate commit** - will be part of Phase 3 Task 2 commit.

---

## Phase 1: Dependency Detection and Installation

### Task 1: Add numpy dependency

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add numpy to dependencies**

Edit `pyproject.toml` to add numpy to the `[project.dependencies]` section:

```toml
dependencies = [
    "typer>=0.9.0",
    "structlog>=24.0.0",
    "tomli>=2.0.0; python_version < '3.11'",
    "tomli-w>=1.0.0",
    "evdev>=1.6.0",
    "numpy",  # Add this line
]
```

**Step 2: Sync dependencies**

Run: `uv sync`
Expected: "Resolved X packages" with numpy installed

**Step 3: Verify numpy import**

Run: `uv run python -c "import numpy; print(numpy.__version__)"`
Expected: Version number printed (e.g., "1.26.4")

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "deps: add numpy for audio array operations"
```

---

### Task 2: Implement PortAudio detection (Functional Core)

**Files:**
- Create: `src/talk_it_out/framework/audio_deps.py`
- Create: `tests/framework/test_audio_deps.py`

**Step 1: Write the failing test**

Create `tests/framework/test_audio_deps.py`:

```python
# pattern: Functional Core (testing pure functions)

from talk_it_out.framework import audio_deps


def test_get_portaudio_install_command_for_fedora():
    """Should return dnf install command for Fedora."""
    # Fedora uses ID='fedora' in os-release
    cmd = audio_deps.get_portaudio_install_command()

    # Command should use dnf (Fedora's package manager)
    assert "dnf" in cmd or "yum" in cmd
    assert "portaudio" in cmd


def test_check_portaudio_returns_tuple():
    """Should return (bool, Optional[str]) tuple."""
    result = audio_deps.check_portaudio()

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], bool)
    # result[1] is either None or str
    assert result[1] is None or isinstance(result[1], str)


def test_check_portaudio_error_includes_install_command():
    """If PortAudio missing, error message includes install command."""
    available, error = audio_deps.check_portaudio()

    # If not available, error should mention how to install
    if not available:
        assert error is not None
        assert "install" in error.lower()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/framework/test_audio_deps.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'talk_it_out.framework.audio_deps'"

**Step 3: Write minimal implementation**

Create `src/talk_it_out/framework/audio_deps.py`:

```python
# pattern: Functional Core
# Pure functions for audio dependency detection

from ctypes.util import find_library
from typing import Optional
import platform


def check_portaudio() -> tuple[bool, Optional[str]]:
    """Check if PortAudio library is available.

    Returns:
        (True, None) if available
        (False, error_message) if not available
    """
    if find_library('portaudio') is None:
        cmd = get_portaudio_install_command()
        error = f"PortAudio library not found. Install with: {cmd}"
        return False, error
    return True, None


def get_portaudio_install_command() -> str:
    """Get platform-specific PortAudio installation command.

    Returns:
        Installation command string for current platform
    """
    try:
        # Python 3.10+ has freedesktop_os_release()
        os_info = platform.freedesktop_os_release()
        os_id = os_info.get('ID', '').lower()

        if os_id in ('fedora', 'rhel', 'centos'):
            return "sudo dnf install portaudio-devel"
        elif os_id in ('ubuntu', 'debian'):
            return "sudo apt-get install portaudio19-dev"
        elif os_id in ('arch', 'manjaro'):
            return "sudo pacman -S portaudio"
    except (AttributeError, OSError):
        # Fall back if freedesktop_os_release not available or fails
        pass

    # Generic fallback
    return "sudo <package-manager> install portaudio-devel (or portaudio19-dev)"
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/framework/test_audio_deps.py -v`
Expected: PASS (all 3 tests)

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/audio_deps.py tests/framework/test_audio_deps.py
git commit -m "feat: add PortAudio dependency detection"
```

---

### Task 3: Integrate PortAudio check into main.py

**Files:**
- Modify: `src/talk_it_out/main.py:23-29`

**Step 1: Write integration**

Modify `src/talk_it_out/main.py` to add PortAudio check after permissions check (line 27).

**Current code (lines 23-29):**
```python
    # Check permissions first
    ok, error = permissions.check_input_group()
    if not ok:
        print(error, file=sys.stderr)
        sys.exit(1)

    # Load configuration
```

**New code (lines 23-34):**
```python
    # Check permissions first
    ok, error = permissions.check_input_group()
    if not ok:
        print(error, file=sys.stderr)
        sys.exit(1)

    # Check PortAudio dependency
    from talk_it_out.framework import audio_deps
    available, error = audio_deps.check_portaudio()
    if not available:
        print(f"❌ {error}", file=sys.stderr)
        sys.exit(1)

    # Load configuration
```

**Step 2: Manual verification documented in MANUAL_TESTING.md**

See Phase 6 Task 1 for manual test procedures.

**Step 3: Commit**

```bash
git add src/talk_it_out/main.py
git commit -m "feat: check PortAudio at startup with helpful error"
```

---

## Phase 2: Pure Audio Functions (Functional Core)

### Task 1: Implement convert_to_whisper_format

**Files:**
- Create: `tests/framework/test_audio.py`
- Create: `src/talk_it_out/framework/audio.py`

**Step 1: Write the failing test**

Create `tests/framework/test_audio.py`:

```python
# pattern: Functional Core (testing pure functions)

import numpy as np
import pytest
from talk_it_out.framework import audio


def test_convert_to_whisper_format_normalizes_int16_to_float32():
    """Convert int16 [-32768, 32767] to float32 [-1.0, 1.0]."""
    # Arrange - Create int16 audio at extremes
    audio_int16 = np.array([-32768, 0, 32767], dtype=np.int16)
    sample_rate = 16000

    # Act
    result = audio.convert_to_whisper_format(audio_int16, sample_rate)

    # Assert
    assert result.dtype == np.float32
    assert result[0] == pytest.approx(-1.0, abs=0.01)
    assert result[1] == pytest.approx(0.0, abs=0.01)
    assert result[2] == pytest.approx(1.0, abs=0.01)


def test_convert_to_whisper_format_rejects_wrong_sample_rate():
    """Raise ValueError if sample_rate != 16000."""
    # Arrange
    audio_int16 = np.array([100, 200, 300], dtype=np.int16)
    wrong_sample_rate = 44100

    # Act & Assert
    with pytest.raises(ValueError, match="Sample rate must be 16000"):
        audio.convert_to_whisper_format(audio_int16, wrong_sample_rate)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/framework/test_audio.py::test_convert_to_whisper_format_normalizes_int16_to_float32 -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'talk_it_out.framework.audio'"

**Step 3: Write minimal implementation**

Create `src/talk_it_out/framework/audio.py`:

```python
# pattern: Functional Core
# Pure functions for audio format handling and validation

import numpy as np
from typing import Optional


def convert_to_whisper_format(
    audio_int16: np.ndarray,
    sample_rate: int
) -> np.ndarray:
    """Convert int16 audio to float32 normalized for Whisper.

    Args:
        audio_int16: Audio data as int16 array
        sample_rate: Sample rate in Hz (must be 16000 for Whisper)

    Returns:
        Audio data as float32 normalized to [-1.0, 1.0]

    Raises:
        ValueError: If sample_rate is not 16000
    """
    if sample_rate != 16000:
        raise ValueError(f"Sample rate must be 16000, got {sample_rate}")

    return audio_int16.astype(np.float32) / 32768.0
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/framework/test_audio.py::test_convert_to_whisper_format_normalizes_int16_to_float32 -v`
Expected: PASS

Run: `uv run pytest tests/framework/test_audio.py::test_convert_to_whisper_format_rejects_wrong_sample_rate -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/audio.py tests/framework/test_audio.py
git commit -m "feat: add Whisper format conversion for audio"
```

---

### Task 2: Implement validate_audio_data

**Files:**
- Modify: `tests/framework/test_audio.py`
- Modify: `src/talk_it_out/framework/audio.py`

**Step 1: Write the failing tests**

Add to `tests/framework/test_audio.py`:

```python
def test_validate_audio_data_accepts_valid_audio():
    """Return (True, None) for valid numpy array."""
    # Arrange - 1 second of audio at 16kHz
    valid_audio = np.zeros(16000, dtype=np.int16)

    # Act
    is_valid, error = audio.validate_audio_data(valid_audio)

    # Assert
    assert is_valid is True
    assert error is None


def test_validate_audio_data_rejects_none():
    """Return (False, error) for None."""
    # Act
    is_valid, error = audio.validate_audio_data(None)

    # Assert
    assert is_valid is False
    assert error is not None
    assert "no audio" in error.lower() or "none" in error.lower()


def test_validate_audio_data_rejects_empty():
    """Return (False, error) for empty array."""
    # Arrange
    empty_audio = np.array([], dtype=np.int16)

    # Act
    is_valid, error = audio.validate_audio_data(empty_audio)

    # Assert
    assert is_valid is False
    assert error is not None
    assert "empty" in error.lower()


def test_validate_audio_data_rejects_too_short():
    """Return (False, error) for < 100ms (1600 samples at 16kHz)."""
    # Arrange - 50ms of audio (800 samples)
    too_short = np.zeros(800, dtype=np.int16)

    # Act
    is_valid, error = audio.validate_audio_data(too_short, min_samples=1600)

    # Assert
    assert is_valid is False
    assert error is not None
    assert "short" in error.lower() or "minimum" in error.lower()
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/framework/test_audio.py::test_validate_audio_data_accepts_valid_audio -v`
Expected: FAIL with "AttributeError: module 'talk_it_out.framework.audio' has no attribute 'validate_audio_data'"

**Step 3: Write minimal implementation**

Add to `src/talk_it_out/framework/audio.py`:

```python
def validate_audio_data(
    audio: Optional[np.ndarray],
    min_samples: int = 1600  # 0.1 seconds at 16kHz
) -> tuple[bool, Optional[str]]:
    """Validate recorded audio data.

    Args:
        audio: Audio data to validate (or None)
        min_samples: Minimum number of samples required (default 1600 = 100ms at 16kHz)

    Returns:
        (True, None) if valid
        (False, error_message) if invalid
    """
    if audio is None:
        return False, "No audio data captured"

    if len(audio) == 0:
        return False, "Audio data is empty"

    if len(audio) < min_samples:
        duration_ms = (len(audio) / 16000) * 1000
        min_duration_ms = (min_samples / 16000) * 1000
        return False, f"Recording too short: {duration_ms:.0f}ms (minimum {min_duration_ms:.0f}ms)"

    return True, None
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/framework/test_audio.py -v`
Expected: PASS (all 6 tests)

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/audio.py tests/framework/test_audio.py
git commit -m "feat: add audio data validation"
```

---

## Phase 3: Audio I/O Implementation (Imperative Shell)

### Task 1: Add audio dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add sounddevice and scipy dependencies**

Edit `pyproject.toml` to add to `[project.dependencies]`:

```toml
dependencies = [
    "typer>=0.9.0",
    "structlog>=24.0.0",
    "tomli>=2.0.0; python_version < '3.11'",
    "tomli-w>=1.0.0",
    "evdev>=1.6.0",
    "numpy",  # Added in Phase 1
    "sounddevice",  # Add this line
    "scipy",  # Add this line
]
```

**Step 2: Sync dependencies**

Run: `uv sync`
Expected: "Resolved X packages" with sounddevice and scipy installed

**Step 3: Verify imports**

Run: `uv run python -c "import sounddevice; import scipy.io.wavfile; print('OK')"`
Expected: "OK"

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "deps: add sounddevice and scipy for audio recording"
```

---

### Task 2: Implement AudioRecorder class

**Files:**
- Create: `src/talk_it_out/framework/audio_io.py`

**Step 1: No test to write (manual testing only)**

This phase has no automated tests because it requires audio hardware.

**Step 2: Implement AudioRecorder**

Create `src/talk_it_out/framework/audio_io.py`:

```python
# pattern: Imperative Shell
# Audio I/O operations using sounddevice
#
# Error Handling Strategy:
# - All errors are recoverable - application continues running
# - Missing devices/PortAudio: Logged at startup (caught earlier in main.py)
# - Stream errors: Log WARNING, return None, continue app
# - Multiple start calls: Log WARNING, ignore duplicate
# - Stop without start: Log WARNING, return None
# - File write errors: Log WARNING, continue app
#
# Logging Levels:
# - DEBUG: Callback status, chunk details, device info
# - INFO: Recording started/stopped, WAV saved with path/size
# - WARNING: Duplicate start, stop without start, invalid audio, device issues
# - ERROR: Not used (all errors are recoverable)

import queue
import tempfile
import structlog
import sounddevice as sd
import numpy as np
from pathlib import Path
from typing import Optional
from scipy.io import wavfile

log = structlog.get_logger()


class AudioRecorder:
    """Record audio from microphone using sounddevice.

    Records audio while active, accumulating chunks in a queue.
    When stopped, concatenates all chunks and returns as NumPy array.
    """

    def __init__(self, sample_rate: int, channels: int, device: str = ""):
        """Initialize audio recorder.

        Args:
            sample_rate: Sample rate in Hz (16000 for Whisper)
            channels: Number of channels (1 for mono, 2 for stereo)
            device: Device name/ID (empty string = default device)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device if device else None

        # Recording state
        self.recording = False
        self.audio_queue: queue.Queue = queue.Queue()
        self.stream: Optional[sd.InputStream] = None

        log.debug("audio_recorder_initialized",
                  sample_rate=sample_rate,
                  channels=channels,
                  device=device or "default")

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for sounddevice InputStream.

        Accumulates audio chunks in queue during recording.

        Args:
            indata: Input audio data (numpy array)
            frames: Number of frames
            time_info: Timing information
            status: Stream status flags
        """
        if status:
            log.debug("audio_callback_status", status=str(status))

        if self.recording:
            # Copy data to avoid issues with buffer reuse
            self.audio_queue.put(indata.copy())

    def start_recording(self) -> None:
        """Start recording audio from microphone.

        If already recording, logs warning and ignores.
        """
        if self.recording:
            log.warning("audio_already_recording",
                       message="start_recording called while already recording")
            return

        # Clear queue from any previous recording
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

        try:
            # Start stream
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                device=self.device,
                callback=self._audio_callback,
                dtype=np.int16
            )
            self.stream.start()
            self.recording = True

            log.info("recording_started",
                    sample_rate=self.sample_rate,
                    channels=self.channels,
                    device=self.device or "default")

        except Exception as e:
            log.warning("recording_start_failed",
                       error=str(e),
                       device=self.device or "default")
            self.recording = False
            self.stream = None

    def stop_recording(self) -> Optional[np.ndarray]:
        """Stop recording and return accumulated audio data.

        Returns:
            NumPy array of audio data (int16, shape: [samples, channels])
            or None if not recording or no data captured
        """
        if not self.recording:
            log.warning("audio_not_recording",
                       message="stop_recording called but not currently recording")
            return None

        self.recording = False

        try:
            # Stop and close stream
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None

            # Collect all chunks from queue
            chunks = []
            while not self.audio_queue.empty():
                try:
                    chunk = self.audio_queue.get_nowait()
                    chunks.append(chunk)
                except queue.Empty:
                    break

            if not chunks:
                log.warning("recording_no_data",
                           message="Recording stopped but no audio data captured")
                return None

            # Concatenate all chunks
            audio_data = np.concatenate(chunks, axis=0)

            duration_seconds = len(audio_data) / self.sample_rate
            log.info("recording_stopped",
                    samples=len(audio_data),
                    duration_seconds=f"{duration_seconds:.2f}",
                    channels=self.channels)

            return audio_data

        except Exception as e:
            log.warning("recording_stop_failed",
                       error=str(e))
            return None

    def save_wav(self, audio_data: np.ndarray, path: Optional[Path] = None) -> Path:
        """Save audio data as WAV file.

        Args:
            audio_data: Audio data to save (int16 numpy array)
            path: Optional path to save to (if None, creates temp file)

        Returns:
            Path to saved WAV file

        Raises:
            Exception: If file write fails (caller should catch and log)
        """
        if path is None:
            # Create temp file with .wav extension
            fd, temp_path = tempfile.mkstemp(suffix='.wav', prefix='recording_')
            import os
            os.close(fd)  # Close file descriptor, scipy will reopen
            path = Path(temp_path)

        # Write WAV file
        wavfile.write(path, self.sample_rate, audio_data)

        file_size = path.stat().st_size
        log.info("wav_file_saved",
                 path=str(path),
                 size_bytes=file_size,
                 sample_rate=self.sample_rate,
                 channels=self.channels)

        return path
```

**Step 3: Manual verification documented in MANUAL_TESTING.md**

See Phase 6 Task 1 for complete manual test procedures.

Standalone verification script:
```bash
uv run python -c "
from talk_it_out.framework.audio_io import AudioRecorder
import time

recorder = AudioRecorder(16000, 1)
print('Press Enter to start recording...')
input()
recorder.start_recording()
print('Recording... (press Enter to stop)')
input()
audio = recorder.stop_recording()
if audio is not None:
    path = recorder.save_wav(audio)
    print(f'Saved to: {path}')
    print('Play with: aplay', path, '(or vlc, etc.)')
"
```

**Step 4: Commit**

```bash
git add src/talk_it_out/framework/audio_io.py
git commit -m "feat: implement AudioRecorder for sounddevice-based recording"
```

---

## Phase 4: Main Application Integration

### Task 1: Integrate AudioRecorder into main.py

**Files:**
- Modify: `src/talk_it_out/main.py:11` (add imports)
- Modify: `src/talk_it_out/main.py:65` (initialize AudioRecorder)
- Modify: `src/talk_it_out/main.py:71-76` (add recording start)
- Modify: `src/talk_it_out/main.py:78-83` (add recording stop/save)

**Step 1: Add imports**

After line 11, modify the import section:

**Current (line 11):**
```python
from talk_it_out.framework import config, config_io, logging_setup, permissions, signals, keyboard, keyboard_io
```

**New (line 11):**
```python
from talk_it_out.framework import config, config_io, logging_setup, permissions, signals, keyboard, keyboard_io, audio, audio_io
```

**Step 2: Initialize AudioRecorder**

After line 63 (keyboard monitoring log), before line 66 (event loop try block), add:

**Insert at line 65:**
```python
    log.info("keyboard_monitoring_started", combos=list(target_combos.keys()))

    # Initialize audio recorder
    audio_recorder = audio_io.AudioRecorder(
        sample_rate=cfg["audio"]["sample_rate"],
        channels=cfg["audio"]["channels"],
        device=cfg["audio"]["device"]
    )

    # Event processing loop
    try:
```

**Step 3: Add recording start to combo_pressed handler**

Modify the `combo_pressed` handler (currently lines 71-76):

**Current code:**
```python
            if combo_event.event_type == 'combo_pressed':
                log.info(
                    "combo_activated",
                    combo=combo_event.combo_type,
                    device=combo_event.device_path
                )
```

**New code:**
```python
            if combo_event.event_type == 'combo_pressed':
                log.info(
                    "combo_activated",
                    combo=combo_event.combo_type,
                    device=combo_event.device_path
                )

                if combo_event.combo_type == 'record_for_paste':
                    audio_recorder.start_recording()
```

**Step 4: Add recording stop/save to combo_released handler**

Modify the `combo_released` handler (currently lines 78-83):

**Current code:**
```python
            elif combo_event.event_type == 'combo_released':
                log.info(
                    "combo_released",
                    combo=combo_event.combo_type,
                    device=combo_event.device_path
                )
```

**New code:**
```python
            elif combo_event.event_type == 'combo_released':
                log.info(
                    "combo_released",
                    combo=combo_event.combo_type,
                    device=combo_event.device_path
                )

                if combo_event.combo_type == 'record_for_paste':
                    audio_data = audio_recorder.stop_recording()

                    # Validate audio data
                    valid, error = audio.validate_audio_data(audio_data)
                    if not valid:
                        log.warning("audio_invalid", reason=error)
                    else:
                        # Save WAV file
                        wav_path = audio_recorder.save_wav(audio_data)
                        log.info("recording_complete", wav_path=str(wav_path))
```

**Step 5: Manual verification documented in MANUAL_TESTING.md**

See Phase 6 Task 1 for complete manual test procedures.

Expected output in logs:
```
recording_started sample_rate=16000 channels=1 device=default
recording_stopped samples=48000 duration_seconds=3.00 channels=1
wav_file_saved path=/tmp/recording_abc123.wav size_bytes=96044 sample_rate=16000 channels=1
recording_complete wav_path=/tmp/recording_abc123.wav
```

**Step 6: Commit**

```bash
git add src/talk_it_out/main.py
git commit -m "feat: integrate audio recording into main event loop"
```

---

## Phase 5: Error Handling and Edge Cases

### Task 1: Verify error handling coverage

**Files:**
- Review: `src/talk_it_out/framework/audio_io.py`
- Review: `src/talk_it_out/framework/audio_deps.py`
- Review: `src/talk_it_out/framework/audio.py`

**Step 1: Verify all error cases are handled**

All error handling is already implemented in Phases 1-4. This phase verifies coverage:

**Error Case Coverage:**

1. **Missing PortAudio** ✓
   - Location: `audio_deps.py:check_portaudio()` (Phase 1)
   - Handling: Returns `(False, error_message)`, main.py exits with helpful message

2. **No audio devices** ✓
   - Location: `audio_io.py:start_recording()` (Phase 3)
   - Handling: Catches Exception, logs WARNING, continues app

3. **Recording fails to start** ✓
   - Location: `audio_io.py:start_recording()` (Phase 3)
   - Handling: Sets `self.recording = False`, logs WARNING, continues app

4. **No audio data** ✓
   - Location: `audio_io.py:stop_recording()` (Phase 3)
   - Handling: Returns None, logs WARNING

5. **Recording too short** ✓
   - Location: `audio.py:validate_audio_data()` + `main.py` (Phases 2 & 4)
   - Handling: Returns `(False, error)`, main.py logs WARNING

6. **Stream errors** ✓
   - Location: `audio_io.py:_audio_callback()` (Phase 3)
   - Handling: Logs DEBUG with status

7. **Multiple start calls** ✓
   - Location: `audio_io.py:start_recording()` (Phase 3)
   - Handling: Checks `self.recording` flag, logs WARNING, returns early

8. **Stop without start** ✓
   - Location: `audio_io.py:stop_recording()` (Phase 3)
   - Handling: Checks `self.recording` flag, logs WARNING, returns None

**Step 2: No code changes needed**

All error handling is already implemented. This phase is verification only.

**Step 3: Document manual test cases**

Manual test cases documented in MANUAL_TESTING.md (created in Phase 6).

**Step 4: No commit needed** (no code changes)

Phase 5 is complete - all error handling already implemented in Phases 1-4.

---

## Phase 6: Documentation and Manual Testing

### Task 1: Create MANUAL_TESTING.md

**Files:**
- Create: `docs/MANUAL_TESTING.md`

**Step 1: Write manual testing document**

Create `docs/MANUAL_TESTING.md` with complete test cases covering:
- Startup tests (PortAudio detection, app starts, device config)
- Basic recording tests (press combo, release combo, WAV file playback)
- Audio quality tests (clarity, sample rate 16kHz, mono channel, no clipping)
- Error handling tests (short recording, duplicate start, stop without start, device errors)
- Integration tests (multiple recordings, keyboard monitoring, clean shutdown)
- Edge case tests (30+ second recording, rapid cycles, silent recording)

See `docs/MANUAL_TESTING.md` for complete test procedures and expected results.

**Step 2: Commit**

```bash
git add docs/MANUAL_TESTING.md
git commit -m "docs: add manual testing guide for audio recording"
```

---

### Task 2: Update README.md

**Files:**
- Modify: `README.md:5-25` (Status section)

**Step 1: Add Phase 3 status to README**

Modify the Status section (currently lines 5-25).

**Add after Phase 2 section, before "Next:" line:**

```markdown
**Phase 3 (Audio Recording): Complete**

Audio recording is implemented with:
- PortAudio dependency detection with helpful install messages
- Microphone recording via sounddevice library
- WAV file output to temporary location (`/tmp`)
- Integration with keyboard combo events (press to start, release to stop)
- Audio validation (minimum duration, format checks)
- Graceful error handling for all audio failures
- Manual testing guide in `docs/MANUAL_TESTING.md`

Audio is recorded at 16kHz mono (Whisper-compatible format) and saved as WAV files for verification.
```

**Update "Next:" line:**

**Current:**
```markdown
**Next:** Phase 3 will add audio recording with PulseAudio/PipeWire.
```

**New:**
```markdown
**Next:** Phase 4 will add Whisper transcription and clipboard integration.
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README with Phase 3 completion"
```

---

## Implementation Complete

All 6 phases are now documented with complete implementation tasks. The plan follows TDD where applicable (Phases 1-2 have automated tests), and provides manual testing procedures for hardware-dependent code (Phases 3-6).

**Total commits expected:** 10
**Total test files created:** 2 (test_audio_deps.py, test_audio.py)
**Total source files created:** 4 (audio_deps.py, audio.py, audio_io.py, MANUAL_TESTING.md)
**Total files modified:** 3 (pyproject.toml, main.py, README.md)
