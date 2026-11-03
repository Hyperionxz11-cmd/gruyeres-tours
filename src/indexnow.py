"""Signale toutes les adresses du sitemap à IndexNow (Bing, Yandex, Seznam, Naver...).

Usage : python src/indexnow.py   (après chaque mise en ligne)
"""
import json
import re
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parent.parent
HOST = "gruyeres-tours.com"
KEY = "d98d6f9673d6ca095c873e21f23a3d4e"
assert (root / f"{KEY}.txt").read_text().strip() == KEY

urls = re.findall(r"<loc>([^<]+)</loc>", (root / "sitemap.xml").read_text(encoding="utf-8"))
body = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"https://{HOST}/{KEY}.txt", "urlList": urls}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                             headers={"Content-Type": "application/json; charset=utf-8"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("IndexNow", r.status, len(urls), "adresses")
except urllib.error.HTTPError as e:
    print("IndexNow refus", e.code, e.read()[:300])
