from mbuild import power_expand_board
from mbuild.smartservo import smartservo_class

# เซอร์โว
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
LIFT_HAND_INDEX = "INDEX2"
BLOCK_HAND_INDEX = "INDEX3"
BALL_HAND_OPEN_DEGREE = 112

class Conveyor:
    def __init__(self) -> None:
        # Ball convey
        self.ball_shooter = DC_BALL_SHOOTER
        self.ball_conveyor = DC_BALL_CONVEYOR
        self.ball_feeder = DC_BALL_FEEDER
        self.sixseven = DC_SIXSEVEN
        self.lift_hand = smartservo_class(SERVO, LIFT_HAND_INDEX)
        self.block_hand = smartservo_class(SERVO, BLOCK_HAND_INDEX)
        self.ball_hand = smartservo_class(SERVO, BALL_HAND_INDEX)
        self.ball_conveyor_toggle = False
        self.toggle_ball = False

        # Block convey
        self.block_a = DC_BLOCK_A
        self.block_b = DC_BLOCK_B
        
        self.cone_lift = DC_CONE_LIFT
        self.hand = DC_HAND


    def toggle_ball_hand(self):
            if not self.toggle_ball:
                self.ball_hand.move_to(BALL_HAND_OPEN_DEGREE, SERVO_SPEED)
                self.toggle_ball = True
            else:
                self.ball_hand.move_to(0, SERVO_SPEED)
                self.toggle_ball = False
    
    def toggle_ball_conveyor(self):
        if not self.ball_conveyor_toggle:
            power_expand_board.set_power(self.ball_feeder, -100)
            power_expand_board.set_power(self.ball_conveyor, 100)
            self.ball_conveyor_toggle = True
        else:
            power_expand_board.set_power(self.ball_feeder, 0)
            power_expand_board.set_power(self.ball_conveyor, 0)
            self.ball_conveyor_toggle = False
            
    def shooter_convey(self, reverse=False):
        if reverse:
            power_expand_board.set_power(self.ball_shooter, -100)
            power_expand_board.set_power(self.ball_conveyor, -100)
            power_expand_board.set_power(self.sixseven, 60)
        else:
            power_expand_board.set_power(self.ball_shooter, 100)
            power_expand_board.set_power(self.ball_conveyor, 100)
            power_expand_board.set_power(self.sixseven, 60)
            
    def shooter_convey_stop(self):
        power_expand_board.set_power(self.ball_shooter, 0)
        power_expand_board.set_power(self.ball_conveyor, 0)
        power_expand_board.set_power(self.sixseven, 0)

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
            power_expand_board.set_power(self.cone_lift, -60)
        else:
            power_expand_board.set_power(self.cone_lift, 60)
            
    def stop_lift(self):
            power_expand_board.set_power(self.cone_lift, 5)
            
    def hand_hold(self, reverse=False):
        if reverse:
            power_expand_board.set_power(self.hand, 80)
        else:
            power_expand_board.set_power(self.hand, -80)
                    
    def stop_hand(self):
        power_expand_board.set_power(self.hand, 0)
                
    