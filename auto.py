import time
from mbuild import power_expand_board

def auto_mode(robot, side="L"):
    if side == "R":
        if (robot.conveyor.ball_hand.get_value("angle") > 10):
            robot.conveyor.toggle_ball_hand()
        robot.conveyor.lift_cone()
        time.sleep(0.65)
        robot.conveyor.move_to(robot.conveyor.lift_hand_servo, -130, 50)
        robot.wheel.move_backward()
        time.sleep(0.4)
        robot.wheel.rotate_slow_right()
        time.sleep(0.15)
        power_expand_board.set_power(robot.conveyor.sixseven, -60)
        time.sleep(0.1)
        robot.wheel.move_slow_forward()
        time.sleep(5)
        robot.wheel.move_slow_backward()
        time.sleep(0.8)
        
        power_expand_board.set_power(robot.conveyor.sixseven, 0)
    else:
        if (robot.conveyor.ball_hand.get_value("angle") > 10):
            robot.conveyor.toggle_ball_hand()
        # robot.conveyor.lift_cone()
        time.sleep(0.65)
        robot.conveyor.move_to(robot.conveyor.lift_hand_servo, -130, 50)
        robot.wheel.move_backward()
        time.sleep(0.4)
        robot.wheel.rotate_slow_left()
        time.sleep(0.08)
        power_expand_board.set_power(robot.conveyor.sixseven, -60)
        time.sleep(0.1)
        robot.wheel.move_slow_forward()
        time.sleep(5)
        robot.wheel.move_slow_backward()
        time.sleep(0.8)
        
        power_expand_board.set_power(robot.conveyor.sixseven, 0)
