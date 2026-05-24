#!/usr/bin/env python3
"""NZ Gym Guide — static site generator."""

import json
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

ROOT    = Path(__file__).parent
DATA    = ROOT / "data"
LAYOUTS = ROOT / "layouts"
STATIC  = ROOT / "static"
CONTENT = ROOT / "content"
OUT     = ROOT / "docs"

env = Environment(loader=FileSystemLoader(str(LAYOUTS)), autoescape=False)


def load(name):
    return json.loads((DATA / f"{name}.json").read_text())


def write(path: Path, html: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html)
    print(f"  {path.relative_to(OUT)}")


def gym_by_slug(gyms, slug):
    return next((g for g in gyms if g["slug"] == slug), None)


def render(template_name, out_path, **ctx):
    t = env.get_template(template_name)
    write(OUT / out_path, t.render(**ctx))


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    # Copy static assets
    if STATIC.exists():
        shutil.copytree(STATIC, OUT / "static")

    site  = load("site")
    gyms  = load("gyms")
    cities = load("cities")

    ctx = dict(site=site, gyms=gyms, cities=cities)

    print("Building pages...")

    # Homepage
    render("index.html", "index.html", **ctx)

    # Compare all page
    render("compare.html", "compare/index.html", **ctx)

    # Individual gym pages
    for gym in gyms:
        render("gym.html", f"gym/{gym['slug']}/index.html",
               gym=gym, **ctx)

    # City pages
    for city in cities:
        city_gyms = [gym_by_slug(gyms, s) for s in city["gyms_available"] if gym_by_slug(gyms, s)]
        render("city.html", f"gym/{city['slug']}/index.html",
               city=city, city_gyms=city_gyms, **ctx)

    # Guide pages — load all guides dynamically from content/guides/
    guides_dir = CONTENT / "guides"
    guides = []
    if guides_dir.exists():
        for f in sorted(guides_dir.glob("*.json")):
            guides.append(json.loads(f.read_text()))
    for guide in guides:
        render("guide.html", f"guides/{guide['slug']}/index.html",
               guide=guide, **ctx)

    # Sitemap
    from datetime import date as _date
    today = _date.today().isoformat()

    def sm_url(path, priority="0.6", changefreq="monthly"):
        loc = f"{site['base_url']}/{path}" if path else site['base_url']
        return f'  <url><loc>{loc}</loc><lastmod>{today}</lastmod><changefreq>{changefreq}</changefreq><priority>{priority}</priority></url>\n'

    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += sm_url("", "1.0", "weekly")
    sitemap += sm_url("compare", "0.9", "weekly")
    for g in gyms:
        sitemap += sm_url(f"gym/{g['slug']}", "0.8", "monthly")
    for c in cities:
        sitemap += sm_url(f"gym/{c['slug']}", "0.7", "monthly")
    for g in guides:
        sitemap += sm_url(f"guides/{g['slug']}", "0.7", "monthly")
    sitemap += "</urlset>"
    (OUT / "sitemap.xml").write_text(sitemap)

    # robots.txt
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {site['base_url']}/sitemap.xml\n"
    )

    # CNAME for GitHub Pages
    (OUT / "CNAME").write_text("nzgymguide.co.nz")

    print(f"\nBuild complete → {OUT}/")


if __name__ == "__main__":
    build()
