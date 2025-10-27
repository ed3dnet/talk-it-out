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
    session_ready = pyqtSignal()  # Emitted when Session initialized (Whisper loaded)
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
        # This is where Whisper model loading happens (can take several seconds)
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

        # Emit session_ready signal after Session is fully initialized
        # This transitions tray icon from loading state to idle state
        self.session_ready.emit()

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
