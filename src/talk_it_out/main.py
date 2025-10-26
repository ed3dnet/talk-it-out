# pattern: Imperative Shell
# Orchestrates framework components and handles I/O

import typer
import sys
import time
import queue
from pathlib import Path
from typing import Optional

from talk_it_out.framework import config, config_io, logging_setup, permissions, signals, keyboard, keyboard_io, audio, audio_io

app = typer.Typer()


@app.command()
def run(
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config file"),
    log_level: Optional[str] = typer.Option(None, "--log-level", "-l", help="Override log level (DEBUG/INFO/WARNING/ERROR)"),
):
    """Start voice-to-text listener (default command)."""

    # Check permissions first
    ok, error = permissions.check_input_group()
    if not ok:
        print(error, file=sys.stderr)
        sys.exit(1)

    # Check PortAudio dependency
    from talk_it_out.framework import audio_deps
    available, error = audio_deps.check_portaudio()
    if not available:
        print(f"❌ {error}", file=sys.stderr)
        sys.exit(1)

    # Load configuration
    path = config_path or config.get_config_path()
    try:
        cfg = config_io.load_config(path)
    except ValueError as e:
        print(f"❌ Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Override log level if specified via CLI
    if log_level:
        cfg["logging"]["level"] = log_level

    # Setup logging
    log = logging_setup.configure_logging(cfg["logging"]["level"])
    log.debug("logging_configured", level=cfg["logging"]["level"])
    log.info("application_started", config_path=str(path))

    # Setup cleanup handlers
    registry = signals.CleanupRegistry()
    registry.register(lambda: log.info("shutdown_complete"))
    signals.setup_signal_handlers(registry, timeout=3.0)

    # Keyboard monitoring integration
    # Phase 4: Main application now processes combo events via queue
    target_combos = keyboard.config_to_target_combos(cfg)

    # Create event queue for combo events
    combo_queue: queue.Queue[keyboard.ComboEvent] = queue.Queue()

    # Start keyboard monitor
    monitor = keyboard_io.KeyboardMonitor(target_combos, combo_queue)
    registry.register(monitor.stop)
    monitor.start()

    log.info("keyboard_monitoring_started", combos=list(target_combos.keys()))

    # Initialize audio recorder
    audio_recorder = audio_io.AudioRecorder(
        sample_rate=cfg["audio"]["sample_rate"],
        channels=cfg["audio"]["channels"],
        device=cfg["audio"]["device"]
    )

    # Event processing loop
    try:
        while True:
            try:
                combo_event = combo_queue.get(timeout=1.0)

                if combo_event.event_type == 'combo_pressed':
                    log.info(
                        "combo_activated",
                        combo=combo_event.combo_type,
                        device=combo_event.device_path
                    )

                    if combo_event.combo_type == 'record_for_paste':
                        audio_recorder.start_recording()

                elif combo_event.event_type == 'combo_released':
                    log.info(
                        "combo_released",
                        combo=combo_event.combo_type,
                        device=combo_event.device_path
                    )

                    if combo_event.combo_type == 'record_for_paste':
                        audio_data = audio_recorder.stop_recording()

                        # Validate audio data
                        valid, error = audio.validate_audio_data(audio_data)
                        if not valid:
                            log.warning("audio_invalid", reason=error)
                        else:
                            # Save WAV file
                            wav_path = audio_recorder.save_wav(audio_data)
                            log.info("recording_complete", wav_path=str(wav_path))

            except queue.Empty:
                # Timeout - continue loop (allows periodic signal checking)
                pass

    except KeyboardInterrupt:
        # Signal handler will take care of cleanup
        pass


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


if __name__ == "__main__":
    app()
