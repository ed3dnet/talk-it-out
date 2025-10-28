# pattern: Imperative Shell
"""
GUI mode entry point.

Launches Qt6 application with SessionWorker, dynamic tray icon, and system notifications.
"""

# Workaround for Python 3.13 + OpenSSL 3.5 incompatibility
# MUST be first, before any imports that might initialize SSL
# Python 3.13 does not support OpenSSL 3.5 (support added in Python 3.14+)
# On systems with OpenSSL 3.5 (e.g., Fedora 42), Python 3.13 fails to create
# ssl.SSLContext with MODULE_INITIALIZATION_ERROR due to incompatible OpenSSL
# configuration file at /etc/pki/tls/openssl.cnf
# This particularly affects QThread workers which re-initialize OpenSSL in their context
# Setting OPENSSL_CONF=/dev/null bypasses the problematic config file
# See: https://github.com/python/cpython/issues/132339
import sys
import os

if sys.version_info[:2] == (3, 13):
    os.environ["OPENSSL_CONF"] = "/dev/null"

# Setup CUDA library paths before any CUDA libraries are imported
# PyTorch bundles cuDNN but doesn't add it to LD_LIBRARY_PATH automatically
# This must happen before importing any modules that might use CUDA
from talk_it_out.framework.cuda_deps import setup_cuda_library_path
setup_cuda_library_path()

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QThread, QTimer
from typing import Optional
from pathlib import Path
import structlog
import signal

from talk_it_out.framework import (
    config,
    config_io,
    logging_setup,
    permissions,
    audio_deps,
)
from talk_it_out.gui.worker import SessionWorker
from talk_it_out.gui.notifications import NotificationManager
from talk_it_out.gui.tray import TrayIcon


def main(config_path: Optional[Path] = None):
    """Launch GUI mode"""
    # Load config
    path = config_path or config.get_config_path()
    cfg = config_io.load_config(path)

    # Setup logging
    log = logging_setup.configure_logging(cfg["logging"]["level"])
    log.info("gui_mode_starting", config_path=str(path))

    # Create Qt application FIRST so we can show error dialogs
    app = QApplication(sys.argv)
    app.setApplicationName("Talk It Out")
    app.setQuitOnLastWindowClosed(False)  # Tray mode

    # Check permissions - show dialog on error
    ok, error = permissions.check_input_group()
    if not ok:
        QMessageBox.critical(None, "Permission Error", error)
        sys.exit(1)

    # Check dependencies - show dialog on error
    ok, error = audio_deps.check_portaudio()
    if not ok:
        QMessageBox.critical(None, "Dependency Error", error)
        sys.exit(1)

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

    # Qt's event loop blocks signal processing, so create a timer that periodically
    # allows Python signal handlers to run
    timer = QTimer()
    timer.timeout.connect(lambda: None)  # Do nothing, just let signals process
    timer.start(500)  # Every 500ms

    # Create tray icon with dynamic state colorization
    # Starts hidden until Session is initialized (Whisper loading takes several seconds)
    # Will be shown by set_state_idle() when session_ready signal fires
    tray = TrayIcon(app)

    # Connect SessionWorker signals to tray icon state changes
    worker.session_ready.connect(
        tray.set_state_idle
    )  # Loading -> Idle after Whisper loads
    worker.recording_started.connect(tray.set_state_recording)
    worker.transcription_started.connect(tray.set_state_transcribing)
    worker.transcription_complete.connect(tray.set_state_idle)
    worker.error_occurred.connect(tray.set_state_idle)

    # Connect audio level updates for recording brightness
    worker.audio_level_update.connect(tray.update_audio_level)

    log.info("tray_icon_connected")

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

    # print("GUI mode running - check system tray (Ctrl+C or right-click tray → Quit)")
    sys.exit(app.exec())
