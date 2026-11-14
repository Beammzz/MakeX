from mbuild.encoder_motor import encoder_motor_class
import novapi

UPPER_LEFT = "M1"
LOWER_LEFT = "M6"
UPPER_RIGHT = "M2"
LOWER_RIGHT = "M4"

REVERSE = [1, 1, 1, -1]

# ใช้ใน Auto
SLOW_SPEED = 35
NORMAL_SPEED = 75

MAX_SPEED = 80
TRIM_FORWARD = [1, 1, 1, 1]
TRIM_BACKWARD = [1, 1, 1, 1]
TRIM_LEFT = [1, 1, 1, 1]
TRIM_RIGHT = [1, 1, 1, 1]


class Wheel:
    def __init__(self) -> None:
        self.motors = [
            encoder_motor_class(UPPER_LEFT, 'INDEX1'),
            encoder_motor_class(LOWER_LEFT, 'INDEX1'),
            encoder_motor_class(UPPER_RIGHT, 'INDEX1'),
            encoder_motor_class(LOWER_RIGHT, 'INDEX1')
        ]
        
        self.slow_speed = SLOW_SPEED
        self.normal_speed = NORMAL_SPEED
        self.max_speed = MAX_SPEED
        self.slide = [-1, 1, 1, -1]
        self.rotate = [1, 1, -1, -1]
        self.deadzone = 10
        novapi.reset_rotation('z')

    def _dz(self, value):
        if abs(value) < self.deadzone:
            return 0
        return value

    def holomix(self, lx, ly, rx, deadzone = True):
        if deadzone:
            lx = self._dz(lx)
            ly = self._dz(ly)
            rx = self._dz(rx)
        if lx == 0 and ly == 0 and rx == 0:
            self.stop()
            novapi.reset_rotation('z')
            return
        
        # Gyro Headlocking
        if rx != 0 or ly != 0 or lx >= 40:
            novapi.reset_rotation('z')
        else:
            yaw = novapi.get_yaw()
            if abs(yaw) > 2.0:
                rx = -yaw * 2.0

        ty = TRIM_FORWARD if ly >= 0 else TRIM_BACKWARD
        tx = TRIM_RIGHT if lx >= 0 else TRIM_LEFT
        powers = []
        for i in range(4):
            powers.append(ly * ty[i] + lx * tx[i] * self.slide[i] - rx * self.rotate[i])

        peak = max(abs(p) for p in powers)
        scale = min(1, self.max_speed / peak)
        for i in range(4):
            self.motors[i].set_power(int(powers[i] * scale) * REVERSE[i])

    def move_forward(self):
        self.holomix(0, self.normal_speed, 0, deadzone=False)

    def move_backward(self):
        self.holomix(0, -self.normal_speed, 0, deadzone=False)

    def move_left(self):
        self.holomix(-self.normal_speed, 0, 0, deadzone=False)

    def move_right(self):
        self.holomix(self.normal_speed, 0, 0, deadzone=False)

    def move_slow_forward(self):
        self.holomix(0, self.slow_speed, 0, deadzone=False)

    def move_slow_backward(self):
        self.holomix(0, -self.slow_speed, 0, deadzone=False)

    def move_slow_left(self):
        self.holomix(-self.slow_speed, 0, 0, deadzone=False)

    def move_slow_right(self):
        self.holomix(self.slow_speed, 0, 0, deadzone=False)

    def rotate_left(self):
        self.holomix(0, 0, -self.normal_speed, deadzone=False)

    def rotate_right(self):
        self.holomix(0, 0, self.normal_speed, deadzone=False)

    def rotate_slow_left(self):
        self.holomix(0, 0, -self.slow_speed, deadzone=False)

    def rotate_slow_right(self):
        self.holomix(0, 0, self.slow_speed, deadzone=False)

    def stop(self):
        for i in range(4):
            self.motors[i].stop()