"""Fabrique les 5 pages de langue, la page d'accueil et le plan du site.

Usage : python src/build.py
Sources : src/template.html et src/i18n/<langue>.json
Sorties : <langue>/index.html, index.html, sitemap.xml
"""
import hashlib
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

BASE = "https://gruyeres-tours.com"
LANGS = ["fr", "de", "en", "pt", "es", "zh"]
DEFAULT = "fr"
# Code de langue complet pour Google et le navigateur (le chemin reste court : /zh/)
TAG = {"zh": "zh-Hans"}
FONT_PRELOAD = (
    '  <link rel="preload" href="/fonts/cormorant-latin-500-normal.woff2" as="font" type="font/woff2" crossorigin>\n'
    '  <link rel="preload" href="/fonts/inter-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>'
)


def tag(lang):
    return TAG.get(lang, lang)

src = Path(__file__).resolve().parent
root = src.parent
template = (src / "template.html").read_text(encoding="utf-8")
texts = {l: json.loads((src / "i18n" / f"{l}.json").read_text(encoding="utf-8")) for l in LANGS}
version = hashlib.sha1((root / "style.css").read_bytes() + (root / "site.js").read_bytes()).hexdigest()[:8]
credits = json.loads((src / "credits.json").read_text(encoding="utf-8"))
WIDTHS = (800, 1400, 2400)
# légende utilisée dans les crédits pour chaque photo
CAPTION = {"chateau": "capChateau", "dents": "capDents", "panorama": "capPanorama", "alpage": "capAlpage",
           "cite": "s1t", "fromage": "alt2", "cailler": "s3t", "saint-germain": "s4t", "moleson": "s5t",
           "village": "capVillage", "lac": "capLac", "cloches": "capCloches", "jogne": "capJogne"}
IMG_RE = re.compile(r'\[\[img (\S+) "([^"]+)" (\w+) (eager|lazy|defer)\]\]')


def img_tag(name, sizes, alt, mode):
    """Une photo en 3 tailles. eager : tout de suite ; lazy : au défilement ; defer : après la page."""
    srcset = ", ".join(f"/img/{name}-{w}.webp {w}w" for w in WIDTHS)
    fallback = f"/img/{name}-1400.webp"
    alt = html.escape(alt, quote=True)
    if mode == "eager":
        return f'<img src="{fallback}" srcset="{srcset}" sizes="{sizes}" alt="{alt}" fetchpriority="high" decoding="async">'
    if mode == "defer":
        return f'<img data-src="{fallback}" data-srcset="{srcset}" sizes="{sizes}" alt="{alt}" decoding="async">'
    return f'<img src="{fallback}" srcset="{srcset}" sizes="{sizes}" alt="{alt}" loading="lazy" decoding="async">'


def credits_list(lang):
    t = texts[lang]
    rows = []
    for name, c in credits.items():
        cap = html.escape(t.get(CAPTION.get(name, ""), name))
        lic = f'<a href="{html.escape(c["licenseUrl"])}" rel="license noopener">{html.escape(c["license"])}</a>' if c["licenseUrl"] else html.escape(c["license"])
        rows.append(f'          <li>{cap} : {html.escape(t["creditsBy"])} {html.escape(c["artist"])}, {lic}, '
                    f'<a href="{html.escape(c["source"])}" rel="noopener">Wikimedia Commons</a></li>')
    return "\n".join(rows)


def make_og():
    """Image de partage 1200 x 630 en JPG (les réseaux sociaux lisent mal le WebP)."""
    og = root / "img" / "og.jpg"
    if og.exists():
        return
    from PIL import Image
    im = Image.open(root / "img" / "chateau-1400.webp").convert("RGB")
    ratio = 1200 / 630
    w, h = im.size
    if w / h > ratio:
        nw = int(h * ratio)
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / ratio)
        im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    im.resize((1200, 630), Image.LANCZOS).save(og, "JPEG", quality=84, optimize=True, progressive=True)
today = date.today().isoformat()

errors = []

# 1. Toutes les langues doivent avoir exactement les mêmes clés
ref_keys = set(texts[DEFAULT])
for l in LANGS:
    missing = ref_keys - set(texts[l])
    extra = set(texts[l]) - ref_keys
    if missing or extra:
        errors.append(f"{l}: manquantes {sorted(missing)} en trop {sorted(extra)}")


def url_of(lang):
    return f"{BASE}/{lang}/"


def hreflang_block(indent="  "):
    lines = [f'{indent}<link rel="alternate" hreflang="{tag(l)}" href="{url_of(l)}">' for l in LANGS]
    lines.append(f'{indent}<link rel="alternate" hreflang="x-default" href="{BASE}/">')
    return "\n".join(lines)


def lang_links(current, style):
    """style : menu (nom + code), pill (code), footer (nom)."""
    out = []
    for l in LANGS:
        cur = ' aria-current="true"' if l == current else ""
        name = html.escape(texts[l]["langName"])
        attrs = f'href="/{l}/" hreflang="{tag(l)}" lang="{tag(l)}"{cur}'
        if style == "menu":
            out.append(f'            <a {attrs}>{name}<span>{l}</span></a>')
        elif style == "pill":
            out.append(f'      <a {attrs} title="{name}">{l}</a>')
        else:
            out.append(f'            <a {attrs}>{name}</a>')
    return "\n".join(out)


def jsonld(lang):
    t = texts[lang]
    data = {
        "@context": "https://schema.org",
        "@type": "TouristTrip",
        "name": t["jsonldName"],
        "description": t["jsonldDescription"],
        "inLanguage": tag(lang),
        "url": url_of(lang),
        "image": f"{BASE}/img/og.jpg",
        "provider": {"@type": "Organization", "name": "Gruyères Tours", "url": f"{BASE}/", "email": "info@gruyeres-tours.com"},
    }
    body = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return "\n".join("  " + line for line in body.splitlines())


def render(lang):
    t = texts[lang]
    values = {k: html.escape(v, quote=True) for k, v in t.items()}
    values.update({
        "lang": lang,
        "htmlLang": tag(lang),
        "langCode": lang.upper(),
        "fontPreload": FONT_PRELOAD,
        "url": url_of(lang),
        "base": BASE,
        "path": f"/{lang}/",
        "version": version,
        "hreflang": hreflang_block(),
        "ogAlternates": "\n".join(
            f'  <meta property="og:locale:alternate" content="{texts[o]["ogLocale"]}">' for o in LANGS if o != lang
        ),
        "langMenu": lang_links(lang, "menu"),
        "langPills": lang_links(lang, "pill"),
        "footerLangLinks": lang_links(lang, "footer"),
        "creditsList": credits_list(lang),
        "jsonld": jsonld(lang),
    })

    def sub(m):
        key = m.group(1)
        if key not in values:
            errors.append(f"{lang}: case vide {{{{{key}}}}}")
            return m.group(0)
        return values[key]

    page = re.sub(r"\{\{(\w+)\}\}", sub, template)

    def img_sub(m):
        name, sizes, alt_key, mode = m.groups()
        if not (root / "img" / f"{name}-800.webp").exists():
            errors.append(f"{lang}: photo manquante {name}")
        if alt_key not in t:
            errors.append(f"{lang}: texte alternatif manquant {alt_key}")
        return img_tag(name, sizes, t.get(alt_key, ""), mode)

    return IMG_RE.sub(img_sub, page)


def root_page():
    names = "\n".join(
        f'        <li><a href="/{l}/" hreflang="{tag(l)}" lang="{tag(l)}">{html.escape(texts[l]["langName"])}</a></li>' for l in LANGS
    )
    choose = " · ".join(html.escape(texts[l]["chooseLanguage"]) for l in LANGS)
    desc = html.escape(texts["fr"]["metaDescription"] + " " + texts["en"]["metaDescription"])
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gruyères Tours | Genève · Gruyères</title>
  <meta name="description" content="{desc}">
  <meta name="theme-color" content="#173f35">
  <link rel="canonical" href="{BASE}/">
{hreflang_block()}
  <meta property="og:type" content="website">
  <meta property="og:title" content="Gruyères Tours">
  <meta property="og:image" content="{BASE}/img/og.jpg">
  <meta property="og:url" content="{BASE}/">
  <link rel="icon" type="image/svg+xml" href="/logo.svg">
  <link rel="stylesheet" href="/style.css?v={version}">
  <script>
    (function () {{
      var langs = {json.dumps(LANGS)};
      var pick = null;
      try {{ pick = localStorage.getItem("gt-lang"); }} catch (e) {{}}
      if (langs.indexOf(pick) < 0) {{
        pick = null;
        var prefs = navigator.languages || [navigator.language || ""];
        for (var i = 0; i < prefs.length && !pick; i++) {{
          var code = String(prefs[i]).slice(0, 2).toLowerCase();
          if (langs.indexOf(code) >= 0) pick = code;
        }}
      }}
      if (pick) location.replace("/" + pick + "/");
    }})();
  </script>
</head>
<body>
  <main class="lang-chooser">
    <div>
      <span class="brand"><svg class="brand-mark" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.3" aria-hidden="true"><circle cx="16" cy="16" r="15"/><path d="M5 22.5 12 13l4 5 3.5-4.5L27 22.5"/><path d="M10.6 15 12 13l1.4 1.8" stroke-width="1"/></svg>Gruyères Tours</span>
      <p class="lead">{choose}</p>
      <ul class="lang-list">
{names}
      </ul>
    </div>
  </main>
</body>
</html>
"""


def sitemap():
    alts = "\n".join(f'    <xhtml:link rel="alternate" hreflang="{tag(l)}" href="{url_of(l)}"/>' for l in LANGS)
    alts += f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{BASE}/"/>'
    entries = []
    for loc in [f"{BASE}/"] + [url_of(l) for l in LANGS]:
        entries.append(f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{today}</lastmod>\n{alts}\n  </url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + "\n".join(entries) + "\n</urlset>\n")


make_og()
pages = {f"{l}/index.html": render(l) for l in LANGS}
pages["index.html"] = root_page()
pages["sitemap.xml"] = sitemap()

# 2. Aucun tiret long dans ce que lit un visiteur
for name, content in pages.items():
    for ch in ("—", "–"):
        if ch in content:
            errors.append(f"{name}: tiret long trouvé")

if errors:
    print("ERREURS :")
    for e in errors:
        print(" -", e)
    sys.exit(1)

for name, content in pages.items():
    out = root / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8", newline="\n")
    print(f"ok {name} ({len(content.encode('utf-8'))} octets)")
