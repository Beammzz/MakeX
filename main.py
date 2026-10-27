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
UPPER_LEFT = "M1"
LOWER_LEFT = "M2"
UPPER_RIGHT = "M3"
LOWER_RIGHT = "M4"

REVERSE = [1, 1, -1, -1]
SLOW_SPEED = 40
NORMAL_SPEED = 75

TRIM_FORWARD = [1, 1, 1, 1]
TRIM_BACKWARD = [1, 1, 1, 1]
TRIM_LEFT = [1, 1, 1, 1]
TRIM_RIGHT = [1, 1, 1, 1]

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
    pass

class Shooter:
    pass
            
class Guzzchan:
    def __init__(self) -> None:
        self.wheel = Wheel()
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
        

robot = Guzzchan()
            
while True:
    if power_manage_module.is_auto_mode():
        time.sleep(0.1)
        while power_manage_module.is_auto_mode():
            time.sleep(0.1)
            
    else:
        robot.control()
    time.sleep(0.05)
        