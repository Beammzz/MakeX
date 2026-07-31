from mbuild.encoder_motor import encoder_motor_class

upper_left = encoder_motor_class("M1", "INDEX1")

while True:
    upper_left.set_speed(20)
    print("Motor : ", upper_left.get_value("speed"))
    time.sleep(0.04)
    