# Whisper Transcription Integration Design

## Overview

Integrate faster-whisper for audio transcription, converting recorded audio to text. This implements Phase 4 (Whisper Transcription) from the initial spec.

**Goals:**
- Transcribe recorded audio using faster-whisper library
- Pass NumPy audio arrays directly (no disk I/O required)
- Support GPU acceleration when available
- Expose key whisper configuration options
- Maintain fast startup while supporting model caching

**Success Criteria:**
- Audio recorded from combo triggers transcription
- Transcribed text logged and ready for paste integration
- Model loads at startup (eager initialization)
- Configuration allows tuning for accuracy vs speed
- All existing tests continue to pass

## Architecture

### Single Transcriber Class (Imperative Shell)

Create `src/talk_it_out/framework/whisper_io.py` with a `Transcriber` class that:
- Owns WhisperModel instance (initialized at startup)
- Handles device/compute type auto-detection
- Converts int16 audio to float32 format
- Manages transcription execution
- Logs timing and results

**Pattern:** Imperative Shell (Mixed)
- Combines I/O (model loading, inference) with business logic (device detection, text joining)
- Simpler than full FCIS split
- All whisper-related code in one file

### Interface

```python
class Transcriber:
    def __init__(self, whisper_config: dict):
        """Initialize WhisperModel with config settings.

        Args:
            whisper_config: Dict with keys:
                - model: str (tiny/base/small/medium/large/turbo)
                - language: str (e.g., "en")
                - device: str (auto/cuda/cpu)
                - compute_type: str (auto/int8/float16/float32/...)
                - beam_size: int (1-10)
                - vad_filter: bool
                - save_debug_audio: bool

        Raises:
            RuntimeError: If model fails to load or CUDA requested but unavailable
        """

    def transcribe(self, audio_int16: np.ndarray, sample_rate: int) -> str:
        """Transcribe audio to text.

        Args:
            audio_int16: Audio data as int16 numpy array
            sample_rate: Sample rate (must be 16000)

        Returns:
            Transcribed text (stripped, joined from all segments)

        Raises:
            ValueError: If sample_rate != 16000
        """
```

## Existing Patterns

### Audio Recording Pattern (Framework to Follow)

The codebase already has:
- `audio.py` (Functional Core) - Pure audio operations
- `audio_io.py` (Imperative Shell) - AudioRecorder class with sounddevice I/O
- `audio_deps.py` (Functional Core) - Dependency detection

### Pattern Divergence

Whisper integration uses a **simpler pattern**:
- Single `whisper_io.py` file (no separate functional core)
- Transcriber class combines model I/O and transcription logic
- **Why:** Whisper inference is inherently I/O-bound (model is external), less benefit from splitting pure functions

### Dependency Pattern (Following Existing)

No separate `whisper_deps.py` needed:
- faster-whisper is a pure Python dependency (installed via pip)
- No system library detection required (unlike PortAudio)
- Model download handled automatically by WhisperModel

## Implementation Phases

### Phase 0: Configuration Expansion

**Goal:** Add whisper config options to support faster-whisper parameters

**Components:**
- `src/talk_it_out/framework/config.py`

**Changes:**
```python
# Update DEFAULT_CONFIG["whisper"]
"whisper": {
    "model": "turbo",              # Changed from "base"
    "language": "en",              # Changed from "" (empty = auto-detect)
    "device": "auto",              # New: auto/cuda/cpu
    "compute_type": "auto",        # New: auto/int8/float16/float32
    "beam_size": 5,                # New: 1-10
    "vad_filter": True,            # New: skip silence detection
    "save_debug_audio": False,     # New: save WAV to /tmp for debugging
}

# Update VALID_WHISPER_MODELS
VALID_WHISPER_MODELS = ["tiny", "base", "small", "medium", "large", "turbo"]

# Add validation in validate_config():
- whisper.device in ["auto", "cuda", "cpu"]
- whisper.compute_type in ["auto", "int8", "int8_float32", "int8_float16",
                           "int16", "float16", "float32"]
- whisper.beam_size: 1 <= value <= 10
- whisper.vad_filter: boolean
- whisper.save_debug_audio: boolean
```

**Testing:**
- Update `test_config.py` with new validation tests
- Verify existing configs migrate gracefully (defaults fill in missing fields)

---

### Phase 1: Dependencies

**Goal:** Add faster-whisper to project dependencies

**Task:**
```bash
uv add faster-whisper
```

**Notes:**
- First run will download model (~809MB for turbo) from HuggingFace
- Downloads to `~/.cache/huggingface/hub/`
- Subsequent runs use cached model
- Works offline after first download

**Testing:**
- Verify `uv sync` installs faster-whisper successfully
- Check import: `python -c "from faster_whisper import WhisperModel"`

---

### Phase 2: Transcriber Implementation

**Goal:** Create Transcriber class with device auto-detection and transcription

**Components:**
- `src/talk_it_out/framework/whisper_io.py` (new file)

**Implementation:**

```python
# pattern: Imperative Shell
# Whisper transcription with faster-whisper

import structlog
import numpy as np
from typing import Optional
from faster_whisper import WhisperModel

log = structlog.get_logger()

class Transcriber:
    """Transcribe audio using faster-whisper."""

    def __init__(self, whisper_config: dict):
        """Initialize WhisperModel with auto-detected device/compute settings."""
        self.config = whisper_config

        # Auto-detect device and compute type
        self.device, self.compute_type = self._detect_device_and_compute()

        log.info(
            "whisper_initializing",
            model=self.config["model"],
            device=self.device,
            compute_type=self.compute_type,
        )

        try:
            self.model = WhisperModel(
                self.config["model"],
                device=self.device,
                compute_type=self.compute_type,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load Whisper model: {e}")

        log.info("whisper_model_loaded", model=self.config["model"])

    def _detect_device_and_compute(self) -> tuple[str, str]:
        """Auto-detect device and compute_type if set to 'auto'."""
        device = self.config.get("device", "auto")
        compute_type = self.config.get("compute_type", "auto")

        if device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"

        if compute_type == "auto":
            # float16 for GPU, int8 for CPU (memory efficient)
            compute_type = "float16" if device == "cuda" else "int8"

        return device, compute_type

    def transcribe(self, audio_int16: np.ndarray, sample_rate: int) -> str:
        """Transcribe audio to text.

        Uses convert_to_whisper_format() to convert int16 to float32.
        Joins all segments into a single string.
        """
        if sample_rate != 16000:
            raise ValueError(f"Sample rate must be 16000, got {sample_rate}")

        # Convert audio format
        from talk_it_out.framework import audio
        audio_float32 = audio.convert_to_whisper_format(audio_int16, sample_rate)

        # Transcribe
        import time
        start_time = time.time()

        segments, info = self.model.transcribe(
            audio_float32,
            language=self.config.get("language", "en"),
            beam_size=self.config.get("beam_size", 5),
            vad_filter=self.config.get("vad_filter", True),
        )

        # Join segments
        text_parts = [segment.text for segment in segments]
        text = " ".join(text_parts).strip()

        duration_ms = (time.time() - start_time) * 1000

        log.info(
            "transcription_complete",
            text_length=len(text),
            segments=len(text_parts),
            detected_language=info.language,
            language_probability=info.language_probability,
            duration_ms=int(duration_ms),
        )

        log.debug("transcription_text", text=text[:200])  # First 200 chars

        return text
```

**Testing:**
- Mock WhisperModel to avoid actual model loading in tests
- Test device/compute auto-detection logic
- Verify convert_to_whisper_format() is called
- Test segment joining and text stripping

---

### Phase 3: Main Integration

**Goal:** Integrate Transcriber into main event loop

**Components:**
- `src/talk_it_out/main.py`

**Changes:**

1. Add import (line ~11):
```python
from talk_it_out.framework import (
    config, config_io, logging_setup, permissions, signals,
    keyboard, keyboard_io, audio, audio_io, audio_deps,
    whisper_io  # NEW
)
```

2. Initialize Transcriber after AudioRecorder (line ~78):
```python
# Initialize audio recorder
audio_recorder = audio_io.AudioRecorder(
    sample_rate=cfg["audio"]["sample_rate"],
    channels=cfg["audio"]["channels"],
    device=cfg["audio"]["device"]
)

# Initialize transcriber (NEW)
try:
    transcriber = whisper_io.Transcriber(cfg["whisper"])
    log.info(
        "transcriber_initialized",
        model=cfg["whisper"]["model"],
        device=transcriber.device,
        compute_type=transcriber.compute_type,
    )
except RuntimeError as e:
    print(f"❌ Failed to load Whisper model: {e}", file=sys.stderr)
    print("   This may be the first run. Ensure internet connectivity for model download.", file=sys.stderr)
    sys.exit(1)
```

3. Add transcription after audio validation (line ~110):
```python
if combo_event.combo_type == 'record_for_paste':
    audio_data = audio_recorder.stop_recording()

    valid, error = audio.validate_audio_data(audio_data)
    if not valid:
        log.warning("audio_invalid", reason=error)
    else:
        # Optional: Save debug audio
        if cfg["whisper"].get("save_debug_audio", False):
            wav_path = audio_recorder.save_wav(audio_data)
            log.debug("debug_audio_saved", wav_path=str(wav_path))

        # Transcribe audio (NEW)
        try:
            text = transcriber.transcribe(audio_data, cfg["audio"]["sample_rate"])
            if not text:
                log.warning("transcription_empty", reason="No speech detected")
            else:
                log.info("transcription_result", text=text[:100])  # First 100 chars
                # TODO: Paste text into focused window (Phase 5)
        except Exception as e:
            log.warning("transcription_failed", error=str(e))
```

**Testing:**
- Integration test: Record audio, verify transcription is called
- Error handling test: Trigger transcription failure, verify graceful handling
- Debug audio test: Enable save_debug_audio, verify WAV is saved

---

### Phase 4: Unit Tests

**Goal:** Comprehensive test coverage for Transcriber

**Components:**
- `tests/framework/test_whisper_io.py` (new file)

**Test cases:**

```python
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from talk_it_out.framework.whisper_io import Transcriber


def test_device_auto_detect_cuda_available():
    """Auto-detect should use CUDA when available."""
    with patch('faster_whisper.WhisperModel'):
        with patch('torch.cuda.is_available', return_value=True):
            transcriber = Transcriber({"model": "tiny", "device": "auto", "compute_type": "auto"})
            assert transcriber.device == "cuda"
            assert transcriber.compute_type == "float16"


def test_device_auto_detect_cuda_unavailable():
    """Auto-detect should fall back to CPU when CUDA unavailable."""
    with patch('faster_whisper.WhisperModel'):
        with patch('torch.cuda.is_available', return_value=False):
            transcriber = Transcriber({"model": "tiny", "device": "auto", "compute_type": "auto"})
            assert transcriber.device == "cpu"
            assert transcriber.compute_type == "int8"


def test_device_auto_detect_no_torch():
    """Auto-detect should fall back to CPU when torch not installed."""
    with patch('faster_whisper.WhisperModel'):
        with patch('builtins.__import__', side_effect=ImportError):
            transcriber = Transcriber({"model": "tiny", "device": "auto", "compute_type": "auto"})
            assert transcriber.device == "cpu"
            assert transcriber.compute_type == "int8"


def test_explicit_device_cuda():
    """Should use explicit device setting."""
    with patch('faster_whisper.WhisperModel'):
        transcriber = Transcriber({"model": "tiny", "device": "cuda", "compute_type": "float16"})
        assert transcriber.device == "cuda"
        assert transcriber.compute_type == "float16"


def test_transcribe_calls_convert_format():
    """Should use convert_to_whisper_format for audio conversion."""
    with patch('faster_whisper.WhisperModel') as mock_model_class:
        mock_model = Mock()
        mock_model.transcribe.return_value = ([], Mock(language="en", language_probability=0.99))
        mock_model_class.return_value = mock_model

        with patch('talk_it_out.framework.audio.convert_to_whisper_format') as mock_convert:
            mock_convert.return_value = np.zeros(16000, dtype=np.float32)

            transcriber = Transcriber({"model": "tiny", "language": "en"})
            audio_int16 = np.zeros(16000, dtype=np.int16)
            transcriber.transcribe(audio_int16, 16000)

            mock_convert.assert_called_once_with(audio_int16, 16000)


def test_transcribe_joins_segments():
    """Should join all segments with spaces."""
    with patch('faster_whisper.WhisperModel') as mock_model_class:
        mock_model = Mock()

        # Create mock segments
        segment1 = Mock(text="Hello")
        segment2 = Mock(text="world")
        segment3 = Mock(text="today")

        mock_info = Mock(language="en", language_probability=0.99)
        mock_model.transcribe.return_value = ([segment1, segment2, segment3], mock_info)
        mock_model_class.return_value = mock_model

        with patch('talk_it_out.framework.audio.convert_to_whisper_format'):
            transcriber = Transcriber({"model": "tiny", "language": "en"})
            audio_int16 = np.zeros(16000, dtype=np.int16)
            result = transcriber.transcribe(audio_int16, 16000)

            assert result == "Hello world today"


def test_transcribe_strips_whitespace():
    """Should strip leading/trailing whitespace."""
    with patch('faster_whisper.WhisperModel') as mock_model_class:
        mock_model = Mock()
        segment = Mock(text="  Hello world  ")
        mock_info = Mock(language="en", language_probability=0.99)
        mock_model.transcribe.return_value = ([segment], mock_info)
        mock_model_class.return_value = mock_model

        with patch('talk_it_out.framework.audio.convert_to_whisper_format'):
            transcriber = Transcriber({"model": "tiny", "language": "en"})
            audio_int16 = np.zeros(16000, dtype=np.int16)
            result = transcriber.transcribe(audio_int16, 16000)

            assert result == "Hello world"


def test_transcribe_invalid_sample_rate():
    """Should raise ValueError for wrong sample rate."""
    with patch('faster_whisper.WhisperModel'):
        transcriber = Transcriber({"model": "tiny", "language": "en"})
        audio_int16 = np.zeros(16000, dtype=np.int16)

        with pytest.raises(ValueError, match="Sample rate must be 16000"):
            transcriber.transcribe(audio_int16, 44100)


def test_model_load_failure():
    """Should raise RuntimeError if model fails to load."""
    with patch('faster_whisper.WhisperModel', side_effect=Exception("Network error")):
        with pytest.raises(RuntimeError, match="Failed to load Whisper model"):
            Transcriber({"model": "turbo", "language": "en"})
```

**Testing:**
- Run with: `uv run pytest tests/framework/test_whisper_io.py -v`
- All tests should use mocks (no actual model loading)
- Fast execution (< 1 second total)

---

### Phase 5: Manual Testing & Documentation

**Goal:** Verify end-to-end transcription with real audio

**Manual test procedure:**

1. Start application:
```bash
uv run python -m talk_it_out.main run --log-level DEBUG
```

2. First run: Verify model download message appears
3. Hold configured combo and speak: "Hello world, this is a test"
4. Release combo
5. Check logs for transcription output
6. Verify transcribed text matches spoken words

**Update documentation:**
- Add to `docs/MANUAL_TESTING.md`:
  - Whisper transcription test cases
  - Model download verification
  - Accuracy assessment procedure

- Update `README.md`:
  - Mention model download on first run
  - Document whisper config options
  - Add transcription examples

**Testing:**
- Test with different model sizes (tiny for speed, turbo for accuracy)
- Test with CUDA enabled/disabled
- Test with vad_filter enabled/disabled
- Test with different languages
- Verify debug audio saving works when enabled

---

## Additional Considerations

### Model Download Strategy

- **First run:** 30s-2min download depending on connection
- **No progress indicator** (faster-whisper doesn't expose download progress)
- **Future:** Could be a post-install step in RPM package
- **Error handling:** Clear message if internet unavailable on first run

### Memory Usage

- **turbo model:** ~809MB disk, ~1-2GB RAM during inference
- **Startup time:** ~5-10s for model loading (eager initialization)
- **Trade-off:** Slower startup vs instant first transcription

### Configuration Complexity

All advanced options exposed in config.toml:
- **Simple use:** Defaults work well (turbo, auto device, en language)
- **Advanced use:** Can tune beam_size, vad_filter, compute_type for quality/speed
- **Documentation needed:** Explain what each option does

### Future Extensions

- Configurable model download location
- Support for distil-large-v3 (distilled model)
- Word-level timestamps (for advanced features)
- Streaming transcription (for very long audio)
- Custom vocabulary/prompts for domain-specific terms
