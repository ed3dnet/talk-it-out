# pattern: Functional Core
# Pure abstract interface definition

from abc import ABC, abstractmethod


class OutputStrategy(ABC):
    """Base class for output strategies.

    Output strategies handle getting transcribed text into the target
    application after speech recognition completes.
    """

    @abstractmethod
    def paste_text(self, text: str) -> None:
        """Paste text into current application.

        Args:
            text: Transcribed text to paste

        Raises:
            OutputError: If paste operation fails
        """
        pass

    @abstractmethod
    def verify_dependencies(self) -> None:
        """Check required tools/dependencies are available.

        Called once at application startup to fail fast if dependencies
        are missing.

        Raises:
            OutputError: If dependencies missing, with helpful install message
        """
        pass


class OutputError(Exception):
    """Raised when output operation fails.

    This includes:
    - Missing dependencies (tools not installed, daemon not running)
    - Runtime failures (clipboard timeout, keystroke injection failed)
    - Configuration errors (invalid strategy settings)
    """
    pass
