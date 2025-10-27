# pattern: Imperative Shell

import pytest
from unittest.mock import Mock, patch
from talk_it_out.framework import session
from talk_it_out.framework import config
from talk_it_out.framework import keyboard


def test_session_initializes_with_config():
    """Session should initialize with config dict"""
    cfg = config.default_config()
    s = session.Session(cfg)
    assert s.config == cfg


def test_session_accepts_callbacks():
    """Session should accept optional callback functions"""
    cfg = config.default_config()
    called = []

    s = session.Session(
        cfg,
        on_recording_started=lambda: called.append("recording_started"),
        on_recording_stopped=lambda: called.append("recording_stopped"),
        on_transcription_started=lambda: called.append("transcription_started"),
        on_transcription_complete=lambda text: called.append(f"complete:{text}"),
        on_audio_level=lambda level: called.append(f"level:{level}"),
        on_error=lambda msg: called.append(f"error:{msg}")
    )

    # Verify callbacks stored
    assert s.on_recording_started is not None
    assert s.on_recording_stopped is not None
    assert s.on_transcription_started is not None
    assert s.on_transcription_complete is not None
    assert s.on_audio_level is not None
    assert s.on_error is not None


def test_session_initializes_components():
    """Session should initialize keyboard monitor, audio recorder, transcriber, output strategy"""
    cfg = config.default_config()

    with patch('talk_it_out.framework.session.keyboard_io.KeyboardMonitor') as mock_monitor, \
         patch('talk_it_out.framework.session.audio_io.AudioRecorder') as mock_audio, \
         patch('talk_it_out.framework.session.whisper_io.Transcriber') as mock_transcriber, \
         patch('talk_it_out.framework.session.create_output_strategy') as mock_output:

        # Create session with audio level callback
        audio_level_callback = Mock()
        s = session.Session(cfg, on_audio_level=audio_level_callback)

        # Verify components created
        mock_monitor.assert_called_once()
        mock_audio.assert_called_once_with(
            sample_rate=cfg["audio"]["sample_rate"],
            channels=cfg["audio"]["channels"],
            device=cfg["audio"]["device"],
            on_audio_level=audio_level_callback
        )
        mock_transcriber.assert_called_once()
        mock_output.assert_called_once_with(cfg)


def test_session_start_monitoring():
    """Session.start_monitoring() should start keyboard monitor"""
    cfg = config.default_config()

    with patch('talk_it_out.framework.keyboard_io.KeyboardMonitor') as mock_monitor_class:
        mock_monitor = Mock()
        mock_monitor_class.return_value = mock_monitor

        s = session.Session(cfg)
        s.start_monitoring()

        mock_monitor.start.assert_called_once()


def test_session_stop():
    """Session.stop() should trigger cleanup"""
    cfg = config.default_config()

    with patch('talk_it_out.framework.keyboard_io.KeyboardMonitor'):
        s = session.Session(cfg)

        # Mock the cleanup registry
        s.cleanup_registry.cleanup = Mock()

        s.stop()

        s.cleanup_registry.cleanup.assert_called_once()


def test_session_process_combo_pressed():
    """Session should start recording on COMBO_PRESSED"""
    cfg = config.default_config()
    recording_started_called = []

    with patch('talk_it_out.framework.audio_io.AudioRecorder') as mock_audio_class:
        mock_audio = Mock()
        mock_audio_class.return_value = mock_audio

        s = session.Session(
            cfg,
            on_recording_started=lambda: recording_started_called.append(True)
        )

        event = keyboard.ComboEvent(
            event_type="combo_pressed",
            combo_type="paste",
            device_path="/dev/input/event0"
        )

        s.process_combo_event(event)

        # Should start recording and call callback
        mock_audio.start_recording.assert_called_once()
        assert recording_started_called == [True]


def test_session_calls_transcription_started_callback():
    """Session should call on_transcription_started callback when transcription begins"""
    cfg = config.default_config()
    transcription_started_called = []

    with patch('talk_it_out.framework.audio_io.AudioRecorder') as mock_audio_class, \
         patch('talk_it_out.framework.whisper_io.Transcriber') as mock_transcriber_class, \
         patch('talk_it_out.framework.session.create_output_strategy') as mock_output:

        # Setup mocks
        mock_audio = Mock()
        mock_audio.sample_rate = 16000
        mock_audio.stop_recording.return_value = b'\x00\x01' * 8000  # 1 second of valid audio
        mock_audio.save_wav.return_value = Mock(unlink=Mock())
        mock_audio_class.return_value = mock_audio

        mock_transcriber = Mock()
        mock_transcriber.transcribe_from_wav.return_value = "test transcription"
        mock_transcriber_class.return_value = mock_transcriber

        mock_output_strategy = Mock()
        mock_output.return_value = mock_output_strategy

        # Create session with callback
        s = session.Session(
            cfg,
            on_transcription_started=lambda: transcription_started_called.append(True)
        )

        # Simulate combo release
        event = keyboard.ComboEvent(
            event_type="combo_released",
            combo_type="paste",
            device_path="/dev/input/event0"
        )

        s.process_combo_event(event)

        # Should have called transcription_started callback
        assert transcription_started_called == [True]
