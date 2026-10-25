"""Draws assets/icon.ico (tray + .exe icon): a dark tile with three rows of keys lit pink → violet."""
import os
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 256
PINK, VIOLET = (255, 79, 216), (106, 61, 255)


def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def draw():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, S - 8, S - 8), radius=56, fill=(22, 22, 28, 255))
    keys = []
    rows = [(4, 0), (4, 0), (3, 1)]  # keys per row, last row has a wide space bar
    top, h, gap = 62, 36, 12
    for r, (n, wide) in enumerate(rows):
        y = top + r * (h + gap)
        widths = [1] * n if not wide else [1, 2, 1]
        units = sum(widths)
        x, w1 = 44, (S - 88 - gap * (len(widths) - 1)) / units
        for w in widths:
            keys.append((x, y, x + w1 * w + gap * (w - 1), y + h))
            x += w1 * w + gap * w
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    for x1, y1, x2, y2 in keys:
        c = lerp(PINK, VIOLET, ((x1 + x2) / 2 - 44) / (S - 88) * .7 + (y1 - top) / 200 * .3)
        g.rounded_rectangle((x1, y1, x2, y2), radius=9, fill=c + (255,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(10)))
    img.alpha_composite(glow)
    return img


if __name__ == "__main__":
    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    icon = draw()
    icon.save(os.path.join(ROOT, "assets", "icon.png"))
    icon.save(os.path.join(ROOT, "assets", "icon.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("assets/icon.ico written")
