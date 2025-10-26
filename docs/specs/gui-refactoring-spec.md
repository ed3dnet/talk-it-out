# Plan: GUI Refactoring and Implementation

**Date:** 2025-10-26

**Author:** Gemini

## 1. Overview

This document outlines the plan to refactor the `talk-it-out` application to support a graphical user interface (GUI). The primary goal is to decouple the core application logic from the command-line interface (CLI) and then build a Qt6-based system tray application as a new front-end.

This plan is divided into two phases:
1.  **Core Logic Refactoring:** Extracting the application's engine into a reusable component.
2.  **GUI Implementation:** Building the system tray application that consumes the refactored core logic.

This plan builds upon the foundation laid out in the `docs/initial-spec.md` document, specifically implementing the concepts from "Phase 2: Qt6 System Tray Application".

---

## 2. Phase 1: Core Logic Refactoring

### Objective

The current application logic resides entirely within the `run` function in `src/talk_it_out/main.py`. This makes it impossible to reuse for a GUI. We will extract this logic into a `Session` class within a new module.

### New Component: `src/talk_it_out/session.py`

A new file will be created to house the main application controller.

```python
# src/talk_it_out/session.py

"""
This module defines the main application session class, which encapsulates the
core logic of keyboard monitoring, audio recording, transcription, and output.
"""

import queue
import threading
from typing import Dict, Any

from .framework import config, logging_setup, signals, keyboard, audio, whisper_io
from .output import create_output_strategy

class Session:
    """
    Manages the main application lifecycle.
    """
    def __init__(self, app_config: Dict[str, Any]):
        """
        Initializes all application components but does not start them.

        Args:
            app_config: The application configuration dictionary.
        """
        self.config = app_config
        self.log = logging_setup.configure_logging(self.config["logging"]["level"])
        
        self.cleanup_registry = signals.CleanupRegistry()
        self._stop_event = threading.Event()

        # Initialize components
        self.combo_queue: queue.Queue[keyboard.ComboEvent] = queue.Queue()
        self.keyboard_monitor = keyboard_io.KeyboardMonitor(
            target_combos=keyboard.config_to_target_combos(self.config),
            combo_queue=self.combo_queue
        )
        self.audio_recorder = audio_io.AudioRecorder(**self.config["audio"])
        self.transcriber = whisper_io.Transcriber(self.config["whisper"])
        self.output_strategy = create_output_strategy(self.config)

        # Register cleanup tasks
        self.cleanup_registry.register(self.keyboard_monitor.stop)
        self.cleanup_registry.register(lambda: self.log.info("shutdown_complete"))

    def start(self):
        """
        Starts the keyboard monitor and the main event loop.
        This method will block until stop() is called.
        """
        self.log.info("session_starting")
        self.keyboard_monitor.start()
        self._event_loop()
        self.log.info("session_stopped")

    def stop(self):
        """
        Signals the event loop to stop and performs cleanup.
        """
        self.log.info("session_stopping")
        self._stop_event.set()
        self.cleanup_registry.run()

    def _event_loop(self):
        """
        The main event processing loop.
        Listens for events from the combo_queue and orchestrates the response.
        """
        while not self._stop_event.is_set():
            try:
                combo_event = self.combo_queue.get(timeout=0.5)
                # ... (The logic from the `while True` loop in main.py) ...
                # This includes handling combo_pressed/released, recording,
                # transcribing, and pasting.
            except queue.Empty:
                continue
```

### Refactoring `src/talk_it_out/main.py`

The existing `run` command will be simplified to act as a client of the `Session` class.

```python
# src/talk_it_out/main.py (simplified `run` function)

from .session import Session

@app.command()
def run(...):
    """Start voice-to-text listener."""
    # ... (Initial permission checks and config loading remain) ...

    # Create and run the session
    session = Session(cfg)

    # Setup signal handlers to gracefully stop the session
    signals.setup_signal_handlers(session.cleanup_registry) # Modified to use the session's registry
    
    # The start method will now block until a signal is received
    session.start() 
```
*Note: `setup_signal_handlers` will need a slight modification to call `session.stop` instead of just running the registry.*

---

## 3. Phase 2: GUI Implementation

### Objective

With the core logic refactored, we will build a Qt6 system tray application. This involves creating a new GUI entry point and several new components in a `src/talk_it_out/gui/` directory.

### Threading Model

The GUI must remain responsive. Therefore, the `Session` object will be moved to a background thread (`QThread`). A `SessionWorker` class will manage the `Session` and emit Qt signals to communicate with the GUI thread.

```python
# src/talk_it_out/gui/worker.py

from PyQt6.QtCore import QObject, pyqtSignal

class SessionWorker(QObject):
    """
    A QObject worker that runs the Session in a separate thread.
    """
    # Signals to communicate with the GUI
    recording_started = pyqtSignal()
    recording_finished = pyqtSignal()
    transcription_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, session):
        super().__init__()
        self.session = session

    def run(self):
        """
        Starts the session. This method is intended to be run in a QThread.
        """
        # We will need to modify the Session to accept callbacks
        # that can be used to emit these signals from the event loop.
        self.session.start()
```

### New GUI Components

1.  **`src/talk_it_out/gui_main.py` (New Entry Point)**
    *   Initializes `QApplication`.
    *   Loads configuration.
    *   Creates the `Session` and the `SessionWorker`.
    *   Moves the worker to a `QThread`.
    *   Creates the `TrayIcon`.
    *   Connects worker signals to `TrayIcon` slots.
    *   Starts the thread and the Qt event loop.

2.  **`src/talk_it_out/gui/tray_icon.py`**
    *   A class inheriting from `QSystemTrayIcon`.
    *   **UI:**
        *   Manages icons for different states (idle, recording, processing, error).
        *   Creates a `QMenu` with actions: "Enable/Disable", "Settings...", "Quit".
    *   **Slots:**
        *   `on_recording_started()`: Change icon to "recording".
        *   `on_recording_finished()`: Change icon to "processing".
        *   `on_transcription_complete(text)`: Change icon to "idle".
        *   `show_settings()`: Open the settings dialog.

3.  **`src/talk_it_out/gui/settings_dialog.py`**
    *   A class inheriting from `QDialog`.
    *   Reads the configuration using `config_io.load_config()`.
    *   Provides widgets (`QComboBox`, `QLineEdit`, etc.) to edit settings.
    *   On save, writes the configuration back using `config_io.save_config()` and informs the running `Session` to reload its configuration if possible.

---

## 4. Proposed File Structure Changes

### Current Structure

```
src/talk_it_out/
├── main.py
├── framework/
│   ├── config.py
│   ├── keyboard_io.py
│   └── ...
└── ...
```

### Proposed Structure

```
src/talk_it_out/
├── main.py                 # Refactored CLI entry point
├── gui_main.py             # New GUI entry point
├── session.py              # New core application session
├── framework/
│   ├── config.py
│   ├── keyboard_io.py
│   └── ...
└── gui/
    ├── __init__.py
    ├── tray_icon.py
    ├── settings_dialog.py
    └── worker.py
```

This refactoring will result in a clean separation of concerns, allowing the core logic in `session.py` to be driven by either the CLI or the new GUI, fulfilling the project's next major goal.
