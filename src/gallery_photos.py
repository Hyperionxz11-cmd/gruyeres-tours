"""Télécharge les photos des galeries (src/gallery.json) en WebP 800/1400/2400.

Écrit img/<slug>-<n>-<largeur>.webp et complète gallery.json (source, licenseUrl).
Les fichiers déjà présents sont gardés.
"""
import io
import json
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

from photos import UA, WIDTHS, info, clean, out  # noqa: E402  (photos.py ne retélécharge rien)

src = Path(__file__).resolve().parent
path = src / "gallery.json"
gallery = json.loads(path.read_text(encoding="utf-8"))

for slug, items in gallery.items():
    for i, g in enumerate(items):
        name = f"{slug}-{i + 1}"
        if not g.get("source"):
            ii = info(g["file"])
            meta = ii.get("extmetadata", {})
            g["source"] = ii["descriptionurl"]
            g["licenseUrl"] = meta.get("LicenseUrl", {}).get("value", "")
            g["artist"] = clean(meta.get("Artist", {}).get("value")) or g.get("artist", "")
            g["license"] = meta.get("LicenseShortName", {}).get("value", "") or g.get("license", "")
            g["_url"] = ii["thumburl"] if ii.get("width", 0) > max(WIDTHS) else ii["url"]
        if all((out / f"{name}-{w}.webp").exists() for w in WIDTHS):
            g.pop("_url", None)
            continue
        url = g.pop("_url", None) or info(g["file"])["thumburl"]
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(r.read()))).convert("RGB")
        for w in WIDTHS:
            c = im.copy()
            if c.width > w:
                c = c.resize((w, round(c.height * w / c.width)), Image.LANCZOS)
            c.save(out / f"{name}-{w}.webp", "WEBP", quality=74 if w > 1000 else 70, method=6)
        print("ok", name, im.size)
        time.sleep(1)

path.write_text(json.dumps(gallery, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print("galerie complete")
