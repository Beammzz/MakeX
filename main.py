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
        self.wheel_left_up = encoder_motor_class("M1", "INDEX1")
        self.wheel_left_bottom = encoder_motor_class("M2", "INDEX1")
        self.wheel_right_up = encoder_motor_class("M3", "INDEX1")
        self.wheel_right_bottom = encoder_motor_class("M4", "INDEX1")

        self.wheel_power = 50

    # Useful Functions
    def set_wheel_power(self, left_up, left_bottom, right_up, right_bottom):
        self.wheel_left_up.set_power(left_up)
        self.wheel_left_bottom.set_power(left_bottom)
        self.wheel_right_up.set_power(right_up)
        self.wheel_right_bottom.set_power(right_bottom)
        pass


    # Auto Mode
    def auto(self, side):
        if side == "L":
            pass
        elif side == "R":
            pass
        pass

    # Main Control with Controller
    def manual(self):
        wheel_power = self.wheel_power
        if gamepad.get_joystick("Ly") > 50:
            self.set_wheel_power(wheel_power, wheel_power, -wheel_power, -wheel_power)
        elif gamepad.get_joystick("Ly") < -50:
            self.set_wheel_power(-wheel_power, -wheel_power, wheel_power, wheel_power)
        elif gamepad.get_joystick("Lx") > 50:
            self.set_wheel_power(wheel_power, -wheel_power, wheel_power, -wheel_power)
        elif gamepad.get_joystick("Lx") < -50:
            self.set_wheel_power(-wheel_power, wheel_power, -wheel_power, wheel_power)
        else:
            self.set_wheel_power(0, 0, 0, 0)
        pass



robot = Kudchan()
# --- Main loop ---
"""
.-. .-')              _ .-') _              ('-. .-.   ('-.         .-') _  
\  ( OO )            ( (  OO) )            ( OO )  /  ( OO ).-.    ( OO ) ) 
,--. ,--. ,--. ,--.   \     .'_    .-----. ,--. ,--.  / . --. /,--./ ,--,'  
|  .'   / |  | |  |   ,`'--..._)  '  .--./ |  | |  |  | \-.  \ |   \ |  |\  
|      /, |  | | .-') |  |  \  '  |  |('-. |   .|  |.-'-'  |  ||    \|  | ) 
|     ' _)|  |_|( OO )|  |   ' | /_) |OO  )|       | \| |_.'  ||  .     |/  
|  .   \  |  | | `-' /|  |   / : ||  |`-'| |  .-.  |  |  .-.  ||  |\    |   
|  |\   \('  '-'(_.-' |  '--'  /(_'  '--'\ |  | |  |  |  | |  ||  | \   |   
`--' '--'  `-----'    `-------'    `-----' `--' `--'  `--' `--'`--'  `--'   
"""

while True:
    # Main Configurations
    auto_side = "L"  # or "R"


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
