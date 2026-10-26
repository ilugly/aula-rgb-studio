"""Animations for the AULA F75, computed per key and packed into the keyboard's live frame.

Every effect returns {led: [r, g, b]} for one moment. `encode` then fits the frame into
what the keyboard accepts (≤126 bytes: groups of [R, G, B, count, led…]).
"""
import ctypes, math, random

# [led, x1, y1, x2, y2] from the official KB.ini
F75 = [[0,30,30,55,57],[12,107,30,132,57],[18,144,30,169,57],[24,183,30,208,57],[30,222,30,247,57],[36,269,30,294,57],[42,305,30,330,57],[48,343,30,368,57],[54,388,30,413,57],[60,439,30,464,57],[66,477,30,502,57],[72,516,30,541,57],[78,555,30,580,57],[88,605,195,630,222],[1,31,81,56,108],[7,70,81,95,108],[13,108,81,133,108],[19,147,81,172,108],[25,184,81,209,108],[31,223,81,248,108],[37,262,81,287,108],[43,300,80,325,107],[49,338,81,363,108],[55,377,81,402,108],[61,416,81,441,108],[67,453,81,478,108],[73,491,81,516,108],[79,531,81,591,108],[85,604,81,629,108],[2,34,120,78,147],[8,89,119,114,146],[14,127,119,152,146],[20,165,119,190,146],[26,204,119,229,146],[32,242,119,267,146],[38,280,119,305,146],[44,318,119,343,146],[50,356,119,381,146],[56,395,119,420,146],[62,433,119,458,146],[68,471,120,496,147],[74,509,119,534,146],[80,549,119,593,146],[86,605,120,630,147],[3,33,158,85,185],[9,98,158,123,185],[15,136,158,161,185],[21,174,158,199,185],[27,213,158,238,185],[33,252,158,277,185],[39,290,158,315,185],[45,327,158,352,185],[51,366,158,391,185],[57,405,158,430,185],[63,443,158,468,185],[69,481,158,506,185],[81,521,158,591,185],[4,33,195,105,222],[10,116,195,141,222],[16,155,195,180,222],[22,193,195,218,222],[28,232,195,257,222],[34,270,196,295,223],[40,309,195,334,222],[46,347,195,372,222],[52,384,195,409,222],[58,424,195,449,222],[64,463,195,488,222],[70,502,195,558,222],[82,567,195,592,222],[5,34,234,69,261],[11,79,234,114,261],[17,122,235,157,262],[35,174,235,400,262],[59,463,236,497,263],[53,414,235,449,262],[77,529,234,554,261],[83,568,234,593,261],[89,605,234,630,261],[87,604,159,629,186]]
# x, y in 0..1; the board is ~2.4× wider than tall, so distances use y * ASPECT
KEYS = [(led, ((x1 + x2) / 2 - 30) / 600, ((y1 + y2) / 2 - 43) / 206) for led, x1, y1, x2, y2 in F75]
ASPECT = 0.42
POS = {led: (x, y) for led, x, y in KEYS}
COLS = 16
COL_OF = {led: min(COLS - 1, int(x * COLS)) for led, x, y in KEYS}
# Windows virtual-key code of each key (for the effects that react to typing); Fn can't be seen
VK = {0:27,1:192,2:9,3:20,4:160,5:162,7:49,8:81,9:65,10:90,11:91,12:112,13:50,14:87,15:83,16:88,17:164,18:113,19:51,20:69,21:68,22:67,24:114,25:52,26:82,27:70,28:86,30:115,31:53,32:84,33:71,34:66,35:32,36:116,37:54,38:89,39:72,40:78,42:117,43:55,44:85,45:74,46:77,48:118,49:56,50:73,51:75,52:188,53:165,54:119,55:57,56:79,57:76,58:190,60:120,61:48,62:80,63:186,64:191,66:121,67:189,68:219,69:222,70:161,72:122,73:187,74:221,77:37,78:123,79:8,80:220,81:13,82:38,83:40,85:46,86:33,87:34,88:35,89:39}
_user32 = ctypes.WinDLL("user32")


def hex_rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def smooth(u):
    return u * u * (3 - 2 * u)


def cyc(pal, t):
    """Cyclic gradient through the palette (wraps from the last color back to the first)."""
    n = len(pal)
    f = (t % 1) * n
    i = int(f)
    s = smooth(f - i)
    a, b = pal[i % n], pal[(i + 1) % n]
    return [a[c] + (b[c] - a[c]) * s for c in range(3)]


def lin(pal, t):
    """Non-cyclic gradient: t=0 first color, t=1 last."""
    t = min(1.0, max(0.0, t))
    f = t * (len(pal) - 1)
    i = min(int(f), len(pal) - 2)
    s = smooth(f - i)
    a, b = pal[i], pal[i + 1]
    return [a[c] + (b[c] - a[c]) * s for c in range(3)]


def mul(c, k):
    return [v * k for v in c]


def add(a, b):
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


def dist(x1, y1, x2, y2):
    return math.hypot(x1 - x2, (y1 - y2) * ASPECT)


class Effect:
    keys = False  # reacts to typing

    def __init__(self):
        self.t = 0.0      # animation time, already scaled by speed
        self.rng = random.Random()

    def band(self, x, y, sc):
        """A fixed position along the animation (0..1) for effects whose color only depends on it, else None."""
        return None

    def step(self, dt, ctx):
        self.t += dt * ctx["sp"] * (-1 if ctx["reverse"] else 1)
        return self.frame(dt * ctx["sp"], ctx)


# ---------------------------------------------------------------- gradient fields
class Field(Effect):
    def frame(self, dt, ctx):
        pal, sc, t = ctx["pal"], ctx["sc"], self.t
        return {led: cyc(pal, self.s(x, y, sc) - t * 0.35) for led, x, y in KEYS}

    def band(self, x, y, sc):
        return self.s(x, y, sc)


class Wave(Field):
    def s(self, x, y, sc): return x / sc


class Center(Field):
    def s(self, x, y, sc): return abs(x - .5) * 2 / sc


class Diagonal(Field):
    def s(self, x, y, sc): return (x * .8 + y * .5) / sc


class Rings(Field):
    def s(self, x, y, sc): return dist(x, y, .5, .5) * 1.6 / sc


class Swirl(Field):
    def s(self, x, y, sc):
        return math.atan2((y - .5) * ASPECT, x - .5) / (2 * math.pi) + dist(x, y, .5, .5) * .9 / sc


class Static(Effect):
    def frame(self, dt, ctx):
        return {led: cyc(ctx["pal"], x / ctx["sc"] * .999) for led, x, y in KEYS}

    def band(self, x, y, sc):
        return x / sc * .999


class Breathe(Effect):
    def frame(self, dt, ctx):
        b = .2 + .8 * (.5 - .5 * math.cos(self.t * 2.2)) ** 1.5
        return {led: mul(cyc(ctx["pal"], self.t * .06 + x * .25 / ctx["sc"]), b) for led, x, y in KEYS}

    def band(self, x, y, sc):
        return x * .999


class Aurora(Effect):
    def frame(self, dt, ctx):
        pal, sc, t = ctx["pal"], ctx["sc"], self.t
        out = {}
        for led, x, y in KEYS:
            v = math.sin(x * 3.1 / sc + t * .7) + math.sin(y * 2.3 - t * .5 + x * 1.7) + math.sin((x + y) * 2.2 / sc + t * .33)
            curtain = .35 + .65 * (.5 + .5 * math.sin(x * 5.0 / sc + t * .9 + math.sin(y * 3 + t * .4) * 1.4)) ** 2
            out[led] = mul(cyc(pal, v / 6 + t * .04), curtain)
        return out


class Plasma(Effect):
    def frame(self, dt, ctx):
        pal, sc, t = ctx["pal"], ctx["sc"], self.t
        out = {}
        for led, x, y in KEYS:
            v = (math.sin(x * 6 / sc + t) + math.sin(y * 4 + t * 1.3) + math.sin((x + y) * 5 / sc + t * .7)
                 + math.sin(dist(x, y, .5 + .3 * math.sin(t * .3), .5) * 14 / sc - t * 1.5))
            out[led] = cyc(pal, v / 8 + t * .05)
        return out


class Lava(Effect):
    """A lava lamp: a few blobs with clear edges slowly rise from the hot bottom, cool at the top and
    sink back, merging when they meet. The palette runs dark liquid → glowing wax (first → last colour)."""
    LANES = [(.12, .085, .23, 0.0), (.33, .07, .17, 2.1), (.55, .095, .2, 4.0), (.75, .075, .26, 1.2), (.92, .08, .19, 5.2)]

    def frame(self, dt, ctx):
        pal, sc, t = ctx["pal"], ctx["sc"], self.t
        blobs = []
        for x0, r, speed, off in self.LANES:
            ph = t * speed + off
            blobs.append((x0 + .03 * math.sin(ph * 1.7), .5 - .68 * math.cos(ph), r * sc * (1 + .15 * math.sin(ph * 2))))
        liquid = mul(lin(pal, 0), .1)
        out = {}
        for led, x, y in KEYS:
            f = sum(r * r / (dist(x, y, bx, by) ** 2 + 1e-4) for bx, by, r in blobs)
            heat = max(0.0, y - .7) / .3                                  # the lamp's warm base
            col = add(liquid, mul(lin(pal, .3), .3 * heat))
            if f >= 1:                                                     # inside wax: brighter towards the core
                col = lin(pal, .65 + .35 * min(1.0, (f - 1) / 1.5))
            elif f > .55:                                                  # soft rim
                k = smooth((f - .55) / .45)
                col = add(mul(col, 1 - k), mul(lin(pal, .5), k))
            out[led] = col
        return out


class Heartbeat(Effect):
    """A heart monitor: the pulse line sweeps left to right across the keys — flat, a small bump,
    a spike up to the F-row and down to the space bar, another bump — with a bright pen at the
    front and the trace fading behind it."""
    COLS, ROWS = 16, 6
    CELL = {led: (min(15, int(x * 16)), round(y * 5)) for led, x, y in KEYS}

    def __init__(self):
        super().__init__()
        self.pen = 0.0        # pen position in columns
        self.trace = {}       # column → (lowest row, highest row, time drawn)

    @staticmethod
    def wave(p):
        """Pulse height (row, 0 = top, 5 = bottom) at phase p of one beat."""
        base = 3.2
        if .06 < p < .16:                                   # P bump
            return base - .7 * math.sin((p - .06) / .1 * math.pi)
        if .24 < p < .27:                                   # Q dip
            return base + .6 * (p - .24) / .03
        if .27 <= p < .31:                                  # R spike to the top row
            return base + .6 - (base + .6) * (p - .27) / .04
        if .31 <= p < .35:                                  # S dip to the bottom row
            return 5 * (p - .31) / .04
        if .35 <= p < .39:                                  # back to the line
            return 5 - (5 - base) * (p - .35) / .04
        if .52 < p < .72:                                   # T bump
            return base - 1.0 * math.sin((p - .52) / .2 * math.pi)
        return base

    def frame(self, dt, ctx):
        pal, adt = ctx["pal"], abs(dt)
        beat_cols = 11 * ctx["sc"]                          # one heartbeat spans this many columns
        old = self.pen
        self.pen += adt * 9                                 # columns per second (speed slider scales dt)
        steps = max(1, int((self.pen - old) * 8))
        for i in range(1, steps + 1):                       # sample finely so the spike isn't skipped
            x = old + (self.pen - old) * i / steps
            col, sweep = int(x) % self.COLS, int(x) // self.COLS
            y = self.wave((x / beat_cols) % 1)
            lo, hi, when, was = self.trace.get(col, (y, y, -1, -1))
            if was != sweep:                                # the pen comes back round: start the column afresh
                lo = hi = y
            self.trace[col] = (min(lo, y), max(hi, y), self.t, sweep)
        head = int(self.pen) % self.COLS
        out = {}
        for led, (c, r) in self.CELL.items():
            col = [0, 0, 0]
            if c in self.trace:
                lo, hi, when, _ = self.trace[c]
                if round(lo) <= r <= round(hi):
                    age = self.t - when
                    fade = math.exp(-age * 1.1)
                    col = mul(lin(pal, .2 + .7 * fade), .15 + .85 * fade)
                    if c == head:                           # the pen itself glows white-hot
                        col = add(mul(col, .4), [150, 150, 150])
            out[led] = col
        return out


class Scanner(Effect):
    def band(self, x, y, sc):
        return x * .999

    def frame(self, dt, ctx):
        pal, t = ctx["pal"], self.t
        pos = .5 + .5 * math.sin(t * 1.4)
        w = .09 * ctx["sc"]
        out = {}
        for led, x, y in KEYS:
            b = .06 + math.exp(-((x - pos) / w) ** 2) + .35 * math.exp(-((x - pos) / (w * 3)) ** 2)
            out[led] = mul(cyc(pal, pos * .6 + y * .15), min(1.0, b))
        return out


# ---------------------------------------------------------------- particles
class Particles(Effect):
    def __init__(self):
        super().__init__()
        self.items = []
        self.acc = 0.0

    def spawn_n(self, dt, rate):
        self.acc += abs(dt) * rate
        n = int(self.acc)
        self.acc -= n
        return n


class Stars(Particles):
    def frame(self, dt, ctx):
        pal = ctx["pal"]
        out = {led: mul(cyc(pal, self.t * .02 + x * .3), .08) for led, x, y in KEYS}
        for _ in range(self.spawn_n(dt, 9 * ctx["density"])):
            self.items.append([self.rng.choice(KEYS)[0], 0.0, self.rng.uniform(.8, 2.0), self.rng.random()])
        alive = []
        for s in self.items:
            s[1] += abs(dt)
            if s[1] < s[2]:
                b = math.sin(math.pi * s[1] / s[2]) ** 2
                out[s[0]] = add(mul(out[s[0]], 1 - b), mul(cyc(pal, s[3]), b))
                alive.append(s)
        self.items = alive
        return out


class Confetti(Particles):
    def frame(self, dt, ctx):
        pal = ctx["pal"]
        if not hasattr(self, "glow"):
            self.glow = {led: [0, 0, 0] for led, x, y in KEYS}
        fade = math.exp(-abs(dt) * 2.2)
        for led in self.glow:
            self.glow[led] = mul(self.glow[led], fade)
        for _ in range(self.spawn_n(dt, 14 * ctx["density"])):
            self.glow[self.rng.choice(KEYS)[0]] = cyc(pal, self.rng.random())
        return {led: list(c) for led, c in self.glow.items()}


class Rain(Particles):
    def frame(self, dt, ctx):
        pal = ctx["pal"]
        for _ in range(self.spawn_n(dt, 5 * ctx["density"])):
            col = self.rng.randrange(COLS)
            self.items.append([col, -.1, self.rng.uniform(.9, 1.5), cyc(pal, col / COLS + self.t * .03)])
        out = {led: mul(cyc(pal, x * .5 + self.t * .03), .04) for led, x, y in KEYS}
        alive = []
        for d in self.items:
            d[1] += abs(dt) * d[2]
            if d[1] < 1.6:
                alive.append(d)
        self.items = alive
        for led, x, y in KEYS:
            b = 0.0
            col = None
            for c, head, v, rgb in self.items:
                if c == COL_OF[led] and y <= head + .05:
                    k = math.exp(-(head - y) * 3.2 / ctx["sc"])
                    if k > b:
                        b, col = k, rgb
            if col:
                out[led] = add(mul(out[led], 1 - b), mul(col, b))
        return out


class Meteors(Particles):
    def frame(self, dt, ctx):
        pal = ctx["pal"]
        dx, dy = .92, .39  # travel direction (left-top → right-bottom)
        for _ in range(self.spawn_n(dt, 1.6 * ctx["density"])):
            self.items.append([self.rng.uniform(-.6, .7), self.rng.uniform(-.6, .2), self.rng.uniform(.7, 1.2), self.rng.random()])
        out = {led: mul(cyc(pal, x * .3 + self.t * .02), .07) for led, x, y in KEYS}
        alive = []
        for m in self.items:
            m[0] += dx * abs(dt) * m[2] * .8
            m[1] += dy * abs(dt) * m[2] * .8 / ASPECT
            if m[0] < 1.5 and m[1] < 2:
                alive.append(m)
        self.items = alive
        tail = .45 * ctx["sc"]
        for led, x, y in KEYS:
            for hx, hy, v, c in self.items:
                rx, ry = x - hx, (y - hy) * ASPECT
                along = rx * dx + ry * dy
                perp = abs(-rx * dy + ry * dx)
                if -tail < along < .04 and perp < .08:
                    b = (1 + along / tail) ** 2 * math.exp(-(perp / .035) ** 2)
                    out[led] = add(mul(out[led], 1 - b), mul(cyc(ctx["pal"], c), b))
        return out


class Fire(Effect):
    def frame(self, dt, ctx):
        pal, t = ctx["pal"], self.t * 1.6
        out = {}
        for led, x, y in KEYS:
            flick = (math.sin(x * 13 + t * 3.1) * math.sin(x * 7.3 - t * 2.3) + math.sin(x * 23 + y * 5 - t * 4.7) * .5)
            h = y * 1.25 - .25 + flick * .22 / ctx["sc"]
            k = min(1.0, max(0.0, h))
            out[led] = mul(lin(pal, k), .1 + .9 * k)
        return out


class Glitch(Particles):
    """Digital glitches: the board idles on the first colour with a dark scanline rolling down,
    then tears — rows slide sideways in chunks of the palette colours, blocks drop out to black or
    burn white, and now and then the whole board blinks. Red, white and black look the part."""
    ROW = {led: round(y * 5) for led, x, y in KEYS}

    def burst(self, pal):
        r, kind = self.rng, self.rng.random()
        if kind < .07:                                       # the whole board blinks
            return {"kind": "flash", "age": 0.0, "life": r.uniform(.08, .14), "col": r.choice(pal[1:] or pal)}
        if kind < .55:                                       # a torn row sliding sideways
            r0 = r.randrange(6)
            cuts = sorted(r.random() for _ in range(r.randint(2, 4)))
            return {"kind": "slice", "age": 0.0, "life": r.uniform(.15, .45), "rows": (r0, min(5, r0 + r.randint(0, 1))),
                    "cuts": cuts, "cols": [r.choice(pal) for _ in range(len(cuts) + 1)],
                    "off": r.random(), "vel": r.choice((-1, 1)) * r.uniform(1.5, 5)}
        if kind < .85:                                       # a solid block
            c0, r0 = r.randrange(COLS), r.randrange(6)
            return {"kind": "block", "age": 0.0, "life": r.uniform(.12, .35), "col": r.choice(pal),
                    "box": (c0, c0 + r.randint(1, 5), r0, r0 + r.randint(0, 2))}
        return {"kind": "dead", "age": 0.0, "life": r.uniform(.2, .5),             # scattered dead pixels
                "keys": {r.choice(KEYS)[0]: r.choice(pal) for _ in range(r.randint(3, 9))}}

    def frame(self, dt, ctx):
        pal, adt = ctx["pal"], abs(dt)
        for _ in range(self.spawn_n(dt, 4 * ctx["density"])):
            self.items.append(self.burst(pal))
        roll = (self.t * .3) % 1.6 - .3
        out = {}
        for led, x, y in KEYS:
            b = .5 + .08 * math.sin(self.t * 23 + y * 9) - .4 * math.exp(-((y - roll) / (.1 * ctx["sc"])) ** 2)
            out[led] = mul(pal[0], max(.05, b))
        alive = []
        for g in self.items:
            g["age"] += adt
            if g["age"] >= g["life"]:
                continue
            alive.append(g)
            if g["kind"] == "flash":
                out = {led: list(g["col"]) for led in out}
            elif g["kind"] == "slice":
                lo, hi = g["rows"]
                shift = g["off"] + g["vel"] * g["age"] // .07 * .07  # jumps in steps, not smooth
                for led, x, y in KEYS:
                    if lo <= self.ROW[led] <= hi:
                        u = (x / ctx["sc"] + shift) % 1
                        out[led] = list(g["cols"][sum(u > c for c in g["cuts"])])
            elif g["kind"] == "block":
                c0, c1, r0, r1 = g["box"]
                for led, x, y in KEYS:
                    if c0 <= COL_OF[led] <= c1 and r0 <= self.ROW[led] <= r1:
                        out[led] = list(g["col"])
            else:
                for led, c in g["keys"].items():
                    out[led] = list(c)
        self.items = alive
        return out


# ---------------------------------------------------------------- typing reactive
class Typing(Effect):
    keys = True

    def __init__(self):
        super().__init__()
        self.down = set()
        self.events = []

    def presses(self):
        new = []
        for led, vk in VK.items():
            st = _user32.GetAsyncKeyState(vk)
            pressed = bool(st & 0x8001)
            if pressed and led not in self.down:
                new.append(led)
                self.down.add(led)
            elif not pressed:
                self.down.discard(led)
        return new


class Splash(Typing):
    """Rings spread from every key you press over a dim gradient."""
    def frame(self, dt, ctx):
        pal = ctx["pal"]
        for led in self.presses():
            x, y = POS[led]
            self.events.append([x, y, 0.0, self.rng.random()])
        out = {led: mul(cyc(pal, x * .4 + self.t * .03), .14) for led, x, y in KEYS}
        alive = []
        for e in self.events:
            e[2] += abs(dt) if dt else 0
            if e[2] < 1.4:
                alive.append(e)
        self.events = alive
        for led, x, y in KEYS:
            for ex, ey, age, c in self.events:
                r = age * .55 * ctx["sc"]
                b = math.exp(-((dist(x, y, ex, ey) - r) / .045) ** 2) * (1 - age / 1.4) ** 1.5
                if age < .15 and (x, y) == (ex, ey):
                    b = 1.0
                if b > .02:
                    out[led] = add(mul(out[led], 1 - b), mul(cyc(pal, c), b))
        return out


class Trails(Typing):
    """Pressed keys light up and fade slowly — your typing leaves a glowing trail."""
    def frame(self, dt, ctx):
        pal = ctx["pal"]
        if not hasattr(self, "glow"):
            self.glow = {}
        for led in self.presses():
            self.glow[led] = 1.0
        fade = math.exp(-abs(dt) * 1.1)
        out = {}
        for led, x, y in KEYS:
            g = self.glow.get(led, 0.0)
            if g:
                g *= fade
                self.glow[led] = g if g > .01 else 0.0
            base = mul(cyc(pal, x * .5 + self.t * .05), .1)
            out[led] = add(mul(base, 1 - g), mul(cyc(pal, x * .5 + .5 + self.t * .05), g))
        return out


EFFECTS = {
    "wave": Wave, "center": Center, "diag": Diagonal, "rings": Rings, "swirl": Swirl, "breathe": Breathe,
    "aurora": Aurora, "plasma": Plasma, "lava": Lava, "heartbeat": Heartbeat, "scanner": Scanner,
    "stars": Stars, "confetti": Confetti, "rain": Rain, "meteors": Meteors, "fire": Fire, "glitch": Glitch,
    "splash": Splash, "trails": Trails, "static": Static,
}


# ---------------------------------------------------------------- packing
# The keyboard takes ≤126 bytes per frame: groups of [R, G, B, count, led…]. With 80 keys that is
# 11 colors. A key that hops from one group to another between frames flickers on the keyboard,
# so groups are kept stable: fixed bands for effects that have them, otherwise clusters that
# only give up a key when its color has clearly moved away.
BUDGET = 126
GROUPS = (BUDGET - len(KEYS)) // 4   # 11
MOVE = 30 ** 2                        # squared RGB distance before a key changes group


def _d2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def _mean(cols):
    n = len(cols)
    return [sum(c[i] for c in cols) / n for i in range(3)]


def _median_cut(colors, n):
    """{led: rgb} → [[led…]] at most n groups of similar color."""
    boxes = [list(colors.items())]
    while len(boxes) < n:
        best = None
        for box in boxes:
            if len(box) < 2:
                continue
            for ch in range(3):
                w = max(c[ch] for _, c in box) - min(c[ch] for _, c in box)
                if best is None or w > best[0]:
                    best = (w, box, ch)
        if not best or best[0] < 1:
            break
        _, box, ch = best
        box.sort(key=lambda it: it[1][ch])
        boxes.remove(box)
        boxes += [box[:len(box) // 2], box[len(box) // 2:]]
    return [[led for led, _ in box] for box in boxes]


class Encoder:
    def __init__(self):
        self.groups = None  # [[led…]] carried over between frames

    def _cluster(self, colors):
        if self.groups is None:
            self.groups = _median_cut(colors, GROUPS)
        groups = [g for g in self.groups if g]
        cents = [_mean([colors[l] for l in g]) for g in groups]
        where = {l: i for i, g in enumerate(groups) for l in g}
        moved = False
        for led, c in colors.items():
            i = where[led]
            e = _d2(c, cents[i])
            if e <= MOVE:
                continue
            j = min(range(len(cents)), key=lambda k: _d2(c, cents[k]))
            if j != i and _d2(c, cents[j]) < e * .5:
                groups[i].remove(led); groups[j].append(led); where[led] = j; moved = True
        groups = [g for g in groups if g]
        # use free slots for the keys that fit their group worst (a sparkle, a meteor head)
        while len(groups) < GROUPS:
            cents = [_mean([colors[l] for l in g]) for g in groups]
            worst = max(((_d2(colors[l], cents[i]), i, l) for i, g in enumerate(groups) for l in g if len(g) > 1), default=None)
            if not worst or worst[0] <= MOVE:
                break
            groups[worst[1]].remove(worst[2]); groups.append([worst[2]])
        self.groups = groups
        return groups

    def encode(self, colors, bright, fx=None, sc=1.0):
        """{led: rgb floats} → (frame bytes, {led: rgb the keyboard shows})."""
        cols = {l: [min(255.0, max(0.0, v * bright)) for v in c] for l, c in colors.items()}
        if fx is not None and fx.band(.5, .5, sc) is not None:
            bands = [[] for _ in range(GROUPS)]
            for led, x, y in KEYS:
                bands[min(GROUPS - 1, int(fx.band(x, y, sc) % 1 * GROUPS))].append(led)
            groups = [g for g in bands if g]
        else:
            groups = self._cluster(cols)
        out, shown = bytearray(), {}
        for g in groups:
            rgb = [int(round(v)) for v in _mean([cols[l] for l in g])]
            for l in g:
                shown[l] = rgb
            if max(rgb) < 4:
                continue  # dark keys are simply left out
            for i in range(0, len(g), 255):
                part = sorted(g[i:i + 255])
                out += bytes(rgb + [len(part)] + part)
        return (bytes(out) or bytes([0, 0, 0, 1, 0])), shown
