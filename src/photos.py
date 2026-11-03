"""Télécharge les photos Wikimedia Commons du site et les prépare en WebP (3 tailles).

Usage : python src/photos.py
Écrit : img/<nom>-<largeur>.webp et src/credits.json (auteur, licence, source).
À relancer seulement pour changer la sélection : les fichiers déjà présents sont gardés.
"""
import io
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

UA = {"User-Agent": "GruyeresToursSite/1.0 (https://gruyeres-tours.com; info@gruyeres-tours.com)"}
WIDTHS = (800, 1400, 2400)

# nom court -> fichier Commons ; focus = point d'intérêt horizontal (0 gauche, 1 droite)
PHOTOS = {
    "chateau": "12 Chateau de Gruyères Photo by Giles Laurent.jpg",
    "dents": "Dent de Broc and Dent du Chamois seen from the Niremont - panoramio.jpg",
    "panorama": "Panorama Gruyères.jpg",
    "alpage": "Vache en alpage (lys).jpg",
    "cite": "Cité médiévale de Gruyères (1).jpg",
    "fromage": "Fromagerie de la ville.jpg",
    "cailler": "Schokoladenfabrik Cailler mit Bahnhof.JPG",
    "saint-germain": "Fribourg - Gruyères - Château Saint-Germain - 2.jpg",
    "moleson": "Moleson from north-east.jpg",
    "village": "Gruyeres le village.jpg",
    "lac": "Moléson depuis le lac de la Gruyère-b.jpg",
    "cloches": "Cloches des vaches.jpg",
}

root = Path(__file__).resolve().parent.parent
out = root / "img"
out.mkdir(exist_ok=True)


def info(title):
    params = {"action": "query", "format": "json", "titles": "File:" + title, "prop": "imageinfo",
              "iiprop": "url|size|extmetadata", "iiurlwidth": max(WIDTHS)}
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        page = next(iter(json.load(r)["query"]["pages"].values()))
    return page["imageinfo"][0]


def clean(html_text):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", "", html_text or "")).strip()


def main():
    credits = {}
    for name, title in PHOTOS.items():
        ii = info(title)
        meta = ii.get("extmetadata", {})
        credits[name] = {
            "file": title,
            "artist": clean(meta.get("Artist", {}).get("value")),
            "license": meta.get("LicenseShortName", {}).get("value", ""),
            "licenseUrl": meta.get("LicenseUrl", {}).get("value", ""),
            "source": ii["descriptionurl"],
        }
        if all((out / f"{name}-{w}.webp").exists() for w in WIDTHS):
            print("deja la", name)
            continue
        src_url = ii["thumburl"] if ii.get("width", 0) > max(WIDTHS) else ii["url"]
        with urllib.request.urlopen(urllib.request.Request(src_url, headers=UA), timeout=120) as r:
            im = Image.open(io.BytesIO(r.read()))
            im = ImageOps.exif_transpose(im).convert("RGB")
        for w in WIDTHS:
            copy = im.copy()
            if copy.width > w:
                copy = copy.resize((w, round(copy.height * w / copy.width)), Image.LANCZOS)
            copy.save(out / f"{name}-{w}.webp", "WEBP", quality=74 if w > 1000 else 70, method=6)
        sizes = [round((out / f"{name}-{w}.webp").stat().st_size / 1024) for w in WIDTHS]
        print(f"ok {name} {im.width}x{im.height} -> {sizes} Ko")
        time.sleep(1)

    (root / "src" / "credits.json").write_text(json.dumps(credits, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("credits.json", len(credits))


if __name__ == "__main__":
    main()
