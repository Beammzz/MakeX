# -*- coding: utf-8 -*-
"""Template for a PC-side live script -- copy this, rename it, edit the TODOs.

    python scripts/my_script.py COM6

or pick it from `NovaPi: Run Script…`, which passes the configured COM port as
the first argument. Put your copy in your project's `scripts/` folder: files
there are never uploaded to the board (only top-level `.py` files are), and the
Run Script picker lists them automatically.

There are exactly two halves:

    board_code()   ordinary Python that runs ON THE BOARD. Sent once at
                   startup by board.define(); its imports, variables and
                   functions become board-side globals.
    main()         runs on the PC. Reads the gamepad and calls the functions
                   board_code() defined, one at a time, over the radio.

Things that bite, all measured (CLAUDE.md finding #21):

* Live mode **stops `/main.py`**; quitting restarts it from the top. This
  script owns the robot while it runs.
* Commands run **one at a time, in order**. A sensor read sent "during" a drive
  pulse actually runs after it.
* A snippet that raises returns **nothing** -- no traceback crosses. If a
  command silently does nothing, check the USB console.
* Every command is a radio round trip. Fine for driving and testing; not for a
  match.

`live` and `pc_gamepad` live in the extension's `scripts/` folder, not next to
this file. `_bootstrap()` puts that folder on `sys.path` at runtime; the
extension adds it to `python.analysis.extraPaths` for the editor (run
`NovaPi: Add API Stubs to Python Settings` once if imports are underlined).
Set `NOVAPI_SCRIPTS` if the extension repo is not the sibling `../NovaPi`.
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

PULSE = 0.18        # seconds a drive command holds before the board stops itself
POWER = 30          # 0..100
BOOST = 1.6         # multiplier while the right trigger is held


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

    # TODO: your mechanisms go here, e.g.
    #   from mbuild import power_expand_board
    #   def intake(on):
    #       power_expand_board.set_power('DC1', 30 if on else 0)


# ------------------------------------------------------------------- PC side --

def mecanum(fwd, strafe, rot, power):
    """Axes in [-1, 1] -> (upper_left, lower_left, upper_right, lower_right).

    Right side is mounted mirrored, hence the flipped signs. When the axes
    combine past full scale the whole vector is scaled down instead of one wheel
    being clipped -- clipping one wheel changes the direction the robot travels.
    """
    ul = fwd - strafe + rot
    ll = fwd + strafe + rot
    ur = -fwd - strafe + rot
    lr = -fwd + strafe + rot
    peak = max(abs(ul), abs(ll), abs(ur), abs(lr))
    if peak > 1.0:
        ul, ll, ur, lr = (v / peak for v in (ul, ll, ur, lr))
    return tuple(max(-100, min(100, int(round(v * power))))
                 for v in (ul, ll, ur, lr))


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

    print('driving on %s -- BACK/Select or Ctrl-C to quit' % sys.argv[1])
    if not gamepad.is_connected():
        print('no controller found; plug one in (this keeps polling)')

    last = None
    try:
        while True:
            if gamepad.is_key_pressed('Select'):
                break

            # pc_gamepad speaks the same API as the board's own gamepad:
            # get_joystick returns -100..100 (deadzone already applied),
            # is_key_pressed is True while held.
            fwd = gamepad.get_joystick('Ly') / 100.0
            strafe = gamepad.get_joystick('Lx') / 100.0
            rot = gamepad.get_joystick('Rx') / 100.0
            power = POWER * (BOOST if gamepad.is_key_pressed('R2') else 1.0)

            # TODO: your buttons go here -- call what board_code() defined:
            #   if gamepad.is_key_pressed('L1'):
            #       board.run('intake(1)', reply=False)
            #
            # TODO: reading state works the same way, but it queues behind
            # whatever the board is already doing:
            #   print(board.run("online_debug_respond(motors[0].get_value('speed'))"))

            wheels = mecanum(fwd, strafe, rot, power)

            # Stopped and already stopped: stay quiet, the board is stopped too.
            if wheels == (0, 0, 0, 0) and last == wheels:
                time.sleep(0.05)
                continue

            # The reply is the flow control: the board answers at the START of
            # its pulse, so this blocks until the previous pulse is under way and
            # the send rate can never outrun the board. Firing faster on a fixed
            # tick queues commands the board drains at 1/PULSE per second, and
            # that backlog -- not the radio -- is what becomes steering lag.
            board.run('drive(%d,%d,%d,%d,%r)' % (wheels + (PULSE,)),
                      timeout=PULSE + 1.0, retries=0)
            last = wheels
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
