from mbuild import power_expand_board
from mbuild.smartservo import smartservo_class
import time

SERVO = "M6"
SERVO_SPEED = 30

DC_BALL_SHOOTER = "DC2"
DC_BALL_CONVEYOR = "DC3"
DC_BALL_FEEDER = "DC8"
DC_SIXSEVEN = "DC6"

DC_BLOCK_A = "DC4"
DC_BLOCK_B = "DC5"

DC_CONE_LIFT = "DC1"
DC_HAND = "DC7"

BALL_HAND_INDEX = "INDEX1"
BALL_HAND_OPEN_DEGREE = 112

LIFT_HAND_INDEX = "INDEX2"

BLOCK_HAND_INDEX = "INDEX3"
BLOCK_HAND_OPEN_DEGREE = -46

class Conveyor:
    def __init__(self) -> None:
        # Ball convey
        self.ball_shooter = DC_BALL_SHOOTER
        self.ball_conveyor = DC_BALL_CONVEYOR
        self.ball_feeder = DC_BALL_FEEDER
        self.sixseven = DC_SIXSEVEN
        
        # Servo
        self.lift_hand_servo = smartservo_class(SERVO, LIFT_HAND_INDEX)
        self.block_hand = smartservo_class(SERVO, BLOCK_HAND_INDEX)
        self.ball_hand = smartservo_class(SERVO, BALL_HAND_INDEX)
        
        # State
        self.ball_conveyor_toggle = False
        self.toggle_ball = False
        self.toggle_block = False
        self.toggle_updown = False
        self.lift_hand_manual = False
        self.sweep_cone_toggle = False
        self.sweep_block_toggle = False

        # Block convey
        self.block_a = DC_BLOCK_A
        self.block_b = DC_BLOCK_B
        
        self.cone_lift = DC_CONE_LIFT
        self.hand = DC_HAND


    def move_to(self, servo, position, speed=SERVO_SPEED, timeout=3):
        servo.move_to(position, speed)
        end = time.ticks_add(time.ticks_ms(), int(timeout * 1000))
        while abs(servo.get_value("angle") - position) > 5:
            if time.ticks_diff(end, time.ticks_ms()) <= 0:
                break
            time.sleep(0.02)

    def toggle_ball_hand(self):
            if not self.toggle_ball:
                self.move_to(self.ball_hand, BALL_HAND_OPEN_DEGREE)
                self.toggle_ball = True
            else:
                self.move_to(self.ball_hand, 0)
                self.toggle_ball = False
    
            
    def toggle_ball_conveyor(self):
        if not self.ball_conveyor_toggle:
            power_expand_board.set_power(self.ball_feeder, -100)
            power_expand_board.set_power(self.ball_conveyor, 100)
            power_expand_board.set_power(self.sixseven, -30)
            self.ball_conveyor_toggle = True
        else:
            power_expand_board.set_power(self.ball_feeder, 0)
            power_expand_board.set_power(self.ball_conveyor, 0)
            power_expand_board.set_power(self.sixseven, 0)
            self.ball_conveyor_toggle = False
            
    def shooter_convey(self, reverse=False):
        if reverse:
            power_expand_board.set_power(self.ball_shooter, -100)
            power_expand_board.set_power(self.ball_conveyor, -100)
            power_expand_board.set_power(self.sixseven, -30)
        else:
            power_expand_board.set_power(self.ball_shooter, 100)
            power_expand_board.set_power(self.ball_conveyor, 100)
            power_expand_board.set_power(self.sixseven, 30)
            
    def shooter_convey_stop(self):
        power_expand_board.set_power(self.ball_shooter, 0)
        power_expand_board.set_power(self.ball_conveyor, 0)
        power_expand_board.set_power(self.sixseven, -60 if self.toggle_updown or self.sweep_cone_toggle or self.sweep_block_toggle else 0)

    def block_convey(self, reverse=False):
            if reverse:
                power_expand_board.set_power(self.block_a, 100)
                power_expand_board.set_power(self.block_b, 100)
            else:
                power_expand_board.set_power(self.block_a, -100)
                power_expand_board.set_power(self.block_b, -100)

    def block_convey_stop(self):
        power_expand_board.set_power(self.block_a, 0)
        power_expand_board.set_power(self.block_b, 0)
        
    def lift_cone(self, reverse=False):
        if reverse:
            power_expand_board.set_power(self.cone_lift, -63)
        else:
            power_expand_board.set_power(self.cone_lift, 63)
            
    def stop_lift(self):
            power_expand_board.set_power(self.cone_lift, 5)
            
    def hand_hold(self, reverse=False):
        if reverse:
            power_expand_board.set_power(self.hand, 80)
        else:
            power_expand_board.set_power(self.hand, -80)
                    
    def stop_hand(self):
        power_expand_board.set_power(self.hand, 0)
                
    def toggle_block_hand(self):
        if not self.toggle_block:
            self.move_to(self.block_hand, BLOCK_HAND_OPEN_DEGREE)
            self.toggle_block = True
        else:
            self.move_to(self.block_hand, 0)
            self.toggle_block = False

    def lift_hand(self, reverse=False):
        self.lift_hand_manual = True
        if reverse:
            self.lift_hand_servo.set_power(-40)
        else:
            self.lift_hand_servo.set_power(40)

    def stop_lift_hand(self):
        if self.lift_hand_manual:
            self.lift_hand_servo.set_power(0)
            self.lift_hand_manual = False

    def toggle_river_feeder(self, lift_degree):
        if self.sweep_cone_toggle:
            self.toggle_river_cone()
        if not self.toggle_updown:
            self.move_to(self.lift_hand_servo, lift_degree)
            self.move_to(self.ball_hand, 100)
            self.lift_cone()
            time.sleep(1.05)
            self.stop_lift()
            power_expand_board.set_power(self.sixseven, -60)
            power_expand_board.set_power(self.ball_feeder, -80)
            self.toggle_updown = True
            self.toggle_ball = False
        else:
            power_expand_board.set_power(self.sixseven, 0)
            power_expand_board.set_power(self.ball_feeder, 0)
            self.move_to(self.lift_hand_servo, 0)
            self.move_to(self.ball_hand, 0)
            self.toggle_updown = False
            self.toggle_ball = False
            
    def toggle_river_cone(self):
        if self.toggle_ball:
            self.toggle_ball_hand()
        if self.toggle_updown:
            self.toggle_river_feeder(lift_degree = 400)
        if self.sweep_block_toggle:
            self.toggle_basket_block()
        if not self.sweep_cone_toggle:
            self.lift_cone()
            time.sleep(1)
            self.stop_lift()
            self.sweep_cone_toggle = True
            self.move_to(self.lift_hand_servo, -153)
            power_expand_board.set_power(self.sixseven, -60)
        else:
            power_expand_board.set_power(self.sixseven, 0)
            self.sweep_cone_toggle = False
            
    def toggle_basket_block(self):
            if self.toggle_ball:
                self.toggle_ball_hand()
            if self.toggle_updown:
                self.toggle_river_feeder(lift_degree = 400)
            if self.sweep_cone_toggle:
                self.toggle_river_cone()
            if not self.sweep_cone_toggle:
                self.lift_cone(reverse=True)
                time.sleep(1)
                self.lift_cone()
                time.sleep(0.5) 
                self.stop_lift()
                self.move_to(self.lift_hand_servo, 19)
                power_expand_board.set_power(self.sixseven, -60)
                self.sweep_block_toggle = True
            else:
                power_expand_board.set_power(self.sixseven, 0)
                self.sweep_block_toggle = False