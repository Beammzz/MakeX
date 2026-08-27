# shooter Servo drgree
1: -24

# Brushless Power
- BL1: 17
- BL2: 17

# Hardware
- M2 (ล้อ LL): เอ็นโค้ดเดอร์เสีย get_value("speed"/"angle") = 0 ตลอด
  ทั้งตอนหมุนด้วยมือและตอนจ่ายไฟ 40% (M1/M3/M4 อ่านได้ปกติ)
  -> ล้อต้องใช้ set_power เท่านั้น ห้ามใช้ set_speed/move_to/move
     จนกว่าจะเปลี่ยนโมดูล
