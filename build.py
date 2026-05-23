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

    # Guide pages
    guides = [
        ("cheapest-gym-nz", "cheapest-gym-nz"),
        ("gym-membership-tips", "gym-membership-tips"),
        ("cancel-gym-membership-nz", "cancel-gym-membership-nz"),
        ("gym-contracts-nz", "gym-contracts-nz"),
        ("classpass-review-nz", "classpass-review-nz"),
    ]
    for slug, tpl_name in guides:
        guide_file = CONTENT / "guides" / f"{slug}.json"
        if guide_file.exists():
            guide = json.loads(guide_file.read_text())
            render("guide.html", f"guides/{slug}/index.html",
                   guide=guide, **ctx)

    # Sitemap
    pages = (
        [""] +
        ["compare"] +
        [f"gym/{g['slug']}" for g in gyms] +
        [f"gym/{c['slug']}" for c in cities] +
        [f"guides/{s}" for s, _ in guides]
    )
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for p in pages:
        sitemap += f"  <url><loc>{site['base_url']}/{p}</loc></url>\n"
    sitemap += "</urlset>"
    (OUT / "sitemap.xml").write_text(sitemap)

    # CNAME for GitHub Pages
    (OUT / "CNAME").write_text("nzgymguide.co.nz")

    print(f"\nBuild complete → {OUT}/")


if __name__ == "__main__":
    build()
