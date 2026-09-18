# -*- coding: utf-8 -*-
"""Drive tuning bench -- main.py's own drive, with its four TRIM lists and two
speeds editable while you drive:

    python scripts/Tune_Teleop.py COM6

or pick it from `NovaPi: Run Script...`, which passes the configured COM port as
the first argument.

    Left/Right  move the cursor over the 18 numbers
    1..4        jump to TRIM_FORWARD / BACKWARD / LEFT / RIGHT
    5 / 6       jump to slow_speed / normal_speed
    Up/Down     number under the cursor +/- its step (hold to ramp)
    R           number under the cursor back to what main.py has
    0           every number back to what main.py has
    P           print the paste block now, without quitting
    ESC         quit (Ctrl-C works too)

    Gamepad: left stick drives and strafes, right stick X rotates -- the same
             three axes main.py reads. D-pad Up/Down = pure forward/back,
             D-pad Left/Right = pure strafe, L1/R1 = pure rotate, all at full
             stick (normal speed); hold R2 to make them half stick (slow
             speed). BACK/Select = quit.

    No gamepad: W/S = forward/back, A/D = strafe, Q/E = rotate, SHIFT = half
             stick (slow speed). Only live while `gamepad.is_connected()` is
             False, so plugging a pad back in hands control back to it.

**This drives main.py's code, not a copy of it.** It loads main.py onto the
board the same way Teleop.py does (see MAIN.PY ON THE BOARD there) and every
pulse calls `Guzzchan.control()` with the PC's sticks. An edit here is written
straight into the board's copy -- `TRIM_FORWARD[1] = 0.97`,
`_R.wheel.slow_speed = 80` -- so the next pulse drives with it. The starting
values are read off the board after main.py loads, so R and 0 go back to
whatever main.py has now.

Which TRIM a move uses is main.py's choice: forward/backward/strafe each have
their own list, used at both speeds; rotation uses none. So tune a direction by
driving it -- D-pad Up for TRIM_FORWARD, and so on -- then check it at the slow
speed too (R2 held) before writing it down.

The paste block prints on P and again on exit, so the numbers survive quitting.
`Note.md` is where the team keeps the field values.

Live mode **stops `/main.py`** while this runs and restarts it from the top on
exit, so this script owns the board. Commands run one at a time, in order, and a
snippet that raises returns nothing -- check the USB console if a command
silently does nothing.

Keys are read with the Windows key-state API, the same way `Teleop.py` and
`Test_DC.py` do it, so a held key really reads as held instead of waiting out
the OS auto-repeat delay. It also means keys register while another window has
focus.
"""
import ast
import ctypes
import sys
import time

# Teleop puts the extension's scripts/ folder on sys.path when imported, so it
# comes before pc_gamepad and live.
from Teleop import DEFAULT_PULSE as PULSE, IDLE_TICK, connect
import pc_gamepad as gamepad                    # noqa: E402
from live import MODE_RUN                       # noqa: E402

# main.py's module-level trim lists, each in its motor order.
TRIMS = ('TRIM_FORWARD', 'TRIM_BACKWARD', 'TRIM_LEFT', 'TRIM_RIGHT')
WHEELS = ('UL', 'LL', 'UR', 'LR')
# Wheel attributes, set in Wheel.__init__.
SPEEDS = ('slow_speed', 'normal_speed')

# Every editable number, in cursor order: (name, wheel index) for a trim,
# (name, None) for a speed.
SLOTS = [(t, i) for t in TRIMS for i in range(4)] + [(s, None) for s in SPEEDS]
JUMP = {'1': 0, '2': 4, '3': 8, '4': 12, '5': 16, '6': 17}

# The board reads these back as one list, in SLOTS order once flattened.
READ = ('online_debug_respond(repr([%s, _R.wheel.slow_speed, _R.wheel.normal_speed]))'
        % ', '.join(TRIMS))


def limits(slot):
    """step, low, high, decimals."""
    return (0.01, 0.5, 1.5, 2) if slot[1] is not None else (5, 0, 300, 0)


def board_set(slot, v):
    """The board-side statement that writes one number into main.py's copy."""
    name, i = slot
    if i is None:
        return '_R.wheel.%s = %d' % (name, v)
    return '%s[%d] = %.2f' % (name, i, v)


# Virtual-key codes for GetAsyncKeyState (same table style as Test_DC.py).
VK = {'UP': 0x26, 'DOWN': 0x28, 'LEFT': 0x25, 'RIGHT': 0x27, 'R': 0x52,
      'P': 0x50, 'ESC': 0x1B, '0': 0x30, 'SHIFT': 0x10,
      'W': 0x57, 'A': 0x41, 'S': 0x53, 'D': 0x44, 'Q': 0x51, 'E': 0x45}
VK.update((d, 0x30 + int(d)) for d in JUMP)

_user32 = ctypes.windll.user32 if sys.platform == 'win32' else None


def down(key):
    """True while `key` is held. Always False where there is no key-state API,
    so a gamepad-only run on another platform still works."""
    if _user32 is None:
        return False
    return bool(_user32.GetAsyncKeyState(VK[key]) & 0x8000)


def paste_block(value):
    """The numbers, formatted the way main.py writes them."""
    lines = ['', 'paste into main.py, replacing the current values:']
    for t in TRIMS:
        lines.append('%s = [%s]' % (t, ', '.join('%.2f' % value[(t, i)]
                                                  for i in range(4))))
    lines.append('and in Wheel.__init__:')
    for s in SPEEDS:
        lines.append('        self.%s = %d' % (s, value[(s, None)]))
    return '\n'.join(lines)


def test_axes():
    """Single-axis moves off the D-pad and the shoulders, or None when none is
    held. These skip the stick, not main.py: control() still picks the move and
    the trim. Full stick is normal speed; R2 halves it into the slow band."""
    k = 50 if gamepad.is_key_pressed('R2') else 100
    if gamepad.is_key_pressed('Up'):
        return 0, k, 0
    if gamepad.is_key_pressed('Down'):
        return 0, -k, 0
    if gamepad.is_key_pressed('Left'):
        return -k, 0, 0
    if gamepad.is_key_pressed('Right'):
        return k, 0, 0
    if gamepad.is_key_pressed('L1'):
        return 0, 0, -k
    if gamepad.is_key_pressed('R1'):
        return 0, 0, k
    return None


def keyboard_axes():
    """WASD + Q/E stand-in for the stick when there is no gamepad, combined the
    way a real stick would be. SHIFT halves it into the slow band."""
    k = 50 if down('SHIFT') else 100
    lx = (k if down('D') else 0) - (k if down('A') else 0)
    ly = (k if down('W') else 0) - (k if down('S') else 0)
    rx = (k if down('E') else 0) - (k if down('Q') else 0)
    return lx, ly, rx


def main():
    if len(sys.argv) < 2:
        sys.exit('Usage: Tune_Teleop.py <port>   (e.g. COM6)')

    board, _ = connect(sys.argv[1], PULSE)
    got = board.run(READ)
    if got is None:
        board.mode(MODE_RUN)
        board.close()
        sys.exit('could not read %s and %s off the board -- has main.py '
                 'renamed them?' % ('/'.join(TRIMS), '/'.join(SPEEDS)))
    lists = ast.literal_eval(got)
    flat = [v for t in lists[:4] for v in t] + lists[4:]
    main_py = dict(zip(SLOTS, flat))

    print('drive tuning on %s, driving main.py\'s Guzzchan.control()' % sys.argv[1])
    print('Left/Right = move cursor, 1-4 = TRIM_FORWARD/BACKWARD/LEFT/RIGHT,')
    print('5/6 = slow/normal speed, Up/Down = edit, R = back to main.py\'s,')
    print('0 = all back, P = print the paste block, ESC or Ctrl-C = quit')
    print('gamepad: left stick = drive/strafe, right stick X = rotate,')
    print('         D-pad = pure forward/back/strafe, L1/R1 = pure rotate,')
    print('         R2 held = slow speed, BACK/Select = quit')
    print('no gamepad: W/S = forward/back, A/D = strafe, Q/E = rotate, '
          'SHIFT = slow')
    if not gamepad.is_connected():
        print('no controller found; driving off WASD/QE until one is plugged '
              'in (this keeps polling)')

    value = dict(main_py)
    sent = dict(main_py)                    # what the board holds right now
    index = 0                               # the number Up/Down edits
    last = None
    was = None
    got = 1
    try:
        while True:
            if down('ESC') or gamepad.is_key_pressed('Select'):
                break

            # Edge-triggered: these move the cursor or reset, so only act on
            # the press.
            now = dict((k, down(k)) for k in ('P', '0', 'LEFT', 'RIGHT') + tuple(JUMP))
            if was is None:
                # First pass: anything held right now was already held before
                # this script started -- the keystroke that launched it, or a
                # key being used in another window. Not a press.
                was = now
            edge = dict((k, v and not was[k]) for k, v in now.items())
            was = now

            if edge['LEFT']:
                index = (index - 1) % len(SLOTS)
            if edge['RIGHT']:
                index = (index + 1) % len(SLOTS)
            for d, n in JUMP.items():
                if edge[d]:
                    index = n

            slot = SLOTS[index]
            step, low, high, decimals = limits(slot)
            if down('R'):
                value[slot] = main_py[slot]
            elif down('UP'):
                value[slot] = round(min(high, value[slot] + step), decimals)
            elif down('DOWN'):
                value[slot] = round(max(low, value[slot] - step), decimals)
            if edge['0']:
                value = dict(main_py)

            # Only what actually moved goes to the board.
            changed = [s for s in SLOTS if value[s] != sent[s]]
            if changed:
                board.run('\n'.join(board_set(s, value[s]) for s in changed),
                          reply=False)
                sent = dict(value)

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

            if edge['P']:
                # A whole line, not the \r status line: this is the thing you
                # came to read, and it has to survive the next tick.
                print('\n' + paste_block(value))

            if axes == (0, 0, 0) and last == axes:
                # Stopped, and the board is stopped too: stay quiet. The screen
                # keeps updating, so editing numbers while parked still works.
                source = 'stop'
                time.sleep(IDLE_TICK)
            else:
                # The reply is the flow control: the board answers at the START
                # of its pulse, so this blocks until that pulse is under way and
                # the send rate can never outrun the board.
                got = board.run('_d(%d,%d,%d)' % axes, timeout=PULSE + 1.0,
                                retries=0)
                last = axes

            # One trim list at a time fits the line: the cursor's, or the last
            # one when the cursor is on a speed.
            group = TRIMS[min(index, 15) // 4]
            row = '  '.join('%s%s %.2f' % ('>' if slot == (group, i) else ' ',
                                           WHEELS[i], value[(group, i)])
                            for i in range(4))
            speeds = '  '.join('%s%s %d' % ('>' if slot == (s, None) else ' ',
                                            s.split('_')[0], value[(s, None)])
                               for s in SPEEDS)
            print('\r' + ('%-13s %s |%s | Lx%+4d Ly%+4d Rx%+4d %-5s %s' % (
                group, row, speeds, axes[0], axes[1], axes[2], source,
                'pad' if gamepad.is_connected() else 'nopad') +
                ('' if got else '  NO REPLY')).ljust(125)[:125], end='')
    except KeyboardInterrupt:
        pass
    finally:
        # Always: stop the hardware, hand the board back, release the port --
        # and then the numbers, so quitting is not how an afternoon's tuning
        # gets lost.
        board.run('_s()', reply=False)
        time.sleep(0.1)
        board.mode(MODE_RUN)                # restarts /main.py
        board.close()
        print('\nstopped; board back in run mode.')
        print(paste_block(value))


if __name__ == '__main__':
    main()
