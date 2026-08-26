# -*- coding: utf-8 -*-
"""Smart servo bench test -- pick any servo on M1..M6 / INDEX1..INDEX8 and
tilt it, home it, re-zero it, all from the PC keyboard or a gamepad:

    python scripts/Test_Servo.py COM6 [port] [index]

or pick it from `NovaPi: Run Script...`, which passes the configured COM port as
the first argument. The two optional arguments are the servo to start on, e.g.
`COM6 M5 INDEX2`.

    1..6        pick the port, M1..M6
    [ / ]       pick the index, INDEX1..INDEX8 (chained servos on one port)
    V           arm / disarm the servo (it starts DISARMED -- see below)
    Up/Down     move speed +/- SPEED_STEP, 1..50 rpm/min (hold to ramp)
    Left/Right  armed only: tilt -/+ ANGLE_STEP degrees
    H           armed only: send the servo home, to angle 0
    Z           armed only: make wherever the servo is right now the new zero
    ESC         quit (Ctrl-C works too)

    Gamepad: L1/R1 = port, L2/R2 = index, START = arm/disarm, D-pad Up/Down =
             speed, D-pad Left/Right = tilt, X = home, Y = set zero,
             BACK/Select = quit. Keyboard and gamepad work at the same time;
             neither one has to be present.

Speed here is the `speed` argument of the servo's own `move()` / `move_to()`,
1..50 rpm/min per the docs -- how fast it travels to the target, not an
open-loop power. Nothing in this script spins a servo continuously.

**The servo is read-only until you arm it.** Starting the script, and switching
to another servo, sends no angle at all: it stays exactly where it is, and the
script only reads the angle back and shows it. Nothing moves until V (or START)
is pressed, and **changing port or index disarms again**, so walking the 48
addresses looking for a servo can never move one on the way past. That matters
because the keys here are read from global key state, so an arrow key pressed in
the editor or the terminal counts as a tilt; leaving the servo disarmed unless
you are actually aiming it is what keeps stray keystrokes from walking an arm
out of range and into a stall (the red light on the servo).

The angle on screen is the one the **servo itself reports**, not a number this
script is keeping. Nothing here remembers a target: a tilt is sent as a relative
move, which the servo resolves from its own encoder, so the readout stays honest
after the arm is pushed by hand, after a stall, or after the servo is
back-driven.

Zero is the servo's own, set by Z and kept in the servo -- this script never
assumes where it is. H is the one control that goes to an absolute angle, so it
is only as safe as that zero: if 0 degrees is somewhere the arm cannot reach,
H drives it into the stop. Tilt does not have that problem.

`--` in the angle column means that address did not answer -- either nothing is
plugged in there, or the index is wrong. That is also how you find a servo: walk
the ports with 1..6 and the indexes with [ and ], disarmed, and watch for the
column to stop reading `--`.

**On exit the board goes back to running `/main.py`, and that program aims a
servo** -- `Guzzchan.__init__` calls `set_shooter_angle(ANGLE_HOME)`, an
absolute `move_to(0, 50)` on M5 INDEX1. So that servo can move once this script
has quit, and that move is main.py's, not this one's.

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

Keys are read with the Windows key-state API, the same way `Test_Shooter.py` and
`Test_DC.py` do it, so a held key really reads as held instead of waiting out
the OS auto-repeat delay. It also means keys register while another window has
focus: disarm before going off to type somewhere else. Off Windows the keyboard
half is simply inactive and the gamepad still drives the test.

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

ANGLE_STEP = 5      # degrees per tilt command
SPEED = 20          # starting move speed; the smartservo docs allow 1..50
SPEED_STEP = 1      # how much Up/Down change the move speed per tick
TILT_RATE = 0.15    # seconds between tilt commands while the key is held
POLL = 0.20         # seconds between angle reads when nothing else is asking

# Every address a smart servo can have: six motor ports, eight daisy-chained
# servos each. Keep the names literal -- the stubs check them.
PORTS = ['M%d' % n for n in range(1, 7)]
INDEXES = ['INDEX%d' % n for n in range(1, 9)]
DIGITS = tuple('%d' % n for n in range(1, 7))

# Board-side stand-in for "the servo did not answer": a reply is a string of
# digits or nothing at all, so there is no None to send back.
NO_ANGLE = -9999

# Virtual-key codes for GetAsyncKeyState (same table style as Test_DC.py).
# 0xDB and 0xDD are [ and ] on a US layout.
VK = {'UP': 0x26, 'DOWN': 0x28, 'LEFT': 0x25, 'RIGHT': 0x27,
      'H': 0x48, 'Z': 0x5A, 'V': 0x56, 'ESC': 0x1B, '[': 0xDB, ']': 0xDD}
VK.update((d, 0x30 + n) for n, d in enumerate(DIGITS, 1))

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
    from mbuild.smartservo import smartservo_class

    # Built as they are asked for and then kept, rather than making all 48 up
    # front: most addresses have nothing on them, and the one being tested gets
    # reused every tick.
    servos = {}

    def pick(port, index):
        key = port + index
        if key not in servos:
            servos[key] = smartservo_class(port, index)
        return servos[key]

    def angle(servo):
        """Degrees the servo itself reports, whole numbers -- -9999 when it does
        not answer. An empty address must not take the command down with it:
        walking the ports to find a servo means asking mostly empty ones."""
        try:
            measured = servo.get_value('angle')
        except Exception:
            return -9999
        if measured is None:
            return -9999
        return int(measured)

    def report(port, index):
        """Just the angle: what the PC polls between commands."""
        online_debug_respond('%d' % angle(pick(port, index)))

    def tilt(port, index, delta, speed):
        """Relative move, so the servo works the target out from its own
        position. This is what keeps the readout true after the arm has been
        moved by hand."""
        servo = pick(port, index)
        servo.move(delta, speed)
        online_debug_respond('%d' % angle(servo))

    def aim(port, index, position, speed):
        """Absolute move, measured from whatever zero() last set."""
        servo = pick(port, index)
        servo.move_to(position, speed)
        online_debug_respond('%d' % angle(servo))

    def zero(port, index):
        """Make the servo's current physical position the new 0 degrees.

        Replies 'before,after': the same read taken either side of set_zero(),
        with a settle in between, because the servo answers over its own bus and
        the reading does not turn over the instant set_zero() returns.

        If 'after' does not come back near 0 the servo is not re-referencing
        get_value('angle'), i.e. the reading is raw position and only move_to()
        sees the new zero. That is worth seeing rather than guessing at.
        """
        servo = pick(port, index)
        before = angle(servo)
        servo.set_zero()
        time.sleep(0.15)
        online_debug_respond('%d,%d' % (before, angle(servo)))


# ------------------------------------------------------------------- PC side --

def main():
    if len(sys.argv) < 2:
        sys.exit('Usage: %s <port> [M1..M6] [INDEX1..INDEX8]   (e.g. COM6 M5 INDEX2)'
                 % os.path.basename(sys.argv[0]))

    port = 0
    index = 0
    if len(sys.argv) > 2:
        wanted = sys.argv[2].upper()
        if wanted not in PORTS:
            sys.exit('Unknown port %r -- pick one of %s'
                     % (sys.argv[2], ', '.join(PORTS)))
        port = PORTS.index(wanted)
    if len(sys.argv) > 3:
        wanted = sys.argv[3].upper()
        if wanted not in INDEXES:
            sys.exit('Unknown index %r -- pick one of %s'
                     % (sys.argv[3], ', '.join(INDEXES)))
        index = INDEXES.index(wanted)

    board = Live(sys.argv[1])
    board.mode(MODE_LIVE)                   # stops /main.py
    try:
        board.define(board_code)            # ships the function above
    except IOError as exc:
        board.mode(MODE_RUN)
        board.close()
        sys.exit(str(exc))

    print('servo test on %s (starting at %s %s)'
          % (sys.argv[1], PORTS[port], INDEXES[index]))
    print('1-6 = port M1..M6, [ ] = index INDEX1..INDEX8,')
    print('V = arm/disarm, Up/Down = move speed 1..50,')
    print('armed: Left/Right = tilt, H = home to 0, Z = set zero here')
    print('ESC or Ctrl-C = quit')
    print('gamepad: L1/R1 = port, L2/R2 = index, START = arm/disarm,')
    print('         D-pad Up/Down = speed, D-pad Left/Right = tilt,')
    print('         X = home, Y = set zero, BACK/Select = quit')
    print('no servo is commanded at startup, and changing port or index disarms:')
    print('this only reads the angle back until you arm it.')
    if _user32 is None:
        print('not on Windows: keyboard control is off, gamepad only')
    elif not gamepad.is_connected():
        print('no controller found; the keyboard drives this (plug one in any time)')

    speed = SPEED
    measured = None                         # last angle the SERVO reported
    armed = False                           # servo moves are opt-in; see below
    tilted_at = 0.0                         # rate limits held tilt keys
    polled_at = 0.0                         # rate limits idle angle reads
    got = 'nothing yet'                     # last reply, kept between commands
    was = None
    try:
        while True:
            if down('ESC') or gamepad.is_key_pressed('Select'):
                break

            # Edge-triggered: these change state, so only act on the press. The
            # two input sources are OR'd first, so either one works and holding
            # a key or a button down does not retrigger.
            now = {'arm': down('V') or gamepad.is_key_pressed('Start'),
                   'home': down('H') or gamepad.is_key_pressed('N3'),        # X
                   'zero': down('Z') or gamepad.is_key_pressed('N4'),        # Y
                   'index-': down('[') or gamepad.is_key_pressed('L2'),
                   'index+': down(']') or gamepad.is_key_pressed('R2'),
                   'port-': gamepad.is_key_pressed('L1'),
                   'port+': gamepad.is_key_pressed('R1')}
            now.update((d, down(d)) for d in DIGITS)
            if was is None:
                # First pass: anything held right now was already held before
                # this script started -- the keystroke that launched it, or a
                # key being used in another window. Not a press.
                was = now
            edge = dict((k, v and not was[k]) for k, v in now.items())
            was = now

            # --- which servo ----------------------------------------------
            switched = False
            for n, digit in enumerate(DIGITS):
                if edge[digit] and n != port:
                    port = n
                    switched = True
                    break
            if edge['port-'] or edge['port+']:
                port = (port + (1 if edge['port+'] else -1)) % len(PORTS)
                switched = True
            if edge['index-'] or edge['index+']:
                index = (index + (1 if edge['index+'] else -1)) % len(INDEXES)
                switched = True
            if switched:
                # Disarm, because the address just changed under the arrow keys
                # and the next tilt would go somewhere the last one did not.
                # Blank the angle too: the old one belongs to the old servo, and
                # the poll below refills it within one tick.
                armed = False
                measured = None
                polled_at = 0.0

            # --- speed ------------------------------------------------------
            # Not a servo command on its own: it is the argument the next move
            # carries, so it can be set while disarmed.
            if down('UP') or gamepad.is_key_pressed('Up'):
                speed = min(50, speed + SPEED_STEP)
            elif down('DOWN') or gamepad.is_key_pressed('Down'):
                speed = max(1, speed - SPEED_STEP)

            # --- servo ------------------------------------------------------
            # Disarmed is the resting state, including at startup: no move
            # command of any kind is built, so the servo holds whatever position
            # it is already in and the angle below is purely a read.
            if edge['arm']:
                armed = not armed

            where = '%r,%r' % (PORTS[port], INDEXES[index])

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

            cmd = None
            if armed:
                if edge['zero']:
                    cmd = 'zero(%s)' % where
                elif edge['home']:
                    cmd = 'aim(%s,0,%d)' % (where, speed)
                elif tilt and time.time() - tilted_at >= TILT_RATE:
                    tilted_at = time.time()
                    cmd = 'tilt(%s,%d,%d)' % (where, tilt, speed)
            if cmd is None and time.time() - polled_at >= POLL:
                # Nothing is moving, so nothing else is asking the servo where
                # it is. Poll it, or the angle would sit frozen on screen while
                # somebody moves the arm by hand.
                polled_at = time.time()
                cmd = 'report(%s)' % where

            # Most ticks send nothing at all -- the poll is slower than the
            # loop -- so `got` is left showing the last reply rather than
            # blinking between a number and an idle marker.
            if cmd:
                reply = board.run(cmd, timeout=2.0, retries=0)
                measured = angle_of(reply, measured)
                got = reply if reply else 'no reply'
                if cmd.startswith('zero('):
                    # A whole line, not the \r status line: set_zero happens
                    # once and its before/after is the thing you came to read.
                    print('\nset_zero %s %s -> before,after = %s'
                          % (PORTS[port], INDEXES[index],
                             reply if reply else 'no reply from the servo'))
            else:
                time.sleep(0.02)

            if armed:
                state = 'ARMED'
            elif asked:
                state = 'press V to arm'    # a control was used; say why nothing moved
            else:
                state = '(read-only)'
            print('\r' + ('%s %-6s  %s deg  speed %2d  %-15s %-5s board says %s' % (
                PORTS[port], INDEXES[index],
                '  --' if measured is None else '%4d' % measured,
                speed, state,
                'pad' if gamepad.is_connected() else 'nopad', got)).ljust(100)[:100],
                end='')
    except KeyboardInterrupt:
        pass
    finally:
        # Hand the board back and release the port. There is nothing to stop:
        # this script never leaves a servo running, and the one it was testing
        # is left where it is on purpose -- a blind move home on the way out
        # could drive an arm into something.
        board.mode(MODE_RUN)                # restarts /main.py
        board.close()
        print('\nstopped; board back in run mode.')


if __name__ == '__main__':
    main()
