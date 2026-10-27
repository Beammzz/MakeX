import time
from mbuild import (
    gamepad,
    power_expand_board,
    power_manage_module,
)
from mbuild.encoder_motor import encoder_motor_class
from mbuild.smartservo import smartservo_class
from mbuild.smart_camera import smart_camera_class

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

# จูนตรงนี้น่ะคร้าบ
UPPER_LEFT = "M1"
LOWER_LEFT = "M2"
UPPER_RIGHT = "M3"
LOWER_RIGHT = "M4"

REVERSE = [1, 1, -1, -1]

# 

class Wheel:
    def __init__(self) -> None:
        self.motors = [
            encoder_motor_class(UPPER_LEFT, 'INDEX1'),
            encoder_motor_class(LOWER_LEFT, 'INDEX1'),
            encoder_motor_class(UPPER_RIGHT, 'INDEX1'),
            encoder_motor_class(LOWER_RIGHT, 'INDEX1')
        ]
        
        self.slow_speed = 40
        self.normal_speed = 75
        
        
class Conveyer:
    pass

class Shooter:
    pass
            
class Guzzchan:
    def __init__(self) -> None:
        self.wheel = Wheel()
        
    def auto_mode(self):
        pass
    
    def control(self):
        lx = gamepad.get_joystick("Lx")
        ly = gamepad.get_joystick("Ly")
        rx = gamepad.get_joystick("Rx")

        

robot = Guzzchan()
            
while True:
    if power_manage_module.is_auto_mode():
        robot.auto_mode()
        while power_manage_module.is_auto_mode():
            time.sleep(0.1)
            
    else:
        robot.control()
    time.sleep(0.05)
        