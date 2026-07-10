import novapi
import time
from mbuild import (
    power_expand_board,
)
from mbuild.smartservo import smartservo_class

is_toggle = False
shooter_servo = smartservo_class("M5", "INDEX1")
    
def toggle():
    global is_toggle
    if is_toggle:
        power_expand_board.set_power("BL1", 0)
        power_expand_board.set_power("BL2", 0)
        is_toggle = False
        time.sleep(0.02)
    else:
        power_expand_board.set_power("BL1", 40)
        power_expand_board.set_power("BL2", 35)
        is_toggle = True
        time.sleep(0.02)
        
        
