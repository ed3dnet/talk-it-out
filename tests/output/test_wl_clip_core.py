# pattern: Mixed (test file)
# Tests pure functions (Functional Core)

import pytest
from talk_it_out.output.strategies.wl_clip import (
    verify_clipboard_content,
    build_wl_copy_commands,
    build_shift_insert_command,
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
