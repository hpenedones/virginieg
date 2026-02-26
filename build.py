#!/usr/bin/env python3
"""
Static site generator for virginieg.com
Usage: python build.py
Output: _site/
"""

import os, re, shutil
from pathlib import Path
import markdown as md_lib
from jinja2 import Environment, FileSystemLoader

ROOT    = Path(__file__).parent
SITE    = ROOT / "_site"
TMPL    = ROOT / "templates"

env = Environment(loader=FileSystemLoader(str(TMPL)), autoescape=False)


# ── Helpers ────────────────────────────────────────────────────────────────

def render(template_name, output_path, **ctx):
    tmpl = env.get_template(template_name)
    html = tmpl.render(**ctx)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def to_html(text):
    return md_lib.markdown(text, extensions=["tables", "nl2br", "attr_list"])


def fix_image_paths(html, base):
    """Rewrite relative image src paths to be relative to the page's depth."""
    html = re.sub(r'src="\.\./images/', f'src="{base}images/', html)
    html = re.sub(r'src="images/', f'src="{base}images/', html)
    return html


# ── Parsers ────────────────────────────────────────────────────────────────

def parse_book(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")

    # Title: "# Main title" (may include subtitle after comma)
    title_m = re.search(r'^# (.+)$', raw, re.M)
    full_title = title_m.group(1) if title_m else path.stem
    # Split into main title and subtitle at the comma
    if ',' in full_title:
        main_title, subtitle = full_title.split(',', 1)
        subtitle = subtitle.strip()
    else:
        main_title = full_title
        subtitle_m = re.search(r'^\*([^*]+)\*$', raw, re.M)
        subtitle = subtitle_m.group(1) if subtitle_m else ""

    # Cover image
    cover_m = re.search(r'!\[Couverture\]\(\.\.\/images\/([^)]+)\)', raw)
    cover = f"images/{cover_m.group(1)}" if cover_m else None

    # Interior / gallery images
    gallery = [f"images/{m}" for m in
               re.findall(r'!\[Intérieur\]\(\.\.\/images\/([^)]+)\)', raw)]

    # Price from table
    price_m = re.search(r'\| Prix[^|]*\|\s*(€[\d.,]+)', raw)
    price = price_m.group(1) if price_m else ""

    # Résumé section
    res_m = re.search(r'## Résumé\n\n([\s\S]+?)(?:\n\n##|\Z)', raw)
    resume = res_m.group(1).strip() if res_m else ""

    # Full HTML stored separately; caller must pass base for image paths
    return dict(
        slug=path.stem,
        title=full_title,
        main_title=main_title.strip(),
        subtitle=subtitle,
        cover=cover,
        gallery=gallery,
        price=price,
        resume=resume,
        raw=raw,
    )


def parse_post(path: Path) -> dict:
    filename = path.stem                          # e.g. "0071-cruelle-maree"
    parts = filename.split("-", 1)
    order = int(parts[0]) if parts[0].isdigit() else 0
    slug  = parts[1] if len(parts) > 1 else filename

    raw = path.read_text(encoding="utf-8")

    title_m = re.search(r'^# (.+)$', raw, re.M)
    title = title_m.group(1) if title_m else slug

    img_m = re.search(r'!\[Header image\]\(\.\.\/images\/([^)]+)\)', raw)
    header_image = f"images/{img_m.group(1)}" if img_m else None

    # Short excerpt for the listing (first non-empty text after ## Contenu)
    contenu_m = re.search(r'## Contenu\n\n([\s\S]{0,300})', raw)
    if contenu_m:
        raw_exc = re.sub(r'[*_`#\[\]!]', '', contenu_m.group(1))
        raw_exc = re.sub(r'\(\.\.\/images\/[^)]+\)', '', raw_exc)
        excerpt = ' '.join(raw_exc.split())[:180]
        if len(contenu_m.group(1)) > 180:
            excerpt += "…"
    else:
        excerpt = ""

    html = to_html(raw)

    return dict(
        slug=slug, order=order, title=title,
        header_image=header_image, excerpt=excerpt, raw=raw, html=html,
    )


# ── Build ──────────────────────────────────────────────────────────────────

def build():
    # Clean output
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()

    # Static assets
    shutil.copytree(ROOT / "images", SITE / "images")
    shutil.copytree(ROOT / "assets", SITE / "assets")

    # ── Homepage ──
    hp_raw = (ROOT / "homepage.md").read_text(encoding="utf-8")
    hp_html = fix_image_paths(to_html(hp_raw), "")
    # Wrap the three intro images in a flex circle gallery
    hp_html = re.sub(
        r'<p>(\s*<img[^>]*/>\s*(?:<br\s*/>\s*<img[^>]*/>\s*)*)</p>',
        r'<div class="home-photos">\1</div>',
        hp_html
    )
    render("home.html", SITE / "index.html", content=hp_html, current_page="home", base="")

    # ── Books ──
    books = [parse_book(p) for p in sorted((ROOT / "books").glob("*.md"))]
    render("books_list.html", SITE / "livres" / "index.html",
           books=books, current_page="livres", base="../")
    for book in books:
        book_html = fix_image_paths(to_html(book["raw"]), "../../")
        render("book.html", SITE / "livres" / book["slug"] / "index.html",
               book={**book, "html": book_html}, current_page="livres", base="../../")

    # ── Blog posts ── (newest first in listing)
    posts = [parse_post(p) for p in sorted((ROOT / "blog").glob("*.md"), reverse=True)]
    render("posts_list.html", SITE / "textes" / "index.html",
           posts=posts, current_page="textes", base="../")
    for post in posts:
        post_html = fix_image_paths(post["html"], "../../")
        render("post.html", SITE / "textes" / post["slug"] / "index.html",
               post={**post, "html": post_html}, current_page="textes", base="../../")

    print(f"✅  {len(books)} livres · {len(posts)} textes")
    print(f"    → {SITE}")


if __name__ == "__main__":
    build()
