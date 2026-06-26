import time

import novapi
from mbuild import (
    dual_rgb_sensor,
    gamepad,
    power_expand_board,
    power_manage_module,
    ranging_sensor,
)
from mbuild.encoder_motor import encoder_motor_class
from mbuild.smartservo import smartservo_class


class Guzzchan:
    def __init__(self):
        self.wheel_upper_left = encoder_motor_class("M1", "INDEX1")
        self.wheel_lower_left = encoder_motor_class("M2", "INDEX1")
        self.wheel_upper_right = encoder_motor_class("M3", "INDEX1")
        self.wheel_lower_right = encoder_motor_class("M4", "INDEX1")

        self.wheel_power = 50

    # Useful Functions
    # Upper left, Lower left, Upper right, Lower right
    def set_wheel_power(self, ul, ll, ur, lr):
        self.wheel_upper_left.set_power(ul)
        self.wheel_lower_left.set_power(ll)
        self.wheel_upper_right.set_power(ur)
        self.wheel_lower_right.set_power(lr)

    # Auto Mode
    def auto(self, side):
        if side == "L":
            pass
        elif side == "R":
            pass

    # Main Control with Controller
    def manual(self):
        wheel_power = self.wheel_power
        # Control movement
        if gamepad.get_joystick("Ly") > 50:
            # Forward
            self.set_wheel_power(ul=wheel_power,  ll=wheel_power,  ur=-wheel_power, lr=-wheel_power)
        elif gamepad.get_joystick("Ly") < -50:
            # Backward
            self.set_wheel_power(ul=-wheel_power, ll=-wheel_power, ur=wheel_power,  lr=wheel_power)
        # เข้าหมดเลย
        elif gamepad.get_joystick("Lx") > 50:
            # Strafe right
            self.set_wheel_power(ul=-wheel_power,  ll=wheel_power, ur=wheel_power,  lr=-wheel_power)
        # ออกหมดเลย
        elif gamepad.get_joystick("Lx") < -50:
            # Strafe left
            self.set_wheel_power(ul=wheel_power, ll=-wheel_power,  ur=-wheel_power, lr=wheel_power)
        else:
            self.set_wheel_power(ul=0, ll=0, ur=0, lr=0)
            
        # Control rotation
        if gamepad.get_joystick("Rx") > 50:
            # Rotate right
            self.set_wheel_power(ul=-wheel_power,  ll=-wheel_power,  ur=-wheel_power,  lr=-wheel_power)
        elif gamepad.get_joystick("Rx") < -50:
            # Rotate left
            self.set_wheel_power(ul=wheel_power, ll=wheel_power, ur=wheel_power, lr=wheel_power)


robot = Guzzchan()
# --- Main loop ---
"""
                           .-') _    .-') _             ('-. .-.   ('-.         .-') _  
                          (  OO) )  (  OO) )           ( OO )  /  ( OO ).-.    ( OO ) ) 
  ,----.    ,--. ,--.   ,(_)----. ,(_)----.    .-----. ,--. ,--.  / . --. /,--./ ,--,'  
 '  .-./-') |  | |  |   |       | |       |   '  .--./ |  | |  |  | \-.  \ |   \ |  |\  
 |  |_( O- )|  | | .-') '--.   /  '--.   /    |  |('-. |   .|  |.-'-'  |  ||    \|  | ) 
 |  | .--, \|  |_|( OO )(_/   /   (_/   /    /_) |OO  )|       | \| |_.'  ||  .     |/  
(|  | '. (_/|  | | `-' / /   /___  /   /___  ||  |`-'| |  .-.  |  |  .-.  ||  |\    |   
 |  '--'  |('  '-'(_.-' |        ||        |(_'  '--'\ |  | |  |  |  | |  ||  | \   |   
  `------'   `-----'    `--------'`--------'   `-----' `--' `--'  `--' `--'`--'  `--'   
"""

while True:
    # Main Configurations
    auto_side = "L"  # or "R"

    # Check Automode
    if power_manage_module.is_auto_mode():
        # ===== AUTO MODE =====
        robot.auto(auto_side)
    else:
        print(robot.wheel_upper_left.get_power())
        print("-" * 20)
        # ===== MANUAL MODE =====
        robot.manual()

    time.sleep(0.05)
