# -*- coding: utf-8 -*-
"""Drive this robot from the PC:  python scripts/novapi_teleop.py COM6

Add --keyboard to ignore an attached Xbox controller and use W/A/S/D + Q/E.

This is a launcher, not a copy. The real script lives in the NovaPi Companion
extension repo (scripts/teleop.py) beside live.py and xinput.py, which it
imports -- so there is nothing here that can drift out of date. Set
NOVAPI_SCRIPTS if that repo is not the sibling ../NovaPi.

It sits in scripts/ rather than beside main.py on purpose: "NovaPi: Run"
uploads every top-level .py in the project to the board's flash, and this is
PC-side code (pyserial, ctypes) that has no business being up there.

The `novapi_` prefix keeps these launchers from shadowing the modules they
launch -- see novapi_live.py, where a plain `live.py` here broke
`from live import Live` in every sibling script. Don't drop it.
"""
import os
import runpy
import sys

SCRIPT = 'teleop.py'

_here = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.environ.get('NOVAPI_SCRIPTS') or os.path.abspath(
    os.path.join(_here, '..', '..', 'NovaPi', 'scripts'))
_target = os.path.join(SCRIPTS, SCRIPT)

if not os.path.isfile(_target):
    sys.exit('Could not find %s in %s\nSet NOVAPI_SCRIPTS to the NovaPi '
             "extension's scripts folder." % (SCRIPT, SCRIPTS))

# run_name='__main__' so the target behaves exactly as it does when run
# directly, including its own argument checks and error handling.
sys.path.insert(0, SCRIPTS)
runpy.run_path(_target, run_name='__main__')
