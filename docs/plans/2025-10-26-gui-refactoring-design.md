# GUI Refactoring Design

## Overview

Transform talk-it-out from CLI-only to supporting both CLI and GUI modes through minimal refactoring. Extract event processing logic into a reusable Session class, then build Qt6 GUI components that provide visual feedback during recording and transcription workflows.

**Goals:**
- Add GUI mode with floating visual indicator showing workflow state
- Maintain full CLI functionality unchanged
- Share core event processing logic between CLI and GUI (no duplication)
- Follow existing codebase patterns (FCIS, structured logging, CleanupRegistry, error handling)

**Success Criteria:**
- `talk-it-out run` works exactly as before (CLI mode)
- `talk-it-out gui` launches with system tray and floating indicator
- Indicator shows: red (recording, brightness varies with volume) → blue (transcribing, pulsing)
- Desktop notifications on errors
- Works on KDE Plasma Wayland with reasonable compatibility across Wayland DEs
- ~10% code changes, ~900 new lines

**Target Environment:**
- Primary: KDE Plasma Wayland
- Secondary: GNOME Wayland, other Wayland compositors (90/10 rule - reasonable compatibility, not perfection)
- X11 compatibility maintained but Wayland is primary target

## Architecture

**Approach:** Session Extraction with Qt Event Integration

Extract event processing from main.py into Session class (imperative shell), expose public API for processing combo events. GUI uses Qt signals/slots to integrate with Session via SessionWorker running in QThread.

**Key Components:**

1. **Session** (`framework/session.py`) - Imperative Shell
   - Orchestrates keyboard monitoring, recording, transcription, output
   - Accepts callbacks for state changes (recording start/stop, transcription, errors, audio levels)
   - Public API: `process_combo_event(combo_event)`
   - Used by both CLI (blocking loop) and GUI (Qt worker thread)

2. **SessionWorker** (`gui/worker.py`) - Imperative Shell
   - QObject wrapper around Session
   - Runs in QThread via moveToThread()
   - Polls combo_queue with QTimer
   - Emits Qt signals for state changes

3. **RecordingIndicator** (`gui/indicator.py`) - Imperative Shell
   - Floating pill-shaped overlay (48px × 12px)
   - Three states: hidden, recording (red, brightness from audio level), transcribing (blue, pulsing)
   - Positioned centered horizontally, 96px from top of primary screen

4. **NotificationManager** (`gui/notifications.py`) - Imperative Shell
   - pydbus wrapper for D-Bus notifications
   - Fallback to stderr if D-Bus unavailable

5. **TrayIcon** (`gui/tray.py`) - Imperative Shell
   - System tray icon with quit menu
   - No settings dialog (deferred to future)

**Data Flow:**

```
User presses combo
    ↓
KeyboardMonitor → combo_queue
    ↓
[CLI path]                    [GUI path]
main.py loop                  SessionWorker QTimer polls queue
    ↓                             ↓
Session.process_combo_event() ← (same method)
    ↓
AudioRecorder.start_recording()
    ↓ (during recording)
AudioRecorder callback → Session.on_audio_level → [GUI: SessionWorker.audio_level_update signal → RecordingIndicator]
    ↓
User releases combo
    ↓
Session.process_combo_event()
    ↓
AudioRecorder.stop_recording()
Transcriber.transcribe()
    ↓ (during transcription)
Session.on_transcription_started → [GUI: SessionWorker.transcription_started signal → RecordingIndicator (blue pulse)]
    ↓
OutputStrategy.paste_text()
    ↓
Session.on_transcription_complete → [GUI: SessionWorker.transcription_complete signal → RecordingIndicator (hide)]
```

## Existing Patterns

This design follows established codebase patterns discovered via codebase-investigator:

### FCIS Pattern
All new files annotated with pattern comments:
- Session, GUI components: `# pattern: Imperative Shell`

### Queue-Based Event Flow
- Maintains existing `combo_queue` (queue.Queue) from keyboard_io.py
- CLI: blocking `get(timeout=1.0)` for responsive shutdown
- GUI: non-blocking `get_nowait()` polled via QTimer

### Error Handling
- Tuple returns `(bool, str)` for validation (following permissions.py pattern)
- Continue on non-critical errors (log warning, don't crash)
- Structured logging: `log.warning("transcription_failed", error=str(e))`
- Custom exceptions for domain errors (if needed, following OutputError pattern)

### Configuration
- Pass full config dict to Session constructor
- Session extracts sections as needed (follows main.py pattern)

### Cleanup
- Session integrates with CleanupRegistry (framework/signals.py)
- Components provide `.stop()` methods
- Timeout protection (3.0s default)

### Structured Logging
- Event names as first argument: `log.info("session_started", mode="gui")`
- Context as kwargs: `config_path=str(path)`, `audio_level=level`
- Levels: DEBUG (events), INFO (operations), WARNING (recoverable), ERROR (critical)

### Threading
- Daemon threads for background work (following keyboard_io.py pattern)
- Qt threading: QThread + moveToThread() (Qt6 best practice from research)

## Implementation Phases

### Phase 1: Session Extraction

**Goal:** Extract event processing into reusable Session class, refactor CLI to use it.

**Components:**

1. **Create `framework/session.py`** (new file, ~150 lines)
   - `Session.__init__(config, callbacks...)` - initialize components, store callbacks
   - `Session.start_monitoring()` - start keyboard monitor (non-blocking)
   - `Session.process_combo_event(combo_event)` - public API for event processing
   - `Session.stop()` - graceful shutdown via CleanupRegistry
   - Callbacks: `on_recording_started`, `on_recording_stopped`, `on_transcription_started`, `on_transcription_complete`, `on_audio_level`, `on_error`

2. **Modify `framework/audio_io.py`** (~20 lines)
   - Add `on_audio_level: Optional[Callable[[float], None]]` parameter to AudioRecorder.__init__
   - In `_recording_callback()`, calculate audio level and call callback:
     ```python
     if self.on_audio_level:
         level = np.abs(indata).mean() / 32768.0  # Normalize to 0.0-1.0
         self.on_audio_level(level)
     ```

3. **Refactor `main.py`** (~80 lines)
   - Extract `run()` command logic into Session usage
   - Create Session with no callbacks (CLI doesn't need them)
   - Keep existing event loop: `combo_queue.get(timeout=1.0)`, call `session.process_combo_event()`
   - Maintain all existing behavior (permissions checks, dependency checks, logging setup)

**Dependencies:** None (uses existing components)

**Testing:**
- [ ] CLI mode works identically to before (`talk-it-out run`)
- [ ] Recording, transcription, paste all function
- [ ] Ctrl+C shutdown is graceful
- [ ] Audio level callback receives values (add debug log to verify)
- [ ] All existing tests pass

---

### Phase 2: GUI Subcommand Stub

**Goal:** Add `talk-it-out gui` subcommand that launches minimal Qt application (no functionality yet).

**Components:**

1. **Create `gui/__init__.py`** (empty)

2. **Create `gui/gui_main.py`** (~30 lines)
   ```python
   from PyQt6.QtWidgets import QApplication
   import sys

   def main(config_path):
       app = QApplication(sys.argv)
       # TODO: Initialize components
       print("GUI mode - coming soon")
       sys.exit(app.exec())
   ```

3. **Add `gui` command to `main.py`** (~10 lines)
   ```python
   @app.command()
   def gui(config: Optional[Path] = None):
       """Run in GUI mode"""
       from talk_it_out.gui import gui_main
       gui_main.main(config)
   ```

**Dependencies:**
```bash
uv add PyQt6
```

**Testing:**
- [ ] `talk-it-out gui` launches and shows Qt application window
- [ ] Application quits cleanly with Ctrl+C
- [ ] `talk-it-out run` still works (no regression)

---

### Phase 3: SessionWorker Threading

**Goal:** Integrate Session with Qt threading via SessionWorker.

**Components:**

1. **Create `gui/worker.py`** (~120 lines)
   - `SessionWorker(QObject)` class with Qt signals:
     - `recording_started = pyqtSignal()`
     - `recording_stopped = pyqtSignal()`
     - `transcription_started = pyqtSignal()`
     - `transcription_complete = pyqtSignal(str)`
     - `audio_level_update = pyqtSignal(float)`
     - `error_occurred = pyqtSignal(str)`
     - `shutdown_complete = pyqtSignal()`
   - `__init__(app_config)` - create Session with callbacks that emit signals
   - `start_monitoring()` slot - start Session monitoring, start QTimer polling
   - `poll_events()` slot - `combo_queue.get_nowait()`, call `session.process_combo_event()`
   - `stop()` slot - stop Session, emit shutdown_complete

2. **Update `gui/gui_main.py`** (~100 lines)
   - Load config (use config_io.load_config)
   - Create SessionWorker (no parent!)
   - Create QThread
   - Move worker to thread: `worker.moveToThread(thread)`
   - Connect lifecycle signals:
     - `thread.started → worker.start_monitoring`
     - `worker.shutdown_complete → thread.quit`
     - `thread.finished → worker.deleteLater`
     - `thread.finished → thread.deleteLater`
   - Connect shutdown: `app.aboutToQuit → worker.stop`
   - Setup signal handlers for Ctrl+C
   - Start thread

**Dependencies:** None (PyQt6 already added)

**Testing:**
- [ ] `talk-it-out gui` launches, Session starts in worker thread
- [ ] Keyboard combo triggers recording (verify via logs)
- [ ] Recording → transcription → paste works in GUI mode
- [ ] Ctrl+C shuts down gracefully (no "QThread destroyed while running" errors)
- [ ] Thread cleanup completes within 3 seconds

---

### Phase 4: Recording Indicator

**Goal:** Display floating pill indicator that changes color based on workflow state.

**Components:**

1. **Create `gui/indicator.py`** (~150 lines)
   - `RecordingIndicator(QWidget)` class
   - Window flags: `FramelessWindowHint | WindowStaysOnTopHint | Tool`
   - Transparent background: `WA_TranslucentBackground`
   - Fixed size: 48px × 12px
   - Position: centered horizontally, 96px from top of primary screen
   - State tracking: `"hidden"`, `"recording"`, `"transcribing"`
   - `paintEvent()`: Draw rounded rectangle (6px radius) with color:
     - Recording: red brightness varies with audio_level (dark 100 → bright 255)
     - Transcribing: blue brightness pulses via `math.sin(pulse_phase)` (100 → 255)
   - QTimer for pulse updates (50ms interval, increment phase)
   - Slots:
     - `show_recording()` - set state, show window
     - `update_audio_level(float)` - store level, trigger repaint
     - `show_transcribing()` - set state, start pulse timer
     - `hide_indicator()` - hide window, stop pulse timer

2. **Update `gui/gui_main.py`** (~30 lines added)
   - Create RecordingIndicator
   - Connect SessionWorker signals to indicator slots:
     - `recording_started → indicator.show_recording`
     - `audio_level_update → indicator.update_audio_level`
     - `transcription_started → indicator.show_transcribing`
     - `transcription_complete → indicator.hide_indicator`
     - `error_occurred → indicator.hide_indicator`

**Dependencies:** None

**Testing:**
- [ ] Indicator appears centered, 96px from top when recording starts
- [ ] Red color brightens with voice volume (speak loudly vs quietly)
- [ ] Indicator turns blue and pulses during transcription
- [ ] Indicator hides after paste completes
- [ ] Indicator hides on errors
- [ ] Indicator stays on top of other windows
- [ ] Works on KDE Plasma Wayland (primary target)
- [ ] Test on GNOME Wayland if available (secondary target)

---

### Phase 5: Desktop Notifications

**Goal:** Show desktop notifications for errors using D-Bus.

**Components:**

1. **Create `gui/notifications.py`** (~50 lines)
   - `NotificationManager` class
   - `__init__(app_name)` - connect to D-Bus session bus, get Notifications interface
   - Handle D-Bus unavailable: set `self.notifications = None`, fallback to stderr
   - `send(summary, body, urgency)` - call D-Bus Notify method or print to stderr
   - Urgency mapping: `{"low": 0, "normal": 1, "critical": 2}`

2. **Update `gui/gui_main.py`** (~20 lines added)
   - Create NotificationManager
   - Connect `worker.error_occurred` signal to notification sender:
     ```python
     worker.error_occurred.connect(
         lambda msg: notifications.send("Talk It Out Error", msg, urgency="normal")
     )
     ```

**Dependencies:**
```bash
uv add pydbus
```

**Testing:**
- [ ] Trigger error (e.g., invalid audio, transcription failure)
- [ ] Desktop notification appears with error message
- [ ] Notification has 5 second timeout
- [ ] Test with D-Bus available (normal case)
- [ ] Test with D-Bus unavailable (fallback to stderr)
- [ ] Works on KDE Plasma (primary target)

---

### Phase 6: System Tray Icon

**Goal:** Add system tray icon with quit menu.

**Components:**

1. **Create `gui/tray.py`** (~40 lines)
   - `TrayIcon(QSystemTrayIcon)` class
   - Use system icon: `QIcon.fromTheme("audio-input-microphone")`
   - Create context menu with "Quit" action
   - Tooltip: "Talk It Out"

2. **Update `gui/gui_main.py`** (~10 lines added)
   - Create TrayIcon
   - Show tray icon: `tray.show()`

**Dependencies:** None

**Testing:**
- [ ] Tray icon appears in system tray
- [ ] Right-click shows menu with "Quit" option
- [ ] Clicking "Quit" exits application cleanly
- [ ] Tooltip shows "Talk It Out" on hover
- [ ] Icon visible on KDE Plasma Wayland

---

### Phase 7: Integration Testing and Polish

**Goal:** End-to-end testing, fix any issues, verify compatibility.

**Activities:**

1. **Full workflow testing:**
   - [ ] Launch `talk-it-out gui`
   - [ ] Press combo, record audio, verify red indicator with brightness changes
   - [ ] Release combo, verify blue pulsing during transcription
   - [ ] Verify text pasted correctly
   - [ ] Verify indicator hides after completion
   - [ ] Trigger error (disconnect mic), verify notification appears

2. **Platform compatibility:**
   - [ ] Test on KDE Plasma Wayland (primary)
   - [ ] Test on GNOME Wayland if available (secondary)
   - [ ] Verify WindowStaysOnTopHint works (indicator stays on top)
   - [ ] Verify indicator position correct on multi-monitor setups

3. **Shutdown testing:**
   - [ ] Quit via tray icon - verify clean shutdown
   - [ ] Ctrl+C in terminal - verify graceful shutdown within 3 seconds
   - [ ] Kill -TERM - verify cleanup runs

4. **Regression testing:**
   - [ ] `talk-it-out run` (CLI mode) still works identically
   - [ ] All existing functionality preserved
   - [ ] No new dependencies for CLI mode (PyQt6/pydbus only loaded in GUI)

5. **Documentation:**
   - [ ] Update README with GUI mode usage
   - [ ] Document `talk-it-out gui` command
   - [ ] Note Wayland compatibility targets

**No new code in this phase** - testing and fixes only.

---

### Phase 8: Commit and Review

**Goal:** Commit work, create pull request or merge to main.

**Activities:**

1. **Commit changes:**
   ```bash
   git add .
   git commit -m "feat: add GUI mode with floating indicator and desktop notifications

   - Extract event processing into Session class (framework/session.py)
   - Add Qt6 GUI mode via 'talk-it-out gui' subcommand
   - Floating pill indicator shows recording (red, volume-based brightness) and transcription (blue pulse)
   - Desktop notifications via pydbus for errors
   - System tray icon with quit menu
   - CLI mode unchanged, shares Session logic with GUI
   - Target: KDE Plasma Wayland with reasonable cross-Wayland compatibility"
   ```

2. **Review:**
   - [ ] Review diff for any debugging code, commented sections
   - [ ] Verify all pattern annotations present
   - [ ] Check structured logging follows conventions
   - [ ] Ensure no user config modifications in code

3. **Merge or PR:**
   - Decide: merge directly to main or create feature branch + PR
   - If PR: title "Add GUI mode with floating indicator", link to design doc

**No coding in this phase** - review and merge only.

## Additional Considerations

### Wayland Compatibility Notes

**Research findings (from internet-researcher):**
- Qt6 Wayland support less mature than X11, but sufficient for our needs
- `windowOpacity` animation not supported in Qt6 Wayland - using color brightness instead (no opacity needed)
- `WindowStaysOnTopHint` works on GNOME Wayland but may fail on KWin Wayland without KWindowSystem library
- Decision: Accept potential limitation on KWin, don't add KWindowSystem dependency (90/10 rule)

**Fallback if WindowStaysOnTopHint fails:**
- Indicator still visible, just may appear behind full-screen windows
- Acceptable degradation for secondary platforms

### Audio Level Calculation

**Implementation:** `np.abs(indata).mean() / 32768.0`
- Takes mean absolute amplitude of audio frame
- Normalizes to 0.0-1.0 range (16-bit audio max is 32768)
- Simple and sufficient for visual feedback (not scientific accuracy)

**Frequency:** Called on every audio frame (~every 20-50ms)
- May emit many signals quickly
- RecordingIndicator handles this fine (repaint is cheap)

### Future Extensions (Out of Scope)

**Not included in this design:**
- Settings dialog for configuration editing (use CLI `config-edit` command)
- Start/stop recording from tray menu (always listening, matches CLI behavior)
- Indicator position customization (fixed position is simplest)
- Multiple indicator styles or themes
- macOS/Windows GUI support (Linux-only via pydbus)

These can be added later without changing the core architecture.

## Design Decisions Rationale

### Why Session callbacks instead of Qt signals everywhere?
- Session must be UI-agnostic (usable by CLI)
- Qt signals would couple Session to PyQt6
- Callbacks allow CLI to ignore them, GUI to convert to signals

### Why QTimer polling instead of event-driven queue?
- Simplest integration with Qt event loop
- CPU usage negligible for 100ms polling on modern hardware
- Matches "adequate for usage level" requirement (not high-performance server)

### Why pydbus instead of dbus-next or desktop-notifier?
- Linux-only project (no need for cross-platform)
- Synchronous API simpler than async (Qt already has event loop)
- Modern replacement for deprecated dbus-python
- Lightweight, focused on simple use case

### Why color brightness instead of opacity animation?
- Qt6 Wayland doesn't support windowOpacity animation
- Color brightness works everywhere (X11 and Wayland)
- Simpler implementation (no platform detection needed)
- Visual effect still clear and effective

### Why 48×12px pill instead of circle?
- User preference for shape and size
- Pill shape distinctive and modern
- Small enough not to obstruct workflow
- Centered position easy to spot without being intrusive

### Why no settings in GUI?
- Existing `talk-it-out config-edit` CLI command works fine
- Defer GUI settings dialog to future (YAGNI)
- Reduces Phase 2 scope significantly (~200 lines saved)

### Why modify audio_io.py instead of separate audio level calculation?
- Audio data already flowing through `_recording_callback()`
- Callback pattern already used by sounddevice
- Natural extension point, minimal code change
- Alternative (separate queue) adds complexity for no benefit
