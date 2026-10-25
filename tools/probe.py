"""Step 1: list dongle collections, read LED config + battery (read-only)."""
import sys, time
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
from aula_hid import *

devs = find_dongle()
for p, c in devs:
    print(p.split("#")[1] if "#" in p else p, f"page=0x{c.UsagePage:04x} usage=0x{c.Usage:x} in={c.InputReportByteLength} out={c.OutputReportByteLength} feat={c.FeatureReportByteLength}" if c else "no caps")
target = next((p for p, c in devs if c and c.UsagePage == 0xFF02 and c.OutputReportByteLength == 20), None)
if not target:
    sys.exit("no 0xFF02 collection with 20-byte output")
d = Dev(target)

def read_block(cmd):
    parts, total = {}, None
    for attempt in range(4):
        while d.read(5): pass
        d.write(pkt(cmd | 0x40, 1, 0, 0, b""))
        end = time.time() + 1.5
        while time.time() < end:
            r = d.read(100)
            if not r or r[1] != (cmd | 0x40): continue
            total = r[2] & 0x7F
            parts[r[3]] = r[5:5 + (r[4] & 15)]
            if len(parts) == total:
                return b"".join(parts[i] for i in range(total))
    return None

led = read_block(0x04)
print("LED:", led.hex(" ") if led else "no reply (asleep? press a key)")
if led:
    print("effect", led[10], "sleep", led[24] * 30, "s")
prof = read_block(0x0A)
print("PROFILE:", prof.hex(" ") if prof else None)
