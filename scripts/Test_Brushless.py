# -*- coding: utf-8 -*-
"""Brushless motor bench test, driven from the PC:

    python scripts/Test_Brushless.py COM6

or pick it from `NovaPi: Run Script…`, which passes the configured COM port as
the first argument.

Two halves:

    board_code()   ordinary Python that runs ON THE BOARD. Sent once at
                   startup by board.define(); its imports, variables and
                   functions become board-side globals.
    main()         runs on the PC. Reads the gamepad and calls the functions
                   board_code() defined, one at a time, over the radio.

Live mode **stops `/main.py`** while this runs and restarts it from the top on
exit, so this script owns the board. Commands run one at a time, in order, and a
snippet that raises returns nothing -- check the USB console if a command
silently does nothing.

`live` and `pc_gamepad` live in the extension's `scripts/` folder, not next to
this file; `_bootstrap()` puts that folder on `sys.path`. Set `NOVAPI_SCRIPTS`
if the extension repo is not the sibling `../NovaPi`.
"""
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
STEP = 5         # how much the controls change power per tick, 0..100


# ---------------------------------------------------------------- board side --

def board_code():
    """Runs on the BOARD, not here. Everything it defines stays available.

    Write it like any other Python file -- autocomplete and error checking work
    the same. Just keep in mind it executes on a NovaPi: no threads, and only
    the modules the firmware has.
    """
    import time
    from mbuild import power_expand_board

    # The board has two dedicated brushless outputs, BL1 and BL2; 'DC1'..'DC8'
    # are the H-bridge DC channels and are the wrong shape of signal for an ESC.
    # Keep the channel names literal: the stubs check them.

    def stop():
        power_expand_board.set_power('BL1', 0)
        power_expand_board.set_power('BL2', 0)

    def spin(left_power, right_power, seconds):
        """Set both motors, hold for `seconds`, then stop."""
        power_expand_board.set_power('BL1', left_power)
        power_expand_board.set_power('BL2', right_power)
        online_debug_respond('%d,%d' % (left_power, right_power))
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

    print('brushless test on %s' % sys.argv[1])
    print('A = start/stop, RT/LT = BL1, R1/L1 = BL2, B or SPACE = 0, BACK/Select or Ctrl-C = quit')
    if not gamepad.is_connected():
        print('no controller found; plug one in (this keeps polling)')

    left_power = 0
    right_power = 0
    running = False
    a_was_pressed = False
    try:
        while True:
            if gamepad.is_key_pressed('Select'):
                break
            if gamepad.is_key_pressed('N2'):        # B
                left_power = 0
                right_power = 0
            elif gamepad.is_key_pressed('R2'):      # right trigger
                left_power = min(100, left_power + STEP)
            elif gamepad.is_key_pressed('L2'):      # left trigger
                left_power = max(0, left_power - STEP)

            if gamepad.is_key_pressed('R1'):        # right shoulder
                right_power = min(100, right_power + STEP)
            elif gamepad.is_key_pressed('L1'):      # left shoulder
                right_power = max(0, right_power - STEP)

            a_pressed = gamepad.is_key_pressed('N1')    # A
            if a_pressed and not a_was_pressed:
                running = not running
                if not running:
                    board.run('stop()', reply=False)
            a_was_pressed = a_pressed

            if running:
                # The reply is the flow control: the board answers at the START
                # of its pulse, so this blocks until that pulse is under way and
                # the send rate can never outrun the board.
                got = board.run('spin(%d,%d,%r)' % (left_power, right_power, PULSE),
                                timeout=PULSE + 1.0, retries=0)
            else:
                got = 'stopped'
                time.sleep(0.05)

            print('\rL %3d  R %3d  %-7s board says %-10s' % (
                left_power, right_power, 'run' if running else 'stop', got),
                end='')

            # TODO: read something back to compare against the setting, e.g.
            #   print(board.run("online_debug_respond(novapi.get_battery())"))
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
