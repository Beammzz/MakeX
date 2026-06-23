"""
mbuild.power_manage_module - Power Management Module
=====================================================

Handles competition mode detection and power management
for MakeX NovaPi.

Usage::

    import novapi
    from mbuild import power_manage_module

    if power_manage_module.is_auto_mode():
        print("Autonomous mode!")
    else:
        print("Manual mode!")
"""


def is_auto_mode():
    """Check if the competition is in autonomous mode.

    Returns:
        bool: True if the competition is in autonomous mode,
            False if in manual (driver-controlled) mode.
    """
    return False


def get_timer():
    """Get the competition timer value.

    Returns:
        float: Competition time in seconds.
    """
    return 0.0


def is_connected():
    """Check if the power management module is connected.

    Returns:
        bool: True if connected, False otherwise.
    """
    return False
