# Gruyères Tours

Site vitrine de Gruyères Tours : excursion privée de Genève à Gruyères, en 6 langues (fr, de, en, pt, es, zh).

## Modifier le site

1. Textes : `src/i18n/<langue>.json`. Structure : `src/template.html`. Style : `style.css`.
2. Fabriquer les pages : `python src/build.py` (écrit `<langue>/index.html`, `index.html` et `sitemap.xml`).
3. Enregistrer et pousser sur `main` : GitHub Pages publie tout seul sur https://gruyeres-tours.com.

Crédits photo : voir `IMAGE-CREDITS.md`. Polices : Cormorant Garamond et Inter, licence SIL OFL.
