import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from talk_it_out.framework.whisper_io import Transcriber


def test_device_auto_detect_cuda_available():
    """Auto-detect should use CUDA when available."""
    with patch('talk_it_out.framework.whisper_io.WhisperModel'):
        # Mock torch module to be importable and return cuda available
        mock_torch = Mock()
        mock_torch.cuda.is_available.return_value = True

        with patch.dict('sys.modules', {'torch': mock_torch}):
            transcriber = Transcriber({"model": "tiny", "device": "auto", "compute_type": "auto"})
            assert transcriber.device == "cuda"
            assert transcriber.compute_type == "float16"


def test_device_auto_detect_cuda_unavailable():
    """Auto-detect should fall back to CPU when CUDA unavailable."""
    with patch('talk_it_out.framework.whisper_io.WhisperModel'):
        # Mock torch module to be importable but return cuda unavailable
        mock_torch = Mock()
        mock_torch.cuda.is_available.return_value = False

        with patch.dict('sys.modules', {'torch': mock_torch}):
            transcriber = Transcriber({"model": "tiny", "device": "auto", "compute_type": "auto"})
            assert transcriber.device == "cpu"
            assert transcriber.compute_type == "int8"


def test_device_auto_detect_no_torch():
    """Auto-detect should fall back to CPU when torch not installed."""
    import sys
    import builtins

    with patch('talk_it_out.framework.whisper_io.WhisperModel'):
        # Save original import
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == 'torch':
                raise ImportError("No module named 'torch'")
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            transcriber = Transcriber({"model": "tiny", "device": "auto", "compute_type": "auto"})
            # Import error in detection, should default to CPU
            assert transcriber.device == "cpu"
            assert transcriber.compute_type == "int8"


def test_explicit_device_cuda():
    """Should use explicit device setting."""
    with patch('talk_it_out.framework.whisper_io.WhisperModel'):
        transcriber = Transcriber({"model": "tiny", "device": "cuda", "compute_type": "float16"})
        assert transcriber.device == "cuda"
        assert transcriber.compute_type == "float16"


def test_transcribe_calls_convert_format():
    """Should use convert_to_whisper_format for audio conversion."""
    with patch('talk_it_out.framework.whisper_io.WhisperModel') as mock_model_class:
        mock_model = Mock()
        mock_model.transcribe.return_value = ([], Mock(language="en", language_probability=0.99))
        mock_model_class.return_value = mock_model

        with patch('talk_it_out.framework.whisper_io.convert_to_whisper_format') as mock_convert:
            mock_convert.return_value = np.zeros(16000, dtype=np.float32)

            transcriber = Transcriber({"model": "tiny", "language": "en"})
            audio_int16 = np.zeros(16000, dtype=np.int16)
            transcriber.transcribe(audio_int16, 16000)

            mock_convert.assert_called_once_with(audio_int16, 16000)


def test_transcribe_joins_segments():
    """Should join all segments with spaces."""
    with patch('talk_it_out.framework.whisper_io.WhisperModel') as mock_model_class:
        mock_model = Mock()

        # Create mock segments
        segment1 = Mock(text="Hello")
        segment2 = Mock(text="world")
        segment3 = Mock(text="today")

        mock_info = Mock(language="en", language_probability=0.99)
        mock_model.transcribe.return_value = ([segment1, segment2, segment3], mock_info)
        mock_model_class.return_value = mock_model

        with patch('talk_it_out.framework.whisper_io.convert_to_whisper_format'):
            transcriber = Transcriber({"model": "tiny", "language": "en"})
            audio_int16 = np.zeros(16000, dtype=np.int16)
            result = transcriber.transcribe(audio_int16, 16000)

            assert result == "Hello world today"


def test_transcribe_strips_whitespace():
    """Should strip leading/trailing whitespace."""
    with patch('talk_it_out.framework.whisper_io.WhisperModel') as mock_model_class:
        mock_model = Mock()
        segment = Mock(text="  Hello world  ")
        mock_info = Mock(language="en", language_probability=0.99)
        mock_model.transcribe.return_value = ([segment], mock_info)
        mock_model_class.return_value = mock_model

        with patch('talk_it_out.framework.whisper_io.convert_to_whisper_format'):
            transcriber = Transcriber({"model": "tiny", "language": "en"})
            audio_int16 = np.zeros(16000, dtype=np.int16)
            result = transcriber.transcribe(audio_int16, 16000)

            assert result == "Hello world"


def test_transcribe_invalid_sample_rate():
    """Should raise ValueError for wrong sample rate."""
    with patch('talk_it_out.framework.whisper_io.WhisperModel'):
        transcriber = Transcriber({"model": "tiny", "language": "en"})
        audio_int16 = np.zeros(16000, dtype=np.int16)

        with pytest.raises(ValueError, match="Sample rate must be 16000"):
            transcriber.transcribe(audio_int16, 44100)


def test_model_load_failure():
    """Should raise RuntimeError if model fails to load."""
    with patch('talk_it_out.framework.whisper_io.WhisperModel', side_effect=Exception("Network error")):
        with pytest.raises(RuntimeError, match="Failed to load Whisper model"):
            Transcriber({"model": "turbo", "language": "en"})
