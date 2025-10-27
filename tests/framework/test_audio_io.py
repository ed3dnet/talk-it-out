# pattern: Imperative Shell

import pytest
import numpy as np
from talk_it_out.framework import audio_io


def test_audio_recorder_accepts_audio_level_callback():
    """AudioRecorder should accept optional on_audio_level callback"""
    called = []

    recorder = audio_io.AudioRecorder(
        sample_rate=16000,
        channels=1,
        device=None,
        on_audio_level=lambda level: called.append(level)
    )

    assert recorder.on_audio_level is not None


def test_audio_callback_reports_audio_level():
    """_audio_callback should calculate and report audio level"""
    levels = []

    recorder = audio_io.AudioRecorder(
        sample_rate=16000,
        channels=1,
        device=None,
        on_audio_level=lambda level: levels.append(level)
    )

    # Simulate audio data (int16, values 0-32768)
    # Loud audio: mean abs value ~16000
    loud_data = np.array([[16000], [16000], [16000]], dtype=np.int16)

    # Call the audio callback directly
    recorder.frames = []
    recorder._audio_callback(loud_data, len(loud_data), None, None)

    # Should have called callback with normalized level
    assert len(levels) == 1
    assert 0.0 <= levels[0] <= 1.0
    assert levels[0] > 0.4  # ~16000/32768 ≈ 0.49
