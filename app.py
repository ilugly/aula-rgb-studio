"""AULA RGB Studio — tray application.

Starts the local helper (server.py) and sits in the Windows tray:
double-click or "Открыть" opens the control page, the menu toggles the animation,
autostart and quits. `--background` (used by autostart) skips opening the browser.
"""
import os, sys, webbrowser

import pystray
from PIL import Image

import server


def icon_image():
    for p in (os.path.join(server.RES, "assets", "icon.ico"), os.path.join(server.RES, "assets", "icon.png")):
        if os.path.exists(p):
            return Image.open(p)
    return Image.new("RGB", (64, 64), (220, 22, 143))


def main():
    if server.start() is None:
        # another copy already runs: just bring its page up
        webbrowser.open(server.URL)
        return
    if "--background" not in sys.argv:
        webbrowser.open(server.URL)

    def open_page(icon=None, item=None):
        webbrowser.open(server.URL)

    def toggle_live(icon, item):
        server.live.st["live"] = not server.live.st["live"]
        server.live.save()

    def toggle_autostart(icon, item):
        on = not os.path.exists(server.STARTUP_FILE)
        server.set_autostart(on)
        server.live.st["autostart"] = on
        server.live.save()

    def quit_(icon, item):
        server.quit_app()

    tray = pystray.Icon(
        "AULA RGB Studio", icon_image(), "AULA RGB Studio",
        menu=pystray.Menu(
            pystray.MenuItem("Открыть", open_page, default=True),
            pystray.MenuItem("Анимация на клавиатуре", toggle_live, checked=lambda i: server.live.st["live"]),
            pystray.MenuItem("Запускать вместе с Windows", toggle_autostart, checked=lambda i: os.path.exists(server.STARTUP_FILE)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", quit_),
        ),
    )
    server.on_quit = tray.stop
    tray.run()


if __name__ == "__main__":
    main()
