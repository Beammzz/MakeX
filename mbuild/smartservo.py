"""
mbuild.smartservo - Smart Servo Module
=======================================

Controls smart servo motors connected to MakeX NovaPi via mBuild ports.

Usage::

    import novapi
    from mbuild.smartservo import smartservo_class

    servo1 = smartservo_class("M1", "INDEX1")
    servo1.move_to(360, 20)
"""


class smartservo_class:
    """Smart servo controller for MakeX NovaPi.

    Args:
        port (str): The mBuild port the servo is connected to.
            Valid values: ``"M1"``, ``"M2"``, ``"M3"``, ``"M4"``,
            ``"M5"``, ``"M6"``.
        index (str): The index of the servo in the daisy-chain.
            Valid values: ``"INDEX1"``, ``"INDEX2"``, ``"INDEX3"``,
            ``"INDEX4"``.

    Example::

        import novapi
        from mbuild.smartservo import smartservo_class

        servo = smartservo_class("M1", "INDEX1")
        servo.set_zero()
        servo.move_to(90, 20)
    """

    def __init__(self, port, index):
        """Initialize a smart servo instance.

        Args:
            port (str): Servo port (``"M1"`` ~ ``"M6"``).
            index (str): Servo index in chain (``"INDEX1"`` ~ ``"INDEX4"``).
        """
        self._port = port
        self._index = index

    def set_zero(self):
        """Set the current position as the zero point."""
        pass

    def move_to(self, position, speed):
        """Move to an absolute angle at a specified speed.

        Args:
            position (int): Target angle in degrees.
                Range: -2147483648 ~ 2147483647.
            speed (int): Speed in RPM, range 1 ~ 50.
        """
        pass

    def move(self, position, speed):
        """Move by a relative angle at a specified speed.

        Args:
            position (int): Relative angle in degrees.
                Range: -2147483648 ~ 2147483647.
            speed (int): Speed in RPM, range 1 ~ 50.
        """
        pass

    def set_power(self, pwm):
        """Set the servo power with open-loop control.

        Args:
            pwm (int): Power value, range -100 ~ 100.
                Positive = forward, negative = reverse.
        """
        pass

    def get_value(self, type):
        """Get servo data.

        Args:
            type (str): The data type to retrieve:
                - ``"current"``     : Current in Amps.
                - ``"voltage"``     : Voltage in Volts.
                - ``"speed"``       : Speed in RPM.
                - ``"angle"``       : Position angle in degrees.
                - ``"temperature"`` : Temperature in °C.

        Returns:
            float: The requested servo data value.
        """
        return 0.0

    def stop(self):
        """Stop the servo immediately."""
        pass
