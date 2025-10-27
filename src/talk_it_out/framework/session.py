# pattern: Imperative Shell
"""
Session orchestrates keyboard monitoring, audio recording, transcription, and output.

Provides callback-based API for state changes, allowing both CLI (no callbacks) and
GUI (callbacks → Qt signals) usage patterns.
"""

from typing import Dict, Any, Optional, Callable
import structlog
import queue

from talk_it_out.framework import keyboard_io, audio_io, whisper_io, signals, keyboard, audio
from talk_it_out.output import create_output_strategy


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

        # Track whether a workflow is in progress
        self.is_busy = False

        # Store callbacks
        self.on_recording_started = on_recording_started
        self.on_recording_stopped = on_recording_stopped
        self.on_transcription_started = on_transcription_started
        self.on_transcription_complete = on_transcription_complete
        self.on_audio_level = on_audio_level
        self.on_error = on_error

        # Initialize cleanup registry
        self.cleanup_registry = signals.CleanupRegistry()
        self.cleanup_registry.register(lambda: self.log.info("session_shutdown"))

        # Create event queue for combo events
        self.event_queue: queue.Queue[keyboard.ComboEvent] = queue.Queue()

        # Extract target combos from config
        # Convert key names (e.g., "KEY_LEFTMETA") to key codes (e.g., 125)
        target_combos = keyboard.config_to_target_combos(app_config)

        # Initialize keyboard monitor
        self.keyboard_monitor = keyboard_io.KeyboardMonitor(
            target_combos=target_combos,
            event_queue=self.event_queue
        )
        self.cleanup_registry.register(self.keyboard_monitor.stop)

        # Initialize audio recorder
        self.audio_recorder = audio_io.AudioRecorder(
            sample_rate=app_config["audio"]["sample_rate"],
            channels=app_config["audio"]["channels"],
            device=app_config["audio"]["device"],
            on_audio_level=self.on_audio_level
        )

        # Initialize transcriber
        self.transcriber = whisper_io.Transcriber(app_config["whisper"])

        # Initialize output strategy
        self.output_strategy = create_output_strategy(app_config)

        self.log.info("session_initialized", mode="unknown")

    @property
    def combo_queue(self) -> queue.Queue:
        """Alias for event_queue (for backward compatibility)"""
        return self.event_queue

    def start_monitoring(self) -> None:
        """Start keyboard monitoring (non-blocking)"""
        self.keyboard_monitor.start()
        self.log.info("session_monitoring_started")

    def stop(self) -> None:
        """Graceful shutdown via cleanup registry"""
        self.log.info("session_stopping")
        self.cleanup_registry.cleanup()

    def process_combo_event(self, combo_event: keyboard.ComboEvent) -> None:
        """Process a single combo event (PUBLIC API for CLI and GUI)"""
        if combo_event.event_type == "combo_pressed":
            self._handle_combo_pressed(combo_event)
        elif combo_event.event_type == "combo_released":
            self._handle_combo_released(combo_event)

    def _handle_combo_pressed(self, combo_event: keyboard.ComboEvent) -> None:
        """Handle combo press: start recording"""
        # Ignore combo if workflow already in progress
        if self.is_busy:
            self.log.debug("combo_ignored_busy", combo=combo_event.combo_type)
            return

        self.log.info(
            "combo_activated",
            combo=combo_event.combo_type,
            device=combo_event.device_path
        )

        # Mark session as busy
        self.is_busy = True

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
        audio_data = self.audio_recorder.stop_recording()

        if self.on_recording_stopped:
            self.on_recording_stopped()

        # Validate audio
        min_duration_ms = self.config["audio"]["min_duration_ms"]
        min_samples = int((min_duration_ms / 1000.0) * self.audio_recorder.sample_rate)
        ok, error = audio.validate_audio_data(audio_data, min_samples=min_samples)

        if not ok:
            self.log.warning("audio_invalid", reason=error)
            if self.on_error:
                self.on_error(f"Audio invalid: {error}")
            # Reset busy state on error
            self.is_busy = False
            return

        # Save WAV
        wav_path = self.audio_recorder.save_wav(audio_data)
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
        finally:
            # Cleanup WAV unless debug mode
            if not self.config["audio"]["debug_save_audio"]:
                wav_path.unlink(missing_ok=True)

            # Reset busy state when workflow completes (success or error)
            self.is_busy = False
