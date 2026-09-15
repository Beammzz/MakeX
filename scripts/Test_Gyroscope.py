# -*- coding: utf-8 -*-
"""Onboard IMU test -- every reading the gyro/accelerometer has:

    python scripts/Test_Gyroscope.py COM6 [shake_threshold]

or pick it from `NovaPi: Run Script...`, which passes the configured COM port as
the first argument. The optional second argument is the shake sensitivity
(0..100, default 50; 0 disables shake detection).

One line is redrawn in place, e.g.

    yaw   12.3 pit   -1.2 rol    0.4 | rate    0.1   -0.3   45.2 d/s | accel   0.01  -0.02   1.00 g  |a| 1.00 | 31.5C | -     | drift   +1.4 d/min

    yaw/pit/rol   get_yaw / get_pitch / get_roll, in degrees.
    rate          get_gyroscope('x'/'y'/'z'), angular velocity in deg/s.
    accel         get_acceleration('x'/'y'/'z'), in g. |a| is the magnitude:
                  it should read ~1.00 while the robot sits still, whatever
                  angle it sits at, so it is the quickest sanity check the
                  accelerometer has.
    C             get_temperature(), the IMU die -- not the room.
    shake         is_shaked(); shown as SHAKE and held lit for HOLD seconds,
                  because the event can otherwise land between two polls.
    drift         how fast yaw has walked since the last reset, in deg/min.

Yaw is integrated from the Z gyro alone -- the board is a 6-axis IMU with no
compass -- so it drifts, and the official docs say not to trust it as a true
heading. `drift` is there to put a number on that for this board: set the robot
down, press R, leave it alone for a minute and read it.

Keys: R resets all three angles, Z resets yaw only, ESC quits.

Two halves:

    board_code()   ordinary Python that runs ON THE BOARD. Sent once at
                   startup by board.define(); its imports, variables and
                   functions become board-side globals.
    main()         runs on the PC. Polls the functions board_code() defined,
                   one command at a time, over the radio.

Live mode **stops `/main.py`** while this runs and restarts it from the top on
exit, so this script owns the board. A snippet that raises returns nothing --
check the USB console if a command silently does nothing.

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

POLL = 0.10             # seconds between reads
HOLD = 1.0              # seconds a shake stays lit on screen
DEFAULT_SHAKE = 50      # 0..100, the firmware default

# Virtual-key codes for GetAsyncKeyState (same table style as Test_Shooter.py).
VK = {'R': 0x52, 'Z': 0x5A, 'ESC': 0x1B}

_user32 = ctypes.windll.user32 if sys.platform == 'win32' else None


def down(key):
    """True while `key` is held. Always False where there is no key-state API,
    so the readout still runs on another platform -- only the resets go away."""
    if _user32 is None:
        return False
    return bool(_user32.GetAsyncKeyState(VK[key]) & 0x8000)


# ---------------------------------------------------------------- board side --

def board_code():
    """Runs on the BOARD, not here. Everything it defines stays available.

    Write it like any other Python file -- autocomplete and error checking work
    the same. Just keep in mind it executes on a NovaPi: no threads, and only
    the modules the firmware has.
    """
    import novapi

    def setup(threshold):
        """Set shake sensitivity and zero the angles, so the run starts from a
        known state. The reply is also the proof the gyro answered at all."""
        novapi.set_shake_threshold(threshold)
        novapi.reset_rotation('all')
        online_debug_respond(1)

    def read():
        """Every reading in one command: 11 comma-separated fields.

        One command rather than eleven because each one is a radio round trip,
        and readings from different trips are not the same instant."""
        online_debug_respond(
            '%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.3f,%.3f,%.3f,%.1f,%d' % (
                novapi.get_yaw(), novapi.get_pitch(), novapi.get_roll(),
                novapi.get_gyroscope('x'), novapi.get_gyroscope('y'),
                novapi.get_gyroscope('z'),
                novapi.get_acceleration('x'), novapi.get_acceleration('y'),
                novapi.get_acceleration('z'),
                novapi.get_temperature(), 1 if novapi.is_shaked() else 0))

    def reset(axis):
        novapi.reset_rotation(axis)
        online_debug_respond(1)


# ------------------------------------------------------------------- PC side --

def reading_of(reply, previous):
    """Pull the 11 fields out of a board reply. Keeps `previous` when the reply
    is missing or malformed, so one lost frame does not blank the display."""
    if not reply:
        return previous
    fields = reply.split(',')
    if len(fields) != 11:
        return previous
    try:
        return [float(v) for v in fields]
    except ValueError:
        return previous


def line(r, shaking, drift):
    yaw, pitch, roll, wx, wy, wz, ax, ay, az = r[:9]
    mag = (ax * ax + ay * ay + az * az) ** 0.5
    return ('yaw %6.1f pit %6.1f rol %6.1f | rate %6.1f %6.1f %6.1f d/s | '
            'accel %6.2f %6.2f %6.2f g  |a| %4.2f | %4.1fC | %-5s | drift %s'
            % (yaw, pitch, roll, wx, wy, wz, ax, ay, az, mag, r[9],
               'SHAKE' if shaking else '-',
               '   ---     ' if drift is None else '%+6.1f d/min' % drift))


def main():
    if len(sys.argv) < 2:
        sys.exit('Usage: %s <port> [shake_threshold]'
                 % os.path.basename(sys.argv[0]))
    threshold = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_SHAKE

    board = Live(sys.argv[1])
    board.mode(MODE_LIVE)                   # stops /main.py
    try:
        board.define(board_code)            # ships the function above
    except IOError as exc:
        board.mode(MODE_RUN)
        board.close()
        sys.exit(str(exc))

    if board.run('setup(%d)' % threshold) is None:
        board.mode(MODE_RUN)
        board.close()
        sys.exit('the gyro did not answer -- check the USB console.')

    print('onboard IMU on %s, shake threshold %d -- angles zeroed'
          % (sys.argv[1], threshold))
    print('R resets all angles, Z resets yaw only, ESC or Ctrl-C quits')

    reading = [0.0] * 11
    shaken_at = 0.0
    zeroed_at = time.time()
    held = set()
    try:
        while True:
            for key in ('R', 'Z', 'ESC'):
                if not down(key):
                    held.discard(key)
                    continue
                if key in held:             # act on the press, not on the hold
                    continue
                held.add(key)
                if key == 'ESC':
                    return
                board.run('reset(%r)' % ('all' if key == 'R' else 'z'))
                zeroed_at = time.time()

            reading = reading_of(board.run('read()', timeout=1.5, retries=0), reading)
            now = time.time()
            if reading[10]:
                shaken_at = now
            # Drift is yaw over time since the reset put it at zero. Under a few
            # seconds of baseline the number swings wildly, so it stays blank.
            elapsed = now - zeroed_at
            drift = reading[0] / elapsed * 60.0 if elapsed > 5.0 else None
            sys.stdout.write('\r' + line(reading, now - shaken_at < HOLD, drift) + '  ')
            sys.stdout.flush()
            time.sleep(POLL)
    except KeyboardInterrupt:
        pass
    finally:
        board.mode(MODE_RUN)                # restarts /main.py
        board.close()
        print('\nstopped; board back in run mode.')


if __name__ == '__main__':
    main()
