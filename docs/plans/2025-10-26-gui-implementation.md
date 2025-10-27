# GUI Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Qt6 GUI mode with floating visual indicator and desktop notifications while maintaining CLI functionality.

**Architecture:** Session extraction pattern - extract event processing from main.py into reusable Session class, then build Qt6 GUI components (SessionWorker, RecordingIndicator, NotificationManager, TrayIcon) that integrate via Qt signals/slots.

**Tech Stack:** PyQt6 (Qt6 GUI framework), pydbus (D-Bus notifications), existing components (Session, KeyboardMonitor, AudioRecorder, Transcriber, OutputStrategy)

**Scope:** 8 phases from original design (complete implementation)

**Codebase verified:** 2025-10-26

**Key correction from verification:** Config path function is `config.get_config_path()` not `config_io.default_config_path()`

---

## Phase 1: Session Extraction

Extract event processing into reusable Session class, refactor CLI to use it.

### Task 1: Create Session Class Foundation

**Files:**
- Create: `src/talk_it_out/framework/session.py`
- Create: `tests/framework/test_session.py`

**Step 1: Write the failing test**

Create test file `tests/framework/test_session.py`:

```python
# pattern: Imperative Shell

import pytest
from talk_it_out.framework import session
from talk_it_out.framework import config


def test_session_initializes_with_config():
    """Session should initialize with config dict"""
    cfg = config.default_config()
    s = session.Session(cfg)
    assert s.config == cfg


def test_session_accepts_callbacks():
    """Session should accept optional callback functions"""
    cfg = config.default_config()
    called = []

    s = session.Session(
        cfg,
        on_recording_started=lambda: called.append("recording_started"),
        on_recording_stopped=lambda: called.append("recording_stopped"),
        on_transcription_started=lambda: called.append("transcription_started"),
        on_transcription_complete=lambda text: called.append(f"complete:{text}"),
        on_audio_level=lambda level: called.append(f"level:{level}"),
        on_error=lambda msg: called.append(f"error:{msg}")
    )

    # Verify callbacks stored
    assert s.on_recording_started is not None
    assert s.on_recording_stopped is not None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/framework/test_session.py -v`

Expected: FAIL with "No module named 'talk_it_out.framework.session'"

**Step 3: Write minimal Session class**

Create `src/talk_it_out/framework/session.py`:

```python
# pattern: Imperative Shell
"""
Session orchestrates keyboard monitoring, audio recording, transcription, and output.

Provides callback-based API for state changes, allowing both CLI (no callbacks) and
GUI (callbacks → Qt signals) usage patterns.
"""

from typing import Dict, Any, Optional, Callable
import structlog


class Session:
    """Orchestrates talk-it-out workflow with optional callbacks for state changes"""

    def __init__(
        self,
        app_config: Dict[str, Any],
        on_recording_started: Optional[Callable[[], None]] = None,
        on_recording_stopped: Optional[Callable[[], None]] = None,
        on_transcription_started: Optional[Callable[[], None]] = None,
        on_transcription_complete: Optional[Callable[[str], None]] = None,
        on_audio_level: Optional[Callable[[float], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        self.config = app_config
        self.log = structlog.get_logger()

        # Store callbacks
        self.on_recording_started = on_recording_started
        self.on_recording_stopped = on_recording_stopped
        self.on_transcription_started = on_transcription_started
        self.on_transcription_complete = on_transcription_complete
        self.on_audio_level = on_audio_level
        self.on_error = on_error
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/framework/test_session.py::test_session_initializes_with_config -v`

Expected: PASS

Run: `uv run pytest tests/framework/test_session.py::test_session_accepts_callbacks -v`

Expected: PASS

**Step 5: Commit**

```bash
git add tests/framework/test_session.py src/talk_it_out/framework/session.py
git commit -m "feat(session): add Session class foundation with callback support

- Session class accepts config and optional callbacks
- Callbacks: recording start/stop, transcription start/complete, audio level, errors
- Pattern: Imperative Shell (orchestration)
- Tests verify initialization and callback storage"
```

---

### Task 2: Add Component Initialization to Session

**Files:**
- Modify: `src/talk_it_out/framework/session.py`
- Modify: `tests/framework/test_session.py`

**Step 1: Write the failing test**

Add to `tests/framework/test_session.py`:

```python
from unittest.mock import Mock, patch


def test_session_initializes_components():
    """Session should initialize keyboard monitor, audio recorder, transcriber, output strategy"""
    cfg = config.default_config()

    with patch('talk_it_out.framework.keyboard_io.KeyboardMonitor') as mock_monitor, \
         patch('talk_it_out.framework.audio_io.AudioRecorder') as mock_audio, \
         patch('talk_it_out.framework.whisper_io.Transcriber') as mock_transcriber, \
         patch('talk_it_out.output.create_output_strategy') as mock_output:

        s = session.Session(cfg)

        # Verify components created
        mock_monitor.assert_called_once()
        mock_audio.assert_called_once()
        mock_transcriber.assert_called_once()
        mock_output.assert_called_once_with(cfg)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/framework/test_session.py::test_session_initializes_components -v`

Expected: FAIL with "AssertionError: expected call not found"

**Step 3: Implement component initialization**

Modify `src/talk_it_out/framework/session.py:__init__` (add after callback storage):

```python
from talk_it_out.framework import keyboard_io, audio_io, whisper_io, signals
from talk_it_out.output import create_output_strategy
from talk_it_out.framework import keyboard
import queue


class Session:
    def __init__(self, app_config: Dict[str, Any], ...):
        # ... existing callback storage ...

        # Initialize cleanup registry
        self.cleanup_registry = signals.CleanupRegistry()
        self.cleanup_registry.register(lambda: self.log.info("session_shutdown"))

        # Create combo queue
        self.combo_queue: queue.Queue[keyboard.ComboEvent] = queue.Queue()

        # Extract target combos from config
        target_combos = {}
        for combo_name, key_lists in app_config["keys"]["combos"].items():
            combo_type = keyboard.ComboType(combo_name)
            target_combos[combo_type] = [
                frozenset(keys) for keys in key_lists
            ]

        # Initialize keyboard monitor
        self.keyboard_monitor = keyboard_io.KeyboardMonitor(
            target_combos=target_combos,
            combo_queue=self.combo_queue
        )
        self.cleanup_registry.register(self.keyboard_monitor.stop)

        # Initialize audio recorder (with audio level callback)
        self.audio_recorder = audio_io.AudioRecorder(
            sample_rate=app_config["audio"]["sample_rate"],
            channels=app_config["audio"]["channels"],
            device=app_config["audio"]["device"],
            on_audio_level=self.on_audio_level  # Pass through callback
        )

        # Initialize transcriber
        self.transcriber = whisper_io.Transcriber(app_config["whisper"])

        # Initialize output strategy
        self.output_strategy = create_output_strategy(app_config)

        self.log.info("session_initialized", mode="unknown")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/framework/test_session.py::test_session_initializes_components -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/session.py tests/framework/test_session.py
git commit -m "feat(session): initialize all workflow components

- Initialize KeyboardMonitor, AudioRecorder, Transcriber, OutputStrategy
- Create combo_queue and extract target_combos from config
- Pass on_audio_level callback to AudioRecorder
- Register cleanup handlers in CleanupRegistry
- Tests verify component initialization via mocks"
```

---

### Task 3: Add Audio Level Callback to AudioRecorder

**Files:**
- Modify: `src/talk_it_out/framework/audio_io.py`
- Create: `tests/framework/test_audio_io.py`

**Step 1: Write the failing test**

Create `tests/framework/test_audio_io.py`:

```python
# pattern: Imperative Shell

import pytest
import numpy as np
from talk_it_out.framework import audio_io


def test_audio_recorder_accepts_audio_level_callback():
    """AudioRecorder should accept optional on_audio_level callback"""
    called = []

    recorder = audio_io.AudioRecorder(
        sample_rate=16000,
        channels=1,
        device=None,
        on_audio_level=lambda level: called.append(level)
    )

    assert recorder.on_audio_level is not None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/framework/test_audio_io.py::test_audio_recorder_accepts_audio_level_callback -v`

Expected: FAIL with "TypeError: __init__() got an unexpected keyword argument 'on_audio_level'"

**Step 3: Add on_audio_level parameter to AudioRecorder**

Modify `src/talk_it_out/framework/audio_io.py` line 37 (AudioRecorder.__init__):

```python
from typing import Callable, Optional

class AudioRecorder:
    def __init__(
        self,
        sample_rate: int,
        channels: int,
        device: Optional[int],
        on_audio_level: Optional[Callable[[float], None]] = None
    ):
        # ... existing initialization ...
        self.on_audio_level = on_audio_level
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/framework/test_audio_io.py::test_audio_recorder_accepts_audio_level_callback -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/audio_io.py tests/framework/test_audio_io.py
git commit -m "feat(audio_io): add on_audio_level callback parameter

- AudioRecorder accepts optional on_audio_level callback
- Callback will be called with normalized audio level (0.0-1.0)
- Tests verify callback parameter acceptance"
```

---

### Task 4: Implement Audio Level Calculation in Callback

**Files:**
- Modify: `src/talk_it_out/framework/audio_io.py`
- Modify: `tests/framework/test_audio_io.py`

**Step 1: Write the failing test**

Add to `tests/framework/test_audio_io.py`:

```python
from unittest.mock import Mock, patch


def test_audio_callback_reports_audio_level():
    """_audio_callback should calculate and report audio level"""
    levels = []

    recorder = audio_io.AudioRecorder(
        sample_rate=16000,
        channels=1,
        device=None,
        on_audio_level=lambda level: levels.append(level)
    )

    # Simulate audio data (int16, values 0-32768)
    # Loud audio: mean abs value ~16000
    loud_data = np.array([[16000], [16000], [16000]], dtype=np.int16)

    # Call the audio callback directly
    recorder.frames = []
    recorder._audio_callback(loud_data, len(loud_data), None, None)

    # Should have called callback with normalized level
    assert len(levels) == 1
    assert 0.0 <= levels[0] <= 1.0
    assert levels[0] > 0.4  # ~16000/32768 ≈ 0.49
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/framework/test_audio_io.py::test_audio_callback_reports_audio_level -v`

Expected: FAIL with "AssertionError: assert 0 == 1" (callback not called)

**Step 3: Add audio level calculation to _audio_callback**

Modify `src/talk_it_out/framework/audio_io.py` line 78-94 (_audio_callback method):

```python
def _audio_callback(self, indata, frames, time, status):
    """Callback invoked by sounddevice for each audio block"""
    if status:
        self.log.debug("audio_callback_status", status=str(status))

    # Store audio data
    self.frames.append(indata.copy())

    # Calculate and report audio level if callback provided
    if self.on_audio_level:
        # Normalize to 0.0-1.0 range (int16 max is 32768)
        level = float(np.abs(indata).mean() / 32768.0)
        self.on_audio_level(level)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/framework/test_audio_io.py::test_audio_callback_reports_audio_level -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/audio_io.py tests/framework/test_audio_io.py
git commit -m "feat(audio_io): calculate and report audio levels during recording

- _audio_callback calculates mean absolute amplitude
- Normalizes to 0.0-1.0 range (int16 max 32768)
- Calls on_audio_level callback if provided
- Tests verify level calculation with simulated audio data"
```

---

### Task 5: Add Session.start_monitoring() and Session.stop()

**Files:**
- Modify: `src/talk_it_out/framework/session.py`
- Modify: `tests/framework/test_session.py`

**Step 1: Write the failing test**

Add to `tests/framework/test_session.py`:

```python
def test_session_start_monitoring():
    """Session.start_monitoring() should start keyboard monitor"""
    cfg = config.default_config()

    with patch('talk_it_out.framework.keyboard_io.KeyboardMonitor') as mock_monitor_class:
        mock_monitor = Mock()
        mock_monitor_class.return_value = mock_monitor

        s = session.Session(cfg)
        s.start_monitoring()

        mock_monitor.start.assert_called_once()


def test_session_stop():
    """Session.stop() should trigger cleanup"""
    cfg = config.default_config()

    with patch('talk_it_out.framework.keyboard_io.KeyboardMonitor'):
        s = session.Session(cfg)

        # Mock the cleanup registry
        s.cleanup_registry.cleanup = Mock()

        s.stop()

        s.cleanup_registry.cleanup.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/framework/test_session.py::test_session_start_monitoring -v`

Expected: FAIL with "AttributeError: 'Session' object has no attribute 'start_monitoring'"

**Step 3: Implement start_monitoring() and stop() methods**

Add to `src/talk_it_out/framework/session.py`:

```python
class Session:
    # ... existing __init__ ...

    def start_monitoring(self) -> None:
        """Start keyboard monitoring (non-blocking)"""
        self.keyboard_monitor.start()
        self.log.info("session_monitoring_started")

    def stop(self) -> None:
        """Graceful shutdown via cleanup registry"""
        self.log.info("session_stopping")
        self.cleanup_registry.cleanup()
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/framework/test_session.py::test_session_start_monitoring -v`

Expected: PASS

Run: `uv run pytest tests/framework/test_session.py::test_session_stop -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/session.py tests/framework/test_session.py
git commit -m "feat(session): add start_monitoring and stop methods

- start_monitoring() starts keyboard monitor non-blocking
- stop() triggers cleanup registry for graceful shutdown
- Tests verify keyboard monitor.start() called and cleanup triggered"
```

---

### Task 6: Implement Session.process_combo_event()

**Files:**
- Modify: `src/talk_it_out/framework/session.py`
- Modify: `tests/framework/test_session.py`

**Step 1: Write the failing test**

Add to `tests/framework/test_session.py`:

```python
from talk_it_out.framework import keyboard


def test_session_process_combo_pressed():
    """Session should start recording on COMBO_PRESSED"""
    cfg = config.default_config()
    recording_started_called = []

    with patch('talk_it_out.framework.audio_io.AudioRecorder') as mock_audio_class:
        mock_audio = Mock()
        mock_audio_class.return_value = mock_audio

        s = session.Session(
            cfg,
            on_recording_started=lambda: recording_started_called.append(True)
        )

        event = keyboard.ComboEvent(
            type=keyboard.EventType.COMBO_PRESSED,
            combo_type=keyboard.ComboType("paste"),
            device_path="/dev/input/event0"
        )

        s.process_combo_event(event)

        # Should start recording and call callback
        mock_audio.start_recording.assert_called_once()
        assert recording_started_called == [True]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/framework/test_session.py::test_session_process_combo_pressed -v`

Expected: FAIL with "AttributeError: 'Session' object has no attribute 'process_combo_event'"

**Step 3: Implement process_combo_event() method**

Add to `src/talk_it_out/framework/session.py`:

```python
from talk_it_out.framework import keyboard, audio


class Session:
    # ... existing methods ...

    def process_combo_event(self, combo_event: keyboard.ComboEvent) -> None:
        """Process a single combo event (PUBLIC API for CLI and GUI)"""
        if combo_event.type == keyboard.EventType.COMBO_PRESSED:
            self._handle_combo_pressed(combo_event)
        elif combo_event.type == keyboard.EventType.COMBO_RELEASED:
            self._handle_combo_released(combo_event)

    def _handle_combo_pressed(self, combo_event: keyboard.ComboEvent) -> None:
        """Handle combo press: start recording"""
        self.log.info(
            "combo_activated",
            combo=combo_event.combo_type,
            device=combo_event.device_path
        )

        self.audio_recorder.start_recording()

        if self.on_recording_started:
            self.on_recording_started()

    def _handle_combo_released(self, combo_event: keyboard.ComboEvent) -> None:
        """Handle combo release: stop, transcribe, paste"""
        self.log.info(
            "combo_released",
            combo=combo_event.combo_type,
            device=combo_event.device_path
        )

        # Stop recording
        self.audio_recorder.stop_recording()

        if self.on_recording_stopped:
            self.on_recording_stopped()

        # Validate audio
        ok, error = audio.validate_audio_data(
            self.audio_recorder.frames,
            self.audio_recorder.sample_rate,
            min_duration_ms=self.config["audio"]["min_duration_ms"]
        )

        if not ok:
            self.log.warning("audio_invalid", reason=error)
            if self.on_error:
                self.on_error(f"Audio invalid: {error}")
            return

        # Save WAV
        wav_path = self.audio_recorder.save_wav()
        self.log.debug("audio_saved", path=str(wav_path))

        # Transcribe
        if self.on_transcription_started:
            self.on_transcription_started()

        try:
            text = self.transcriber.transcribe_from_wav(wav_path)
            self.log.info("transcription_complete", text_length=len(text))

            # Paste
            try:
                self.output_strategy.paste_text(text)
                self.log.info("paste_complete")

                if self.on_transcription_complete:
                    self.on_transcription_complete(text)
            except Exception as e:
                self.log.warning("paste_failed", error=str(e))
                if self.on_error:
                    self.on_error(f"Paste failed: {str(e)}")
        except Exception as e:
            self.log.warning("transcription_failed", error=str(e))
            if self.on_error:
                self.on_error(f"Transcription failed: {str(e)}")

        # Cleanup WAV unless debug mode
        if not self.config["audio"]["debug_save_audio"]:
            wav_path.unlink(missing_ok=True)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/framework/test_session.py::test_session_process_combo_pressed -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/session.py tests/framework/test_session.py
git commit -m "feat(session): implement process_combo_event workflow

- process_combo_event() handles COMBO_PRESSED and COMBO_RELEASED
- PRESSED: start recording, call on_recording_started callback
- RELEASED: stop, validate, transcribe, paste with callbacks
- Error handling: continue on non-critical errors, call on_error callback
- Tests verify recording started on combo press"
```

---

### Task 7: Refactor main.py to use Session

**Files:**
- Modify: `src/talk_it_out/main.py`

**Step 1: No test needed (integration test)**

This is a refactoring step. Manual verification that CLI still works.

**Step 2: Refactor run() command to use Session**

Modify `src/talk_it_out/main.py` lines 17-170:

```python
from talk_it_out.framework import session as session_module
import threading
import queue


@app.command()
def run(
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config file"),
    log_level: Optional[str] = typer.Option(None, "--log-level", "-l", help="Override log level"),
):
    """Start voice-to-text listener (default command)."""
    # Load config
    path = config_path or config.get_config_path()
    cfg = config_io.load_config(path)

    # Override log level if provided
    if log_level:
        cfg["logging"]["level"] = log_level.upper()

    # Setup logging
    log = logging_setup.configure_logging(cfg["logging"]["level"])
    log.info("application_started", config_path=str(path), mode="cli")

    # Check permissions
    ok, error = permissions.check_input_group()
    if not ok:
        print(error, file=sys.stderr)
        sys.exit(1)

    # Check dependencies
    ok, error = audio_deps.check_portaudio()
    if not ok:
        print(error, file=sys.stderr)
        sys.exit(1)

    # Create session (no callbacks for CLI)
    sess = session_module.Session(cfg)

    # Setup signal handlers for graceful shutdown
    stop_event = threading.Event()

    def signal_handler(signum, frame):
        log.info("shutdown_requested", signal=signum)
        stop_event.set()

    import signal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start monitoring
    sess.start_monitoring()
    log.info("keyboard_monitoring_started")

    # Event loop
    try:
        while not stop_event.is_set():
            try:
                combo_event = sess.combo_queue.get(timeout=1.0)
                sess.process_combo_event(combo_event)
            except queue.Empty:
                continue
    except KeyboardInterrupt:
        log.info("keyboard_interrupt")
    finally:
        sess.stop()
        log.info("application_stopped")
```

**Step 3: Manual verification**

Run: `uv run python -m talk_it_out.main run`

Expected: Application starts, keyboard monitoring active, Ctrl+C shuts down cleanly

**Step 4: Run existing tests**

Run: `uv run pytest tests/ -v`

Expected: All existing tests pass (if any exist)

**Step 5: Commit**

```bash
git add src/talk_it_out/main.py
git commit -m "refactor(main): use Session class in run() command

- Refactor run() to create Session instance
- Session handles all component initialization and event processing
- CLI mode uses no callbacks (Session works standalone)
- Event loop simplified: get from combo_queue, call process_combo_event()
- Maintain all existing behavior: permissions, dependencies, signal handling
- CLI functionality unchanged"
```

---

## Phase 2: GUI Subcommand Stub

Add `talk-it-out gui` subcommand that launches minimal Qt application.

### Task 1: Add PyQt6 Dependency

**Files:**
- Modify: `pyproject.toml` (via uv add command)

**Step 1: Add PyQt6 dependency**

Run: `uv add PyQt6`

Expected: PyQt6 added to dependencies, uv.lock updated

**Step 2: Verify installation**

Run: `uv run python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK')"`

Expected: Output "PyQt6 OK"

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add PyQt6 for GUI mode

- PyQt6 added via uv add
- Required for Qt6 GUI components in Phase 2-6"
```

---

### Task 2: Create GUI Module and Stub Entry Point

**Files:**
- Create: `src/talk_it_out/gui/__init__.py`
- Create: `src/talk_it_out/gui/gui_main.py`

**Step 1: Create GUI package init**

Create `src/talk_it_out/gui/__init__.py`:

```python
"""
GUI mode for talk-it-out using Qt6.

Provides floating indicator, system tray, and desktop notifications.
"""
```

**Step 2: Create GUI main stub**

Create `src/talk_it_out/gui/gui_main.py`:

```python
# pattern: Imperative Shell
"""
GUI mode entry point.

Launches Qt6 application with SessionWorker, RecordingIndicator, and system tray.
"""

from PyQt6.QtWidgets import QApplication
from typing import Optional
from pathlib import Path
import sys
import structlog


def main(config_path: Optional[Path] = None):
    """Launch GUI mode"""
    log = structlog.get_logger()
    log.info("gui_mode_starting", config_path=str(config_path) if config_path else "default")

    app = QApplication(sys.argv)
    app.setApplicationName("Talk It Out")
    app.setQuitOnLastWindowClosed(False)  # Tray mode

    # TODO: Initialize components (Phase 3-6)
    log.info("gui_mode_ready")
    print("GUI mode - coming soon (Ctrl+C to quit)")

    sys.exit(app.exec())
```

**Step 3: Manual test**

Run: `uv run python -m talk_it_out.gui.gui_main`

Expected: Qt application starts, prints message, waits for Ctrl+C

**Step 4: Commit**

```bash
git add src/talk_it_out/gui/__init__.py src/talk_it_out/gui/gui_main.py
git commit -m "feat(gui): add GUI module and stub entry point

- Create gui package with __init__.py
- gui_main.main() launches minimal Qt6 application
- QuitOnLastWindowClosed=False for tray mode
- Pattern: Imperative Shell"
```

---

### Task 3: Add GUI Subcommand to Main CLI

**Files:**
- Modify: `src/talk_it_out/main.py`

**Step 1: Add gui command after select-audio-device**

Modify `src/talk_it_out/main.py` (add after line 184):

```python
@app.command()
def gui(
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Run in GUI mode with floating indicator and system tray."""
    from talk_it_out.gui import gui_main
    gui_main.main(config_path)
```

**Step 2: Manual test**

Run: `uv run python -m talk_it_out.main gui`

Expected: GUI mode launches, shows "coming soon" message

Run: `uv run python -m talk_it_out.main run`

Expected: CLI mode still works (no regression)

**Step 3: Commit**

```bash
git add src/talk_it_out/main.py
git commit -m "feat(main): add gui subcommand

- Add gui() command to Typer app
- Accepts --config/-c flag like run() command
- Imports and calls gui_main.main()
- CLI mode unchanged"
```

---

## Phase 3: SessionWorker Threading

Integrate Session with Qt threading via SessionWorker.

### Task 1: Create SessionWorker with Qt Signals

**Files:**
- Create: `src/talk_it_out/gui/worker.py`

**Step 1: Create SessionWorker class**

Create `src/talk_it_out/gui/worker.py`:

```python
# pattern: Imperative Shell
"""
SessionWorker wraps Session for Qt threading.

Runs in QThread, emits Qt signals for GUI components to subscribe to.
"""

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer
from typing import Dict, Any
import queue
import structlog

from talk_it_out.framework import session as session_module


class SessionWorker(QObject):
    """Qt worker that wraps Session and emits signals for state changes"""

    # Qt signals for GUI components
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    transcription_started = pyqtSignal()
    transcription_complete = pyqtSignal(str)  # text
    audio_level_update = pyqtSignal(float)  # 0.0-1.0
    error_occurred = pyqtSignal(str)  # error message
    shutdown_complete = pyqtSignal()

    def __init__(self, app_config: Dict[str, Any]):
        super().__init__()  # No parent! Will be moved to thread

        self.log = structlog.get_logger()
        self.app_config = app_config
        self.session = None
        self.poll_timer = None

    @pyqtSlot()
    def start_monitoring(self):
        """Initialize Session and start monitoring (runs in worker thread)"""
        self.log.info("session_worker_starting")

        # Create Session with callbacks that emit Qt signals
        self.session = session_module.Session(
            self.app_config,
            on_recording_started=self._emit_recording_started,
            on_recording_stopped=self._emit_recording_stopped,
            on_transcription_started=self._emit_transcription_started,
            on_transcription_complete=self._emit_transcription_complete,
            on_audio_level=self._emit_audio_level,
            on_error=self._emit_error,
        )

        # Start keyboard monitoring
        self.session.start_monitoring()

        # Start QTimer to poll combo_queue
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll_events)
        self.poll_timer.start(100)  # Poll every 100ms

        self.log.info("session_worker_started")

    @pyqtSlot()
    def poll_events(self):
        """Poll combo_queue and process events (called by QTimer)"""
        if self.session is None:
            return

        try:
            combo_event = self.session.combo_queue.get_nowait()
            self.session.process_combo_event(combo_event)
        except queue.Empty:
            pass  # No event, continue

    @pyqtSlot()
    def stop(self):
        """Stop Session and cleanup (graceful shutdown)"""
        self.log.info("session_worker_stopping")

        if self.poll_timer:
            self.poll_timer.stop()

        if self.session:
            self.session.stop()

        self.shutdown_complete.emit()
        self.log.info("session_worker_stopped")

    # Callback methods that emit Qt signals
    def _emit_recording_started(self):
        self.recording_started.emit()

    def _emit_recording_stopped(self):
        self.recording_stopped.emit()

    def _emit_transcription_started(self):
        self.transcription_started.emit()

    def _emit_transcription_complete(self, text: str):
        self.transcription_complete.emit(text)

    def _emit_audio_level(self, level: float):
        self.audio_level_update.emit(level)

    def _emit_error(self, message: str):
        self.error_occurred.emit(message)
```

**Step 2: Manual test (deferred to integration)**

Testing deferred to Phase 7 integration testing

**Step 3: Commit**

```bash
git add src/talk_it_out/gui/worker.py
git commit -m "feat(gui): add SessionWorker for Qt threading

- SessionWorker wraps Session, emits Qt signals
- Signals: recording started/stopped, transcription, audio levels, errors
- QTimer polls combo_queue every 100ms
- Callbacks convert Session events to Qt signals
- Pattern: Imperative Shell"
```

---

### Task 2: Integrate SessionWorker into GUI Main

**Files:**
- Modify: `src/talk_it_out/gui/gui_main.py`

**Step 1: Update gui_main to use SessionWorker with threading**

Modify `src/talk_it_out/gui/gui_main.py`:

```python
# pattern: Imperative Shell
"""
GUI mode entry point.

Launches Qt6 application with SessionWorker, RecordingIndicator, and system tray.
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread
from typing import Optional
from pathlib import Path
import sys
import structlog
import signal

from talk_it_out.framework import config, config_io, logging_setup, permissions, audio_deps
from talk_it_out.gui.worker import SessionWorker


def main(config_path: Optional[Path] = None):
    """Launch GUI mode"""
    # Load config
    path = config_path or config.get_config_path()
    cfg = config_io.load_config(path)

    # Setup logging
    log = logging_setup.configure_logging(cfg["logging"]["level"])
    log.info("gui_mode_starting", config_path=str(path))

    # Check permissions
    ok, error = permissions.check_input_group()
    if not ok:
        print(error, file=sys.stderr)
        sys.exit(1)

    # Check dependencies
    ok, error = audio_deps.check_portaudio()
    if not ok:
        print(error, file=sys.stderr)
        sys.exit(1)

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Talk It Out")
    app.setQuitOnLastWindowClosed(False)  # Tray mode

    # Create SessionWorker (no parent!)
    worker = SessionWorker(cfg)

    # Create QThread
    thread = QThread()
    worker.moveToThread(thread)

    # Connect lifecycle signals
    thread.started.connect(worker.start_monitoring)
    worker.shutdown_complete.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    # Connect shutdown
    app.aboutToQuit.connect(worker.stop)

    # Setup signal handlers for Ctrl+C
    def signal_handler(signum, frame):
        log.info("shutdown_requested", signal=signum)
        app.quit()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start worker thread
    thread.start()
    log.info("gui_mode_ready")

    # TODO: Create indicator (Phase 4)
    # TODO: Create notifications (Phase 5)
    # TODO: Create tray icon (Phase 6)

    print("GUI mode running (Ctrl+C to quit)")
    sys.exit(app.exec())
```

**Step 2: Manual test**

Run: `uv run python -m talk_it_out.main gui`

Expected: GUI starts, SessionWorker thread starts, keyboard monitoring active, Ctrl+C shuts down cleanly

**Step 3: Commit**

```bash
git add src/talk_it_out/gui/gui_main.py
git commit -m "feat(gui): integrate SessionWorker with Qt threading

- Load config, check permissions and dependencies
- Create SessionWorker and move to QThread
- Connect lifecycle signals (started, finished, deleteLater)
- Setup signal handlers for graceful Ctrl+C shutdown
- Worker thread polls combo_queue, processes events
- Qt6 threading pattern: QThread + moveToThread()"
```

---

## Phase 4: Recording Indicator

Display floating pill indicator that changes color based on workflow state.

### Task 1: Create RecordingIndicator Widget

**Files:**
- Create: `src/talk_it_out/gui/indicator.py`

**Step 1: Create RecordingIndicator class**

Create `src/talk_it_out/gui/indicator.py`:

```python
# pattern: Imperative Shell
"""
RecordingIndicator: Floating pill-shaped overlay showing workflow state.

States:
- Hidden: Not visible (idle)
- Recording: Red pill, brightness varies with audio volume
- Transcribing: Blue pill, brightness pulses
"""

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QPainter, QColor
import math
import structlog


class RecordingIndicator(QWidget):
    """Floating pill indicator (48x12px) showing recording/transcription state"""

    def __init__(self):
        super().__init__()

        self.log = structlog.get_logger()

        # Window configuration for floating overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Fixed size: 48px × 12px pill
        self.setFixedSize(48, 12)

        # State tracking
        self.state = "hidden"  # "hidden", "recording", "transcribing"
        self.audio_level = 0.0  # 0.0-1.0

        # Pulsing for transcribing state
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self._pulse_update)
        self.pulse_phase = 0.0  # 0.0 to 2π

        # Position on screen
        self._position_on_screen()

        # Start hidden
        self.hide()

    def _position_on_screen(self):
        """Position indicator centered horizontally, 96px from top"""
        screen = QApplication.primaryScreen()
        if screen is None:
            self.log.warning("no_primary_screen_found")
            return

        screen_geometry = screen.availableGeometry()

        # Center horizontally
        x = screen_geometry.x() + (screen_geometry.width() - 48) // 2
        # 96px from top
        y = screen_geometry.y() + 96

        self.move(x, y)
        self.log.debug("indicator_positioned", x=x, y=y)

    def paintEvent(self, event):
        """Draw pill with color based on state"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.state == "recording":
            # Red: brightness varies with audio level (dark 100 → bright 255)
            brightness = int(100 + 155 * self.audio_level)
            color = QColor(brightness, 0, 0)
        elif self.state == "transcribing":
            # Blue: brightness pulses (100 → 255)
            brightness = int(100 + 155 * abs(math.sin(self.pulse_phase)))
            color = QColor(0, 50, brightness)
        else:
            # Hidden state - don't draw anything
            return

        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        # Draw rounded rectangle: 6px radius = pill shape
        painter.drawRoundedRect(0, 0, 48, 12, 6, 6)

    @pyqtSlot()
    def _pulse_update(self):
        """Update pulse phase for transcribing animation"""
        self.pulse_phase += 0.15  # Increment phase
        if self.pulse_phase > 2 * math.pi:
            self.pulse_phase = 0.0
        self.update()  # Trigger repaint

    @pyqtSlot()
    def show_recording(self):
        """Show indicator in recording state (red)"""
        self.log.debug("indicator_show_recording")
        self.state = "recording"
        self.audio_level = 0.0
        self.show()
        self.update()

    @pyqtSlot(float)
    def update_audio_level(self, level: float):
        """Update audio level and repaint (recording state)"""
        if self.state != "recording":
            return

        self.audio_level = max(0.0, min(1.0, level))  # Clamp to 0.0-1.0
        self.update()

    @pyqtSlot()
    def show_transcribing(self):
        """Show indicator in transcribing state (blue pulse)"""
        self.log.debug("indicator_show_transcribing")
        self.state = "transcribing"
        self.pulse_phase = 0.0
        self.pulse_timer.start(50)  # 50ms interval = ~20fps
        self.show()
        self.update()

    @pyqtSlot()
    def hide_indicator(self):
        """Hide indicator (idle state)"""
        self.log.debug("indicator_hide")
        self.state = "hidden"
        self.pulse_timer.stop()
        self.hide()
```

**Step 2: Manual test (deferred to integration)**

Testing deferred to Phase 7 integration testing

**Step 3: Commit**

```bash
git add src/talk_it_out/gui/indicator.py
git commit -m "feat(gui): add RecordingIndicator widget

- 48x12px pill-shaped floating overlay
- Three states: hidden, recording (red), transcribing (blue pulse)
- Recording: brightness varies with audio level (dark → bright)
- Transcribing: brightness pulses via math.sin()
- Positioned centered horizontally, 96px from top
- Window flags: frameless, stays on top, tool (no taskbar)
- Pattern: Imperative Shell"
```

---

### Task 2: Connect Indicator to SessionWorker

**Files:**
- Modify: `src/talk_it_out/gui/gui_main.py`

**Step 1: Create indicator and connect signals**

Modify `src/talk_it_out/gui/gui_main.py` (add after worker thread setup, before thread.start()):

```python
from talk_it_out.gui.indicator import RecordingIndicator


def main(config_path: Optional[Path] = None):
    # ... existing code ...

    # Create RecordingIndicator
    indicator = RecordingIndicator()

    # Connect SessionWorker signals to indicator slots
    worker.recording_started.connect(indicator.show_recording)
    worker.audio_level_update.connect(indicator.update_audio_level)
    worker.transcription_started.connect(indicator.show_transcribing)
    worker.transcription_complete.connect(indicator.hide_indicator)
    worker.error_occurred.connect(indicator.hide_indicator)

    log.info("indicator_connected")

    # Start worker thread
    thread.start()
    log.info("gui_mode_ready")

    # TODO: Create notifications (Phase 5)
    # TODO: Create tray icon (Phase 6)

    print("GUI mode running with indicator (Ctrl+C to quit)")
    sys.exit(app.exec())
```

**Step 2: Manual test**

Run: `uv run python -m talk_it_out.main gui`

Expected:
- GUI starts
- Press combo: red pill appears, brightens with voice volume
- Release combo: pill turns blue and pulses during transcription
- After paste: pill disappears

**Step 3: Commit**

```bash
git add src/talk_it_out/gui/gui_main.py
git commit -m "feat(gui): connect RecordingIndicator to SessionWorker

- Create RecordingIndicator instance
- Connect worker signals to indicator slots:
  - recording_started → show_recording
  - audio_level_update → update_audio_level
  - transcription_started → show_transcribing
  - transcription_complete/error_occurred → hide_indicator
- Indicator provides visual feedback for complete workflow"
```

---

## Phase 5: Desktop Notifications

Show desktop notifications for errors using D-Bus.

### Task 1: Add pydbus Dependency

**Files:**
- Modify: `pyproject.toml` (via uv add command)

**Step 1: Add pydbus dependency**

Run: `uv add pydbus`

Expected: pydbus added to dependencies, uv.lock updated

**Step 2: Verify installation**

Run: `uv run python -c "from pydbus import SessionBus; print('pydbus OK')"`

Expected: Output "pydbus OK"

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add pydbus for desktop notifications

- pydbus added via uv add
- Required for D-Bus notifications in Phase 5"
```

---

### Task 2: Create NotificationManager

**Files:**
- Create: `src/talk_it_out/gui/notifications.py`

**Step 1: Create NotificationManager class**

Create `src/talk_it_out/gui/notifications.py`:

```python
# pattern: Imperative Shell
"""
NotificationManager: D-Bus desktop notifications for errors.

Uses FreeDesktop.org Desktop Notifications Specification via pydbus.
Falls back to stderr if D-Bus unavailable.
"""

import sys
import structlog


class NotificationManager:
    """Send desktop notifications via D-Bus (pydbus)"""

    def __init__(self, app_name: str = "talk-it-out"):
        self.app_name = app_name
        self.log = structlog.get_logger()

        # Try to connect to D-Bus
        try:
            from pydbus import SessionBus
            self.bus = SessionBus()
            self.notifications = self.bus.get('org.freedesktop.Notifications')
            self.log.info("notifications_initialized", backend="dbus")
        except Exception as e:
            self.log.warning("dbus_unavailable", error=str(e), fallback="stderr")
            self.notifications = None

    def send(self, summary: str, body: str, urgency: str = "normal"):
        """
        Send desktop notification.

        Args:
            summary: Notification title
            body: Notification message
            urgency: "low", "normal", or "critical"
        """
        if self.notifications is None:
            # Fallback to stderr
            print(f"[NOTIFICATION] {summary}: {body}", file=sys.stderr)
            return

        # Map urgency to D-Bus byte values
        urgency_map = {"low": 0, "normal": 1, "critical": 2}
        urgency_value = urgency_map.get(urgency, 1)

        try:
            notification_id = self.notifications.Notify(
                self.app_name,      # app_name
                0,                   # replaces_id (0 = new notification)
                "",                  # app_icon (empty = default)
                summary,             # summary
                body,                # body
                [],                  # actions (none)
                {"urgency": urgency_value},  # hints
                5000                 # timeout (5 seconds)
            )
            self.log.debug("notification_sent", id=notification_id, summary=summary)
        except Exception as e:
            self.log.warning("notification_failed", error=str(e))
            # Fallback to stderr on error
            print(f"[NOTIFICATION] {summary}: {body}", file=sys.stderr)
```

**Step 2: Manual test (deferred to integration)**

Testing deferred to Phase 7 integration testing

**Step 3: Commit**

```bash
git add src/talk_it_out/gui/notifications.py
git commit -m "feat(gui): add NotificationManager for D-Bus notifications

- NotificationManager wraps pydbus D-Bus interface
- Sends notifications via org.freedesktop.Notifications
- Urgency levels: low (0), normal (1), critical (2)
- Fallback to stderr if D-Bus unavailable
- 5 second timeout for notifications
- Pattern: Imperative Shell"
```

---

### Task 3: Connect Notifications to SessionWorker

**Files:**
- Modify: `src/talk_it_out/gui/gui_main.py`

**Step 1: Create NotificationManager and connect error signal**

Modify `src/talk_it_out/gui/gui_main.py` (add after indicator setup):

```python
from talk_it_out.gui.notifications import NotificationManager


def main(config_path: Optional[Path] = None):
    # ... existing code ...

    # Create NotificationManager
    notifications = NotificationManager()

    # Connect SessionWorker error signal to notifications
    worker.error_occurred.connect(
        lambda msg: notifications.send("Talk It Out Error", msg, urgency="normal")
    )

    log.info("notifications_connected")

    # Start worker thread
    thread.start()
    log.info("gui_mode_ready")

    # TODO: Create tray icon (Phase 6)

    print("GUI mode running with indicator and notifications (Ctrl+C to quit)")
    sys.exit(app.exec())
```

**Step 2: Manual test**

Run: `uv run python -m talk_it_out.main gui`

Then trigger an error (e.g., speak nothing and release combo quickly - invalid audio)

Expected: Desktop notification appears with error message

**Step 3: Commit**

```bash
git add src/talk_it_out/gui/gui_main.py
git commit -m "feat(gui): connect NotificationManager to SessionWorker errors

- Create NotificationManager instance
- Connect worker.error_occurred signal to notifications.send()
- Errors trigger desktop notifications with \"normal\" urgency
- Users notified of transcription failures, paste errors, etc."
```

---

## Phase 6: System Tray Icon

Add system tray icon with quit menu.

### Task 1: Create TrayIcon

**Files:**
- Create: `src/talk_it_out/gui/tray.py`

**Step 1: Create TrayIcon class**

Create `src/talk_it_out/gui/tray.py`:

```python
# pattern: Imperative Shell
"""
TrayIcon: System tray icon with quit menu.

Provides minimal tray presence (no settings dialog per design).
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
import structlog


class TrayIcon(QSystemTrayIcon):
    """System tray icon with quit menu"""

    def __init__(self, app):
        self.log = structlog.get_logger()

        # Use system icon for microphone/audio
        icon = QIcon.fromTheme("audio-input-microphone")

        # Fallback to a basic icon if theme icon not found
        if icon.isNull():
            self.log.warning("theme_icon_not_found", fallback="using_default")
            icon = QIcon.fromTheme("application-x-executable")

        super().__init__(icon)

        # Set tooltip
        self.setToolTip("Talk It Out")

        # Create context menu
        menu = QMenu()

        # Quit action
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(app.quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)
        self.log.info("tray_icon_created")
```

**Step 2: Manual test (deferred to integration)**

Testing deferred to Phase 7 integration testing

**Step 3: Commit**

```bash
git add src/talk_it_out/gui/tray.py
git commit -m "feat(gui): add system tray icon

- TrayIcon with microphone icon from theme
- Context menu with Quit action
- Tooltip: \"Talk It Out\"
- Fallback icon if theme icon unavailable
- Pattern: Imperative Shell"
```

---

### Task 2: Add Tray Icon to GUI Main

**Files:**
- Modify: `src/talk_it_out/gui/gui_main.py`

**Step 1: Create and show tray icon**

Modify `src/talk_it_out/gui/gui_main.py` (add after notifications setup):

```python
from talk_it_out.gui.tray import TrayIcon


def main(config_path: Optional[Path] = None):
    # ... existing code ...

    # Create and show tray icon
    tray = TrayIcon(app)
    tray.show()

    log.info("tray_icon_shown")

    # Start worker thread
    thread.start()
    log.info("gui_mode_ready")

    print("GUI mode running - check system tray (Ctrl+C or right-click tray → Quit)")
    sys.exit(app.exec())
```

**Step 2: Manual test**

Run: `uv run python -m talk_it_out.main gui`

Expected:
- Tray icon appears in system tray
- Hover shows "Talk It Out" tooltip
- Right-click shows menu with "Quit" option
- Clicking "Quit" exits cleanly

**Step 3: Commit**

```bash
git add src/talk_it_out/gui/gui_main.py
git commit -m "feat(gui): add tray icon to GUI mode

- Create TrayIcon instance
- Show tray icon on startup
- Users can quit via tray menu or Ctrl+C
- Complete GUI mode: indicator + notifications + tray"
```

---

## Phase 7: Integration Testing and Polish

End-to-end testing, fix any issues, verify compatibility. **All testing is manual.**

### Task 1: Full Workflow Testing

**Manual test checklist:**

**Step 1: Launch GUI mode**

Run: `uv run python -m talk_it_out.main gui`

Verify:
- [ ] Application starts without errors
- [ ] Structured log shows "gui_mode_ready"
- [ ] Tray icon appears in system tray
- [ ] No indicator visible yet (idle state)

**Step 2: Test recording workflow**

- [ ] Press configured combo key
- [ ] Red pill indicator appears centered, 96px from top
- [ ] Speak loudly: indicator brightens to bright red
- [ ] Speak quietly: indicator dims to dark red
- [ ] Indicator updates smoothly with voice volume

**Step 3: Test transcription workflow**

- [ ] Release combo key
- [ ] Indicator turns blue immediately
- [ ] Blue indicator pulses (brightness oscillates)
- [ ] Text pastes into active window
- [ ] Indicator disappears after paste completes

**Step 4: Test error handling**

- [ ] Press combo, don't speak, release immediately
- [ ] Desktop notification appears: "Talk It Out Error: Audio invalid..."
- [ ] Indicator hides on error
- [ ] Application continues running (doesn't crash)

**Step 5: Test shutdown**

- [ ] Quit via tray icon → Quit
  - [ ] Application exits cleanly
  - [ ] No "QThread destroyed while running" errors
  - [ ] Cleanup completes within 3 seconds

- [ ] Restart, then Ctrl+C in terminal
  - [ ] Graceful shutdown within 3 seconds
  - [ ] Structured log shows "shutdown_requested"

**Step 6: Regression testing**

Run: `uv run python -m talk_it_out.main run`

Verify:
- [ ] CLI mode works identically to before
- [ ] Recording, transcription, paste all function
- [ ] Ctrl+C shutdown is graceful
- [ ] No GUI dependencies loaded (PyQt6/pydbus only for GUI mode)

---

### Task 2: Platform Compatibility Testing

**Manual test on KDE Plasma Wayland (primary target):**

**Step 1: Test on KDE Plasma Wayland**

- [ ] Indicator appears and stays on top of windows
- [ ] `WindowStaysOnTopHint` works correctly
- [ ] Pill shape renders correctly (48x12px, 6px corner radius)
- [ ] Colors correct: red for recording, blue for transcribing
- [ ] Pulsing animation smooth
- [ ] Tray icon visible and functional
- [ ] Desktop notifications appear

**Step 2: Test on GNOME Wayland if available (secondary target)**

- [ ] Indicator visible and on top
- [ ] Colors and animations work
- [ ] Tray icon visible
- [ ] Notifications work

**Step 3: Test multi-monitor setup if available**

- [ ] Indicator positioned on primary screen
- [ ] Centered correctly on primary screen
- [ ] 96px from top of primary screen

---

### Task 3: Documentation Updates

**Files:**
- Modify: `README.md`

**Step 1: Add GUI mode documentation to README**

Modify `README.md` (add after CLI usage section):

```markdown
## Usage

### CLI Mode (default)

```bash
talk-it-out run
```

Runs in terminal with keyboard shortcuts for voice-to-text.

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
```

**Step 2: Commit documentation**

```bash
git add README.md
git commit -m "docs: add GUI mode usage and requirements

- Document talk-it-out gui command
- Explain indicator states (red recording, blue transcribing)
- Note platform requirements (Wayland, D-Bus)
- List primary/secondary platform targets"
```

---

### Task 4: Fix Any Issues Found

**This task is a placeholder for fixes discovered during testing**

**Process:**

1. Run all manual tests from Task 1-2
2. Document any issues found
3. Fix issues one at a time
4. Commit each fix individually with descriptive message
5. Re-test to verify fix

**Common issues to watch for:**
- Indicator not staying on top (WindowStaysOnTopHint not working)
- Colors not rendering correctly
- Audio level updates too fast/slow
- Notifications not appearing
- Thread cleanup errors on shutdown
- Tray icon not visible

**Commit format for fixes:**
```bash
git add [files]
git commit -m "fix(component): description of fix

- Root cause explanation
- Solution implemented
- Testing verification"
```

---

## Phase 8: Commit and Review

Final review and merge. **No new code.**

### Task 1: Final Review

**Manual review checklist:**

**Step 1: Review all changes**

Run: `git diff main...ed/gui`

Review:
- [ ] No debugging code left (print statements, commented sections)
- [ ] All pattern annotations present (`# pattern: Imperative Shell`)
- [ ] Structured logging follows conventions (event names, kwargs)
- [ ] No hardcoded paths or user-specific values
- [ ] Error handling follows existing patterns

**Step 2: Verify pattern annotations**

Check these files have pattern comments at top:
- [ ] `src/talk_it_out/framework/session.py`
- [ ] `src/talk_it_out/gui/gui_main.py`
- [ ] `src/talk_it_out/gui/worker.py`
- [ ] `src/talk_it_out/gui/indicator.py`
- [ ] `src/talk_it_out/gui/notifications.py`
- [ ] `src/talk_it_out/gui/tray.py`

**Step 3: Verify structured logging**

Check log statements use:
- [ ] Event names as first argument (snake_case)
- [ ] Context as keyword arguments
- [ ] Appropriate log levels (DEBUG/INFO/WARNING/ERROR)

**Step 4: Check for test config modifications**

Verify:
- [ ] No modifications to `~/.config/talk-it-out/config.toml` in code
- [ ] Tests use temporary config files or mocks
- [ ] No global config writes during tests

---

### Task 2: Create Summary Commit (Optional)

**Note:** Individual commits already made throughout implementation. This step is optional.

If there are uncommitted changes:

```bash
git add .
git status  # Review what's being committed
git commit -m "feat: GUI mode with floating indicator and desktop notifications

Complete GUI implementation across 8 phases:
- Phase 1: Extract Session class from main.py
- Phase 2: Add gui subcommand and Qt6 stub
- Phase 3: SessionWorker threading with Qt signals
- Phase 4: RecordingIndicator (48x12px pill, red/blue states)
- Phase 5: Desktop notifications via pydbus
- Phase 6: System tray icon with quit menu
- Phase 7: Integration testing and documentation
- Phase 8: Final review

Changes:
- New: src/talk_it_out/framework/session.py (~200 lines)
- New: src/talk_it_out/gui/ module (~450 lines)
- Modified: src/talk_it_out/main.py (refactored run(), added gui())
- Modified: src/talk_it_out/framework/audio_io.py (added audio level callback)
- Modified: README.md (added GUI mode documentation)
- Dependencies: PyQt6, pydbus

CLI mode unchanged, GUI mode shares Session logic.
Target: KDE Plasma Wayland with reasonable cross-Wayland compatibility."
```

---

### Task 3: Review Commit History

**Step 1: Review commit history**

Run: `git log --oneline main..ed/gui`

Verify:
- [ ] Commits are logical, atomic changes
- [ ] Commit messages follow convention (feat/fix/docs/deps)
- [ ] Each commit has clear description
- [ ] No "WIP" or "temp" commits

**Step 2: Optionally squash if needed**

If commit history is messy:

```bash
git rebase -i main
# Mark commits for squash/fixup as needed
# Follow interactive rebase prompts
```

Otherwise, keep detailed commit history (preferred for reviewability)

---

### Task 4: Merge Decision

**Final step - decide how to integrate:**

**Option A: Merge to main (if working alone)**

```bash
git checkout main
git merge ed/gui --no-ff
git push origin main
```

**Option B: Create Pull Request (if using PR workflow)**

```bash
git push origin ed/gui
# Then create PR via GitHub/GitLab UI
# Title: "Add GUI mode with floating indicator"
# Description: Link to design doc, summarize changes, note testing done
```

**Option C: Keep branch for further testing**

```bash
# Don't merge yet, continue testing
# Make fixes as needed
# Merge when fully validated
```

---

## Implementation Complete

All 8 phases documented with:
- Bite-sized tasks (2-5 minutes each)
- Exact file paths and line numbers
- Complete code examples
- Exact commands with expected outputs
- Individual commit messages for each step
- Manual testing checklists

Ready for execution via `superpowers:executing-plans` or `superpowers:subagent-driven-development`.
