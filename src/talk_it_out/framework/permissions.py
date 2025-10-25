# pattern: Functional Core
# Pure functions for permission checking

import os
import grp


def get_user_groups() -> list[str]:
    """Get list of groups current user belongs to.

    Returns:
        List of group names
    """
    groups = os.getgroups()
    return [grp.getgrgid(gid).gr_name for gid in groups]


def check_input_group() -> tuple[bool, str]:
    """Check if user is in 'input' group.

    python-evdev requires the user to be in the 'input' group
    to access /dev/input/eventX devices for keyboard monitoring.

    Returns:
        Tuple of (success, error_message)
        - success: True if in input group, False otherwise
        - error_message: Empty string if success, instructions if failure
    """
    groups = get_user_groups()

    if "input" not in groups:
        error_msg = (
            "User is not in 'input' group. python-evdev requires this for keyboard access.\n"
            "Run: sudo usermod -a -G input $USER\n"
            "Then log out and log back in."
        )
        return (False, error_msg)

    return (True, "")
