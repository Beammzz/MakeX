import time
from mbuild import (
    gamepad,
    power_expand_board,
    power_manage_module,
)
from mbuild.encoder_motor import encoder_motor_class
from mbuild.smartservo import smartservo_class

print(r"""
                           .-') _    .-') _             ('-. .-.   ('-.         .-') _  
                          (  OO) )  (  OO) )           ( OO )  /  ( OO ).-.    ( OO ) ) 
  ,----.    ,--. ,--.   ,(_)----. ,(_)----.    .-----. ,--. ,--.  / . --. /,--./ ,--,'  
 '  .-./-') |  | |  |   |       | |       |   '  .--./ |  | |  |  | \-.  \ |   \ |  |\  
 |  |_( O- )|  | | .-') '--.   /  '--.   /    |  |('-. |   .|  |.-'-'  |  ||    \|  | ) 
 |  | .--, \|  |_|( OO )(_/   /   (_/   /    /_) |OO  )|       | \| |_.'  ||  .     |/  
(|  | '. (_/|  | | `-' / /   /___  /   /___  ||  |`-'| |  .-.  |  |  .-.  ||  |\    |   
 |  '--'  |('  '-'(_.-' |        ||        |(_'  '--'\ |  | |  |  |  | |  ||  | \   |   
  `------'   `-----'    `--------'`--------'   `-----' `--' `--'  `--' `--'`--'  `--' 
""")

# ตัวคุม PID ตัวเดียวใช้ได้ทุกล้อ update() คืนค่าที่ต้องแก้ ไม่ใช่กำลังทั้งก้อน
class PID:
    def __init__(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.previous_error = 0.0

    def reset(self):
        self.integral = 0.0
        self.previous_error = 0.0

    def update(self, target, current):
        error = target - current
        self.integral += error
        derivative = error - self.previous_error
        self.previous_error = error
        return self.kp * error + self.ki * self.integral + self.kd * derivative

# Mecanum Wheel Control
class Wheel:
    def __init__(self):
        self.upper_left = encoder_motor_class("M1", "INDEX1")
        self.lower_left = encoder_motor_class("M2", "INDEX1")
        self.upper_right = encoder_motor_class("M3", "INDEX1")
        self.lower_right = encoder_motor_class("M4", "INDEX1")

        # Holomix Tuning Parameters
        self.DEADZONE = 40
        self.STRAFE_GAIN = 1
        self.Multiply = 1.5        # กำลัง 0-100 คูณเป็นความเร็วเป้าหมาย (rpm) ก่อนเข้า PID
        self.MAX_SPEED = 255        # เพดานความเร็วที่ส่งให้มอเตอร์

        # ค่าถ่วงกำลังรายล้อ คูณหลัง PID แก้แล้ว ล้อไหนยังแรงเกินก็ลดตัวนั้น
        self.UL_TUNE = 1.00
        self.LL_TUNE = 1.00
        self.UR_TUNE = 1.00
        self.LR_TUNE = 1.00

        # เครื่องหมายของความเร็วที่อ่านกลับมา เทียบกับความเร็วที่สั่ง
        # ถ้าหุ่นพุ่งแรงผิดปกติหรือคุมไม่อยู่ทันทีที่เริ่มวิ่ง ให้สลับเป็น 1
        self.FEEDBACK_SIGN = -1

        # PID รายล้อ (kp, ki, kd) จูนด้วย scripts/Tune_Teleop.py
        self.pid_ul = PID(1.00, 0.00, 0.00)
        self.pid_ll = PID(1.00, 0.00, 0.00)
        self.pid_ur = PID(1.00, 0.00, 0.00)
        self.pid_lr = PID(1.00, 0.00, 0.00)
        self._pids = (self.pid_ul, self.pid_ll, self.pid_ur, self.pid_lr)

    def _dz(self, v):
        if abs(v) < self.DEADZONE:
            return 0
        span = 100 - self.DEADZONE
        if v > 0:
            return (v - self.DEADZONE) * 100 / span
        return (v + self.DEADZONE) * 100 / span

    # กำลัง -100..100 ต่อล้อ แปลงเป็นความเร็วเป้าหมาย ให้ PID แก้ แล้วค่อยคูณ TUNE
    def set_speed(self, ul, ll, ur, lr):
        motors = (self.upper_left, self.lower_left, self.upper_right, self.lower_right)
        tunes = (self.UL_TUNE, self.LL_TUNE, self.UR_TUNE, self.LR_TUNE)
        targets = (ul * self.Multiply, ll * self.Multiply,
                   ur * self.Multiply, lr * self.Multiply)

        for i in range(4):
            current = self.FEEDBACK_SIGN * motors[i].get_value("speed")
            out = (targets[i] + self._pids[i].update(targets[i], current)) * tunes[i]
            motors[i].set_speed(int(max(min(out, self.MAX_SPEED), -self.MAX_SPEED)))

    def stop(self):
        # สั่งหยุดตรง ๆ ไม่ผ่าน PID แล้วล้างค่าสะสม รอบหน้าจะได้ไม่กระชากจากค่าค้าง
        self.upper_left.set_speed(0)
        self.lower_left.set_speed(0)
        self.upper_right.set_speed(0)
        self.lower_right.set_speed(0)
        for pid in self._pids:
            pid.reset()

    # รวมแกนเป็นกำลังของล้อ ฝั่งขวาติดกลับด้าน เครื่องหมายเลยสลับ
    def _mix(self, vx, vy, vw):
        return (
            vx + vy + vw,
            -vx + vy + vw,
            vx - vy + vw,
            -vx - vy + vw,
        )

    # ใช้ร่วมกันทั้งโหมดจอยและโหมดออโต้ ทางเข้าเดียวไปหา PID
    def drive(self, vx, vy, vw):
        if vx == 0 and vy == 0 and vw == 0:
            self.stop()
            return

        ul, ll, ur, lr = self._mix(vx, vy, vw)

        # หารด้วยล้อที่แรงสุดเฉพาะตอนทะลุ 100 ทิศทแยงจะได้หดทั้งก้อน ไม่ใช่ตัดล้อเดียว
        # ตัดล้อเดียวแล้วทิศที่หุ่นวิ่งจริงจะเพี้ยน
        peak = max(abs(ul), abs(ll), abs(ur), abs(lr), 100)
        scale = 100 / peak
        self.set_speed(ul * scale, ll * scale, ur * scale, lr * scale)

    def holomix(self, lx, ly, rx):
        self.drive(-self._dz(lx) * self.STRAFE_GAIN, self._dz(ly), -self._dz(rx))

    # Basic Movement for Auto Mode
    # power คือความเร็วที่สั่งจริง ไม่ถูกหั่นด้วยค่าจำกัดของโหมดจอย
    def forward(self, power):
        self.drive(0, power, 0)

    def backward(self, power):
        self.drive(0, -power, 0)

    def slide_left(self, power):
        self.drive(power, 0, 0)

    def slide_right(self, power):
        self.drive(-power, 0, 0)

    # ทแยง = เดินหน้า + สไลด์ พร้อมกัน
    def slide_upper_left(self, power):
        self.drive(power, power, 0)

    def slide_upper_right(self, power):
        self.drive(-power, power, 0)

    def turn_left(self, power):
        self.drive(0, 0, power)

    def turn_right(self, power):
        self.drive(0, 0, -power)

class conveyor:
    def __init__(self):
        # Class linker
        self.shooter = Shooter()

        # DC Motors
        self.block_a = "DC1"
        self.block_b = "DC3"
        
        self.convey_upper = "DC4"
        self.front_feeder = "DC2"
        self.convey_midway = "DC5"
        self.convey_lower = "DC6"
        self.sweeper = "DC2"
        self.block_convey_servo = smartservo_class("M5", "INDEX2")

        # Toggle State
        self.is_ball_convey_toggled = False
        self.is_midway_convey_toggled = False
        self.block_convey_servo_toggled = False
        self.is_sweeper_toggled = False
        self.is_lift_sweeper_toggled = False

    def block_convey(self, reverse=False):
        if reverse:
            power_expand_board.set_power(self.block_a, -100)
            power_expand_board.set_power(self.block_b, -100)
        else:
            power_expand_board.set_power(self.block_a, 100)
            power_expand_board.set_power(self.block_b, 100)

    def block_convey_stop(self):
        power_expand_board.set_power(self.block_a, 0)
        power_expand_board.set_power(self.block_b, 0)

    def ball_convey(self, reverse=False):
        if not self.is_ball_convey_toggled:
            if reverse:
                power_expand_board.set_power(self.convey_upper, -100)
                power_expand_board.set_power(self.convey_lower, 100)
                power_expand_board.set_power(self.front_feeder, -100)
            else:
                power_expand_board.set_power(self.convey_upper, 100)
                power_expand_board.set_power(self.convey_lower, -100)
                power_expand_board.set_power(self.front_feeder, 100)
            self.is_ball_convey_toggled = True
        else:
            power_expand_board.set_power(self.convey_upper, 0)
            power_expand_board.set_power(self.front_feeder, 0)
            power_expand_board.set_power(self.convey_lower, 0)
            self.is_ball_convey_toggled = False

    def midway_convey(self, reverse=False):
        if reverse:
            power_expand_board.set_power(self.convey_midway, -70)
            power_expand_board.set_power(self.convey_lower, 80)
        else:
            power_expand_board.set_power(self.convey_midway, 70)
            power_expand_board.set_power(self.convey_lower, -80)

    def midway_convey_stop(self):
        power_expand_board.set_power(self.convey_midway, 0)
        power_expand_board.set_power(self.convey_lower, 0)

    def block_convey_servo_move(self):
        if not self.block_convey_servo_toggled:
            self.block_convey_servo.move_to(55, 50)
            self.block_convey_servo_toggled = True
        else:
            self.block_convey_servo.move_to(0, 50)
            self.block_convey_servo_toggled = False


    def toggle_sweeper(self):
        if not self.is_sweeper_toggled:
            if self.shooter.is_shooter_toggled:
                self.shooter.toggle_shooter()
            time.sleep(0.1)
            self.shooter.set_shooter_angle(-45)
            power_expand_board.set_power(self.sweeper, -80)
            self.is_sweeper_toggled = True

    
        else:
            self.shooter.set_shooter_angle(0)
            self.shooter.is_shooter_toggled_angle = False
            power_expand_board.set_power(self.sweeper, 0)
            self.is_sweeper_toggled = False

    def stop_all(self):
        power_expand_board.set_power(self.block_a, 0)
        power_expand_board.set_power(self.block_b, 0)
        power_expand_board.set_power(self.convey_upper, 0)
        power_expand_board.set_power(self.front_feeder, 0)
        power_expand_board.set_power(self.convey_midway, 0)
        power_expand_board.set_power(self.convey_lower, 0)
        power_expand_board.set_power(self.sweeper, 0)
        # รีเซ็ตเฉพาะ toggle ของตัวที่สั่งหยุดไปจริง ๆ (เซอร์โวยังค้างมุมเดิม)
        self.is_ball_convey_toggled = False
        self.is_midway_convey_toggled = False
        self.is_sweeper_toggled = False

# Consist of Brushless Motor and Shooter Servo
class Shooter:
    def __init__(self):
        self.is_shooter_toggled = False

        self.is_shooter_toggled_angle = False
        self.servo = smartservo_class("M5", "INDEX1")

        # Shooter Servo Tuning Parameters
        self.ANGLE_HOME = 0
        self.ANGLE_AIM = -15
        self.ANGLE_SPEED = 50

    def set_shooter_angle(self, angle):
        self.servo.move_to(angle, self.ANGLE_SPEED)

    def toggle_shooter(self):
        if not self.is_shooter_toggled:
            power_expand_board.set_power("BL1", 17)
            power_expand_board.set_power("BL2", 17)
            self.is_shooter_toggled = True
        else:
            power_expand_board.set_power("BL1", 0)
            power_expand_board.set_power("BL2", 0)
            self.is_shooter_toggled = False

    def toggle_shooter_angle(self):
        if not self.is_shooter_toggled_angle:
            self.set_shooter_angle(self.ANGLE_AIM)
            self.is_shooter_toggled_angle = True
        else:
            self.set_shooter_angle(self.ANGLE_HOME)
            self.is_shooter_toggled_angle = False

    def stop(self):
        power_expand_board.set_power("BL1", 0)
        power_expand_board.set_power("BL2", 0)
        self.is_shooter_toggled = False
        

class Guzzchan:
    def __init__(self):
        self.wheel = Wheel()
        self.shooter = Shooter()
        self.conveyor = conveyor()
        self._prev_keys = {}

    def _pressed(self, key):
        now = gamepad.is_key_pressed(key)
        fired = now and not self._prev_keys.get(key, False)
        self._prev_keys[key] = now
        return fired
    
    def control(self):
        lx = gamepad.get_joystick("Lx")
        ly = gamepad.get_joystick("Ly")
        rx = gamepad.get_joystick("Rx")
        # Robot Movement Control (Wheel)
        # Pass to Holomix Function
        self.wheel.holomix(lx, ly, rx)

        # Button Control
        if self._pressed("+"):
            self.shooter.toggle_shooter()
            time.sleep(0.1)

        if self._pressed("N1"):
            self.conveyor.ball_convey()
            time.sleep(0.1)

        if self._pressed("N4"):
            self.conveyor.toggle_sweeper()
            time.sleep(0.1)

        if gamepad.is_key_pressed("L1"):
            self.conveyor.block_convey()
        elif gamepad.is_key_pressed("R1"):
            self.conveyor.block_convey(reverse=True)
        else:
            self.conveyor.block_convey_stop()

        if gamepad.is_key_pressed("L2"):
            self.conveyor.midway_convey()
        elif gamepad.is_key_pressed("R2"):
            self.conveyor.midway_convey(reverse=True)
        else:
            self.conveyor.midway_convey_stop()

        if self._pressed("N3"):
            self.shooter.toggle_shooter_angle()
            time.sleep(0.1)

        if self._pressed("≡"):
            self.conveyor.block_convey_servo_move()
            time.sleep(0.1)

        if self._pressed("N2"):
            self.conveyor.ball_convey(reverse=True)
            time.sleep(0.1)  


    def stop_all(self):
        self.wheel.stop()
        self.conveyor.stop_all()
        self.shooter.stop()

    def auto(self, side):
        if side == "L":
            """ self.shooter.set_shooter_angle(-45)
            self.conveyor.sweeper_lift_servo.move_to(270, 30)
            power_expand_board.set_power("DC7", -80)
            self.wheel.turn_right(50)
            time.sleep(0.50)
            self.wheel.forward(50)
            time.sleep(1.8)
            self.wheel.turn_left(50)
            time.sleep(0.60)
            self.wheel.forward(40)
            time.sleep(1.5)
            self.wheel.backward(30)
            time.sleep(0.3) """
            self.stop_all()
        else:
            """ self.shooter.set_shooter_angle(-45)
            self.conveyor.sweeper_lift_servo.move_to(270, 30)
            power_expand_board.set_power("DC7", -80)
            self.wheel.turn_left(50)
            time.sleep(0.50)
            self.wheel.forward(50)
            time.sleep(1.8)
            self.wheel.turn_right(50)
            time.sleep(0.15)
            self.wheel.forward(40)
            time.sleep(1.5)
            self.conveyor.sweeper_lift_servo.move_to(250, 30)
            time.sleep(0.4)
            self.wheel.backward(30)
            time.sleep(0.3) """
            self.stop_all()

# Init
robot = Guzzchan()
was_auto = False
robot.shooter.set_shooter_angle(0)

# Main Loop
while True:
    is_auto = power_manage_module.is_auto_mode()
    if is_auto:
        if not was_auto:
            print("Competition is in auto mode")
            robot.auto("L")
            robot.stop_all()
        else:
            time.sleep(0.15)
    else:
        robot.control()
    was_auto = is_auto
