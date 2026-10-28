from mbuild import power_expand_board

SHOOTER = "BL1"

class Shooter:
    def __init__(self) -> None:
        self.shooter = SHOOTER
        self.shooter_toggle = False

    def toggle_shooter(self):
        if not self.shooter_toggle:
            power_expand_board.set_power(self.shooter, 100)
            self.shooter_toggle = True
        else:
            power_expand_board.set_power(self.shooter, 0)
            self.shooter_toggle = False