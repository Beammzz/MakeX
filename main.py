import time
from mbuild import (
    gamepad,
    power_expand_board,
    power_manage_module,
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

# Mecanum Wheel Control
class Wheel:
    def __init__(self):
        self.upper_left = encoder_motor_class("M1", "INDEX1")
        self.lower_left = encoder_motor_class("M2", "INDEX1")
        self.upper_right = encoder_motor_class("M3", "INDEX1")
        self.lower_right = encoder_motor_class("M4", "INDEX1")
        
        # Holomix Tuning Parameters
        # TODO: Tune the parameters for Holomix Function.
        
    def set_power(self, ul, ll, ur, lr):
        self.upper_left.set_power(ul)
        self.lower_left.set_power(ll)
        self.upper_right.set_power(ur)
        self.lower_right.set_power(lr)
    
    def stop(self):
        self.set_power(0, 0, 0, 0)
        
    def holomix(self, lx, ly, rx):
        # TODO: Implement Holomix Function.
        
        pass
    
# Consist of Ball Conveyor and Block Conveyor
class conveyor:
    def __init__(self):
        # DC Motors
        self.block_a = "DC1"
        self.block_b = "DC3"
        
        self.convey_upper = "DC4"
        self.convey_lower = "DC6"
        
    def block_convey(self):
        pass
    
    
    
# Consist of Brushless Motor and Shooter Servo
class shooter:
    def __init__(self):
        self.is_shooter_toggled = False
    
    def set_shooter_angle(self, angle):
        smartservo_class("M5").move_to(angle, 50)
        
    def toogle_shooter(self):
        if not self.is_shooter_toggled:
            power_expand_board.set_power("BL1", 17)
            power_expand_board.set_power("BL2", 17)
            self.is_shooter_toggled = False
        else:
            power_expand_board.set_power("BL1", 0)
            power_expand_board.set_power("BL2", 0)
            self.is_shooter_toggled = True
        

class Guzzchan:
    def __init__(self):
        self.wheel = Wheel()
    
    def control(self):
        lx = gamepad.get_joystick("Lx")
        ly = gamepad.get_joystick("Ly")
        rx = gamepad.get_joystick("Rx")
        # Robot Movement Control (Wheel)
        # Pass to Holomix Function
        if (lx > 30 or ly > 30 or rx > 30 or lx < -30 or ly < -30 or rx < -30):
            self.wheel.holomix(lx, ly, rx)
        else:
            self.wheel.stop()
        pass
    
    def auto(self, side):
        # TODO: Implement Auto Mode with side.
        pass
    
# Init
shooter().set_shooter_angle(0)

# Main Loop
while True:
    if power_manage_module.is_auto_mode():
        print("Competition is in auto mode")
        Guzzchan().auto("Left")
    else:
        Guzzchan().control()
        
    time.sleep(0.05)