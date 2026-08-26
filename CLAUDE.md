# iLarb Robotics MakeX — "Guzzchan"

MicroPython on the NovaPi controller. Nothing here runs on a PC: there are no
tests, and `python main.py` fails on the `mbuild` imports. Verification means
deploying to the board and driving it.

## Read the hardware docs first
`docs/` is the mbuild API reference (Thai), one file per module: encoder_motor,
smartservo, gamepad, dual_rgb_sensor, ranging_sensor, onboard_gyro_sensor,
power_expand_board, power_manage_module, timer. Check the relevant file for
method names, parameter ranges, and sign conventions instead of guessing.

## Layout
- `main.py` — teleop + auto. The only file that runs on the robot; only
  top-level `.py` files get uploaded.
- `scripts/` — PC-side live-control and test scripts run over the radio, never
  uploaded. Copy `scripts/template.py` for a new one and read its docstring:
  live mode stops `/main.py` while it runs.
- `docs/` — hardware API reference (above).
- `old_code/` — previous versions, for reference. Read, never edit.
- `Note.md` — current field tuning values (servo offsets, brushless power).

## Conventions
- No central CONFIG block. That convention is gone: hoisting every number to
  the top of the file made field debugging much slower, because a value you
  wanted to change was never next to the code it affected. Keep tuning
  parameters in the class that uses them (see `Wheel` and `Shooter`).
- Motor direction is a sign in the power table, handled in exactly one place.
- Comments in Thai; clear and concise, say what the code does.
- Don't overengineer. Match existing formatting, naming, and comment density.
- MicroPython only: no third-party packages, no `typing`/`dataclasses`.

## Deploy
VS Code build task `NovaPi: Deploy & Serial Monitor` uploads `main.py` over COM
and opens the REPL. The NovaPi Companion extension is optional but recommended.
