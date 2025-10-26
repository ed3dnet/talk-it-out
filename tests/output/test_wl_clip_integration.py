# pattern: Mixed (test file)
# Tests I/O operations with mocking

import pytest
from unittest.mock import patch, MagicMock
from talk_it_out.output.strategies.wl_clip import WlClipSimplePaste
from talk_it_out.output import OutputError


class TestDependencyVerification:
    """Tests for verify_dependencies() with mocked subprocess."""

    @patch('subprocess.run')
    def test_verify_dependencies_all_present(self, mock_run):
        """All tools present and ydotoold running - should not raise."""
        # Mock successful tool checks
        mock_run.return_value = MagicMock(returncode=0)

        strategy = WlClipSimplePaste({})

        strategy.verify_dependencies()  # Should not raise

        # Should check wl-copy, wl-paste, ydotool
        assert mock_run.call_count >= 3

    @patch('subprocess.run')
    def test_verify_dependencies_missing_wl_copy(self, mock_run):
        """Missing wl-copy raises OutputError with install instructions."""
        # wl-copy --help fails (not installed)
        def side_effect(cmd, *args, **kwargs):
            if 'wl-copy' in cmd:
                raise FileNotFoundError()
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect

        strategy = WlClipSimplePaste({})

        with pytest.raises(OutputError, match="wl-copy"):
            strategy.verify_dependencies()

    @patch('subprocess.run')
    def test_verify_dependencies_missing_ydotool(self, mock_run):
        """Missing ydotool raises OutputError with install instructions."""
        def side_effect(cmd, *args, **kwargs):
            if 'ydotool' in cmd:
                raise FileNotFoundError()
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect

        strategy = WlClipSimplePaste({})

        with pytest.raises(OutputError, match="ydotool"):
            strategy.verify_dependencies()

    @patch('subprocess.run')
    def test_verify_dependencies_daemon_not_running(self, mock_run):
        """ydotoold daemon not running raises OutputError."""
        # Tools present but pgrep ydotoold fails
        def side_effect(cmd, *args, **kwargs):
            if 'pgrep' in cmd and 'ydotoold' in cmd:
                return MagicMock(returncode=1)  # Not found
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect

        strategy = WlClipSimplePaste({})

        with pytest.raises(OutputError, match="ydotoold"):
            strategy.verify_dependencies()

    @patch('subprocess.run')
    def test_verify_dependencies_error_includes_install_instructions(self, mock_run):
        """Error message includes distro-specific install commands."""
        mock_run.side_effect = FileNotFoundError()

        strategy = WlClipSimplePaste({})

        with pytest.raises(OutputError) as exc_info:
            strategy.verify_dependencies()

        error_msg = str(exc_info.value)
        # Should mention at least one distro's install command
        assert any(pkg_mgr in error_msg for pkg_mgr in ["dnf", "apt", "pacman"])

    @patch('subprocess.run')
    @patch('os.access')
    @patch('pathlib.Path.exists')
    def test_verify_dependencies_socket_missing(self, mock_exists, mock_access, mock_run):
        """Custom socket path that doesn't exist raises OutputError."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_exists.return_value = False

        strategy = WlClipSimplePaste({"ydotool_socket": "/tmp/missing-socket"})

        with pytest.raises(OutputError, match="socket not found"):
            strategy.verify_dependencies()

    @patch('subprocess.run')
    @patch('os.access')
    @patch('pathlib.Path.stat')
    @patch('pathlib.Path.exists')
    def test_verify_dependencies_socket_not_writable(self, mock_exists, mock_stat, mock_access, mock_run):
        """Socket without write permissions raises OutputError."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_exists.return_value = True
        mock_access.return_value = False  # No read/write
        # Mock stat to return a fake mode
        mock_stat.return_value = MagicMock(st_mode=0o100600)

        strategy = WlClipSimplePaste({"ydotool_socket": "/tmp/readonly-socket"})

        with pytest.raises(OutputError, match="not readable/writable"):
            strategy.verify_dependencies()


import subprocess
import shutil


def has_wl_clipboard() -> bool:
    """Check if wl-copy and wl-paste are available."""
    return shutil.which("wl-copy") is not None and shutil.which("wl-paste") is not None


@pytest.mark.skipif(not has_wl_clipboard(), reason="wl-clipboard not installed")
@pytest.mark.clipboard
class TestClipboardOperations:
    """Tests with real wl-copy/wl-paste (run single-threaded)."""

    def test_copy_to_clipboard_single_target(self):
        """Copying to clipboard target works."""
        strategy = WlClipSimplePaste({"targets": ["clipboard"]})
        text = "test content for clipboard"

        strategy._copy_to_clipboard(text)

        # Verify with wl-paste (note: wl-paste adds trailing newline)
        result = subprocess.run(
            ["wl-paste"],
            capture_output=True,
            text=True,
        )
        assert result.stdout.rstrip('\n') == text

    def test_copy_to_primary_target(self):
        """Copying to primary selection works."""
        strategy = WlClipSimplePaste({"targets": ["primary"]})
        text = "test content for primary"

        strategy._copy_to_clipboard(text)

        # Verify with wl-paste --primary (note: wl-paste adds trailing newline)
        result = subprocess.run(
            ["wl-paste", "--primary"],
            capture_output=True,
            text=True,
        )
        assert result.stdout.rstrip('\n') == text

    def test_copy_to_both_targets(self):
        """Copying to both clipboard and primary works."""
        strategy = WlClipSimplePaste({"targets": ["clipboard", "primary"]})
        text = "test content for both"

        strategy._copy_to_clipboard(text)

        # Verify both (note: wl-paste adds trailing newline)
        clipboard_result = subprocess.run(
            ["wl-paste"],
            capture_output=True,
            text=True,
        )
        primary_result = subprocess.run(
            ["wl-paste", "--primary"],
            capture_output=True,
            text=True,
        )

        assert clipboard_result.stdout.rstrip('\n') == text
        assert primary_result.stdout.rstrip('\n') == text

    def test_verify_clipboard_ready_succeeds(self):
        """verify_clipboard_ready succeeds when content matches."""
        strategy = WlClipSimplePaste({"targets": ["clipboard"]})
        text = "test verification content"

        # Set clipboard using our method (avoids wl-copy hang issue)
        strategy._copy_to_clipboard(text)

        # Should not raise
        strategy._verify_clipboard_ready(text)

    def test_verify_clipboard_ready_timeout(self):
        """verify_clipboard_ready times out if content doesn't match."""
        strategy = WlClipSimplePaste({"targets": ["clipboard"]})
        strategy.clipboard_timeout = 0.3  # Short timeout for test

        # Set different content using our method
        strategy._copy_to_clipboard("wrong content")

        # Should timeout when looking for different content
        with pytest.raises(OutputError, match="timeout"):
            strategy._verify_clipboard_ready("expected content")


class TestKeystrokeInjection:
    """Tests for _send_shift_insert() with mocked ydotool."""

    @patch('talk_it_out.output.strategies.wl_clip.subprocess.run')
    def test_send_shift_insert_success(self, mock_run):
        """Successful ydotool call logs and returns."""
        mock_run.return_value = MagicMock(returncode=0)

        strategy = WlClipSimplePaste({})

        strategy._send_shift_insert()  # Should not raise

        # Verify ydotool called with correct key sequence
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["ydotool", "key", "42:1", "110:1", "110:0", "42:0"]

    @patch('talk_it_out.output.strategies.wl_clip.subprocess.run')
    def test_send_shift_insert_failure(self, mock_run):
        """ydotool failure raises OutputError."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr=b"ydotool error message"
        )

        strategy = WlClipSimplePaste({})

        with pytest.raises(OutputError, match="ydotool failed"):
            strategy._send_shift_insert()

    @patch('talk_it_out.output.strategies.wl_clip.subprocess.run')
    def test_send_shift_insert_not_found(self, mock_run):
        """Missing ydotool raises OutputError."""
        mock_run.side_effect = FileNotFoundError()

        strategy = WlClipSimplePaste({})

        with pytest.raises(OutputError, match="ydotool not found"):
            strategy._send_shift_insert()

    @patch('talk_it_out.output.strategies.wl_clip.subprocess.run')
    def test_send_shift_insert_with_custom_socket(self, mock_run):
        """Custom socket sets YDOTOOL_SOCKET env var."""
        mock_run.return_value = MagicMock(returncode=0)

        strategy = WlClipSimplePaste({"ydotool_socket": "/tmp/custom"})

        strategy._send_shift_insert()

        # Verify env passed to subprocess
        call_kwargs = mock_run.call_args[1]
        assert "env" in call_kwargs
        assert "YDOTOOL_SOCKET" in call_kwargs["env"]
        assert call_kwargs["env"]["YDOTOOL_SOCKET"] == "/tmp/custom"


@pytest.mark.skipif(not has_wl_clipboard(), reason="wl-clipboard not installed")
@pytest.mark.clipboard
class TestPasteTextFullFlow:
    """Full paste_text() with real clipboard, mocked ydotool."""

    def test_paste_text_success(self):
        """Full paste workflow: copy → verify → delay → paste."""
        # Use real subprocess for this test - we mock ydotool at method level
        strategy = WlClipSimplePaste({"targets": ["clipboard"]})
        strategy.virtual_device_delay = 0.1  # Short delay for test
        text = "Full workflow test content"

        # Mock only _send_shift_insert to avoid needing ydotool
        with patch.object(strategy, '_send_shift_insert') as mock_shift_insert:
            strategy.paste_text(text)

            # Verify _send_shift_insert was called
            mock_shift_insert.assert_called_once()

        # Verify clipboard has content (real wl-paste check)
        result = subprocess.run(
            ["wl-paste"],
            capture_output=True,
            text=True,
        )
        # wl-paste adds trailing newline even with --trim-newline on wl-copy
        assert result.stdout.rstrip('\n') == text
