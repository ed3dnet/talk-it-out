# GUI Refactoring and Implementation Specification

**Date:** 2025-10-26
**Status:** Research Complete, Ready for Implementation
**Authors:** Research by codebase-investigator, internet-researcher; Compiled by Claude

---

## 1. Executive Summary

This specification outlines the architecture for transforming `talk-it-out` from a CLI-only application into a dual-interface system supporting both CLI and GUI front-ends. The GUI will be a Qt6-based system tray application with a floating visual indicator inspired by Hex for macOS.

**Key Findings from Architecture Analysis:**
- Current codebase is **95% ready** for GUI refactoring
- Framework modules already follow FCIS (Functional Core, Imperative Shell) pattern
- Only ~10% of code needs modification (primarily `main.py` event loop)
- Zero changes required to framework modules (`keyboard_io`, `audio_io`, `whisper_io`, etc.)
- All threading and queue-based communication already in place

**Implementation Effort:** ~14 hours (2 working days) split across two phases

---

## 2. Current Architecture Assessment

### 2.1 Strengths

**Excellent Separation of Concerns:**
- `keyboard.py`, `config.py`, `audio.py` → Pure functional core (business logic)
- `keyboard_io.py`, `audio_io.py`, `whisper_io.py` → Imperative shell (I/O orchestration)
- Framework modules designed to be called from any front-end

**Sound Threading Model:**
- Main thread: Event processing loop
- Keyboard thread: Background hotkey monitoring via `pynput`
- Audio thread: Callback-based recording via `sounddevice`
- Clean queue-based communication (`combo_queue`)

### 2.2 Refactoring Requirements

**CLI-Specific Code Requiring Extraction:**

| Location | Issue | Severity | Lines Affected |
|----------|-------|----------|----------------|
| `main.py:103-166` | Blocking event loop (`while True`) | CRITICAL | ~60 |
| `signals.py:52-74` | Hardcoded `sys.exit()` in handlers | HIGH | ~20 |
| `main.py:30-50` | Permission checks exit on failure | LOW | ~20 |

**Total Impact:** ~100 lines out of 1000+ codebase (10%)

---

## 3. Phase 1: Session Extraction

### 3.1 Objective

Extract the event processing logic from `main.py` into a reusable `Session` class that can be driven by either CLI (blocking loop) or GUI (Qt signals).

### 3.2 Architecture Pattern: Event-Driven Session

**Key Insight:** Instead of moving the entire blocking `while True` loop into Session, we extract the **event handler** as a public API method:

```python
# src/talk_it_out/session.py
# pattern: Imperative Shell

class Session:
    """
    Manages the application lifecycle and coordinates components.
    Designed to be driven by either CLI (blocking) or GUI (event-driven).
    """

    def __init__(self, app_config: Dict[str, Any]):
        """Initialize all components but don't start them."""
        self.config = app_config
        self.log = logging_setup.configure_logging(self.config["logging"]["level"])

        self.cleanup_registry = signals.CleanupRegistry()
        self._stop_event = threading.Event()

        # Initialize components (same as current main.py)
        self.combo_queue: queue.Queue[keyboard.ComboEvent] = queue.Queue()
        self.keyboard_monitor = keyboard_io.KeyboardMonitor(
            target_combos=keyboard.config_to_target_combos(self.config),
            combo_queue=self.combo_queue
        )
        self.audio_recorder = audio_io.AudioRecorder(**self.config["audio"])
        self.transcriber = whisper_io.Transcriber(self.config["whisper"])
        self.output_strategy = create_output_strategy(self.config)

        # State tracking
        self.recording_data = None

        # Register cleanup
        self.cleanup_registry.register(self.keyboard_monitor.stop)
        self.cleanup_registry.register(lambda: self.log.info("shutdown_complete"))

    def start(self):
        """Start keyboard monitor and begin processing events (CLI mode)."""
        self.log.info("session_starting")
        self.keyboard_monitor.start()
        self._event_loop()  # Blocks until stop() called
        self.log.info("session_stopped")

    def start_monitoring(self):
        """Start keyboard monitor without blocking (GUI mode)."""
        self.log.info("session_starting")
        self.keyboard_monitor.start()

    def process_combo_event(self, combo_event: keyboard.ComboEvent) -> None:
        """
        Process a single combo event. PUBLIC API for both CLI and GUI.

        CLI calls this from blocking while loop.
        GUI calls this from Qt slot connected to QTimer polling combo_queue.
        """
        if combo_event.type == keyboard.EventType.COMBO_PRESSED:
            self.log.info("combo_pressed", combo=combo_event.combo)
            self.recording_data = self.audio_recorder.record_until_silence()

        elif combo_event.type == keyboard.EventType.COMBO_RELEASED:
            self.log.info("combo_released", combo=combo_event.combo)

            if self.recording_data:
                # Transcribe
                audio_array, sample_rate = self.recording_data
                text = self.transcriber.transcribe(audio_array, sample_rate)
                self.log.info("transcription_complete", text=text)

                # Output
                self.output_strategy.output(text)
                self.log.info("output_complete")

                # Clear state
                self.recording_data = None

    def stop(self):
        """Signal event loop to stop and perform cleanup."""
        self.log.info("session_stopping")
        self._stop_event.set()
        self.cleanup_registry.run()

    def _event_loop(self):
        """CLI-specific blocking event loop."""
        while not self._stop_event.is_set():
            try:
                combo_event = self.combo_queue.get(timeout=0.5)
                self.process_combo_event(combo_event)
            except queue.Empty:
                continue
```

### 3.3 Refactored CLI Entry Point

```python
# src/talk_it_out/main.py (simplified)

from .session import Session

@app.command()
def run(
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c"),
):
    """Start voice-to-text listener (CLI mode)."""

    # Permission checks (unchanged)
    if not permissions.check_portaudio_permissions():
        typer.echo("Error: PortAudio not available", err=True)
        raise typer.Exit(1)

    # Load config (unchanged)
    cfg = config_io.load_config(config_path)
    cfg["logging"]["level"] = log_level

    # Create session
    session = Session(cfg)

    # Setup signal handlers for graceful shutdown
    def shutdown_handler(signum, frame):
        session.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # Start session (blocks until interrupted)
    session.start()
```

### 3.4 Signal Handler Refactoring

Modify `signals.py` to support both CLI (exit process) and GUI (just cleanup) modes:

```python
# src/talk_it_out/framework/signals.py

def setup_signal_handlers(cleanup_registry: CleanupRegistry, exit_on_signal: bool = True):
    """
    Setup SIGINT/SIGTERM handlers.

    Args:
        cleanup_registry: Registry of cleanup callbacks to run
        exit_on_signal: If True, call sys.exit() after cleanup (CLI mode)
                       If False, just run cleanup (GUI mode)
    """
    def signal_handler(signum, frame):
        cleanup_registry.run()
        if exit_on_signal:
            sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
```

---

## 4. Phase 2: Qt6 GUI Implementation

### 4.1 Visual Design Goals

**Inspired by Hex for macOS:**
- Floating, always-on-top recording indicator window
- Red pulsing circle when recording (brightness responds to audio levels)
- Blue pulsing circle during transcription
- Native Linux notifications for errors/status
- System tray icon for app control

### 4.2 Qt6 Threading Architecture

**Pattern: QThread + moveToThread() (Official Qt Recommendation)**

```
┌─────────────────────────────────────┐
│   Qt Main Thread (GUI)              │
│  - QApplication event loop          │
│  - System tray icon                 │
│  - Floating indicator window        │
│  - Event queue polling (QTimer)     │
└──────────┬──────────────────────────┘
           │ signals/slots
      ┌────┴────────────┐
      │                 │
┌─────▼──────┐   ┌──────▼──────────┐
│ Session    │   │ Notification    │
│ Worker     │   │ Manager         │
│ Thread     │   │                 │
│            │   │ - D-Bus calls   │
│- Session   │   │ - Toast msgs    │
│- Keyboard  │   └─────────────────┘
│- Audio     │
│- Whisper   │
└────────────┘
```

**Key Principles:**
1. Qt event loop is the **primary** event loop
2. Session runs in background QThread via `moveToThread()`
3. **All communication via signals/slots** (never call worker methods from GUI)
4. Worker inherits from `QObject` (not `QThread`)
5. Worker must have **no parent** before `moveToThread()`

### 4.3 Component Architecture

#### 4.3.1 Session Worker

```python
# src/talk_it_out/gui/worker.py
# pattern: Imperative Shell

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer
from ..session import Session

class SessionWorker(QObject):
    """
    Qt worker that manages Session in background thread.
    Communicates state changes via signals.
    """

    # Signals to GUI thread
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    transcription_started = pyqtSignal()
    transcription_complete = pyqtSignal(str)  # text result
    error_occurred = pyqtSignal(str)  # error message
    audio_level_update = pyqtSignal(float)  # 0.0-1.0 for visual feedback

    def __init__(self, app_config):
        super().__init__()
        self.session = Session(app_config)

        # Timer to poll combo_queue
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll_events)

    @pyqtSlot()
    def start(self):
        """Start session monitoring (called when thread starts)."""
        self.session.start_monitoring()
        self.poll_timer.start(50)  # Poll every 50ms

    @pyqtSlot()
    def stop(self):
        """Stop session (called from GUI)."""
        self.poll_timer.stop()
        self.session.stop()

    @pyqtSlot()
    def poll_events(self):
        """Poll combo_queue for events and process them."""
        try:
            combo_event = self.session.combo_queue.get_nowait()

            # Emit state change signals
            if combo_event.type == keyboard.EventType.COMBO_PRESSED:
                self.recording_started.emit()

            # Process event
            self.session.process_combo_event(combo_event)

            # Emit completion signals
            if combo_event.type == keyboard.EventType.COMBO_RELEASED:
                self.recording_stopped.emit()
                self.transcription_started.emit()
                # (transcription_complete emitted after processing)

        except queue.Empty:
            pass
        except Exception as e:
            self.error_occurred.emit(str(e))
```

#### 4.3.2 Floating Recording Indicator

```python
# src/talk_it_out/gui/indicator.py
# pattern: Imperative Shell (PyQt6 UI)

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSlot
from PyQt6.QtGui import QPainter, QColor, QBrush
import math

class RecordingIndicator(QWidget):
    """
    Always-on-top floating indicator window.
    Shows recording/transcription status with color and pulsing animation.
    """

    class State:
        IDLE = "idle"
        RECORDING = "recording"
        TRANSCRIBING = "transcribing"

    def __init__(self):
        super().__init__()

        # Window configuration for floating overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |      # No title bar
            Qt.WindowType.WindowStaysOnTopHint |     # Always on top
            Qt.WindowType.Tool                       # No taskbar entry
        )

        # Transparency and click-through
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # Size and position (top-right corner)
        self.setGeometry(0, 0, 80, 80)
        self.position_at_screen_corner()

        # State
        self.state = self.State.IDLE
        self.audio_level = 0.0  # 0.0-1.0

        # Pulsing animation
        self.pulse_animation = QPropertyAnimation(self, b"windowOpacity")
        self.pulse_animation.setDuration(800)
        self.pulse_animation.setStartValue(0.5)
        self.pulse_animation.setEndValue(1.0)
        self.pulse_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.pulse_animation.setLoopCount(-1)  # Infinite

        # Audio level update timer (for brightness during recording)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update)

        self.hide()

    def position_at_screen_corner(self):
        """Position indicator at top-right corner of primary screen."""
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - 100  # 20px margin
        y = 20
        self.move(x, y)

    @pyqtSlot()
    def set_recording(self):
        """Enter recording state: red, pulsing, brightness from audio."""
        self.state = self.State.RECORDING
        self.pulse_animation.start()
        self.update_timer.start(33)  # 30 FPS updates
        self.show()

    @pyqtSlot()
    def set_transcribing(self):
        """Enter transcribing state: blue, pulsing."""
        self.state = self.State.TRANSCRIBING
        self.pulse_animation.start()
        self.update_timer.stop()
        self.audio_level = 0.0
        self.update()

    @pyqtSlot()
    def set_idle(self):
        """Enter idle state: hidden."""
        self.state = self.State.IDLE
        self.pulse_animation.stop()
        self.update_timer.stop()
        self.setWindowOpacity(1.0)
        self.hide()

    @pyqtSlot(float)
    def update_audio_level(self, level: float):
        """Update audio level for brightness adjustment (0.0-1.0)."""
        self.audio_level = level
        # update() called by update_timer

    def paintEvent(self, event):
        """Draw the indicator circle with color and brightness."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.state == self.State.RECORDING:
            # Red circle, brightness based on audio level
            brightness = int(100 + 155 * self.audio_level)  # 100-255
            color = QColor(brightness, 0, 0, 200)
        elif self.state == self.State.TRANSCRIBING:
            # Blue circle
            color = QColor(50, 100, 255, 200)
        else:
            # Shouldn't be visible, but just in case
            color = QColor(100, 100, 100, 100)

        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 80, 80)
        painter.end()
```

#### 4.3.3 Notification Manager

```python
# src/talk_it_out/gui/notifications.py
# pattern: Imperative Shell

import dbus
from typing import Literal

class NotificationManager:
    """
    Manages desktop notifications via FreeDesktop D-Bus specification.
    Cross-desktop compatible (GNOME, KDE, XFCE, etc.)
    """

    Urgency = Literal["low", "normal", "critical"]

    def __init__(self, app_name: str = "talk-it-out"):
        self.app_name = app_name
        try:
            self.bus = dbus.SessionBus()
            self.notify_obj = self.bus.get_object(
                "org.freedesktop.Notifications",
                "/org/freedesktop/Notifications"
            )
            self.notify_interface = dbus.Interface(
                self.notify_obj,
                "org.freedesktop.Notifications"
            )
            self.available = True
        except Exception:
            self.available = False

    def send(
        self,
        summary: str,
        body: str = "",
        urgency: Urgency = "normal",
        timeout: int = -1,
        icon: str = "dialog-information"
    ):
        """
        Send a desktop notification.

        Args:
            summary: Notification title
            body: Notification body text
            urgency: "low", "normal", or "critical"
            timeout: Display duration in ms (-1 = server default)
            icon: FreeDesktop icon name (dialog-information, dialog-error, etc.)
        """
        if not self.available:
            print(f"Notification: {summary} - {body}")
            return

        urgency_map = {"low": 0, "normal": 1, "critical": 2}

        try:
            self.notify_interface.Notify(
                self.app_name,                        # app_name
                0,                                    # replaces_id (0 = new)
                icon,                                 # icon
                summary,                              # summary
                body,                                 # body
                [],                                   # actions
                {"urgency": dbus.Byte(urgency_map[urgency])},  # hints
                timeout                               # timeout
            )
        except Exception as e:
            print(f"Notification failed: {e}")

    def notify_error(self, title: str, message: str):
        """Send critical error notification."""
        self.send(title, message, urgency="critical", icon="dialog-error")

    def notify_info(self, title: str, message: str):
        """Send informational notification."""
        self.send(title, message, urgency="low", icon="dialog-information")
```

#### 4.3.4 System Tray Icon

```python
# src/talk_it_out/gui/tray_icon.py
# pattern: Imperative Shell

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import pyqtSlot, QCoreApplication

class TrayIcon(QSystemTrayIcon):
    """
    System tray icon for application control.
    Provides menu for quit action (settings deferred to future work).
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Icon (would use proper icons in production)
        self.setIcon(QIcon.fromTheme("microphone"))
        self.setToolTip("talk-it-out")

        # Context menu
        self.menu = QMenu()

        self.quit_action = QAction("Quit", self.menu)
        self.quit_action.triggered.connect(self.on_quit)
        self.menu.addAction(self.quit_action)

        self.setContextMenu(self.menu)

        # Show tray icon
        if self.isSystemTrayAvailable():
            self.show()
        else:
            print("Warning: System tray not available")

    @pyqtSlot()
    def on_quit(self):
        """Handle quit action."""
        QCoreApplication.quit()
```

#### 4.3.5 GUI Main Entry Point

```python
# src/talk_it_out/gui_main.py
# pattern: Imperative Shell

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread

from .framework import config_io, permissions
from .gui.worker import SessionWorker
from .gui.indicator import RecordingIndicator
from .gui.notifications import NotificationManager
from .gui.tray_icon import TrayIcon

def main():
    """GUI entry point for talk-it-out."""

    # Check permissions
    if not permissions.check_portaudio_permissions():
        print("Error: PortAudio not available")
        sys.exit(1)

    # Load configuration
    cfg = config_io.load_config()

    # Create Qt application
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running when windows close
    app.setApplicationName("talk-it-out")

    # Create GUI components
    notifications = NotificationManager()
    indicator = RecordingIndicator()
    tray = TrayIcon()

    # Create session worker and thread
    worker = SessionWorker(cfg)
    thread = QThread()

    # Move worker to thread (MUST have no parent before this)
    worker.moveToThread(thread)

    # Connect thread lifecycle
    thread.started.connect(worker.start)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    # Connect worker signals to GUI slots
    worker.recording_started.connect(indicator.set_recording)
    worker.recording_stopped.connect(indicator.set_transcribing)
    worker.transcription_complete.connect(indicator.set_idle)
    worker.transcription_complete.connect(
        lambda text: notifications.notify_info("Transcription Complete", text[:100])
    )
    worker.error_occurred.connect(
        lambda msg: notifications.notify_error("Error", msg)
    )
    worker.audio_level_update.connect(indicator.update_audio_level)

    # Graceful shutdown
    app.aboutToQuit.connect(worker.stop)
    app.aboutToQuit.connect(thread.quit)

    # Start worker thread
    thread.start()

    # Start Qt event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

### 4.4 Graceful Shutdown Pattern

**Critical for avoiding "QThread: Destroyed while thread is still running" errors:**

```python
# In gui_main.py or TrayIcon.on_quit()

def shutdown():
    """Cooperative shutdown of worker thread."""

    # Signal worker to stop
    worker.stop()  # Sets stop flags in Session

    # Request thread termination
    thread.quit()

    # Wait for thread to finish (with timeout)
    if not thread.wait(5000):  # 5 second timeout
        print("Warning: Worker thread did not stop gracefully")
        # Never use thread.terminate() - it's dangerous

    # Qt will clean up worker/thread via deleteLater
```

---

## 5. File Structure

### 5.1 Proposed Structure

```
src/talk_it_out/
├── main.py                      # Refactored CLI entry point
├── gui_main.py                  # NEW: GUI entry point
├── session.py                   # NEW: Core session class
├── framework/
│   ├── config.py                # Unchanged
│   ├── keyboard.py              # Unchanged
│   ├── keyboard_io.py           # Unchanged
│   ├── audio.py                 # Unchanged
│   ├── audio_io.py              # Unchanged
│   ├── whisper_io.py            # Unchanged
│   ├── signals.py               # MODIFIED: Add exit_on_signal param
│   ├── logging_setup.py         # Unchanged
│   └── permissions.py           # Unchanged
├── output/
│   ├── __init__.py              # Unchanged
│   ├── base.py                  # Unchanged
│   ├── wl_clip.py               # Unchanged
│   └── ...                      # Unchanged
└── gui/
    ├── __init__.py              # NEW
    ├── worker.py                # NEW: SessionWorker (QObject)
    ├── indicator.py             # NEW: Floating recording indicator
    ├── notifications.py         # NEW: D-Bus notification manager
    └── tray_icon.py             # NEW: System tray icon
```

### 5.2 Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `session.py` | NEW | Extract event processing from main.py |
| `main.py` | MODIFIED | Simplify to use Session class |
| `signals.py` | MODIFIED | Add `exit_on_signal` parameter |
| `gui_main.py` | NEW | Qt6 entry point |
| `gui/worker.py` | NEW | Session worker for QThread |
| `gui/indicator.py` | NEW | Floating visual indicator |
| `gui/notifications.py` | NEW | D-Bus notifications |
| `gui/tray_icon.py` | NEW | System tray icon |
| All framework modules | UNCHANGED | 100% reusable as-is |

---

## 6. Dependencies

### 6.1 New Dependencies

Add to `pyproject.toml`:

```toml
[project.dependencies]
# Existing dependencies remain
# ...

# New GUI dependencies
PyQt6 = "^6.6.0"
dbus-python = "^1.3.0"
```

### 6.2 Installation

```bash
uv add PyQt6 dbus-python
uv sync
```

---

## 7. Implementation Plan

### 7.1 Phase 1: Session Extraction (6 hours)

**Tasks:**
1. Create `src/talk_it_out/session.py` with Session class (~2 hours)
2. Refactor `main.py` to use Session (~1 hour)
3. Update `signals.py` with `exit_on_signal` parameter (~0.5 hours)
4. Create unit tests for Session (~2 hours)
5. Verify CLI still works with `uv run python -m talk_it_out.main run` (~0.5 hours)

**Validation:**
- All existing tests pass
- CLI functionality unchanged
- `session.py` can be imported and instantiated independently

### 7.2 Phase 2: GUI Implementation (8 hours)

**Tasks:**
1. Create `gui/notifications.py` with D-Bus integration (~1 hour)
2. Create `gui/indicator.py` with floating window (~2 hours)
3. Create `gui/worker.py` with SessionWorker (~1.5 hours)
4. Create `gui/tray_icon.py` with system tray (~1 hour)
5. Create `gui_main.py` entry point (~1 hour)
6. Test GUI on GNOME and KDE (~1.5 hours)
7. Document GUI usage (~1 hour)

**Validation:**
- GUI launches and shows tray icon
- Floating indicator appears during recording/transcription
- Notifications appear on state changes
- Graceful shutdown works (no thread warnings)
- Both CLI and GUI can run (not simultaneously on same config)

---

## 8. Design Decisions

### 8.1 Why Event-Driven Session API?

**Decision:** Expose `process_combo_event()` as public API instead of moving `while True` loop into Session.

**Rationale:**
- CLI can call it from blocking loop (`while True`)
- GUI can call it from Qt slot triggered by QTimer
- Same logic works for both interfaces
- Session doesn't need to know about event loop implementation
- Easier to test (just call method with mock events)

### 8.2 Why QThread + moveToThread()?

**Decision:** Use official Qt pattern of QObject worker + moveToThread().

**Alternatives Considered:**
- Inherit from QThread directly (deprecated pattern, not recommended)
- QThreadPool + QRunnable (better for one-off tasks, not persistent monitoring)

**Rationale:**
- Official Qt6 recommendation in docs
- Clean signal/slot integration
- Proper lifecycle management
- Widely used, well-documented pattern

### 8.3 Why D-Bus Notifications Instead of QSystemTrayIcon.showMessage()?

**Decision:** Use FreeDesktop D-Bus notifications directly.

**Rationale:**
- `QSystemTrayIcon.showMessage()` doesn't use native Linux notifications
- D-Bus is the cross-desktop standard (GNOME, KDE, XFCE all implement it)
- Better control over urgency, icons, timeout
- Consistent UX with other Linux apps

### 8.4 Why Floating Indicator Instead of Just Tray Icon?

**Decision:** Implement Hex-style floating indicator in addition to tray icon.

**Rationale:**
- Tray icon is small and easy to miss
- Floating indicator provides immediate visual feedback
- Audio level visualization requires larger display
- Matches UX of reference application (Hex for macOS)
- Can be disabled in config if user prefers minimal approach

---

## 9. Future Enhancements (Out of Scope)

**Deferred to future iterations:**
- Settings dialog (`gui/settings_dialog.py`) for editing config via GUI
- Enable/disable toggle in tray menu
- Multi-monitor support for indicator positioning
- Custom icon themes
- Audio level meter in tray icon (small bar graph)
- Notification preferences (enable/disable different notification types)

---

## 10. Testing Strategy

### 10.1 Unit Tests

**New tests needed:**
- `tests/test_session.py`: Session initialization, event processing, cleanup
- `tests/gui/test_worker.py`: Signal emissions, event polling
- `tests/gui/test_notifications.py`: D-Bus notification sending (with mock)

### 10.2 Integration Tests

**Manual testing checklist:**
- [ ] CLI mode still works as before
- [ ] GUI launches and shows tray icon
- [ ] Recording indicator appears on hotkey press
- [ ] Indicator changes from red (recording) to blue (transcribing)
- [ ] Indicator brightness responds to audio levels during recording
- [ ] Notification appears on transcription complete
- [ ] Error notifications appear on failures
- [ ] Graceful shutdown (no Qt thread warnings in console)
- [ ] Works on GNOME (Wayland and X11)
- [ ] Works on KDE (Wayland and X11)

### 10.3 Accessibility Testing

- [ ] Screen reader announces state changes (if accessible names set)
- [ ] Indicator visible to colorblind users (shape + color)
- [ ] High contrast mode support

---

## 11. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| QThread lifecycle issues | MEDIUM | Follow official Qt pattern, test shutdown thoroughly |
| Window manager compatibility | LOW | Use standard Qt flags, test on GNOME/KDE |
| D-Bus not available | LOW | Graceful fallback to console logging |
| Permission issues (X11 vs Wayland) | MEDIUM | Document requirements, provide setup instructions |
| Performance (real-time updates) | LOW | QTimer at 30 FPS is standard for UI updates |

**Overall Risk:** LOW - Architecture follows proven patterns, existing code is well-structured.

---

## 12. Success Criteria

**Phase 1 Complete When:**
- [ ] Session class exists and is fully tested
- [ ] CLI uses Session and maintains all existing functionality
- [ ] All existing tests pass
- [ ] No behavioral changes to CLI user experience

**Phase 2 Complete When:**
- [ ] GUI launches and runs without errors
- [ ] Floating indicator shows correct states (recording/transcribing/idle)
- [ ] Audio levels affect indicator brightness in real-time
- [ ] Notifications appear for transcription complete and errors
- [ ] Graceful shutdown works (no Qt warnings)
- [ ] Both CLI and GUI modes functional

---

## 13. References

**Research Documentation:**
- Codebase analysis: `ARCHITECTURE_ANALYSIS.md` (generated by investigator)
- Qt6 best practices: Research from official Qt docs and community resources
- FreeDesktop notification spec: https://specifications.freedesktop.org/notification-spec/1.2/

**Related Specifications:**
- Original project spec: `docs/initial-spec.md`
- Current implementation: `src/talk_it_out/main.py:103-166` (event loop to extract)

---

**End of Specification**
