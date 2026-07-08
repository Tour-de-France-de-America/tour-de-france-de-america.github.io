#!/usr/bin/env python3
"""
One-off asset generator for the share image + touch icon (branding, not data).
Renders web/og.png (1200x630 Open Graph card) and web/icon-180.png (touch icon)
in the site's colors. Run once; the PNGs are committed and served statically.

    python3 src/make_og.py
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")

NAVY = (12, 12, 26)
RED = (224, 52, 74)       # a touch brighter than Code Red, for contrast on dark
BLUE = (60, 59, 110)
WHITE = (254, 254, 254)
SILVER = (206, 206, 206)
GOLD = (244, 208, 63)
LIGHT = (205, 214, 240)

FONTS = {
    "impact": "/System/Library/Fonts/Supplemental/Impact.ttf",
    "georgia_it": "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
    "georgia": "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "courier": "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
}


def font(key, size):
    path = FONTS.get(key, "")
    if not os.path.exists(path):
        path = FONTS["georgia"] if os.path.exists(FONTS["georgia"]) else None
    return ImageFont.truetype(path, size) if path else ImageFont.load_default()


def star(cx, cy, R, r, rot=-90):
    return [(cx + (R if i % 2 == 0 else r) * math.cos(math.radians(rot + i * 36)),
             cy + (R if i % 2 == 0 else r) * math.sin(math.radians(rot + i * 36)))
            for i in range(10)]


def w(draw, text, fnt):
    return draw.textlength(text, font=fnt)


def make_og():
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)

    # starfield
    rnd = random.Random(1776)
    for _ in range(150):
        x, y = rnd.randint(0, W), rnd.randint(0, H)
        s = rnd.choice([1, 1, 1, 2])
        c = rnd.choice([WHITE, LIGHT, (255, 246, 200)])
        d.ellipse([x, y, x + s, y + s], fill=c)

    # top + bottom tricolor ribbons (repeating red/white/blue like the site)
    for ry in (0, H - 14):
        for i, x in enumerate(range(0, W, 80)):
            d.rectangle([x, ry, x + 80, ry + 14], fill=(RED, WHITE, BLUE)[i % 3])

    # small gold star up top
    d.polygon(star(W / 2, 96, 30, 12), fill=GOLD)

    # title, two lines, auto-fit
    size = 132
    f = font("impact", size)
    while w(d, "TOUR DE FRANCE", f) > W - 130 and size > 60:
        size -= 4
        f = font("impact", size)

    def centered_shadow(text, y, fnt, fill):
        x = (W - w(d, text, fnt)) / 2
        d.text((x + 4, y + 4), text, font=fnt, fill=(0, 0, 0))
        d.text((x, y), text, font=fnt, fill=fill)

    centered_shadow("TOUR DE FRANCE", 150, f, WHITE)

    # line 2: "de " silver + "AMERICA" red, centered as a unit
    de, am = "de ", "AMERICA"
    total = w(d, de, f) + w(d, am, f)
    x0 = (W - total) / 2
    y2 = 150 + size + 6
    d.text((x0 + 4, y2 + 4), de, font=f, fill=(0, 0, 0))
    d.text((x0 + 4 + w(d, de, f), y2 + 4), am, font=f, fill=(0, 0, 0))
    d.text((x0, y2), de, font=f, fill=SILVER)
    d.text((x0 + w(d, de, f), y2), am, font=f, fill=RED)

    # tagline
    tag = "What if only the six Americans counted in the Tour de France?"
    tf = font("georgia_it", 34)
    d.text(((W - w(d, tag, tf)) / 2, 468), tag, font=tf, fill=LIGHT)

    # footer url
    url = "tour-de-france-de-america.github.io"
    uf = font("courier", 26)
    d.text(((W - w(d, url, uf)) / 2, 552), url, font=uf, fill=GOLD)

    img.save(os.path.join(WEB, "og.png"))
    print("wrote web/og.png (1200x630)")


def make_icon():
    S = 180
    img = Image.new("RGB", (S, S), (12, 20, 48))
    d = ImageDraw.Draw(img)
    d.polygon(star(S / 2, S / 2 + 4, 62, 26), fill=GOLD)
    img.save(os.path.join(WEB, "icon-180.png"))
    print("wrote web/icon-180.png (180x180)")


if __name__ == "__main__":
    make_og()
    make_icon()
