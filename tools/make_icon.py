"""Draws the app logo: assets/icon.png and assets/icon.ico (tray, .exe, page header, browser tab).

python tools/make_icon.py            → writes the chosen variant (VARIANT below)
python tools/make_icon.py --sheet DIR → writes DIR/logo-variants.png to compare all variants
"""
import math, os, random, sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARIANT = "front_blade"
S = 1024
PINK, PINK_DARK, WHITE, BLOOD = (255, 46, 160), (196, 18, 120), (255, 255, 255), (150, 0, 24)
RED, RED_DARK = (255, 30, 70), (178, 0, 40)


def taper(d, pts, w0, w1):
    """A sharp limb: straight segments narrowing from w0 to w1."""
    lens = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    total, done = sum(lens), 0.0
    for (a, b), L in zip(zip(pts, pts[1:]), lens):
        wa, wb = w0 + (w1 - w0) * done / total, w0 + (w1 - w0) * (done + L) / total
        done += L
        nx, ny = (b[1] - a[1]) / L, -(b[0] - a[0]) / L
        d.polygon([(a[0] + nx * wa / 2, a[1] + ny * wa / 2), (b[0] + nx * wb / 2, b[1] + ny * wb / 2),
                   (b[0] - nx * wb / 2, b[1] - ny * wb / 2), (a[0] - nx * wa / 2, a[1] - ny * wa / 2)], fill=255)
        d.ellipse((a[0] - wa / 2, a[1] - wa / 2, a[0] + wa / 2, a[1] + wa / 2), fill=255)


def silhouette(scale=1.0, cy_frac=.46, scar=True):
    """Angular spider mask: high sharp knees, faceted chest, long pointed abdomen."""
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    cx, cy, k = S / 2, S * cy_frac, scale
    legs = [((30, -70), (200, -330), (330, -120)), ((40, -35), (300, -200), (450, 60)),
            ((40, 5), (310, -60), (440, 280)), ((30, 45), (230, 70), (300, 420))]
    for hip, knee, tip in legs:
        for s in (-1, 1):
            taper(d, [(cx + s * hip[0] * k, cy + hip[1] * k), (cx + s * knee[0] * k, cy + knee[1] * k),
                      (cx + s * tip[0] * k, cy + tip[1] * k)], 46 * k, 6 * k)
    poly = lambda pts: d.polygon([(cx + x * k, cy + y * k) for x, y in pts], fill=255)
    poly([(0, -165), (95, -95), (80, 40), (0, 75), (-80, 40), (-95, -95)])
    poly([(0, 30), (140, 130), (120, 300), (0, 470), (-120, 300), (-140, 130)])
    for s in (-1, 1):
        taper(d, [(cx + s * 35 * k, cy - 150 * k), (cx + s * 70 * k, cy - 240 * k), (cx + s * 30 * k, cy - 300 * k)], 34 * k, 4 * k)
    if scar:
        d.line([(cx - 120 * k, cy + 230 * k), (cx + 120 * k, cy + 200 * k)], fill=0, width=int(14 * k))
    return m


def fill(mask, top=PINK, bottom=PINK_DARK):
    grad = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        t = y / S
        gd.line([(0, y), (S, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)) + (255,))
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(grad, (0, 0), mask)
    return out


def v_sharp():
    """Clean angular silhouette in pink."""
    return fill(silhouette())


def v_glitch():
    """The same spider split into white and blood-red ghosts, cut by a few glitch slices."""
    m = silhouette()
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    for (dx, dy), col, a in (((18, 7), BLOOD, 235), ((-15, -4), WHITE, 150)):
        layer = Image.new("RGBA", (S, S), col + (0,))
        layer.putalpha(ImageChops.offset(m, dx, dy).point(lambda v: v * a // 255))
        out.alpha_composite(layer)
    out.alpha_composite(fill(m))
    rnd = random.Random(993)
    for _ in range(3):
        y, h, dx = rnd.randrange(int(S * .38), int(S * .8)), rnd.randrange(10, 22), rnd.choice((-1, 1)) * rnd.randrange(16, 32)
        band = out.crop((0, y, S, y + h))
        out.paste((0, 0, 0, 0), (0, y, S, y + h))
        out.alpha_composite(band, (dx, y))
    return out


def v_outline(stroke=31):
    """Line art: only the contour of the spider, drawn as a pink stroke (thicker for tiny tray sizes)."""
    m = silhouette(scar=False).filter(ImageFilter.MaxFilter(9 + stroke // 3 // 2 * 2))
    inner = m.filter(ImageFilter.MinFilter(stroke))
    return fill(ImageChops.subtract(m, inner))


def front_parts(k=1.0, cy_frac=.5, leg=50):
    """Spider seen head-on, crouched to attack: high arched knees, abdomen rising behind the head,
    angry slanted eyes and two hooked fangs. Returns separate masks so variants can colour them apart."""
    cx, cy = S / 2, S * cy_frac
    P = lambda pts: [(cx + x * k, cy + y * k) for x, y in pts]
    legs, abdomen, head, eyes, marks = (Image.new("L", (S, S), 0) for _ in range(5))
    d = ImageDraw.Draw(legs)
    for hip, knee, tip in (((70, 20), (170, -330), (330, 300)), ((85, 0), (290, -270), (440, 250)),
                           ((90, -20), (380, -170), (490, 170)), ((85, -40), (430, -60), (500, 90))):
        for s in (-1, 1):
            taper(d, P([(s * hip[0], hip[1]), (s * knee[0], knee[1]), (s * tip[0], tip[1])]), leg * k, 6 * k)
    for s in (-1, 1):                                    # pedipalps and fangs
        taper(d, P([(s * 70, 80), (s * 105, 150), (s * 70, 210)]), 34 * k, 8 * k)
        taper(d, P([(s * 32, 100), (s * 48, 200), (s * 8, 285)]), 40 * k, 3 * k)
    ImageDraw.Draw(abdomen).ellipse(P([(-140, -290), (140, -50)]), fill=255)
    ImageDraw.Draw(head).polygon(P([(0, -105), (110, -70), (125, 25), (60, 120), (-60, 120), (-125, 25), (-110, -70)]), fill=255)
    e = ImageDraw.Draw(eyes)
    for s in (-1, 1):
        e.polygon(P([(s * 18, 10), (s * 95, -22), (s * 82, 22), (s * 30, 38)]), fill=255)   # big, slanted down to the middle
        e.polygon(P([(s * 22, -40), (s * 58, -55), (s * 52, -32)]), fill=255)              # small upper pair
    m = ImageDraw.Draw(marks)
    for y in (-240, -175, -110):                         # chevrons on the back
        m.line(P([(-100, y - 10), (0, y + 30), (100, y - 10)]), fill=255, width=int(24 * k))
    return dict(legs=legs, abdomen=abdomen, head=head, eyes=eyes, marks=marks)


def front_mask(p):
    m = ImageChops.lighter(ImageChops.lighter(p["legs"], p["abdomen"]), p["head"])
    return ImageChops.subtract(ImageChops.subtract(m, p["eyes"]), ImageChops.subtract(p["marks"], p["head"]))


def v_front():
    """Head-on attack pose, solid pink-to-red, eyes and back chevrons cut out."""
    return fill(front_mask(front_parts()), PINK, RED_DARK)


def back_mark(style):
    """A single tidy pattern for the abdomen (centre 0, -170 in front_parts coordinates)."""
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    P = lambda pts: [(S / 2 + x, S / 2 + y) for x, y in pts]
    if style == "chevrons":                              # two thin, evenly spaced chevrons
        for y in (-245, -195):
            d.line(P([(-62, y), (0, y + 28), (62, y)]), fill=255, width=16, joint="curve")
    elif style == "hourglass":                           # black-widow mark
        d.polygon(P([(-34, -262), (34, -262), (0, -205)]), fill=255)
        d.polygon(P([(0, -193), (34, -136), (-34, -136)]), fill=255)
    elif style == "blade":                               # one long diamond down the spine
        d.polygon(P([(0, -272), (20, -205), (0, -128), (-20, -205)]), fill=255)
    elif style == "rings":                               # arcs following the shell
        for r in (105, 72):
            d.arc(P([(-r, -170 - r * .86), (r, -170 + r * .86)]), 205, 335, fill=255, width=14)
    elif style == "eye":                                 # a third, bigger slit eye on the back
        d.polygon(P([(-60, -215), (0, -248), (60, -215), (0, -182)]), fill=255)
    return m


def v_front_neat(style, leg=50):
    """Like Анфас, but the abdomen sits behind a dark seam and carries one tidy mark."""
    p = front_parts(leg=leg)
    front = ImageChops.lighter(p["legs"], p["head"])
    abd = ImageChops.subtract(p["abdomen"], front.filter(ImageFilter.MaxFilter(19)))
    abd = ImageChops.subtract(abd, ImageChops.multiply(back_mark(style), p["abdomen"].filter(ImageFilter.MinFilter(25))))
    return fill(ImageChops.subtract(ImageChops.lighter(front, abd), p["eyes"]), PINK, RED_DARK)


def v_front_duo():
    """Pink legs and head, a red abdomen behind them — two flat colours, nothing else."""
    p = front_parts()
    out = fill(ImageChops.subtract(p["abdomen"], p["marks"]), RED, RED_DARK)
    body = ImageChops.subtract(ImageChops.lighter(p["legs"], p["head"]), p["eyes"])
    gap = body.filter(ImageFilter.MaxFilter(17))        # thin dark seam so the colours don't bleed together
    out.putalpha(ImageChops.subtract(out.getchannel("A"), gap))
    out.alpha_composite(fill(body, PINK, PINK_DARK))
    return out


def v_front_outline(stroke=31):
    """The head-on spider as a contour, matching the current outline logo."""
    m = front_mask(front_parts()).filter(ImageFilter.MaxFilter(9 + stroke // 3 // 2 * 2))
    return fill(ImageChops.subtract(m, m.filter(ImageFilter.MinFilter(stroke))), PINK, RED)


def v_front_split():
    """Mirror halves: pink on the left, red on the right."""
    m = front_mask(front_parts())
    half = Image.new("L", (S, S), 0)
    ImageDraw.Draw(half).rectangle((S // 2, 0, S, S), fill=255)
    out = fill(ImageChops.subtract(m, half), PINK, PINK)
    out.alpha_composite(fill(ImageChops.multiply(m, half), RED, RED))
    return out


def v_face():
    """Close-up of the face only: wide head, four angry eyes, fangs, no abdomen — reads at 16 px."""
    p = front_parts(k=1.25, cy_frac=.5)
    return fill(ImageChops.subtract(ImageChops.lighter(p["legs"], p["head"]), p["eyes"]), PINK, RED_DARK)


PIXEL = ["................",
         ".#............#.",
         "..#..........#..",
         "#..#..####..#..#",
         ".#..#######.#..#",
         "..#.#######..#..",
         "#..#.######.#..#",
         ".##..######..##.",
         "....########....",
         ".##.########.##.",
         "#..#.######.#..#",
         "..#..######..#..",
         ".#....####....#.",
         ".#.....##.....#.",
         "................",
         "................"]


def v_pixel():
    """8-bit spider on a 16 × 16 grid: crisp in the tray, like a lit key cluster."""
    small = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(PIXEL):
        for x, ch in enumerate(row):
            if ch == "#":
                small.putpixel((x, y), PINK if y < 8 else PINK_DARK)
    return small.resize((S, S), Image.NEAREST)


def v_thread():
    """A smaller spider hanging on a thread from the top edge."""
    m = silhouette(scale=.62, cy_frac=.6, scar=False)
    d = ImageDraw.Draw(m)
    d.line([(S / 2, 0), (S / 2, S * .6 - 165 * .62)], fill=255, width=16)
    return fill(m)


BACK_MARKS = {"clean": "гладкий", "chevrons": "2 шеврона", "hourglass": "песочные часы",
              "blade": "клинок", "rings": "дуги", "eye": "третий глаз"}
VARIANTS = {"sharp": ("Острый", v_sharp), "glitch": ("Глитч (сейчас)", v_glitch), "outline": ("Контур", v_outline),
            "pixel": ("Пиксельный", v_pixel), "thread": ("На нити", v_thread),
            "front": ("Анфас", v_front), "front_duo": ("Анфас, 2 цвета", v_front_duo),
            "front_outline": ("Анфас, контур", v_front_outline), "front_split": ("Анфас, половинки", v_front_split),
            "face": ("Морда", v_face),
            **{f"front_{st}": (f"Анфас: {t}", lambda st=st: v_front_neat(st)) for st, t in BACK_MARKS.items()}}


def square(img):
    bbox = img.getbbox()
    side = max(bbox[2] - bbox[0], bbox[3] - bbox[1]) + 30
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.alpha_composite(img.crop(bbox), ((side - (bbox[2] - bbox[0])) // 2, (side - (bbox[3] - bbox[1])) // 2))
    return sq


def logo(name):
    img = VARIANTS[name][1]()
    return img if name == "pixel" else square(img)


def sheet(out_dir):
    names = list(VARIANTS)
    tile = 300
    W, H = tile * len(names), 470
    sh = Image.new("RGBA", (W, H), (16, 16, 20, 255))
    d = ImageDraw.Draw(sh)
    try:
        font = ImageFont.truetype("segoeuib.ttf", 26)
    except OSError:
        font = ImageFont.load_default()
    for i, n in enumerate(names):
        x0 = i * tile
        big = logo(n).resize((220, 220), Image.LANCZOS)
        sh.alpha_composite(big, (x0 + 40, 30))
        for j, s in enumerate((32, 16)):          # tray sizes, blown up 3× with hard pixels
            bg = Image.new("RGBA", (s, s), (32, 32, 36, 255))
            bg.alpha_composite(logo(n).resize((s, s), Image.LANCZOS))
            bg = bg.resize((s * 3, s * 3), Image.NEAREST)
            sh.alpha_composite(bg, (x0 + 50 + j * 120, 270))
        d.text((x0 + 40, 410), f"{i + 1}. {VARIANTS[n][0]}", fill=(236, 236, 242), font=font)
    path = os.path.join(out_dir, "logo-variants.png")
    sh.save(path)
    return path


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--sheet":
        print(sheet(sys.argv[2]))
        sys.exit()
    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    name = sys.argv[1] if len(sys.argv) > 1 else VARIANT
    img = logo(name)
    resample = Image.NEAREST if name == "pixel" else Image.LANCZOS
    img.resize((256, 256), resample).save(os.path.join(ROOT, "assets", "icon.png"))
    # tray sizes get a heavier stroke / thicker legs so the drawing doesn't fade to a hairline
    bold = (square(v_outline(stroke=81)) if name == "outline" else
            square(v_front_neat(name[6:], leg=95)) if name.startswith("front_") and name[6:] in BACK_MARKS else img)
    frames = [(bold if s <= 32 else img).resize((s, s), resample) for s in (16, 24, 32, 48, 64, 128, 256)]
    frames[-1].save(os.path.join(ROOT, "assets", "icon.ico"), sizes=[f.size for f in frames], append_images=frames[:-1])
    bold.resize((128, 128), resample).save(os.path.join(ROOT, "assets", "logo.png"))   # page header
    prev = os.environ.get("ICON_PREVIEW_DIR")
    if prev:
        for f in frames[:3]:
            bg = Image.new("RGBA", f.size, (32, 32, 36, 255))
            bg.alpha_composite(f)
            bg.resize((f.size[0] * 6, f.size[1] * 6), Image.NEAREST).save(os.path.join(prev, f"tray-{f.size[0]}.png"))
    print("assets/icon.png + icon.ico written")
