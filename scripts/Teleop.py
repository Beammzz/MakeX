# -*- coding: utf-8 -*-
"""Drive the robot from the PC, and fire `Guzzchan.auto()` without leaving teleop.

A copy of the extension's `teleop.py` with one thing added: a button that reads
`main.py` off the disk, ships its classes to the board and calls
`Guzzchan.auto(side)` there, then hands the sticks back. Copied rather than
imported because the extension's script is not ours to edit, and because it is
worth reading -- everything under HOW THE DRIVING WORKS is its original text.

    python scripts/Teleop.py COM6
    python scripts/Teleop.py COM6 --keyboard

    W / S   forward / backward        Q / E   rotate left / right
    A / D   strafe left / right       SHIFT   boost      SPACE  stop
    1..5    set power 20/30/40/50/60  ESC     quit (stops motors, restarts main.py)
    Z       flip the auto side, L <-> R
    X       run auto on that side -- re-reads main.py first

    Xbox: left stick drives/strafes, right stick X rotates, RT boost,
          B stop, BACK or ESC quit, Y flips the side, X runs auto.
          1..5 still set power.

Motor ports follow main.py: M1 upper-left, M2 lower-left, M3 upper-right,
M4 lower-right, all INDEX1, right side mirrored.

Keys count only while the terminal running this script has focus, so typing W in
the editor or a browser cannot drive the robot; click back into the terminal to
take the sticks. Losing focus reads as all-keys-up, which the deadman turns into
a stop. A gamepad is read whatever has focus -- it is not the machine's keyboard.


AUTO
====

**The file is read when you press X, not when you save it.** That is the whole
point of the button: a half-written `auto()` sitting in the editor is nothing to
the board until you ask for it, so saving mid-session can never light the board
up red in the middle of a drive. Nothing is watched, nothing uploads in the
background.

**A main.py that does not compile never leaves the PC.** `board_program()`
parses it here with `ast`, so a typo costs a printed SyntaxError and the drive
carries on; the board is not touched at all. Only source that already parses is
shipped.

**What gets shipped is main.py's imports and classes, not main.py.** The banner
print, `robot = Guzzchan()` and the match loop are dropped -- the board builds
its own `Guzzchan` and calls `auto(side)` on it, which is the same code path the
real match takes minus `power_manage_module.is_auto_mode()`. Note that main.py's
own loop calls `auto("Left")` while `auto()` compares against `"L"`; `SIDES`
below holds what the comparison actually wants.

**The classes really are live board-side, not re-sent per call.** The source
is reassembled into `_S` and `exec`d, which binds `Wheel`, `Shooter`,
`conveyor` and `Guzzchan` -- and the `mbuild` imports their methods resolve
against -- into the board's live-mode globals, and those persist for the whole
session. That is live.py's own chunked path: every `define()` body over 240
bytes takes it, which is every board_code in this repo. `load()` proves it
rather than trusting it, by naming the class from a *different* frame than the
one that exec'd it, then frees `_S` and reports the RAM auto has left.

**Roughly 10 KB goes over the radio in ~67 frames, about 3 seconds.** So the
source last sent is remembered and re-sent only when the file really changed:
edit, press X, wait ~3 s; press X again and auto starts immediately.

**Auto cannot be interrupted from here.** Live mode runs one request at a time,
so while `auto()` runs board-side the PC is blocked waiting for its reply and
any stop you send just queues behind it. The robot's power switch is the abort.
`AUTO_TIMEOUT` bounds how long this script waits, not how long the board runs.

`live` and `xinput` live in the extension's `scripts/` folder, not next to this
file; `_bootstrap()` puts that folder on `sys.path`. Set `NOVAPI_SCRIPTS` if the
extension repo is not the sibling `../NovaPi`.


HOW THE DRIVING WORKS  (from the extension's teleop.py)
=======================================================

Built on live mode (see live.py): the board is put in live mode, a `_d()` helper
is defined once board-side, and each poll sends a tiny `_d(ul, ll, ur, lr)`
frame.

**The command rate is 1/PULSE, not the radio's speed.** Live mode runs one
request at a time, and `_d` spends PULSE seconds asleep inside its own call, so
the next command cannot start until that sleep ends. Measured over the dongle:
a bare round trip is 38 ms median / 45 ms worst (~26 Hz of headroom), while the
achieved command rate tracked 1/PULSE exactly -- 5.6 Hz at PULSE 0.18, 10.3 at
0.10, 13.2 at 0.08, 16.6 at 0.06, with no dropped replies at any of them. Hence
the default below; `--pulse` exists because the right value depends on the link
and on how long the four `set_power` calls take on a given robot.

**The board stops itself.** Live mode cannot spawn a watchdog thread
(`_thread.start_new_thread` raises there) and the motor API has no timed move,
so the deadman is built into the command: `_d` sets power, sleeps PULSE, then
stops. Nothing arriving for PULSE seconds means the wheels stop -- a crashed PC,
a yanked dongle or a closed laptop all fail safe.

**The board sets the pace, not a fixed tick.** Live-mode requests are queued and
run one at a time, so a command costs the board PULSE seconds no matter how fast
the PC sends. An earlier version fired `_d` every 0.12 s with no reply, which is
~6/s into a board that drains ~4/s: the queue grew, and the steering lag grew
with it. Each `_d` now replies the instant it has set the power, and the loop
waits for that reply, so the send rate matches the board exactly and the queue
never holds more than one command.

Because live mode stops /main.py, your MakeX program is NOT running while you
drive; this owns the robot outright. Exiting puts the board back in mode 0,
which restarts /main.py from the top.

An Xbox controller is used automatically when one is plugged in (see xinput.py);
pass --keyboard to force keys. Analog sticks suit mecanum better than keys,
since strafe wants proportional input.
"""
import ast
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

from live import Live, MODE_LIVE, MODE_RUN            # noqa: E402  (needs sys.path)
from xinput import Controller, find as xinput_find    # noqa: E402

# Board-side auto-stop, the deadman -- and the loop's tick, since the board is
# busy for exactly this long per command. 0.08 s is ~13 Hz with ~55 ms of slack
# for the PC to answer in (measured worst-case round trip: 45 ms). Going lower
# keeps working right down to 0.06 s; it just leaves less room for a late reply,
# and a reply that misses its slot costs one skipped pulse -- the wheels stop
# for a gap and pick up again, which is a stutter, not a runaway.
DEFAULT_PULSE = 0.08
IDLE_TICK = 0.05        # poll interval while stopped (nothing is in flight)
DEFAULT_POWER = 30
BOOST = 1.6

# main.py sits one level up from scripts/; that is the file the auto button reads.
MAIN_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'main.py')
# The class the auto button builds and calls auto() on.
ENTRY = 'Guzzchan'
# What `Guzzchan.auto()` compares `side` against, in the order the button cycles.
SIDES = ('L', 'R')
# How long to wait for auto to say it finished. A MakeX auto period is 30 s;
# this only bounds the wait, the board keeps running either way.
AUTO_TIMEOUT = 45.0


# Board-side setup, one small statement per frame. Live-mode globals persist for
# the session, so this runs once. Deliberately NOT one big blob: a single
# oversized source has to go through live.py's chunked `exec` path, which failed
# here for reasons not worth chasing when four short frames just work -- and
# stepwise, each frame's reply confirms that part landed.
def setup_steps(pulse):
    return [
        "import time\n"
        "from mbuild.encoder_motor import encoder_motor_class as _E\n"
        "online_debug_respond('imported')",

        "_M = [_E('M1','INDEX1'), _E('M2','INDEX1'),"
        " _E('M3','INDEX1'), _E('M4','INDEX1')]\n"
        "online_debug_respond(len(_M))",

        "def _s():\n"
        " for m in _M:\n"
        "  m.stop()\n"
        "online_debug_respond('stop ok')",

        # Responds as soon as the power is set, BEFORE the pulse sleep. That reply
        # is the PC's go-ahead to send the next command, which then queues while
        # this one is still sleeping -- so the board rolls straight from one pulse
        # into the next with no radio round trip in between, and the queue never
        # holds more than one command. Responding after the sleep instead would
        # leave the wheels stopped for a round trip on every pulse.
        "def _d(a,b,c,d,t=%r):\n"
        " for i in range(4):\n"
        "  _M[i].set_power((a,b,c,d)[i])\n"
        " online_debug_respond(1)\n"
        " time.sleep(t)\n"
        " _s()\n"
        "online_debug_respond('drive ok')" % pulse,
    ]


# Virtual-key codes for GetAsyncKeyState. msvcrt only reports keypress events,
# with the OS auto-repeat delay in the way; this reports true held-key state,
# which is what makes holding W feel like holding W.
VK = {'W': 0x57, 'A': 0x41, 'S': 0x53, 'D': 0x44, 'Q': 0x51, 'E': 0x45,
      'Z': 0x5A, 'X': 0x58,
      'SHIFT': 0x10, 'SPACE': 0x20, 'ESC': 0x1B,
      '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34, '5': 0x35}

_user32 = ctypes.windll.user32 if sys.platform == 'win32' else None
_kernel32 = ctypes.windll.kernel32 if sys.platform == 'win32' else None
if _user32 is not None:
    # Handles are pointer-sized; the default int restype truncates them on 64-bit.
    _user32.GetForegroundWindow.restype = ctypes.c_void_p
    _kernel32.GetConsoleWindow.restype = ctypes.c_void_p
    _kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    _kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    for _f in ('Process32First', 'Process32Next'):
        getattr(_kernel32, _f).argtypes = [ctypes.c_void_p, ctypes.c_void_p]


class _PROCESSENTRY32(ctypes.Structure):
    """One process from CreateToolhelp32Snapshot; only the two PIDs are read."""
    _fields_ = [('dwSize', ctypes.c_ulong),
                ('cntUsage', ctypes.c_ulong),
                ('th32ProcessID', ctypes.c_ulong),
                ('th32DefaultHeapID', ctypes.c_size_t),
                ('th32ModuleID', ctypes.c_ulong),
                ('cntThreads', ctypes.c_ulong),
                ('th32ParentProcessID', ctypes.c_ulong),
                ('pcPriClassBase', ctypes.c_long),
                ('dwFlags', ctypes.c_ulong),
                ('szExeFile', ctypes.c_char * 260)]


def _own_pids():
    """This process' PID and every ancestor's, walked once at startup.

    The window the keys actually go to is not ours: VS Code's terminal is drawn
    by Code.exe, several levels up the tree (Code.exe -> shell -> python.exe),
    and Windows Terminal has the same shape. Comparing the foreground window's
    process against our whole ancestry recognises the host without naming any
    host in particular.

    The walk stops below explorer.exe, which is the one ancestor that is not a
    terminal host: it owns the desktop and every File Explorer window, so
    counting it would hand the robot back to any folder window.
    """
    pids = {os.getpid()}
    snap = _kernel32.CreateToolhelp32Snapshot(0x2, 0)       # TH32CS_SNAPPROCESS
    if not snap:
        return pids
    tree = {}
    try:
        entry = _PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(entry)
        ok = _kernel32.Process32First(snap, ctypes.byref(entry))
        while ok:
            tree[entry.th32ProcessID] = (entry.th32ParentProcessID,
                                         entry.szExeFile.decode('mbcs', 'replace'))
            ok = _kernel32.Process32Next(snap, ctypes.byref(entry))
    finally:
        _kernel32.CloseHandle(snap)
    pid = tree.get(os.getpid(), (0, ''))[0]
    while pid and pid not in pids:      # `not in` also breaks a PID-reuse cycle
        parent, name = tree.get(pid, (0, ''))
        if name.lower() == 'explorer.exe':
            break
        pids.add(pid)
        pid = parent
    return pids


_OWN_PIDS = _own_pids() if _user32 is not None else set()


def focused():
    """True while the terminal running this script owns the keyboard.

    GetAsyncKeyState reports the state of the machine's keyboard, not of a
    window, so without this W typed anywhere -- the editor, a browser -- drives
    the robot. The foreground window is either our own console (a plain conhost
    window, which a ConPTY host such as VS Code does not have) or a window of a
    process hosting us, hence the two checks.
    """
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return False
    if hwnd == _kernel32.GetConsoleWindow():
        return True
    pid = ctypes.c_ulong()
    _user32.GetWindowThreadProcessId(ctypes.c_void_p(hwnd), ctypes.byref(pid))
    return pid.value in _OWN_PIDS


def down(key):
    """Held-key state, but only while our terminal is in front."""
    return focused() and bool(_user32.GetAsyncKeyState(VK[key]) & 0x8000)


def mecanum(fwd, strafe, rot, power):
    """Turn axes in [-1, 1] into (ul, ll, ur, lr), mirroring main.py.

    Combining axes can push a wheel past full scale; the whole vector is scaled
    down rather than clamped per wheel, because clamping one wheel changes the
    direction the robot actually travels.
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


def keyboard_axes():
    """(fwd, strafe, rot, boost, stop, quit, run_auto, flip_side) from held keys."""
    fwd = (1.0 if down('W') else 0.0) - (1.0 if down('S') else 0.0)
    strafe = (1.0 if down('D') else 0.0) - (1.0 if down('A') else 0.0)
    rot = (1.0 if down('E') else 0.0) - (1.0 if down('Q') else 0.0)
    return (fwd, strafe, rot, down('SHIFT'), down('SPACE'), down('ESC'),
            down('X'), down('Z'))


def gamepad_axes(pad):
    """Same tuple, from an Xbox controller.

    Left stick drives and strafes, right stick X rotates, RT boosts, B stops,
    BACK quits, X runs auto and Y flips the side. Falls back to zeros (not a
    crash) if the pad is unplugged mid-session, which the deadman then turns
    into a stop.
    """
    s = pad.read()
    if s is None:
        return 0.0, 0.0, 0.0, False, True, False, False, False
    return (s['ly'], s['lx'], s['rx'],
            s['rt'] > 0.5, 'B' in s['buttons'], 'BACK' in s['buttons'],
            'X' in s['buttons'], 'Y' in s['buttons'])


def pressed(prev, name, now):
    """Rising edge: True once per press, however long the button is held.

    The loop polls at up to ~13 Hz, so without this one press of X would ask for
    auto a dozen times over. `prev` is a dict the caller keeps.
    """
    fired = now and not prev.get(name, False)
    prev[name] = now
    return fired


# ------------------------------------------------------------------- auto --

def board_program(path):
    """main.py's top-level imports, classes and functions, as one source string.

    Parsing here is the point: a main.py that does not compile raises
    SyntaxError on the PC, before a single frame is sent. What is dropped is
    everything that is not a definition -- the banner print, `robot =
    Guzzchan()` and the match loop -- because the board builds its own Guzzchan
    and calls auto() on it.
    """
    with open(path, encoding='utf-8') as fh:
        src = fh.read()
    lines = src.split('\n')
    kept = [n for n in ast.parse(src, path).body
            if isinstance(n, (ast.Import, ast.ImportFrom,
                              ast.ClassDef, ast.FunctionDef))]
    if not kept:
        raise IOError('%s has no classes to send' % path)
    return '\n'.join('\n'.join(lines[n.lineno - 1:n.end_lineno])
                     for n in kept) + '\n'


class Auto(object):
    """Loads main.py's classes onto the board on demand and runs auto() there.

    Reading is tied to the button and nothing else: no watcher, no upload on
    save. Between presses the board holds whatever was last sent, so a broken
    editor buffer is invisible to it.
    """

    def __init__(self, lv, path):
        self.lv = lv
        self.path = path
        self.sent = None        # the source the board currently holds

    def load(self, src):
        """Ship the classes if they changed. True if the board was re-loaded."""
        if src == self.sent:
            return False
        self.sent = None        # a load that fails halfway must not look cached
        free = self.lv.run('import gc\ngc.collect()\n'
                           'online_debug_respond(gc.mem_free())')
        print('  sending %d bytes of main.py (%s bytes free board-side)'
              % (len(src.encode('utf-8')), free or '?'))
        self.lv.send_source(src)        # raises IOError if a fragment is lost
        # exec(_S) is live.py's own chunked path -- the one define() takes for
        # any board_code over 240 bytes, which is every board_code in this repo
        # (Tune_Teleop 1.1 KB, Test_Shooter 2.7 KB, Test_Encoder 2.9 KB). Names
        # it binds land in the board-side globals, and those persist for the
        # session; that is what lets the NEXT frame call Guzzchan(), and what
        # lets each method resolve `encoder_motor_class` and friends when it
        # runs. No reply means the source raised on the way in.
        if self.lv.run("exec(_S)\nonline_debug_respond('loaded')",
                       timeout=20) is None:
            raise IOError('the board did not accept main.py. It parses here, so '
                          'look at the USB console: an import raised, or the '
                          'board ran out of memory part-way through 10 KB.')
        # A separate frame on purpose. Naming the class here, from a frame that
        # is not the one that exec'd it, is the proof that the assumption above
        # held: a bare NameError gets no reply and is reported as exactly that.
        # It also drops the 10 KB of source and says how much RAM auto has left.
        free = self.lv.run("_S = ''\nimport gc\ngc.collect()\n%s\n"
                           "online_debug_respond(gc.mem_free())" % ENTRY)
        if free is None:
            raise IOError('%s did not survive into the board globals: the source '
                          'exec\'d, but the next frame cannot see the class. '
                          'Nothing was run.' % ENTRY)
        print('  loaded, %s bytes free' % free)
        self.sent = src
        return True

    def run(self, side):
        """Read, then stop the wheels, then refresh the code, then run auto(side).

        The read comes first on purpose: a main.py that does not parse costs
        nothing at all -- not a frame, not even the stop -- so pressing X on a
        broken file leaves the drive exactly as it was.
        """
        src = board_program(self.path)
        self.lv.run('_s()', reply=False)
        self.load(src)
        # This is the end-to-end check: __init__ walks Wheel, Shooter and
        # conveyor and every module name they were compiled against, so a reply
        # means the whole graph resolved, not just the one class named above.
        if self.lv.run("_G = %s()\nonline_debug_respond('ready')" % ENTRY,
                       timeout=15) is None:
            raise IOError('%s() would not construct. The classes are loaded, so '
                          'this is __init__ itself -- a servo or motor not '
                          'answering (M1-M4, M5 INDEX1/INDEX2, M6), or a name a '
                          'class body uses. Check the USB console.' % ENTRY)
        # retries=0 is not a detail: a retry here would run the whole auto a
        # second time. A lost reply means "no idea how it went", never "again".
        return self.lv.run("_G.auto(%r)\n_G.stop_all()\nonline_debug_respond('done')"
                           % side, timeout=AUTO_TIMEOUT, retries=0)


def start_auto(auto, side):
    """One press of the auto button. Never lets a bad main.py reach the board."""
    print('\nauto %s: reading %s' % (side, auto.path))
    t0 = time.time()
    try:
        done = auto.run(side)
    except SyntaxError as exc:
        print('  main.py does not compile, nothing was sent:\n    %s' % exc)
    except (IOError, OSError) as exc:
        print('  %s' % exc)
    else:
        print('  auto %s %s after %.1f s'
              % (side, 'finished' if done else 'gave no reply (still running?)',
                 time.time() - t0))
    print('back on the sticks.')


# ------------------------------------------------------------------- main --

def main():
    if _user32 is None:
        sys.stderr.write('Teleop.py uses the Windows key-state API.\n')
        sys.exit(2)
    if len(sys.argv) < 2:
        sys.stderr.write('Usage: Teleop.py <port> [--keyboard] [--pulse SECONDS]\n')
        sys.exit(2)

    pulse = DEFAULT_PULSE
    if '--pulse' in sys.argv:
        try:
            pulse = float(sys.argv[sys.argv.index('--pulse') + 1])
        except (IndexError, ValueError):
            sys.stderr.write('--pulse wants a number of seconds, e.g. --pulse 0.1\n')
            sys.exit(2)
        # The pulse IS the deadman, so it is clamped rather than trusted: too
        # long leaves the robot driving itself for that long after the PC dies,
        # too short and every pulse ends before its successor is queued.
        pulse = max(0.03, min(0.5, pulse))

    # An Xbox pad is used when one is plugged in; the keyboard is the fallback,
    # so teleop still works with nothing but a laptop. Search all four XInput
    # slots -- a pad does not always land in slot 0.
    pad = None
    if '--keyboard' not in sys.argv:
        idx = xinput_find()
        pad = Controller(idx) if idx is not None else None

    lv = Live(sys.argv[1])
    lv.mode(MODE_LIVE)
    for step in setup_steps(pulse):
        if lv.run(step, timeout=6) is None:
            lv.mode(MODE_RUN)
            lv.close()
            sys.stderr.write('The board did not accept this setup step:\n\n%s\n\n'
                             'Is it powered on, and are the motors plugged into '
                             'M1-M4?\n' % step)
            sys.exit(1)

    auto = Auto(lv, MAIN_PY)
    side = SIDES[0]
    power = DEFAULT_POWER
    # The key table is only written once, in the docstring; this prints that
    # same block, cut between the usage lines above it and the note below it.
    print(__doc__.split('--keyboard\n', 1)[1]
                 .split('\n\nMotor ports', 1)[0].strip('\n'))
    print('\npower %d%%  pulse %.0f ms  --  live mode is on, /main.py is stopped.'
          % (power, pulse * 1000))
    print('input: %s   auto side: %s   auto from: %s'
          % ('Xbox controller' if pad else 'keyboard', side, MAIN_PY))
    prev = {}
    last = None
    had_focus = True
    try:
        while True:
            # Say why the keys went dead, once per change; without a word here a
            # click into the editor just looks like the robot stopped answering.
            if not pad and focused() != had_focus:
                had_focus = not had_focus
                print('\n%s' % ('keys live again.' if had_focus else
                                'terminal lost focus -- keys ignored, robot '
                                'stopped. Click the terminal to drive.'))
            (fwd, strafe, rot, boost, stop, quit_,
             run_auto, flip_side) = gamepad_axes(pad) if pad else keyboard_axes()
            if quit_ or (pad and down('ESC')):
                break
            for k in '12345':
                if down(k):
                    power = 10 + 10 * int(k)
            if pressed(prev, 'side', flip_side):
                side = SIDES[(SIDES.index(side) + 1) % len(SIDES)]
                print('\nauto side: %s' % side)
            if pressed(prev, 'auto', run_auto):
                start_auto(auto, side)
                last = None     # board is stopped; resend whatever comes next
                continue
            if stop:
                fwd = strafe = rot = 0.0
            v = mecanum(fwd, strafe, rot, power * (BOOST if boost else 1.0))
            # Resend while moving so pulses overlap; when stopped, send the zero
            # once and then stay quiet -- the board is already stopped.
            if v == (0, 0, 0, 0) and last == v:
                time.sleep(IDLE_TICK)
                continue
            # reply=True is the flow control: the board answers at the START of
            # its pulse, so this blocks until the previous pulse is under way
            # and the send rate can never outrun the board. Sending faster
            # (reply=False on a fixed tick) queues commands the board can only
            # drain at 1/PULSE per second, and the backlog -- not the radio --
            # is what turns into seconds of steering lag.
            t0 = time.time()
            lv.run('_d(%d,%d,%d,%d)' % v, timeout=pulse + 1.0, retries=0)
            dt = time.time() - t0
            sys.stdout.write('\r%-58s' % ('power %d%%  auto %s  %s  %.0f Hz'
                                          % (power, side, v, 1.0 / dt if dt else 0)))
            sys.stdout.flush()
            last = v
    except KeyboardInterrupt:
        pass
    finally:
        lv.run('_s()', reply=False)
        time.sleep(0.1)
        lv.mode(MODE_RUN)          # restarts /main.py
        lv.close()
        print('\nstopped; board back in run mode.')


if __name__ == '__main__':
    main()
