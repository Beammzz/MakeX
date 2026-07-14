import novapi
import time
import random
from mbuild import (
    dual_rgb_sensor,
    gamepad,
    power_expand_board,
    power_manage_module,
    ranging_sensor,
)
from mbuild.encoder_motor import encoder_motor_class
from mbuild.smartservo import smartservo_class


class MyRobloxBrain():
    def __init__(self, debug=False):
        self.brushless_speed = 0
        self.tolerance = 3
        self.taopos = 45
        self.shooter_state = False
        self.readyshoot = False
        self.brushless_active = False
        self.servo_angle = 0
        self.handToggle = 0
        self.autoplay = False

        self.debug = debug
        if self.debug:
            print("--DEBUG MODE : ON")
        else:
            print("--DEBUG MODE : OFF")

        self.left_wheel = encoder_motor_class("M1", "INDEX1")
        self.right_wheel = encoder_motor_class("M5", "INDEX1")
        self.mid_wheel = encoder_motor_class("M6", "INDEX1")
        self.feeder = encoder_motor_class("M4", "INDEX1")

        self.angle_servo = smartservo_class("M2", "INDEX1")

    def debug_print(self, msg):
        if self.debug:
            print(msg)

    def set_motor(self, lw, rw, mw):
        self.left_wheel.set_power(lw)
        self.right_wheel.set_power(rw)
        self.mid_wheel.set_power(mw)

    def move_forward(self):
        self.set_motor(50, -50, 0)

    def move_backward(self):
        self.set_motor(-50, 60, 0)

    def move_left(self):
        self.set_motor(25, 25, -65)

    def move_right(self):
        self.set_motor(-30, -30, 60)

    def spin_left(self):
        self.set_motor(-30, -30, -30)

    def spin_right(self):
        self.set_motor(30, 30, 30)

    def stop_motors(self):
        self.set_motor(0, 0, 0)

    def control_servo_angle(self, angle):
        self.debug_print("Setting servo angle to %d" % angle)
        self.angle_servo.move(angle, 50)
        current_real_angle = self.angle_servo.get_value("angle")

    def stop_servo(self):
        self.angle_servo.set_power(0)

    def toggle_brushless(self):
        if self.brushless_active:
            self.debug_print("Turning brushless motor OFF")
            self.brushless_active = False
            power_expand_board.set_power("BL1", 0)
        else:
            self.debug_print("Turning brushless motor ON")
            self.brushless_active = True
            power_expand_board.set_power("BL1", 80)

    def toggle_servo_angle(self):
        self.debug_print("Toggling servo angle")
        current_real_angle = self.angle_servo.get_value("angle")

        if not (self.taopos - self.tolerance <= current_real_angle <= self.taopos + self.tolerance):
            self.angle_servo.move_to(self.taopos, 50)
            time.sleep(0.5)
        else:
            self.angle_servo.move_to(0, 50)
            time.sleep(0.3)

        current_real_angle = self.angle_servo.get_value("angle")
        print("New Angle : %d" % current_real_angle)

    def feed(self, reverse=False, hold=False, Toponly=False, Max=False, Num=1, Launcher=False, LF=False):
        power = -67 if reverse else 67
        launcherpower = -76 if reverse else 76
        self.debug_print("Feed: reverse=%s, hold=%s, Toponly=%s, Max=%s, Num=%d" %
                          (reverse, hold, Toponly, Max, Num))

        if hold and Toponly:
            # NOTE: self.motor_expand_board / self.top_feed were never defined
            # anywhere in the original script - add them in __init__ once you
            # know the real port names, or this line will raise AttributeError.
            self.motor_expand_board.set_power(self.top_feed, -power)

        if Max and Launcher:
            self.debug_print("Toggling shooter")
            self.toggle_brushless()
            time.sleep(0.5)

    def control_hand(self, reverse=False):
        self.debug_print("Toggling hand")
        self.handToggle = 255 if self.handToggle == 0 else 0
        handToggleR = self.handToggle if reverse else -self.handToggle
        # NOTE: self.power_expand_board / self.padblock were never defined
        # anywhere in the original script - same issue as above.
        self.power_expand_board.set_power(self.padblock, -handToggleR)

    def superautomode(self, pos="L"):
        if self.autoplay == False:
            self.autoplay = True
            if pos == "L":
                self.debug_print("PLAY AUTO MODE ON LEFT SIDE")
            else:
                self.debug_print("PLAY AUTO MODE ON RIGHT SIDE")

    def handle_input(self, position):
        if gamepad.is_key_pressed("Up"):
            self.move_forward()
        elif gamepad.is_key_pressed("Down"):
            self.move_backward()
        elif gamepad.is_key_pressed("Left"):
            self.move_left()
        elif gamepad.is_key_pressed("Right"):
            self.move_right()
        elif gamepad.get_joystick("Rx") < 0:
            self.spin_left()
        elif gamepad.get_joystick("Rx") > 0:
            self.spin_right()
        else:
            self.stop_motors()

        if gamepad.is_key_pressed("+"):
            self.toggle_brushless()
            time.sleep(0.1)

        ly_value = gamepad.get_joystick("Ly")

        if ly_value != 0:
            if ly_value > 0:
                self.servo_angle += 1
            elif ly_value < 0:
                self.servo_angle -= 1
            self.control_servo_angle(self.servo_angle)
        else:
            self.stop_servo()

        if gamepad.is_key_pressed("R2"):
            self.toggle_servo_angle()
            time.sleep(0.3)

        if gamepad.is_key_pressed("="):
            self.superautomode(position)


robot = MyRobloxBrain(debug=True)

robot.angle_servo.move_to(0, 50)
time.sleep(0.3)

while True:
    robot.handle_input("R")