# Manual Testing Guide - Audio Recording

This document provides comprehensive manual test cases for the audio recording functionality in talk-it-out.

## Prerequisites

Before testing, ensure:
- User is in `input` group: `groups | grep input`
- PortAudio is installed: `sudo dnf install portaudio-devel` (Fedora) or equivalent
- Microphone is connected and working
- Application dependencies are installed: `uv sync`

## Test Environment

For all tests, run the application with DEBUG logging:

```bash
uv run python -m talk_it_out.main run --log-level DEBUG
```

Watch for structured log output in JSON format.

---

## 1. Startup Tests

### Test 1.1: PortAudio Detection (Missing)

**Purpose:** Verify helpful error when PortAudio not installed

**Steps:**
1. Temporarily rename PortAudio library (requires root):
   ```bash
   sudo mv /usr/lib64/libportaudio.so.2 /usr/lib64/libportaudio.so.2.bak
   ```
2. Run application: `uv run python -m talk_it_out.main run`
3. Restore library:
   ```bash
   sudo mv /usr/lib64/libportaudio.so.2.bak /usr/lib64/libportaudio.so.2
   ```

**Expected:**
- Application exits with error message
- Error message includes platform-specific install command
- Example: `❌ PortAudio library not found. Install with: sudo dnf install portaudio-devel`

### Test 1.2: Application Startup (Normal)

**Purpose:** Verify application starts with audio enabled

**Steps:**
1. Run: `uv run python -m talk_it_out.main run --log-level DEBUG`
2. Check logs for initialization messages

**Expected:**
- Log: `audio_recorder_initialized` with sample_rate=16000, channels=1, device="default"
- Log: `keyboard_monitoring_started` with combos list
- Application runs without errors
- No warnings about audio device

### Test 1.3: Audio Device Configuration

**Purpose:** Verify device selection command

**Steps:**
1. Run: `uv run python -m talk_it_out.main select-audio-device`
2. View device list
3. Select device number (try 0 for default)
4. Verify config updated: `cat ~/.config/talk-it-out/config.toml | grep device`

**Expected:**
- Menu displays available input devices with channels and sample rates
- System default is marked clearly
- Selection updates config file
- Success message shows config path

---

## 2. Basic Recording Tests

### Test 2.1: Single Recording

**Purpose:** Verify basic record/stop/save workflow

**Steps:**
1. Run application: `uv run python -m talk_it_out.main run --log-level DEBUG`
2. Press configured combo (default: Meta+Alt)
3. Speak clearly for 2-3 seconds: "Testing audio recording"
4. Release combo
5. Note the WAV file path in logs

**Expected:**
- Log: `recording_started` when combo pressed
- Log: `recording_stopped` with samples and duration when released
- Log: `wav_file_saved` with path (e.g., `/tmp/recording_abc123.wav`)
- Log: `recording_complete` with wav_path
- No warnings or errors

### Test 2.2: WAV File Playback

**Purpose:** Verify recorded audio can be played

**Steps:**
1. Complete Test 2.1
2. Play WAV file from logs: `aplay /tmp/recording_abc123.wav`
   (or use `vlc`, `mpv`, etc.)

**Expected:**
- Audio plays back clearly
- Speech is intelligible
- No distortion or noise
- Volume levels are reasonable

### Test 2.3: Multiple Consecutive Recordings

**Purpose:** Verify multiple recordings work without restart

**Steps:**
1. Run application
2. Record 3 separate clips (different content each time):
   - Recording 1: "First test"
   - Recording 2: "Second test"
   - Recording 3: "Third test"
3. Play each WAV file

**Expected:**
- Each recording works independently
- All 3 WAV files are created with unique names
- Each file contains only its own recording (no cross-contamination)
- Logs show distinct start/stop pairs for each

---

## 3. Audio Quality Tests

### Test 3.1: Audio Clarity

**Purpose:** Verify speech quality is sufficient for transcription

**Steps:**
1. Record clear speech at normal volume
2. Record whispered speech
3. Record loud speech
4. Play back all recordings

**Expected:**
- Normal speech: Clear and intelligible
- Whisper: Audible (may be quiet but not silent)
- Loud: No clipping or distortion (check waveform if possible)

### Test 3.2: Sample Rate Verification

**Purpose:** Confirm audio is recorded at 16kHz (Whisper requirement)

**Steps:**
1. Record test audio
2. Check file properties:
   ```bash
   file /tmp/recording_abc123.wav
   soxi /tmp/recording_abc123.wav  # if sox is installed
   ```

**Expected:**
- Sample rate: 16000 Hz
- Channels: 1 (mono)
- Format: WAV, signed 16-bit PCM

### Test 3.3: Channel Configuration

**Purpose:** Verify mono recording (required for Whisper)

**Steps:**
1. Inspect WAV file metadata (see Test 3.2)
2. Check logs for `channels=1`

**Expected:**
- All recordings are mono (1 channel)
- Logs consistently show `channels=1`

---

## 4. Error Handling Tests

### Test 4.1: Recording Too Short

**Purpose:** Verify validation rejects <100ms recordings

**Steps:**
1. Run application
2. Press and immediately release combo (tap quickly)
3. Check logs for warning

**Expected:**
- Log: `audio_invalid` with reason containing "too short" or "minimum"
- No WAV file saved
- Application continues running (no crash)

### Test 4.2: Duplicate Start Calls

**Purpose:** Verify graceful handling of multiple start_recording calls

**Steps:**
This requires code inspection rather than direct testing, but verify:
1. Review `audio_io.py:101-104`
2. Confirm `if self.recording:` check exists
3. Confirm warning is logged

**Expected:**
- Code checks `self.recording` flag before starting
- Logs `audio_already_recording` warning
- Returns early without starting second stream

### Test 4.3: Stop Without Start

**Purpose:** Verify handling of stop_recording without active recording

**Steps:**
Similar to 4.2, verify by code inspection:
1. Review `audio_io.py:144-147`
2. Confirm `if not self.recording:` check exists

**Expected:**
- Code checks `self.recording` flag
- Logs `audio_not_recording` warning
- Returns None

### Test 4.4: Device Not Found

**Purpose:** Verify handling when configured device doesn't exist

**Steps:**
1. Edit config: `talk-it-out config-edit`
2. Set `device = "NONEXISTENT_DEVICE_12345"`
3. Run application: `uv run python -m talk_it_out.main run --log-level DEBUG`

**Expected:**
- Log: `audio_device_not_found` with device name
- Log indicates falling back to system default
- Application continues running
- Recording still works (using default device)

### Test 4.5: No Audio Data Captured

**Purpose:** Verify handling when recording produces no data

**Steps:**
This is difficult to trigger intentionally, but verify by code inspection:
1. Review `audio_io.py:167-170`
2. Confirm empty chunks are handled

**Expected:**
- Code checks `if not chunks:`
- Logs `recording_no_data` warning
- Returns None

---

## 5. Integration Tests

### Test 5.1: Keyboard Monitoring Integration

**Purpose:** Verify audio recording integrates with keyboard monitoring

**Steps:**
1. Run application with DEBUG logging
2. Press combo and hold
3. Check logs for combo_activated before recording_started
4. Release combo
5. Check logs for combo_released before recording_stopped

**Expected:**
- Event order: `combo_activated` → `recording_started` → `combo_released` → `recording_stopped`
- No warnings about missing events
- Clean integration between keyboard and audio systems

### Test 5.2: Multiple Keyboards (if available)

**Purpose:** Verify recording works with any keyboard device

**Steps:**
1. Connect multiple keyboards (built-in + USB, or multiple USB)
2. Run application
3. Test combo on each keyboard separately

**Expected:**
- Recording works from any keyboard
- Each keyboard triggers recording independently
- Logs show correct device path for each

### Test 5.3: Clean Shutdown

**Purpose:** Verify graceful shutdown during recording

**Steps:**
1. Start recording (press combo)
2. While recording, send SIGINT: Ctrl+C
3. Check logs for cleanup

**Expected:**
- Recording stops cleanly
- Stream is closed
- Log: `shutdown_complete`
- No errors or warnings about unclosed resources

---

## 6. Edge Case Tests

### Test 6.1: Long Recording (30+ seconds)

**Purpose:** Verify no issues with extended recordings

**Steps:**
1. Press combo
2. Speak continuously for 30+ seconds
3. Release combo
4. Play back recording

**Expected:**
- Recording captures full duration
- No dropouts or gaps in audio
- WAV file size is appropriate (~960KB for 30s mono 16kHz)
- Logs show duration ≥30 seconds

### Test 6.2: Rapid Press/Release Cycles

**Purpose:** Verify queue handling under rapid input

**Steps:**
1. Rapidly press and release combo 5 times in quick succession
2. Check logs and WAV files

**Expected:**
- Each press/release pair is handled independently
- Short recordings may be rejected (Test 4.1)
- Valid recordings are saved
- No crashes or queue overflow

### Test 6.3: Silent Recording

**Purpose:** Verify recording works even with no audio input

**Steps:**
1. Press combo
2. Stay silent for 3 seconds
3. Release combo
4. Play back recording

**Expected:**
- Recording is created and saved
- Playback is silent or contains only background noise
- No errors (silence is valid audio data)

---

## 7. Whisper Transcription Tests

### 7.1 Model Download Verification (First Run Only)

**Purpose:** Verify model downloads correctly on first run

**Prerequisites:** Delete `~/.cache/huggingface/hub/` to force fresh download

**Steps:**
1. Start application
2. Observe console output during startup

**Expected:**
- Whisper model downloads (may take 30s-2min depending on connection)
- Application starts normally after download completes
- Log shows "whisper_model_loaded" with model name

**Actual:** [Pass/Fail]

**Notes:**
- Only happens on first run or when switching models
- Subsequent runs load cached model instantly

---

### 7.2 Basic Transcription

**Purpose:** Verify audio transcribes to text

**Steps:**
1. Start application
2. Hold keyboard combo
3. Speak clearly: "Hello world, this is a test"
4. Release keyboard combo
5. Check application logs

**Expected:**
- Log shows "transcription_complete" with segment count
- Log shows "transcription_result" with transcribed text
- Text matches spoken words reasonably well

**Actual:** [Pass/Fail]

**Notes:**
- Check for language detection log entry
- Turbo model should have high accuracy

---

### 7.3 Silent Audio Transcription

**Purpose:** Verify handling of silence/no speech

**Steps:**
1. Start application
2. Hold keyboard combo
3. Remain silent for 2 seconds
4. Release keyboard combo
5. Check logs

**Expected:**
- Log shows "transcription_empty" warning with reason "No speech detected"
- OR empty transcription result
- No errors or crashes

**Actual:** [Pass/Fail]

---

### 7.4 Debug Audio Saving

**Purpose:** Verify save_debug_audio config works

**Steps:**
1. Edit config: Set `whisper.save_debug_audio = true`
2. Start application
3. Record audio (speak any phrase)
4. Check `/tmp/` directory for WAV files

**Expected:**
- WAV file created in `/tmp/recording_*.wav`
- Log shows "debug_audio_saved" with file path
- WAV file playable with `aplay` or `ffplay`

**Actual:** [Pass/Fail]

**Steps (save_debug_audio = false):**
1. Edit config: Set `whisper.save_debug_audio = false`
2. Start application
3. Record audio
4. Check `/tmp/` directory

**Expected:**
- NO new WAV files created
- No "debug_audio_saved" log entries
- Transcription still works

**Actual:** [Pass/Fail]

---

### 7.5 Different Model Sizes

**Purpose:** Verify model switching works

**Steps:**
1. Edit config: Set `whisper.model = "tiny"`
2. Start application
3. Record and transcribe test phrase
4. Note transcription quality
5. Stop application
6. Edit config: Set `whisper.model = "turbo"`
7. Start application
8. Record same test phrase
9. Compare transcription quality

**Expected:**
- Both models load successfully
- Turbo has better accuracy than tiny
- Model switch requires app restart
- Logs show different model names at startup

**Actual:** [Pass/Fail]

**Notes:**
- Tiny: Fast but lower accuracy
- Turbo: Best balance of speed/accuracy

---

### 7.6 Language Detection

**Purpose:** Verify language auto-detection works

**Steps:**
1. Start application with `whisper.language = "en"`
2. Record English phrase
3. Check logs for detected_language
4. Edit config: Set `whisper.language = "es"`
5. Restart application
6. Record Spanish phrase
7. Check logs

**Expected:**
- Logs show detected_language matches config setting
- Transcription respects language parameter
- Language probability logged

**Actual:** [Pass/Fail]

---

### 7.7 Device Auto-Detection

**Purpose:** Verify CUDA/CPU auto-detection

**Steps:**
1. Edit config: Set `whisper.device = "auto"`
2. Start application
3. Check logs for transcriber_initialized

**Expected (if CUDA available):**
- device=cuda, compute_type=float16

**Expected (if CPU only):**
- device=cpu, compute_type=int8

**Actual:** [Pass/Fail]

**Notes:**
- Use `nvidia-smi` to check CUDA availability
- CPU fallback is automatic and transparent

---

## Test Results Template

Use this template to document test results:

```markdown
## Test Session: YYYY-MM-DD

**Environment:**
- OS: Fedora 42 / Ubuntu 24.04 / etc.
- Kernel: 6.17.4
- PortAudio version: X.Y.Z
- Microphone: Built-in / USB / etc.

**Test Results:**

| Test ID | Test Name | Status | Notes |
|---------|-----------|--------|-------|
| 1.1 | PortAudio Detection | PASS/FAIL | |
| 1.2 | Application Startup | PASS/FAIL | |
| 1.3 | Device Configuration | PASS/FAIL | |
| 2.1 | Single Recording | PASS/FAIL | |
| 2.2 | WAV Playback | PASS/FAIL | |
| 2.3 | Multiple Recordings | PASS/FAIL | |
| 3.1 | Audio Clarity | PASS/FAIL | |
| 3.2 | Sample Rate | PASS/FAIL | |
| 3.3 | Channel Config | PASS/FAIL | |
| 4.1 | Short Recording | PASS/FAIL | |
| 4.2 | Duplicate Start | PASS/FAIL | Code inspection |
| 4.3 | Stop Without Start | PASS/FAIL | Code inspection |
| 4.4 | Device Not Found | PASS/FAIL | |
| 4.5 | No Audio Data | PASS/FAIL | Code inspection |
| 5.1 | Keyboard Integration | PASS/FAIL | |
| 5.2 | Multiple Keyboards | PASS/SKIP | Skip if only 1 keyboard |
| 5.3 | Clean Shutdown | PASS/FAIL | |
| 6.1 | Long Recording | PASS/FAIL | |
| 6.2 | Rapid Cycles | PASS/FAIL | |
| 6.3 | Silent Recording | PASS/FAIL | |
| 7.1 | Model Download | PASS/FAIL | First run only |
| 7.2 | Basic Transcription | PASS/FAIL | |
| 7.3 | Silent Transcription | PASS/FAIL | |
| 7.4 | Debug Audio Saving | PASS/FAIL | |
| 7.5 | Model Sizes | PASS/FAIL | |
| 7.6 | Language Detection | PASS/FAIL | |
| 7.7 | Device Auto-Detection | PASS/FAIL | |

**Issues Found:**
- List any bugs, unexpected behavior, or concerns

**Overall Assessment:**
- Ready for next phase? YES/NO
- Confidence level: HIGH/MEDIUM/LOW
```

---

## Troubleshooting

### No recording_started log

**Possible causes:**
- Combo not configured correctly
- Check config: `cat ~/.config/talk-it-out/config.toml`
- Verify key names match evdev constants

### recording_start_failed error

**Possible causes:**
- Microphone not connected
- Permissions issue (though PortAudio usually doesn't require special permissions)
- Device already in use by another application

**Solutions:**
- Check `arecord -l` to list capture devices
- Close other audio applications
- Try selecting different device: `talk-it-out select-audio-device`

### WAV file is silent

**Possible causes:**
- Wrong device selected (e.g., line-in instead of microphone)
- Microphone muted in system settings
- Recording duration too short to capture audio

**Solutions:**
- Check system audio settings (pavucontrol, KDE audio settings)
- Test microphone: `arecord -d 3 test.wav && aplay test.wav`
- Use `select-audio-device` to choose correct input

### Recording stutters or has dropouts

**Possible causes:**
- High CPU usage
- USB audio device buffering issues
- System under heavy load

**Solutions:**
- Monitor CPU during recording: `top` or `htop`
- Try built-in audio device instead of USB
- Close resource-intensive applications

---

## Next Steps After Manual Testing

After completing manual tests:

1. Document results using template above
2. File issues for any failures
3. Verify all PASS before proceeding to next phase
4. Update docs/plans/ with any implementation changes needed

Phase 4 (Whisper Transcription) can begin once Phase 3 manual tests pass.
