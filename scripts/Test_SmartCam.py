# -*- coding: utf-8 -*-
"""Smart Camera label test -- which MakeX tag (3 / 6 / 9 / 12) is in view:

    python scripts/Test_SmartCam.py COM6 [PORT5] [INDEX1]

or pick it from `NovaPi: Run Script...`, which passes the configured COM port as
the first argument. The optional second and third arguments are the mBuild port
and index the camera is plugged into (default PORT5 / INDEX1).

The camera is put in "line" mode, because that is the mode the label reads
belong to -- `set_mode` only accepts "line" and "color", and label/sign/barcode
detection are methods, not modes. Then `detect_label(id)` is polled for the four
tag ids, plus `get_label_x/get_label_y` so a detection can be sanity-checked
against a plausible screen position.

One line is redrawn in place, e.g.

    tag  6   raw 3:- 6:X(88,71) 9:- 12:-      hits 3:0 6:5 9:0 12:0

`tag` is the debounced answer -- an id has to be seen in HITS of the last WINDOW
polls before it is called, and `no tag` shows when none of them clears that bar.
`raw` is the unfiltered read of this poll, `hits` the counters behind `tag`.

Heads up, from the stub's own measurements (`../NovaPi/stubs/mbuild/
smart_camera.pyi`): on the camera that was probed the whole label path read
inert -- `detect_label` / `get_label_x` / `get_label_y` returned False/0 in 18
reads out of 18, with the marker in frame and out of it. If this script only
ever prints `no tag`, that is the thing to check first: teach the tags with the
button on the side of the camera, confirm `learn?` prints yes, and only then
suspect this code. `learn?` in the header is `get_learn_status()`, read once at
startup.

Two halves:

    board_code()   ordinary Python that runs ON THE BOARD. Sent once at
                   startup by board.define(); its imports, variables and
                   functions become board-side globals.
    main()         runs on the PC. Polls the function board_code() defined,
                   one command at a time, over the radio.

Live mode **stops `/main.py`** while this runs and restarts it from the top on
exit, so this script owns the board. A snippet that raises returns nothing --
check the USB console if a command silently does nothing.

`live` lives in the extension's `scripts/` folder, not next to this file;
`_bootstrap()` puts that folder on `sys.path`. Set `NOVAPI_SCRIPTS` if the
extension repo is not the sibling `../NovaPi`.
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

from live import (Live, MODE_LIVE, MODE_RUN,    # noqa: E402  (needs sys.path first)
                  online_debug_respond)         # board builtin; see live.py

LABELS = (3, 6, 9, 12)      # the MakeX tags, by the clock positions on the field
POLL = 0.20                 # seconds between reads
WINDOW = 5                  # polls kept in the debounce history
HITS = 3                    # of WINDOW polls needed before a tag is called

DEFAULT_PORT = 'PORT2'
DEFAULT_INDEX = 'INDEX1'


# ---------------------------------------------------------------- board side --

def board_code():
    """Runs on the BOARD, not here. Everything it defines stays available.

    Write it like any other Python file -- autocomplete and error checking work
    the same. Just keep in mind it executes on a NovaPi: no threads, and only
    the modules the firmware has.
    """
    from mbuild.smart_camera import smart_camera_class

    labels = (3, 6, 9, 12)
    cam = None

    def setup(port, index):
        """Bind the camera and put it in the mode the label reads live in.

        Done in its own command rather than at define() time so a wrong port is
        one retry away instead of a restart, and so the reply says whether the
        camera answered at all."""
        global cam
        cam = smart_camera_class(port, index)
        cam.set_mode('line')
        online_debug_respond('%d' % (1 if cam.get_learn_status() else 0))

    def scan():
        """'id,detected,x,y' per label, semicolon separated.

        Every read is guarded on its own: the camera methods are decorated
        board-side and return None on anything unexpected, and one None must not
        take the whole reply down with it."""
        out = []
        for label in labels:
            try:
                seen = 1 if cam.detect_label(label) else 0
                x = int(cam.get_label_x(label) or 0)
                y = int(cam.get_label_y(label) or 0)
            except Exception:
                seen, x, y = 0, 0, 0
            out.append('%d,%d,%d,%d' % (label, seen, x, y))
        online_debug_respond(';'.join(out))


# ------------------------------------------------------------------- PC side --

def readings_of(reply, previous):
    """Pull 'id,detected,x,y;...' out of a board reply, one entry per label.
    Keeps `previous` when the reply is missing or malformed, so one lost frame
    does not blank the display."""
    if not reply:
        return previous
    fields = reply.split(';')
    if len(fields) != len(LABELS):
        return previous
    out = {}
    for field in fields:
        try:
            label, seen, x, y = [int(v) for v in field.split(',')]
        except ValueError:
            return previous
        out[label] = (bool(seen), x, y)
    return out


def winner(history):
    """The debounced tag: the label with the most hits in the last WINDOW polls,
    or None when nobody clears HITS. Ties go to the lower id, which is arbitrary
    but stable -- two tags in frame at once is a framing problem, not something
    to pick a side on."""
    best, best_hits = None, 0
    for label in LABELS:
        hits = sum(1 for frame in history if frame.get(label, (False,))[0])
        if hits >= HITS and hits > best_hits:
            best, best_hits = label, hits
    return best


def line(tag, readings, history):
    raw = ' '.join('%d:%s' % (label, 'X(%d,%d)' % (readings[label][1], readings[label][2])
                              if readings[label][0] else '-')
                   for label in LABELS)
    hits = ' '.join('%d:%d' % (label, sum(1 for frame in history
                                          if frame.get(label, (False,))[0]))
                    for label in LABELS)
    return 'tag %-6s raw %s   hits %s' % ('no tag' if tag is None else tag, raw, hits)


def main():
    if len(sys.argv) < 2:
        sys.exit('Usage: %s <port> [PORT5] [INDEX1]'
                 % os.path.basename(sys.argv[0]))
    cam_port = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_PORT
    cam_index = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_INDEX

    board = Live(sys.argv[1])
    board.mode(MODE_LIVE)                   # stops /main.py
    try:
        board.define(board_code)            # ships the function above
    except IOError as exc:
        board.mode(MODE_RUN)
        board.close()
        sys.exit(str(exc))

    learned = board.run('setup(%r,%r)' % (cam_port, cam_index))
    if learned is None:
        board.mode(MODE_RUN)
        board.close()
        sys.exit('the camera on %s/%s did not answer -- check the cable and the port.'
                 % (cam_port, cam_index))

    print('smart camera on %s, %s/%s, mode line -- learn? %s'
          % (sys.argv[1], cam_port, cam_index,
             'yes' if learned.strip() == '1' else 'NO (teach the tags with the '
             'button on the camera first)'))
    print('watching labels %s; Ctrl-C to quit'
          % ', '.join('%d' % label for label in LABELS))

    readings = dict((label, (False, 0, 0)) for label in LABELS)
    history = []
    try:
        while True:
            readings = readings_of(board.run('scan()', timeout=1.5, retries=0), readings)
            history.append(readings)
            del history[:-WINDOW]
            sys.stdout.write('\r' + line(winner(history), readings, history) + '  ')
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
