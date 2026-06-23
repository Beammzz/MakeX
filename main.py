import novapi
import time

# --- Import the modules you need ---
from mbuild.encoder_motor import encoder_motor_class
from mbuild.smartservo import smartservo_class
from mbuild import gamepad
from mbuild import dual_rgb_sensor
from mbuild import ranging_sensor
from mbuild import power_manage_module
from mbuild import power_expand_board


class Kudchan:
    def __init__(self):
        # Initialize your robot components here
        self.encoder = encoder_motor_class("M6", "INDEX1")

    def autonomous(self, side):
        # Autonomous code goes here
        pass

    def teleop(self):
        # Teleop code goes here
        if (gamepad.is_key_pressed("L1")):
            self.encoder.set_power(20)
        pass

robot = Kudchan()
# --- Main loop ---
while True:
    # Check competition mode
    if power_manage_module.is_auto_mode():
        # ===== AUTONOMOUS MODE =====
        robot.autonomous(side="L")  # or side="R"
        pass

    else:
        # ===== TELEOP MODE =====
        robot.teleop()
        pass

    # Small delay to prevent CPU overload
    time.sleep(0.05)
