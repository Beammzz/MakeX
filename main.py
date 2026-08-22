import time

import novapi
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


# ============================================================
#  Drivetrain (Mecanum)
# ============================================================
class Wheel:
    """4x mecanum wheels. Right side is mounted mirrored, so its sign is flipped."""

    def __init__(self, default_power=40):
        self.upper_left = encoder_motor_class("M1", "INDEX1")
        self.lower_left = encoder_motor_class("M2", "INDEX1")
        self.upper_right = encoder_motor_class("M3", "INDEX1")
        self.lower_right = encoder_motor_class("M4", "INDEX1")

        self.default_power = default_power

    # ---- low level ----
    def set_power(self, ul, ll, ur, lr):
        self.upper_left.set_power(ul)
        self.lower_left.set_power(ll)
        self.upper_right.set_power(ur)
        self.lower_right.set_power(lr)

    def _p(self, power):
        return self.default_power if power is None else power

    # ---- primitives ----
    def move_forward(self, power=None):
        p = self._p(power)
        self.set_power(ul=p, ll=p, ur=-p, lr=-p)

    def move_backward(self, power=None):
        p = self._p(power)
        self.set_power(ul=-p, ll=-p, ur=p, lr=p)

    def move_sideway_right(self, power=None):
        p = self._p(power)
        self.set_power(ul=-p, ll=p, ur=-p, lr=p)

    def move_sideway_left(self, power=None):
        p = self._p(power)
        self.set_power(ul=p, ll=-p, ur=p, lr=-p)

    def rotate_right(self, power=None):
        p = self._p(power)
        self.set_power(ul=-p, ll=-p, ur=-p, lr=-p)

    def rotate_left(self, power=None):
        p = self._p(power)
        self.set_power(ul=p, ll=p, ur=p, lr=p)

    def stop(self):
        self.upper_left.stop()
        self.lower_left.stop()
        self.upper_right.stop()
        self.lower_right.stop()

    # ---- holonomic mix ----
    # If Bung Guzz want to mix movement between movement and rotation
    def drive(self, forward, strafe, turn):
        """All three axes at once. Each arg is -100..100."""
        ul = forward + strafe + turn
        ll = forward - strafe + turn
        ur = -(forward - strafe - turn)
        lr = -(forward + strafe - turn)

        peak = max(abs(ul), abs(ll), abs(ur), abs(lr), 100)
        scale = 100 / peak
        self.set_power(ul * scale, ll * scale, ur * scale, lr * scale)


# ============================================================
#  Shooter (servo aim + flywheels)
# ============================================================
class Shooter:
    ANGLE_UP = -24
    ANGLE_MID = 0
    ANGLE_DOWN = 20
    SERVO_SPEED = 300

    def __init__(self):
        self.servo = smartservo_class("M5", "INDEX1")
        self._spinning = False

    def aim(self, angle, speed=None):
        self.servo.move_to(angle, speed or self.SERVO_SPEED)

    def aim_up(self):
        self.aim(self.ANGLE_UP)

    def aim_mid(self):
        self.aim(self.ANGLE_MID)

    def aim_down(self):
        self.aim(self.ANGLE_DOWN)

    def spin(self, on, power=17):
        # only touch the board when the state actually changes
        if on == self._spinning:
            return
        value = power if on else 0
        power_expand_board.set_power("BL1", value)
        power_expand_board.set_power("BL2", value)
        self._spinning = on
        

class Feeder:
    def __init__(self):
        self.feeder_toggle_ball = False
        self.feeder_toggle_block = False
        
    def toggle_ball(self):
        self.feeder_toggle_ball = not self.feeder_toggle_ball
        if self.feeder_toggle_ball:
            power_expand_board.set_power("DC6", 30)  # Turn on feeder
        else:
            power_expand_board.set_power("DC6", 0)   # Turn off feeder

    def toggle_block(self, button=""):
        self.feeder_toggle_block = not self.feeder_toggle_block
        if self.feeder_toggle_block and button == "L1":
            power_expand_board.set_power("DC1", 75)  # Turn on block feeder
            power_expand_board.set_power("DC3", 75)   # Turn on another feeder
        elif self.feeder_toggle_block and button == "R1":
            power_expand_board.set_power("DC1", -75)  # Turn on block feeder
            power_expand_board.set_power("DC3", -75)   # Turn on another feeder
        else:
            power_expand_board.set_power("DC1", 0)   # Turn off block feeder
            power_expand_board.set_power("DC3", 0)   # Turn off another feeder


# ============================================================
#  Robot
# ============================================================
class Guzzchan:
    DEADZONE = 50

    def __init__(self):
        self.wheel = Wheel(default_power=50)
        self.shooter = Shooter()
        self.feeder = Feeder()
        self.auto_done = False

        self.shooter.aim_mid()

    # ---- teleop ----
    def manual(self):
        ly = gamepad.get_joystick("Ly")
        lx = gamepad.get_joystick("Lx")
        rx = gamepad.get_joystick("Rx")
        ry = gamepad.get_joystick("Ry")
        dz = self.DEADZONE

        if ly > dz:
            self.wheel.move_forward()
        elif ly < -dz:
            self.wheel.move_backward()
        elif lx > dz:
            self.wheel.move_sideway_right()
        elif lx < -dz:
            self.wheel.move_sideway_left()
        elif rx > dz:
            self.wheel.rotate_right()
        elif rx < -dz:
            self.wheel.rotate_left()
        else:
            self.wheel.stop()

        # --- buttons ---
        if gamepad.is_key_pressed("N2"):
            self.shooter.aim_up()
        if gamepad.is_key_pressed("≡"):
            self.shooter.aim_mid()
        if gamepad.is_key_pressed("N3"):
            self.shooter.aim_down()
        if gamepad.is_key_pressed("L1"):
            self.feeder.toggle_block("L1")
            time.sleep(0.1)
        if gamepad.is_key_pressed("R1"):
            self.feeder.toggle_block("R1")
            time.sleep(0.1)

        self.shooter.spin(gamepad.is_key_pressed("+"))

    # ---- autonomous ----
    def auto(self, side):
        if self.auto_done:
            return

        if side == "L":
            self.wheel.upper_left.move(5000, 100)
        else:
            self.wheel.upper_right.move(500, 100)

        self.auto_done = True

    def reset_auto(self):
        self.auto_done = False

    # ---- one tick of the robot ----
    def update(self, auto_side="L", force_auto=False):
        if power_manage_module.is_auto_mode() or force_auto:
            self.auto(auto_side)
        else:
            if self.auto_done:
                self.reset_auto()
            self.manual()


# ============================================================
#  Main
# ============================================================
AUTO_SIDE = "L"   # "L" or "R"
DEBUG_AUTO = False

robot = Guzzchan()

while True:
    robot.update(auto_side=AUTO_SIDE, force_auto=DEBUG_AUTO)
    time.sleep(0.05)