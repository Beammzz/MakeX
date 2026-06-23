"""
mbuild - MakeX mBuild Modules Package
======================================

Stub package for local development with autocompletion.
This package mirrors the real mbuild package on the NovaPi device.

Sub-modules:
    - encoder_motor   : Encoder motor control (180 / 36 brushless)
    - smartservo       : Smart servo motor control
    - dual_rgb_sensor  : Dual RGB line-following sensor
    - gamepad          : Wireless gamepad controller
    - ranging_sensor   : Laser/ultrasonic distance sensor
    - power_manage_module : Competition mode / power management
    - power_expand_board  : DC motor / solenoid / brushless expansion
"""

from mbuild import encoder_motor
from mbuild import smartservo
from mbuild import dual_rgb_sensor
from mbuild import gamepad
from mbuild import ranging_sensor
from mbuild import power_manage_module
from mbuild import power_expand_board
