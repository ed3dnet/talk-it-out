# pattern: Functional Core
# Pure functions for audio format handling and validation

import numpy as np
from typing import Optional


def convert_to_whisper_format(
    audio_int16: np.ndarray,
    sample_rate: int
) -> np.ndarray:
    """Convert int16 audio to float32 normalized for Whisper.

    Args:
        audio_int16: Audio data as int16 array
        sample_rate: Sample rate in Hz (must be 16000 for Whisper)

    Returns:
        Audio data as float32 normalized to [-1.0, 1.0]

    Raises:
        ValueError: If sample_rate is not 16000
    """
    if sample_rate != 16000:
        raise ValueError(f"Sample rate must be 16000, got {sample_rate}")

    return audio_int16.astype(np.float32) / 32768.0


def validate_audio_data(
    audio: Optional[np.ndarray],
    min_samples: int = 1600  # 0.1 seconds at 16kHz
) -> tuple[bool, Optional[str]]:
    """Validate recorded audio data.

    Args:
        audio: Audio data to validate (or None)
        min_samples: Minimum number of samples required (default 1600 = 100ms at 16kHz)

    Returns:
        (True, None) if valid
        (False, error_message) if invalid
    """
    if audio is None:
        return False, "No audio data captured"

    if len(audio) == 0:
        return False, "Audio data is empty"

    if len(audio) < min_samples:
        duration_ms = (len(audio) / 16000) * 1000
        min_duration_ms = (min_samples / 16000) * 1000
        return False, f"Recording too short: {duration_ms:.0f}ms (minimum {min_duration_ms:.0f}ms)"

    return True, None


def find_device_by_name(name: str) -> Optional[tuple[int, dict]]:
    """Find audio input device by name substring matching.

    Args:
        name: Device name or substring to search for (case-insensitive)

    Returns:
        (device_index, device_info) if found, None otherwise

    Note:
        Requires sounddevice to be imported. Returns None if sounddevice
        not available or device not found.
    """
    try:
        import sounddevice as sd
    except ImportError:
        return None

    devices = sd.query_devices()
    for device in devices:
        # Only consider input devices
        if device['max_input_channels'] > 0:
            # Case-insensitive substring matching
            if name.lower() in device['name'].lower():
                return (device['index'], device)

    return None
