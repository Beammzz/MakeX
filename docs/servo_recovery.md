# Smart servo recovery — status and knowledge (2026-11-14)

Handover and technical reference for the bricked smart servo on **M5**. Read this before touching the M5 servo chain.

> **Safety rule:** **NEVER send `0x61` subtypes above 3** (`61 05` = `UPDATEBLOCK` is what bricked `INDEX1`). Do not fuzz any servo with raw `0x61` frames: the bootloader could erase the application flash.

---

## 1. Current status & resolved M5 chain mapping

- **Broken servo confirmed (`INDEX1`)**: The 1st servo in the **M5** chain (`LOWER_HAND_INDEX = "INDEX1"` -> `self.lower_hand_servo` in `conveyor.py`) is the stuck servo with the **red LED**.
  - After receiving `[11, 1, 0x61, 0x05]` (`UPDATEBLOCK`), its heartbeat still reports `0b 01 10 60` (port 11 = M5, id 1, `0x10` assign reply, type `0x60`), so NovaPi detects `[1]` on port 11, but it answers no servo command, no version query (`0x12`), no handshake, and no bootloader frame (`0x61 0x06`/`0x08`).
  - Downstream servos **`INDEX2`** and **`INDEX3`** show healthy **blue LEDs**, but the stuck `INDEX1` unit blocks bus propagation so `get_mbuild_block_ids()` on port 11 only sees `[1]` and `get_position()` / `get_value()` downstream return `None`.
- **Exact role of each M5 servo in code (`conveyor.py`, `main.py`, `auto.py`)**:
  - `SERVO = "M5"` (bus port `11` / `0x0b`), `SERVO_SPEED = 30`.
  - **`INDEX1` (`LOWER_HAND_INDEX` — `self.lower_hand_servo`) — BROKEN**:
    - Used **only** in `Conveyor.sweep_ball()` (`conveyor.py:75-81`, moving `0` <-> `111` deg), called **only** on gamepad `"Up"` press (`main.py:54-55`).
    - **Not used anywhere in `auto.py`.**
  - **`INDEX2` (`LIFT_HAND_INDEX` — `self.lift_hand_servo`) — HEALTHY, BLOCKED**:
    - Critical lift/arm servo used by `lift_hand()` / `stop_lift_hand()` (`main.py:110-115`), `toggle_river_cone()` (`main.py:71-72`, `auto.py:6, 27`), `toggle_basket_block()` (`main.py:65-66`), `toggle_river_feeder()` (`conveyor.py:148-163`), telemetry print (`main.py:126`), and direct positioning in `auto.py:14, 17, 23, 26`.
  - **`INDEX3` (`BLOCK_HAND_INDEX` — `self.block_hand`) — HEALTHY, BLOCKED**:
    - Used by `toggle_block_hand()` (`conveyor.py:128-134`), triggered on gamepad `"≡"` press (`main.py:60-61`).
- **NovaPi mainboard firmware status**: Reinstalled on `2026-11-14` (`V41.02.40` / `V41.02.40-ht1`). **Re-upload `main.py` (and `auto.py`, `conveyor.py`, `wheel.py`, `shooter.py`)** after flashing if wiped. All other ports work normally.

---

## 2. Immediate competition workaround: M5 daisy-chain hardware bypass

Because `INDEX1` (`lower_hand_servo`) is only used for `sweep_ball()` (and not in `auto.py`), and `INDEX2`/`INDEX3` behind it are healthy, the robot can run without replacing the broken servo by physically bypassing it:

1. **Power off** the NovaPi battery completely.
2. **Unplug** the cable between NovaPi **M5** and the broken 1st servo (`lower_hand_servo` / red LED), and disconnect the downstream cable leaving that broken servo.
3. Plug the **2nd servo (`lift_hand_servo`, blue LED)** directly into NovaPi port **M5**, keeping `block_hand` chained right after `lift_hand_servo`.
   - Smart Servo / Neuron bus IDs are assigned dynamically by daisy-chain order (`[port, 0xff, 0x10, 0x00]`), so `lift_hand_servo` automatically becomes **`INDEX1`** and `block_hand` becomes **`INDEX2`**.
4. Update `conveyor.py` (when ready to deploy to the robot) to match the 2-servo chain:
   - Set `LIFT_HAND_INDEX = "INDEX1"` and `BLOCK_HAND_INDEX = "INDEX2"`.
   - Comment out `self.lower_hand_servo = smartservo_class(SERVO, LOWER_HAND_INDEX)` (and `LOWER_HAND_INDEX` or leave unused) and turn `sweep_ball()` into a no-op (`return`), so pressing `"Up"` cannot stall on missing telemetry (`get_value("angle")`).
   - Result: `auto.py` and all lift, cone, basket, and block-hand controls work normally with zero encoder-motor conversion needed.

---

## 3. What did NOT work on the robot (do not repeat)

Recorded from on-robot tests on `2026-11-14`:

- `reset_block` (`[11, idx, 0x11]`, single and broadcast `[255, 255, 0x11]`), `assign_id()`, `makeblock.reset()`.
- Full battery unplug (short duration): `INDEX1` stays red; `INDEX2`/`INDEX3` are blue but unreachable behind it.
- Bootloader recovery frames `61 06` (query hardware ID), `61 08` (query result), followed by `0x11` RESET: no reply from `INDEX1`.
- Wired USB (`COM3`, mode 3, raw `F8..F9` frames after power-cycle): broadcast `[255, 255, 0x61, 6]` received replies from ports `1, 6, 7, 8, 10, 12`, **nothing from port 11 (M5)**. `[11, 255, 16, 0]` alloc and `[11, 1, 18]` version were silent too.

---

## 4. Root cause of missing `0x60` firmware & `V41.02.40-ht1`

Exhaustive inspection of Makeblock's desktop client and cloud extension servers explains why no mBlock update or firmware dump can re-flash the Smart Servo:

- **Local mBlock 5.6.0 cache (`C:\Users\Sorra\mBlock\exts\novapi`, `v1.1.17`)**:
  - Bundles mainboard image `res/78fff3662104406383ae7c17e4bb90c9.bin` (`novapi_app_v41.02.039.bin`, `524,288` bytes) plus only 5 module firmware binaries:
    - `0x6207` (`power_expand_board`)
    - `0x6409` (`power_management_module`)
    - `0x6311` (`dual_rgb_sensor`)
    - `0x016206` (`encoder_motor_180`)
    - `0x026206` (`encoder_motor_36`)
- **Cloud `novapi` `v1.1.22` (`novapi_v1.1.22_732d55c9.mext` & `novapi_v1.1.22_2822e0c7.mext`)**:
  - This is where `V41.02.40-ht1` comes from (`res/d8d3d800_novapi_fimware_V41.02.40-ht1.bin`, `348,992` bytes, alongside the same 5 module firmwares: `16420`, `27868`, `39836`, `24340`, `41104` bytes).
  - Unminified `src/index.js` inside `novapi_v1.1.22` shows Makeblock **explicitly commented out Smart Servo firmware updates**:
    ```js
    const hardwareIDTab = [
        //{ hidM: 256, hidL: 444, typeId: 0x6000 }, //smart servo
        { hidM: 256, hidL: 193, typeId: 0x016206 }, //encoder180 motor
        { hidM: 320, hidL: 830, typeId: 0x026206 }, //encoder36 motor
        { hidM: 256, hidL: 256, typeId: 0x6409 }, //power_manage_module
        { hidM: 194, hidL: 895, typeId: 0x6311 }, //dual_rgb_sensor
        { hidM: 256, hidL: 320, typeId: 0x6207 }, //power_expand_board
    ]
    ```
  - Inside `ModuleUpgrade._switchBootLoad`, Makeblock also left `return true;` right before dead `throw "TODO by CKR"`.
- **Mainboard images contain no module firmware**:
  - String inspection inside `novapi` (`78fff3662104406383ae7c17e4bb90c9.bin`), `cyberpi` (`aeef0f00d526481aaef25b97a7476e25.bin`), and `motionblock` (`a6f1c5ceba6941c7abd085e2eb340dd1.bin`) confirmed every `smartservo`/`0x60`/`bootloader` hit is a MicroPython driver (`mbuild/smartservo.py`, `smartservo,0x60,None,...`) or ESP-IDF assert/register string (`0x60013000`, `0x60000000`, `bootloader_random.c`), not an embedded servo image. NovaPi only passes mBlock flash frames through (`updata modules firmware interrupt` comes from that pass-through).

**Conclusion:** Type-`0x60` (`0x6000`, MS-12A / MS-1.5A) firmware binary is not distributed in mBlock PC, mBlock Cloud, npm, or Makeblock GitHub repositories; it only exists internally at Makeblock (or possibly bundled inside an older Neuron/Makeblock mobile app release).

---

## 5. Exhaustive firmware search matrix (verified `2026-11-14`)

Every candidate source checked and confirmed to have **zero** type-`0x60` Smart Servo `.bin`/`.hex` images:

1. **Local mBlock 5.6.0 & workstation (`C:\Users\Sorra` & `C:\Users\Public\Programs\mblock`)**:
   - `C:\Users\Public\Programs\mblock\resources\app.asar`: extracted `extservice` URLs, `ap=mblockpc`, `v=5.6.0` parameters, and verified no hidden `0x60` binary.
   - `C:\Users\Sorra\mBlock\exts`: scanned all **153** extension folders.
     - `halocode_smartservo` (`v0.0.5`) and `neuron` (`v0.6.0`): 0 firmware binaries.
     - `mbuild` (`v0.0.8`): 19 module firmwares across 26 `.bin` files (no `0x60`; RC servo driver `0x620a` only).
     - `novapi` (`v1.1.17`): 1 mainboard `.bin` + 5 module `.bin`s (`6207`, `6409`, `6311`, `016206`, `026206`).
     - Large mainboard `.bin`s (`novapi`, `cyberpi`, `motionblock`): string-verified MicroPython/ESP-IDF only.
   - Checked `AppData\Roaming\mblock`, `Downloads`, `Documents`, and `.vscode\extensions\makeblock-community.novapi-companion-0.1.0` (`scripts/novapi_cli.py`, `stubs/mbuild/smartservo.pyi` — API stubs only).
2. **mBlock Cloud Extension APIs (`extservice.mblock.cc` & `extservice.makeblock.com`)**:
   - Earlier session queries failed because required query params (`ap=mblockpc&v=5.6.0&t=device|ext`) were omitted. With exact `app.asar` query parameters:
     - `extservice.mblock.cc`: queried all **423** `device` entries + all **2,452** `ext` entries across pages 1–3.
     - `extservice.makeblock.com`: queried all **298** `device` entries + all **1,948** `ext` entries across pages 1–2.
     - Tested alternate `ap` values (`mblockweb`, `mblockapp`, `mblock`, `neuron`, `makeblock`) and `POST /api/publish/ext/update`.
   - Downloaded and scanned **353** unique `.mext` archives (matching servo, novapi, mbuild, neuron, cyberpi, motionblock, halocode, makex, megapi, auriga, etc.): **0** contain a type-`0x60` Smart Servo binary.
3. **npm Registry**:
   - Searched and/or inspected tarballs for `neuron-engine`, `@mblock/neuron-engine`, `mblock@0.0.0`, `makeblock@1.0.0`, `sensorium@0.4.5`, `msensorium`, `@makeblock/service-api`, and `mblock-core`: no firmware `.bin`/`.hex` files.
4. **GitHub (`Makeblock-official` + community)**:
   - Queried all **83** public repos under `Makeblock-official`.
   - Downloaded and scanned full repository ZIP archives for `Makeblock-official/neuron-engine`, `Makeblock-official/MSmartServo-Driver`, `Makeblock-official/Makeblock-Firmware` (only AVR `.hex` tools: `base_shield.hex`, `leonardo.hex`, `mbot.hex`, `uno.hex`), `Makeblock-official/Makeblock-Libraries`, and `tlack/makeblock-auriga-ms12a-smart-servo`: protocol/driver source only, no Smart Servo firmware binary and no hidden bootloader-exit opcode.
5. **Web search**:
   - Confirmed Makeblock does not publish standalone MS-12A `.bin`/`.hex` firmware outside mBlock / mobile apps.

---

## 6. Bootloader & bus protocol reference

Verified across `novapi_v1.1.22` (`src/index.js`), `cyberpi_test_updated_v1.1.264`, `mbuild_v0.0.8`, `motionblock_v0.3.11`, and `Makeblock-official/neuron-engine` (`lib/engine/logic/system.js`, `update.js`, `process.js`, `table.js`):

- **Port numbering**: Ports `M1..M6` = bus port `7..12` (**`M5 = 11 / 0x0b`**).
- **Host -> NovaPi pass-through framing**:
  - Enter raw bus mode 3 with an `F3..F4` frame carrying payload `0d 00 03` (`_prepareUpdate`); exit with `0d 00 00` (`_endUpdate`).
  - `F3` frame: `F3 <(F3 + lenLo + lenHi) & 0xFF> <lenLo> <lenHi> <payload> <sum(payload) & 0xFF> F4`.
- **Raw Neuron bus frame (`f8f9`)**: `F8 <payload> <sum(payload) & 0x7F> F9`.
- **Standard system & `0x61` opcodes**:
  - `0x10` Arrange / assign ID: `[port, 0xff, 0x10, 0x00]`.
    - Normal Smart Servo (`type = 0x60 < 0x61`) replies without subtype: `[port, modID, 0x10, 0x60]`.
    - Modules with `type` in `0x61..0x7f` include subtype: `[port, modID, 0x10, type, subtype]`.
    - A module truly in bootloader replies with `type = 0x00, subtype = 0x00` (`neuron-engine` `process.js` routes `blocktype === 0` to `update.handleBootloadBlock`). Since broken `INDEX1` still reports `0x60`, it is not cleanly responding as a bootloader node either.
  - `0x11` Reset block: `[port, modID, 0x11]`.
  - `0x12` Get version: `[port, modID, 0x12]` -> `[port, modID, 0x12, BYTE type, BYTE subtype, SHORT version]`.
  - `0x13` Set baudrate (`neuron-engine`): `[modID, 0x13, BYTE rate]` (`0` = `115200`, `1` = `921600`).
  - `0x15` Error/ack response: `[..., 0x15, BYTE code]` where `0x0f` = ok/succ, `0x10` = system busy (`neuron-engine`), `0x11` = channel busy / block type error, `0x12` = wrong service request / checksum error, `0x01` = wrong data.
  - **Safe `0x61` subtypes (`<= 3`, `neuron-engine` `system.js`)**:
    - `0x61 0x01` `FEEDBACKENABLE`: `[modID, 0x61, 0x01, BYTE 0|1]`
    - `0x61 0x02` `RGB`: `[modID, 0x61, 0x02, SHORT R, SHORT G, SHORT B]`
    - `0x61 0x03` `HANDSHAKE`: `[modID, 0x61, 0x03]`
  - **Dangerous `0x61` update/bootloader subtypes (`> 3` — DO NOT SEND TO ANY WORKING SERVO)**:
    1. `0x61 0x05` `_switchBootLoad` / `UPDATEBLOCK`: `[port, modID, 0x61, 0x05, BYTE type, BYTE subtype]` (note `motionblock_v0.3.11` uses `[port, modID, 0x61, 0x05, SHORT type]`).
    2. `0x61 0x06` `allocHardwareId` / `QUERYBLOCKID`: broadcast `[0xff, 0xff, 0x61, 0x06]` or addressed `[port, modID, 0x61, 0x06]` -> replies `[..., 0x61, 0x06, short hidM, short hidL]`. Smart Servo expected pair in `novapi` `hardwareIDTab` is **`hidM = 256 (0x100), hidL = 444 (0x1bc)` (`typeId = 0x6000`)**.
    3. `0x61 0x07` `_updateFileInfo`: `[port, modID, 0x61, 0x07, SHORT 0x00, long length, long crc32]` (CRC32 init `0xFFFFFFFF`) -> replies `[..., 0x61, 0x07, SHORT 0x00, BYTE status]` (`1` = ok).
    4. `0x61 0x07` `_updateChunk` / `SENDFIRMWAREFILEDATA`: 64-byte chunks (`seq = 1..`). Note `novapi` packs `[port, modID, 0x61, 0x07, SHORT seq, block 64B]`, whereas `neuron-engine` inserts `SHORT 0x80` after `SHORT seq`. Replies `[..., 0x61, 0x07, SHORT seq, BYTE status]` (`1` = ok).
    5. `0x61 0x08` `_updateCheckSucc` / `QUERYUPDATERESULT`: `[port, modID, 0x61, 0x08]` -> `BYTE 1` = ok, followed by `0x11` Reset.
    6. `0x61 0x09` `_checkBootLoadVer` (seen in `cyberpi_test_updated_v1.1.264`): `[modID, 0x61, 0x09]` -> `[modID, 0x61, 0x09, BYTE, BYTE]`.
    7. `0x61 0x0C` `_shakeHands` (seen in `cyberpi_test_updated_v1.1.264`): `[modID, 0x61, 0x0C, BYTE type, BYTE subtype]` -> `[modID, 0x15, BYTE]`.
- No bus command reads firmware back; a working servo cannot be dumped over the UART/Neuron bus.

---

## 7. Link notes (on-robot)

- **Wired USB (`CH340`, `COM3`)**: Opening the port resets the board (DTR). Mode 3 + `F8..F9` frames work only after a board power-cycle. There is no live Python over USB here (mode 1 restarts the board, no REPL, Ctrl-C does not stop `main.py`).
- **Bluetooth dongle**: Live Python works (`novapi-companion` `live.py COM3 mode 1` / `eval`), but it does not relay `F8..F9` frames.
- mBlock holds the COM port while open; close mBlock before running scripts.

---

## 8. Other smart-servo facts (measured on this robot)

- `smartservo_class.reset()` is **NOT** a bus reset; it sends the same frame as `set_zero()` (`[port, index, 0x60, 0x30]`).
- Real reset: `from mbuild.smartservo import default_link; default_link.send(bytearray([11, idx, 0x11]))`.
  - The servo misses one read (~`0.4–0.6` s), then rejoins with the same index and zero.
  - It drops any active move and holding torque; send a fresh `move_to` afterwards.
- Stall protection (red LED, ignores moves): trips after ~`2` s at `get_value("current")` ≈ `900`. Only cutting servo power cleared stall protection.
- Additional methods present on `smartservo_class`: `lock_angle`, `release_angle`, `stop`, `back_to_zero`, `get_position` (frame cmd 22 = lock/unlock).
- Never reassign `neurons_engine.default_link`. Never call decorated `mbuild` functions with junk args (they execute instead of raising).

---

## 9. Other recovery & contingency options (priority order)

1. **Apply the M5 bypass (Section 2)** so `lift_hand_servo` (`INDEX1`) and `block_hand` (`INDEX2`) operate immediately without `lower_hand_servo`.
2. **Source a replacement MS-12A smart servo**: coach, teammates, other teams, MakeX organizer / local Makeblock dealer, Shopee/Lazada.
3. **Contact Makeblock / MakeX support** (`service@makeblock.com` + organizer chat): request either the standalone MS-12A (`type 0x60` / `0x6000`) `.bin` firmware image or a warranty replacement ("Smart servo type `0x60` entered firmware update mode with `0x61 0x05` and won't exit, and `novapi v1.1.22` has `0x6000` commented out in `hardwareIDTab`").
4. **Zero-risk passive checks when the robot is connected**:
   - Leave battery unplugged for 10+ minutes, then retest `INDEX1` **alone** on another port (`M1..M4` or `M6`) — note **passive monitoring or safe `0x10`/`0x12`/`0x61 0x03` only**, never `0x61 > 0x03`.
   - Confirm `lift_hand_servo` + `block_hand` work when plugged straight into `M5` without `lower_hand_servo`.
5. **Post-competition SWD inspection (do NOT open a working servo before competition)**:
   - Open the dead `INDEX1` servo, identify the MCU, locate `SWDIO`/`SWCLK`/`GND`/`3V3` pads, and check flash with an ST-Link / CMSIS-DAP + OpenOCD / STM32CubeProgrammer.
   - Only read if readout protection (RDP) is off — **never clear RDP** (mass-erases flash). Its application flash may still be intact if `0x61 0x05` only latched a bootloader flag.
   - Secondary check if needed later: inspect an official Makeblock/Neuron Android `.apk` bundle's `/assets/` on a device with the app installed.

---

## 10. Sources

- Local mBlock 5.6.0 installation (`C:\Users\Public\Programs\mblock\resources\app.asar`, `C:\Users\Sorra\mBlock\exts\`) and cloud `novapi_v1.1.22` (`src/index.js`).
- https://github.com/Makeblock-official/neuron-engine (`lib/engine/logic/system.js`, `update.js`, `process.js`, `table.js`).
- https://github.com/Makeblock-official/MSmartServo-Driver
- https://github.com/Makeblock-official/Makeblock-Libraries
- https://support.makeblock.com/hc/en-us/articles/30138274904855-Product-Firmware-Update-Failure
- Prior on-robot diagnostic log from session `1177195f-a255-4609-a2d6-becdfefa8eb9`.
