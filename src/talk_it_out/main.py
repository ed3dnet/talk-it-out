# pattern: Imperative Shell
# Orchestrates framework components and handles I/O

# Workaround for Python 3.13 + OpenSSL 3.5 incompatibility
# MUST be first, before any imports that might initialize SSL
# Python 3.13 does not support OpenSSL 3.5 (support added in Python 3.14+)
# On systems with OpenSSL 3.5 (e.g., Fedora 42), Python 3.13 fails to create
# ssl.SSLContext with MODULE_INITIALIZATION_ERROR due to incompatible OpenSSL
# configuration file at /etc/pki/tls/openssl.cnf
# Setting OPENSSL_CONF=/dev/null bypasses the problematic config file
# See: https://github.com/python/cpython/issues/132339
import sys
import os
if sys.version_info[:2] == (3, 13):
    os.environ['OPENSSL_CONF'] = '/dev/null'

import typer
import signal
import threading
import queue
from pathlib import Path
from typing import Optional

from talk_it_out.framework import config, config_io, logging_setup, permissions, audio_deps
from talk_it_out.framework import session as session_module
from talk_it_out.output import OutputError

app = typer.Typer()


@app.command()
def run(
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config file"),
    log_level: Optional[str] = typer.Option(None, "--log-level", "-l", help="Override log level"),
):
    """Start voice-to-text listener (default command)."""
    # Load config
    path = config_path or config.get_config_path()
    try:
        cfg = config_io.load_config(path)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except (OSError, PermissionError) as e:
        print(f"Failed to load or create config file: {e}", file=sys.stderr)
        sys.exit(1)

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

    # Create session with transcription feedback for CLI
    try:
        sess = session_module.Session(
            cfg,
            on_transcription_started=lambda: log.info("transcription_started")
        )
    except RuntimeError as e:
        print(f"Failed to load Whisper model: {e}", file=sys.stderr)
        print("This may be the first run. Ensure internet connectivity for model download.", file=sys.stderr)
        sys.exit(1)
    except OutputError as e:
        print(f"Output strategy initialization failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Setup signal handlers for graceful shutdown
    stop_event = threading.Event()

    def signal_handler(signum, frame):
        log.info("shutdown_requested", signal=signum)
        stop_event.set()

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


@app.command()
def config_edit():
    """Edit configuration file in $EDITOR and validate."""
    from talk_it_out.commands.config_edit import edit_config
    sys.exit(edit_config())


@app.command()
def select_audio_device():
    """Select audio input device interactively."""
    from talk_it_out.commands.select_audio_device import select_audio_device
    sys.exit(select_audio_device())


@app.command()
def gui(
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Run in GUI mode with floating indicator and system tray."""
    from talk_it_out.gui import gui_main
    gui_main.main(config_path)


if __name__ == "__main__":
    app()
