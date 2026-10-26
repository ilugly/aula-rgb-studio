"""AULA RGB Studio — local helper.

Talks to the AULA F75 2.4G dongle over HID (Windows, no extra packages), plays live
animations by itself (keeps running with the browser closed) and serves the web UI at
http://127.0.0.1:8777/. Started by app.py, which puts it in the system tray.
"""
import ctypes, json, math, os, sys, threading, time, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from aula_hid import find_dongle, Dev, pkt, split

FROZEN = getattr(sys, "frozen", False)           # running as the PyInstaller .exe
RES = getattr(sys, "_MEIPASS", HERE)              # bundled web page, fonts, icon
DATA = os.path.join(os.environ.get("APPDATA", HERE), "AULA RGB Studio")
os.makedirs(DATA, exist_ok=True)
PORT = 8777
URL = f"http://127.0.0.1:{PORT}/"
SETTINGS_FILE = os.path.join(DATA, "settings.json")
STARTUP_FILE = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup\AULA RGB Studio.vbs")
ctypes.WinDLL("winmm").timeBeginPeriod(1)  # 1 ms sleep resolution for the 5 ms packet gaps

CMD_KEYMAP, CMD_CUSTOM, CMD_LED, CMD_PALETTE, CMD_PROFILE, CMD_LIVE = 0x01, 0x02, 0x04, 0x09, 0x0A, 0x88
BLOCK_LEN = {CMD_KEYMAP: 504, CMD_CUSTOM: 378, CMD_LED: 128, CMD_PALETTE: 490}  # keymap: base layer, 126 × 4 bytes

# ---------------------------------------------------------------- keyboard
class Keyboard:
    def __init__(self):
        self.lock = threading.RLock()
        self.dev = None

    def _dev(self):
        if self.dev is None:
            path = next((p for p, c in find_dongle() if c and c.UsagePage == 0xFF02 and c.OutputReportByteLength == 20), None)
            if not path:
                raise RuntimeError("Донгл AULA не найден. Вставь его и переключи клавиатуру в режим 2.4G.")
            self.dev = Dev(path)
        return self.dev

    def _drop(self):
        if self.dev:
            try: self.dev.close()
            except Exception: pass
        self.dev = None

    def _write(self, p):
        if self._dev().write(p) != len(p):
            self._drop()
            raise RuntimeError("Не удалось отправить данные донглу (он отключён?)")

    def _drain(self):
        while self.dev.read(2):
            pass

    def read_block(self, cmd):
        with self.lock:
            self._dev()
            rcmd, parts, total = cmd | 0x40, {}, None
            for _ in range(5):
                self._drain()
                self._write(pkt(rcmd, 1, 0, 0, b""))
                end, last = time.time() + 2, None
                while time.time() < end:
                    if last and time.time() - last > 0.25:
                        break
                    r = self.dev.read(50)
                    if not r or len(r) < 20 or r[1] != rcmd or (sum(r[:19]) & 0xFF) != r[19]:
                        continue
                    if r[2] & 0x80:
                        raise RuntimeError(f"Клавиатура отклонила чтение 0x{rcmd:02x}")
                    last, total = time.time(), r[2] & 0x7F
                    if r[3] < total:
                        parts[r[3]] = r[5:5 + (r[4] & 0x0F)]
                    if len(parts) == total:
                        return b"".join(parts[i] for i in range(total))
                time.sleep(0.08)
            if total is None:
                raise RuntimeError("Клавиатура не отвечает — нажми любую клавишу, чтобы разбудить её, и попробуй ещё раз.")
            raise RuntimeError("Чтение прошло не полностью, попробуй ещё раз.")

    def write_block(self, cmd, data):
        with self.lock:
            self._dev()
            for p in split(cmd, 0, data):
                for _ in range(3):
                    self._drain()
                    self._write(p)
                    end = time.time() + 1
                    ok = False
                    while time.time() < end:
                        r = self.dev.read(50)
                        if r and len(r) >= 20 and r[1] == cmd and r[3] == p[3]:
                            if r[2] & 0x80:
                                raise RuntimeError(f"Клавиатура отклонила команду 0x{cmd:02x}")
                            ok = True
                            break
                    if ok:
                        break
                else:
                    raise RuntimeError(f"Клавиатура не подтвердила запись (пакет {p[3]})")
                time.sleep(0.015)

    def live(self, sub, data):
        with self.lock:
            for p in split(CMD_LIVE, sub, data):
                self._write(p)
                time.sleep(0.005)  # closer than ~5 ms the keyboard drops the frame


kb = Keyboard()

# ---------------------------------------------------------------- animation engine
import effects

DEFAULTS = {"fx": "wave", "theme": "pinkpurple", "palette": ["#ff4fd8", "#b14dff", "#6a3dff"], "speed": 35, "scale": 100,
            "bright": 100, "density": 50, "reverse": False, "fps": 14, "live": False, "autostart": False}


class Live(threading.Thread):
    """Computes the selected animation all the time (the page previews it) and streams it while live is on."""
    def __init__(self):
        super().__init__(daemon=True)
        self.st = dict(DEFAULTS)
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                self.st.update(json.load(f))
        except Exception:
            pass
        if self.st["fx"] not in effects.EFFECTS:
            self.st["fx"] = "wave"
        self.fps_real = 0
        self.error = None
        self.shown = {}
        self.fx_name, self.fx = None, None

    def save(self):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.st, f, ensure_ascii=False, indent=1)

    def run(self):
        last, last_frame, last_sent, sent, clock = time.time(), b"", 0.0, 0, time.time()
        while True:
            st = self.st
            now = time.time()
            dt = min(0.2, now - last)
            last = now
            try:
                if st["fx"] != self.fx_name:
                    self.fx_name, self.fx = st["fx"], effects.EFFECTS.get(st["fx"], effects.Wave)()
                    self.enc = effects.Encoder()
                ctx = {"pal": [effects.hex_rgb(h) for h in st["palette"]] or [[255, 0, 255]],
                       "sc": max(.2, st["scale"] / 100), "sp": st["speed"] / 35, "reverse": st["reverse"],
                       "density": .2 + st["density"] / 50 * .8}
                fr, self.shown = self.enc.encode(self.fx.step(dt, ctx), st["bright"] / 100, self.fx, ctx["sc"])
            except Exception as e:
                self.error = "эффект: " + str(e)
                time.sleep(.5)
                continue
            if st["live"] and (fr != last_frame or now - last_sent > 0.7):
                try:
                    kb.live(1, fr)
                    last_frame, last_sent, self.error = fr, now, None
                    sent += 1
                except Exception as e:
                    self.error = str(e)
                    time.sleep(1)
            if now - clock >= 1:
                self.fps_real, sent, clock = sent, 0, now
            time.sleep(max(0.0, 1 / max(2, st["fps"]) - (time.time() - now)))


live = Live()


# ---------------------------------------------------------------- autostart
def set_autostart(on):
    if on:
        if FROZEN:
            cmd = f'""{sys.executable}"" --background'
        else:
            pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            cmd = f'""{pyw if os.path.exists(pyw) else sys.executable}"" ""{os.path.join(HERE, "app.py")}"" --background'
        with open(STARTUP_FILE, "w", encoding="utf-16") as f:
            f.write(f'CreateObject("WScript.Shell").Run "{cmd}", 0, False\r\n')
    elif os.path.exists(STARTUP_FILE):
        os.remove(STARTUP_FILE)

# ---------------------------------------------------------------- http
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _local(self):
        # only the page served from here may talk to the keyboard
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            self._json({"ok": False, "error": "forbidden"}, 403)
            return False
        return True

    def do_GET(self):
        if not self._local():
            return
        self.path = self.path.split("?", 1)[0]   # "?v=…" only busts the browser cache
        if self.path in ("/", "/index.html"):
            with open(os.path.join(RES, "web", "index.html"), "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        elif self.path in ("/logo.png", "/brand.png", "/favicon.ico"):
            name, ctype = ("icon.ico", "image/x-icon") if self.path == "/favicon.ico" else (self.path[1:], "image/png")
            with open(os.path.join(RES, "assets", name), "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith("/fonts/") and self.path.endswith(".woff2") and "/.." not in self.path:
            fp = os.path.join(RES, "web", "fonts", os.path.basename(self.path))
            if not os.path.isfile(fp):
                return self._json({"ok": False, "error": "not found"}, 404)
            with open(fp, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "font/woff2")
            self.send_header("Cache-Control", "max-age=86400")
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/status":
            self._json({"ok": True, "live": live.st["live"], "fps": live.fps_real, "error": live.error,
                        "settings": live.st, "autostart": os.path.exists(STARTUP_FILE)})
        elif self.path == "/api/frame":
            self._json({"ok": True, "leds": live.shown, "live": live.st["live"]})
        elif self.path == "/api/memory":
            try:
                led = kb.read_block(CMD_LED)
                pal = kb.read_block(CMD_PALETTE)
                custom = kb.read_block(CMD_CUSTOM)
                try:
                    prof = kb.read_block(CMD_PROFILE)
                    battery = prof[0] if prof and prof[0] <= 100 else None
                except Exception:
                    battery = None
                keymap = kb.read_block(CMD_KEYMAP)
                self._json({"ok": True, "led": led.hex(), "palette": pal.hex(), "custom": custom.hex(), "keymap": keymap.hex(), "battery": battery})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
        else:
            self._json({"ok": False, "error": "not found"}, 404)

    def do_POST(self):
        if not self._local():
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            if self.path == "/api/write":
                cmd, data = int(body["cmd"]), bytes.fromhex(body["data"])
                if BLOCK_LEN.get(cmd) != len(data):
                    raise ValueError("неверный блок данных")
                if cmd == CMD_LED and data[126:128] != b"\x5a\xa5":
                    raise ValueError("повреждённый блок настроек")
                kb.write_block(cmd, data)
            elif self.path == "/api/settings":
                for k, v in body.items():
                    if k in DEFAULTS:
                        live.st[k] = v
                live.save()
            elif self.path == "/api/autostart":
                set_autostart(bool(body.get("on")))
            elif self.path == "/api/solid":
                kb.live(2, bytes(body.get("rgb", [255, 40, 200])))
            elif self.path == "/api/quit":
                self._json({"ok": True})
                threading.Timer(0.3, quit_app).start()
                return
            else:
                return self._json({"ok": False, "error": "not found"}, 404)
            self._json({"ok": True})
        except Exception as e:
            self._json({"ok": False, "error": str(e)})


class Server(ThreadingHTTPServer):
    # Windows would otherwise let a second copy bind the same port, and both would drive the keyboard
    allow_reuse_address = False

    def server_bind(self):
        import socket
        self.socket.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE", -5), 1)
        super().server_bind()


on_quit = None  # set by app.py to take the tray icon down first


def quit_app():
    if on_quit:
        on_quit()
    os._exit(0)


def start():
    """Start the web server and the animation thread; None when another copy already runs."""
    try:
        srv = Server(("127.0.0.1", PORT), Handler)
    except OSError:
        return None
    live.start()
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
