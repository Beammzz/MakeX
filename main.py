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

print(r"""
                           .-') _    .-') _             ('-. .-.   ('-.         .-') _  
                          (  OO) )  (  OO) )           ( OO )  /  ( OO ).-.    ( OO ) ) 
  ,----.    ,--. ,--.   ,(_)----. ,(_)----.    .-----. ,--. ,--.  / . --. /,--./ ,--,'  
 '  .-./-') |  | |  |   |       | |       |   '  .--./ |  | |  |  | \-.  \ |   \ |  |\  
 |  |_( O- )|  | | .-') '--.   /  '--.   /    |  |('-. |   .|  |.-'-'  |  ||    \|  | ) 
 |  | .--, \|  |_|( OO )(_/   /   (_/   /    /_) |OO  )|       | \| |_.'  ||  .     |/  
(|  | '. (_/|  | | `-' / /   /___  /   /___  ||  |`-'| |  .-.  |  |  .-.  ||  |\    |   
 |  '--'  |('  '-'(_.-' |        ||        |(_'  '--'\ |  | |  |  |  | |  ||  | \   |   
  `------'   `-----'    `--------'`--------'   `-----' `--' `--'  `--' `--'`--'  `--'   
""")

class Guzzchan:
    def __init__(self):
        self.wheel_upper_left = encoder_motor_class("M1", "INDEX1")
        self.wheel_lower_left = encoder_motor_class("M2", "INDEX1")
        self.wheel_upper_right = encoder_motor_class("M3", "INDEX1")
        self.wheel_lower_right = encoder_motor_class("M4", "INDEX1")
        self.shooter_servo = smartservo_class("M5", "INDEX1")

        self.wheel_power = 50
        
        # Init Value
        self.runauto = False

    # Useful Functions
    # Upper left, Lower left, Upper right, Lower right
    def set_wheel_power(self, ul, ll, ur, lr):
        self.wheel_upper_left.set_power(ul)
        self.wheel_lower_left.set_power(ll)
        self.wheel_upper_right.set_power(ur)
        self.wheel_lower_right.set_power(lr)

    def move_forward(self, power):
        self.set_wheel_power(ul=power,  ll=power,  ur=-power, lr=-power)
        
    def move_backward(self, power):
        self.set_wheel_power(ul=-power, ll=-power, ur=power,  lr=power)
        
    def move_sideway_right(self, power):
        self.set_wheel_power(ul=-power, ll=power,  ur=-power, lr=power)
        
    def move_sideway_left(self, power):
        self.set_wheel_power(ul=power, ll=-power,  ur=power,  lr=-power)
        
    def rotate_right(self, power):
        self.set_wheel_power(ul=-power, ll=-power, ur=-power, lr=-power)
    
    def rotate_left(self, power):
        self.set_wheel_power(ul=power, ll=power, ur=power, lr=power)
        
    def stop(self):
        self.wheel_upper_right.stop()
        self.wheel_upper_left.stop()
        self.wheel_lower_right.stop()
        self.wheel_lower_left.stop()

    # Auto Mode
    def auto(self, side):
        if not self.runauto:
            if side == "L":
                self.wheel_upper_left.move(5000, 100)
            else:
                self.wheel_upper_right.move(500, 100)
            self.runauto = True    

    # Main Control with Controller
    def manual(self):
        wheel_power = self.wheel_power
        # Control movement
        if gamepad.get_joystick("Ly") > 50:
            self.move_forward(wheel_power)
        elif gamepad.get_joystick("Ly") < -50:
            self.move_backward(wheel_power)
        elif gamepad.get_joystick("Lx") > 50:
            self.move_sideway_right(wheel_power)
        elif gamepad.get_joystick("Lx") < -50:
            self.move_sideway_left(wheel_power)
        # Control rotation
        elif gamepad.get_joystick("Rx") > 50:
            self.rotate_right(wheel_power)
        elif gamepad.get_joystick("Rx") < -50:
            self.rotate_left(wheel_power)
        else:
            self.stop()
            
        # Control Buttons
        # Up
        if gamepad.is_key_pressed("N2"):
            self.shooter_servo.move_to(-30, 300)
        # Zero
        if gamepad.is_key_pressed("≡"):
            self.shooter_servo.move_to(0, 300)
        # Down
        if gamepad.is_key_pressed("N3"):
            self.shooter_servo.move_to(30, 300)

robot = Guzzchan()
debug_auto = False

robot.shooter_servo.move_to(0, 300)

# --- Main loop ---
while True:
    # Main Configurations
    auto_side = "L"  # or "R"

    # Check Automode
    if power_manage_module.is_auto_mode() or debug_auto:
        print(robot.runauto)
        # ===== AUTO MODE =====
        robot.auto(auto_side)
    else:
        # ===== MANUAL MODE =====
        robot.manual()
        print("yaw:", novapi.get_yaw())
        print("-"*20)
    time.sleep(0.05)
