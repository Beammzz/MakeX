# -*- coding: utf-8 -*-
"""GUZZ-CHAN teleop / auto.

Everything you tune lives in the CONFIG block below. Nothing under
"ROBOT CODE" contains a number you should have to edit at the field --
if you find yourself editing down there, the knob is missing up here.

How the DC channels work:

    DC_CHANNEL   name -> the physical channel on the power expand board
    DC_POWER     name -> the power that name runs at, -100..100

  The SIGN in DC_POWER is the wiring direction. A motor mounted mirrored
  gets a minus sign here, and that is the ONLY place it is handled. Asking
  for "reverse" just negates whatever is in the table, so a group whose two
  motors are wired opposite still moves material the same way.

  Every channel has its own number, so a weak roller is a one-number fix.

Set DEBUG_DC = True to print every DC write to the USB console. That is the
quickest way to tell "the code never commanded it" apart from "the code
commanded it and the motor did not move" (see scripts/Test_DC.py to drive a
single channel from the PC).
"""
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


# ==========================================================================
#  CONFIG -- tune everything here
# ==========================================================================

LOOP_PERIOD = 0.05        # seconds per tick
DEBUG_DC = False          # print every DC write to the console
DEBUG_AUTO = False        # run the auto routine without the field switch
AUTO_SIDE = "L"           # "L" or "R" -- which side we start on


# ---- 1. Drivetrain -------------------------------------------------------
# Mecanum, plain and known-good: forward/strafe/turn are summed per wheel and
# the result is scaled down if it would clip. No gyro, no closed loop.

WHEEL_PORTS = ("M1", "M2", "M3", "M4")   # upper-left, lower-left, upper-right, lower-right
WHEEL_INVERT = (1, 1, -1, -1)            # per wheel: -1 if that wheel is mounted mirrored

DEADZONE = 15             # stick counts ignored around center, 0..99
DRIVE_POWER = 60          # max power for forward + strafe
TURN_POWER = 45           # max power for turning

# Which physical direction counts as positive for each axis. Flip one to -1
# if the robot goes the wrong way on that axis -- it applies to teleop and
# auto alike, so both stay consistent. NOTE: the gamepad docs say the X axes
# read POSITIVE when the stick is pushed LEFT, so if strafe/turn come out
# mirrored on the real robot, these two are the knobs.
AXIS_FORWARD_INVERT = 1
AXIS_STRAFE_INVERT = 1
AXIS_TURN_INVERT = 1


# ---- 2. DC channels ------------------------------------------------------
# name -> physical channel. Names are used everywhere else in the file.
#
# CHECK THIS TABLE FIRST if a motor "does nothing". DC2, DC4 and DC5 only
# appeared in the last refactor and have never been confirmed against the
# real wiring: before that the code only ever drove DC1, DC3 and DC6 -- and
# DC6 was the BALL feeder at +30, not a conveyor. Use scripts/Test_DC.py to
# find which channel actually moves each motor, then fix it here.
DC_CHANNEL = {
    "block_a":      "DC1",
    "ball":         "DC2",
    "block_b":      "DC3",
    "convey_upper": "DC4",
    "midway":       "DC5",
    "convey_lower": "DC6",
}

# name -> power, -100..100. Sign = wiring direction (see the module docstring).
# Raise a number here if that motor is too weak; negate it if it runs backwards.
DC_POWER = {
    "block_a":       100,
    "ball":           30,
    "block_b":      -100,   # wired opposite block_a
    "convey_upper":  100,   # DC4 -- raise/negate here if the upper belt stalls
    "midway":         50,
    "convey_lower": -100,   # wired opposite convey_upper
}

# Named groups that a single button drives together.
DC_GROUP = {
    "intake": ("convey_upper", "convey_lower", "midway"),
    "block":  ("block_a", "block_b"),
}


# ---- 3. Shooter ----------------------------------------------------------
SERVO_PORT = "M5"
SERVO_SPEED = 50          # rpm; the smartservo docs allow 1..50
ANGLE_UP = -24
ANGLE_MID = 0
ANGLE_DOWN = 20

# Brushless channels, each with its own power so they can be trimmed apart.
FLYWHEEL = (
    ("BL1", 17),
    ("BL2", 17),
)


# ---- 4. Buttons ----------------------------------------------------------
# action -> gamepad button. Rebinding is a one-line edit: only the buttons
# listed here are polled, so nothing can go stale.
BTN = {
    "aim_up":     "N2",
    "aim_mid":    "≡",   # the "≡" menu button
    "aim_down":   "N3",
    "block_fwd":  "L1",
    "block_rev":  "R1",
    "midway_fwd": "L2",       # midway alone, for clearing a jam
    "midway_rev": "R2",
    "intake":     "N1",       # whole transport chain
    "ball":       "N4",
    "flywheel":   "+",        # hold to spin
    "stop_all":   "-",        # panic: everything off
}


# ---- 5. Autonomous -------------------------------------------------------
AUTO_FORWARD_POWER = 60
AUTO_FORWARD_TIME = 1.0
AUTO_SIDEWAY_POWER = 60
AUTO_SIDEWAY_TIME = 0.6
AUTO_SPINUP_TIME = 1.5
AUTO_FEED_TIME = 2.0


# ==========================================================================
#  ROBOT CODE -- no tuning below this line
# ==========================================================================

def clamp(value):
    """Board takes -100..100 integers."""
    value = int(value)
    if value > 100:
        return 100
    if value < -100:
        return -100
    return value


def read_stick(axis):
    """Stick value with the deadzone removed and the remaining travel
    rescaled, so the output still reaches 100 instead of jumping from 0
    to (100 - DEADZONE). Axis direction is not applied here -- drive() owns
    that, so it is handled in exactly one place."""
    value = gamepad.get_joystick(axis)
    span = 100 - DEADZONE
    if span <= 0:
        return 0
    if value > DEADZONE:
        return (value - DEADZONE) * 100.0 / span
    if value < -DEADZONE:
        return (value + DEADZONE) * 100.0 / span
    return 0


class Buttons:
    """Polls each bound button once per tick and reports rising edges, so a
    held button toggles once instead of every loop."""

    def __init__(self, keys):
        self._keys = tuple(keys)
        self._now = {}
        self._prev = {}
        for key in self._keys:
            self._now[key] = False
            self._prev[key] = False

    def update(self):
        for key in self._keys:
            self._prev[key] = self._now[key]
            self._now[key] = bool(gamepad.is_key_pressed(key))

    def pressed(self, key):
        return self._now[key] and not self._prev[key]

    def held(self, key):
        return self._now[key]


class Drive:
    """4x mecanum wheels."""

    def __init__(self):
        self.motors = []
        for port in WHEEL_PORTS:
            self.motors.append(encoder_motor_class(port, "INDEX1"))

    def set_power(self, ul, ll, ur, lr):
        values = (ul, ll, ur, lr)
        for i in range(len(self.motors)):
            self.motors[i].set_power(clamp(values[i] * WHEEL_INVERT[i]))

    def drive(self, forward, strafe, turn):
        """Each argument is -100..100. Positive: forward / right / clockwise."""
        forward = forward * AXIS_FORWARD_INVERT
        strafe = strafe * AXIS_STRAFE_INVERT
        turn = turn * AXIS_TURN_INVERT

        ul = forward - strafe - turn
        ll = forward + strafe - turn
        ur = forward + strafe + turn
        lr = forward - strafe + turn

        # Only ever scale down: a peak below 100 must not get boosted.
        peak = max(abs(ul), abs(ll), abs(ur), abs(lr), 100)
        scale = 100.0 / peak
        self.set_power(ul * scale, ll * scale, ur * scale, lr * scale)

    def stop(self):
        self.set_power(0, 0, 0, 0)


class DCBank:
    """Every DC channel on the power expand board, addressed by name.

    Direction is +1 (as configured), -1 (reversed) or 0 (stopped). The
    running direction is read back from the power actually written, so it
    can never disagree with what the board was told.
    """

    def __init__(self):
        self._power = {}
        self.all_off()

    # ---- one channel ----
    def set(self, name, direction):
        power = 0
        if direction:
            power = clamp(DC_POWER.get(name, 0) * direction)
        channel = DC_CHANNEL[name]
        power_expand_board.set_power(channel, power)
        self._power[name] = power
        if DEBUG_DC:
            print("DC %-13s %-4s -> %4d" % (name, channel, power))

    def direction(self, name):
        power = self._power.get(name, 0)
        base = DC_POWER.get(name, 0)
        if power == 0 or base == 0:
            return 0
        return 1 if (power > 0) == (base > 0) else -1

    def toggle(self, name, direction):
        """Pressing the direction it already runs stops it; pressing the
        other one flips it without needing a stop press in between."""
        self.set(name, 0 if self.direction(name) == direction else direction)

    # ---- a group ----
    def set_group(self, group, direction):
        for name in DC_GROUP[group]:
            self.set(name, direction)

    def group_direction(self, group):
        for name in DC_GROUP[group]:
            direction = self.direction(name)
            if direction:
                return direction
        return 0

    def toggle_group(self, group, direction):
        self.set_group(
            group, 0 if self.group_direction(group) == direction else direction
        )

    def all_off(self):
        """Sweeps DC_CHANNEL itself, so a channel added to the config above
        is covered here without a second edit."""
        for name in DC_CHANNEL:
            self.set(name, 0)
            


class Shooter:
    """Servo aim + brushless flywheels."""

    def __init__(self):
        self.servo = smartservo_class(SERVO_PORT, "INDEX1")
        self._spinning = None      # unknown until the first write
        self.spin(False)           # so boot really does zero the flywheels

    def aim(self, angle):
        self.servo.move_to(angle, SERVO_SPEED)

    def spin(self, on):
        on = bool(on)
        if on == self._spinning:
            return
        for channel, power in FLYWHEEL:
            power_expand_board.set_power(channel, clamp(power) if on else 0)
        self._spinning = on


class Robot:

    def __init__(self):
        self.drive = Drive()
        self.dc = DCBank()
        self.shooter = Shooter()
        self.buttons = Buttons(BTN.values())
        self.auto_done = False

        self.shooter.aim(ANGLE_MID)
        self.safe_state()

    def safe_state(self):
        self.drive.stop()
        self.dc.all_off()
        self.shooter.spin(False)

    def _pressed(self, action):
        return self.buttons.pressed(BTN[action])

    def _held(self, action):
        return self.buttons.held(BTN[action])

    # ---- teleop ----
    def manual(self):
        self.buttons.update()

        forward = read_stick("Ly") * DRIVE_POWER / 100.0
        strafe = read_stick("Lx") * DRIVE_POWER / 100.0
        turn = read_stick("Rx") * TURN_POWER / 100.0

        if forward == 0 and strafe == 0 and turn == 0:
            self.drive.stop()
        else:
            self.drive.drive(forward, strafe, turn)

        if self._pressed("aim_up"):
            self.shooter.aim(ANGLE_UP)
        if self._pressed("aim_mid"):
            self.shooter.aim(ANGLE_MID)
        if self._pressed("aim_down"):
            self.shooter.aim(ANGLE_DOWN)

        if self._pressed("block_fwd"):
            self.dc.toggle_group("block", 1)
        if self._pressed("block_rev"):
            self.dc.toggle_group("block", -1)

        if self._pressed("midway_fwd"):
            self.dc.toggle("midway", 1)
        if self._pressed("midway_rev"):
            self.dc.toggle("midway", -1)

        if self._pressed("intake"):
            self.dc.toggle_group("intake", 1)

        if self._pressed("ball"):
            self.dc.toggle("ball", 1)

        if self._pressed("stop_all"):
            self.safe_state()

        self.shooter.spin(self._held("flywheel"))

    # ---- autonomous ----
    def auto(self, side):
        if self.auto_done:
            return

        # Mirror the sideways step depending on which side we start.
        side_sign = 1 if side == "L" else -1

        self.drive.drive(AUTO_FORWARD_POWER, 0, 0)
        time.sleep(AUTO_FORWARD_TIME)

        self.drive.drive(0, AUTO_SIDEWAY_POWER * side_sign, 0)
        time.sleep(AUTO_SIDEWAY_TIME)

        self.drive.stop()

        self.shooter.aim(ANGLE_UP)
        self.shooter.spin(True)
        time.sleep(AUTO_SPINUP_TIME)

        self.dc.set_group("block", 1)
        time.sleep(AUTO_FEED_TIME)

        self.dc.set_group("block", 0)
        self.shooter.spin(False)

        self.auto_done = True

    # ---- one tick ----
    def update(self):
        if power_manage_module.is_auto_mode() or DEBUG_AUTO:
            self.auto(AUTO_SIDE)
        else:
            if self.auto_done:
                self.auto_done = False
                self.safe_state()
            self.manual()


robot = Robot()

while True:
    robot.update()
    time.sleep(LOOP_PERIOD)
