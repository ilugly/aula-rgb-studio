"""Non-exclusive access to the lighting interface of the AULA 2.4G receiver."""
import ctypes

import hid


def find_rgb_path():
    return next(
        (entry["path"] for entry in hid.enumerate(0x3554, 0xFA09)
         if entry["usage_page"] == 0xFF02),
        None,
    )


def use_shared_access():
    # HIDAPI defaults to seizing devices on macOS. Leave system input intact.
    set_exclusive = ctypes.CDLL(hid.__file__).hid_darwin_set_open_exclusive
    set_exclusive.argtypes = [ctypes.c_int]
    set_exclusive.restype = None
    set_exclusive(0)


class Dev:
    def __init__(self, path):
        use_shared_access()
        self.device = hid.device()
        self.device.open_path(path)

    def close(self):
        self.device.close()

    def write(self, data):
        try:
            return self.device.write(data)
        except OSError:
            return -1

    def read(self, timeout_ms=100):
        report = self.device.read(20, timeout_ms)
        return bytes(report) if report else None
