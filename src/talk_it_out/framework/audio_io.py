# pattern: Imperative Shell
# Audio I/O operations using sounddevice
#
# Error Handling Strategy:
# - All errors are recoverable - application continues running
# - Missing devices/PortAudio: Logged at startup (caught earlier in main.py)
# - Stream errors: Log WARNING, return None, continue app
# - Multiple start calls: Log WARNING, ignore duplicate
# - Stop without start: Log WARNING, return None
# - File write errors: Log WARNING, continue app
#
# Logging Levels:
# - DEBUG: Callback status, chunk details, device info
# - INFO: Recording started/stopped, WAV saved with path/size
# - WARNING: Duplicate start, stop without start, invalid audio, device issues
# - ERROR: Not used (all errors are recoverable)

import queue
import tempfile
import structlog
import sounddevice as sd
import numpy as np
from pathlib import Path
from typing import Callable, Optional
from scipy.io import wavfile

log = structlog.get_logger()


class AudioRecorder:
    """Record audio from microphone using sounddevice.

    Records audio while active, accumulating chunks in a queue.
    When stopped, concatenates all chunks and returns as NumPy array.
    """

    def __init__(
        self,
        sample_rate: int,
        channels: int,
        device: str = "",
        on_audio_level: Optional[Callable[[float], None]] = None
    ):
        """Initialize audio recorder.

        Args:
            sample_rate: Sample rate in Hz (16000 for Whisper)
            channels: Number of channels (1 for mono, 2 for stereo)
            device: Device name (empty string = default device)
            on_audio_level: Optional callback called with normalized audio level (0.0-1.0)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.on_audio_level = on_audio_level

        # Resolve device name to index/object
        if device:
            # Search for device by name
            from talk_it_out.framework import audio
            result = audio.find_device_by_name(device)
            if result is None:
                log.warning("audio_device_not_found",
                           device_name=device,
                           message=f"Device '{device}' not found, using system default")
                self.device = None
            else:
                device_idx, device_info = result
                self.device = device_idx
                log.debug("audio_device_resolved",
                         device_name=device,
                         device_index=device_idx)
        else:
            # Empty string means system default
            self.device = None

        # Recording state
        self.recording = False
        self.audio_queue: queue.Queue = queue.Queue()
        self.stream: Optional[sd.InputStream] = None

        log.debug("audio_recorder_initialized",
                  sample_rate=sample_rate,
                  channels=channels,
                  device=device or "default")

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for sounddevice InputStream.

        Accumulates audio chunks in queue during recording.

        Args:
            indata: Input audio data (numpy array)
            frames: Number of frames
            time_info: Timing information
            status: Stream status flags
        """
        if status:
            log.debug("audio_callback_status", status=str(status))

        if self.recording:
            # Copy data to avoid issues with buffer reuse
            self.audio_queue.put(indata.copy())

        # Calculate and report audio level if callback provided
        if self.on_audio_level:
            # Normalize to 0.0-1.0 range (int16 max is 32768)
            level = float(np.abs(indata).mean() / 32768.0)
            self.on_audio_level(level)

    def start_recording(self) -> None:
        """Start recording audio from microphone.

        If already recording, logs warning and ignores.
        """
        if self.recording:
            log.warning("audio_already_recording",
                       message="start_recording called while already recording")
            return

        # Clear queue from any previous recording
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

        try:
            # Start stream
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                device=self.device,
                callback=self._audio_callback,
                dtype=np.int16
            )
            self.stream.start()
            self.recording = True

            log.info("recording_started",
                    sample_rate=self.sample_rate,
                    channels=self.channels,
                    device=self.device or "default")

        except Exception as e:
            log.warning("recording_start_failed",
                       error=str(e),
                       device=self.device or "default")
            self.recording = False
            self.stream = None

    def stop_recording(self) -> Optional[np.ndarray]:
        """Stop recording and return accumulated audio data.

        Returns:
            NumPy array of audio data (int16, shape: [samples, channels])
            or None if not recording or no data captured
        """
        if not self.recording:
            log.warning("audio_not_recording",
                       message="stop_recording called but not currently recording")
            return None

        self.recording = False

        try:
            # Stop and close stream
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None

            # Collect all chunks from queue
            chunks = []
            while not self.audio_queue.empty():
                try:
                    chunk = self.audio_queue.get_nowait()
                    chunks.append(chunk)
                except queue.Empty:
                    break

            if not chunks:
                log.warning("recording_no_data",
                           message="Recording stopped but no audio data captured")
                return None

            # Concatenate all chunks
            audio_data = np.concatenate(chunks, axis=0)

            duration_seconds = len(audio_data) / self.sample_rate
            log.info("recording_stopped",
                    samples=len(audio_data),
                    duration_seconds=f"{duration_seconds:.2f}",
                    channels=self.channels)

            return audio_data

        except Exception as e:
            log.warning("recording_stop_failed",
                       error=str(e))
            return None

    def save_wav(self, audio_data: np.ndarray, path: Optional[Path] = None) -> Path:
        """Save audio data as WAV file.

        Args:
            audio_data: Audio data to save (int16 numpy array)
            path: Optional path to save to (if None, creates temp file)

        Returns:
            Path to saved WAV file

        Raises:
            Exception: If file write fails (caller should catch and log)
        """
        if path is None:
            # Create temp file with .wav extension
            fd, temp_path = tempfile.mkstemp(suffix='.wav', prefix='recording_')
            import os
            os.close(fd)  # Close file descriptor, scipy will reopen
            path = Path(temp_path)

        # Write WAV file
        wavfile.write(path, self.sample_rate, audio_data)

        file_size = path.stat().st_size
        log.info("wav_file_saved",
                 path=str(path),
                 size_bytes=file_size,
                 sample_rate=self.sample_rate,
                 channels=self.channels)

        return path
