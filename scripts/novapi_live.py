# -*- coding: utf-8 -*-
"""Run Python on the board from this project folder, over USB or the dongle:

    python scripts/novapi_live.py COM6              interactive REPL
    python scripts/novapi_live.py COM6 ls           recursive listing, sizes
    python scripts/novapi_live.py COM6 cat /flash/main.py
    python scripts/novapi_live.py COM6 rm /flash/old.py
    python scripts/novapi_live.py COM6 reset        makeblock.reset()

Launcher only -- see scripts/novapi_teleop.py in this folder for why. Set
NOVAPI_SCRIPTS if the extension repo is not the sibling ../NovaPi.

**The `novapi_` prefix is load-bearing.** Named plain `live.py`, this file would
sit in the same folder as your own scripts and *shadow* the real `live` module
for all of them: `from live import Live` resolves to this launcher, which has no
`Live` in it, and the editor underlines the import. Don't drop the prefix.

Live mode stops /main.py while the session is open and restarts it from the top
on exit, so this owns the board while it runs.
"""
import os
import runpy
import sys

SCRIPT = 'live.py'

_here = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.environ.get('NOVAPI_SCRIPTS') or os.path.abspath(
    os.path.join(_here, '..', '..', 'NovaPi', 'scripts'))
_target = os.path.join(SCRIPTS, SCRIPT)

if not os.path.isfile(_target):
    sys.exit('Could not find %s in %s\nSet NOVAPI_SCRIPTS to the NovaPi '
             "extension's scripts folder." % (SCRIPT, SCRIPTS))

sys.path.insert(0, SCRIPTS)
runpy.run_path(_target, run_name='__main__')
