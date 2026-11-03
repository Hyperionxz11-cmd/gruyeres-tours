"""Fabrique tout le site statique à partir des sources.

Usage : python src/build.py
Sources : src/template.html (accueil), src/i18n/<langue>.json (libellés), src/content/<langue>.json (lieux et FAQ),
          src/gallery.json (galeries), src/credits.json (crédits photo)
Sorties : <langue>/index.html, <langue>/lieux/<lieu>/index.html, <langue>/faq/index.html, <langue>/merci/index.html,
          index.html, sitemap.xml, robots.txt, llms.txt, site.webmanifest
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
TAG = {"zh": "zh-Hans"}  # code complet pour Google ; le chemin reste /zh/
FORM_ENDPOINT = "info@gruyeres-tours.com"
EMAIL = "info@gruyeres-tours.com"
SLUGS = ["chateau-de-gruyeres", "maison-du-gruyere", "maison-cailler", "musee-hr-giger", "moleson"]
STOP_KEY = {s: f"s{i}t" for i, s in enumerate(SLUGS, 1)}
HERO_OF = {"chateau-de-gruyeres": "cite", "maison-du-gruyere": "fromage", "maison-cailler": "cailler",
           "musee-hr-giger": "saint-germain", "moleson": "moleson"}
ALT_OF = {s: f"alt{i}" for i, s in enumerate(SLUGS, 1)}
GUIDES = ["excursion-depuis-geneve", "en-famille", "fromage-et-chocolat", "quand-visiter", "sortie-entreprise"]
GUIDE_IMG = {"excursion-depuis-geneve": "chateau-de-gruyeres-1", "en-famille": "maison-du-gruyere-5",
             "fromage-et-chocolat": "maison-du-gruyere-1", "quand-visiter": "moleson-5", "sortie-entreprise": "chateau-de-gruyeres-5"}
LOCALITY = {"chateau-de-gruyeres": "Gruyères", "maison-du-gruyere": "Pringy", "maison-cailler": "Broc",
            "musee-hr-giger": "Gruyères", "moleson": "Moléson-sur-Gruyères"}
FONT_PRELOAD = (
    '  <link rel="preload" href="/fonts/ebgaramond-400.woff2" as="font" type="font/woff2" crossorigin>\n'
    '  <link rel="preload" href="/fonts/inter-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>'
)
ICONS = (
    '  <link rel="icon" href="/favicon.ico" sizes="48x48">\n'
    '  <link rel="icon" type="image/svg+xml" href="/logo.svg">\n'
    '  <link rel="icon" type="image/png" sizes="192x192" href="/img/icon-192.png">\n'
    '  <link rel="apple-touch-icon" href="/apple-touch-icon.png">\n'
    '  <link rel="manifest" href="/site.webmanifest">'
)
WIDTHS = (800, 1400, 2400)
ARROW = '<svg viewBox="0 0 22 10" fill="none" stroke="currentColor" stroke-width="1.2" aria-hidden="true"><path d="M0 5h21M17 1l4 4-4 4"/></svg>'

src = Path(__file__).resolve().parent
root = src.parent
template = (src / "template.html").read_text(encoding="utf-8")
texts = {l: json.loads((src / "i18n" / f"{l}.json").read_text(encoding="utf-8")) for l in LANGS}
content = {}
for l in LANGS:
    f = src / "content" / f"{l}.json"
    if f.exists():
        content[l] = json.loads(f.read_text(encoding="utf-8"))
gallery = json.loads((src / "gallery.json").read_text(encoding="utf-8")) if (src / "gallery.json").exists() else {}
credits = json.loads((src / "credits.json").read_text(encoding="utf-8"))
version = hashlib.sha1((root / "style.css").read_bytes() + (root / "site.js").read_bytes()).hexdigest()[:8]
today = date.today().isoformat()
errors = []

# légende utilisée dans les crédits pour chaque photo de l'accueil
CAPTION = {"chateau": "capChateau", "dents": "capDents", "panorama": "capPanorama", "alpage": "capAlpage",
           "cite": "s1t", "fromage": "alt2", "cailler": "s3t", "saint-germain": "s4t", "moleson": "s5t",
           "village": "capVillage", "lac": "capLac", "cloches": "capCloches", "jogne": "capJogne"}
IMG_RE = re.compile(r'\[\[img (\S+) "([^"]+)" (\w+) (eager|lazy|defer)\]\]')

# Toutes les langues doivent avoir les mêmes libellés
ref_keys = set(texts[DEFAULT])
for l in LANGS:
    missing, extra = ref_keys - set(texts[l]), set(texts[l]) - ref_keys
    if missing or extra:
        errors.append(f"{l}: libellés manquants {sorted(missing)} en trop {sorted(extra)}")


def tag(lang):
    return TAG.get(lang, lang)


def esc(s):
    return html.escape(str(s), quote=True)


def has_places(lang):
    return lang in content and all(s in content[lang].get("places", {}) for s in SLUGS)


def guides_of(lang):
    p = src / "guides" / f"{lang}.json"
    if not p.exists():
        return None
    g = json.loads(p.read_text(encoding="utf-8"))
    return g if all(s in g.get("guides", {}) for s in GUIDES) else None


def has_guides(lang):
    return guides_of(lang) is not None


def has_faq(lang):
    return lang in content and bool(content[lang].get("faq"))


def img_tag(name, sizes, alt, mode="lazy", cls=""):
    srcset = ", ".join(f"/img/{name}-{w}.webp {w}w" for w in WIDTHS)
    fallback = f"/img/{name}-1400.webp"
    c = f' class="{cls}"' if cls else ""
    if not (root / "img" / f"{name}-800.webp").exists():
        errors.append(f"photo manquante {name}")
    if mode == "eager":
        return f'<img{c} src="{fallback}" srcset="{srcset}" sizes="{sizes}" alt="{esc(alt)}" fetchpriority="high" decoding="async">'
    if mode == "defer":
        return f'<img{c} data-src="{fallback}" data-srcset="{srcset}" sizes="{sizes}" alt="{esc(alt)}" decoding="async">'
    return f'<img{c} src="{fallback}" srcset="{srcset}" sizes="{sizes}" alt="{esc(alt)}" loading="lazy" decoding="async">'


def gallery_items(slug, lang):
    """Photos de la galerie d'un lieu, avec leur légende dans la langue (repli en français)."""
    items = gallery.get(slug, [])
    caps = content.get(lang, {}).get("captions", {}).get(slug, [])
    out = []
    for i, g in enumerate(items):
        name = f"{slug}-{i + 1}"
        if not (root / "img" / f"{name}-800.webp").exists():
            continue
        cap = caps[i] if i < len(caps) and caps[i] else g.get("caption_fr", "")
        out.append({"name": name, "caption": cap, "credit": g})
    return out


# ---------- morceaux communs ----------

def hreflang_block(urls):
    lines = [f'  <link rel="alternate" hreflang="{tag(l)}" href="{u}">' for l, u in urls.items()]
    if "fr" in urls:
        x = f"{BASE}/" if urls["fr"] == f"{BASE}/fr/" else urls["fr"]
        lines.append(f'  <link rel="alternate" hreflang="x-default" href="{x}">')
    return "\n".join(lines)


def lang_links(current, style, urls=None):
    out = []
    for l in LANGS:
        href = (urls or {}).get(l, f"/{l}/").replace(BASE, "")
        cur = ' aria-current="true"' if l == current else ""
        name = esc(texts[l]["langName"])
        attrs = f'href="{href}" hreflang="{tag(l)}" lang="{tag(l)}"{cur}'
        if style == "menu":
            out.append(f'            <a {attrs}>{name}<span>{l}</span></a>')
        elif style == "pill":
            out.append(f'      <a {attrs} title="{name}">{l}</a>')
        else:
            out.append(f'            <a {attrs}>{name}</a>')
    return "\n".join(out)


def lang_options(lang):
    rows = []
    for l in LANGS:
        sel = " selected" if l == lang else ""
        rows.append(f'              <option value="{esc(texts[l]["langName"])}"{sel}>{esc(texts[l]["langName"])}</option>')
    return "\n".join(rows)


def footer_places(lang):
    t = texts[lang]
    rows = [f'            <a href="/{lang}/lieux/{s}/">{esc(t[STOP_KEY[s]])}</a>' for s in SLUGS if has_places(lang)]
    if has_faq(lang):
        rows.append(f'            <a href="/{lang}/faq/">{esc(t["navFaq"])}</a>')
    return "\n".join(rows)


def guides_path(lang):
    return f"/{lang}/guides/" if has_guides(lang) else f"/{DEFAULT}/guides/"


def footer_guides(lang):
    l = lang if has_guides(lang) else DEFAULT
    g = guides_of(l)
    if not g:
        return ""
    return "\n".join(f'            <a href="/{l}/guides/{s}/">{esc(g["guides"][s]["h1"])}</a>' for s in GUIDES)


def credits_list(lang):
    t = texts[lang]
    rows = []

    def row(cap, c):
        lic = (f'<a href="{esc(c["licenseUrl"])}" rel="license noopener">{esc(c["license"])}</a>'
               if c.get("licenseUrl") else esc(c.get("license", "")))
        return (f'          <li>{esc(cap)} : {esc(t["creditsBy"])} {esc(c.get("artist", ""))}, {lic}, '
                f'<a href="{esc(c["source"])}" rel="noopener">Wikimedia Commons</a></li>')

    for name, c in credits.items():
        rows.append(row(t.get(CAPTION.get(name, ""), name), c))
    for slug in SLUGS:
        for g in gallery_items(slug, lang):
            c = g["credit"]
            rows.append(row(g["caption"], {"license": c.get("license", ""), "licenseUrl": c.get("licenseUrl", ""),
                                           "artist": c.get("artist", ""), "source": c.get("source", "")}))
    return "\n".join(rows)


def ld(obj):
    body = json.dumps(obj, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return '  <script type="application/ld+json">\n' + "\n".join("  " + line for line in body.splitlines()) + "\n  </script>"


ORG = {"@type": "TravelAgency", "@id": f"{BASE}/#organisation", "name": "Gruyères Tours", "url": f"{BASE}/",
       "logo": {"@type": "ImageObject", "url": f"{BASE}/img/logo-512.png", "width": 512, "height": 512},
       "image": f"{BASE}/img/og.jpg", "email": EMAIL,
       "areaServed": [{"@type": "City", "name": "Genève"}, {"@type": "AdministrativeArea", "name": "Gruyère, canton de Fribourg"}],
       "knowsLanguage": [tag(l) for l in LANGS]}


def page_urls(kind, slug=None):
    """Adresse de la même page dans chaque langue disponible."""
    urls = {}
    for l in LANGS:
        if kind == "home":
            urls[l] = f"{BASE}/{l}/"
        elif kind == "place" and has_places(l):
            urls[l] = f"{BASE}/{l}/lieux/{slug}/"
        elif kind == "faq" and has_faq(l):
            urls[l] = f"{BASE}/{l}/faq/"
        elif kind == "guides" and has_guides(l):
            urls[l] = f"{BASE}/{l}/guides/"
        elif kind == "guide" and has_guides(l):
            urls[l] = f"{BASE}/{l}/guides/{slug}/"
    return urls


# ---------- accueil ----------

head_part, _, rest = template.partition("<body>")
HEADER = rest.split('  <main id="main">')[0]
FOOTER = "  </main>" + rest.split("  </main>", 1)[1]


def base_values(lang, urls):
    t = texts[lang]
    v = {k: esc(x) for k, x in t.items()}
    v.update({
        "lang": lang, "htmlLang": tag(lang), "langCode": lang.upper(), "fontPreload": FONT_PRELOAD, "icons": ICONS,
        "base": BASE, "path": f"/{lang}/", "version": version, "url": f"{BASE}/{lang}/",
        "hreflang": hreflang_block(urls),
        "ogAlternates": "\n".join(f'  <meta property="og:locale:alternate" content="{texts[o]["ogLocale"]}">' for o in urls if o != lang),
        "langMenu": lang_links(lang, "menu", urls), "langPills": lang_links(lang, "pill", urls),
        "footerLangLinks": lang_links(lang, "footer", urls), "creditsList": credits_list(lang),
        "footerPlaces": footer_places(lang), "footerGuides": footer_guides(lang), "guidesPath": guides_path(lang), "langOptions": lang_options(lang), "formEndpoint": FORM_ENDPOINT,
    })
    return v


def fill(text, values, lang):
    def sub(m):
        key = m.group(1)
        if key not in values:
            errors.append(f"{lang}: case vide {{{{{key}}}}}")
            return m.group(0)
        return values[key]

    text = re.sub(r"\{\{(\w+)\}\}", sub, text)

    def img_sub(m):
        name, sizes, alt_key, mode = m.groups()
        if alt_key not in texts[lang]:
            errors.append(f"{lang}: texte alternatif manquant {alt_key}")
        return img_tag(name, sizes, texts[lang].get(alt_key, ""), mode)

    return IMG_RE.sub(img_sub, text)


def home_jsonld(lang):
    t = texts[lang]
    items = []
    for i, s in enumerate(SLUGS, 1):
        a = {"@type": "TouristAttraction", "name": t[STOP_KEY[s]],
             "address": {"@type": "PostalAddress", "addressLocality": LOCALITY[s], "addressRegion": "FR", "addressCountry": "CH"}}
        if has_places(lang):
            a["url"] = f"{BASE}/{lang}/lieux/{s}/"
        items.append({"@type": "ListItem", "position": i, "item": a})
    graph = {"@context": "https://schema.org", "@graph": [
        ORG,
        {"@type": "WebSite", "@id": f"{BASE}/#site", "name": "Gruyères Tours", "url": f"{BASE}/", "inLanguage": [tag(l) for l in LANGS],
         "publisher": {"@id": f"{BASE}/#organisation"}},
        {"@type": "TouristTrip", "name": t["jsonldName"], "description": t["jsonldDescription"], "inLanguage": tag(lang),
         "url": f"{BASE}/{lang}/", "image": f"{BASE}/img/og.jpg", "touristType": ["Groupes privés", "Familles"],
         "provider": {"@id": f"{BASE}/#organisation"},
         "itinerary": {"@type": "ItemList", "numberOfItems": len(SLUGS), "itemListElement": items}},
    ]}
    return ld(graph)


def render_home(lang):
    urls = page_urls("home")
    v = base_values(lang, urls)
    v["jsonld"] = home_jsonld(lang)
    return fill(template, v, lang)


# ---------- pages intérieures ----------

def head(lang, title, desc, url, urls, image, jsonlds, robots="index, follow, max-image-preview:large"):
    t = texts[lang]
    alts = "\n".join(f'  <meta property="og:locale:alternate" content="{texts[o]["ogLocale"]}">' for o in urls if o != lang)
    return f"""<!DOCTYPE html>
<html lang="{tag(lang)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">
  <meta name="theme-color" content="#0e2820">
  <meta name="color-scheme" content="light">
  <meta name="robots" content="{robots}">
  <link rel="canonical" href="{url}">
{hreflang_block(urls) if urls else ""}
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Gruyères Tours">
  <meta property="og:locale" content="{t['ogLocale']}">
{alts}
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:image" content="{image}">
  <meta property="og:url" content="{url}">
  <meta name="twitter:card" content="summary_large_image">
{FONT_PRELOAD}
{ICONS}
  <link rel="stylesheet" href="/style.css?v={version}">
  <script>document.documentElement.classList.add("js")</script>
{chr(10).join(jsonlds)}
</head>
<body>"""


def shell(lang, urls, title, desc, url, image, jsonlds, main, robots="index, follow, max-image-preview:large"):
    v = base_values(lang, urls)
    return head(lang, title, desc, url, urls, image, jsonlds, robots) + fill(HEADER, v, lang) + main + fill(FOOTER, v, lang)


def breadcrumb(lang, trail):
    """trail : liste (nom, url) ; dernier élément = page courante."""
    items = [{"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(trail, 1)]
    links = []
    for i, (n, u) in enumerate(trail):
        if i < len(trail) - 1:
            links.append(f'<a href="{u.replace(BASE, "")}">{esc(n)}</a>')
        else:
            links.append(f'<span aria-current="page">{esc(n)}</span>')
    nav = f'<nav class="crumbs" aria-label="breadcrumb">{" <i>/</i> ".join(links)}</nav>'
    return nav, ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items})


def cta_button(lang, href):
    t = texts[lang]
    return (f'<a class="btn" href="{href}"><span class="roll"><b>{esc(t["discover"])}</b><b aria-hidden="true">{esc(t["discover"])}</b></span>'
            f'<span class="pave" aria-hidden="true"></span><svg class="fleche" viewBox="0 0 22 10" fill="none" stroke="currentColor" stroke-width="1.3" aria-hidden="true"><path d="M0 5h21M17 1l4 4-4 4"/></svg></a>')


def render_place(lang, slug):
    t, c = texts[lang], content[lang]["places"][slug]
    urls = page_urls("place", slug)
    url = urls[lang]
    items = gallery_items(slug, lang)
    hero = HERO_OF[slug]
    images = [f"{BASE}/img/{hero}-1400.webp"] + [f"{BASE}/img/{g['name']}-1400.webp" for g in items]
    crumbs_nav, crumbs_ld = breadcrumb(lang, [(t["crumbHome"], f"{BASE}/{lang}/"), (t["crumbPlaces"], f"{BASE}/{lang}/#stops"), (c["h1"], url)])
    attraction = {"@context": "https://schema.org", "@type": "TouristAttraction", "name": c["h1"], "description": c["description"],
                  "url": url, "image": images, "inLanguage": tag(lang),
                  "address": {"@type": "PostalAddress", "addressLocality": LOCALITY[slug], "addressRegion": "FR", "addressCountry": "CH"},
                  "isPartOf": {"@type": "TouristTrip", "name": t["jsonldName"], "url": f"{BASE}/{lang}/", "provider": {"@id": f"{BASE}/#organisation"}}}
    sections = "\n".join(f'          <section><h2>{esc(s["h2"])}</h2><p>{esc(s["text"])}</p></section>' for s in c["sections"])
    facts = "\n".join(f'            <div><dt>{esc(f["label"])}</dt><dd>{esc(f["value"])}</dd></div>' for f in c.get("facts", []))
    gal = "\n".join(
        f'          <figure class="g-item{" g-wide" if i % 5 == 0 else ""}"><a href="/img/{g["name"]}-2400.webp" data-lightbox="{esc(g["caption"])}">'
        f'{img_tag(g["name"], "(max-width: 900px) 100vw, 50vw", g["caption"])}</a><figcaption>{esc(g["caption"])}</figcaption></figure>'
        for i, g in enumerate(items))
    others = "\n".join(
        f'          <a class="other" href="/{lang}/lieux/{s}/">{img_tag(HERO_OF[s], "(max-width: 900px) 100vw, 25vw", t[ALT_OF[s]])}'
        f'<span>{esc(t[STOP_KEY[s]])} {ARROW}</span></a>' for s in SLUGS if s != slug)
    sources = "".join(f'<li><a href="{esc(u)}" rel="noopener">{esc(re.sub(r"^https?://(www\\.)?", "", u).split("/")[0])}</a></li>' for u in c.get("sources", []))
    main = f"""  <main id="main">
    <section class="scene place-hero">
      <div class="scene-bg" aria-hidden="true">{img_tag(hero, "100vw", t[ALT_OF[slug]], "eager")}</div>
      <div class="scene-body">
        <div class="container">
          {crumbs_nav}
          <p class="eyebrow" data-rise>{esc(t["crumbPlaces"])}</p>
          <h1 data-rise style="--d:.1s">{esc(c["h1"])}</h1>
          <p class="lead" data-rise style="--d:.2s">{esc(c["intro"])}</p>
          <div class="hero-actions" data-rise style="--d:.3s">{cta_button(lang, f"/{lang}/#organiser")}</div>
        </div>
      </div>
    </section>

    <section class="scene">
      <div class="scene-bg" aria-hidden="true">{img_tag("panorama", "100vw", t["capPanorama"])}</div>
      <div class="scene-body">
        <div class="container place-grid">
          <article class="glass place-text" data-reveal>
{sections}
          </article>
          <aside class="place-side">
            <div class="glass" data-reveal style="--d:.1s">
              <p class="eyebrow">{esc(t["factsTitle"])}</p>
              <dl class="facts">
{facts}
              </dl>
            </div>
            <div class="glass" data-reveal style="--d:.2s">
              <p class="eyebrow">{esc(t["inTourTitle"])}</p>
              <p class="lead">{esc(c["inTour"])}</p>
              {cta_button(lang, f"/{lang}/#organiser")}
            </div>
          </aside>
        </div>
      </div>
    </section>
""" + (f"""
    <section class="scene">
      <div class="scene-bg" aria-hidden="true">{img_tag("dents", "100vw", t["capDents"])}</div>
      <div class="scene-body">
        <div class="container">
          <div class="glass section-title" data-reveal><p class="eyebrow">{esc(t["galleryTitle"])}</p><h2>{esc(c["h1"])}</h2></div>
          <div class="gallery">
{gal}
          </div>
        </div>
      </div>
    </section>
""" if items else "") + f"""
    <section class="scene">
      <div class="scene-bg" aria-hidden="true">{img_tag("lac", "100vw", t["capLac"])}</div>
      <div class="scene-body">
        <div class="container">
          <div class="glass section-title" data-reveal><p class="eyebrow">{esc(t["crumbPlaces"])}</p><h2>{esc(t["otherPlaces"])}</h2></div>
          <div class="others">
{others}
          </div>
          <p class="sources"><span>{esc(t["sourcesTitle"])} :</span> <ul>{sources}</ul></p>
        </div>
      </div>
    </section>
"""
    return shell(lang, urls, c["title"], c["description"], url, f"{BASE}/img/{hero}-1400.webp", [ld(attraction), crumbs_ld], main)


def render_faq(lang):
    t, faq = texts[lang], content[lang]["faq"]
    urls = page_urls("faq")
    url = urls[lang]
    crumbs_nav, crumbs_ld = breadcrumb(lang, [(t["crumbHome"], f"{BASE}/{lang}/"), (t["navFaq"], url)])
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": tag(lang),
              "mainEntity": [{"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}} for q in faq]}
    rows = "\n".join(f'          <details class="qa glass"{" open" if i == 0 else ""}><summary><h2>{esc(q["q"])}</h2><i aria-hidden="true"></i></summary><p>{esc(q["a"])}</p></details>'
                     for i, q in enumerate(faq))
    main = f"""  <main id="main">
    <section class="scene">
      <div class="scene-bg" aria-hidden="true">{img_tag("village", "100vw", t["capVillage"], "eager")}</div>
      <div class="scene-body">
        <div class="container faq-wrap">
          {crumbs_nav}
          <div class="glass section-title" data-rise><p class="eyebrow">{esc(t["faqEyebrow"])}</p><h1>{esc(t["faqTitle"])}</h1></div>
          <div class="faq-list">
{rows}
          </div>
          <div class="hero-actions">{cta_button(lang, f"/{lang}/#organiser")}</div>
        </div>
      </div>
    </section>
"""
    title = f'{t["faqEyebrow"]} | Gruyères Tours'
    return shell(lang, urls, title, t["faqMeta"], url, f"{BASE}/img/og.jpg", [ld(faq_ld), crumbs_ld], main)


def guide_card(lang, slug, g):
    t = texts[lang]
    return (f'          <a class="other guide-card" href="/{lang}/guides/{slug}/">{img_tag(GUIDE_IMG[slug], "(max-width: 900px) 100vw, 33vw", g["h1"])}'
            f'<span>{esc(g["h1"])} {ARROW}</span></a>')


def render_guide(lang, slug):
    t, gall = texts[lang], guides_of(lang)
    g = gall["guides"][slug]
    urls = page_urls("guide", slug)
    url = urls[lang]
    hub = f"{BASE}/{lang}/guides/"
    crumbs_nav, crumbs_ld = breadcrumb(lang, [(t["crumbHome"], f"{BASE}/{lang}/"), (t["navGuides"], hub), (g["h1"], url)])
    image = f"{BASE}/img/{GUIDE_IMG[slug]}-1400.webp"
    article = {"@context": "https://schema.org", "@type": "Article", "headline": g["h1"], "description": g["description"],
               "inLanguage": tag(lang), "url": url, "image": image, "datePublished": today, "dateModified": today,
               "author": {"@id": f"{BASE}/#organisation"}, "publisher": {"@id": f"{BASE}/#organisation"},
               "mainEntityOfPage": url, "about": [{"@type": "TouristAttraction", "name": t[STOP_KEY[s]]} for s in g.get("places", []) if s in STOP_KEY]}
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": tag(lang),
              "mainEntity": [{"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}} for q in g["faq"]]}
    sections = "\n".join(f'          <section><h2>{esc(s["h2"])}</h2>' + "".join(f"<p>{esc(p)}</p>" for p in s["p"]) + "</section>" for s in g["sections"])
    tips = "\n".join(f"                <li>{esc(x)}</li>" for x in g["tips"])
    place_links = "\n".join(f'              <a class="more" href="/{lang}/lieux/{s}/">{esc(t[STOP_KEY[s]])} {ARROW}</a>'
                            for s in g.get("places", []) if s in STOP_KEY and has_places(lang))
    faq = "\n".join(f'          <details class="qa glass"><summary><h3>{esc(q["q"])}</h3><i aria-hidden="true"></i></summary><p>{esc(q["a"])}</p></details>' for q in g["faq"])
    others = "\n".join(guide_card(lang, s, gall["guides"][s]) for s in GUIDES if s != slug)
    main = f"""  <main id="main">
    <section class="scene place-hero">
      <div class="scene-bg" aria-hidden="true">{img_tag(GUIDE_IMG[slug], "100vw", g["h1"], "eager")}</div>
      <div class="scene-body">
        <div class="container">
          {crumbs_nav}
          <p class="eyebrow" data-rise>{esc(t["guidesEyebrow"])}</p>
          <h1 data-rise style="--d:.1s">{esc(g["h1"])}</h1>
          <p class="lead" data-rise style="--d:.2s">{esc(g["intro"])}</p>
          <div class="hero-actions" data-rise style="--d:.3s">{cta_button(lang, f"/{lang}/#organiser")}</div>
        </div>
      </div>
    </section>

    <section class="scene">
      <div class="scene-bg" aria-hidden="true">{img_tag("panorama", "100vw", t["capPanorama"])}</div>
      <div class="scene-body">
        <div class="container place-grid">
          <article class="glass place-text" data-reveal>
{sections}
          </article>
          <aside class="place-side">
            <div class="glass" data-reveal style="--d:.1s">
              <p class="eyebrow">{esc(t["tipsTitle"])}</p>
              <ul class="tips">
{tips}
              </ul>
            </div>
            <div class="glass" data-reveal style="--d:.2s">
              <p class="eyebrow">{esc(t["crumbPlaces"])}</p>
              <div class="place-links">
{place_links}
              </div>
              {cta_button(lang, f"/{lang}/#organiser")}
            </div>
          </aside>
        </div>
      </div>
    </section>

    <section class="scene">
      <div class="scene-bg" aria-hidden="true">{img_tag("village", "100vw", t["capVillage"])}</div>
      <div class="scene-body">
        <div class="container faq-wrap">
          <div class="glass section-title" data-reveal><p class="eyebrow">{esc(t["guideFaqTitle"])}</p><h2>{esc(g["h1"])}</h2></div>
          <div class="faq-list">
{faq}
          </div>
        </div>
      </div>
    </section>

    <section class="scene">
      <div class="scene-bg" aria-hidden="true">{img_tag("lac", "100vw", t["capLac"])}</div>
      <div class="scene-body">
        <div class="container">
          <div class="glass section-title" data-reveal><p class="eyebrow">{esc(t["guidesEyebrow"])}</p><h2>{esc(t["otherGuides"])}</h2></div>
          <div class="others">
{others}
          </div>
        </div>
      </div>
    </section>
"""
    return shell(lang, urls, g["title"], g["description"], url, image, [ld(article), ld(faq_ld), crumbs_ld], main)


def render_guides(lang):
    t, gall = texts[lang], guides_of(lang)
    urls = page_urls("guides")
    url = urls[lang]
    crumbs_nav, crumbs_ld = breadcrumb(lang, [(t["crumbHome"], f"{BASE}/{lang}/"), (t["navGuides"], url)])
    items = [{"@type": "ListItem", "position": i, "url": f"{BASE}/{lang}/guides/{s}/", "name": gall["guides"][s]["h1"]} for i, s in enumerate(GUIDES, 1)]
    list_ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": gall["hubH1"], "description": gall["hubDescription"],
               "inLanguage": tag(lang), "url": url, "mainEntity": {"@type": "ItemList", "itemListElement": items}}
    cards = "\n".join(
        f'          <a class="glass guide-row" href="/{lang}/guides/{s}/" data-reveal><h2>{esc(gall["guides"][s]["h1"])}</h2>'
        f'<p>{esc(gall["guides"][s]["card"])}</p><span class="more">{esc(t["readGuide"])} {ARROW}</span></a>' for s in GUIDES)
    main = f"""  <main id="main">
    <section class="scene">
      <div class="scene-bg" aria-hidden="true">{img_tag("village", "100vw", t["capVillage"], "eager")}</div>
      <div class="scene-body">
        <div class="container faq-wrap">
          {crumbs_nav}
          <div class="glass section-title" data-rise><p class="eyebrow">{esc(t["guidesEyebrow"])}</p><h1>{esc(gall["hubH1"])}</h1><p class="lead">{esc(gall["hubIntro"])}</p></div>
          <div class="faq-list">
{cards}
          </div>
          <div class="hero-actions">{cta_button(lang, f"/{lang}/#organiser")}</div>
        </div>
      </div>
    </section>
"""
    return shell(lang, urls, gall["hubTitle"], gall["hubDescription"], url, f"{BASE}/img/og.jpg", [ld(list_ld), crumbs_ld], main)


def render_thanks(lang):
    t = texts[lang]
    url = f"{BASE}/{lang}/merci/"
    main = f"""  <main id="main">
    <section class="scene">
      <div class="scene-bg" aria-hidden="true">{img_tag("chateau", "100vw", t["capChateau"], "eager")}</div>
      <div class="scene-body thanks">
        <div class="container">
          <div class="glass" data-rise>
            <p class="eyebrow">Gruyères Tours</p>
            <h1>{esc(t["thanksTitle"])}</h1>
            <p class="lead">{esc(t["fOk"])}</p>
            <p><a class="more" href="/{lang}/">{esc(t["thanksBack"])} {ARROW}</a></p>
          </div>
        </div>
      </div>
    </section>
"""
    return shell(lang, {}, f'{t["thanksTitle"]} | Gruyères Tours', t["fOk"], url, f"{BASE}/img/og.jpg", [], main, robots="noindex, follow")


# ---------- fichiers racine ----------

def root_page():
    names = "\n".join(f'        <li><a href="/{l}/" hreflang="{tag(l)}" lang="{tag(l)}">{esc(texts[l]["langName"])}</a></li>' for l in LANGS)
    choose = " · ".join(esc(texts[l]["chooseLanguage"]) for l in LANGS)
    desc = esc(texts["fr"]["metaDescription"] + " " + texts["en"]["metaDescription"])
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gruyères Tours | Excursion privée Genève · Gruyères</title>
  <meta name="description" content="{desc}">
  <meta name="theme-color" content="#0e2820">
  <link rel="canonical" href="{BASE}/">
{hreflang_block(page_urls("home"))}
  <meta property="og:type" content="website">
  <meta property="og:title" content="Gruyères Tours">
  <meta property="og:image" content="{BASE}/img/og.jpg">
  <meta property="og:url" content="{BASE}/">
{ICONS}
  <link rel="stylesheet" href="/style.css?v={version}">
{ld({"@context": "https://schema.org", "@graph": [ORG, {"@type": "WebSite", "@id": f"{BASE}/#site", "name": "Gruyères Tours", "url": f"{BASE}/", "publisher": {"@id": f"{BASE}/#organisation"}}]})}
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
      <span class="brand"><img class="brand-mark" src="/logo.svg" alt="Gruyères Tours" width="96" height="96"><span class="brand-text"><span class="brand-name">Gruyères Tours</span><span class="brand-tag">Genève · Gruyère</span></span></span>
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
    groups = [page_urls("home")] + [page_urls("place", s) for s in SLUGS] + [page_urls("faq"), page_urls("guides")] + [page_urls("guide", s) for s in GUIDES]
    entries = [f"  <url>\n    <loc>{BASE}/</loc>\n    <lastmod>{today}</lastmod>\n  </url>"]
    for urls in groups:
        if not urls:
            continue
        alts = "\n".join(f'    <xhtml:link rel="alternate" hreflang="{tag(l)}" href="{u}"/>' for l, u in urls.items())
        for l, u in urls.items():
            imgs = ""
            m = re.match(rf"{re.escape(BASE)}/{l}/lieux/([^/]+)/", u)
            if m:
                slug = m.group(1)
                names = [HERO_OF[slug]] + [g["name"] for g in gallery_items(slug, l)]
                imgs = "\n" + "\n".join(f"    <image:image><image:loc>{BASE}/img/{n}-2400.webp</image:loc></image:image>" for n in names)
            elif re.match(rf"{re.escape(BASE)}/{l}/guides/([^/]+)/", u):
                gs = re.match(rf"{re.escape(BASE)}/{l}/guides/([^/]+)/", u).group(1)
                imgs = f"\n    <image:image><image:loc>{BASE}/img/{GUIDE_IMG[gs]}-2400.webp</image:loc></image:image>"
            elif u.endswith(f"/{l}/"):
                imgs = "\n" + "\n".join(f"    <image:image><image:loc>{BASE}/img/{n}-2400.webp</image:loc></image:image>"
                                        for n in ["chateau", "dents", "panorama", "alpage", "lac", "village"])
            entries.append(f"  <url>\n    <loc>{u}</loc>\n    <lastmod>{today}</lastmod>\n{alts}{imgs}\n  </url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml" '
            'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n' + "\n".join(entries) + "\n</urlset>\n")


def robots():
    bots = ["Googlebot", "Bingbot", "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "PerplexityBot",
            "Google-Extended", "Applebot", "Applebot-Extended", "DuckDuckBot"]
    lines = ["# Gruyères Tours : tout le site est ouvert aux moteurs de recherche et aux assistants IA", ""]
    for b in bots:
        lines += [f"User-agent: {b}", "Allow: /", ""]
    lines += ["User-agent: *", "Allow: /", "Disallow: /*/merci/", "", f"Sitemap: {BASE}/sitemap.xml", ""]
    return "\n".join(lines)


def llms():
    fr, en = texts["fr"], texts["en"]
    lines = ["# Gruyères Tours", "",
             f"> {fr['metaDescription']}", f"> {en['metaDescription']}", "",
             "Gruyères Tours organise des excursions privées d'une journée au départ de Genève vers la région de la Gruyère "
             "(canton de Fribourg, Suisse) : château de Gruyères, La Maison du Gruyère, Maison Cailler, musée HR Giger et Moléson. "
             f"Demandes sans engagement via le formulaire « Organiser votre journée » ; contact : {EMAIL}. "
             "Site disponible en français, allemand, anglais, portugais, espagnol et chinois.", ""]
    for l in ["fr", "en", "de", "es", "pt", "zh"]:
        t = texts[l]
        lines.append(f"## {t['langName']}")
        lines.append(f"- [{t['jsonldName']}]({BASE}/{l}/)")
        if has_places(l):
            for s in SLUGS:
                lines.append(f"- [{content[l]['places'][s]['h1']}]({BASE}/{l}/lieux/{s}/): {content[l]['places'][s]['description']}")
        if has_faq(l):
            lines.append(f"- [{t['faqEyebrow']}]({BASE}/{l}/faq/)")
        if has_guides(l):
            for s in GUIDES:
                gg = guides_of(l)["guides"][s]
                lines.append(f"- [{gg['h1']}]({BASE}/{l}/guides/{s}/): {gg['description']}")
        lines.append("")
    return "\n".join(lines)


def manifest():
    return json.dumps({"name": "Gruyères Tours", "short_name": "Gruyères Tours", "start_url": "/", "display": "standalone",
                       "background_color": "#0e2820", "theme_color": "#0e2820",
                       "icons": [{"src": f"/img/icon-{s}.png", "sizes": f"{s}x{s}", "type": "image/png"} for s in (192, 512)]},
                      ensure_ascii=False, indent=2) + "\n"


# ---------- fabrication ----------

def make_og():
    og = root / "img" / "og.jpg"
    if og.exists():
        return
    from PIL import Image
    im = Image.open(root / "img" / "chateau-1400.webp").convert("RGB")
    ratio, (w, h) = 1200 / 630, im.size
    if w / h > ratio:
        nw = int(h * ratio)
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / ratio)
        im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    im.resize((1200, 630), Image.LANCZOS).save(og, "JPEG", quality=84, optimize=True, progressive=True)


make_og()
pages = {}
for l in LANGS:
    pages[f"{l}/index.html"] = render_home(l)
    pages[f"{l}/merci/index.html"] = render_thanks(l)
    if has_places(l):
        for s in SLUGS:
            pages[f"{l}/lieux/{s}/index.html"] = render_place(l, s)
    if has_faq(l):
        pages[f"{l}/faq/index.html"] = render_faq(l)
    if has_guides(l):
        pages[f"{l}/guides/index.html"] = render_guides(l)
        for s in GUIDES:
            pages[f"{l}/guides/{s}/index.html"] = render_guide(l, s)
pages["index.html"] = root_page()
pages["sitemap.xml"] = sitemap()
pages["robots.txt"] = robots()
pages["llms.txt"] = llms()
pages["site.webmanifest"] = manifest()

for name, text in pages.items():
    for ch in ("—", "–"):
        if ch in text:
            errors.append(f"{name}: tiret long trouvé")

if errors:
    print("ERREURS :")
    for e in sorted(set(errors)):
        print(" -", e)
    sys.exit(1)

for name, text in pages.items():
    out = root / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
print(f"ok {len(pages)} fichiers ({sum(1 for n in pages if n.endswith('.html'))} pages)")
