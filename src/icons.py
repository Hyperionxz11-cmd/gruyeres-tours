"""Dessine le logo en PNG et ICO (Google, Bing, téléphones) à partir des mêmes tracés que logo.svg.

Sorties : favicon.ico (16, 32, 48), img/icon-48.png ... icon-512.png, apple-touch-icon.png, img/logo-512.png
"""
from pathlib import Path

from PIL import Image, ImageDraw

root = Path(__file__).resolve().parent.parent
FOREST = (14, 40, 32, 255)
GOLD = (201, 164, 106, 255)
GOLD_SOFT = (201, 164, 106, 128)
S = 16  # sur-échantillonnage pour des bords nets


def p(x, y):
    return (x * S, y * S)


def draw_logo(size_units=64, full_bleed=False):
    big = Image.new("RGBA", (size_units * S, size_units * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    if full_bleed:
        d.rectangle([0, 0, 64 * S, 64 * S], fill=FOREST)
    # disque et anneaux
    d.ellipse([p(1.4, 1.4), p(62.6, 62.6)], fill=FOREST, outline=GOLD, width=int(1.8 * S))
    d.ellipse([p(5.4, 5.4), p(58.6, 58.6)], outline=GOLD_SOFT, width=int(.7 * S))
    # montagnes
    mountains = [p(9.5, 41), p(20, 28.2), p(24.6, 33.5), p(32, 21), p(39.6, 31.2), p(43.6, 26.9), p(54.5, 41)]
    d.line(mountains, fill=GOLD, width=int(1.6 * S), joint="curve")
    for pt in (mountains[0], mountains[-1]):
        r = .8 * S
        d.ellipse([pt[0] - r, pt[1] - r, pt[0] + r, pt[1] + r], fill=GOLD)
    # château (silhouette pleine)
    castle = [(17, 46.2), (17, 38), (18.9, 38), (18.9, 35.9), (21.1, 35.9), (21.1, 38), (22.7, 38), (22.7, 35.9), (24.9, 35.9),
              (24.9, 38), (26.5, 38), (26.5, 35.9), (28.7, 35.9), (28.7, 38), (29.2, 38), (29.2, 35), (31.7, 29.4), (34.2, 35),
              (34.2, 41), (35.8, 41), (35.8, 39.5), (37.6, 39.5), (37.6, 41), (39.2, 41), (39.2, 39.5), (41, 39.5), (41, 41),
              (42.6, 41), (42.6, 39.5), (44.4, 39.5), (44.4, 41), (45, 41), (45, 46.2)]
    d.polygon([p(x, y) for x, y in castle], fill=GOLD)
    # colline
    hill = [p(8.5 + i * 47 / 40, 47 - 3 * (1 - ((i - 20) / 20) ** 2)) for i in range(41)]
    d.line(hill, fill=GOLD, width=int(1.4 * S), joint="curve")
    return big


def export(size, path, full_bleed=False):
    big = draw_logo(full_bleed=full_bleed)
    img = big.resize((size, size), Image.LANCZOS)
    img.save(path)
    return img


(root / "img").mkdir(exist_ok=True)
for s in (48, 96, 192, 512):
    export(s, root / "img" / f"icon-{s}.png")
export(512, root / "img" / "logo-512.png")
export(180, root / "apple-touch-icon.png", full_bleed=True)
big = draw_logo()
big.resize((256, 256), Image.LANCZOS).save(root / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
print("ok")
