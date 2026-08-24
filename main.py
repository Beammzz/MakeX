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

LOOP_PERIOD = 0.05

# Single source of truth for every DC channel. Nothing outside this map
# should hardcode a channel string.
CH_BLOCK_A = "DC1"
CH_BALL = "DC2"
CH_BLOCK_B = "DC3"
CH_MIDWAY = "DC5"
CH_CONVEY_UPPER = "DC4"
CH_CONVEY_LOWER = "DC6"


def apply_deadzone(value, deadzone):
    """Remove stick jitter near center, then rescale so output still
    reaches full range instead of jumping from 0 to (100 - deadzone)."""
    span = 100 - deadzone
    if span <= 0:
        return 0
    if value > deadzone:
        return (value - deadzone) * 100 / span
    if value < -deadzone:
        return (value + deadzone) * 100 / span
    return 0


class Buttons:
    """Polls every button once per tick and exposes rising-edge detection,
    so holding a button no longer re-triggers a toggle every loop."""

    KEYS = ("N1", "N2", "N3", "N4", "L1", "R1", "L2", "R2", "+", "-", "≡")

    def __init__(self):
        self._now = {}
        self._prev = {}
        for key in self.KEYS:
            self._now[key] = False
            self._prev[key] = False

    def update(self):
        for key in self.KEYS:
            self._prev[key] = self._now[key]
            self._now[key] = bool(gamepad.is_key_pressed(key))

    def pressed(self, key):
        return self._now[key] and not self._prev[key]

    def held(self, key):
        return self._now[key]


class Wheel:
    """4x mecanum wheels. Right side is mounted mirrored, so its sign is flipped.

    Sign convention (verified against the original tested primitives):
        positive forward = ahead
        positive strafe  = right
        positive turn    = clockwise
    """

    CONVEY_POWER = 100
    MIDWAY_POWER = 50

    # Wiring polarity per conveyor channel. The lower motor is mounted
    # mirrored, so it needs the opposite sign to move material the same
    # way as the upper one. This is hardware orientation only -- it is
    # applied on top of the requested direction, never instead of it.
    CONVEY_SIGN = {
        CH_CONVEY_UPPER: 1,
        CH_CONVEY_LOWER: -1,
    }

    def __init__(self, default_power=50):
        self.upper_left = encoder_motor_class("M1", "INDEX1")
        self.lower_left = encoder_motor_class("M2", "INDEX1")
        self.upper_right = encoder_motor_class("M3", "INDEX1")
        self.lower_right = encoder_motor_class("M4", "INDEX1")

        self.convey_lower = CH_CONVEY_LOWER
        self.convey_upper = CH_CONVEY_UPPER
        self.midway = CH_MIDWAY

        self.default_power = default_power

        # Per-channel DC state so each subsystem toggles independently.
        self._dc_power = {}
        self.midway_state = "off"  # "off" | "forward" | "reverse"
        self.all_dc_off()

    # ---- low level ----
    def set_power(self, ul, ll, ur, lr):
        self.upper_left.set_power(int(ul))
        self.lower_left.set_power(int(ll))
        self.upper_right.set_power(int(ur))
        self.lower_right.set_power(int(lr))

    def _p(self, power):
        return self.default_power if power is None else power

    # ---- holonomic mix ----
    def drive(self, forward, strafe, turn):
        """All three axes at once. Each arg is -100..100."""
        ul = forward - strafe - turn
        ll = forward + strafe - turn
        ur = -(forward + strafe + turn)
        lr = -(forward - strafe + turn)

        # Only ever scale down: a peak below 100 must not get boosted.
        peak = max(abs(ul), abs(ll), abs(ur), abs(lr), 100)
        scale = 100.0 / peak
        self.set_power(ul * scale, ll * scale, ur * scale, lr * scale)

    # ---- primitives (now derived from drive so they can never drift) ----
    def move_forward(self, power=None):
        self.drive(self._p(power), 0, 0)

    def move_backward(self, power=None):
        self.drive(-self._p(power), 0, 0)

    def move_sideway_right(self, power=None):
        self.drive(0, self._p(power), 0)

    def move_sideway_left(self, power=None):
        self.drive(0, -self._p(power), 0)

    def rotate_right(self, power=None):
        self.drive(0, 0, self._p(power))

    def rotate_left(self, power=None):
        self.drive(0, 0, -self._p(power))

    def stop(self):
        self.upper_left.stop()
        self.lower_left.stop()
        self.upper_right.stop()
        self.lower_right.stop()

    # ---- DC accessories ----
    def set_dc(self, channel, power):
        value = int(power)
        power_expand_board.set_power(channel, value)
        self._dc_power[channel] = value

    def toggle_dc(self, channel, power):
        if self._dc_power.get(channel, 0) != 0:
            self.set_dc(channel, 0)
        else:
            self.set_dc(channel, power)

    def all_dc_off(self):
        for channel in (self.convey_lower, self.convey_upper, self.midway):
            self.set_dc(channel, 0)
        self.midway_state = "off"

    def convey_system(self, reverse=False, toggle=False):
        """Conveyor belts only (upper + lower). Does not touch midway."""
        speed = -self.CONVEY_POWER if reverse else self.CONVEY_POWER
        channels = (self.convey_lower, self.convey_upper)

        if toggle:
            running = any(
                self._dc_power.get(channel, 0) != 0 for channel in channels
            )
            for channel in channels:
                if running:
                    self.set_dc(channel, 0)
                else:
                    self.set_dc(channel, speed * self.CONVEY_SIGN[channel])
        else:
            for channel in channels:
                self.set_dc(channel, speed * self.CONVEY_SIGN[channel])

    def conveyors_running(self):
        """Derived from the real channel state, not a separate flag, so this
        can never disagree with what the board is actually doing."""
        return any(
            self._dc_power.get(channel, 0) != 0
            for channel in (self.convey_lower, self.convey_upper)
        )

    def set_intake(self, on, reverse=False):
        """Whole transport chain as one unit: both conveyors plus midway."""
        if on:
            self.convey_system(reverse=reverse)
            self.set_midway("reverse" if reverse else "forward")
        else:
            for channel in (self.convey_lower, self.convey_upper):
                self.set_dc(channel, 0)
            self.set_midway("off")

    def toggle_intake(self, reverse=False):
        self.set_intake(not self.conveyors_running(), reverse=reverse)

    def set_midway(self, state):
        """state is "off" | "forward" | "reverse"."""
        self.midway_state = state
        if state == "forward":
            self.set_dc(self.midway, self.MIDWAY_POWER)
        elif state == "reverse":
            self.set_dc(self.midway, -self.MIDWAY_POWER)
        else:
            self.set_dc(self.midway, 0)

    def toggle_midway(self, button):
        """L2 latches forward, R2 latches reverse. Pressing the button that
        matches the current direction turns it off; pressing the other one
        flips direction without needing an extra stop press."""
        if button == "L2":
            target = "forward"
        elif button == "R2":
            target = "reverse"
        else:
            return
        self.set_midway("off" if self.midway_state == target else target)


class Shooter:
    ANGLE_UP = -24
    ANGLE_MID = 0
    ANGLE_DOWN = 20
    SERVO_SPEED = 300
    FLYWHEEL_POWER = 17

    def __init__(self):
        self.servo = smartservo_class("M5", "INDEX1")
        self._spinning = False
        self.spin(False)

    def aim(self, angle, speed=None):
        if speed is None:
            speed = self.SERVO_SPEED
        self.servo.move_to(angle, speed)

    def aim_up(self):
        self.aim(self.ANGLE_UP)

    def aim_mid(self):
        self.aim(self.ANGLE_MID)

    def aim_down(self):
        self.aim(self.ANGLE_DOWN)

    def spin(self, on, power=None):
        on = bool(on)
        if on == self._spinning:
            return
        if power is None:
            power = self.FLYWHEEL_POWER
        value = int(power) if on else 0
        power_expand_board.set_power("BL1", value)
        power_expand_board.set_power("BL2", value)
        self._spinning = on


class Feeder:
    BALL_POWER = 30
    BLOCK_POWER = 100

    def __init__(self):
        self.ball_channel = CH_BALL
        self.block_a = CH_BLOCK_A
        self.block_b = CH_BLOCK_B

        self.ball_on = False
        self.block_state = "off"  # "off" | "forward" | "reverse"
        self.set_ball(False)
        self.set_block("off")

    def set_ball(self, on):
        self.ball_on = bool(on)
        power_expand_board.set_power(
            self.ball_channel, self.BALL_POWER if self.ball_on else 0
        )

    def toggle_ball(self):
        self.set_ball(not self.ball_on)

    def set_block(self, state):
        self.block_state = state
        if state == "forward":
            power_expand_board.set_power(self.block_a, self.BLOCK_POWER)
            power_expand_board.set_power(self.block_b, -self.BLOCK_POWER)
        elif state == "reverse":
            power_expand_board.set_power(self.block_a, -self.BLOCK_POWER)
            power_expand_board.set_power(self.block_b, self.BLOCK_POWER)
        else:
            power_expand_board.set_power(self.block_a, 0)
            power_expand_board.set_power(self.block_b, 0)

    def toggle_block(self, button):
        if button == "L1":
            target = "forward"
        elif button == "R1":
            target = "reverse"
        else:
            return
        self.set_block("off" if self.block_state == target else target)

    def all_off(self):
        self.set_ball(False)
        self.set_block("off")


class Guzzchan:
    DEADZONE = 15
    DRIVE_POWER = 60
    TURN_POWER = 45

    def __init__(self):
        self.wheel = Wheel(default_power=50)
        self.shooter = Shooter()
        self.feeder = Feeder()
        self.buttons = Buttons()
        self.auto_done = False

        self.shooter.aim_mid()
        self.safe_state()

    def safe_state(self):
        self.wheel.stop()
        self.wheel.all_dc_off()
        self.feeder.all_off()
        self.shooter.spin(False)

    # ---- teleop ----
    def manual(self):
        self.buttons.update()

        ly = apply_deadzone(gamepad.get_joystick("Ly"), self.DEADZONE)
        lx = apply_deadzone(gamepad.get_joystick("Lx"), self.DEADZONE)
        rx = apply_deadzone(gamepad.get_joystick("Rx"), self.DEADZONE)

        forward = ly * self.DRIVE_POWER / 100.0
        strafe = lx * self.DRIVE_POWER / 100.0
        turn = rx * self.TURN_POWER / 100.0

        if forward == 0 and strafe == 0 and turn == 0:
            self.wheel.stop()
        else:
            self.wheel.drive(forward, strafe, turn)

        if self.buttons.pressed("N2"):
            self.shooter.aim_up()
        if self.buttons.pressed("≡"):
            self.shooter.aim_mid()
        if self.buttons.pressed("N3"):
            self.shooter.aim_down()

        if self.buttons.pressed("L1"):
            self.feeder.toggle_block("L1")
        if self.buttons.pressed("R1"):
            self.feeder.toggle_block("R1")

        # L2 / R2 still drive midway on its own, for clearing a jam without
        # running the whole chain.
        if self.buttons.pressed("L2"):
            self.wheel.toggle_midway("L2")
        if self.buttons.pressed("R2"):
            self.wheel.toggle_midway("R2")

        # N1 now runs the full transport chain: both conveyors + midway.
        if self.buttons.pressed("N1"):
            self.wheel.toggle_intake()

        if self.buttons.pressed("N4"):
            self.feeder.toggle_ball()

        self.shooter.spin(self.buttons.held("+"))

    # ---- autonomous ----
    def auto(self, side):
        if self.auto_done:
            return

        # Mirror the sideways step depending on which side of the field we start.
        direction = 1 if side == "L" else -1

        self.wheel.drive(60, 0, 0)
        time.sleep(1.0)

        self.wheel.drive(0, 60 * direction, 0)
        time.sleep(0.6)

        self.wheel.stop()

        self.shooter.aim_up()
        self.shooter.spin(True)
        time.sleep(1.5)

        self.feeder.set_block("forward")
        time.sleep(2.0)

        self.feeder.set_block("off")
        self.shooter.spin(False)

        self.auto_done = True

    def reset_auto(self):
        self.auto_done = False
        self.safe_state()

    # ---- one tick of the robot ----
    def update(self, auto_side="L", force_auto=False):
        if power_manage_module.is_auto_mode() or force_auto:
            self.auto(auto_side)
        else:
            if self.auto_done:
                self.reset_auto()
            self.manual()


AUTO_SIDE = "L"   # "L" or "R"
DEBUG_AUTO = False

robot = Guzzchan()

while True:
    robot.update(auto_side=AUTO_SIDE, force_auto=DEBUG_AUTO)
    time.sleep(LOOP_PERIOD)
