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
        self.DEADZONE = 30
        self.STRAFE_GAIN = 1
        self.MAX_POWER = 80
        self.TRIM_UL = 1.00
        self.TRIM_LL = 1.00
        self.TRIM_UR = 1.00
        self.TRIM_LR = 1.00
        

    # Deadzone Function for Holomix
    def _dz(self, v):
        if abs(v) < self.DEADZONE:
            return 0
        span = 100 - self.DEADZONE
        if v > 0:
            return (v - self.DEADZONE) * 100 / span
        return (v + self.DEADZONE) * 100 / span
        
    def set_power(self, ul, ll, ur, lr):
        self.upper_left.set_power(ul)
        self.lower_left.set_power(ll)
        self.upper_right.set_power(ur)
        self.lower_right.set_power(lr)
    
    def stop(self):
        self.set_power(0, 0, 0, 0)
        
    def holomix(self, lx, ly, rx):
        vx = -self._dz(lx) * self.STRAFE_GAIN
        vy = self._dz(ly)
        vw = -self._dz(rx)

        # ล้อฝั่งขวาติดกลับด้าน จึงติดลบที่ ur/lr -- ทั้งไฟล์มีที่เดียวตรงนี้
        # ถ้าไม่มี vy จะกลายเป็นหมุนและ vw จะกลายเป็นเดินหน้า (Ly หมุน, Rx เดิน)
        ul = (vy + vx + vw) * self.TRIM_UL
        ll = (vy - vx + vw) * self.TRIM_LL
        ur = -(vy - vx - vw) * self.TRIM_UR
        lr = -(vy + vx - vw) * self.TRIM_LR

        peak = max(abs(ul), abs(ll), abs(ur), abs(lr), 100)
        scale = self.MAX_POWER / peak

        self.set_power(
            int(ul * scale),
            int(ll * scale),
            int(ur * scale),
            int(lr * scale),
        )
    
# Consist of Ball Conveyor and Block Conveyor
class conveyor:
    def __init__(self):
        # Class linker
        self.shooter = Shooter()

        # DC Motors
        self.block_a = "DC1"
        self.block_b = "DC3"
        
        self.convey_upper = "DC4"
        self.front_feeder = "DC2"
        self.convey_midway = "DC5"
        self.convey_lower = "DC6"
        self.sweeper = "DC7"
        self.block_convey_servo = smartservo_class("M5", "INDEX2")
        self.sweeper_lift_servo = smartservo_class("M6", "INDEX1")

        # Toggle State
        self.is_block_convey_toggled = False
        self.is_ball_convey_toggled = False
        self.is_midway_convey_toggled = False
        self.block_convey_servo_toggled = False
        self.is_sweeper_toggled = False
        self.is_lift_sweeper_toggled = False

    def block_convey(self, reverse=False):
        if not self.is_block_convey_toggled:
            if reverse:
                power_expand_board.set_power(self.block_a, 100)
                power_expand_board.set_power(self.block_b, -100)
            else:
                power_expand_board.set_power(self.block_a, -100)
                power_expand_board.set_power(self.block_b, 100)
            self.is_block_convey_toggled = True
        else:
            power_expand_board.set_power(self.block_a, 0)
            power_expand_board.set_power(self.block_b, 0)
            self.is_block_convey_toggled = False

    def ball_convey(self, reverse=False):
        if not self.is_ball_convey_toggled:
            if reverse:
                power_expand_board.set_power(self.convey_upper, -100)
                power_expand_board.set_power(self.convey_lower, 100)
                power_expand_board.set_power(self.front_feeder, 100)
            else:
                power_expand_board.set_power(self.convey_upper, 100)
                power_expand_board.set_power(self.convey_lower, -100)
                power_expand_board.set_power(self.front_feeder, -100)
            self.is_ball_convey_toggled = True
        else:
            power_expand_board.set_power(self.convey_upper, 0)
            power_expand_board.set_power(self.front_feeder, 0)
            power_expand_board.set_power(self.convey_lower, 0)
            self.is_ball_convey_toggled = False

    def midway_convey(self, reverse=False):
        if not self.is_midway_convey_toggled:
            if reverse:
                power_expand_board.set_power(self.convey_midway, -100)
            else:
                power_expand_board.set_power(self.convey_midway, 100)
            self.is_midway_convey_toggled = True
        else:
            power_expand_board.set_power(self.convey_midway, 0)
            self.is_midway_convey_toggled = False

    def block_convey_servo_move(self):
        if not self.block_convey_servo_toggled:
            self.block_convey_servo.move_to(55, 50)
            self.block_convey_servo_toggled = True
        else:
            self.block_convey_servo.move_to(0, 50)
            self.block_convey_servo_toggled = False

    def toggle_sweeper(self):
        if not self.is_sweeper_toggled:
            if self.shooter.is_shooter_toggled:
                self.shooter.toggle_shooter()
            time.sleep(0.1)
            self.shooter.set_shooter_angle(-50)
            power_expand_board.set_power(self.sweeper, -80)
            self.is_sweeper_toggled = True
        else:
            self.shooter.set_shooter_angle(0)
            self.shooter.is_shooter_toggled_angle = False
            power_expand_board.set_power(self.sweeper, 0)
            self.is_sweeper_toggled = False

    def lift(self, angle):
        self.sweeper_lift_servo.move_to(angle, 30)

    def stop_all(self):
        power_expand_board.set_power(self.block_a, 0)
        power_expand_board.set_power(self.block_b, 0)
        power_expand_board.set_power(self.convey_upper, 0)
        power_expand_board.set_power(self.convey_midway, 0)
        power_expand_board.set_power(self.convey_lower, 0)
        power_expand_board.set_power(self.sweeper, 0)
        self.is_block_convey_toggled = False
        self.is_ball_convey_toggled = False
        self.is_midway_convey_toggled = False

# Consist of Brushless Motor and Shooter Servo
class Shooter:
    def __init__(self):
        self.is_shooter_toggled = False
        self.is_shooter_toggled_angle = False
        self.servo = smartservo_class("M5", "INDEX1")

        # Shooter Servo Tuning Parameters
        self.ANGLE_HOME = 0
        self.ANGLE_AIM = -24
        self.ANGLE_SPEED = 50

    def set_shooter_angle(self, angle):
        self.servo.move_to(angle, self.ANGLE_SPEED)

    def toggle_shooter(self):
        if not self.is_shooter_toggled:
            power_expand_board.set_power("BL1", 17)
            power_expand_board.set_power("BL2", 17)
            self.is_shooter_toggled = True
        else:
            power_expand_board.set_power("BL1", 0)
            power_expand_board.set_power("BL2", 0)
            self.is_shooter_toggled = False

    def toggle_shooter_angle(self):
        if not self.is_shooter_toggled_angle:
            self.set_shooter_angle(self.ANGLE_AIM)
            self.is_shooter_toggled_angle = True
        else:
            self.set_shooter_angle(self.ANGLE_HOME)
            self.is_shooter_toggled_angle = False

    def stop(self):
        power_expand_board.set_power("BL1", 0)
        power_expand_board.set_power("BL2", 0)
        self.is_shooter_toggled = False
        

class Guzzchan:
    def __init__(self):
        self.wheel = Wheel()
        self.shooter = Shooter()
        self.conveyor = conveyor()
        self._prev_keys = {}
        self.shooter.set_shooter_angle(self.shooter.ANGLE_HOME)

    def _pressed(self, key):
        now = gamepad.is_key_pressed(key)
        fired = now and not self._prev_keys.get(key, False)
        self._prev_keys[key] = now
        return fired
    
    def control(self):
        lx = gamepad.get_joystick("Lx")
        ly = gamepad.get_joystick("Ly")
        rx = gamepad.get_joystick("Rx")
        # Robot Movement Control (Wheel)
        # Pass to Holomix Function
        self.wheel.holomix(lx, ly, rx)

        # Button Control
        if self._pressed("+"):
            self.shooter.toggle_shooter()
            time.sleep(0.1)

        if self._pressed("N1"):
            self.conveyor.ball_convey()
            time.sleep(0.1)

        if self._pressed("N4"):
            self.conveyor.toggle_sweeper()
            time.sleep(0.1)

        if self._pressed("L1"):
            self.conveyor.block_convey()
            time.sleep(0.1)

        if self._pressed("R1"):
            self.conveyor.block_convey(reverse=True)
            time.sleep(0.1)

        if self._pressed("L2"):
            self.conveyor.midway_convey()
            time.sleep(0.1)

        if self._pressed("R2"):
            self.conveyor.midway_convey(reverse=True)
            time.sleep(0.1)

        if self._pressed("N3"):
            self.shooter.toggle_shooter_angle()
            time.sleep(0.1)

        if self._pressed("≡"):
            self.conveyor.block_convey_servo_move()
            time.sleep(0.1)

        if self._pressed("Up"):
            self.conveyor.lift(137)
            time.sleep(0.1)

        if self._pressed("Down"):
            self.conveyor.lift(0)
            time.sleep(0.1)


    def stop_all(self):
        self.wheel.stop()
        self.conveyor.stop_all()
        self.shooter.stop()   

    def auto(self, side):
        # TODO: Implement Auto Mode with side.
        pass

# Init
robot = Guzzchan()
was_auto = False

# Main Loop
while True:
    is_auto = power_manage_module.is_auto_mode()
    if power_manage_module.is_auto_mode():
        print("Competition is in auto mode")
        robot.auto("Left")
    else:
        robot.control()
        
    time.sleep(0.05)