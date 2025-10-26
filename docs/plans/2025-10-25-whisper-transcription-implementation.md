# Whisper Transcription Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task OR superpowers:subagent-driven-development for subagent execution.

**Goal:** Integrate faster-whisper library to transcribe recorded audio to text

**Architecture:** Single Transcriber class (Imperative Shell) that manages WhisperModel, device auto-detection, and transcription execution

**Tech Stack:** faster-whisper, NumPy, PyTorch (for CUDA detection)

**Scope:** 6 phases (Phase 0-5) from original design

**Codebase verified:** 2025-10-25

---

## Phase 0: Configuration Expansion

### Task 1: Update Whisper Configuration Defaults

**Files:**
- Modify: `src/talk_it_out/framework/config.py:37-40`
- Modify: `src/talk_it_out/framework/config.py:50`
- Test: Run existing tests to verify defaults load

**Step 1: Update DEFAULT_CONFIG whisper section**

In `src/talk_it_out/framework/config.py`, replace lines 37-40:

```python
"whisper": {
    "model": "turbo",
    "language": "en",
    "device": "auto",
    "compute_type": "auto",
    "beam_size": 5,
    "vad_filter": True,
    "save_debug_audio": False,
},
```

**Step 2: Add "turbo" to VALID_WHISPER_MODELS**

In `src/talk_it_out/framework/config.py`, replace line 50:

```python
VALID_WHISPER_MODELS = ["tiny", "base", "small", "medium", "large", "turbo"]
```

**Step 3: Run existing tests to verify changes**

Run: `uv run pytest tests/framework/test_config.py::test_default_config_whisper_section -v`

Expected: Test will FAIL because test expects old values

**Step 4: Update test to match new defaults**

In `tests/framework/test_config.py`, find test around line 55-60 and update assertions:

```python
def test_default_config_whisper_section():
    """Test that default config includes whisper section with all required keys."""
    cfg = config.get_default_config()

    assert "whisper" in cfg
    assert cfg["whisper"]["model"] == "turbo"
    assert cfg["whisper"]["language"] == "en"
    assert cfg["whisper"]["device"] == "auto"
    assert cfg["whisper"]["compute_type"] == "auto"
    assert cfg["whisper"]["beam_size"] == 5
    assert cfg["whisper"]["vad_filter"] is True
    assert cfg["whisper"]["save_debug_audio"] is False
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/framework/test_config.py::test_default_config_whisper_section -v`

Expected: PASS

**Step 6: Commit**

```bash
git add src/talk_it_out/framework/config.py tests/framework/test_config.py
git commit -m "feat: expand whisper config with device, compute_type, beam_size, vad_filter, save_debug_audio"
```

---

### Task 2: Add Config Validation for New Whisper Options

**Files:**
- Modify: `src/talk_it_out/framework/config.py:123-127` (extend validation section)
- Test: `tests/framework/test_config.py` (new tests)

**Step 1: Write failing test for device validation**

Add to `tests/framework/test_config.py`:

```python
def test_validate_config_rejects_invalid_whisper_device():
    """Test that validate_config rejects invalid whisper.device values."""
    cfg = config.get_default_config()
    cfg["whisper"]["device"] = "invalid"

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("whisper.device" in err for err in errors)


def test_validate_config_accepts_valid_whisper_devices():
    """Test that validate_config accepts all valid device values."""
    cfg = config.get_default_config()

    for device in ["auto", "cuda", "cpu"]:
        cfg["whisper"]["device"] = device
        errors = config.validate_config(cfg)
        assert len(errors) == 0, f"device={device} should be valid"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/framework/test_config.py::test_validate_config_rejects_invalid_whisper_device -v`

Expected: FAIL - validation not implemented

**Step 3: Implement device validation**

In `src/talk_it_out/framework/config.py`, after line 127, add:

```python
# Validate whisper.device
VALID_DEVICES = ["auto", "cuda", "cpu"]
if "device" in cfg.get("whisper", {}):
    if cfg["whisper"]["device"] not in VALID_DEVICES:
        errors.append(
            f"Invalid whisper.device: {cfg['whisper']['device']}. "
            f"Must be one of: {VALID_DEVICES}"
        )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/framework/test_config.py::test_validate_config_rejects_invalid_whisper_device tests/framework/test_config.py::test_validate_config_accepts_valid_whisper_devices -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/config.py tests/framework/test_config.py
git commit -m "feat: add whisper.device validation"
```

---

### Task 3: Add Compute Type Validation

**Files:**
- Modify: `src/talk_it_out/framework/config.py` (extend validation)
- Test: `tests/framework/test_config.py` (new tests)

**Step 1: Write failing test**

Add to `tests/framework/test_config.py`:

```python
def test_validate_config_rejects_invalid_compute_type():
    """Test that validate_config rejects invalid whisper.compute_type values."""
    cfg = config.get_default_config()
    cfg["whisper"]["compute_type"] = "invalid"

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("whisper.compute_type" in err for err in errors)


def test_validate_config_accepts_valid_compute_types():
    """Test that validate_config accepts all valid compute_type values."""
    cfg = config.get_default_config()

    valid_types = ["auto", "int8", "int8_float32", "int8_float16",
                   "int16", "float16", "float32"]
    for compute_type in valid_types:
        cfg["whisper"]["compute_type"] = compute_type
        errors = config.validate_config(cfg)
        assert len(errors) == 0, f"compute_type={compute_type} should be valid"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/framework/test_config.py::test_validate_config_rejects_invalid_compute_type -v`

Expected: FAIL

**Step 3: Implement compute_type validation**

In `src/talk_it_out/framework/config.py`, after device validation, add:

```python
# Validate whisper.compute_type
VALID_COMPUTE_TYPES = [
    "auto", "int8", "int8_float32", "int8_float16",
    "int16", "float16", "float32"
]
if "compute_type" in cfg.get("whisper", {}):
    if cfg["whisper"]["compute_type"] not in VALID_COMPUTE_TYPES:
        errors.append(
            f"Invalid whisper.compute_type: {cfg['whisper']['compute_type']}. "
            f"Must be one of: {VALID_COMPUTE_TYPES}"
        )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/framework/test_config.py::test_validate_config_rejects_invalid_compute_type tests/framework/test_config.py::test_validate_config_accepts_valid_compute_types -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/config.py tests/framework/test_config.py
git commit -m "feat: add whisper.compute_type validation"
```

---

### Task 4: Add Beam Size Validation

**Files:**
- Modify: `src/talk_it_out/framework/config.py`
- Test: `tests/framework/test_config.py`

**Step 1: Write failing test**

Add to `tests/framework/test_config.py`:

```python
def test_validate_config_rejects_invalid_beam_size():
    """Test that validate_config rejects beam_size outside 1-10 range."""
    cfg = config.get_default_config()

    # Test below range
    cfg["whisper"]["beam_size"] = 0
    errors = config.validate_config(cfg)
    assert len(errors) > 0
    assert any("whisper.beam_size" in err for err in errors)

    # Test above range
    cfg["whisper"]["beam_size"] = 11
    errors = config.validate_config(cfg)
    assert len(errors) > 0
    assert any("whisper.beam_size" in err for err in errors)


def test_validate_config_accepts_valid_beam_sizes():
    """Test that validate_config accepts beam_size in 1-10 range."""
    cfg = config.get_default_config()

    for beam_size in [1, 5, 10]:
        cfg["whisper"]["beam_size"] = beam_size
        errors = config.validate_config(cfg)
        assert len(errors) == 0, f"beam_size={beam_size} should be valid"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/framework/test_config.py::test_validate_config_rejects_invalid_beam_size -v`

Expected: FAIL

**Step 3: Implement beam_size validation**

In `src/talk_it_out/framework/config.py`, after compute_type validation, add:

```python
# Validate whisper.beam_size
if "beam_size" in cfg.get("whisper", {}):
    beam_size = cfg["whisper"]["beam_size"]
    if not isinstance(beam_size, int) or beam_size < 1 or beam_size > 10:
        errors.append(
            f"Invalid whisper.beam_size: {beam_size}. "
            "Must be an integer between 1 and 10."
        )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/framework/test_config.py::test_validate_config_rejects_invalid_beam_size tests/framework/test_config.py::test_validate_config_accepts_valid_beam_sizes -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/config.py tests/framework/test_config.py
git commit -m "feat: add whisper.beam_size validation (1-10 range)"
```

---

### Task 5: Add Boolean Field Validation

**Files:**
- Modify: `src/talk_it_out/framework/config.py`
- Test: `tests/framework/test_config.py`

**Step 1: Write failing tests**

Add to `tests/framework/test_config.py`:

```python
def test_validate_config_rejects_non_boolean_vad_filter():
    """Test that validate_config rejects non-boolean vad_filter."""
    cfg = config.get_default_config()
    cfg["whisper"]["vad_filter"] = "true"  # String instead of bool

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("whisper.vad_filter" in err for err in errors)


def test_validate_config_rejects_non_boolean_save_debug_audio():
    """Test that validate_config rejects non-boolean save_debug_audio."""
    cfg = config.get_default_config()
    cfg["whisper"]["save_debug_audio"] = 1  # Int instead of bool

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("whisper.save_debug_audio" in err for err in errors)


def test_validate_config_accepts_boolean_whisper_flags():
    """Test that validate_config accepts boolean values for flags."""
    cfg = config.get_default_config()

    cfg["whisper"]["vad_filter"] = True
    cfg["whisper"]["save_debug_audio"] = False
    errors = config.validate_config(cfg)
    assert len(errors) == 0

    cfg["whisper"]["vad_filter"] = False
    cfg["whisper"]["save_debug_audio"] = True
    errors = config.validate_config(cfg)
    assert len(errors) == 0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/framework/test_config.py::test_validate_config_rejects_non_boolean_vad_filter -v`

Expected: FAIL

**Step 3: Implement boolean validation**

In `src/talk_it_out/framework/config.py`, after beam_size validation, add:

```python
# Validate whisper.vad_filter (boolean)
if "vad_filter" in cfg.get("whisper", {}):
    if not isinstance(cfg["whisper"]["vad_filter"], bool):
        errors.append(
            f"Invalid whisper.vad_filter: {cfg['whisper']['vad_filter']}. "
            "Must be a boolean (true or false)."
        )

# Validate whisper.save_debug_audio (boolean)
if "save_debug_audio" in cfg.get("whisper", {}):
    if not isinstance(cfg["whisper"]["save_debug_audio"], bool):
        errors.append(
            f"Invalid whisper.save_debug_audio: {cfg['whisper']['save_debug_audio']}. "
            "Must be a boolean (true or false)."
        )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/framework/test_config.py::test_validate_config_rejects_non_boolean_vad_filter tests/framework/test_config.py::test_validate_config_rejects_non_boolean_save_debug_audio tests/framework/test_config.py::test_validate_config_accepts_boolean_whisper_flags -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/config.py tests/framework/test_config.py
git commit -m "feat: add whisper.vad_filter and save_debug_audio boolean validation"
```

---

### Task 6: Run All Tests to Verify Phase Complete

**Step 1: Run all config tests**

Run: `uv run pytest tests/framework/test_config.py -v`

Expected: All tests PASS

**Step 2: Run full test suite to ensure no regressions**

Run: `uv run pytest`

Expected: All 60 existing tests PASS (no new failures introduced)

**Step 3: Manual verification of config file**

Run: `uv run python -c "from talk_it_out.framework import config; import json; print(json.dumps(config.get_default_config()['whisper'], indent=2))"`

Expected output:
```json
{
  "model": "turbo",
  "language": "en",
  "device": "auto",
  "compute_type": "auto",
  "beam_size": 5,
  "vad_filter": true,
  "save_debug_audio": false
}
```

---

## Phase 1: Dependencies

### Task 1: Add faster-whisper Dependency

**Files:**
- Modify: `pyproject.toml` (uv will update this automatically)

**Step 1: Add faster-whisper using uv**

Run: `uv add faster-whisper`

Expected: Command succeeds, `pyproject.toml` updated with faster-whisper in `[project.dependencies]`

**Step 2: Verify installation**

Run: `uv run python -c "from faster_whisper import WhisperModel; print('faster-whisper installed successfully')"`

Expected output: `faster-whisper installed successfully`

**Step 3: Check installed version**

Run: `uv run python -c "import faster_whisper; print(f'faster-whisper version: {faster_whisper.__version__}')"`

Expected: Prints version number (likely 1.2.0 or newer)

**Step 4: Verify torch dependency (faster-whisper requires it)**

Run: `uv run python -c "import torch; print(f'torch available: {torch.cuda.is_available()}')"`

Expected: Prints `torch available: True` (if CUDA) or `torch available: False` (CPU only)

**Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add faster-whisper for audio transcription"
```

---

## Phase 2: Transcriber Implementation

### Task 1: Create Transcriber Class Skeleton

**Files:**
- Create: `src/talk_it_out/framework/whisper_io.py`

**Step 1: Create file with pattern declaration and imports**

Create `src/talk_it_out/framework/whisper_io.py`:

```python
# pattern: Imperative Shell
# Whisper transcription with faster-whisper

import time
import structlog
import numpy as np
from typing import Optional
from faster_whisper import WhisperModel
from talk_it_out.framework.audio import convert_to_whisper_format

log = structlog.get_logger()


class Transcriber:
    """Transcribe audio using faster-whisper."""

    def __init__(self, whisper_config: dict):
        """Initialize WhisperModel with auto-detected device/compute settings.

        Args:
            whisper_config: Dict with keys: model, language, device,
                          compute_type, beam_size, vad_filter

        Raises:
            RuntimeError: If model fails to load
        """
        pass

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
        pass
```

**Step 2: Verify file imports correctly**

Run: `uv run python -c "from talk_it_out.framework.whisper_io import Transcriber; print('Import successful')"`

Expected output: `Import successful`

**Step 3: Commit skeleton**

```bash
git add src/talk_it_out/framework/whisper_io.py
git commit -m "feat: add Transcriber class skeleton for whisper integration"
```

---

### Task 2: Implement Device Auto-Detection

**Files:**
- Modify: `src/talk_it_out/framework/whisper_io.py`

**Step 1: Add _detect_device_and_compute method**

In `whisper_io.py`, add after the class definition, before `__init__`:

```python
def _detect_device_and_compute(self) -> tuple[str, str]:
    """Auto-detect device and compute_type if set to 'auto'.

    Returns:
        Tuple of (device, compute_type)
    """
    device = self.config.get("device", "auto")
    compute_type = self.config.get("compute_type", "auto")

    if device == "auto":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            log.debug("device_auto_detected", device=device, cuda_available=torch.cuda.is_available())
        except ImportError:
            device = "cpu"
            log.debug("device_auto_detected", device="cpu", reason="torch_not_available")

    if compute_type == "auto":
        # float16 for GPU, int8 for CPU (memory efficient)
        compute_type = "float16" if device == "cuda" else "int8"
        log.debug("compute_type_auto_selected", compute_type=compute_type, device=device)

    return device, compute_type
```

**Step 2: Implement __init__ to use device detection**

Replace the `pass` in `__init__` with:

```python
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
    log.info("whisper_model_loaded", model=self.config["model"])
except Exception as e:
    log.error("whisper_model_load_failed", error=str(e))
    raise RuntimeError(f"Failed to load Whisper model: {e}")
```

**Step 3: Test instantiation (will fail gracefully without model download)**

Run: `uv run python -c "from talk_it_out.framework.whisper_io import Transcriber; cfg = {'model': 'tiny', 'device': 'cpu', 'compute_type': 'int8'}; print('Instantiation works (model download will occur)')"`

Expected: Code runs without import errors (model download may start)

**Step 4: Commit**

```bash
git add src/talk_it_out/framework/whisper_io.py
git commit -m "feat: implement device auto-detection for Transcriber"
```

---

### Task 3: Implement Transcribe Method

**Files:**
- Modify: `src/talk_it_out/framework/whisper_io.py`

**Step 1: Implement transcribe method**

Replace the `pass` in `transcribe()` with:

```python
if sample_rate != 16000:
    raise ValueError(f"Sample rate must be 16000, got {sample_rate}")

# Convert int16 to float32 format for Whisper
audio_float32 = convert_to_whisper_format(audio_int16, sample_rate)

# Transcribe
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
    language_probability=round(info.language_probability, 3),
    duration_ms=int(duration_ms),
)

log.debug("transcription_text", text=text[:200])  # First 200 chars

return text
```

**Step 2: Test transcribe with sample audio (basic smoke test)**

Run: `uv run python -c "import numpy as np; from talk_it_out.framework.whisper_io import Transcriber; cfg = {'model': 'tiny', 'language': 'en', 'device': 'cpu', 'compute_type': 'int8', 'beam_size': 5, 'vad_filter': False}; t = Transcriber(cfg); audio = np.zeros(16000, dtype=np.int16); result = t.transcribe(audio, 16000); print(f'Result: {result}')"`

Expected: Model downloads (first run), transcribes silence (likely returns empty string or noise artifacts)

**Step 3: Test sample rate validation**

Run: `uv run python -c "import numpy as np; from talk_it_out.framework.whisper_io import Transcriber; cfg = {'model': 'tiny', 'language': 'en', 'device': 'cpu', 'compute_type': 'int8'}; t = Transcriber(cfg); audio = np.zeros(16000, dtype=np.int16); t.transcribe(audio, 44100)"`

Expected: Raises `ValueError: Sample rate must be 16000, got 44100`

**Step 4: Commit**

```bash
git add src/talk_it_out/framework/whisper_io.py
git commit -m "feat: implement Transcriber.transcribe() with segment joining and logging"
```

---

### Task 4: Verify Complete Implementation

**Step 1: Read final whisper_io.py to verify completeness**

Run: `uv run python -c "with open('src/talk_it_out/framework/whisper_io.py') as f: print(f.read()[:500])"`

Expected: Should see pattern comment, imports, Transcriber class with all methods

**Step 2: Test full instantiation and transcription**

Run: `uv run python -c "from talk_it_out.framework.whisper_io import Transcriber; cfg = {'model': 'tiny', 'language': 'en', 'device': 'auto', 'compute_type': 'auto', 'beam_size': 5, 'vad_filter': True}; print('Creating transcriber...'); t = Transcriber(cfg); print(f'Device: {t.device}, Compute: {t.compute_type}'); import numpy as np; audio = np.random.randint(-1000, 1000, 32000, dtype=np.int16); result = t.transcribe(audio, 16000); print(f'Transcribed {len(result)} chars')"`

Expected: Success, prints device/compute type, transcribes 2 seconds of noise

**Step 3: Run all existing tests to ensure no regressions**

Run: `uv run pytest`

Expected: All tests pass (whisper_io.py doesn't break anything)

---

## Phase 3: Main Integration

### Task 1: Add whisper_io Import

**Files:**
- Modify: `src/talk_it_out/main.py:11`

**Step 1: Add whisper_io to import statement**

In `src/talk_it_out/main.py`, replace line 11:

```python
from talk_it_out.framework import config, config_io, logging_setup, permissions, signals, keyboard, keyboard_io, audio, audio_io, whisper_io
```

**Step 2: Verify import works**

Run: `uv run python -c "import sys; exec(open('src/talk_it_out/main.py').readline()); print('Import verified')"`

Expected: No import errors

**Step 3: Commit**

```bash
git add src/talk_it_out/main.py
git commit -m "feat: add whisper_io to main.py imports"
```

---

### Task 2: Initialize Transcriber at Startup

**Files:**
- Modify: `src/talk_it_out/main.py:77` (insert after AudioRecorder init)

**Step 1: Add Transcriber initialization with error handling**

In `src/talk_it_out/main.py`, after line 77, insert:

```python

# Initialize transcriber
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

**Step 2: Test startup (will download model on first run)**

Run: `timeout 120 uv run python -m talk_it_out.main run --help`

Expected: Program starts, model loads (may download ~809MB), prints help and exits

**Step 3: Check startup logs for transcriber_initialized**

Run: `uv run python -m talk_it_out.main run --log-level INFO 2>&1 | head -20 | grep transcriber_initialized || echo "Looking for transcriber log..."`

Expected: Should see "transcriber_initialized" log entry with model, device, compute_type

**Step 4: Commit**

```bash
git add src/talk_it_out/main.py
git commit -m "feat: initialize Transcriber at startup with error handling"
```

---

### Task 3: Make WAV Saving Conditional

**Files:**
- Modify: `src/talk_it_out/main.py:110-112`

**Step 1: Replace unconditional WAV saving with conditional logic**

In `src/talk_it_out/main.py`, replace lines 110-112:

```python
# Optional: Save debug audio
if cfg["whisper"].get("save_debug_audio", False):
    wav_path = audio_recorder.save_wav(audio_data)
    log.debug("debug_audio_saved", wav_path=str(wav_path))
```

**Step 2: Verify conditional behavior (debug audio OFF)**

Run: `uv run python -c "from talk_it_out.framework import config; cfg = config.get_default_config(); print('save_debug_audio:', cfg['whisper'].get('save_debug_audio', False))"`

Expected output: `save_debug_audio: False`

**Step 3: Commit**

```bash
git add src/talk_it_out/main.py
git commit -m "refactor: make WAV saving conditional on save_debug_audio config"
```

---

### Task 4: Add Transcription Call

**Files:**
- Modify: `src/talk_it_out/main.py` (after conditional WAV saving, before end of combo_released handler)

**Step 1: Add transcription with error handling**

In `src/talk_it_out/main.py`, after the debug audio saving block, add:

```python

# Transcribe audio
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

**Step 2: Test end-to-end with manual recording**

Create a test script `test_transcription.py`:

```python
#!/usr/bin/env python3
import numpy as np
from talk_it_out.framework import config, whisper_io

# Load config
cfg = config.get_default_config()

# Create transcriber
transcriber = whisper_io.Transcriber(cfg["whisper"])

# Create 2 seconds of silence
audio_int16 = np.zeros(32000, dtype=np.int16)

# Transcribe
text = transcriber.transcribe(audio_int16, 16000)

print(f"Transcribed text: '{text}'")
print(f"Text length: {len(text)} chars")
```

Run: `uv run python test_transcription.py`

Expected: Transcribes silence (empty or minimal output)

**Step 3: Remove test script**

Run: `rm test_transcription.py`

**Step 4: Commit**

```bash
git add src/talk_it_out/main.py
git commit -m "feat: add transcription call after audio recording with error handling"
```

---

### Task 5: Verify Integration

**Step 1: Read modified combo_released handler to verify structure**

Run: `uv run python -c "with open('src/talk_it_out/main.py') as f: lines = f.readlines(); print(''.join(lines[94:125]))"`

Expected: Should see complete flow: combo_released → stop_recording → validate → optional debug save → transcribe

**Step 2: Run all tests**

Run: `uv run pytest`

Expected: All tests pass (no regressions from main.py changes)

**Step 3: Verify application starts successfully**

Run: `timeout 5 uv run python -m talk_it_out.main run --log-level DEBUG 2>&1 | head -30`

Expected:
- Application starts
- PortAudio check passes
- AudioRecorder initialized
- Transcriber initialized with device/model info
- Keyboard monitoring starts

---

## Phase 4: Unit Tests

### Task 1: Create Test File with Device Auto-Detection Tests

**Files:**
- Create: `tests/framework/test_whisper_io.py`

**Step 1: Write failing tests for device auto-detection**

Create `tests/framework/test_whisper_io.py`:

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
        def mock_import(name, *args, **kwargs):
            if name == 'torch':
                raise ImportError("No module named 'torch'")
            return __import__(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            transcriber = Transcriber({"model": "tiny", "device": "auto", "compute_type": "auto"})
            # Import error in detection, should default to CPU
            assert transcriber.device == "cpu"
            assert transcriber.compute_type == "int8"


def test_explicit_device_cuda():
    """Should use explicit device setting."""
    with patch('faster_whisper.WhisperModel'):
        transcriber = Transcriber({"model": "tiny", "device": "cuda", "compute_type": "float16"})
        assert transcriber.device == "cuda"
        assert transcriber.compute_type == "float16"
```

**Step 2: Run tests to verify they fail or pass**

Run: `uv run pytest tests/framework/test_whisper_io.py::test_device_auto_detect_cuda_available -v`

Expected: Tests may PASS if whisper_io.py is already correctly implemented

**Step 3: Commit**

```bash
git add tests/framework/test_whisper_io.py
git commit -m "test: add device auto-detection tests for Transcriber"
```

---

### Task 2: Add Transcription Behavior Tests

**Files:**
- Modify: `tests/framework/test_whisper_io.py`

**Step 1: Add tests for transcribe() method**

Append to `tests/framework/test_whisper_io.py`:

```python


def test_transcribe_calls_convert_format():
    """Should use convert_to_whisper_format for audio conversion."""
    with patch('faster_whisper.WhisperModel') as mock_model_class:
        mock_model = Mock()
        mock_model.transcribe.return_value = ([], Mock(language="en", language_probability=0.99))
        mock_model_class.return_value = mock_model

        with patch('talk_it_out.framework.whisper_io.convert_to_whisper_format') as mock_convert:
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

        with patch('talk_it_out.framework.whisper_io.convert_to_whisper_format'):
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

        with patch('talk_it_out.framework.whisper_io.convert_to_whisper_format'):
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

**Step 2: Run all whisper_io tests**

Run: `uv run pytest tests/framework/test_whisper_io.py -v`

Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/framework/test_whisper_io.py
git commit -m "test: add transcription behavior tests for Transcriber"
```

---

### Task 3: Verify All Tests Pass

**Step 1: Run full test suite**

Run: `uv run pytest`

Expected: All tests pass (60+ existing tests + ~10 new whisper_io tests)

**Step 2: Run only new tests with coverage info**

Run: `uv run pytest tests/framework/test_whisper_io.py -v --tb=short`

Expected: 10 tests pass, clear output showing what's tested

**Step 3: Verify no test warnings**

Run: `uv run pytest tests/framework/test_whisper_io.py -v 2>&1 | grep -i warning || echo "No warnings found"`

Expected: "No warnings found" or only deprecation warnings from dependencies

---

## Phase 5: Manual Testing & Documentation

### Task 1: Add Whisper Transcription Test Cases

**Files:**
- Modify: `docs/MANUAL_TESTING.md` (append new section)

**Step 1: Add Whisper Transcription Tests section**

Append to `docs/MANUAL_TESTING.md` (after section 6.3, before Test Results Template):

```markdown

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
```

**Step 2: Commit documentation**

```bash
git add docs/MANUAL_TESTING.md
git commit -m "docs: add Whisper transcription manual test cases"
```

---

### Task 2: Update README.md Status and Configuration

**Files:**
- Modify: `README.md`

**Step 1: Update Phase 4 status to completed**

In `README.md`, find the Status section (around line 30-38) and update:

```markdown
### Phase 3: Audio Recording ✅

Audio recording has been implemented and tested:
- Microphone audio capture during keyboard combo hold
- WAV file output to temporary location
- Audio validation (minimum duration, format checks)
- Comprehensive error handling

### Phase 4: Whisper Transcription ✅

Whisper transcription has been integrated:
- faster-whisper library integration
- GPU/CPU auto-detection with fallback
- Configurable model size, language, and parameters
- Audio transcription pipeline with logging
```

**Step 2: Expand Whisper configuration documentation**

In `README.md`, find the whisper config section (around lines 100-102) and replace with:

```toml
[whisper]
model = "turbo"              # Model size: tiny, base, small, medium, large, turbo
language = "en"              # Language code (e.g., "en", "es", "fr") or "" for auto-detect
device = "auto"              # Device: "auto", "cuda", "cpu"
compute_type = "auto"        # Precision: "auto", "int8", "float16", "float32"
beam_size = 5                # Search breadth (1-10, higher = better but slower)
vad_filter = true            # Voice activity detection (skip silence)
save_debug_audio = false     # Save WAV files to /tmp for debugging
```

**Step 3: Add Whisper Transcription usage section**

In `README.md`, after the Usage section (around line 76), add:

```markdown

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
```

**Step 4: Commit README updates**

```bash
git add README.md
git commit -m "docs: update README with Whisper transcription documentation"
```

---

### Task 3: Manual Verification

**Step 1: Test real transcription end-to-end**

Run: `uv run python -m talk_it_out.main run`

Then:
1. Hold your configured keyboard combo
2. Speak: "This is a manual test of whisper transcription"
3. Release combo
4. Check logs for transcription_result

Expected: Transcribed text appears in logs matching spoken words

**Step 2: Verify documentation accuracy**

Run: `uv run python -c "with open('docs/MANUAL_TESTING.md') as f: lines = f.readlines(); [print(l, end='') for l in lines if '## 7. Whisper' in l or (i > 0 and '## 7. Whisper' in lines[i-1]) for i, l in enumerate(lines)][:5]"`

Expected: Shows new Whisper Transcription Tests section

Run: `uv run python -c "with open('README.md') as f: content = f.read(); print('Phase 4 completed' if 'Phase 4: Whisper Transcription ✅' in content else 'Not found')"`

Expected: Shows "Phase 4 completed"

**Step 3: Run full test suite one final time**

Run: `uv run pytest`

Expected: All tests pass (including new whisper_io tests)

---
