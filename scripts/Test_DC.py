# -*- coding: utf-8 -*-
"""DC motor bench test, driven from the PC keyboard:

    python scripts/Test_DC.py COM6 [channel]

or pick it from `NovaPi: Run Script…`, which passes the configured COM port as
the first argument. The optional second argument is the channel to start on.

    1..8      pick DC1..DC8 -- the one Up/Down edits; the others keep theirs
    Up/Down   power +/- STEP (hold to ramp; goes negative to reverse)
    SPACE     start / stop every channel that has a non-zero power
    R         picked channel back to 0
    ESC       quit (Ctrl-C works too)

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

Keys are read with the Windows key-state API, the same way `teleop.py` does it,
so a held key really reads as held instead of waiting out the OS auto-repeat
delay. It also means keys register while another window has focus: stop the
motor before going off to type somewhere else.

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

PULSE = 0.25        # seconds a command holds before the board stops the motor
STEP = 5            # how much Up/Down change power per tick, -100..100

# The H-bridge DC channels. The official docs call them "CH1".."CH8", mBlock's
# generated code calls the same pins "DC1".."DC8" and that is what main.py uses,
# so keep the spelling consistent with the robot code being tested.
CHANNELS = ['DC%d' % n for n in range(1, 9)]
DIGITS = tuple('%d' % n for n in range(1, 9))

# Virtual-key codes for GetAsyncKeyState (same table style as teleop.py).
VK = {'UP': 0x26, 'DOWN': 0x28, 'SPACE': 0x20, 'R': 0x52, 'ESC': 0x1B}
VK.update((d, 0x30 + n) for n, d in enumerate(DIGITS, 1))

_user32 = ctypes.windll.user32 if sys.platform == 'win32' else None


def down(key):
    return bool(_user32.GetAsyncKeyState(VK[key]) & 0x8000)


# ---------------------------------------------------------------- board side --

def board_code():
    """Runs on the BOARD, not here. Everything it defines stays available.

    Write it like any other Python file -- autocomplete and error checking work
    the same. Just keep in mind it executes on a NovaPi: no threads, and only
    the modules the firmware has.
    """
    import time
    from mbuild import power_expand_board

    def stop():
        power_expand_board.stop('ALL')

    def spin(pairs, seconds):
        """Drive every (channel, power) in `pairs` together, hold for `seconds`,
        then stop them all -- so the command is its own deadman: a crashed PC, a
        yanked dongle or a closed laptop stops the motors within one pulse.
        Don't remove the stop. A channel dropped from `pairs` stays stopped: the
        pulse that last drove it ended by zeroing it."""
        for ch, power in pairs:
            power_expand_board.set_power(ch, power)
        online_debug_respond(' '.join(              # reply FIRST, so the PC's
            '%s %d' % (c, p) for c, p in pairs))    # next command queues while
        time.sleep(seconds)                         # this pulse still runs
        for ch, _ in pairs:
            power_expand_board.set_power(ch, 0)


# ------------------------------------------------------------------- PC side --

def main():
    if _user32 is None:
        sys.exit('Test_DC.py uses the Windows key-state API.')
    if len(sys.argv) < 2:
        sys.exit('Usage: %s <port> [channel]   (e.g. COM6 DC1)'
                 % os.path.basename(sys.argv[0]))

    index = 0
    if len(sys.argv) > 2:
        wanted = sys.argv[2].upper()
        if wanted not in CHANNELS:
            sys.exit('Unknown channel %r -- pick one of %s'
                     % (sys.argv[2], ', '.join(CHANNELS)))
        index = CHANNELS.index(wanted)

    board = Live(sys.argv[1])
    board.mode(MODE_LIVE)                   # stops /main.py
    try:
        board.define(board_code)            # ships the function above
    except IOError as exc:
        board.mode(MODE_RUN)
        board.close()
        sys.exit(str(exc))

    print('DC motor test on %s' % sys.argv[1])
    print('1-8 = pick channel, Up/Down = its power, SPACE = start/stop all,')
    print('R = picked channel to 0,')
    print('ESC or Ctrl-C = quit')

    powers = dict.fromkeys(CHANNELS, 0)     # every channel; most stay idle
    running = False
    was = {}
    try:
        while True:
            if down('ESC'):
                break

            # Edge-triggered: these change state, so only act on the press.
            edge = {}
            for key in ('SPACE',) + DIGITS:
                now = down(key)
                edge[key] = now and not was.get(key)
                was[key] = now

            ch = CHANNELS[index]
            if down('R'):
                powers[ch] = 0
            elif down('UP'):
                powers[ch] = min(100, powers[ch] + STEP)
            elif down('DOWN'):
                powers[ch] = max(-100, powers[ch] - STEP)

            for n, digit in enumerate(DIGITS):
                if edge[digit]:
                    index = n           # moves the cursor only: the channel
                    break               # left behind keeps its own power

            if edge['SPACE']:
                running = not running
                if not running:
                    board.run('stop()', reply=False)

            active = [(c, powers[c]) for c in CHANNELS if powers[c]]
            if running and active:
                # The reply is the flow control: the board answers at the START
                # of its pulse, so this blocks until that pulse is under way and
                # the send rate can never outrun the board.
                got = board.run('spin(%r,%r)' % (active, PULSE),
                                timeout=PULSE + 1.0, retries=0)
            else:
                got = 'stopped'
                time.sleep(0.05)

            # The cursor channel always shows, idle or not; the rest only
            # once they have a power, so the line stays short at the start.
            shown = '  '.join('%s%s %d' % ('>' if n == index else ' ', c, powers[c])
                              for n, c in enumerate(CHANNELS)
                              if powers[c] or n == index)
            print('\r' + ('%s  %-4s  board says %s' % (
                shown, 'run' if running else 'stop', got)).ljust(110)[:110],
                end='')
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
