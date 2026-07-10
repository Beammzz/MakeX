import time

import novapi
from mbuild import (
    gamepad,
    power_manage_module,
)
from mbuild.encoder_motor import encoder_motor_class
import shooter

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
        # Init Value
        self.runauto = False

    # Useful Functions
    # Upper left, Lower left, Upper right, Lower right
    
        
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

        if gamepad.is_key_pressed("+"):
            shooter.toggle()
            

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
    time.sleep(0.02)
