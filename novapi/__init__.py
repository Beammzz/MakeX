"""
novapi - MakeX NovaPi MicroPython Stub Module
==============================================

Stub module for local development with autocompletion.
This module mirrors the real novapi module on the NovaPi device.

Usage in MBlock (Upload Mode):
    import novapi

When you copy your main.py to MBlock editor, remove/ignore this stub folder.
The real novapi module is built into the NovaPi firmware.
"""


# ---------------------------------------------------------------------------
# Timer functions
# ---------------------------------------------------------------------------

def timer():
    """Get the system timer value in seconds (float).

    Returns:
        float: Elapsed time in seconds since last reset.
    """
    return 0.0


def reset_timer():
    """Reset the system timer to zero."""
    pass


# ---------------------------------------------------------------------------
# Onboard Gyro Sensor (6-axis IMU)
# ---------------------------------------------------------------------------

def get_pitch():
    """Get the pitch angle (rotation around X-axis).

    Returns:
        float: Pitch angle in degrees, range -180 ~ 180.
    """
    return 0.0


def get_roll():
    """Get the roll angle (rotation around Y-axis).

    Returns:
        float: Roll angle in degrees, range -180 ~ 180.
    """
    return 0.0


def get_yaw():
    """Get the yaw angle (rotation around Z-axis).

    Note: The onboard gyroscope is a 6-axis sensor without an electronic
    compass, so the yaw value is derived from Z-axis angular velocity
    integration. It has accumulated drift error over time.

    Returns:
        float: Yaw angle in degrees, range -32768 ~ 32767.
    """
    return 0.0


def get_gyro_rotation(axis):
    """Get the angular velocity of the specified axis.

    Args:
        axis (str): The axis to query. One of:
            - ``"x"`` : X-axis angular velocity
            - ``"y"`` : Y-axis angular velocity
            - ``"z"`` : Z-axis angular velocity

    Returns:
        float: Angular velocity in degrees/second.
    """
    return 0.0


def get_acceleration(axis):
    """Get the acceleration value of the specified axis.

    Args:
        axis (str): The axis to query. One of:
            - ``"x"`` : X-axis acceleration
            - ``"y"`` : Y-axis acceleration
            - ``"z"`` : Z-axis acceleration

    Returns:
        float: Acceleration value in m/s^2.
    """
    return 0.0


def is_shaked():
    """Check if the NovaPi board is being shaken.

    Returns:
        bool: True if the board is being shaken, False otherwise.
    """
    return False


def reset_yaw():
    """Reset the yaw angle to zero."""
    pass


def is_tilted_left():
    """Check if the board is tilted to the left.

    Returns:
        bool: True if tilted left, False otherwise.
    """
    return False


def is_tilted_right():
    """Check if the board is tilted to the right.

    Returns:
        bool: True if tilted right, False otherwise.
    """
    return False


def is_tilted_forward():
    """Check if the board is tilted forward.

    Returns:
        bool: True if tilted forward, False otherwise.
    """
    return False


def is_tilted_backward():
    """Check if the board is tilted backward.

    Returns:
        bool: True if tilted backward, False otherwise.
    """
    return False


def is_face_up():
    """Check if the board is face up.

    Returns:
        bool: True if face up, False otherwise.
    """
    return False


def is_face_down():
    """Check if the board is face down.

    Returns:
        bool: True if face down, False otherwise.
    """
    return False


# ---------------------------------------------------------------------------
# Onboard LED functions
# ---------------------------------------------------------------------------

def led_show(index, r, g, b):
    """Set the color of the onboard LED(s).

    Args:
        index (int): LED index (1-based), or 0 to set all LEDs.
        r (int): Red value, range 0 ~ 255.
        g (int): Green value, range 0 ~ 255.
        b (int): Blue value, range 0 ~ 255.
    """
    pass


def set_led(r, g, b, index=0):
    """Set the color of the onboard LED(s).

    Args:
        r (int): Red value, range 0 ~ 255.
        g (int): Green value, range 0 ~ 255.
        b (int): Blue value, range 0 ~ 255.
        index (int): LED index (1-based), or 0 for all LEDs. Default is 0.
    """
    pass


# ---------------------------------------------------------------------------
# Onboard Buzzer functions
# ---------------------------------------------------------------------------

def play_note(note, beat=1):
    """Play a musical note on the onboard buzzer.

    Args:
        note (str or int): Note name (e.g. ``"C4"``, ``"D5"``) or
            MIDI note number.
        beat (float): Duration in beats. Default is 1.
    """
    pass


def play_tone(frequency, duration=1):
    """Play a tone at a specific frequency.

    Args:
        frequency (int): Frequency in Hz.
        duration (float): Duration in seconds. Default is 1.
    """
    pass


def stop_buzzer():
    """Stop the buzzer immediately."""
    pass


# ---------------------------------------------------------------------------
# Button
# ---------------------------------------------------------------------------

def is_button_pressed():
    """Check if the onboard button is pressed.

    Returns:
        bool: True if pressed, False otherwise.
    """
    return False


# ---------------------------------------------------------------------------
# Mesh / Network Communication
# ---------------------------------------------------------------------------

def mesh_send(message):
    """Send a message through the mesh network.

    Args:
        message (str): The message to broadcast.
    """
    pass


def mesh_read():
    """Read a message from the mesh network.

    Returns:
        str: The received message, or empty string if none.
    """
    return ""
