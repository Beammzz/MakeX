# -*- coding: utf-8 -*-
"""Drive tuning bench -- main.py's `Wheel.holomix`, with its six tuning numbers
editable while you drive:

    python scripts/Tune_Teleop.py COM6

or pick it from `NovaPi: Run Script...`, which passes the configured COM port as
the first argument.

    1..7        pick the number Up/Down edits
    Up/Down     picked number +/- its step (hold to ramp)
    R           picked number back to what main.py has
    0           every number back to what main.py has
    P           print the paste block now, without quitting
    ESC         quit (Ctrl-C works too)

    Gamepad: left stick drives and strafes, right stick X rotates -- the same
             three axes main.py reads. D-pad Up/Down = pure forward/back,
             D-pad Left/Right = pure strafe, L1/R1 = pure rotate: full-scale
             single-axis moves that go through holomix but not through the
             stick, so a stick that does not quite centre cannot be mistaken
             for a trim error. BACK/Select = quit.

The seven numbers are `Wheel`'s six (DEADZONE, STRAFE_GAIN and the four TRIMs)
plus POWER, which is this script's own output cap and is **not** a `Wheel`
value: main.py always drives at full scale. Tune at whatever POWER is
comfortable, then confirm the trims at 100 before writing them down -- a robot
that tracks straight at 40% does not have to at 100%.

The paste block prints on P and again on exit, so the numbers survive quitting.
`Note.md` is where the team keeps the field values.

**The holomix here is a copy of main.py's**, tuning numbers passed in instead of
read off `self`. It has to be: the point is to try numbers the board's copy does
not have, and main.py is not even running while this is. If you change the math
in main.py, change it here too or this stops predicting anything.

**Forward/back may be inverted.** main.py computes `vy = -_dz(ly)`, matching the
board's own gamepad; `pc_gamepad` says its Ly sign is a guess (see AXIS_MAP in
that file). If the D-pad's forward drives the robot backwards, that is the PC
pad's sign, not a trim -- the numbers you tune are still good.

This tunes the drive only. The shooter is `Test_Shooter.py`, the conveyors are
`Test_DC.py`.

Two halves:

    board_code()   ordinary Python that runs ON THE BOARD. Sent once at
                   startup by board.define(); its imports, variables and
                   functions become board-side globals.
    main()         runs on the PC. Reads the keyboard and the gamepad, does the
                   holomix here, and sends the four wheel powers over the radio.

Live mode **stops `/main.py`** while this runs and restarts it from the top on
exit, so this script owns the board. Commands run one at a time, in order, and a
snippet that raises returns nothing -- check the USB console if a command
silently does nothing.

Keys are read with the Windows key-state API, the same way `teleop.py` and
`Test_DC.py` do it, so a held key really reads as held instead of waiting out
the OS auto-repeat delay. It also means keys register while another window has
focus. Off Windows the keyboard half is simply inactive and the gamepad still
drives the robot, at whatever the defaults below hold.

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

# Board-side auto-stop, and the loop's tick with it: the board is busy for
# exactly this long per command, so the send rate can never outrun it. teleop.py
# measured a 45 ms worst-case round trip, which leaves ~35 ms of slack here.
PULSE = 0.08
IDLE_TICK = 0.05    # poll interval while stopped -- nothing is in flight

# name, label, default, step, low, high, decimals. The defaults are main.py's:
# keep them in step with Wheel.__init__, or R and 0 undo to the wrong place.
# POWER is this script's output cap, not a Wheel value -- see the docstring.
PARAMS = [
    ('DEADZONE',    'DZ',   30,   1,    0,  90, 0),
    ('STRAFE_GAIN', 'GAIN', 1.00, 0.05, 0,  3,  2),
    ('TRIM_UL',     'UL',   1.00, 0.01, 0,  2,  2),
    ('TRIM_LL',     'LL',   1.00, 0.01, 0,  2,  2),
    ('TRIM_UR',     'UR',   1.00, 0.01, 0,  2,  2),
    ('TRIM_LR',     'LR',   1.00, 0.01, 0,  2,  2),
    ('POWER',       'PWR',  60,   5,    0, 100, 0),
]
WHEEL_PARAMS = 6        # the first six are Wheel's; POWER is ours

DIGITS = tuple('%d' % n for n in range(1, len(PARAMS) + 1))

# Virtual-key codes for GetAsyncKeyState (same table style as Test_DC.py).
VK = {'UP': 0x26, 'DOWN': 0x28, 'R': 0x52, 'P': 0x50, 'ESC': 0x1B, '0': 0x30}
VK.update((d, 0x30 + n) for n, d in enumerate(DIGITS, 1))

_user32 = ctypes.windll.user32 if sys.platform == 'win32' else None


def down(key):
    """True while `key` is held. Always False where there is no key-state API,
    so a gamepad-only run on another platform still works."""
    if _user32 is None:
        return False
    return bool(_user32.GetAsyncKeyState(VK[key]) & 0x8000)


def shown(value, decimals):
    """A number the way its parameter is written in main.py."""
    return '%d' % value if decimals == 0 else '%.2f' % value


def defaults():
    return dict((p[0], p[2]) for p in PARAMS)


# ---------------------------------------------------------------- board side --

def board_code():
    """Runs on the BOARD, not here. Everything it defines stays available.

    Write it like any other Python file -- autocomplete and error checking work
    the same. Just keep in mind it executes on a NovaPi: no threads, and only
    the modules the firmware has.
    """
    import time
    from mbuild.encoder_motor import encoder_motor_class

    # M1 upper-left, M2 lower-left, M3 upper-right, M4 lower-right -- the same
    # ports, in the same order, as main.py's Wheel.
    motors = [encoder_motor_class('M1', 'INDEX1'), encoder_motor_class('M2', 'INDEX1'),
              encoder_motor_class('M3', 'INDEX1'), encoder_motor_class('M4', 'INDEX1')]

    def stop():
        for m in motors:
            m.stop()

    def drive(ul, ll, ur, lr, seconds):
        """Set power, hold for `seconds`, then stop -- so the command is its own
        deadman: a crashed PC, a yanked dongle or a closed laptop stops the
        wheels within one pulse. Don't remove the stop."""
        for i in range(4):
            motors[i].set_power((ul, ll, ur, lr)[i])
        online_debug_respond(1)     # reply FIRST, so the PC's next command
        time.sleep(seconds)         # queues while this pulse is still running
        stop()


# ------------------------------------------------------------------- PC side --

def deadzone(v, size):
    """main.py's Wheel._dz: below `size` is nothing, and above it the travel
    that is left stretches back out to a full 0..100, so the first live degree
    of stick is still a small number."""
    if abs(v) < size:
        return 0
    span = 100 - size
    if v > 0:
        return (v - size) * 100 / span
    return (v + size) * 100 / span


def holomix(lx, ly, rx, value):
    """main.py's Wheel.holomix, reading its numbers out of `value` instead of
    off self, returning the wheel powers instead of setting them, and scaled by
    POWER at the end.

    `peak` has 100 in it, so combining axes past full scale shrinks the whole
    vector rather than clipping one wheel -- clipping one wheel changes the
    direction the robot travels -- while anything below full scale is left
    alone. int() truncates towards zero, exactly as main.py does.
    """
    vx = deadzone(lx, value['DEADZONE']) * value['STRAFE_GAIN']
    vy = deadzone(ly, value['DEADZONE'])
    vw = deadzone(rx, value['DEADZONE'])

    # The right side is mounted mirrored, hence the minus on ur/lr -- see
    # WHEEL_INVERT in old_code_main.py, which is where this came from. Without
    # it vy turns the robot and vw drives it, which is Ly rotating and Rx going
    # forward, and strafe lands in the degenerate front-pair-against-rear-pair
    # pattern that just scrubs.
    ul = (vy + vx + vw) * value['TRIM_UL']
    ll = (vy - vx + vw) * value['TRIM_LL']
    ur = -(vy - vx - vw) * value['TRIM_UR']
    lr = -(vy + vx - vw) * value['TRIM_LR']

    peak = max(abs(ul), abs(ll), abs(ur), abs(lr), 100)
    scale = 100 / peak
    out = [v * scale for v in (ul, ll, ur, lr)]
    # Left alone at 100, not multiplied by 1.0: folding the cap into `scale`
    # reorders the arithmetic, and on the wheel that set `peak` that is worth a
    # last bit -- 99.999999999 truncates to 99 where main.py gets a clean 100.
    # Skipping it keeps full power identical to main.py, wheel for wheel.
    if value['POWER'] != 100:
        out = [v * value['POWER'] / 100 for v in out]
    return tuple(int(v) for v in out)


def paste_block(value):
    """The six Wheel numbers, formatted for Wheel.__init__. POWER is left out on
    purpose: it is this script's cap, and main.py has nowhere to put it."""
    lines = ['', 'paste into Wheel.__init__ in main.py:']
    for name, _, _, _, _, _, decimals in PARAMS[:WHEEL_PARAMS]:
        lines.append('        self.%s = %s' % (name, shown(value[name], decimals)))
    lines.append('  (driven at POWER %d%%; main.py always drives at 100 -- '
                 'confirm there before writing these down)' % value['POWER'])
    return '\n'.join(lines)


def test_axes():
    """Full-scale single-axis moves off the D-pad and the shoulders, or None
    when none is held. These skip the stick, not the math: holomix still applies
    the deadzone, the gain and the trims, so what you see is what main.py would
    do with the stick pushed all the way. Forward is ly = -100 because main.py
    flips Ly (`vy = -_dz(ly)`)."""
    if gamepad.is_key_pressed('Up'):
        return 0, -100, 0
    if gamepad.is_key_pressed('Down'):
        return 0, 100, 0
    if gamepad.is_key_pressed('Left'):
        return -100, 0, 0
    if gamepad.is_key_pressed('Right'):
        return 100, 0, 0
    if gamepad.is_key_pressed('L1'):
        return 0, 0, -100
    if gamepad.is_key_pressed('R1'):
        return 0, 0, 100
    return None


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

    print('drive tuning on %s (wheels M1-M4)' % sys.argv[1])
    print('1-%s = pick a number, Up/Down = edit it, R = picked back to'
          " main.py's," % DIGITS[-1])
    print('0 = all back, P = print the paste block,')
    print('ESC or Ctrl-C = quit')
    print('gamepad: left stick = drive/strafe, right stick X = rotate,')
    print('         D-pad = pure forward/back/strafe, L1/R1 = pure rotate,')
    print('         BACK/Select = quit')
    if _user32 is None:
        print('not on Windows: keyboard control is off, so the numbers stay at '
              'their defaults')
    elif not gamepad.is_connected():
        print('no controller found; nothing moves until one is plugged in '
              '(this keeps polling)')

    value = defaults()
    index = 0                               # the number Up/Down edits
    last = None
    was = None
    try:
        while True:
            if down('ESC') or gamepad.is_key_pressed('Select'):
                break

            # Edge-triggered: these change state, so only act on the press.
            now = dict((k, down(k)) for k in ('P', '0') + DIGITS)
            if was is None:
                # First pass: anything held right now was already held before
                # this script started -- the keystroke that launched it, or a
                # key being used in another window. Not a press.
                was = now
            edge = dict((k, v and not was[k]) for k, v in now.items())
            was = now

            name, _, default, step, low, high, decimals = PARAMS[index]
            if down('R'):
                value[name] = default
            elif down('UP'):
                value[name] = round(min(high, value[name] + step), decimals)
            elif down('DOWN'):
                value[name] = round(max(low, value[name] - step), decimals)

            if edge['0']:
                value = defaults()

            for n, digit in enumerate(DIGITS):
                if edge[digit]:
                    index = n           # moves the cursor only: the number
                    break               # left behind keeps its value

            axes = test_axes()
            if axes is None:
                source = 'stick'
                axes = (gamepad.get_joystick('Lx'), gamepad.get_joystick('Ly'),
                        gamepad.get_joystick('Rx'))
            else:
                source = 'test'
            wheels = holomix(axes[0], axes[1], axes[2], value)

            if edge['P']:
                # A whole line, not the \r status line: this is the thing you
                # came to read, and it has to survive the next tick.
                print('\n' + paste_block(value))

            if wheels == (0, 0, 0, 0) and last == wheels:
                # Stopped, and the board is stopped too: stay quiet. The screen
                # keeps updating, so editing numbers while parked still works.
                source = 'stop'
                time.sleep(IDLE_TICK)
            else:
                # The reply is the flow control: the board answers at the START
                # of its pulse, so this blocks until that pulse is under way and
                # the send rate can never outrun the board.
                board.run('drive(%d,%d,%d,%d,%r)' % (wheels + (PULSE,)),
                          timeout=PULSE + 1.0, retries=0)
                last = wheels

            row = '  '.join('%s%s %s' % ('>' if n == index else ' ', p[1],
                                         shown(value[p[0]], p[6]))
                            for n, p in enumerate(PARAMS))
            print('\r' + ('%s  [%4d %4d %4d %4d]  %-5s %s' % (
                row, wheels[0], wheels[1], wheels[2], wheels[3], source,
                'pad' if gamepad.is_connected() else 'nopad')).ljust(120)[:120],
                end='')
    except KeyboardInterrupt:
        pass
    finally:
        # Always: stop the hardware, hand the board back, release the port --
        # and then the numbers, so quitting is not how an afternoon's tuning
        # gets lost.
        board.run('stop()', reply=False)
        time.sleep(0.1)
        board.mode(MODE_RUN)                # restarts /main.py
        board.close()
        print('\nstopped; board back in run mode.')
        print(paste_block(value))


if __name__ == '__main__':
    main()
