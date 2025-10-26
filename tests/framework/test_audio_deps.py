# pattern: Functional Core (testing pure functions)

from talk_it_out.framework import audio_deps


def test_get_portaudio_install_command_for_fedora():
    """Should return dnf install command for Fedora."""
    # Fedora uses ID='fedora' in os-release
    cmd = audio_deps.get_portaudio_install_command()

    # Command should use dnf (Fedora's package manager)
    assert "dnf" in cmd or "yum" in cmd
    assert "portaudio" in cmd


def test_check_portaudio_returns_tuple():
    """Should return (bool, Optional[str]) tuple."""
    result = audio_deps.check_portaudio()

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], bool)
    # result[1] is either None or str
    assert result[1] is None or isinstance(result[1], str)


def test_check_portaudio_error_includes_install_command():
    """If PortAudio missing, error message includes install command."""
    available, error = audio_deps.check_portaudio()

    # If not available, error should mention how to install
    if not available:
        assert error is not None
        assert "install" in error.lower()
