import time
from mbuild import (
    gamepad,
    power_expand_board,
    power_manage_module,
)
from mbuild.encoder_motor import encoder_motor_class
from mbuild.smartservo import smartservo_class
from mbuild.smart_camera import smart_camera_class

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
        self.Multiply = 2.55       # กำลัง 0-100 คูณเป็นความเร็วเป้าหมาย (rpm)
        self.MAX_SPEED = 255        # เพดานความเร็วที่ส่งให้มอเตอร์

        # ค่าถ่วงกำลังรายล้อ ล้อไหนแรงเกินก็ลดตัวนั้น
        self.UL_TUNE = 1.00
        self.LL_TUNE = 1.00
        self.UR_TUNE = 1.00
        self.LR_TUNE = 1.00

        # ก้าวกำลังสูงสุดต่อรอบ loop กันสั่งกลับทิศทันทีแล้วหุ่นเสียหลัก
        # หน่วงเฉพาะตอนเพิ่มกำลัง ผ่อนจอยจ่ายตามทันทีเลย คนขับจะได้ไม่รู้สึกว่าเบรกไม่อยู่
        # รู้สึกช้า = เพิ่มค่า, ยังเสียหลักตอนกลับทิศ = ลดค่า, 100 = ปิดการหน่วง
        self.SLEW_STEP = 25

        # ค่ากำลังของแต่ละแกนที่ผ่านการหน่วงแล้ว ใช้เฉพาะโหมดจอย
        self._vx = 0.0
        self._vy = 0.0
        self._vw = 0.0

    def _dz(self, v):
        if abs(v) < self.DEADZONE:
            return 0
        span = 100 - self.DEADZONE
        if v > 0:
            return (v - self.DEADZONE) * 100 / span
        return (v + self.DEADZONE) * 100 / span

    # กำลัง -100..100 ต่อล้อ แปลงเป็นความเร็วเป้าหมาย แล้วคูณ TUNE
    def set_speed(self, ul, ll, ur, lr):
        motors = (self.upper_left, self.lower_left, self.upper_right, self.lower_right)
        tunes = (self.UL_TUNE, self.LL_TUNE, self.UR_TUNE, self.LR_TUNE)
        powers = (ul, ll, ur, lr)

        for i in range(4):
            out = powers[i] * self.Multiply * tunes[i]
            motors[i].set_speed(int(max(min(out, self.MAX_SPEED), -self.MAX_SPEED)))

    def stop(self):
        self.upper_left.set_speed(0)
        self.lower_left.set_speed(0)
        self.upper_right.set_speed(0)
        self.lower_right.set_speed(0)
        self._reset_slew()

    # ล้างค่าหน่วงเวลาหยุด กลับเข้าโหมดจอยอีกทีจะได้ไม่กระชากจากค่าค้าง
    def _reset_slew(self):
        self._vx = 0.0
        self._vy = 0.0
        self._vw = 0.0

    # ไล่ค่าปัจจุบันเข้าหาค่าที่สั่ง ทีละไม่เกินหนึ่งก้าว
    def _slew(self, cur, target):
        # ผ่อนหรือปล่อยจอยในทิศเดิม จ่ายตามจอยทันที ไม่ต้องหน่วง
        if abs(target) <= abs(cur) and target * cur >= 0:
            return target
        if target > cur + self.SLEW_STEP:
            return cur + self.SLEW_STEP
        if target < cur - self.SLEW_STEP:
            return cur - self.SLEW_STEP
        return target

    # รวมแกนเป็นกำลังของล้อ ฝั่งขวาติดกลับด้าน เครื่องหมายเลยสลับ
    def _mix(self, vx, vy, vw):
        return (
            vx + vy + vw,
            -vx + vy + vw,
            vx - vy + vw,
            -vx - vy + vw,
        )

    # ใช้ร่วมกันทั้งโหมดจอยและโหมดออโต้ ทางเข้าเดียวไปหามอเตอร์
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
        # หน่วงที่ระดับแกนก่อนเข้า drive กันสั่งกลับทิศทันทีแล้วหุ่นเสียหลัก
        self._vx = self._slew(self._vx, -self._dz(lx) * self.STRAFE_GAIN)
        self._vy = self._slew(self._vy, self._dz(ly))
        self._vw = self._slew(self._vw, -self._dz(rx))
        self.drive(self._vx, self._vy, self._vw)

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
        self.hand = "DC2"
        self.block_b = "DC3"
        
        self.convey_upper = "DC4"
        self.convey_midway = "DC5"
        self.convey_lower = "DC6"
        self.sweeper = "DC7"
        self.block_convey_servo = smartservo_class("M5", "INDEX2")

        # Toggle State
        self.is_ball_convey_toggled = False
        self.is_midway_convey_toggled = False
        self.block_convey_servo_toggled = False
        self.is_sweeper_toggled = False
        self.is_hand_toggled = False

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
            else:
                power_expand_board.set_power(self.convey_upper, 100)
                power_expand_board.set_power(self.convey_lower, -100)
            self.is_ball_convey_toggled = True
        else:
            power_expand_board.set_power(self.convey_upper, 0)
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
            power_expand_board.set_power(self.sweeper, -10)
            self.is_sweeper_toggled = True
        else:
            power_expand_board.set_power(self.sweeper, 0)
            self.is_sweeper_toggled = False
            
    def toggle_hand(self):
        # เปิดออก
        if not self.is_hand_toggled:
            power_expand_board.set_power(self.hand, 20)
            time.sleep(0.5)
            power_expand_board.set_power(self.hand, 0)
            self.is_hand_toggled = True
        # ปิดเข้า
        else:
            power_expand_board.set_power(self.hand, -45)
            self.is_hand_toggled = False

    def stop_all(self):
        power_expand_board.set_power(self.block_a, 0)
        power_expand_board.set_power(self.block_b, 0)
        power_expand_board.set_power(self.convey_upper, 0) 
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
        self.is_shooter_toggled_angle = False

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

        if self._pressed("Down"):
            self.shooter.toggle_shooter_angle()

        if self._pressed("≡"):
            self.conveyor.block_convey_servo_move()

        if self._pressed("Up"):
            self.conveyor.ball_convey(reverse=True)
            
        if gamepad.is_key_pressed("N2"):
            power_expand_board.set_power("DC8", -100)
        elif gamepad.is_key_pressed("N3"):
            power_expand_board.set_power("DC8", 100)
        else:
            power_expand_board.set_power("DC8", 0)
            
        if self._pressed("Right"):
            self.conveyor.toggle_hand()


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
robot.shooter.set_shooter_angle(0)

# Main Loop
while True:
    robot.control()
    time.sleep(0.02)
