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
from PIL import Image, ImageOps

MOIS_FR = ["janvier","février","mars","avril","mai","juin",
           "juillet","août","septembre","octobre","novembre","décembre"]

def fmt_date_fr(d):
    if d is None:
        return ""
    try:
        import datetime
        if isinstance(d, str):
            d = datetime.date.fromisoformat(d)
        return f"{d.day} {MOIS_FR[d.month - 1]} {d.year}"
    except Exception:
        return str(d)

ROOT    = Path(__file__).parent
SITE    = ROOT / "_site"
TMPL    = ROOT / "templates"

env = Environment(loader=FileSystemLoader(str(TMPL)), autoescape=False)


# ── Helpers ────────────────────────────────────────────────────────────────

def optimise_images(src_dir: Path, dst_dir: Path, max_width=1400, quality=82):
    """Resize and compress images, saving to dst_dir."""
    dst_dir.mkdir(parents=True, exist_ok=True)
    total_in = total_out = 0
    for src in src_dir.iterdir():
        dst = dst_dir / src.name
        if src.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
            shutil.copy2(src, dst)
            continue
        try:
            img = Image.open(src)
            img = ImageOps.exif_transpose(img)  # fix rotation
            if img.width > max_width:
                ratio = max_width / img.width
                img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
            save_kwargs = {"optimize": True}
            if src.suffix.lower() in ('.jpg', '.jpeg'):
                save_kwargs["quality"] = quality
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
            total_in += src.stat().st_size
            img.save(dst, **save_kwargs)
            total_out += dst.stat().st_size
        except Exception as e:
            print(f"  ⚠️  Could not process {src.name}: {e}")
            shutil.copy2(src, dst)
    saved = total_in - total_out
    print(f"    🖼️  Images: {total_in//1024//1024}MB → {total_out//1024//1024}MB (saved {saved//1024//1024}MB)")


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

    # Featured (hero) image from avis-de-lecteurs page
    featured_m = re.search(r'!\[Featured\]\(\.\.\/images\/([^)]+)\)', raw)
    featured = f"images/{featured_m.group(1)}" if featured_m else None

    # Interior / gallery images
    gallery = [f"images/{m}" for m in
               re.findall(r'!\[Intérieur\]\(\.\.\/images\/([^)]+)\)', raw)]

    # Price from table
    price_m = re.search(r'\| Prix[^|]*\|\s*(€[\d.,]+)', raw)
    price = price_m.group(1) if price_m else ""

    # Extract ## Informations, ## Disponibilité, ## Liens (rendered separately at bottom)
    info_m = re.search(r'(## Informations\n[\s\S]+?)(?:\n## |\Z)', raw)
    info_raw = info_m.group(1).strip() if info_m else ""

    dispo_m = re.search(r'(## Disponibilité\n[\s\S]+?)(?:\n## |\Z)', raw)
    dispo_raw = dispo_m.group(1).strip() if dispo_m else ""

    liens_m = re.search(r'(## Liens\n[\s\S]+?)(?:\n## |\Z)', raw)
    liens_raw = liens_m.group(1).strip() if liens_m else ""

    # Strip those sections and ![Featured] from main body
    raw_body = re.sub(r'## Informations\n[\s\S]+?(?=\n## |\Z)', '', raw).strip()
    raw_body = re.sub(r'## Disponibilité\n[\s\S]+?(?=\n## |\Z)', '', raw_body).strip()
    raw_body = re.sub(r'## Liens\n[\s\S]+?(?=\n## |\Z)', '', raw_body).strip()
    raw_body = re.sub(r'!\[Featured\]\([^)]+\)\n?', '', raw_body).strip()

    # Résumé section — strip trailing © line
    res_m = re.search(r'## Résumé\n\n([\s\S]+?)(?:\n\n##|\Z)', raw)
    resume = res_m.group(1).strip() if res_m else ""
    resume = re.sub(r'\n©[^\n]*$', '', resume).strip()

    # Buy links as list of (label, url) tuples for button rendering
    liens_list = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', liens_raw) if liens_raw else []

    # Disponibilité as plain text (one line)
    dispo_text = re.sub(r'^## Disponibilité\s*', '', dispo_raw).strip() if dispo_raw else ""

    return dict(
        slug=path.stem,
        title=full_title,
        main_title=main_title.strip(),
        subtitle=subtitle,
        cover=cover,
        featured=featured,
        gallery=gallery,
        price=price,
        resume=resume,
        liens=liens_list,
        dispo_text=dispo_text,
        info_raw=info_raw,
        raw=raw_body,
    )


def parse_post(path: Path) -> dict:
    import yaml
    filename = path.stem                          # e.g. "0071-cruelle-maree"
    parts = filename.split("-", 1)
    slug  = parts[1] if len(parts) > 1 else filename

    raw = path.read_text(encoding="utf-8")

    # Parse YAML frontmatter
    fm = {}
    body = raw
    if raw.startswith("---"):
        end = raw.find("---", 3)
        if end != -1:
            try:
                fm = yaml.safe_load(raw[3:end]) or {}
            except Exception:
                fm = {}
            body = raw[end+3:].lstrip("\n")

    title        = fm.get("title") or slug
    order        = int(fm.get("order") or 0)
    header_image = fm.get("header_image") or None
    date         = fm.get("date") or None   # may be a datetime.date object from YAML

    # Short excerpt: first ~180 chars of body text
    raw_exc = body
    raw_exc = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', raw_exc)   # strip images
    raw_exc = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', raw_exc)  # links → text
    raw_exc = re.sub(r'https?://\S+', '', raw_exc)            # bare URLs
    raw_exc = re.sub(r'[*_`#!]', '', raw_exc)
    excerpt = ' '.join(raw_exc.split())[:180]
    if len(' '.join(raw_exc.split())) > 180:
        excerpt += "…"

    html = to_html(body)

    return dict(
        slug=slug, order=order, title=title,
        header_image=header_image, excerpt=excerpt, html=html,
        date=date, date_str=fmt_date_fr(date),
    )


# ── Build ──────────────────────────────────────────────────────────────────

def build():
    # Clean output
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()

    # Static assets
    optimise_images(ROOT / "images", SITE / "images")
    shutil.copytree(ROOT / "assets", SITE / "assets")
    # Copy static public/ files (e.g. Decap CMS admin)
    public = ROOT / "public"
    if public.exists():
        shutil.copytree(public, SITE, dirs_exist_ok=True)

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
        resume_html = to_html(book["resume"]) if book["resume"] else ""
        info_html = to_html(book["info_raw"]) if book["info_raw"] else ""
        review_path = ROOT / "reviews" / f"{book['slug']}.md"
        if review_path.exists():
            reviews_raw = re.sub(r'^# .+\n', '', review_path.read_text(encoding="utf-8"), count=1)
            reviews_html = fix_image_paths(to_html(reviews_raw), "../../")
        else:
            reviews_html = ""
        render("book.html", SITE / "livres" / book["slug"] / "index.html",
               book={**book, "html": book_html, "resume_html": resume_html,
                     "info_html": info_html, "reviews_html": reviews_html},
               current_page="livres", base="../../")

    # ── Blog posts ── (newest first in listing; only posts with a header image)
    posts = [parse_post(p) for p in sorted((ROOT / "blog").glob("*.md"), reverse=True)]
    posts = [p for p in posts if p["header_image"]]
    posts.sort(key=lambda p: str(p["date"] or "0000-00-00"), reverse=True)
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
