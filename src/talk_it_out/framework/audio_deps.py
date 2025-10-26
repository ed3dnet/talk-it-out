# pattern: Functional Core
# Pure functions for audio dependency detection

from ctypes.util import find_library
from typing import Optional
import platform


def check_portaudio() -> tuple[bool, Optional[str]]:
    """Check if PortAudio library is available.

    Returns:
        (True, None) if available
        (False, error_message) if not available
    """
    if find_library('portaudio') is None:
        cmd = get_portaudio_install_command()
        error = f"PortAudio library not found. Install with: {cmd}"
        return False, error
    return True, None


def get_portaudio_install_command() -> str:
    """Get platform-specific PortAudio installation command.

    Returns:
        Installation command string for current platform
    """
    try:
        # Python 3.10+ has freedesktop_os_release()
        os_info = platform.freedesktop_os_release()
        os_id = os_info.get('ID', '').lower()

        if os_id in ('fedora', 'rhel', 'centos'):
            return "sudo dnf install portaudio-devel"
        elif os_id in ('ubuntu', 'debian'):
            return "sudo apt-get install portaudio19-dev"
        elif os_id in ('arch', 'manjaro'):
            return "sudo pacman -S portaudio"
    except (AttributeError, OSError):
        # Fall back if freedesktop_os_release not available or fails
        pass

    # Generic fallback
    return "sudo <package-manager> install portaudio-devel (or portaudio19-dev)"
