"""Global Windows hotkeys: switch scenes, colour themes and brightness without opening the page.

The keyboard's own Fn shortcuts are handled inside its firmware and never reach the PC, so these
use Ctrl+Alt instead. THEMES and SCENES mirror the lists in web/index.html (keep them in sync).
"""
import ctypes, threading
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

MOD_ALT, MOD_CONTROL, MOD_NOREPEAT = 0x1, 0x2, 0x4000
VK_LEFT, VK_UP, VK_RIGHT, VK_DOWN, VK_PRIOR, VK_NEXT, VK_SPACE = 0x25, 0x26, 0x27, 0x28, 0x21, 0x22, 0x20
WM_HOTKEY = 0x0312

HELP = [("Ctrl+Alt+←/→", "предыдущая / следующая сцена"), ("Ctrl+Alt+↑/↓", "следующие / предыдущие цвета"),
        ("Ctrl+Alt+PgUp/PgDn", "ярче / тусклее"), ("Ctrl+Alt+Пробел", "включить / выключить анимацию")]


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


def start(live):
    """Register the hotkeys on a thread of their own; the settings flag `hotkeys` is checked on every press."""
    binds = [(VK_RIGHT, "scene", 1), (VK_LEFT, "scene", -1), (VK_UP, "theme", 1), (VK_DOWN, "theme", -1),
             (VK_PRIOR, "bright", 10), (VK_NEXT, "bright", -10), (VK_SPACE, "toggle", 0)]

    def loop():
        u = ctypes.windll.user32
        ok = [u.RegisterHotKey(None, i + 1, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, b[0]) for i, b in enumerate(binds)]
        if not any(ok):
            return
        msg = wintypes.MSG()
        while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY and live.st.get("hotkeys", True):
                try:
                    _step(live, binds[msg.wParam - 1][1], binds[msg.wParam - 1][2])
                except Exception:
                    pass

    threading.Thread(target=loop, daemon=True).start()
