"""Plays a few scenes through the running helper (server.py), N seconds each."""
import json, sys, time, urllib.request

SCENES = [
    ("Розово-фиолетовая волна", "wave", ["#ff4fd8", "#b14dff", "#6a3dff"], {"speed": 35, "scale": 100}),
    ("Северное сияние", "aurora", ["#00ff9d", "#00e1ff", "#4d5bff", "#b300ff"], {"speed": 25, "scale": 110}),
    ("Сакура под дождём", "rain", ["#ffc2e2", "#ff7eb9", "#ff3d8b", "#e0218a"], {"speed": 30, "density": 55}),
    ("Неоновый город", "plasma", ["#ff2a6d", "#d300c5", "#7b2ff7", "#05d9e8"], {"speed": 35, "scale": 90}),
    ("Звёздная ночь", "stars", ["#ffffff", "#9d7bff", "#ff4fd8", "#3d5afe"], {"speed": 30, "density": 60}),
    ("Лавовая лампа", "lava", ["#ff0000", "#ff3c00", "#ff7b00", "#ffb700"], {"speed": 30, "scale": 110}),
    ("Вейпорвейв-вихрь", "swirl", ["#ff71ce", "#01cdfe", "#05ffa1", "#b967ff"], {"speed": 30, "scale": 110}),
    ("Сердцебиение", "heartbeat", ["#ff4fd8", "#b14dff", "#6a3dff"], {"speed": 35, "scale": 100}),
]
secs = float(sys.argv[1]) if len(sys.argv) > 1 else 7
for name, fx, pal, opts in SCENES:
    body = {"fx": fx, "palette": pal, "theme": "", "live": True, "bright": 100, "density": 50, "reverse": False, **opts}
    req = urllib.request.Request("http://127.0.0.1:8777/api/settings", json.dumps(body).encode(), {"Content-Type": "application/json"})
    urllib.request.urlopen(req).read()
    print(time.strftime("%H:%M:%S"), name, flush=True)
    time.sleep(secs)
