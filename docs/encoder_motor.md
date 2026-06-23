# `encoder_motor` --- มอเตอร์เอ็นโค้ดเดอร์

ฟังก์ชันหลักและเมธอดของโมดูล `encoder_motor`

## คำอธิบายมอเตอร์เอ็นโค้ดเดอร์

มอเตอร์เอ็นโค้ดเดอร์ประกอบด้วยมอเตอร์ 180 และมอเตอร์บัสเลส 36 แบบเรียงซ้อน โมดูลมีลักษณะดังภาพด้านล่าง:

(ไม่มีรูปภาพตามที่ระบุ)

## ฟังก์ชันที่เกี่ยวข้อง

### `move_to(position, speed)`

เคลื่อนที่ไปยังมุมแบบสัมบูรณ์ด้วยความเร็วที่กำหนด, พารามิเตอร์:

- `position` มุมเป้าหมาย, หน่วยเป็นองศา, ช่วง `-2147483648~2147483647`
- `speed` ความเร็วการหมุน, หน่วยเป็น rpm/min, ช่วง `ไม่จำกัด`

### `move(position, speed)`

เคลื่อนที่ไปยังมุมแบบสัมพัทธ์ด้วยความเร็วที่กำหนด, พารามิเตอร์:

- `position` มุมเป้าหมาย, หน่วยเป็นองศา, ช่วง `-2147483648~2147483647`
- `speed` ความเร็วการหมุน, หน่วยเป็น rpm/min, ช่วง `ไม่จำกัด`

### `set_speed(speed)`

กำหนดความเร็วเป้าหมาย, ควบคุมแบบ closed-loop, พารามิเตอร์:

- `speed` ความเร็วการหมุน, หน่วยเป็น rpm/min, ช่วง: ไม่จำกัด, หมุนด้วยกำลังสูงสุดของมอเตอร์

### `set_power(pwm)`

กำหนดให้มอเตอร์หมุนด้วยกำลังที่กำหนด, ควบคุมแบบ open-loop, พารามิเตอร์:

- `pwm` ความเร็วการหมุน, หน่วย `ไม่มี`, ช่วง `-100~100`

### `get_value(type)`

รับข้อมูลมอเตอร์, พารามิเตอร์:

- `type` ประเภทข้อมูลที่รับ, เป็นสตริง (ชนิดข้อความ), สามารถเลือกพารามิเตอร์ได้ดังนี้:
  - `"angle"`: มุมตำแหน่งปัจจุบัน, ค่าที่คืนกลับมามีหน่วยเป็นองศา
  - `"speed"`: ความเร็วปัจจุบัน, ค่าที่คืนกลับมามีหน่วยเป็น rpm/min

## ตัวอย่างโปรแกรม:

```python
import novapi
import time
from mbuild.encoder_motor import encoder_motor_class

# เริ่มต้นระบบก่อน โดยกำหนดให้มอเตอร์เชื่อมต่อที่พอร์ต M1 ตัวที่ 1
__encoder_motor_1 = encoder_motor_class("M1", "INDEX1")

while True:
    __encoder_motor_1.set_power(50)
    __encoder_motor_1.set_power(-50)
    time.sleep(1)

    __encoder_motor_1.set_speed(100)
    __encoder_motor_1.set_speed(-100)
    time.sleep(1)

    __encoder_motor_1.move_to(360, 100)
    __encoder_motor_1.move_to(-360, 100)
    time.sleep(1)

    __encoder_motor_1.move(360, 100)
    __encoder_motor_1.move(-360, 100)
    time.sleep(1)

    __encoder_motor_1.set_power(50)
    time.sleep(1)
    speed = __encoder_motor_1.get_value("speed")
    print("speed: %d" % speed)
    position1 = __encoder_motor_1.get_value("angle")
    print("position1: %d" % position1)
```
