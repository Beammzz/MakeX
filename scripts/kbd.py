"""Held-key state for the PC-side scripts: down('W') is True while W is held.

Windows: GetAsyncKeyState, true key state, works even when another window has
focus.

Linux/macOS: a terminal only delivers key-down events (no key-up), so a key
counts as held while its auto-repeat keeps arriving. The first press is held
for FIRST_HOLD, which has to outlast the OS repeat delay (~0.6 s) or the key
would drop out between the first event and the first repeat; once repeating,
a key that stops for REPEAT_HOLD counts as released. Only the terminal running
the script gets the keys, so there is no focus problem, and a tap reads as
held for FIRST_HOLD. SHIFT is guessed from an upper-case letter.
"""
import sys
import time

# Virtual-key codes for GetAsyncKeyState. 0xDB and 0xDD are [ and ] on a US
# layout.
VK = {'UP': 0x26, 'DOWN': 0x28, 'LEFT': 0x25, 'RIGHT': 0x27,
      'SPACE': 0x20, 'ESC': 0x1B, 'SHIFT': 0x10, '[': 0xDB, ']': 0xDD}
VK.update((c, ord(c)) for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')

FIRST_HOLD = 0.65
REPEAT_HOLD = 0.12
STREAK_GAP = 0.7            # a longer pause starts a new press

_ARROWS = {'A': 'UP', 'B': 'DOWN', 'C': 'RIGHT', 'D': 'LEFT'}

if sys.platform == 'win32':
    import ctypes
    _user32 = ctypes.windll.user32

    def available():
        return True

    def down(key):
        return bool(_user32.GetAsyncKeyState(VK[key]) & 0x8000)

else:
    import atexit
    import os
    import select

    _seen = {}              # key -> (time of last event, events in this streak)
    _state = {'ready': False, 'old': None}

    def _setup():
        _state['ready'] = True
        try:
            import termios
            import tty
            fd = sys.stdin.fileno()
            if not os.isatty(fd):
                return
            _state['old'] = termios.tcgetattr(fd)
            tty.setcbreak(fd)               # no echo, no line buffering, Ctrl-C still works
            atexit.register(termios.tcsetattr, fd, termios.TCSADRAIN, _state['old'])
        except (ImportError, OSError, ValueError):
            _state['old'] = None

    def available():
        if not _state['ready']:
            _setup()
        return _state['old'] is not None

    def _mark(key, now):
        last, n = _seen.get(key, (0.0, 0))
        _seen[key] = (now, n + 1 if now - last < STREAK_GAP else 1)

    def _drain(now):
        fd = sys.stdin.fileno()
        while select.select([fd], [], [], 0)[0]:
            data = os.read(fd, 64).decode('utf-8', 'ignore')
            if not data:
                return
            i = 0
            while i < len(data):
                c = data[i]
                if c == '\x1b':
                    if data[i + 1:i + 2] in ('[', 'O') and data[i + 2:i + 3] in _ARROWS:
                        _mark(_ARROWS[data[i + 2]], now)
                        i += 3
                        continue
                    if data[i + 1:i + 2] in ('[', 'O'):
                        i += 3          # some other escape sequence, skip it
                        continue
                    _mark('ESC', now)
                elif c == ' ':
                    _mark('SPACE', now)
                elif c.isalpha() or c.isdigit() or c in '[]':
                    if c.isupper():
                        _mark('SHIFT', now)
                    _mark(c.upper(), now)
                i += 1

    def down(key):
        if not available():
            return False
        now = time.time()
        _drain(now)
        last, n = _seen.get(key, (0.0, 0))
        return now - last < (FIRST_HOLD if n == 1 else REPEAT_HOLD)
