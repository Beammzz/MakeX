"""
mbuild.power_expand_board - Power Expansion Board Module
========================================================

Controls DC motors, solenoid valves, and brushless motors
through the power expansion board connected to MakeX NovaPi.

Usage::

    import novapi
    from mbuild import power_expand_board

    power_expand_board.set_power("CH1", 80)    # DC motor at 80% power
    power_expand_board.set_power("BL1", 50)    # Brushless motor
    power_expand_board.set_power("CH5", 1)     # Solenoid ON
    power_expand_board.set_power("CH5", 0)     # Solenoid OFF
"""


def set_power(ch, pwm):
    """Set the power for a DC motor, brushless motor, or solenoid valve.

    Args:
        ch (str): Channel selection:
            - DC motor / solenoid channels: ``"CH1"`` ~ ``"CH8"``
            - Brushless motor channels: ``"BL1"`` ~ ``"BL2"``
        pwm (int): Power value, range -100 ~ 100.
            - For DC motors: positive = forward, negative = reverse.
            - For solenoid valves: 0 = OFF, 1 = ON.
            - For brushless motors: speed control.
    """
    pass


def stop(ch):
    """Stop the motor on the specified channel.

    Args:
        ch (str): Channel to stop (``"CH1"`` ~ ``"CH8"``
            or ``"BL1"`` ~ ``"BL2"``).
    """
    pass


def stop_all():
    """Stop all motors and solenoids on the power expansion board."""
    pass
