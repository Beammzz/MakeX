"""
mbuild.gamepad - Wireless Gamepad Controller Module
====================================================

Reads input from the MakeX wireless gamepad connected to NovaPi.

Usage::

    import novapi
    from mbuild import gamepad

    lx = gamepad.get_joystick("Lx")
    if gamepad.is_key_pressed("R1"):
        print("R1 pressed!")
"""


def get_joystick(joystick_pos):
    """Get the joystick axis value.

    Range: -100 ~ 100.
    Left/Up is positive, Right/Down is negative.

    Args:
        joystick_pos (str): The joystick axis to read:
            - ``"Lx"`` : Left joystick, X-axis (horizontal)
            - ``"Ly"`` : Left joystick, Y-axis (vertical)
            - ``"Rx"`` : Right joystick, X-axis (horizontal)
            - ``"Ry"`` : Right joystick, Y-axis (vertical)

    Returns:
        int: Joystick value, range -100 ~ 100.
    """
    return 0


def is_key_pressed(button):
    """Check if a gamepad button is currently pressed.

    Args:
        button (str): Button name. Valid values:
            - ``"N1"``  : Button N1
            - ``"N2"``  : Button N2
            - ``"N3"``  : Button N3
            - ``"N4"``  : Button N4
            - ``"L1"``  : Left shoulder L1
            - ``"L2"``  : Left shoulder L2
            - ``"R1"``  : Right shoulder R1
            - ``"R2"``  : Right shoulder R2
            - ``"Up"``  : D-pad Up
            - ``"Down"``  : D-pad Down
            - ``"Left"``  : D-pad Left
            - ``"Right"`` : D-pad Right

    Returns:
        bool: True if the button is pressed, False otherwise.
    """
    return False


# Alias: some firmware versions / docs use this name
s_key_pressed = is_key_pressed
