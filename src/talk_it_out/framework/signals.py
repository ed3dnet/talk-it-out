# pattern: Functional Core
# Pure functions and data structures for cleanup management

import signal
import sys
from typing import Callable


class CleanupRegistry:
    """Registry for cleanup functions to run on shutdown.

    Why this exists: Allows components to register cleanup functions
    that will be executed when the application receives SIGINT/SIGTERM.
    Ensures graceful shutdown even if cleanup hangs.
    """

    def __init__(self):
        self.cleanup_fns: list[Callable] = []

    def register(self, fn: Callable) -> None:
        """Register a cleanup function.

        Args:
            fn: Callable with no arguments to run on shutdown
        """
        self.cleanup_fns.append(fn)

    def cleanup(self, timeout: float = 3.0) -> None:
        """Run all cleanup functions with default timeout.

        Convenience method for run_all() with default timeout.

        Args:
            timeout: Maximum seconds to wait for all cleanup (default 3.0)
        """
        self.run_all(timeout)

    def run_all(self, timeout: float) -> None:
        """Run all cleanup functions with timeout.

        If cleanup takes longer than timeout, force exit to prevent hanging.

        Args:
            timeout: Maximum seconds to wait for all cleanup
        """
        # Setup timeout alarm
        def timeout_handler(signum, frame):
            raise TimeoutError("Cleanup timeout exceeded")

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))

        try:
            for fn in self.cleanup_fns:
                fn()
        except TimeoutError:
            print("⚠️  Cleanup timeout exceeded, forcing exit", file=sys.stderr)
        finally:
            signal.alarm(0)  # Cancel alarm


def setup_signal_handlers(registry: CleanupRegistry, timeout: float = 3.0) -> None:
    """Install SIGINT/SIGTERM handlers for graceful shutdown.

    Why this exists: Ensures cleanup runs when user presses Ctrl-C or
    system sends termination signal.

    Args:
        registry: CleanupRegistry with registered cleanup functions
        timeout: Maximum seconds to wait for cleanup (default 3.0)
    """
    def handler(signum, frame):
        print("\n🛑 Shutting down...", file=sys.stderr)
        registry.run_all(timeout)

        # Exit with appropriate code
        # 130 = 128 + SIGINT (2) - standard Unix convention
        # 0 = clean shutdown for SIGTERM
        exit_code = 0 if signum == signal.SIGTERM else 130
        sys.exit(exit_code)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
