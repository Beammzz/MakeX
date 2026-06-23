# `power_manage_module` --- โมดูลจัดการพลังงาน

ฟังก์ชันหลักและเมธอดของโมดูล `power_manage_module`

## คำอธิบายโมดูลจัดการพลังงาน

โมดูลจัดการพลังงานมีลักษณะดังภาพด้านล่าง:

(ไม่มีรูปภาพตามที่ระบุ)

## ฟังก์ชันที่เกี่ยวข้อง

### `is_auto_mode()`

ตรวจสอบว่าการแข่งขันอยู่ในโหมดอัตโนมัติหรือไม่, คืนค่าเป็นบูลีน, โดย `True` หมายถึงการแข่งขันอยู่ในโหมดอัตโนมัติ, `False` หมายถึงการแข่งขันอยู่ในโหมดบังคับมือ

## ตัวอย่างโปรแกรม:

```python
import novapi
from mbuild import power_manage_module

while True:
    if power_manage_module.is_auto_mode():
        print("Competition is in auto mode")
    else:
        print("Competition is in manual mode")
```
