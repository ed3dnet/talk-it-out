# pattern: Mixed (unavoidable)
# Functional Core (pure functions) + Imperative Shell (WlClipSimplePaste class)
# Mixed because both business logic and I/O live in same module, but separated
# into different functions/methods for testability

import os
import subprocess
import time
from pathlib import Path
import structlog

from ..base import OutputStrategy, OutputError

log = structlog.get_logger()


# ============================================================================
# Functional Core - Pure Functions
# ============================================================================


def verify_clipboard_content(expected: str, actual: str) -> bool:
    """Exact text comparison for clipboard verification.

    Args:
        expected: Text that should be in clipboard
        actual: Text retrieved from clipboard

    Returns:
        True if content matches exactly, False otherwise
    """
    return expected == actual


def build_wl_copy_commands(text: str, targets: list[str]) -> list[tuple[list[str], str]]:
    """Build wl-copy command lists for each target.

    Args:
        text: Text to copy to clipboard
        targets: List of clipboard targets ("clipboard", "primary")

    Returns:
        List of (command_args, input_text) tuples
    """
    commands = []
    for target in targets:
        if target == "clipboard":
            commands.append((["wl-copy", "--type", "text/plain"], text))
        elif target == "primary":
            commands.append((["wl-copy", "--primary", "--type", "text/plain"], text))
    return commands


def build_shift_insert_command() -> list[str]:
    """Build ydotool command for Shift+Insert keystroke.

    Key codes from Linux input-event-codes.h:
        42 = KEY_LEFTSHIFT
        110 = KEY_INSERT

    Format: KEYCODE:STATE where 1=press, 0=release

    Returns:
        Command args for ydotool
    """
    return ["ydotool", "key", "42:1", "110:1", "110:0", "42:0"]


def get_ydotool_env(socket_path: str) -> dict[str, str]:
    """Build environment dict for ydotool subprocess.

    Args:
        socket_path: Path to ydotool socket, or empty string to use default

    Returns:
        Environment dict with YDOTOOL_SOCKET if needed
    """
    if socket_path:
        return {"YDOTOOL_SOCKET": socket_path}
    return {}


# ============================================================================
# Imperative Shell - I/O Operations (to be implemented next)
# ============================================================================

class WlClipSimplePaste(OutputStrategy):
    """Output strategy using wl-clipboard + ydotool.

    Workflow:
        1. Copy text to clipboard(s) via wl-copy
        2. Poll wl-paste to verify clipboard ready
        3. Delay for ydotool virtual device recognition
        4. Send Shift+Insert keystroke via ydotool
    """

    def __init__(self, config: dict):
        """Initialize from [output.wl-clip] config section."""
        self.targets = config.get("targets", ["clipboard", "primary"])
        self.ydotool_socket = config.get("ydotool_socket", "")
        self.clipboard_timeout = 2.0  # seconds
        self.poll_interval = 0.1  # seconds
        self.virtual_device_delay = 0.5  # seconds
        self.log = structlog.get_logger()

        # Auto-detect ydotool socket if not configured
        if not self.ydotool_socket:
            uid = os.getuid()
            candidates = [
                f"/run/user/{uid}/.ydotool_socket",
                f"/var/run/user/{uid}/.ydotool_socket",
                "/tmp/.ydotool_socket"
            ]
            for path in candidates:
                if os.path.exists(path):
                    self.ydotool_socket = path
                    self.log.debug("ydotool_socket_detected", path=path)
                    break

    def verify_dependencies(self) -> None:
        """Check wl-copy, wl-paste, ydotool, ydotoold.

        Raises:
            OutputError: With install instructions if missing
        """
        missing_tools = []

        # Check wl-copy
        try:
            subprocess.run(
                ["wl-copy", "--help"],
                capture_output=True,
                check=True,
            )
            log.debug("dependency_check", tool="wl-copy", status="found")
        except (FileNotFoundError, subprocess.CalledProcessError):
            missing_tools.append("wl-copy")
            log.debug("dependency_check", tool="wl-copy", status="missing")

        # Check wl-paste
        try:
            subprocess.run(
                ["wl-paste", "--help"],
                capture_output=True,
                check=True,
            )
            log.debug("dependency_check", tool="wl-paste", status="found")
        except (FileNotFoundError, subprocess.CalledProcessError):
            missing_tools.append("wl-paste")
            log.debug("dependency_check", tool="wl-paste", status="missing")

        # Check ydotool
        try:
            subprocess.run(
                ["ydotool", "help"],
                capture_output=True,
                check=True,
            )
            log.debug("dependency_check", tool="ydotool", status="found")
        except (FileNotFoundError, subprocess.CalledProcessError):
            missing_tools.append("ydotool")
            log.debug("dependency_check", tool="ydotool", status="missing")

        # Check ydotoold daemon
        daemon_running = False
        try:
            result = subprocess.run(
                ["pgrep", "-x", "ydotoold"],
                capture_output=True,
            )
            daemon_running = result.returncode == 0
            log.debug("dependency_check", daemon="ydotoold", running=daemon_running)
        except FileNotFoundError:
            log.debug("dependency_check", daemon="ydotoold", status="pgrep_missing")

        # Build error message if any dependencies missing
        if missing_tools or not daemon_running:
            error_parts = [
                "Required tools not found for output strategy 'wl-clip-simplepaste'\n"
            ]

            if "wl-copy" in missing_tools or "wl-paste" in missing_tools:
                error_parts.append("Missing: wl-copy, wl-paste")
                error_parts.append("Install: sudo dnf install wl-clipboard    # Fedora/RHEL")
                error_parts.append("         sudo apt install wl-clipboard    # Debian/Ubuntu")
                error_parts.append("         sudo pacman -S wl-clipboard      # Arch\n")

            if "ydotool" in missing_tools:
                error_parts.append("Missing: ydotool")
                error_parts.append("Install: sudo dnf install ydotool         # Fedora/RHEL")
                error_parts.append("         sudo apt install ydotool         # Debian/Ubuntu")
                error_parts.append("         yay -S ydotool-git               # Arch (AUR)\n")

            if not daemon_running and "ydotool" not in missing_tools:
                error_parts.append("ydotoold daemon not running:")
                error_parts.append("Start: sudo systemctl start ydotoold")
                error_parts.append("Enable: sudo systemctl enable ydotoold\n")

            error_parts.append("See: https://github.com/ReimuNotMoe/ydotool")

            raise OutputError("\n".join(error_parts))

        # Check ydotool socket if configured
        if self.ydotool_socket:
            socket_path = Path(self.ydotool_socket)

            if not socket_path.exists():
                raise OutputError(
                    f"ydotool socket not found: {self.ydotool_socket}\n"
                    f"Check YDOTOOL_SOCKET path or start ydotoold daemon"
                )

            # Check read/write permissions
            if not os.access(socket_path, os.R_OK | os.W_OK):
                raise OutputError(
                    f"ydotool socket not readable/writable: {self.ydotool_socket}\n"
                    f"Current user: {os.getenv('USER')}\n"
                    f"Socket permissions: {oct(socket_path.stat().st_mode)[-3:]}\n"
                    f"Fix: sudo chmod 666 {self.ydotool_socket}  # or add user to ydotool group"
                )

            log.debug("ydotool_socket_verified", path=self.ydotool_socket)

        log.info("output_dependencies_verified", strategy="wl-clip-simplepaste")

    def _copy_to_clipboard(self, text: str) -> None:
        """Run wl-copy for each configured target.

        Args:
            text: Text to copy

        Raises:
            OutputError: If wl-copy fails
        """
        commands = build_wl_copy_commands(text, self.targets)

        for cmd, input_text in commands:
            log.debug("running_wl_copy", command=cmd)
            try:
                # Use Popen since wl-copy forks to background to serve clipboard.
                # subprocess.run() waits for forked processes which causes hangs.
                # start_new_session=True prevents subprocess from waiting.
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True,
                )
                # Write input and close stdin
                stdout, stderr = proc.communicate(input_text.encode(), timeout=1.0)

                # Check if process failed
                if proc.returncode not in (None, 0):
                    raise OutputError(f"wl-copy failed: {stderr.decode()}")

            except subprocess.TimeoutExpired:
                # wl-copy forked successfully, still serving clipboard in background
                # This is expected behavior
                pass
            except FileNotFoundError:
                raise OutputError("wl-copy not found - run verify_dependencies() first")

    def _verify_clipboard_ready(self, expected_text: str) -> None:
        """Poll wl-paste until content matches or timeout.

        Args:
            expected_text: Text that should be in clipboard

        Raises:
            OutputError: If verification times out
        """
        log.debug("verifying_clipboard")
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > self.clipboard_timeout:
                raise OutputError(
                    f"Clipboard verification timeout after {self.clipboard_timeout}s"
                )

            try:
                result = subprocess.run(
                    ["wl-paste"],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    # wl-paste adds a trailing newline, strip it for comparison
                    actual = result.stdout.rstrip('\n')
                    if verify_clipboard_content(expected_text, actual):
                        log.debug("clipboard_verified", elapsed_ms=int(elapsed * 1000))
                        return
            except FileNotFoundError:
                raise OutputError("wl-paste not found")

            time.sleep(self.poll_interval)

    def _send_shift_insert(self) -> None:
        """Send Shift+Insert keystroke via ydotool.

        Raises:
            OutputError: If ydotool fails
        """
        cmd = build_shift_insert_command()
        env = get_ydotool_env(self.ydotool_socket)

        log.info("sending_shift_insert")
        log.debug("running_ydotool", command=cmd, env=env)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env={**os.environ, **env} if env else None,
            )

            if result.returncode != 0:
                stderr = result.stderr.strip() if result.stderr else ""
                stdout = result.stdout.strip() if result.stdout else ""
                error_msg = stderr or stdout or "(no error output)"
                raise OutputError(f"ydotool failed (exit {result.returncode}): {error_msg}")

        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if e.stderr else ""
            stdout = e.stdout.strip() if e.stdout else ""
            error_msg = stderr or stdout or "(no error output)"
            raise OutputError(f"ydotool failed (exit {e.returncode}): {error_msg}")
        except FileNotFoundError:
            raise OutputError("ydotool not found - run verify_dependencies() first")

    def paste_text(self, text: str) -> None:
        """Copy to clipboard, verify, then paste.

        Args:
            text: Transcribed text to paste

        Raises:
            OutputError: If any step fails
        """
        log.info("paste_operation_started", text_length=len(text))

        # Step 1: Copy to clipboard(s)
        self._copy_to_clipboard(text)

        # Step 2: Poll-verify clipboard ready
        self._verify_clipboard_ready(text)

        # Step 3: Delay for ydotool virtual device recognition
        log.debug("waiting_for_virtual_device", delay_ms=int(self.virtual_device_delay * 1000))
        time.sleep(self.virtual_device_delay)

        # Step 4: Send Shift+Insert
        self._send_shift_insert()

        log.info("paste_operation_completed")
