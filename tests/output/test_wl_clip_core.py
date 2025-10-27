# pattern: Mixed (test file)
# Tests pure functions (Functional Core)

import os
import tempfile
from pathlib import Path
import pytest
from talk_it_out.output.strategies.wl_clip import (
    verify_clipboard_content,
    build_wl_copy_commands,
    build_shift_insert_command,
    WlClipSimplePaste,
)


def test_verify_clipboard_content_exact_match():
    """Returns True when content matches exactly."""
    expected = "Hello, world!"
    actual = "Hello, world!"

    assert verify_clipboard_content(expected, actual) is True


def test_verify_clipboard_content_mismatch():
    """Returns False when content differs."""
    expected = "Hello"
    actual = "Goodbye"

    assert verify_clipboard_content(expected, actual) is False


def test_verify_clipboard_content_whitespace_sensitive():
    """Whitespace differences cause mismatch."""
    expected = "Hello"
    actual = "Hello\n"

    assert verify_clipboard_content(expected, actual) is False


def test_build_wl_copy_commands_clipboard_target():
    """Builds wl-copy command for clipboard target."""
    text = "test content"
    targets = ["clipboard"]

    commands = build_wl_copy_commands(text, targets)

    assert len(commands) == 1
    cmd, input_text = commands[0]
    assert cmd == ["wl-copy", "--type", "text/plain"]
    assert input_text == text


def test_build_wl_copy_commands_primary_target():
    """Builds wl-copy command for primary selection."""
    text = "test content"
    targets = ["primary"]

    commands = build_wl_copy_commands(text, targets)

    assert len(commands) == 1
    cmd, input_text = commands[0]
    assert cmd == ["wl-copy", "--primary", "--type", "text/plain"]
    assert input_text == text


def test_build_wl_copy_commands_both_targets():
    """Builds commands for both clipboard and primary."""
    text = "test content"
    targets = ["clipboard", "primary"]

    commands = build_wl_copy_commands(text, targets)

    assert len(commands) == 2
    assert commands[0][0] == ["wl-copy", "--type", "text/plain"]
    assert commands[1][0] == ["wl-copy", "--primary", "--type", "text/plain"]
    assert all(cmd[1] == text for cmd in commands)


def test_build_shift_insert_command():
    """Builds ydotool command for Shift+Insert."""
    cmd = build_shift_insert_command()

    # Left shift (42) press, Insert (110) press, Insert release, shift release
    assert cmd == ["ydotool", "key", "42:1", "110:1", "110:0", "42:0"]


def test_get_ydotool_env_with_socket():
    """Custom socket path sets YDOTOOL_SOCKET env var."""
    from talk_it_out.output.strategies.wl_clip import get_ydotool_env

    env = get_ydotool_env("/tmp/custom-socket")

    assert env == {"YDOTOOL_SOCKET": "/tmp/custom-socket"}


def test_get_ydotool_env_empty_socket():
    """Empty socket path returns empty env (uses default)."""
    from talk_it_out.output.strategies.wl_clip import get_ydotool_env

    env = get_ydotool_env("")

    assert env == {}


def test_ydotool_socket_autodetect_run_user():
    """Auto-detect socket in /run/user/{uid}/.ydotool_socket."""
    uid = os.getuid()
    socket_path = f"/run/user/{uid}/.ydotool_socket"

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create temporary socket file
        test_socket = Path(tmpdir) / ".ydotool_socket"
        test_socket.touch()

        # Temporarily patch os.path.exists to return True for the expected path
        original_exists = os.path.exists
        def mock_exists(path):
            if path == socket_path:
                return True
            return original_exists(path)

        os.path.exists = mock_exists
        try:
            strategy = WlClipSimplePaste({})
            assert strategy.ydotool_socket == socket_path
        finally:
            os.path.exists = original_exists


def test_ydotool_socket_autodetect_var_run_user():
    """Auto-detect socket in /var/run/user/{uid}/.ydotool_socket."""
    uid = os.getuid()
    socket_path = f"/var/run/user/{uid}/.ydotool_socket"

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create temporary socket file
        test_socket = Path(tmpdir) / ".ydotool_socket"
        test_socket.touch()

        # Temporarily patch os.path.exists
        original_exists = os.path.exists
        def mock_exists(path):
            # First path doesn't exist, second path does
            if path == f"/run/user/{uid}/.ydotool_socket":
                return False
            if path == socket_path:
                return True
            return original_exists(path)

        os.path.exists = mock_exists
        try:
            strategy = WlClipSimplePaste({})
            assert strategy.ydotool_socket == socket_path
        finally:
            os.path.exists = original_exists


def test_ydotool_socket_autodetect_tmp():
    """Auto-detect socket in /tmp/.ydotool_socket."""
    uid = os.getuid()
    socket_path = "/tmp/.ydotool_socket"

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create temporary socket file
        test_socket = Path(tmpdir) / ".ydotool_socket"
        test_socket.touch()

        # Temporarily patch os.path.exists
        original_exists = os.path.exists
        def mock_exists(path):
            # First two paths don't exist, third path does
            if path == f"/run/user/{uid}/.ydotool_socket":
                return False
            if path == f"/var/run/user/{uid}/.ydotool_socket":
                return False
            if path == socket_path:
                return True
            return original_exists(path)

        os.path.exists = mock_exists
        try:
            strategy = WlClipSimplePaste({})
            assert strategy.ydotool_socket == socket_path
        finally:
            os.path.exists = original_exists


def test_ydotool_socket_autodetect_none_found():
    """Auto-detect returns empty string when no socket found."""
    uid = os.getuid()

    # Temporarily patch os.path.exists to return False for all paths
    original_exists = os.path.exists
    def mock_exists(path):
        if path in [
            f"/run/user/{uid}/.ydotool_socket",
            f"/var/run/user/{uid}/.ydotool_socket",
            "/tmp/.ydotool_socket"
        ]:
            return False
        return original_exists(path)

    os.path.exists = mock_exists
    try:
        strategy = WlClipSimplePaste({})
        assert strategy.ydotool_socket == ""
    finally:
        os.path.exists = original_exists


def test_ydotool_socket_configured_skips_autodetect():
    """Configured socket path skips auto-detection."""
    configured_path = "/custom/path/to/socket"
    strategy = WlClipSimplePaste({"ydotool_socket": configured_path})

    # Should use configured path, not auto-detect
    assert strategy.ydotool_socket == configured_path
