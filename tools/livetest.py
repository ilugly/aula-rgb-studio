"""Step 2: real-time frames only (cmd 0x88 — nothing is stored). Three 5-second phases."""
import sys, time, math, colorsys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
from aula_hid import *

KEYS = [0,12,18,24,30,36,42,48,54,60,66,72,78,88,1,7,13,19,25,31,37,43,49,55,61,67,73,79,85,2,8,14,20,26,32,38,44,50,56,62,68,74,80,86,3,9,15,21,27,33,39,45,51,57,63,69,81,4,10,16,22,28,34,40,46,52,58,64,70,82,5,11,17,35,59,53,77,83,89,87]
target = next(p for p, c in find_dongle() if c and c.UsagePage == 0xFF02 and c.OutputReportByteLength == 20)
d = Dev(target)
GAP = float(sys.argv[1]) if len(sys.argv) > 1 else 0.005

def send(sub, data):
    for p in split(0x88, sub, data):
        d.write(p); time.sleep(GAP)

phase = sys.argv[2] if len(sys.argv) > 2 else "ABC"
if "A" in phase:
    print("A: solid pink"); end = time.time() + 5
    while time.time() < end: send(2, bytes([255, 40, 200])); time.sleep(0.2)
    time.sleep(2.5)
if "B" in phase:
    print("B: all keys blue via per-key"); end = time.time() + 5
    while time.time() < end: send(1, bytes([0, 60, 255, len(KEYS)] + KEYS)); time.sleep(0.1)
    time.sleep(2.5)
if "C" in phase:
    print("C: moving pink/purple wave"); end = time.time() + 6; t0 = time.time()
    cols = sorted(set(k // 6 for k in KEYS))  # LED index // 6 = column
    bands = [[k for k in KEYS if k // 6 * 11 // (max(cols) + 1) == b] for b in range(11)]
    while time.time() < end:
        t = time.time() - t0; out = []
        for b, ks in enumerate(bands):
            if not ks: continue
            v = (math.sin(b / 11 * 6.283 - t * 3) + 1) / 2
            out += [255, int(40 + 0 * v), int(120 + 135 * v) if v > .5 else 200, len(ks)] + ks
            out[-4 - len(ks)] = int(255 - 140 * v)
        send(1, bytes(out))
print("done")
