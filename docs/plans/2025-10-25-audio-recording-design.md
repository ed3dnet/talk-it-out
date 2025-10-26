# Audio Recording Design

## Overview

Add audio recording capability to the voice-to-text application. When the user presses the `record_for_paste` key combination, the application starts recording audio. When released, recording stops and the audio is saved as a WAV file to a temporary location with the path logged.

**Goals:**
- Record audio synchronized with keyboard combo events
- Save recordings as WAV files for manual verification
- Prepare audio in the correct format for future Whisper transcription
- Gracefully handle missing dependencies and errors

**Success Criteria:**
- Audio recording starts when combo pressed, stops when released
- WAV files are saved and playable
- PortAudio dependency detection with helpful error messages
- Application continues running even if recording fails

## Architecture

### Approach: Direct Integration

**Pattern:** Synchronous integration into main event loop
- AudioRecorder called directly from combo event handlers
- Recording starts on `combo_pressed`, stops on `combo_released`
- Audio chunks accumulate in memory during recording
- All chunks concatenated when recording stops
- WAV file saved immediately after stop

**Rationale:**
- Simple and straightforward
- Matches existing keyboard monitoring pattern
- Whisper (future) requires complete audio anyway, not streaming
- YAGNI - current scope doesn't need event-driven complexity

**Flow:**
```
User presses combo → combo_pressed event
  → AudioRecorder.start_recording()
  → sounddevice.InputStream starts
  → Callback accumulates chunks in queue

User releases combo → combo_released event
  → AudioRecorder.stop_recording()
  → Stream stops and closes
  → Concatenate all chunks from queue
  → Return NumPy array (int16, 16kHz, mono)
  → Validate audio data
  → Save as WAV to temp file
  → Log file path at INFO level
```

## Existing Patterns

This design follows established patterns from the keyboard monitoring implementation:

### FCIS Separation
From `keyboard.py` / `keyboard_io.py`:
- **Functional Core** (`audio.py`): Pure functions for format conversion, validation
- **Imperative Shell** (`audio_io.py`): sounddevice I/O, file writing, device management

### Error Philosophy
From `keyboard_io.py` docstring:
- All errors are recoverable - application continues running
- Device/permission errors: Log WARNING, continue
- Missing dependencies: Detect at startup, show helpful message, exit
- Operational failures: Log ERROR, skip that operation, continue

### Logging Structure
From existing modules:
- Use structlog with context fields
- DEBUG: Verbose operational details (callbacks, chunks)
- INFO: User-facing events (recording started/stopped, file saved)
- WARNING: Expected failures (short recordings, no data)
- ERROR: Unexpected failures (device errors, stream failures)

### Resource Management
From `keyboard_io.py`:
- Initialize resources once at startup
- No background threads (stream uses callbacks)
- Clean shutdown by closing streams
- Per-operation state (recording flag, queue)

## Implementation Phases

### Phase 1: Dependency Detection and Installation

**Goal:** Detect PortAudio availability and guide users to install if missing

**Components:**
- `src/talk_it_out/framework/audio_deps.py` (Functional Core)
  - `check_portaudio() -> tuple[bool, Optional[str]]`
  - `get_portaudio_install_command() -> str`

**Files Modified:**
- `src/talk_it_out/main.py` - Add PortAudio check at startup (after permissions, before config)

**Dependencies:**
- No new Python dependencies (uses ctypes.util.find_library)

**Testing:**
- Unit test: `test_get_portaudio_install_command_for_fedora()`
- Manual test: Remove portaudio, verify error message shows correct command
- Manual test: Install portaudio, verify app starts

**Verification:**
```bash
# Test missing PortAudio
sudo dnf remove portaudio-devel
uv run python -m talk_it_out.main run
# Should show: "Install with: sudo dnf install portaudio-devel"

# Test with PortAudio
sudo dnf install portaudio-devel
uv run python -m talk_it_out.main run
# Should start normally
```

---

### Phase 2: Pure Audio Functions (Functional Core)

**Goal:** Implement pure functions for audio format handling and validation

**Components:**
- `src/talk_it_out/framework/audio.py` (Functional Core)
  - `convert_to_whisper_format(audio_int16, sample_rate) -> np.ndarray`
  - `validate_audio_data(audio, min_samples) -> tuple[bool, Optional[str]]`

**Files Created:**
- `src/talk_it_out/framework/audio.py`
- `tests/framework/test_audio.py`

**Dependencies:**
- `numpy` (already available)

**Testing:**
```python
# Unit tests (all pure, no mocks needed)
def test_convert_to_whisper_format_normalizes_int16_to_float32():
    """Convert int16 [-32768, 32767] to float32 [-1.0, 1.0]"""

def test_convert_to_whisper_format_rejects_wrong_sample_rate():
    """Raise ValueError if sample_rate != 16000"""

def test_validate_audio_data_accepts_valid_audio():
    """Return (True, None) for valid numpy array"""

def test_validate_audio_data_rejects_none():
    """Return (False, error) for None"""

def test_validate_audio_data_rejects_empty():
    """Return (False, error) for empty array"""

def test_validate_audio_data_rejects_too_short():
    """Return (False, error) for < 100ms (1600 samples at 16kHz)"""
```

**Verification:**
```bash
uv run pytest tests/framework/test_audio.py -v
```

---

### Phase 3: Audio I/O Implementation (Imperative Shell)

**Goal:** Implement sounddevice-based recording with WAV file output

**Components:**
- `src/talk_it_out/framework/audio_io.py` (Imperative Shell)
  - `class AudioRecorder`
    - `__init__(sample_rate, channels, device)`
    - `start_recording() -> None`
    - `stop_recording() -> Optional[np.ndarray]`
    - `save_wav(audio_data, path) -> Path`
  - Private: `_audio_callback(indata, frames, time, status)`

**Files Created:**
- `src/talk_it_out/framework/audio_io.py`

**Dependencies:**
- `sounddevice` - Add via `uv add sounddevice`
- `scipy` - Add via `uv add scipy` (for wavfile.write)

**System Dependencies:**
- PortAudio (checked in Phase 1)

**Key Implementation Details:**
```python
class AudioRecorder:
    def __init__(self, sample_rate: int, channels: int, device: str = ""):
        self.sample_rate = sample_rate  # 16000 for Whisper
        self.channels = channels        # 1 for Whisper
        self.device = device if device else None
        self.recording = False
        self.audio_queue = queue.Queue()
        self.stream = None

    def start_recording(self):
        # Start sounddevice.InputStream with callback
        # Callback puts chunks into queue

    def stop_recording(self) -> Optional[np.ndarray]:
        # Stop stream
        # Collect all chunks from queue
        # Concatenate into single array
        # Return or None if no data

    def save_wav(self, audio_data, path=None):
        # Create temp file if path not provided
        # Use scipy.io.wavfile.write()
        # Return Path object
```

**Testing:**
- No unit tests (requires audio hardware)
- Manual testing only (see MANUAL_TESTING.md)

**Verification:**
```bash
# Standalone test script (create for manual testing)
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
"
```

---

### Phase 4: Main Application Integration

**Goal:** Wire audio recording into main event loop triggered by keyboard combos

**Files Modified:**
- `src/talk_it_out/main.py`
  - Import audio modules
  - Initialize AudioRecorder after keyboard monitor
  - Handle combo events: start/stop recording, validate, save

**Integration Code:**
```python
# After keyboard monitor setup (line ~60):
from talk_it_out.framework import audio_io, audio

audio_recorder = audio_io.AudioRecorder(
    sample_rate=cfg["audio"]["sample_rate"],
    channels=cfg["audio"]["channels"],
    device=cfg["audio"]["device"]
)

# In event loop (modify existing combo handlers):
if combo_event.event_type == 'combo_pressed':
    log.info("combo_activated", combo=combo_event.combo_type)

    if combo_event.combo_type == 'record_for_paste':
        audio_recorder.start_recording()

elif combo_event.event_type == 'combo_released':
    log.info("combo_released", combo=combo_event.combo_type)

    if combo_event.combo_type == 'record_for_paste':
        audio_data = audio_recorder.stop_recording()

        # Validate
        valid, error = audio.validate_audio_data(audio_data)
        if not valid:
            log.warning("audio_invalid", reason=error)
        else:
            # Save WAV
            wav_path = audio_recorder.save_wav(audio_data)
            log.info("recording_complete", wav_path=str(wav_path))
```

**Testing:**
- Manual testing (see MANUAL_TESTING.md)

**Verification:**
```bash
# Start app
uv run python -m talk_it_out.main run

# Press and hold combo (Super+Alt)
# Speak into microphone
# Release combo
# Check logs for WAV file path
# Play WAV file to verify audio captured
```

---

### Phase 5: Error Handling and Edge Cases

**Goal:** Handle all error conditions gracefully

**Components:**
- Already implemented in previous phases
- Verify error paths work correctly

**Error Cases to Handle:**
1. **Missing PortAudio:** Detected in Phase 1, app exits with helpful message
2. **No audio devices:** sounddevice raises exception, caught and logged
3. **Recording fails to start:** Log ERROR, continue app
4. **No audio data:** Validate catches this, log WARNING
5. **Recording too short:** Validate catches this, log WARNING
6. **Stream errors:** Callback receives status, log DEBUG
7. **Multiple start calls:** Check `self.recording` flag, log WARNING, ignore
8. **Stop without start:** Check `self.recording` flag, log WARNING, return None

**Testing:**
- Manual test each error case (see MANUAL_TESTING.md)

**Verification:**
```bash
# Test short recording
# Press and immediately release combo
# Should log: "Recording too short"

# Test multiple starts
# Press combo twice rapidly
# Should log: "audio_already_recording"

# Test stop without start
# Start app, release combo without pressing
# Should log: "audio_not_recording"
```

---

### Phase 6: Documentation and Manual Testing

**Goal:** Create comprehensive manual testing runbook and update README

**Files Created:**
- `docs/MANUAL_TESTING.md` - Complete manual test checklist

**Files Modified:**
- `README.md` - Update status, add audio recording section

**Manual Testing Checklist:**

#### Startup Tests
- [ ] Missing PortAudio detected with install command
- [ ] App starts with PortAudio installed
- [ ] Audio device configuration respected from config.toml

#### Basic Recording
- [ ] Press combo → "recording started" log appears
- [ ] Release combo → "recording stopped" log appears
- [ ] WAV file path logged at INFO level
- [ ] WAV file exists at logged path
- [ ] WAV file is playable (use `aplay` or VLC)
- [ ] Recording contains expected audio

#### Audio Quality
- [ ] Recording is clear and audible
- [ ] Sample rate is 16kHz (check with `soxi <file>.wav`)
- [ ] Channels is mono (1 channel)
- [ ] No clipping or distortion

#### Error Cases
- [ ] Very short press (< 100ms) logs "too short" warning
- [ ] Press combo twice rapidly logs "already recording"
- [ ] Release without press logs "not recording"
- [ ] Unplug microphone during recording logs error, app continues

#### Integration
- [ ] Keyboard monitoring still works after recording
- [ ] Multiple recordings in same session work
- [ ] Different combos don't interfere with recording
- [ ] Clean shutdown with Ctrl+C

#### Edge Cases
- [ ] 30+ second recording works
- [ ] Rapid press/release cycles don't crash
- [ ] Silent recording (no speech) still saves valid WAV

**Verification:**
```bash
# Check manual testing document exists
cat docs/MANUAL_TESTING.md

# Verify all test cases are documented
grep -c "\[ \]" docs/MANUAL_TESTING.md
# Should show number of test cases
```

---

## Additional Considerations

### Audio Format Requirements

**For Whisper (future implementation):**
- Sample rate: 16kHz (already enforced in config)
- Channels: 1 (mono) (already enforced in config)
- Format for transcription: float32 normalized to [-1.0, 1.0]
- Recording format: int16 (sounddevice default, efficient)
- Conversion: `audio.astype(np.float32) / 32768.0`

**WAV File Format:**
- Sample rate: 16kHz
- Channels: 1
- Sample format: int16 (PCM)
- Created by: `scipy.io.wavfile.write(path, 16000, audio_int16)`

### Performance Considerations

**Memory:**
- 1 second of audio = 16,000 samples × 2 bytes = 32 KB
- 30 second recording = ~960 KB in memory
- Negligible for modern systems

**CPU:**
- Audio callback runs in separate thread (sounddevice internal)
- Minimal CPU usage for buffering
- No processing during recording

**Latency:**
- Start: < 10ms (stream initialization)
- Stop: < 100ms (concatenate chunks)
- Total overhead: Imperceptible to user

### Future Extensibility

**Phase 4 (Whisper Transcription) will add:**
- `faster-whisper` library for transcription
- Model loading and initialization
- Transcription call after WAV save
- Text output (clipboard or paste)

**This design prepares for Phase 4 by:**
- Recording at 16kHz mono (Whisper requirement)
- Providing NumPy arrays (faster-whisper accepts these directly)
- Saving WAV files (for debugging transcription issues)
- Validation ensures minimum audio length for meaningful transcription

**No changes needed to audio recording when adding Whisper:**
```python
# Future Phase 4 code (after save_wav):
from faster_whisper import WhisperModel

model = WhisperModel("large-v3", device="cpu", compute_type="int8")

# Convert for Whisper
audio_float = audio.convert_to_whisper_format(audio_data, 16000)

# Transcribe
segments, info = model.transcribe(audio_float, language="en", vad_filter=True)
text = " ".join([seg.text for seg in segments])

log.info("transcription_complete", text=text)
# ... paste logic ...
```

### Security and Privacy

**Local Processing:**
- All audio recorded and processed locally
- No network transmission
- No cloud services

**Temporary Files:**
- WAV files saved to `/tmp` (system temp directory)
- Files persist for debugging
- User can manually delete if desired
- Future: Add config option for auto-cleanup

**Permissions:**
- Requires microphone access (standard for audio apps)
- No elevated privileges needed
- PortAudio uses user's audio permissions

### Dependencies Summary

**Python Dependencies:**
- `sounddevice` - Audio I/O (PortAudio wrapper)
- `scipy` - WAV file writing
- `numpy` - Already available (array operations)

**System Dependencies:**
- `portaudio-devel` (Fedora) - Required for sounddevice
- Microphone device with working driver

**Installation:**
```bash
# System dependency
sudo dnf install portaudio-devel

# Python dependencies
uv add sounddevice scipy
```

### Logging Levels

**DEBUG:**
- Audio callback status messages
- Chunk collection details
- Device initialization details

**INFO:**
- Recording started (with config)
- Recording stopped (with duration, sample count)
- WAV file saved (with path, size)

**WARNING:**
- Already recording (duplicate start)
- Not recording (stop without start)
- Invalid audio (too short, empty, None)
- Device initialization warnings

**ERROR:**
- Stream start failure
- File write failure
- Unexpected exceptions

### Configuration

**Existing config.toml fields (already defined):**
```toml
[audio]
sample_rate = 16000  # Required for Whisper
channels = 1         # Required for Whisper
device = ""          # Empty = default device
```

**No new configuration needed for Phase 3 (Audio Recording).**

**Future configuration (Phase 4 - Whisper):**
```toml
[whisper]
model = "base"       # tiny, base, small, medium, large
language = ""        # Empty = auto-detect
```

---

## Summary

This design implements audio recording using a direct integration approach with sounddevice. Audio is recorded while the user holds a key combination, then saved as a WAV file to a temporary location with the path logged.

**Key architectural decisions:**
1. **Direct integration** - Simplest approach, matches keyboard monitoring pattern
2. **faster-whisper ready** - Audio format correct for future transcription
3. **FCIS compliance** - Pure logic in audio.py, I/O in audio_io.py
4. **Error resilience** - Graceful degradation, app continues on failures
5. **Manual testing** - Comprehensive runbook since automated testing isn't feasible
6. **PortAudio detection** - Helpful error messages guide users to install dependencies

**Implementation order:**
1. Dependency detection (can be tested immediately)
2. Pure functions (testable with unit tests)
3. Audio I/O (requires manual testing)
4. Main integration (end-to-end manual testing)
5. Error handling verification
6. Documentation and manual testing runbook

**Next phase:**
After validating audio recording works correctly through manual testing, Phase 4 will add faster-whisper transcription, clipboard integration, and text insertion.
