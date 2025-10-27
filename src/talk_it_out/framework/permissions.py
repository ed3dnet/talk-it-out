# pattern: Functional Core
# Pure functions for permission checking

import os
import grp
from pathlib import Path


def get_user_groups() -> list[str]:
    """Get list of groups current user belongs to.

    Returns:
        List of group names
    """
    groups = os.getgroups()
    return [grp.getgrgid(gid).gr_name for gid in groups]


def get_input_device_group() -> str | None:
    """Get the group that owns /dev/input devices.

    Returns:
        Group name if found, None if no devices exist
    """
    input_dir = Path("/dev/input")
    if not input_dir.exists():
        return None

    # Find first event device
    for device in input_dir.glob("event*"):
        try:
            stat = device.stat()
            return grp.getgrgid(stat.st_gid).gr_name
        except (OSError, KeyError):
            continue

    return None


def check_input_group() -> tuple[bool, str]:
    """Check if user is in the required group for /dev/input access.

    python-evdev requires the user to be in the group that owns /dev/input/eventX
    devices for keyboard monitoring. This is typically 'input' but may vary by system.

    Returns:
        Tuple of (success, error_message)
        - success: True if in required group, False otherwise
        - error_message: Empty string if success, instructions if failure
    """
    # Determine which group owns /dev/input devices
    required_group = get_input_device_group()

    if required_group is None:
        error_msg = (
            "Cannot determine input device group. /dev/input devices not found.\n"
            "This may indicate a system configuration issue."
        )
        return (False, error_msg)

    # Check if user is in that group
    user_groups = get_user_groups()

    if required_group not in user_groups:
        error_msg = (
            f"User is not in '{required_group}' group. python-evdev requires this for keyboard access.\n"
            f"Run: sudo usermod -a -G {required_group} $USER\n"
            "Then log out and log back in."
        )
        return (False, error_msg)

    return (True, "")
