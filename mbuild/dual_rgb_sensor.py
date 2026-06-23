"""
mbuild.dual_rgb_sensor - Dual RGB Sensor Module
================================================

Dual RGB line-following sensor for MakeX NovaPi.
Used for line tracking and color detection.

Usage::

    import novapi
    from mbuild import dual_rgb_sensor

    intensity = dual_rgb_sensor.get_intensity("RGB1")
    on_line = dual_rgb_sensor.is_state("00")
"""


def get_intensity(ch, index=1):
    """Get the light intensity value of a sensor probe.

    Args:
        ch (str): Channel selection:
            - ``"RGB1"`` : Probe 1 (left)
            - ``"RGB2"`` : Probe 2 (right)
        index (int): Module index if multiple sensors are daisy-chained.
            Default is 1.

    Returns:
        int: Light intensity value, range 0 ~ 255.
    """
    return 0


def is_state(state, index=1):
    """Check the line-following state of both RGB probes.

    Args:
        state (str): The expected state to check:
            - ``"00"`` : RGB1 on line, RGB2 on line
            - ``"01"`` : RGB1 on line, RGB2 on track
            - ``"10"`` : RGB1 on track, RGB2 on line
            - ``"11"`` : RGB1 on track, RGB2 on track
        index (int): Module index if multiple sensors are daisy-chained.
            Default is 1.

    Returns:
        bool: True if the current state matches the given state,
            False otherwise.
    """
    return False


def get_offset_track_value(index=1):
    """Get the offset value from the track center during line following.

    Args:
        index (int): Module index if multiple sensors are daisy-chained.
            Default is 1.

    Returns:
        int: Offset value, range -100 ~ 100.
            Negative = left of center, positive = right of center.
    """
    return 0


def is_color(ch, color, index=1):
    """Check if a specific color is detected by the given channel.

    Args:
        ch (str): Channel selection:
            - ``"RGB1"`` : Probe 1 (left)
            - ``"RGB2"`` : Probe 2 (right)
        color (str): Color to detect. Common values:
            - ``"red"``
            - ``"green"``
            - ``"blue"``
            - ``"yellow"``
            - ``"cyan"``
            - ``"purple"``
            - ``"white"``
            - ``"black"``
        index (int): Module index if multiple sensors are daisy-chained.
            Default is 1.

    Returns:
        bool: True if the detected color matches, False otherwise.
    """
    return False


def get_color(ch, index=1):
    """Get the detected color name from the given channel.

    Args:
        ch (str): Channel selection:
            - ``"RGB1"`` : Probe 1 (left)
            - ``"RGB2"`` : Probe 2 (right)
        index (int): Module index if multiple sensors are daisy-chained.
            Default is 1.

    Returns:
        str: Detected color name (e.g. ``"red"``, ``"blue"``,
            ``"white"``, ``"black"``).
    """
    return ""


def get_red(ch, index=1):
    """Get the red channel value from the given sensor probe.

    Args:
        ch (str): Channel selection (``"RGB1"`` or ``"RGB2"``).
        index (int): Module index. Default is 1.

    Returns:
        int: Red channel intensity, range 0 ~ 255.
    """
    return 0


def get_green(ch, index=1):
    """Get the green channel value from the given sensor probe.

    Args:
        ch (str): Channel selection (``"RGB1"`` or ``"RGB2"``).
        index (int): Module index. Default is 1.

    Returns:
        int: Green channel intensity, range 0 ~ 255.
    """
    return 0


def get_blue(ch, index=1):
    """Get the blue channel value from the given sensor probe.

    Args:
        ch (str): Channel selection (``"RGB1"`` or ``"RGB2"``).
        index (int): Module index. Default is 1.

    Returns:
        int: Blue channel intensity, range 0 ~ 255.
    """
    return 0


def set_led_color(ch, r, g, b, index=1):
    """Set the LED color on the dual RGB sensor module.

    Args:
        ch (str): Channel selection (``"RGB1"`` or ``"RGB2"``).
        r (int): Red value, range 0 ~ 255.
        g (int): Green value, range 0 ~ 255.
        b (int): Blue value, range 0 ~ 255.
        index (int): Module index. Default is 1.
    """
    pass
