import novapi
import time
from mbuild.encoder_motor import encoder_motor_class
from mbuild.smartservo import smartservo_class
from mbuild import gamepad
from mbuild import dual_rgb_sensor
from mbuild import ranging_sensor
from mbuild import power_manage_module
from mbuild import power_expand_board


class Kudchan:
    def __init__(self):
        self.encoder_upleft = encoder_motor_class("M1", "INDEX1")
        self.encoder_upright = encoder_motor_class("M2", "INDEX1")
        self.encoder_downleft = encoder_motor_class("M3", "INDEX1")
        self.encoder_downright = encoder_motor_class("M4", "INDEX1")

    def auto(self, side):
        if side == "L":
            pass
        elif side == "R":
            pass
        pass

    def manual(self):
        pass



robot = Kudchan()
# --- Main loop ---
while True:
    # Main Configurations
    auto_side: str = "L"  # or "R"


    # Check Automode
    if power_manage_module.is_auto_mode():
        # ===== AUTO MODE =====
        robot.auto(auto_side)
        pass

    else:
        # ===== MANUAL MODE =====
        robot.manual()
        pass

    time.sleep(0.05)
