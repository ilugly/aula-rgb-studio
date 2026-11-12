"""Read macOS key state without intercepting keyboard input."""
import ctypes

_quartz = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
_key_state = _quartz.CGEventSourceKeyState
_key_state.argtypes = [ctypes.c_int32, ctypes.c_uint16]
_key_state.restype = ctypes.c_bool
_flags_state = _quartz.CGEventSourceFlagsState
_flags_state.argtypes = [ctypes.c_int32]
_flags_state.restype = ctypes.c_uint64

# Windows virtual keys used by the shared settings and effects, mapped to macOS keycodes.
KEYCODES = {
    8: 51, 9: 48, 13: 36, 20: 57, 27: 53, 32: 49, 33: 116, 34: 121, 35: 119,
    36: 115, 37: 123, 38: 126, 39: 124, 40: 125, 45: 114, 46: 117, 91: 55,
    112: 122, 113: 120, 114: 99, 115: 118, 116: 96, 117: 97,
    118: 98, 119: 100, 120: 101, 121: 109, 122: 103, 123: 111,
    160: 56, 161: 60, 162: 59, 164: 58, 165: 61, 186: 41, 187: 24, 188: 43,
    189: 27, 190: 47, 191: 44, 192: 50, 219: 33, 220: 42, 221: 30, 222: 39,
}
KEYCODES.update(zip(range(48, 58), (29, 18, 19, 20, 21, 23, 22, 26, 28, 25)))
KEYCODES.update(zip(range(65, 91), (
    0, 11, 8, 2, 14, 3, 5, 4, 34, 38, 40, 37, 46, 45, 31, 35, 12,
    15, 1, 17, 32, 9, 13, 7, 16, 6,
)))


def pressed(vk):
    return _key_state(0, KEYCODES[vk])


def modifiers():
    flags = _flags_state(0)
    return ((flags >> 19) & 1) | ((flags >> 17) & 2) | ((flags >> 15) & 4) | ((flags >> 17) & 8)
