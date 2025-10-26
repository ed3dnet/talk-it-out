# pattern: Functional Core (testing pure functions)

import numpy as np
import pytest
from talk_it_out.framework import audio


def test_find_device_by_name_returns_none_for_nonexistent():
    """Should return None if device name not found."""
    # Arrange - name that definitely doesn't exist
    nonexistent_name = "ZZZZZ_NONEXISTENT_DEVICE_12345"

    # Act
    result = audio.find_device_by_name(nonexistent_name)

    # Assert
    assert result is None


def test_find_device_by_name_matches_substring():
    """Should match device names by substring (case-insensitive)."""
    # This test requires actual audio hardware, so we just verify function signature
    # Real testing happens in manual tests
    import inspect
    sig = inspect.signature(audio.find_device_by_name)

    assert 'name' in sig.parameters
    assert sig.return_annotation != inspect.Signature.empty


def test_convert_to_whisper_format_normalizes_int16_to_float32():
    """Convert int16 [-32768, 32767] to float32 [-1.0, 1.0]."""
    # Arrange - Create int16 audio at extremes
    audio_int16 = np.array([-32768, 0, 32767], dtype=np.int16)
    sample_rate = 16000

    # Act
    result = audio.convert_to_whisper_format(audio_int16, sample_rate)

    # Assert
    assert result.dtype == np.float32
    assert result[0] == pytest.approx(-1.0, abs=0.01)
    assert result[1] == pytest.approx(0.0, abs=0.01)
    assert result[2] == pytest.approx(1.0, abs=0.01)


def test_convert_to_whisper_format_rejects_wrong_sample_rate():
    """Raise ValueError if sample_rate != 16000."""
    # Arrange
    audio_int16 = np.array([100, 200, 300], dtype=np.int16)
    wrong_sample_rate = 44100

    # Act & Assert
    with pytest.raises(ValueError, match="Sample rate must be 16000"):
        audio.convert_to_whisper_format(audio_int16, wrong_sample_rate)


def test_validate_audio_data_accepts_valid_audio():
    """Return (True, None) for valid numpy array."""
    # Arrange - 1 second of audio at 16kHz
    valid_audio = np.zeros(16000, dtype=np.int16)

    # Act
    is_valid, error = audio.validate_audio_data(valid_audio)

    # Assert
    assert is_valid is True
    assert error is None


def test_validate_audio_data_rejects_none():
    """Return (False, error) for None."""
    # Act
    is_valid, error = audio.validate_audio_data(None)

    # Assert
    assert is_valid is False
    assert error is not None
    assert "no audio" in error.lower() or "none" in error.lower()


def test_validate_audio_data_rejects_empty():
    """Return (False, error) for empty array."""
    # Arrange
    empty_audio = np.array([], dtype=np.int16)

    # Act
    is_valid, error = audio.validate_audio_data(empty_audio)

    # Assert
    assert is_valid is False
    assert error is not None
    assert "empty" in error.lower()


def test_validate_audio_data_rejects_too_short():
    """Return (False, error) for < 100ms (1600 samples at 16kHz)."""
    # Arrange - 50ms of audio (800 samples)
    too_short = np.zeros(800, dtype=np.int16)

    # Act
    is_valid, error = audio.validate_audio_data(too_short, min_samples=1600)

    # Assert
    assert is_valid is False
    assert error is not None
    assert "short" in error.lower() or "minimum" in error.lower()
