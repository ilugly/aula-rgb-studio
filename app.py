"""AULA RGB Studio — tray application.

Starts the local helper (server.py) and sits in the Windows tray:
double-click or "Открыть" opens the control page, the menu toggles the animation,
autostart and quits. `--background` (used by autostart) skips opening the browser.
"""
import atexit, os, sys, time, webbrowser

import pystray
from PIL import Image

import server


def icon_image():
    for p in (os.path.join(server.RES, "assets", n) for n in ("tray.png", "icon.ico", "icon.png")):
        if os.path.exists(p):
            return Image.open(p)
    return Image.new("RGB", (64, 64), (220, 22, 143))


def main():
    if server.start() is None:
        # another copy already runs: just bring its page up (autostart stays quiet)
        if "--background" not in sys.argv:
            webbrowser.open(server.URL)
        return
    # start and exit lines show in error.log when the program went away and whether it left on its own
    server.log_error(f"started, pid {os.getpid()}, {' '.join(sys.argv[1:]) or 'no args'}")
    atexit.register(server.log_error, "exited normally")
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

    def make_tray():
        return pystray.Icon(
            "AULA RGB Studio", icon_image(), "AULA RGB Studio",
            menu=pystray.Menu(
                pystray.MenuItem("Открыть", open_page, default=True),
                pystray.MenuItem("Анимация на клавиатуре", toggle_live, checked=lambda i: server.live.st["live"]),
                pystray.MenuItem("Запускать вместе с Windows", toggle_autostart, checked=lambda i: os.path.exists(server.STARTUP_FILE)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Выход", quit_),
            ),
        )

    tray = make_tray()
    server.on_quit = tray.stop
    # if the tray icon dies on its own (explorer restart, a driver hiccup) bring it back instead of exiting
    while True:
        try:
            tray.run()
        except BaseException:
            server.log_error("tray icon crashed")
        server.log_error("tray stopped, restarting it")
        time.sleep(2)
        tray = make_tray()
        server.on_quit = tray.stop


if __name__ == "__main__":
    main()
