"""
mbuild.encoder_motor - Encoder Motor Module
============================================

Controls 180 encoder motors and 36 stacked brushless motors
connected to MakeX NovaPi via mBuild ports.

Usage::

    import novapi
    from mbuild.encoder_motor import encoder_motor_class

    motor1 = encoder_motor_class("M1", "INDEX1")
    motor1.set_power(50)
"""


class encoder_motor_class:
    """Encoder motor controller for MakeX NovaPi.

    Args:
        port (str): The mBuild port the motor is connected to.
            Valid values: ``"M1"``, ``"M2"``, ``"M3"``, ``"M4"``,
            ``"M5"``, ``"M6"``.
        index (str): The index of the motor in the daisy-chain.
            Valid values: ``"INDEX1"``, ``"INDEX2"``, ``"INDEX3"``,
            ``"INDEX4"``.

    Example::

        import novapi
        from mbuild.encoder_motor import encoder_motor_class

        motor = encoder_motor_class("M1", "INDEX1")
        motor.set_speed(100)
    """

    def __init__(self, port, index):
        """Initialize an encoder motor instance.

        Args:
            port (str): Motor port (``"M1"`` ~ ``"M6"``).
            index (str): Motor index in chain (``"INDEX1"`` ~ ``"INDEX4"``).
        """
        self._port = port
        self._index = index

    def move_to(self, position, speed):
        """Move to an absolute angle at a specified speed (closed-loop).

        Args:
            position (int): Target angle in degrees.
                Range: -2147483648 ~ 2147483647.
            speed (int): Speed in RPM. No hard limit — motor runs at
                max capability.
        """
        pass

    def move(self, position, speed):
        """Move by a relative angle at a specified speed (closed-loop).

        Args:
            position (int): Relative angle in degrees.
                Range: -2147483648 ~ 2147483647.
            speed (int): Speed in RPM. No hard limit.
        """
        pass

    def set_speed(self, speed):
        """Set the target speed with closed-loop control.

        Args:
            speed (int): Target speed in RPM. No hard limit —
                motor runs at max capability.
        """
        pass

    def set_power(self, pwm):
        """Set the motor power with open-loop control.

        Args:
            pwm (int): Power value, range -100 ~ 100.
                Positive = forward, negative = reverse.
        """
        pass

    def get_value(self, type):
        """Get motor data.

        Args:
            type (str): The data type to retrieve:
                - ``"angle"`` : Current position angle in degrees.
                - ``"speed"`` : Current speed in RPM.

        Returns:
            float: The requested motor data value.
        """
        return 0.0

    def stop(self):
        """Stop the motor immediately."""
        pass

    def set_zero(self):
        """Set the current position as the zero point."""
        pass
