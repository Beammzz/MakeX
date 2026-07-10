import time
import novapi
from mbuild.encoder_motor import encoder_motor_class

wheel_upper_left = encoder_motor_class("M1", "INDEX1")
wheel_lower_left = encoder_motor_class("M2", "INDEX1")
wheel_upper_right = encoder_motor_class("M3", "INDEX1")
wheel_lower_right = encoder_motor_class("M4", "INDEX1")

def set_wheel_power(ul, ll, ur, lr):
        wheel_upper_left.set_power(ul)
        wheel_lower_left.set_power(ll)
        wheel_upper_right.set_power(ur)
        wheel_lower_right.set_power(lr)

def move_forward(power):
    set_wheel_power(ul=power,  ll=power,  ur=-power, lr=-power)
        
def move_backward(power):
    set_wheel_power(ul=-power, ll=-power, ur=power,  lr=power)
        
def move_sideway_right(power):
    set_wheel_power(ul=-power, ll=power,  ur=-power, lr=power)
        
def move_sideway_left(power):
    set_wheel_power(ul=power, ll=-power,  ur=power,  lr=-power)
        
def rotate_right(power):
    set_wheel_power(ul=-power, ll=-power, ur=-power, lr=-power)
    
def rotate_left(power):
    set_wheel_power(ul=power, ll=power, ur=power, lr=power)