# pattern: Imperative Shell
# Whisper transcription with faster-whisper

import time
import structlog
import numpy as np
from faster_whisper import WhisperModel
from talk_it_out.framework.audio import convert_to_whisper_format

log = structlog.get_logger()


class Transcriber:
    """Transcribe audio using faster-whisper."""

    def _detect_device_and_compute(self) -> tuple[str, str]:
        """Auto-detect device and compute_type if set to 'auto'.

        Returns:
            Tuple of (device, compute_type)
        """
        device = self.config.get("device", "auto")
        compute_type = self.config.get("compute_type", "auto")

        if device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
                log.debug("device_auto_detected", device=device, cuda_available=torch.cuda.is_available())
            except ImportError:
                device = "cpu"
                log.debug("device_auto_detected", device="cpu", reason="torch_not_available")

        if compute_type == "auto":
            # float16 for GPU, int8 for CPU (memory efficient)
            compute_type = "float16" if device == "cuda" else "int8"
            log.debug("compute_type_auto_selected", compute_type=compute_type, device=device)

        return device, compute_type

    def __init__(self, whisper_config: dict):
        """Initialize WhisperModel with auto-detected device/compute settings.

        Args:
            whisper_config: Dict with keys: model, language, device,
                          compute_type, beam_size, vad_filter

        Raises:
            RuntimeError: If model fails to load
        """
        self.config = whisper_config

        # Auto-detect device and compute type
        self.device, self.compute_type = self._detect_device_and_compute()

        log.info(
            "whisper_initializing",
            model=self.config["model"],
            device=self.device,
            compute_type=self.compute_type,
        )

        try:
            self.model = WhisperModel(
                self.config["model"],
                device=self.device,
                compute_type=self.compute_type,
            )
            log.info("whisper_model_loaded", model=self.config["model"])
        except Exception as e:
            log.error("whisper_model_load_failed", error=str(e))
            raise RuntimeError(f"Failed to load Whisper model: {e}")

    def transcribe_from_wav(self, wav_path) -> str:
        """Transcribe audio from WAV file.

        Args:
            wav_path: Path to WAV file (must be 16kHz mono)

        Returns:
            Transcribed text (stripped, joined from all segments)

        Raises:
            ValueError: If WAV file is not 16kHz or cannot be read
        """
        from scipy.io import wavfile
        from pathlib import Path

        try:
            sample_rate, audio_int16 = wavfile.read(Path(wav_path))
        except Exception as e:
            raise ValueError(f"Failed to read WAV file {wav_path}: {e}")

        return self.transcribe(audio_int16, sample_rate)

    def transcribe(self, audio_int16: np.ndarray, sample_rate: int) -> str:
        """Transcribe audio to text.

        Args:
            audio_int16: Audio data as int16 numpy array
            sample_rate: Sample rate (must be 16000)

        Returns:
            Transcribed text (stripped, joined from all segments)

        Raises:
            ValueError: If sample_rate != 16000
        """
        if sample_rate != 16000:
            raise ValueError(f"Sample rate must be 16000, got {sample_rate}")

        # Convert int16 to float32 format for Whisper
        audio_float32 = convert_to_whisper_format(audio_int16, sample_rate)

        # Transcribe
        start_time = time.time()

        segments, info = self.model.transcribe(
            audio_float32,
            language=self.config.get("language", "en"),
            beam_size=self.config.get("beam_size", 5),
            vad_filter=self.config.get("vad_filter", True),
        )

        # Join segments
        text_parts = [segment.text for segment in segments]
        text = " ".join(text_parts).strip()

        duration_ms = (time.time() - start_time) * 1000

        log.info(
            "transcription_complete",
            text_length=len(text),
            segments=len(text_parts),
            detected_language=info.language,
            language_probability=round(info.language_probability, 3),
            duration_ms=int(duration_ms),
        )

        log.debug("transcription_text", text=text[:200])  # First 200 chars

        return text
