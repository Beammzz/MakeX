# -*- coding: utf-8 -*-
"""Shooter bench test -- the two brushless flywheels plus the M5 aim servo,
driven from the PC keyboard or a gamepad:

    python scripts/Test_Shooter.py COM6

or pick it from `NovaPi: Run Script...`, which passes the configured COM port as
the first argument.

    1 / 2       pick BL1 / BL2 -- the one Up/Down edits; the other keeps its own
    Up/Down     picked motor power +/- STEP (hold to ramp), 0..100
    SPACE       start / stop
    R           picked motor back to 0
    0           both motors back to 0
    V           arm / disarm the servo (it starts DISARMED -- see below)
    Left/Right  armed only: tilt the M5 servo -/+ ANGLE_STEP degrees
    H           armed only: send the servo home, to angle 0
    Z           armed only: make wherever the servo is right now the new zero
    ESC         quit (Ctrl-C works too)

    Gamepad: A = start/stop, RT/LT = BL1, R1/L1 = BL2, B = both to 0,
             START = arm/disarm the servo, then D-pad Left/Right = tilt,
             X = home, Y = set zero, BACK/Select = quit. Keyboard and gamepad
             work at the same time; neither one has to be present.

**The servo is read-only until you arm it.** Starting the script sends it no
angle at all: it stays exactly where it is, and the script only reads the angle
back and shows it. Nothing moves the servo until V (or START) is pressed, and
disarming it stops there too -- no move on the way out. That matters because the
keys here are read from global key state, so an arrow key pressed in the editor
or the terminal counts as a tilt; leaving the servo disarmed unless you are
actually aiming it is what keeps stray keystrokes from walking the arm out of
range and into a stall (the red light on the servo).

The angle on screen is the one the **servo itself reports**, not a number this
script is keeping. Nothing here remembers a target: a tilt is sent as a relative
move, which the servo resolves from its own encoder, so the readout stays honest
after the arm is pushed by hand, after a stall, or after the servo is back-driven
by a ball.

Zero is the servo's own, set by Z and kept in the servo -- this script never
assumes where it is. H is the one control that goes to an absolute angle, so it
is only as safe as that zero: if 0 degrees is somewhere the arm cannot reach,
H drives it into the stop. Tilt does not have that problem.

`--` in the angle column means the servo did not answer: check M5 is plugged in
and powered.

**On exit the board goes back to running `/main.py`, and that program aims the
servo** -- `Guzzchan.__init__` calls `shooter.aim_mid()`, an absolute
`move_to(0, 300)`. So the servo can move once this script has quit, and that
move is main.py's, not this one's.

Two halves:

    board_code()   ordinary Python that runs ON THE BOARD. Sent once at
                   startup by board.define(); its imports, variables and
                   functions become board-side globals.
    main()         runs on the PC. Reads the keyboard and the gamepad and calls
                   the functions board_code() defined, one at a time, over the
                   radio.

Live mode **stops `/main.py`** while this runs and restarts it from the top on
exit, so this script owns the board. Commands run one at a time, in order, and a
snippet that raises returns nothing -- check the USB console if a command
silently does nothing.

Keys are read with the Windows key-state API, the same way `teleop.py` and
`Test_DC.py` do it, so a held key really reads as held instead of waiting out
the OS auto-repeat delay. It also means keys register while another window has
focus: stop the motors before going off to type somewhere else. Off Windows the
keyboard half is simply inactive and the gamepad still drives the test.

`live` and `pc_gamepad` live in the extension's `scripts/` folder, not next to
this file; `_bootstrap()` puts that folder on `sys.path`. Set `NOVAPI_SCRIPTS`
if the extension repo is not the sibling `../NovaPi`.
"""
import ctypes
import os
import sys
import time


def _bootstrap():
    """Make the extension's scripts/ folder importable (see the docstring)."""
    here = os.path.dirname(os.path.abspath(__file__))
    scripts = os.environ.get('NOVAPI_SCRIPTS') or os.path.abspath(
        os.path.join(here, '..', '..', 'NovaPi', 'scripts'))
    if not os.path.isfile(os.path.join(scripts, 'live.py')):
        sys.exit('Could not find the NovaPi helper scripts in %s\n'
                 'Set NOVAPI_SCRIPTS to the extension\'s scripts folder.' % scripts)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)


_bootstrap()

import pc_gamepad as gamepad                    # noqa: E402  (needs sys.path first)
from live import (Live, MODE_LIVE, MODE_RUN,    # noqa: E402
                  online_debug_respond)         # board builtin; see live.py

PULSE = 0.25        # seconds a command holds before the board stops the motor
STEP = 1            # how much the controls change power per tick, 0..100

# The aim servo. main.py's Shooter drives the same one, so keep the port here in
# step with it.
SERVO_PORT = 'M5'
ANGLE_STEP = 5      # degrees per tilt command
SERVO_SPEED = 20    # rpm/min; the smartservo docs allow 1..50
TILT_RATE = 0.15    # seconds between tilt commands while the key is held
POLL = 0.20         # seconds between angle reads while the flywheels are off

# Board-side stand-in for "the servo did not answer": a reply is a string of
# digits or nothing at all, so there is no None to send back.
NO_ANGLE = -9999

# The two dedicated brushless outputs, in the order the cursor walks them.
MOTORS = ['BL1', 'BL2']

# Virtual-key codes for GetAsyncKeyState (same table style as Test_DC.py).
VK = {'UP': 0x26, 'DOWN': 0x28, 'LEFT': 0x25, 'RIGHT': 0x27,
      'SPACE': 0x20, 'R': 0x52, 'H': 0x48, 'Z': 0x5A, 'V': 0x56, 'ESC': 0x1B,
      '0': 0x30, '1': 0x31, '2': 0x32}

_user32 = ctypes.windll.user32 if sys.platform == 'win32' else None


def down(key):
    """True while `key` is held. Always False where there is no key-state API,
    so a gamepad-only run on another platform still works."""
    if _user32 is None:
        return False
    return bool(_user32.GetAsyncKeyState(VK[key]) & 0x8000)


def angle_of(reply, previous):
    """Pull the servo angle out of a board reply -- it is always the last
    comma-separated field. Keeps `previous` when the reply is missing or
    malformed, so one lost frame does not blank the readout."""
    if not reply:
        return previous
    try:
        measured = int(reply.split(',')[-1])
    except ValueError:
        return previous
    return None if measured == NO_ANGLE else measured


# ---------------------------------------------------------------- board side --

def board_code():
    """Runs on the BOARD, not here. Everything it defines stays available.

    Write it like any other Python file -- autocomplete and error checking work
    the same. Just keep in mind it executes on a NovaPi: no threads, and only
    the modules the firmware has.
    """
    import time
    from mbuild import power_expand_board
    from mbuild.smartservo import smartservo_class

    # The board has two dedicated brushless outputs, BL1 and BL2; 'DC1'..'DC8'
    # are the H-bridge DC channels and are the wrong shape of signal for an ESC.
    # Keep the channel names literal: the stubs check them.
    servo = smartservo_class('M5', 'INDEX1')

    def angle():
        """Degrees the servo itself reports, whole numbers -- -9999 when it does
        not answer. An unplugged M5 must not take the whole command down with
        it: the flywheel half of this test still works without the servo."""
        try:
            measured = servo.get_value('angle')
        except Exception:
            return -9999
        if measured is None:
            return -9999
        return int(measured)

    def stop():
        power_expand_board.set_power('BL1', 0)
        power_expand_board.set_power('BL2', 0)

    def report():
        """Just the angle: what the PC polls while the flywheels are idle."""
        online_debug_respond('%d' % angle())

    def tilt(delta, speed):
        """Relative move, so the servo works the target out from its own
        position. This is what keeps the readout true after the arm has been
        moved by hand or shoved by a ball."""
        servo.move(delta, speed)
        online_debug_respond('%d' % angle())

    def aim(position, speed):
        """Absolute move, measured from whatever zero() last set."""
        servo.move_to(position, speed)
        online_debug_respond('%d' % angle())

    def zero():
        """Make the servo's current physical position the new 0 degrees.

        Replies 'before,after': the same read taken either side of set_zero(),
        with a settle in between, because the servo answers the PC over its own
        bus and the reading does not turn over the instant set_zero() returns.

        If 'after' does not come back near 0 the servo is not re-referencing
        get_value('angle'), i.e. the reading is raw position and only move_to()
        sees the new zero. That is worth seeing rather than guessing at.
        """
        before = angle()
        servo.set_zero()
        time.sleep(0.15)
        online_debug_respond('%d,%d' % (before, angle()))

    def spin(left_power, right_power, seconds):
        """Set both motors, hold for `seconds`, then stop."""
        power_expand_board.set_power('BL1', left_power)
        power_expand_board.set_power('BL2', right_power)
        online_debug_respond('%d,%d,%d' % (left_power, right_power, angle()))
        time.sleep(seconds)
        stop()

    # TODO: if the ESC needs an arming ramp, do it here -- this runs once.


# ------------------------------------------------------------------- PC side --

def main():
    if len(sys.argv) < 2:
        sys.exit('Usage: %s <port>   (e.g. COM6)' % os.path.basename(sys.argv[0]))

    board = Live(sys.argv[1])
    board.mode(MODE_LIVE)                   # stops /main.py
    try:
        board.define(board_code)            # ships the function above
    except IOError as exc:
        board.mode(MODE_RUN)
        board.close()
        sys.exit(str(exc))

    print('shooter test on %s (flywheels BL1/BL2, aim servo %s)'
          % (sys.argv[1], SERVO_PORT))
    print('1/2 = pick BL1/BL2, Up/Down = its power, SPACE = start/stop,')
    print('R = picked motor to 0, 0 = both to 0,')
    print('V = arm/disarm servo; armed: Left/Right = tilt, H = home to 0,')
    print('    Z = set zero here')
    print('ESC or Ctrl-C = quit')
    print('gamepad: A = start/stop, RT/LT = BL1, R1/L1 = BL2, B = both to 0,')
    print('         START = arm/disarm servo, D-pad Left/Right = tilt,')
    print('         X = home, Y = set zero, BACK/Select = quit')
    print('the servo is NOT commanded at startup: it holds its position and')
    print('this only reads the angle back until you arm it.')
    if _user32 is None:
        print('not on Windows: keyboard control is off, gamepad only')
    elif not gamepad.is_connected():
        print('no controller found; the keyboard drives this (plug one in any time)')

    powers = [0, 0]                         # BL1, BL2
    index = 0                               # the one Up/Down edits
    running = False
    measured = None                         # last angle the SERVO reported
    armed = False                           # servo moves are opt-in; see below
    tilted_at = 0.0                         # rate limits held tilt keys
    polled_at = 0.0                         # rate limits idle angle reads
    was = None
    try:
        while True:
            if down('ESC') or gamepad.is_key_pressed('Select'):
                break

            # Edge-triggered: these change state, so only act on the press. The
            # two input sources are OR'd first, so either one works and holding
            # a key or a button down does not retrigger.
            now = {'toggle': down('SPACE') or gamepad.is_key_pressed('N1'),   # A
                   'arm': down('V') or gamepad.is_key_pressed('Start'),
                   'home': down('H') or gamepad.is_key_pressed('N3'),         # X
                   'zero': down('Z') or gamepad.is_key_pressed('N4'),         # Y
                   '1': down('1'), '2': down('2')}
            if was is None:
                # First pass: anything held right now was already held before
                # this script started -- the keystroke that launched it, or a
                # key being used in another window. Not a press.
                was = now
            edge = dict((k, v and not was[k]) for k, v in now.items())
            was = now

            if down('0') or gamepad.is_key_pressed('N2'):       # B
                powers[0] = 0
                powers[1] = 0
            elif down('R'):
                powers[index] = 0

            # The keyboard edits the picked motor; the gamepad keeps a control
            # per motor, so both motors stay live on it at once.
            if down('UP'):
                powers[index] = min(100, powers[index] + STEP)
            elif down('DOWN'):
                powers[index] = max(0, powers[index] - STEP)

            if gamepad.is_key_pressed('R2'):        # right trigger
                powers[0] = min(100, powers[0] + STEP)
            elif gamepad.is_key_pressed('L2'):      # left trigger
                powers[0] = max(0, powers[0] - STEP)

            if gamepad.is_key_pressed('R1'):        # right shoulder
                powers[1] = min(100, powers[1] + STEP)
            elif gamepad.is_key_pressed('L1'):      # left shoulder
                powers[1] = max(0, powers[1] - STEP)

            for n, digit in enumerate(('1', '2')):
                if edge[digit]:
                    index = n           # moves the cursor only: the motor
                    break               # left behind keeps its own power

            if edge['toggle']:
                running = not running
                if not running:
                    board.run('stop()', reply=False)

            # --- servo ---------------------------------------------------
            # Disarmed is the resting state, including at startup: no move
            # command of any kind is built, so the servo holds whatever
            # position it is already in and the angle below is purely a read.
            if edge['arm']:
                armed = not armed

            # One command at most per tick, and every one of them answers with
            # the measured angle, so the same round trip that moves the servo
            # refreshes the readout.
            tilt = 0
            if down('LEFT') or gamepad.is_key_pressed('Left'):
                tilt = -ANGLE_STEP
            elif down('RIGHT') or gamepad.is_key_pressed('Right'):
                tilt = ANGLE_STEP
            # Read the servo controls even while disarmed, so asking for one can
            # be answered with "it is disarmed" instead of with silence.
            asked = bool(tilt) or edge['home'] or edge['zero']

            servo_cmd = None
            if armed:
                if edge['zero']:
                    servo_cmd = 'zero()'
                elif edge['home']:
                    servo_cmd = 'aim(0,%d)' % SERVO_SPEED
                elif tilt and time.time() - tilted_at >= TILT_RATE:
                    tilted_at = time.time()
                    servo_cmd = 'tilt(%d,%d)' % (tilt, SERVO_SPEED)
            if servo_cmd:
                reply = board.run(servo_cmd, timeout=2.0, retries=0)
                measured = angle_of(reply, measured)
                if servo_cmd == 'zero()':
                    # A whole line, not the \r status line: set_zero happens
                    # once and its before/after is the thing you came to read.
                    print('\nset_zero -> before,after = %s'
                          % (reply if reply else 'no reply from the servo'))

            if running:
                # The reply is the flow control: the board answers at the START
                # of its pulse, so this blocks until that pulse is under way and
                # the send rate can never outrun the board.
                got = board.run('spin(%d,%d,%r)' % (powers[0], powers[1], PULSE),
                                timeout=PULSE + 1.0, retries=0)
                measured = angle_of(got, measured)
            else:
                got = 'stopped'
                if time.time() - polled_at >= POLL:
                    # Nothing is spinning, so nothing else is asking the servo
                    # where it is. Poll it, or the angle would sit frozen on
                    # screen while somebody moves the arm by hand.
                    polled_at = time.time()
                    measured = angle_of(
                        board.run('report()', timeout=2.0, retries=0), measured)
                time.sleep(0.05)

            # The cursor marks the motor Up/Down edits; both always show, there
            # being only the two of them. The angle is the board's, never ours.
            shown = '  '.join('%s%s %3d' % ('>' if n == index else ' ', m, powers[n])
                              for n, m in enumerate(MOTORS))
            if armed:
                state = 'ARMED'
            elif asked:
                state = 'press V to arm'    # a control was used; say why nothing moved
            else:
                state = '(read-only)'
            print('\r%s  servo %s deg %-15s %-7s %s board says %-12s' % (
                shown,
                '  --' if measured is None else '%4d' % measured,
                state, 'run' if running else 'stop',
                'pad' if gamepad.is_connected() else 'nopad', got),
                end='')

            # TODO: read something back to compare against the setting, e.g.
            #   print(board.run("online_debug_respond(novapi.get_battery())"))
    except KeyboardInterrupt:
        pass
    finally:
        # Always: stop the hardware, hand the board back, release the port. The
        # servo is left where it is on purpose -- it holds the aim, and a blind
        # move home on the way out could drive the arm into something.
        board.run('stop()', reply=False)
        time.sleep(0.1)
        board.mode(MODE_RUN)                # restarts /main.py
        board.close()
        print('\nstopped; board back in run mode.')


if __name__ == '__main__':
    main()
