# -*- coding: utf-8 -*-
"""Send the M5 INDEX1 smart servo reset and wake-up sequence over COM8."""
import os
import sys
import time


def _bootstrap():
    """Make the NovaPi Companion extension's scripts/ folder importable."""
    here = os.path.dirname(os.path.abspath(__file__))
    scripts = os.environ.get('NOVAPI_SCRIPTS')
    if not scripts:
        ext = os.path.join(os.path.expanduser('~'), '.vscode', 'extensions')
        found = sorted(
            d for d in os.listdir(ext)
            if d.startswith('makeblock-community.novapi-companion-')
        ) if os.path.isdir(ext) else []
        scripts = (os.path.join(ext, found[-1], 'scripts') if found else
                   os.path.abspath(os.path.join(here, '..', '..', 'NovaPi', 'scripts')))
    if not os.path.isfile(os.path.join(scripts, 'live.py')):
        sys.exit('Could not find NovaPi helper scripts in %s' % scripts)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)


_bootstrap()

from board_fs import KeepaliveFilter, open_port  # noqa: E402
from live import Live, MODE_LIVE, MODE_RUN, build_frame  # noqa: E402

RECOVERY_SEQUENCE = [
    ('reset', [11, 1, 0x11], 0.6),
    ('assign_id', [11, 0xFF, 0x10, 0x00], 0.3),
    ('baud_115200', [11, 1, 0x13, 0x00], 0.1),
    ('sys_handshake', [11, 1, 0x61, 0x03], 0.1),
    ('feedback_en', [11, 1, 0x61, 0x01, 0x01], 0.1),
    ('servo_handshake', [11, 1, 0x60, 0x18], 0.1),
    ('cmd_mode_0', [11, 1, 0x60, 0x19, 0x00], 0.1),
    ('clr_comp', [11, 1, 0x60, 0x15], 0.1),
    ('release_brake', [11, 1, 0x60, 0x16, 0x01], 0.1),
    ('pwm_zero', [11, 1, 0x60, 0x35, 0x00, 0x00, 0x00], 0.1),
    ('led_blue', [11, 1, 0x60, 0x17, 0x00, 0x00, 0x00, 0x00, 0x7F, 0x01], 0.2),
]

MODE3_QUERIES = [
    ('query_version', [11, 1, 0x12], 0.2),
    ('query_angle', [11, 1, 0x60, 0x36, 0x00], 0.2),
]


def drain_banner(ser, seconds=2.0):
    """Wait for boot banner bytes and return text minus dongle keepalives."""
    kf = KeepaliveFilter()
    raw = bytearray()
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            raw += kf.feed(chunk)
    return bytes(raw).decode('utf-8', 'replace').strip(), kf.seen


def neuron_frame(payload):
    """Wrap a payload in raw Neuron bus framing (F8 <payload> <ck7> F9)."""
    return bytes([0xF8]) + bytes(payload) + bytes([sum(payload) & 0x7F, 0xF9])


def extract_f8_frames(buf):
    """Pop complete F8..F9 frames from bytearray buf."""
    frames = []
    while True:
        start = buf.find(0xF8)
        if start < 0:
            del buf[:]
            return frames
        if start > 0:
            del buf[:start]
        end = buf.find(0xF9, 1)
        if end < 0:
            return frames
        frames.append(bytes(buf[1:end]))
        del buf[:end + 1]


def run_live_path(board):
    """Execute baseline read, recovery sequence, and post-check over live mode."""
    setup = (
        "import time, novapi\n"
        "from mbuild.smartservo import smartservo_class, default_link\n"
        "s1 = smartservo_class('M5', 'INDEX1')\n"
        "s2 = smartservo_class('M5', 'INDEX2')\n"
        "def _rd(s):\n"
        "    out = []\n"
        "    for k in ('angle', 'voltage', 'temperature'):\n"
        "        try: out.append(s.get_value(k))\n"
        "        except Exception as e: out.append(repr(e))\n"
        "    return out\n"
        "online_debug_respond('ok')"
    )
    print('live setup:', board.run(setup, timeout=5.0))
    print('baseline block_ids:', board.evaluate('novapi.get_mbuild_block_ids()'))
    print('baseline (INDEX1, INDEX2) [angle, V, C]:', board.evaluate('(_rd(s1), _rd(s2))'))

    for label, payload, delay in RECOVERY_SEQUENCE:
        res = board.evaluate('default_link.send(bytearray(%r))' % payload)
        print('  sent %-16s %s -> %s' % (label, [hex(b) for b in payload], res))
        time.sleep(delay)

    print('post block_ids:', board.evaluate('novapi.get_mbuild_block_ids()'))
    print('post (INDEX1, INDEX2) [angle, V, C]:', board.evaluate('(_rd(s1), _rd(s2))'))


def run_mode3_fallback(ser):
    """Send Neuron F8..F9 frames over wired USB pass-through mode 3."""
    print('live mode unavailable; falling back to mode 3 pass-through...')
    ser.reset_input_buffer()
    ser.write(build_frame(bytes([0x0D, 0x00, 0x03])))
    time.sleep(0.3)

    rx_buf = bytearray()
    total_frames = 0
    m5_replies = []
    try:
        for label, payload, delay in RECOVERY_SEQUENCE + MODE3_QUERIES:
            ser.write(neuron_frame(payload))
            print('  tx %-16s %s' % (label, [hex(b) for b in payload]))
            deadline = time.monotonic() + max(delay, 0.2)
            while time.monotonic() < deadline:
                chunk = ser.read(ser.in_waiting or 1)
                if chunk:
                    rx_buf += chunk
            for frame in extract_f8_frames(rx_buf):
                total_frames += 1
                if len(frame) >= 2 and frame[0] == 0x0B:
                    hex_str = ' '.join('%02x' % b for b in frame[:-1])
                    print('    M5 reply (%s): [%s]' % (label, hex_str))
                    m5_replies.append(hex_str)
    finally:
        ser.write(build_frame(bytes([0x0D, 0x00, 0x00])))
        time.sleep(0.1)
    print('mode 3 summary: %d F8 frames seen, %d from port 11 (M5)' % (total_frames, len(m5_replies)))


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else 'COM8'
    print('opening %s...' % port)
    ser = open_port(port, 115200, 0.1)
    board = Live(port, ser=ser)
    try:
        banner, is_dongle = drain_banner(ser, 2.0)
        print('transport: %s' % ('dongle' if is_dongle else 'usb/serial'))
        if banner:
            print('boot banner:\n%s' % banner)

        board.mode(MODE_LIVE)
        if board.evaluate('1') is not None:
            try:
                run_live_path(board)
            finally:
                board.mode(MODE_RUN)
        else:
            run_mode3_fallback(ser)
    finally:
        board.close()
        print('closed %s.' % port)


if __name__ == '__main__':
    main()
