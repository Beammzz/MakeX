from mbuild.encoder_motor import encoder_motor_class

UPPER_LEFT = "M1"
LOWER_LEFT = "M2"
UPPER_RIGHT = "M5"
LOWER_RIGHT = "M4"

REVERSE = [1, 1, 1, -1]

# ใช้ใน Auto
SLOW_SPEED = 40

NORMAL_SPEED = 75
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
        self.slide = [-1, 1, 1, -1]
        self.rotate = [1, 1, -1, -1]
        self.deadzone = 40

    def _dz(self, value):
        if abs(value) < self.deadzone:
            return 0
        return value

    def holomix(self, lx, ly, rx, speed=None):
        if speed is None:
            speed = self.normal_speed
        lx = self._dz(lx)
        ly = self._dz(ly)
        rx = self._dz(rx)
        if lx == 0 and ly == 0 and rx == 0:
            self.stop()
            return

        ty = TRIM_FORWARD if ly >= 0 else TRIM_BACKWARD
        tx = TRIM_RIGHT if lx >= 0 else TRIM_LEFT
        powers = []
        for i in range(4):
            powers.append(ly * ty[i] + lx * tx[i] * self.slide[i] - rx * self.rotate[i])

        peak = max(abs(p) for p in powers)
        scale = speed / max(peak, 100)
        for i in range(4):
            self.motors[i].set_power(int(powers[i] * scale) * REVERSE[i])

    def move_forward(self):
        self.holomix(0, 100, 0)

    def move_backward(self):
        self.holomix(0, -100, 0)

    def move_left(self):
        self.holomix(-100, 0, 0)

    def move_right(self):
        self.holomix(100, 0, 0)

    def move_slow_forward(self):
        self.holomix(0, 100, 0, self.slow_speed)

    def move_slow_backward(self):
        self.holomix(0, -100, 0, self.slow_speed)

    def move_slow_left(self):
        self.holomix(-100, 0, 0, self.slow_speed)

    def move_slow_right(self):
        self.holomix(100, 0, 0, self.slow_speed)

    def rotate_left(self):
        self.holomix(0, 0, -100)

    def rotate_right(self):
        self.holomix(0, 0, 100)

    def rotate_slow_left(self):
        self.holomix(0, 0, -100, self.slow_speed)

    def rotate_slow_right(self):
        self.holomix(0, 0, 100, self.slow_speed)

    def stop(self):
        for i in range(4):
            self.motors[i].stop()