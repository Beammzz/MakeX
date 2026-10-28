import time
from mbuild import (
    gamepad,
    power_expand_board,
    power_manage_module,
)
from mbuild.smartservo import smartservo_class
from auto import auto_mode
from wheel import Wheel
from conveyor import Conveyor
from shooter import Shooter

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

# หุ่นยบต์
BOARD_SLEEP_TIME = 0.05
            
class Guzzchan:
    def __init__(self) -> None:
        self.wheel = Wheel()
        self.conveyor = Conveyor()
        self.shooter = Shooter()
        self._prev_keys = {}

    def _pressed(self, key):
            now = gamepad.is_key_pressed(key)
            fired = now and not self._prev_keys.get(key, False)
            self._prev_keys[key] = now
            return fired
    
    def control(self):
        lx = gamepad.get_joystick("Lx")
        ly = gamepad.get_joystick("Ly")
        rx = gamepad.get_joystick("Rx")

        # Wheel controller
        self.wheel.holomix(lx, ly, rx)

        if self._pressed("N1"):
            self.conveyor.toggle_ball_conveyor()

        if self._pressed("+"):
            self.shooter.toggle_shooter()  
            
        if self._pressed("Up"):
            self.conveyor.toggle_ball_hand()


        if gamepad.is_key_pressed("L2") or gamepad.is_key_pressed("R2"):
            if self.conveyor.ball_conveyor_toggle:
                self.conveyor.toggle_ball_conveyor()
        if gamepad.is_key_pressed("L2"):
            self.conveyor.shooter_convey()
        elif gamepad.is_key_pressed("R2"):
            self.conveyor.shooter_convey(reverse=True)
        elif not self.conveyor.ball_conveyor_toggle:
            self.conveyor.shooter_convey_stop()
            

        if gamepad.is_key_pressed("L1"):
            self.conveyor.block_convey()
        elif gamepad.is_key_pressed("R1"):
            self.conveyor.block_convey(reverse=True)
        else:
            self.conveyor.block_convey_stop()
        
        if gamepad.is_key_pressed("N2"):
            self.conveyor.lift_cone()
        elif gamepad.is_key_pressed("N3"):
            self.conveyor.lift_cone(reverse=True)
        else:
            self.conveyor.stop_lift()
            
        if gamepad.is_key_pressed("Left"):
            self.conveyor.hand_hold()
            
        elif gamepad.is_key_pressed("Right"):
            self.conveyor.hand_hold(reverse=True)
        else:
            self.conveyor.stop_hand()
            
    def auto(self):
        auto_mode(self, "L") # "L" or "R"


robot = Guzzchan()
            
while True:
    if power_manage_module.is_auto_mode():
        robot.auto()
        while power_manage_module.is_auto_mode():
            time.sleep(BOARD_SLEEP_TIME)
            
    else:
        robot.control()
    time.sleep(BOARD_SLEEP_TIME)
        