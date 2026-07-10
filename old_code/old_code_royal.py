import novapi
from mbuild.encoder_motor import encoder_motor_class
from mbuild import gamepad
from mbuild import power_expand_board
from mbuild import power_manage_module
from mbuild.smartservo import smartservo_class
import time

class Ikazuchibot:
    
    def logo():
        print("""
        
         ______     __  __     ______     __  __     __        __     ______     ______  
        /\  ___\   /\ \/\ \   /\  ___\   /\ \_\ \   /\ \      /\ \   /\  __ \   /\__  _\ 
        \ \___  \  \ \ \_\ \  \ \___  \  \ \  __ \  \ \ \     \ \ \  \ \ \/\ \  \/_/\ \/ 
         \/\_____\  \ \_____\  \/\_____\  \ \_\ \_\  \ \_\     \ \_\  \ \_____\    \ \_\ 
          \/_____/   \/_____/   \/_____/   \/_/\/_/   \/_/      \/_/   \/_____/     \/_/ 
                                                                        [ROYAL PALADIN]
        """)
        print(";-; This code made by SUSHI_IOT || DEV by Ikazuchi || ROYAL PALADIN! Team [WIP]")
    
    def __init__(self):
        self.upper_left_motor_wheel = encoder_motor_class("M1", "INDEX1")
        self.upper_right_motor_wheel = encoder_motor_class("M2", "INDEX1")
        self.lower_left_motor_wheel = encoder_motor_class("M3", "INDEX1")
        self.lower_right_motor_wheel = encoder_motor_class("M4", "INDEX1")
        self.upper_convey = "DC1"
        self.midway_convey = "DC2"
        self.lower_convey = "DC3"
        self.folklift = "DC4"
        self.gripper = "DC7"
        self.intake = "DC8"
        self.block_gather = encoder_motor_class("M6","INDEX1")
        self.servo_level_adjustment = smartservo_class("M5", "INDEX1")
        self.brushless_motor = "BL1"
        self.auto_mode_status = 0
        self.set_toggle_brushless = 0
        self.set_toggle_dc = 0
        self.set_toggle_servo = 0
        self.set_intake_system_toggle = 0
        self.set_block_gather_system_toggle = 0
        self.set_upper_convey_only = 0
        self.zone = "L"

    def set_move_degree(self, ul, ur, ll, lr):
        self.upper_left_motor_wheel.move(ul,255)
        self.upper_right_motor_wheel.move(ur,255)
        self.lower_left_motor_wheel.move(ll,255)
        self.lower_right_motor_wheel.move(lr,255)


    def set_motor_speed(self, ul, ur, ll, lr):
        self.upper_left_motor_wheel.set_power(ul)
        self.upper_right_motor_wheel.set_power(ur)
        self.lower_left_motor_wheel.set_power(ll)
        self.lower_right_motor_wheel.set_power(lr)

    def move_forward(self):
        self.set_motor_speed(70, -70, 70, -70)

    def move_backward(self):
        self.set_motor_speed(-70, 70, -70, 70)

    def move_right_sideway(self):
        self.set_motor_speed(70, 65, -70, -70)

    def move_left_sideway(self):
        self.set_motor_speed(-70, -70, 60, 70)

    def spin_right(self):
        self.set_motor_speed(-70, -70, -70, -70)

    def spin_left(self):
        self.set_motor_speed(70, 70, 70, 70)

    def stop_motor(self):
        self.set_motor_speed(0, 0, 0, 0)

    def brushless_speed(self, bl_speed):
        power_expand_board.set_power(self.brushless_motor, bl_speed)

    def shooter(self):
        if self.set_toggle_brushless == 0:
            self.brushless_speed(80)
            self.set_toggle_brushless = 1
        else:
            self.brushless_speed(0)
            self.set_toggle_brushless = 0

    def convey_system(self, reverse=False, toggle=False, upper_only=False):
        dcspeed = -80 if reverse else 80
        if toggle and not upper_only:
            if self.set_toggle_dc == 0:
                power_expand_board.set_power(self.upper_convey, dcspeed)
                power_expand_board.set_power(self.midway_convey, dcspeed)
                power_expand_board.set_power(self.lower_convey, dcspeed)
                power_expand_board.set_power(self.intake, dcspeed+30)
                self.set_toggle_dc = 1
            else:
                power_expand_board.set_power(self.upper_convey, 0)
                power_expand_board.set_power(self.midway_convey,0)
                power_expand_board.set_power(self.lower_convey, 0)
                power_expand_board.set_power(self.intake, 0)
                self.set_toggle_dc = 0
        elif upper_only:
            if self.set_upper_convey_only == 0:
                power_expand_board.set_power(self.upper_convey, dcspeed)
                power_expand_board.set_power(self.midway_convey, dcspeed)
                power_expand_board.set_power(self.lower_convey, 0)
                self.set_upper_convey_only = 1
            else:
                power_expand_board.set_power(self.upper_convey, 0)
                power_expand_board.set_power(self.midway_convey, 0)
                power_expand_board.set_power(self.lower_convey, 0)
                power_expand_board.set_power(self.intake, 0)
                self.set_upper_convey_only = 0
        else:
            power_expand_board.set_power(self.upper_convey, dcspeed)
            power_expand_board.set_power(self.midway_convey, dcspeed)
            power_expand_board.set_power(self.lower_convey, dcspeed)
            power_expand_board.set_power(self.intake, dcspeed+30)

    def servo_control(self):
        if self.set_toggle_servo == 0:
            self.servo_level_adjustment.move_to(-50, 20)
            self.set_toggle_servo = 1
        elif self.set_toggle_servo == 1:
            self.servo_level_adjustment.move_to(-10, 20)
            self.set_toggle_servo = 2
        else:
            self.servo_level_adjustment.move_to(0, 20)
            self.set_toggle_servo = 0

    def forklift_system(self):
        ly = gamepad.get_joystick("Ly")
        if ly <= -20:
            power_expand_board.set_power(self.folklift, ly)
        elif ly >= 20:
            power_expand_board.set_power(self.folklift, ly)
        else:
            power_expand_board.set_power(self.folklift, 10)
        
    def block_gather_system(self):
        if self.set_block_gather_system_toggle == 0:
            self.block_gather.set_power(50)
            self.set_block_gather_system_toggle = 1
        else:
            self.block_gather.set_power(0)
            self.set_block_gather_system_toggle = 0    
            
    def intake_system(self):
        if self.set_intake_system_toggle == 0:
            power_expand_board.set_power(self.intake, -50)
            self.set_intake_system_toggle = 1
        else:
            power_expand_board.set_power(self.intake, 0)
            self.set_intake_system_toggle = 0           
    
    def kachidoki_auto_system(self,zone):
        if self.auto_mode_status == 0:
            if self.zone == "R":
                #self.servo_control()
                #self.servo_control()
                time.sleep(0.1)
                self.block_gather_system()
                time.sleep(0.1)
                self.move_left_sideway()
                time.sleep(0.75)
                self.set_motor_speed(53, -53, 53, -53)
                time.sleep(1.81)
                self.block_gather_system()
                time.sleep(0.1)
                self.move_backward()
                time.sleep(0.7)
                self.auto_mode_status = 1
            else:
                time.sleep(0.1)
                self.move_right_sideway()
                time.sleep(0.3)
                self.stop_motor()
                time.sleep(0.15)
                self.spin_left()
                time.sleep(0.05)
                self.block_gather_system()
                time.sleep(0.1)
                self.set_move_degree(360*7.5, -360*7.5, 360*7.5, -360*7.5)
                time.sleep(1.55)
                self.block_gather_system()
                time.sleep(0.1)
                self.stop_motor()
                time.sleep(0.15)
                self.move_backward()
                time.sleep(0.7)
                
        else:
            pass            
    
    def control_system(self):
        ly = gamepad.get_joystick("Ly")
        rx = gamepad.get_joystick("Rx")
        
        if power_manage_module.is_auto_mode() or gamepad.is_key_pressed("R_Thumb"):
            time.sleep(0.1) 
            #self.kachidoki_auto_system(zone="R")
            self.kachidoki_auto_system(zone="L")
            
        if rx > 20:
            self.spin_right()
            time.sleep(0.1)
        elif rx < -20:
            self.spin_left()
            time.sleep(0.1)
        if gamepad.is_key_pressed("Up"):
            self.move_forward()
        elif gamepad.is_key_pressed("Down"):
            self.move_backward()
        elif gamepad.is_key_pressed("Left"):
            self.move_left_sideway()
        elif gamepad.is_key_pressed("Right"):
            self.move_right_sideway()
        else:
            self.stop_motor()
    
        if gamepad.is_key_pressed("+"):
            self.shooter()
            time.sleep(0.2)
        elif gamepad.is_key_pressed("L_Thumb"):
            self.block_gather_system()
            time.sleep(0.2)    
        elif gamepad.is_key_pressed("R1"):
            self.convey_system(reverse=True, toggle=True, upper_only=False)
            time.sleep(0.2)
        elif gamepad.is_key_pressed("R2"):
            self.convey_system(reverse=False, toggle=True, upper_only=False)
            time.sleep(0.2)
        elif gamepad.is_key_pressed("L1"):
            self.convey_system(reverse=True, toggle=True, upper_only=True)
            time.sleep(0.2)
        elif gamepad.is_key_pressed("L2"):
            self.convey_system(reverse=False, toggle=True, upper_only=True)
            time.sleep(0.2)
        elif gamepad.is_key_pressed("N2"):
            self.servo_control()
            time.sleep(0.2)
        elif gamepad.is_key_pressed("N3"):
            self.intake_system()
            time.sleep(0.2)    
        elif gamepad.is_key_pressed("N1"):   # เปิด
            power_expand_board.set_power(self.gripper,80)
            print("gripper_opened")
        elif gamepad.is_key_pressed("N4"):   # ปิด
            power_expand_board.set_power(self.gripper,-80)    
            print("gripper_closed")    
        elif not gamepad.is_key_pressed("N4") and not gamepad.is_key_pressed("N1"):
            power_expand_board.set_power(self.gripper,0)    
            #print("gripper_disable")    
        self.forklift_system()

robot = Ikazuchibot()
Ikazuchibot.logo()
while True:
    robot.control_system()