# `smartservo` --- สมาร์ทเซอร์โว

ฟังก์ชันหลักและเมธอดของโมดูล `smartservo`

## คำอธิบายสมาร์ทเซอร์โว

โมดูลสมาร์ทเซอร์โวของโมดูล mbuild มีลักษณะดังภาพด้านล่าง:

(ไม่มีรูปภาพตามที่ระบุ)

## ฟังก์ชันที่เกี่ยวข้อง

### `set_zero()`

ตั้งค่าตำแหน่งปัจจุบันให้เป็นจุดศูนย์

### `move_to(position, speed)`

เคลื่อนที่ไปยังมุมแบบสัมบูรณ์ด้วยความเร็วที่กำหนด, พารามิเตอร์:

- `position` มุมเป้าหมาย, หน่วยเป็นองศา, ช่วง `-2147483648~2147483647`
- `speed` ความเร็วการหมุน, หน่วยเป็น rpm/min, ช่วง `1~50`

### `move(position, speed)`

เคลื่อนที่ไปยังมุมแบบสัมพัทธ์ด้วยความเร็วที่กำหนด, พารามิเตอร์:

- `position` มุมเป้าหมาย, หน่วยเป็นองศา, ช่วง `-2147483648~2147483647`
- `speed` ความเร็วการหมุน, หน่วยเป็น rpm/min, ช่วง `1~50`

### `set_power(pwm)`

ตั้งค่าให้มอเตอร์หมุนด้วยกำลังที่กำหนด, ควบคุมแบบ open-loop, พารามิเตอร์:

- `pwm` ความเร็วการหมุน, หน่วย `ไม่มี`, ช่วง `-100~100`

### `get_value(type)`

รับข้อมูลมอเตอร์, พารามิเตอร์:

- `type` ประเภทข้อมูลที่รับ, เป็นสตริง (ชนิดข้อความ), สามารถเลือกพารามิเตอร์ได้ดังนี้:
  - `"current"`: กระแสไฟฟ้า, หน่วย A
  - `"voltage"`: แรงดันไฟฟ้า, หน่วย V
  - `"speed"`: ความเร็ว, หน่วย rpm/min
  - `"angle"`: มุม, หน่วยองศา
  - `"temperature"`: อุณหภูมิ, หน่วยองศาเซลเซียส

## ตัวอย่างโปรแกรม 1:

```python
import novapi
import time
from mbuild.smartservo import smartservo_class

# เริ่มต้นระบบก่อน โดยกำหนดให้สมาร์ทเซอร์โวเชื่อมต่อที่พอร์ต M1 ตัวที่ 1
__smartservo_1 = smartservo_class("M1", "INDEX1")

while True:
    __smartservo_1.set_zero()
    time.sleep(0.1)

    __smartservo_1.move_to(360, 20)
    time.sleep(4)
    position = __smartservo_1.get_value("angle")
    print("position: " ,position)

    __smartservo_1.move(-360, 20)
    time.sleep(4)
    position = __smartservo_1.get_value("angle")
    print("position: ",position)

    __smartservo_1.set_power(50)
    time.sleep(1)

    param0 = __smartservo_1.get_value("current")
    print("current: " ,param0)

    param1 = __smartservo_1.get_value("voltage")
    print("voltage: " ,param1)

    param2 = __smartservo_1.get_value("speed")
    print("speed: " ,param2)

    param3 = __smartservo_1.get_value("angle")
    print("angle: " ,param3)

    param4 = __smartservo_1.get_value("temperature")
    print("temperature: ", param4)
```
