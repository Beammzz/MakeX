# -*- coding: utf-8 -*-
"""Encoder motor (wheel) bench test, driven from the PC keyboard:

    python scripts/Test_Encoder.py COM6 [power|speed]

or pick it from `NovaPi: Run Script…`, which passes the configured COM port as
the first argument. The optional second argument is the mode to start in.

    1..4      pick M1..M4 -- the one Up/Down edits; the others keep theirs
    Up/Down   picked value +/- STEP (hold to ramp; goes negative to reverse)
    A         copy the picked value to all four wheels
    M         switch set_power <-> set_speed; both modes zero on the way over
    SPACE     start / stop -- every wheel, including the ones sitting at 0
    R         picked wheel to 0        0   every wheel to 0
    Z         make the angles read 0 from here
    ESC       quit (Ctrl-C works too)

The two modes are the two ways `encoder_motor` takes a command, and the table
shows what each one actually gets you:

    POWER   set_power(-100..100), open loop. Raw pwm; the speed column is
            whatever that pwm produces, so it sags under load and differs
            wheel to wheel. This is what main.py's `Wheel` uses.
    SPEED   set_speed(rpm), closed loop. The motor holds the rpm you asked
            for and the speed column should settle on the commanded number --
            a wheel that cannot get there is geared, loaded or broken.

Both columns are read straight off the encoders, all four wheels every round
trip, so the table is also the encoder test: with SPACE off the script keeps
polling, and turning a wheel by hand has to move its speed and angle. A wheel
whose numbers never move has a dead encoder or a dead port -- and a wheel whose
speed reads backwards is a reversed motor, which in main.py is a sign in the
power table, not a wiring job.

The speed shown is measured, so it trails the command by about one pulse: it is
the wheel's real speed at the moment the board answered, not the number just
sent.

Two halves:

    board_code()   ordinary Python that runs ON THE BOARD. Sent once at
                   startup by board.define(); its imports, variables and
                   functions become board-side globals.
    main()         runs on the PC. Reads the keyboard and calls the functions
                   board_code() defined, one at a time, over the radio.

Live mode **stops `/main.py`** while this runs and restarts it from the top on
exit, so this script owns the board. Commands run one at a time, in order, and a
snippet that raises returns nothing -- check the USB console if a command
silently does nothing.

Keys are read with the Windows key-state API, the same way `Test_DC.py` does it,
so a held key really reads as held instead of waiting out the OS auto-repeat
delay. It also means keys register while another window has focus: stop the
wheels before going off to type somewhere else.

`live` lives in the extension's `scripts/` folder, not next to this file;
`_bootstrap()` puts that folder on `sys.path`. Set `NOVAPI_SCRIPTS` if the
extension repo is not the sibling `../NovaPi`.
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

from live import (Live, MODE_LIVE, MODE_RUN,    # noqa: E402  (needs sys.path first)
                  online_debug_respond)         # board builtin; see live.py

PULSE = 0.25        # seconds a drive command holds before the board stops the wheels
POWER_STEP = 5      # how much Up/Down change power per tick, -100..100
SPEED_STEP = 10     # how much Up/Down change target speed per tick, rpm
SPEED_MAX = 200     # rpm; the docs leave set_speed open-ended, this is a bench cap
POLL = 0.15         # seconds between reads while nothing is being driven

# M1 upper-left, M2 lower-left, M3 upper-right, M4 lower-right -- the four
# wheels `Wheel` drives in main.py, in the order it builds them.
MOTORS = (('M1', 'UL'), ('M2', 'LL'), ('M3', 'UR'), ('M4', 'LR'))
DIGITS = tuple('%d' % n for n in range(1, len(MOTORS) + 1))

# Board-side stand-in for "the motor did not answer": a reply is digits and
# separators, so there is no None to send back.
NO_VALUE = -99999

# Virtual-key codes for GetAsyncKeyState (same table style as Test_DC.py).
VK = {'UP': 0x26, 'DOWN': 0x28, 'SPACE': 0x20, 'A': 0x41, 'M': 0x4D,
      'R': 0x52, 'Z': 0x5A, 'ESC': 0x1B, '0': 0x30}
VK.update((d, 0x30 + n) for n, d in enumerate(DIGITS, 1))

_user32 = ctypes.windll.user32 if sys.platform == 'win32' else None


def down(key):
    return bool(_user32.GetAsyncKeyState(VK[key]) & 0x8000)


def enable_ansi():
    """Turn on VT processing so the table can redraw over itself. False when the
    console will not do it, or output is redirected to a file, and the display
    falls back to the single line the other test scripts use."""
    if _user32 is None:
        return True                     # other terminals already speak ANSI
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11)             # STD_OUTPUT_HANDLE
    mode = ctypes.c_uint32()
    if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        return False
    return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))


def readings_of(reply, previous):
    """Pull 'speed,angle;speed,angle;...' out of a board reply, one pair per
    motor. Keeps `previous` when the reply is missing or malformed, so one lost
    frame does not blank the whole table."""
    if not reply:
        return previous
    fields = reply.split(';')
    if len(fields) != len(MOTORS):
        return previous
    pairs = []
    for field in fields:
        try:
            speed, angle = [int(v) for v in field.split(',')]
        except ValueError:
            return previous
        pairs.append((None if speed == NO_VALUE else speed,
                      None if angle == NO_VALUE else angle))
    return pairs


# ---------------------------------------------------------------- board side --

def board_code():
    """Runs on the BOARD, not here. Everything it defines stays available.

    Write it like any other Python file -- autocomplete and error checking work
    the same. Just keep in mind it executes on a NovaPi: no threads, and only
    the modules the firmware has.
    """
    import time
    from mbuild.encoder_motor import encoder_motor_class

    # M1 upper-left, M2 lower-left, M3 upper-right, M4 lower-right.
    motors = [encoder_motor_class('M1', 'INDEX1'), encoder_motor_class('M2', 'INDEX1'),
              encoder_motor_class('M3', 'INDEX1'), encoder_motor_class('M4', 'INDEX1')]

    # Subtracted from the raw angles. The encoder motor has no set_zero(), so
    # "zero it here" is arithmetic on this side, not a command to the motor.
    zeros = [0, 0, 0, 0]

    def read(motor, what):
        """Whole numbers off the encoder -- -99999 when the motor does not
        answer, so an empty port reads as blank instead of taking the whole
        command down with it and stopping the wheels that do work."""
        try:
            value = motor.get_value(what)
        except Exception:
            return -99999
        if value is None:
            return -99999
        return int(value)

    def telemetry():
        """'speed,angle' per motor, semicolon separated; angles measured from
        the last zero()."""
        out = []
        for i in range(4):
            speed = read(motors[i], 'speed')
            angle = read(motors[i], 'angle')
            if angle != -99999:
                angle -= zeros[i]
            out.append('%d,%d' % (speed, angle))
        return ';'.join(out)

    def stop():
        for m in motors:
            m.stop()

    def report():
        """Read only: what the PC polls while nothing is being driven. Turning a
        wheel by hand moves these numbers, which is the encoder test itself."""
        online_debug_respond(telemetry())

    def zero():
        """Take the angles as they stand right now to be 0."""
        for i in range(4):
            angle = read(motors[i], 'angle')
            zeros[i] = 0 if angle == -99999 else angle
        online_debug_respond(telemetry())

    def drive(values, closed_loop, seconds):
        """Set every wheel, hold for `seconds`, then stop -- so the command is
        its own deadman: a crashed PC, a yanked dongle or a closed laptop stops
        the wheels within one pulse. Don't remove the stop.

        `closed_loop` picks how `values` are read: set_speed() takes rpm and the
        motor's own loop holds it, set_power() takes raw pwm and gets whatever
        speed that is worth. The reply is measured either way, so it is the
        speed the wheels are doing now -- one pulse behind the values just set.
        """
        for i in range(4):
            if closed_loop:
                motors[i].set_speed(values[i])
            else:
                motors[i].set_power(values[i])
        online_debug_respond(telemetry())   # reply FIRST, so the PC's next
        time.sleep(seconds)                 # command queues while this pulse
        stop()                              # is still running


# ------------------------------------------------------------------- PC side --

def show(lines, ansi, first):
    """Redraw the table in place: the cursor walks back up over the block
    printed last tick. Without ANSI everything collapses onto the single \\r
    status line the other test scripts use."""
    if not ansi:
        sys.stdout.write('\r' + ' '.join(t.strip() for t in lines[2:]).ljust(110)[:110])
        sys.stdout.flush()
        return
    if not first:
        sys.stdout.write('\033[%dA' % len(lines))
    for text in lines:
        sys.stdout.write('\r\033[K' + text + '\n')
    sys.stdout.flush()


def main():
    if _user32 is None:
        sys.exit('Test_Encoder.py uses the Windows key-state API.')
    if len(sys.argv) < 2:
        sys.exit('Usage: %s <port> [power|speed]   (e.g. COM6 speed)'
                 % os.path.basename(sys.argv[0]))

    closed_loop = False
    if len(sys.argv) > 2:
        wanted = sys.argv[2].lower()
        if wanted not in ('power', 'speed'):
            sys.exit('Unknown mode %r -- pick power or speed' % sys.argv[2])
        closed_loop = wanted == 'speed'

    board = Live(sys.argv[1])
    board.mode(MODE_LIVE)                   # stops /main.py
    try:
        board.define(board_code)            # ships the function above
    except IOError as exc:
        board.mode(MODE_RUN)
        board.close()
        sys.exit(str(exc))

    print('encoder motor test on %s' % sys.argv[1])
    print('1-4 = pick wheel, Up/Down = its value, A = copy it to all,')
    print('M = set_power/set_speed, SPACE = start/stop, R = picked to 0, 0 = all to 0,')
    print('Z = zero the angles, ESC or Ctrl-C = quit')
    print('stopped is not idle: it keeps reading, so turn a wheel by hand to test it.')
    ansi = enable_ansi()

    index = 0
    values = [0] * len(MOTORS)                  # what each wheel is being asked for
    running = False
    readings = [(None, None)] * len(MOTORS)     # last speed,angle the BOARD reported
    link = 'nothing yet'
    polled_at = 0.0
    was = None
    first = True
    try:
        while True:
            if down('ESC'):
                break

            # Edge-triggered: these change state, so only act on the press.
            now = dict((key, down(key)) for key in ('SPACE', 'A', 'M', 'Z', '0'))
            now.update((d, down(d)) for d in DIGITS)
            if was is None:
                # First pass: anything held right now was already held before
                # this script started -- the keystroke that launched it, or a
                # key being used in another window. Not a press.
                was = now
            edge = dict((k, v and not was[k]) for k, v in now.items())
            was = now

            limit = SPEED_MAX if closed_loop else 100
            step = SPEED_STEP if closed_loop else POWER_STEP

            if down('R'):
                values[index] = 0
            elif down('UP'):
                values[index] = min(limit, values[index] + step)
            elif down('DOWN'):
                values[index] = max(-limit, values[index] - step)

            for n, digit in enumerate(DIGITS):
                if edge[digit]:
                    index = n           # moves the cursor only: the wheel left
                    break               # behind keeps its own value

            if edge['A']:
                values = [values[index]] * len(MOTORS)
            if edge['0']:
                values = [0] * len(MOTORS)

            if edge['M']:
                # Zero everything on the way over: 30 pwm and 30 rpm are not the
                # same command, and a wheel must not carry one number into the
                # other mode's meaning.
                closed_loop = not closed_loop
                values = [0] * len(MOTORS)
                running = False
                board.run('stop()', reply=False)

            if edge['SPACE']:
                running = not running
                if not running:
                    board.run('stop()', reply=False)

            # One command per tick at most. Zeroing wins the tick it is pressed:
            # the wheels coast through that one pulse, which is what the deadman
            # in drive() is there for.
            if edge['Z']:
                cmd = 'zero()'
            elif running:
                # The reply is the flow control: the board answers at the START
                # of its pulse, so this blocks until that pulse is under way and
                # the send rate can never outrun the board.
                cmd = 'drive(%r,%d,%r)' % (values, 1 if closed_loop else 0, PULSE)
            elif time.time() - polled_at >= POLL:
                polled_at = time.time()
                cmd = 'report()'
            else:
                cmd = None

            if cmd:
                reply = board.run(cmd, timeout=PULSE + 1.0, retries=0)
                readings = readings_of(reply, readings)
                link = 'ok' if reply else 'no reply'
            else:
                time.sleep(0.02)

            unit = 'rpm' if closed_loop else 'pwm'
            lines = ['  mode %-5s (%-20s)  %-8s  link %s'
                     % ('SPEED' if closed_loop else 'POWER',
                        'set_speed, rpm' if closed_loop else 'set_power -100..100',
                        'RUNNING' if running else 'stopped', link),
                     '     wheel      asked     speed        angle']
            for n, (port, corner) in enumerate(MOTORS):
                speed, angle = readings[n]
                lines.append('   %s %s %s %10s %9s rpm %8s deg'
                             % ('>' if n == index else ' ', port, corner,
                                '%+d %s' % (values[n], unit),
                                '--' if speed is None else '%d' % speed,
                                '--' if angle is None else '%d' % angle))
            show(lines, ansi, first)
            first = False
    except KeyboardInterrupt:
        pass
    finally:
        # Always: stop the hardware, hand the board back, release the port.
        board.run('stop()', reply=False)
        time.sleep(0.1)
        board.mode(MODE_RUN)                # restarts /main.py
        board.close()
        print('\nstopped; board back in run mode.')


if __name__ == '__main__':
    main()
