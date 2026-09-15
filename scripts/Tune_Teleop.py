# -*- coding: utf-8 -*-
"""Drive tuning bench -- main.py's `Wheel.holomix`, with its nine tuning
numbers editable while you drive:

    python scripts/Tune_Teleop.py COM6

or pick it from `NovaPi: Run Script...`, which passes the configured COM port as
the first argument.

    1..9        pick the number Up/Down edits
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

    No gamepad: W/S = forward/back, A/D = strafe, Q/E = rotate -- held keys
             combine like a real stick (W+A drives forward-left), full scale,
             through the same holomix. Only live while `gamepad.is_connected()`
             is False, so plugging a pad back in hands control back to it.

The nine numbers are `Wheel`'s eight (DEADZONE, the four TUNEs and a shared
KP/KI/KD) plus POWER, which is this script's own output cap and is **not** a
`Wheel` value: main.py always drives at full scale. Tune at whatever POWER is
comfortable, then confirm the tunes at 100 before writing them down -- a robot
that tracks straight at 40% does not have to at 100%.

The paste block prints on P and again on exit, so the numbers survive quitting.
`Note.md` is where the team keeps the field values.

**The mix and deadzone are a copy of main.py's**, computed here on the PC from
the stick, with DEADZONE and the four TUNEs passed in instead of read off
module globals. It has to be a copy: the point is to try numbers the board's
copy does not have, and main.py is not even running while this is. If you
change the mix in main.py, change it here too or this stops predicting
anything.

**PID and the TUNEs run on the board, not here** -- pid.update() needs the
motor's live encoder speed, which only exists on the board, and main.py
applies TUNE *after* the PID correction (see `Wheel.set_speed`), so it has to
sit on the same side of that addition. This script sends the PC-computed mix
as a target speed; `board_code()`'s `drive()` runs main.py's own `PID.update`
and `set_speed(target * TUNE)` against the real motors, using main.py's exact
sign convention (`ul`/`ll` feedback negated, `ur`/`lr` not). KP/KI/KD here tune
all four corners together; main.py has them per corner (UL/UR/LL/LR) -- the
paste block fans the one tuned value out to all twelve.

**Forward/back may be inverted.** main.py negates lx and rx before mixing
(`self.drive(-lx, ly, -rx, pid=True)`) but passes ly through unchanged;
`pc_gamepad` says its axis signs are a guess (see AXIS_MAP in that file). If
the D-pad's forward drives the robot backwards, or its strafe goes the wrong
way, that is the PC pad's sign, not a tune -- the numbers you tune are still
good.

This tunes the drive only. The shooter is `Test_Shooter.py`, the conveyors are
`Test_DC.py`.

Two halves:

    board_code()   ordinary Python that runs ON THE BOARD. Sent once at
                   startup by board.define(); its imports, variables and
                   functions become board-side globals.
    main()         runs on the PC. Reads the keyboard and the gamepad, does the
                   mix here, and sends the four wheel PID targets over the radio
                   for board_code()'s drive() to correct and apply.

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
# keep them in step with its module-level DEADZONE/UL_TUNE/UL_KP/etc, or R and 0
# undo to the wrong place. POWER is this script's output cap, not a Wheel
# value -- see the docstring.
PARAMS = [
    ('DEADZONE', 'DZ',  40,   1,    0,   90, 0),
    ('UL_TUNE',  'UL',  1.00, 0.01, 0.1, 1.0, 2),
    ('UR_TUNE',  'UR',  1.00, 0.01, 0.1, 1.0, 2),
    ('LL_TUNE',  'LL',  1.00, 0.01, 0.1, 1.0, 2),
    ('LR_TUNE',  'LR',  1.00, 0.01, 0.1, 1.0, 2),
    ('KP',       'KP',  1.00, 0.05, 0,   5,   2),
    ('KI',       'KI',  0.00, 0.01, 0,   2,   2),
    ('KD',       'KD',  0.00, 0.01, 0,   2,   2),
    ('POWER',    'PWR', 60,   5,    0,   100, 0),
]
WHEEL_PARAMS = 5        # DEADZONE + the four TUNEs; PID and POWER are separate
PID_PARAMS = ('KP', 'KI', 'KD')

DIGITS = tuple('%d' % n for n in range(1, len(PARAMS) + 1))

# Virtual-key codes for GetAsyncKeyState (same table style as Test_DC.py).
VK = {'UP': 0x26, 'DOWN': 0x28, 'R': 0x52, 'P': 0x50, 'ESC': 0x1B, '0': 0x30,
      'W': 0x57, 'A': 0x41, 'S': 0x53, 'D': 0x44, 'Q': 0x51, 'E': 0x45}
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

    MAX_SPEED = 255     # main.py's restrict() ceiling

    class PID:
        """A copy of main.py's PID class -- same kp/ki/kd/update, so tuning it
        here means something on main.py's copy."""
        def __init__(self, kp, ki, kd):
            self.kp = kp
            self.ki = ki
            self.kd = kd
            self.integral = 0.0
            self.previous_error = 0.0

        def reset(self):
            self.integral = 0.0
            self.previous_error = 0.0

        def update(self, target, current):
            error = target - current
            self.integral += error
            derivative = error - self.previous_error
            self.previous_error = error
            return self.kp * error + self.ki * self.integral + self.kd * derivative

    # One PID and one TUNE per motor, in the same ul/ll/ur/lr order as `motors`.
    # main.py has these as four separate PIDs (UL/UR/LL/LR); set_gains() below
    # tunes all four together since that is what fits this bench's keys.
    pids = [PID(1.0, 0.0, 0.0) for _ in range(4)]
    tunes = [1.0, 1.0, 1.0, 1.0]

    def set_gains(kp, ki, kd):
        for p in pids:
            p.kp = kp
            p.ki = ki
            p.kd = kd
            p.reset()            # a gain change mid-drive would otherwise spike

    def set_tunes(ul, ll, ur, lr):
        tunes[0], tunes[1], tunes[2], tunes[3] = ul, ll, ur, lr

    def stop():
        for m in motors:
            m.set_speed(0)
        for p in pids:
            p.reset()

    def drive(ul, ll, ur, lr, seconds):
        """main.py's Wheel.drive(pid=True) + Wheel.set_speed, run against the
        real motors: `target` is what the PC's holomix computed (mix, deadzone,
        peak-normalize, POWER cap already applied -- see Tune_Teleop.py's
        holomix()), then PID-corrected against live encoder speed and scaled by
        TUNE here, exactly where main.py does it. Same feedback signs as
        main.py: ul/ll negated, ur/lr not (`Wheel.drive`).

        Holds for `seconds` then stops -- so the command is its own deadman: a
        crashed PC, a yanked dongle or a closed laptop stops the wheels within
        one pulse. Don't remove the stop."""
        target = (ul, ll, ur, lr)
        feedback = (-motors[0].get_value('speed'), -motors[1].get_value('speed'),
                    motors[2].get_value('speed'), motors[3].get_value('speed'))
        for i in range(4):
            out = target[i] + pids[i].update(target[i], feedback[i])
            out = out * tunes[i]
            out = max(min(out, MAX_SPEED), -MAX_SPEED)
            motors[i].set_speed(int(out))
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
    """main.py's Wheel.holomix -> drive, up to (not including) the PID/TUNE
    step -- see the module docstring for why those run on the board instead.
    Reads DEADZONE out of `value` instead of off a module global; returns a PID
    *target* per wheel, scaled by POWER at the end, for `drive()` in
    `board_code()` to correct and send.

    main.py negates lx and rx before mixing (`self.drive(-lx, ly, -rx, ...)`),
    so that happens here first too.

    `peak` has 100 in it, so combining axes past full scale shrinks the whole
    vector rather than clipping one wheel -- clipping one wheel changes the
    direction the robot travels -- while anything below full scale is left
    alone.
    """
    vx = deadzone(-lx, value['DEADZONE'])
    vy = deadzone(ly, value['DEADZONE'])
    vw = deadzone(-rx, value['DEADZONE'])

    # The right side is mounted mirrored, hence the sign pattern on ur/lr --
    # see Wheel._mix in main.py, which this copies. Without it vy turns the
    # robot and vw drives it, which is Ly rotating and Rx going forward, and
    # strafe lands in the degenerate front-pair-against-rear-pair pattern that
    # just scrubs.
    ul = vx + vy + vw
    ll = -vx + vy + vw
    ur = vx - vy + vw
    lr = -vx - vy + vw

    peak = max(abs(ul), abs(ll), abs(ur), abs(lr), 100)
    scale = 100 / peak
    out = tuple(v * scale for v in (ul, ll, ur, lr))
    if value['POWER'] != 100:
        out = tuple(v * value['POWER'] / 100 for v in out)
    return out


def paste_block(value):
    """The Wheel numbers, formatted as main.py's module-level constants. POWER
    is left out on purpose: it is this script's cap, and main.py has nowhere to
    put it. KP/KI/KD are tuned here as one shared set but fanned out to all
    four corners, since that is how main.py declares them."""
    lines = ['', 'paste near the top of main.py, replacing the current values:']
    for name, _, _, _, _, _, decimals in PARAMS[:WHEEL_PARAMS]:
        lines.append('%s = %s' % (name, shown(value[name], decimals)))
    kp, ki, kd = (shown(value[n], 2) for n in PID_PARAMS)
    lines.append('  (KP/KI/KD tuned together below -- split them per corner by '
                 'hand if one needs to differ)')
    for corner in ('UL', 'UR', 'LL', 'LR'):
        lines.append('%s_KP = %s' % (corner, kp))
        lines.append('%s_KI = %s' % (corner, ki))
        lines.append('%s_KD = %s' % (corner, kd))
    lines.append('  (driven at POWER %d%%; main.py always drives at full scale '
                 '-- confirm there before writing these down)' % value['POWER'])
    return '\n'.join(lines)


def test_axes():
    """Full-scale single-axis moves off the D-pad and the shoulders, or None
    when none is held. These skip the stick, not the math: holomix still applies
    the deadzone and the tunes, so what you see is what main.py would do with
    the stick pushed all the way. Forward is ly = -100, matching the board
    gamepad's usual convention; main.py does not flip Ly itself, so if this
    drives backwards on your pad it is `pc_gamepad`'s sign, not a tune (see the
    module docstring)."""
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


def keyboard_axes():
    """WASD + Q/E stand-in for the stick when there is no gamepad: W/S = ly,
    A/D = lx, Q/E = rx, full scale, and they combine (W+A is forward-left) the
    way a real stick would -- unlike test_axes()'s one-axis-at-a-time moves.
    Only meaningful on Windows; down() is always False elsewhere."""
    lx = (100 if down('D') else 0) - (100 if down('A') else 0)
    ly = (100 if down('W') else 0) - (100 if down('S') else 0)
    rx = (100 if down('E') else 0) - (100 if down('Q') else 0)
    return lx, ly, rx


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
    print('no gamepad: W/S = forward/back, A/D = strafe, Q/E = rotate')
    if _user32 is None:
        print('not on Windows: keyboard control (numbers and WASD/QE) is off, '
              'so nothing drives without a gamepad')
    elif not gamepad.is_connected():
        print('no controller found; driving off WASD/QE until one is plugged '
              'in (this keeps polling)')

    value = defaults()
    index = 0                               # the number Up/Down edits
    last = None
    was = None
    # board_code()'s pids/tunes already start at these same defaults, so no
    # push is needed until a key actually changes one of them.
    last_tunes = (value['UL_TUNE'], value['LL_TUNE'], value['UR_TUNE'], value['LR_TUNE'])
    last_gains = tuple(value[n] for n in PID_PARAMS)
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

            # Push TUNE/gain edits to the board only when they actually moved --
            # everything else (deadzone, mix, POWER) travels inside drive()'s
            # own target numbers and needs no separate command.
            tunes_now = (value['UL_TUNE'], value['LL_TUNE'], value['UR_TUNE'], value['LR_TUNE'])
            if tunes_now != last_tunes:
                board.run('set_tunes(%.2f,%.2f,%.2f,%.2f)' % tunes_now, reply=False)
                last_tunes = tunes_now
            gains_now = tuple(value[n] for n in PID_PARAMS)
            if gains_now != last_gains:
                board.run('set_gains(%.2f,%.2f,%.2f)' % gains_now, reply=False)
                last_gains = gains_now

            axes = test_axes()
            if axes is not None:
                source = 'test'
            elif gamepad.is_connected():
                source = 'stick'
                axes = (gamepad.get_joystick('Lx'), gamepad.get_joystick('Ly'),
                        gamepad.get_joystick('Rx'))
            else:
                source = 'wasd'
                axes = keyboard_axes()
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
                # the send rate can never outrun the board. Targets go over as
                # floats -- the PID on the board wants the same precision
                # main.py's own holomix would hand it, not a pre-rounded int.
                board.run('drive(%.2f,%.2f,%.2f,%.2f,%r)' % (wheels + (PULSE,)),
                          timeout=PULSE + 1.0, retries=0)
                last = wheels

            disp = tuple(int(w) for w in wheels)   # display only; drive() got floats
            row = '  '.join('%s%s %s' % ('>' if n == index else ' ', p[1],
                                         shown(value[p[0]], p[6]))
                            for n, p in enumerate(PARAMS))
            print('\r' + ('%s  [%4d %4d %4d %4d]  %-5s %s' % (
                row, disp[0], disp[1], disp[2], disp[3], source,
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
