"""Global Windows hotkeys: switch scenes, colour themes and brightness without opening the page.

The keyboard's own Fn shortcuts are handled inside its firmware and never reach the PC, so these
use Ctrl+Alt instead. THEMES and SCENES mirror the lists in web/index.html (keep them in sync).
"""
import ctypes, threading, time
from ctypes import wintypes

THEMES = {
    "pinkpurple": ["#ff4fd8", "#b14dff", "#6a3dff"],
    "sakura": ["#ffc2e2", "#ff7eb9", "#ff3d8b", "#e0218a"],
    "cyberpunk": ["#ff2a6d", "#d300c5", "#7b2ff7", "#05d9e8"],
    "vaporwave": ["#ff71ce", "#01cdfe", "#05ffa1", "#b967ff"],
    "aurora": ["#00ff9d", "#00e1ff", "#4d5bff", "#b300ff"],
    "ocean": ["#00e5ff", "#0091ff", "#2b3cff", "#00ffc8"],
    "sunset": ["#ff2e63", "#ff6a3d", "#ffb347", "#c13584"],
    "galaxy": ["#ffffff", "#9d7bff", "#ff4fd8", "#3d5afe"],
    "ice": ["#ffffff", "#a8e6ff", "#3fa9ff", "#6a5cff"],
    "emerald": ["#00330d", "#008f2e", "#00d84a", "#6cff6c"],
    "malachite": ["#002a0c", "#008a2e", "#e8b33a"],
    "fire": ["#3a0000", "#c81000", "#ff5a00", "#ffb300", "#fff1a0"],
    "lava": ["#ff0000", "#ff3c00", "#ff7b00", "#ffb700"],
    "candy": ["#ff4fd8", "#ffe14f", "#4fd8ff", "#8cff4f", "#b14dff"],
    "blood": ["#ff0033", "#8b0000", "#ff4d6d"],
    "glitch": ["#ff0018", "#ffffff", "#000000"],
    "rainbow": ["#ff0000", "#ffa500", "#ffff00", "#00ff00", "#00bfff", "#8a2be2"],
    "beigeemerald": ["#ffe2b8", "#d6b98c", "#00873a"],
    "cappuccino": ["#ffe8c8", "#e0a15a", "#7a3f12"],
    "terracotta": ["#ffd9b0", "#e2683c", "#7a2210"],
    "lavender": ["#ffe4c4", "#c9a2ff", "#7c55ff"],
}
SCENES = [  # fx, theme, speed, scale, density
    ("wave", "pinkpurple", 35, 100, 50), ("aurora", "aurora", 25, 110, 50), ("rain", "sakura", 30, 100, 55),
    ("plasma", "cyberpunk", 35, 90, 50), ("stars", "galaxy", 30, 100, 60), ("lava", "lava", 30, 110, 50),
    ("swirl", "vaporwave", 30, 110, 50), ("meteors", "ice", 45, 100, 55), ("fire", "fire", 40, 100, 50),
    ("breathe", "sunset", 20, 120, 50), ("glitch", "glitch", 35, 100, 55), ("heartbeat", "pinkpurple", 35, 100, 50),
    ("scanner", "cyberpunk", 40, 100, 50), ("center", "ocean", 25, 140, 50), ("confetti", "candy", 40, 100, 60),
    ("rings", "emerald", 30, 100, 50), ("wave", "emerald", 25, 130, 50), ("lava", "malachite", 30, 110, 50),
    ("wave", "beigeemerald", 22, 140, 50), ("wave", "cappuccino", 22, 140, 50), ("wave", "terracotta", 22, 140, 50),
    ("wave", "lavender", 22, 140, 50), ("splash", "pinkpurple", 40, 100, 50),
]

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000
WM_HOTKEY = 0x0312

ACTIONS = {  # id: (default combo, label)
    "scene_next": ("Ctrl+Alt+Right", "Следующая сцена"), "scene_prev": ("Ctrl+Alt+Left", "Предыдущая сцена"),
    "theme_next": ("Ctrl+Alt+Up", "Следующие цвета"), "theme_prev": ("Ctrl+Alt+Down", "Предыдущие цвета"),
    "bright_up": ("Ctrl+Alt+PageUp", "Ярче"), "bright_down": ("Ctrl+Alt+PageDown", "Тусклее"),
    "toggle": ("Ctrl+Alt+Home", "Включить / выключить анимацию"),
}
DEFAULT_KEYS = {k: v[0] for k, v in ACTIONS.items()}
_ACTION = {"scene_next": ("scene", 1), "scene_prev": ("scene", -1), "theme_next": ("theme", 1), "theme_prev": ("theme", -1),
           "bright_up": ("bright", 10), "bright_down": ("bright", -10), "toggle": ("toggle", 0)}
_NAMES = {"Left": 0x25, "Up": 0x26, "Right": 0x27, "Down": 0x28, "PageUp": 0x21, "PageDown": 0x22, "Space": 0x20,
          "Home": 0x24, "End": 0x23, "Insert": 0x2D, "Delete": 0x2E, "Tab": 0x09, "Enter": 0x0D,
          "Minus": 0xBD, "Equal": 0xBB, "Comma": 0xBC, "Period": 0xBE, "Slash": 0xBF, "Backquote": 0xC0,
          "BracketLeft": 0xDB, "BracketRight": 0xDD, "Backslash": 0xDC, "Semicolon": 0xBA, "Quote": 0xDE}
_NAMES.update({f"F{i}": 0x6F + i for i in range(1, 13)})
_NAMES.update({chr(c): c for c in range(0x30, 0x3A)})
_NAMES.update({chr(c): c for c in range(0x41, 0x5B)})
_MODS = {"Ctrl": MOD_CONTROL, "Alt": MOD_ALT, "Shift": MOD_SHIFT, "Win": MOD_WIN}


def parse(combo):
    """'Ctrl+Alt+Right' -> (modifiers, vk); ValueError unless it has a modifier and a known key."""
    parts = str(combo).split("+")
    mods = 0
    for m in parts[:-1]:
        if m not in _MODS:
            raise ValueError("неизвестная клавиша: " + m)
        mods |= _MODS[m]
    if not mods or parts[-1] not in _NAMES:
        raise ValueError("нужна хотя бы одна из Ctrl / Alt / Shift / Win и обычная клавиша")
    return mods, _NAMES[parts[-1]]


def validate(keys):
    seen = set()
    for a, combo in keys.items():
        if a not in ACTIONS:
            raise ValueError("неизвестное действие: " + a)
        p = parse(combo)
        if p in seen:
            raise ValueError("одно сочетание назначено дважды: " + combo)
        seen.add(p)


def _step(live, kind, d):
    st = live.st
    if kind == "scene":
        cur = next((i for i, s in enumerate(SCENES) if s[0] == st["fx"] and s[1] == st["theme"]), -1 if d > 0 else 0)
        fx, th, sp, sc, de = SCENES[(cur + d) % len(SCENES)]
        st.update(fx=fx, theme=th, palette=list(THEMES[th]), speed=sp, scale=sc, density=de, live=True)
    elif kind == "theme":
        names = list(THEMES)
        th = names[((names.index(st["theme"]) if st["theme"] in THEMES else -1 if d > 0 else 0) + d) % len(names)]
        st.update(theme=th, palette=list(THEMES[th]), live=True)
    elif kind == "bright":
        st["bright"] = max(10, min(100, st["bright"] + d))
    else:
        st["live"] = not st["live"]
    live.save()


_failed = []   # combos Windows refused (another program owns them); shown on the page
_dirty = threading.Event()


def reload():
    _dirty.set()


def start(live):
    """Register the hotkeys on a thread of their own; `reload()` re-reads live.st['hk'] after a change."""
    _dirty.set()

    def loop():
        u = ctypes.windll.user32
        ids = {}
        msg = wintypes.MSG()
        while True:
            if _dirty.is_set():
                _dirty.clear()
                for i in ids:
                    u.UnregisterHotKey(None, i)
                ids.clear()
                _failed.clear()
                keys = {**DEFAULT_KEYS, **live.st.get("hk", {})}
                for n, (a, combo) in enumerate(keys.items(), 1):
                    try:
                        mods, vk = parse(combo)
                    except ValueError:
                        continue
                    if u.RegisterHotKey(None, n, mods | MOD_NOREPEAT, vk):
                        ids[n] = a
                    else:
                        _failed.append(combo)
            while u.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                if msg.message == WM_HOTKEY and live.st.get("hotkeys", True) and msg.wParam in ids:
                    try:
                        _step(live, *_ACTION[ids[msg.wParam]])
                    except Exception:
                        pass
            time.sleep(0.05)

    threading.Thread(target=loop, daemon=True).start()
