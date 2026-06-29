from mbuild.encoder_motor import encoder_motor_class
from mbuild import power_manage_module
from mbuild import gamepad
from mbuild import power_expand_board
from mbuild.smartservo import smartservo_class
import time


class donttrythisathome:
    def __init__(self):
        self.encoder_motor_M1 = encoder_motor_class("M1", "INDEX1")
        self.encoder_motor_M2 = encoder_motor_class("M2", "INDEX1")
        self.encoder_motor_M3 = encoder_motor_class("M3", "INDEX1")
        self.encoder_motor_M4 = encoder_motor_class("M4", "INDEX1")
        self.encoder_motor_M6 = encoder_motor_class("M6", "INDEX1")
        
        self.auto_side = 'R' # L or R
        
        self.N2_current_index = 0

        self.blushless_motor = "BL1"
        self.feed_lower = "DC4"
        self.feed_mid = "DC3"
        self.feed_upper = "DC6"
        self.tong = "DC7"
        self.flick_block = "DC5"
        self.lift_dc = "DC2"

        self.servo_level = smartservo_class("M5", "INDEX1")

        # state variables
        self.set_Bl = 0
        self.auto_set = 0
        self.tong_set = 0
        self.L2_toggle_step = 0
        self.L2_last_state = False
        self.feed_middle_toggle = False
        self.l1_last_state = False
        self.r1_active = False
        self.bl_hard_active = False
        self.bl_smooth_active = False
        self.auto_key_last = False
        self.arm_on_state = False
        self.n1_last_state = False
        self.n4_last_state = False
        self.bl_key_last = False

        # สำหรับ block_expro
        self.block_expro_active = False
        self.r_thumb_last_state = False
        self.block_expro_start_time = 0.0
        self.block_expro_last_toggle_time = 0.0
        self.block_expro_power_on = False
        self.block_expro_toggle_interval = 0.2   # หน่วงเวลา toggle
        self.block_expro_duration = 5.0          # เวลาที่ให้ทำงาน expro
        self.block_expro_power_value = -15       # ลดพลังเล็กน้อย

        self.servo_control_zero()

    # -------------------- Movement Functions --------------------
    def set_motor_speed(self, ul, ur, ll, lr):
        self.encoder_motor_M1.set_power(ul)
        self.encoder_motor_M2.set_power(ur)
        self.encoder_motor_M3.set_power(ll)
        self.encoder_motor_M4.set_power(lr)

    def spin_right(self):
        self.set_motor_speed(-30, -30, -30, -30)

    def spin_left(self):
        self.set_motor_speed(30, 30, 30, 30)

    def move_forward(self):
        self.set_motor_speed(60, -75, 85, -85)

    def move_forward_slow(self):
        self.set_motor_speed(40, -55, 60, -40)

    def move_backward(self):
        self.set_motor_speed(-65, 70, -70, 75)

    def move_backward_slow(self):
        self.set_motor_speed(-45, 50, -50, 55)

    def move_right_sideway(self):
        self.set_motor_speed(75, 75, -90, -70)

    def move_left_sideway(self):
        self.set_motor_speed(-75, -100, 75, 100)

    def stop_motor(self):
        self.set_motor_speed(0, 0, 0, 0)

    def move_suddenly(self):
        for _ in range(2):
            self.set_motor_speed(40, -40, 40, -40)
            time.sleep(0.4)
            self.set_motor_speed(0, 0, 0, 0)
            time.sleep(0.4)

    # -------------------- Brushless Motor --------------------
    def Bl_hard(self):
        if not self.bl_smooth_active:
            power_expand_board.set_power(self.blushless_motor, 90 if not self.bl_hard_active else 0)
            self.bl_hard_active = not self.bl_hard_active
            time.sleep(0.1)

    def BL_smooth(self):
        if not self.bl_hard_active:
            power_expand_board.set_power(self.blushless_motor, 60 if not self.bl_smooth_active else 0)
            self.bl_smooth_active = not self.bl_smooth_active
            time.sleep(0.1)

    # -------------------- Servo --------------------
    def servo_control_down(self):
        self.servo_level.move_to(5, 25)

    def servo_control_zero(self):
        self.servo_level.move_to(0, 20)

    def servo_control_up(self):
        self.servo_level.move_to(-32, 25)

    def servo_control_block(self):
        self.servo_level.move_to(30, 20)

    def servo_control_up_2(self):
        self.servo_level.move_to(-20, 20)
        
    #L2 servo-------------------------------------
    def servo_control_up_L2_1(self):
        self.servo_level.move_to(-10, 20)
        
    def servo_control_up_L2_2(self):
        self.servo_level.move_to(0, 20)
        
    def servo_control_up_L2_3(self):
        self.servo_level.move_to(10, 20) 

    # -------------------- Feeder --------------------
    def feed_middle_down(self):
        self.encoder_motor_M6.set_power(100)
        power_expand_board.set_power(self.feed_lower, 90)
        power_expand_board.set_power(self.feed_mid, -100)

    def feed_middle_down_slow_with_upper(self):
        self.encoder_motor_M6.set_power(90)
        power_expand_board.set_power(self.feed_lower, 90)
        power_expand_board.set_power(self.feed_mid, -80)
        power_expand_board.set_power(self.feed_upper, -100)

    def feed_middle_down_slow_with_upper_2(self):
        self.encoder_motor_M6.set_power(50)
        power_expand_board.set_power(self.feed_lower, 100)
        power_expand_board.set_power(self.feed_mid, -25)
        power_expand_board.set_power(self.feed_upper, -60)

    def feed_set_zero(self):
        self.encoder_motor_M6.set_power(0)
        power_expand_board.set_power(self.feed_lower, 0)
        power_expand_board.set_power(self.feed_mid, 0)
        power_expand_board.set_power(self.feed_upper, 0)

    def feed_reverse(self):
        self.encoder_motor_M6.set_power(-70)
        power_expand_board.set_power(self.feed_lower, -55)
        power_expand_board.set_power(self.feed_mid, 80)
        power_expand_board.set_power(self.feed_upper, 100)

    # -------------------- Arm / Tong --------------------
    def arm_on(self):
        power_expand_board.set_power(self.tong, 40)

    def arm_off(self):
        power_expand_board.set_power(self.tong, -35)

    def arm_set_zero(self):
        power_expand_board.set_power(self.tong, 0)

    # -------------------- Lifter --------------------
    def lift_up(self):
        power_expand_board.set_power(self.lift_dc, 100)

    def lift_down(self):
        power_expand_board.set_power(self.lift_dc, -100)

    def lift_frozen(self):
        power_expand_board.set_power(self.lift_dc, 8)

    # -------------------- Block Flick --------------------
    def block_up(self):
        power_expand_board.set_power(self.flick_block, 80)

    def block_back_to_zero(self):
        power_expand_board.set_power(self.flick_block, 0)

    def block_expro(self):
        power_expand_board.set_power(self.flick_block, self.block_expro_power_value)
        
    def auto_two(self, side):
        if side == 'R':
            self.block_up()
            self.move_forward()
            time.sleep(1.05)
            self.move_suddenly()
            time.sleep(0.01)
            self.block_expro()
            time.sleep(0.2)
            self.move_backward_slow()
            time.sleep(0.8)
            self.stop_motor()
            time.sleep(0.2)
            
            self.set_motor_speed(-60, -60, -60, -60)
            time.sleep(0.6)
            self.move_backward()
            time.sleep(0.5)
            self.feed_middle_down()
            time.sleep(0.05)
            self.set_motor_speed(20, -28, 30, -20)
            time.sleep(1)
            # Loop Feed
            for _ in range(5):
                self.set_motor_speed(-25, -25, -25, -25)
                time.sleep(0.5)
                self.set_motor_speed(25, 25, 25, 25)
                time.sleep(0.7)
                self.move_forward_slow()
                time.sleep(0.1)
            self.move_backward_slow()
            time.sleep(0.2)
            self.spin_left()
            time.sleep(1)
            self.feed_set_zero()
            time.sleep(0.1)
        else:
            self.move_right_sideway()
            time.sleep(0.3)
            self.move_backward_slow()
            time.sleep(0.7)
            self.block_up()
            self.move_forward()
            time.sleep(0.95)
            self.move_suddenly()
            time.sleep(0.1)
            self.block_expro()
            time.sleep(0.2)
            self.move_backward_slow()
            time.sleep(1)
            self.stop_motor()
            time.sleep(0.2)
            self.set_motor_speed(60, 60, 60, 60)
            time.sleep(0.6)
            self.move_backward()
            time.sleep(0.5)
            self.feed_middle_down()
            time.sleep(0.05)
            self.set_motor_speed(20, -28, 30, -20)
            time.sleep(1)
            # Loop Feed
            for _ in range(5):
                self.set_motor_speed(-25, -25, -25, -25)
                time.sleep(0.5)
                self.set_motor_speed(25, 25, 25, 25)
                time.sleep(0.7)
                self.move_forward_slow()
                time.sleep(0.1)
            self.move_backward_slow()
            time.sleep(0.2)
            self.spin_right()
            time.sleep(1)
            self.feed_set_zero()
            time.sleep(0.1)
            

    # -------------------- Main Control Loop --------------------
    def control_system(self):
        ly = gamepad.get_joystick("Ly")
        rx = gamepad.get_joystick("Rx")
        lx = gamepad.get_joystick("Lx")

        move_handled = False

        # ---- SPIN FIRST ----
        if 30 <= rx <= 70:
            self.set_motor_speed(-50, -50, -50, -50)
            move_handled = True
        elif rx > 70 and rx != 0:
            self.set_motor_speed(-90, -90, -90, -90)
            move_handled = True
        elif rx < -70 and rx != 0:
            self.set_motor_speed(90, 90, 90, 90)
            move_handled = True
        elif -70 <= rx <= -30:
            self.set_motor_speed(50, 50, 50, 50)
            move_handled = True
        elif ly >= 40:
            self.move_forward()
            move_handled = True
        elif ly <= -40:
            self.move_backward()
            move_handled = True
        elif lx >= 40:
            self.move_left_sideway()
            move_handled = True
        elif lx <= -40:
            self.move_right_sideway()
            move_handled = True

        if not move_handled:
            self.stop_motor()

        # ---- FEED CONTROLS ----
        l1 = gamepad.is_key_pressed("L1")
        r1 = gamepad.is_key_pressed("R1")

        if l1 and not self.l1_last_state:
            if self.r1_active:
                self.r1_active = False
            self.feed_middle_toggle = not self.feed_middle_toggle
        self.l1_last_state = l1

        if r1 and not self.r1_active:
            self.feed_middle_toggle = False
            self.r1_active = True
        if not r1 and self.r1_active:
            self.r1_active = False

        if self.r1_active:
            self.feed_middle_down_slow_with_upper()
        elif self.feed_middle_toggle:
            self.feed_middle_down()
        else:
            self.feed_set_zero()

        # ---- FEED REVERSE ----
        if gamepad.is_key_pressed("R2"):
            self.feed_reverse()
            time.sleep(0.01)

        # ---- BRUSHLESS MOTOR ----
        if gamepad.is_key_pressed("Left"):
            self.BL_smooth()

        if gamepad.is_key_pressed("+") and not self.bl_key_last:
            self.Bl_hard()
        self.bl_key_last = gamepad.is_key_pressed("+")

        # ---- SERVO CONTROL ----
        if gamepad.is_key_pressed("N2"):
            self.servo_control_up()
            time.sleep(0.02)
        
        elif gamepad.is_key_pressed("N3"):
            
            if self.N2_current_index >= 4:
                self.N2_current_index = 1
                
            if self.N2_current_index == 1:
                self.servo_level.move_to(35, 25)
                time.sleep(0.02)
            elif self.N2_current_index == 2:
                self.servo_level.move_to(13, 25)
                time.sleep(0.02)
            else:
                self.servo_level.move_to(0, 25)
                time.sleep(0.02)
                
            self.N2_current_index += 1
        
        elif gamepad.is_key_pressed("≡"):
            self.N2_current_index = 0
            self.servo_control_zero()
            time.sleep(0.02)
        
        elif gamepad.is_key_pressed("Right"):
            self.servo_control_up_2()
            time.sleep(0.02)
            
        # ---- L2 Toggle: Step Control ----
        #l2_pressed = gamepad.is_key_pressed("L2")
        #if l2_pressed and not self.L2_last_state:
        #    self.L2_toggle_step = (self.L2_toggle_step + 1) % 4

        #    if self.L2_toggle_step == 1:
        #        self.servo_control_up_L2_1()
        #    elif self.L2_toggle_step == 2:
        #        self.servo_control_up_L2_2()
        #    elif self.L2_toggle_step == 3:
        #        self.servo_control_up_L2_3()
        #    elif self.L2_toggle_step == 0:
        #        self.servo_control_zero()

        #self.L2_last_state = l2_pressed
        
        
        
    
        # ---- BLOCK CONTROL ----
        l_thumb_current = gamepad.is_key_pressed("L_Thumb")
        r_thumb_current = gamepad.is_key_pressed("R_Thumb")

        if not hasattr(self, 'block_flick_mode'):
            self.block_flick_mode = 0
            self.l_thumb_last_state = False
            self.r_thumb_last_state = False

        # --- R_Thumb toggle ---
        if r_thumb_current and not self.r_thumb_last_state:
            if self.block_flick_mode == 2:
                self.block_flick_mode = 0
                power_expand_board.set_power(self.flick_block, 0)
            else:
                self.block_flick_mode = 2
                power_expand_board.set_power(self.flick_block, -20)
        self.r_thumb_last_state = r_thumb_current

        # --- L_Thumb toggle ---
        if l_thumb_current and not self.l_thumb_last_state:
            if self.block_flick_mode == 1:
                self.block_flick_mode = 0
                power_expand_board.set_power(self.flick_block, 0)
            elif self.block_flick_mode == 0:
                self.block_flick_mode = 1
                power_expand_board.set_power(self.flick_block, 80)
        self.l_thumb_last_state = l_thumb_current

                
        # ---- ARM CONTROL ----
        n1_pressed = gamepad.is_key_pressed("N1")
        n4_pressed = gamepad.is_key_pressed("N4")
        lifting = gamepad.is_key_pressed("Up") or gamepad.is_key_pressed("Down")

        if n4_pressed and not lifting:
            self.arm_on_state = False
            self.arm_off()
        else:
            if n1_pressed and not self.n1_last_state:
                self.arm_on_state = True

            if self.arm_on_state:
                self.arm_on()
            else:
                self.arm_set_zero()

        self.n1_last_state = n1_pressed
        self.n4_last_state = n4_pressed

        # ---- LIFT CONTROL ----
        if gamepad.is_key_pressed("Up"):
            self.lift_up()
        elif gamepad.is_key_pressed("Down"):
            self.lift_down()
        else:
            self.lift_frozen()
            
        if gamepad.is_key_pressed("L2"):
            self.auto_two(self.auto_side)
            time.sleep(0.2)


# -------------------- MAIN LOOP --------------------
robot = donttrythisathome()
auto_side = "R"
while True:
    if power_manage_module.is_auto_mode():
        if robot.auto_set == 0:
            robot.auto_two(auto_side)
            robot.auto_set = 0
    else:
        robot.control_system()
        time.sleep(0.02)
