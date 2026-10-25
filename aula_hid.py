"""Minimal Windows HID access to the AULA F75 2.4G dongle (3554:FA09), no extra packages."""
import ctypes, ctypes.wintypes as wt, sys, time, uuid

setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
hid = ctypes.WinDLL("hid", use_last_error=True)
k32 = ctypes.WinDLL("kernel32", use_last_error=True)

class GUID(ctypes.Structure):
    _fields_ = [("Data1", wt.DWORD), ("Data2", wt.WORD), ("Data3", wt.WORD), ("Data4", ctypes.c_ubyte * 8)]

class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("InterfaceClassGuid", GUID), ("Flags", wt.DWORD), ("Reserved", ctypes.c_void_p)]

class HIDP_CAPS(ctypes.Structure):
    _fields_ = [("Usage", wt.USHORT), ("UsagePage", wt.USHORT), ("InputReportByteLength", wt.USHORT),
                ("OutputReportByteLength", wt.USHORT), ("FeatureReportByteLength", wt.USHORT),
                ("Reserved", wt.USHORT * 17), ("rest", wt.USHORT * 10)]

class OVERLAPPED(ctypes.Structure):
    _fields_ = [("Internal", ctypes.c_void_p), ("InternalHigh", ctypes.c_void_p), ("Offset", wt.DWORD),
                ("OffsetHigh", wt.DWORD), ("hEvent", wt.HANDLE)]

setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
setupapi.SetupDiGetClassDevsW.argtypes = [ctypes.POINTER(GUID), wt.LPCWSTR, wt.HWND, wt.DWORD]
setupapi.SetupDiEnumDeviceInterfaces.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(GUID), wt.DWORD, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA)]
setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [ctypes.c_void_p, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA), ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
k32.CreateFileW.restype = wt.HANDLE
k32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE]
k32.CreateEventW.restype = wt.HANDLE
hid.HidD_GetPreparsedData.argtypes = [wt.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDP_CAPS)]
hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]

GENERIC_RW = 0xC0000000
SHARE_RW = 3
OPEN_EXISTING = 3
FILE_FLAG_OVERLAPPED = 0x40000000
INVALID = ctypes.c_void_p(-1).value


def hid_paths():
    g = GUID()
    hid.HidD_GetHidGuid(ctypes.byref(g))
    h = setupapi.SetupDiGetClassDevsW(ctypes.byref(g), None, None, 0x12)
    i = 0
    while True:
        d = SP_DEVICE_INTERFACE_DATA(); d.cbSize = ctypes.sizeof(d)
        if not setupapi.SetupDiEnumDeviceInterfaces(h, None, ctypes.byref(g), i, ctypes.byref(d)):
            break
        need = wt.DWORD()
        setupapi.SetupDiGetDeviceInterfaceDetailW(h, ctypes.byref(d), None, 0, ctypes.byref(need), None)
        buf = ctypes.create_string_buffer(need.value)
        ctypes.cast(buf, ctypes.POINTER(wt.DWORD))[0] = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
        if setupapi.SetupDiGetDeviceInterfaceDetailW(h, ctypes.byref(d), buf, need, None, None):
            yield ctypes.wstring_at(ctypes.addressof(buf) + 4)
        i += 1


def caps(handle):
    pp = ctypes.c_void_p()
    if not hid.HidD_GetPreparsedData(handle, ctypes.byref(pp)):
        return None
    c = HIDP_CAPS(); hid.HidP_GetCaps(pp, ctypes.byref(c)); hid.HidD_FreePreparsedData(pp)
    return c


class Dev:
    def __init__(self, path):
        self.h = k32.CreateFileW(path, GENERIC_RW, SHARE_RW, None, OPEN_EXISTING, FILE_FLAG_OVERLAPPED, None)
        if self.h == INVALID:
            raise OSError(ctypes.get_last_error(), "open failed")
        self.ev = k32.CreateEventW(None, True, False, None)
        self.rbuf = ctypes.create_string_buffer(64)
        self.ov = None

    def close(self):
        k32.CancelIo(self.h)
        k32.CloseHandle(self.h)
        k32.CloseHandle(self.ev)

    def write(self, data: bytes):
        ov = OVERLAPPED(); ov.hEvent = k32.CreateEventW(None, True, False, None)
        n = wt.DWORD()
        buf = ctypes.create_string_buffer(bytes(data), len(data))
        ok = k32.WriteFile(self.h, buf, len(data), ctypes.byref(n), ctypes.byref(ov))
        if not ok and ctypes.get_last_error() == 997:
            k32.WaitForSingleObject(ov.hEvent, 1000)
            k32.GetOverlappedResult(self.h, ctypes.byref(ov), ctypes.byref(n), False)
        k32.CloseHandle(ov.hEvent)
        return n.value

    def read(self, timeout_ms=100):
        if self.ov is None:
            self.ov = OVERLAPPED(); self.ov.hEvent = self.ev
            k32.ResetEvent(self.ev)
            k32.ReadFile(self.h, self.rbuf, 20, None, ctypes.byref(self.ov))
        if k32.WaitForSingleObject(self.ev, timeout_ms) != 0:
            return None
        n = wt.DWORD()
        k32.GetOverlappedResult(self.h, ctypes.byref(self.ov), ctypes.byref(n), False)
        self.ov = None
        return self.rbuf.raw[:n.value]


def find_dongle():
    out = []
    for p in hid_paths():
        if "vid_3554&pid_fa09" not in p.lower():
            continue
        h = k32.CreateFileW(p, 0, SHARE_RW, None, OPEN_EXISTING, 0, None)
        c = caps(h) if h != INVALID else None
        if h != INVALID:
            k32.CloseHandle(h)
        out.append((p, c))
    return out


def pkt(cmd, total, idx, sub, chunk):
    b = bytearray(20)
    b[0] = 0x13; b[1] = cmd; b[2] = total; b[3] = idx; b[4] = ((sub << 4) | len(chunk)) & 0xFF
    b[5:5 + len(chunk)] = chunk
    b[19] = sum(b[:19]) & 0xFF
    return bytes(b)


def split(cmd, sub, data):
    chunks = [data[i:i + 14] for i in range(0, len(data), 14)] or [b""]
    return [pkt(cmd, len(chunks), i, sub, c) for i, c in enumerate(chunks)]
