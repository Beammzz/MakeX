import time
from mbuild import power_expand_board

def auto_mode(robot, side="L"):
    if side == "R":
        robot.conveyor.toggle_river_cone()
        time.sleep(0.65)
        robot.wheel.move_backward()
        time.sleep(0.4)
        robot.wheel.rotate_slow_right()
        time.sleep(0.25)
        robot.wheel.move_slow_forward()
        time.sleep(5)
        robot.conveyor.move_to(robot.conveyor.lift_hand_servo, 50)
        robot.wheel.move_slow_backward()
        time.sleep(0.15)
        robot.conveyor.move_to(robot.conveyor.lift_hand_servo, -10)
        robot.wheel.move_right()
        time.sleep(0.55)
        robot.wheel.move_slow_forward()
        time.sleep(3)
        # debug ชั่วคราว: ดูว่าเซอร์โวยกถึงไหม
        robot.conveyor.move_to(robot.conveyor.lift_hand_servo, 50)
        robot.wheel.move_slow_backward()
        time.sleep(0.4)
        robot.conveyor.move_to(robot.conveyor.lift_hand_servo, -10)
        robot.conveyor.toggle_river_cone()
        robot.wheel.stop()
    else:
        pass
