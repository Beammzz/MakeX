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

class Wheel:
    def __init__(self) -> None:
        self.upper_left = encoder_motor_class("M1", "INDEX1")
        self.lower_left = encoder_motor_class("M2", "INDEX1")
        self.upper_right = encoder_motor_class("M3", "INDEX1")
        self.lower_right = encoder_motor_class("M4", "INDEX1")
    pass

class Conveyor:
    pass

class Shooter:
    pass

class SmartCamera:
    smart_camera_1 = smart_camera_class("PORT2", "INDEX1") 
    smart_camera_1.set_mode("line")

class Guzzchan:
    def __init__(self) -> None:
        self.wheel = Wheel()
        self.shooter = Shooter()
        self.conveyor = Conveyor()

    def control(self) -> None:
        pass
    pass

# Init Robot
robot = Guzzchan()
was_auto = False

while True:
    is_auto = power_manage_module.is_auto_mode()
    if is_auto:
        if not was_auto:
            print("Competition is in auto mode")
            # robot.auto("L")
            # robot.stop_all()
        else:
            time.sleep(0.15)
    else:
        # robot.control()
        pass
    was_auto = is_auto
