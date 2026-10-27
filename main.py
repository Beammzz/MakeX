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

# จูนตรงนี้น่ะคร้าบ
# ล้อ
UPPER_LEFT = "M1"
LOWER_LEFT = "M2"
UPPER_RIGHT = "M5"
LOWER_RIGHT = "M4"

REVERSE = [1, 1, 1, -1]
SLOW_SPEED = 40
NORMAL_SPEED = 75
TRIM_FORWARD = [1, 1, 1, 1]
TRIM_BACKWARD = [1, 1, 1, 1]
TRIM_LEFT = [1, 1, 1, 1]
TRIM_RIGHT = [1, 1, 1, 1]

# สายพาน
DC_BALL_SHOOTER = "DC3"
DC_BALL_CONVEYOR = "DC2"
DC_BALL_FEEDER = "DC1"

DC_BLOCK_A = "DC4"
DC_BLOCK_B = "DC5"

# ที่ยิง
SHOOTER = "BL1"
SIXSEVEN_SERVO = "M6"

# ลิฟท์
DC_CONE_LIFT = "DC6"


class Wheel:
    def __init__(self) -> None:
        self.motors = [
            encoder_motor_class(UPPER_LEFT, 'INDEX1'),
            encoder_motor_class(LOWER_LEFT, 'INDEX1'),
            encoder_motor_class(UPPER_RIGHT, 'INDEX1'),
            encoder_motor_class(LOWER_RIGHT, 'INDEX1')
        ]
        
        self.slow_speed = SLOW_SPEED
        self.normal_speed = NORMAL_SPEED
        self.slide = [-1, 1, 1, -1]
        self.rotate = [1, 1, -1, -1]
        
        
    def move_forward(self):
        for i in range(4):
            self.motors[i].set_power((self.normal_speed * TRIM_FORWARD[i]) * REVERSE[i])
            
    def move_backward(self):
        for i in range(4):
            self.motors[i].set_power(-(self.normal_speed * TRIM_BACKWARD[i]) * REVERSE[i])
            
    def move_left(self):
        for i in range(4):
            self.motors[i].set_power(-(self.normal_speed * TRIM_LEFT[i]) * REVERSE[i] * self.slide[i])
            
    def move_right(self):
        for i in range(4):
            self.motors[i].set_power((self.normal_speed * TRIM_RIGHT[i]) * REVERSE[i] * self.slide[i])
            
    def move_slow_forward(self):
        for i in range(4):
            self.motors[i].set_power((self.slow_speed * TRIM_FORWARD[i]) * REVERSE[i])
            
    def move_slow_backward(self):
        for i in range(4):
            self.motors[i].set_power(-(self.slow_speed * TRIM_BACKWARD[i]) * REVERSE[i])
            
    def move_slow_left(self):
        for i in range(4):
            self.motors[i].set_power(-(self.slow_speed * TRIM_LEFT[i]) * REVERSE[i] * self.slide[i])
            
    def move_slow_right(self):
        for i in range(4):
            self.motors[i].set_power((self.slow_speed * TRIM_RIGHT[i]) * REVERSE[i] * self.slide[i])
            
    def rotate_left(self):
        for i in range(4):
            self.motors[i].set_power(self.normal_speed * REVERSE[i] * self.rotate[i])
            
    def rotate_right(self):
        for i in range(4):
            self.motors[i].set_power(-self.normal_speed * REVERSE[i] * self.rotate[i])
            
    def rotate_slow_left(self):
        for i in range(4):
            self.motors[i].set_power(self.slow_speed * REVERSE[i] * self.rotate[i])
            
    def rotate_slow_right(self):
        for i in range(4):
            self.motors[i].set_power(-self.slow_speed * REVERSE[i] * self.rotate[i])

    def stop(self):
        for i in range(4):
            self.motors[i].stop()

class Conveyor:
    def __init__(self) -> None:
        # Ball convey
        self.ball_shooter = DC_BALL_SHOOTER
        self.ball_conveyor = DC_BALL_CONVEYOR
        self.ball_feeder = DC_BALL_FEEDER
        self.sixseven = smartservo_class(SIXSEVEN_SERVO, "INDEX1")
        self.ball_conveyor_toggle = False

        # Block convey
        self.block_a = DC_BLOCK_A
        self.block_b = DC_BLOCK_B

    def toggle_ball_conveyor(self):
        if not self.ball_conveyor_toggle:
            power_expand_board.set_power(self.ball_feeder, 60)
            power_expand_board.set_power(self.ball_conveyor, 60)
            power_expand_board.set_power(self.ball_shooter, 60)
            self.ball_conveyor_toggle = True
        else:
            power_expand_board.set_power(self.ball_feeder, 0)
            power_expand_board.set_power(self.ball_conveyor, 0)
            power_expand_board.set_power(self.ball_shooter, 0)
            self.ball_conveyor_toggle = False

    def block_convey(self, reverse=False):
            if reverse:
                power_expand_board.set_power(self.block_a, -100)
                power_expand_board.set_power(self.block_b, -100)
            else:
                power_expand_board.set_power(self.block_a, 100)
                power_expand_board.set_power(self.block_b, 100)

    def block_convey_stop(self):
        power_expand_board.set_power(self.block_a, 0)
        power_expand_board.set_power(self.block_b, 0)
        
class Lift:
    def __init__(self) -> None:
        self.cone_lift = DC_CONE_LIFT
        
    def lift_cone(self, reverse=False):
        if reverse:
            power_expand_board.set_power(self.cone_lift, -60)
        else:
            power_expand_board.set_power(self.cone_lift, 60)
            
    def stop_lift(self):
        power_expand_board.set_power(self.cone_lift, 0)


class Shooter:
    def __init__(self) -> None:
        self.shooter = SHOOTER
        self.shooter_toggle = False

    def toggle_shooter(self):
        if not self.shooter_toggle:
            power_expand_board.set_power(self.shooter, 100)
            self.shooter_toggle = True
        else:
            power_expand_board.set_power(self.shooter, 0)
            self.shooter_toggle = False
            
class Guzzchan:
    def __init__(self) -> None:
        self.wheel = Wheel()
        self.conveyor = Conveyor()
        self.shooter = Shooter()
        self.lift = Lift()
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
        if rx > 70:
            self.wheel.rotate_right()
        elif rx < -70:
            self.wheel.rotate_left()
        elif rx > 20 and rx < 70:
            self.wheel.rotate_slow_right()
        elif rx < -20 and rx > -70:
            self.wheel.rotate_slow_left()
        elif lx > 70:
            self.wheel.move_right()
        elif lx < -70:
            self.wheel.move_left()
        elif ly > 70:
            self.wheel.move_forward()
        elif ly < -70:
            self.wheel.move_backward()
        elif lx > 20 and lx < 70:
            self.wheel.move_slow_right()
        elif lx < -20 and lx > -70:
            self.wheel.move_slow_left()
        elif ly > 20 and ly < 70:
            self.wheel.move_slow_forward()
        elif ly < -20 and ly > -70:
            self.wheel.move_slow_backward()
        else:
            self.wheel.stop()

        if self._pressed("N1"):
            self.conveyor.toggle_ball_conveyor()

        if self._pressed("+"):
            self.shooter.toggle_shooter()  


        if gamepad.is_key_pressed("L2") or gamepad.is_key_pressed("R2"):
            if self.conveyor.ball_conveyor_toggle:
                self.conveyor.toggle_ball_conveyor()
        if gamepad.is_key_pressed("L2"):
            power_expand_board.set_power(self.conveyor.ball_shooter, -100)
            power_expand_board.set_power(self.conveyor.ball_conveyor, -100)
            self.conveyor.sixseven.set_power(60)
        elif gamepad.is_key_pressed("R2"):
            power_expand_board.set_power(self.conveyor.ball_shooter, 100)
            power_expand_board.set_power(self.conveyor.ball_conveyor, 100)
            self.conveyor.sixseven.set_power(60)
        elif not self.conveyor.ball_conveyor_toggle:
            power_expand_board.set_power(self.conveyor.ball_shooter, 0)
            power_expand_board.set_power(self.conveyor.ball_conveyor, 0)
            self.conveyor.sixseven.set_power(0)
            

        if gamepad.is_key_pressed("L1"):
            self.conveyor.block_convey()
        elif gamepad.is_key_pressed("R1"):
            self.conveyor.block_convey(reverse=True)
        else:
            self.conveyor.block_convey_stop()
        
        if gamepad.is_key_pressed("N2"):
            self.lift.lift_cone()
        elif gamepad.is_key_pressed("N3"):
            self.lift.lift_cone(reverse=True)
        else:
            self.lift.stop_lift()

robot = Guzzchan()
            
while True:
    if power_manage_module.is_auto_mode():
        time.sleep(0.1)
        while power_manage_module.is_auto_mode():
            time.sleep(0.1)
            
    else:
        robot.control()
    time.sleep(0.05)
        