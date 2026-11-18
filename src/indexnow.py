"""Signale toutes les adresses du sitemap à IndexNow (Bing, Yandex, Seznam, Naver...).

Usage : python src/indexnow.py            (toutes les pages, après chaque mise en ligne)
        python src/indexnow.py lieux ...  (seulement les adresses qui contiennent un des mots)
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parent.parent
HOST = "gruyeres-tours.com"
KEY = "d98d6f9673d6ca095c873e21f23a3d4e"
assert (root / f"{KEY}.txt").read_text().strip() == KEY

urls = re.findall(r"<loc>([^<]+)</loc>", (root / "sitemap.xml").read_text(encoding="utf-8"))
words = sys.argv[1:]
urls = [u for u in dict.fromkeys(urls) if not words or any(w in u for w in words)]
body = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"https://{HOST}/{KEY}.txt", "urlList": urls}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                             headers={"Content-Type": "application/json; charset=utf-8"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("IndexNow", r.status, len(urls), "adresses")
except urllib.error.HTTPError as e:
    print("IndexNow refus", e.code, e.read()[:300])
