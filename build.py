#!/usr/bin/env python3
"""NZ Gym Guide — static site generator."""

import json
import shutil
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

ROOT    = Path(__file__).parent
DATA    = ROOT / "data"
LAYOUTS = ROOT / "layouts"
STATIC  = ROOT / "static"
CONTENT = ROOT / "content"
OUT     = ROOT / "docs"

env = Environment(loader=FileSystemLoader(str(LAYOUTS)), autoescape=False)

def _to_iso_date(s):
    for fmt in ('%B %Y', '%b %Y', '%Y-%m-%d'):
        try: return datetime.strptime(str(s), fmt).strftime('%Y-%m-01' if 'Y' == fmt[-1] else '%Y-%m-%d')
        except: pass
    return str(s)

env.filters['to_iso_date'] = _to_iso_date
env.filters['tojson'] = lambda v: json.dumps(v, ensure_ascii=False)


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
    pts   = load("personal-trainers")

    ctx = dict(site=site, gyms=gyms, cities=cities)

    print("Building pages...")

    # Homepage
    render("index.html", "index.html", **ctx)

    # Compare all page
    render("compare.html", "compare/index.html", **ctx)

    # Free gym trials & day passes aggregator page
    render("free-trial.html", "free-gym-trial/index.html", **ctx)

    # Gym deal alerts email signup page
    render("gym-alerts.html", "gym-alerts/index.html", **ctx)

    # Individual gym pages
    for gym in gyms:
        render("gym.html", f"gym/{gym['slug']}/index.html",
               gym=gym, **ctx)

    # City pages
    for city in cities:
        city_gyms = [gym_by_slug(gyms, s) for s in city["gyms_available"] if gym_by_slug(gyms, s)]
        render("city.html", f"gym/{city['slug']}/index.html",
               city=city, city_gyms=city_gyms, **ctx)

    # Gym×city intersection pages — programmatic pSEO
    for gym in gyms:
        gym_city_names = [c.lower() for c in gym.get("locations", [])]
        for city in cities:
            if city["name"].lower() in gym_city_names and gym["slug"] in city.get("gyms_available", []):
                render("gym-city.html", f"gym/{gym['slug']}/{city['slug']}/index.html",
                       gym=gym, city=city, **ctx)

    # Auckland suburb pages — capture "[suburb] gym" local search
    akl = next((c for c in cities if c["slug"] == "auckland"), None)
    if akl:
        akl_gyms = [gym_by_slug(gyms, s) for s in akl["gyms_available"] if gym_by_slug(gyms, s)]
        for suburb in akl.get("suburbs", []):
            suburb_slug = suburb.lower().replace(" ", "-").replace("&", "and")
            render("gym-suburb.html", f"gym/auckland/{suburb_slug}/index.html",
                   suburb_name=suburb, suburb_slug=suburb_slug,
                   suburb_gyms=akl_gyms, city=akl, **ctx)

    # My Gyms shortlist page
    render("my-gyms.html", "my-gyms/index.html", **ctx)

    # Personal trainer directory (Auckland)
    render("personal-trainers.html", "personal-trainers/auckland/index.html",
           pts=pts, **ctx)
    for pt in pts:
        render("personal-trainer.html", f"personal-trainers/{pt['slug']}/index.html",
               pt=pt, **ctx)

    # Guide pages — load all guides dynamically from content/guides/
    guides_dir = CONTENT / "guides"
    guides = []
    if guides_dir.exists():
        for f in sorted(guides_dir.glob("*.json")):
            guides.append(json.loads(f.read_text()))
    for guide in guides:
        render("guide.html", f"guides/{guide['slug']}/index.html",
               guide=guide, **ctx)

    # Auto-generated posts — content/posts/
    posts_dir = CONTENT / "posts"
    posts = []
    if posts_dir.exists():
        for f in sorted(posts_dir.glob("*.json"), reverse=True):  # newest first
            posts.append(json.loads(f.read_text()))
    if posts:
        # Posts index page — reuse the guide layout as a simple hub
        render("posts.html", "deals/index.html", posts=posts, **ctx)
        for post in posts:
            render("guide.html", f"deals/{post['slug']}/index.html",
                   guide=post, guide_section='deals', guide_section_label='Gym Deals', **ctx)

    # About and Privacy pages
    render("about.html", "about/index.html", **ctx)
    render("privacy.html", "privacy/index.html", **ctx)

    # Quiz page
    render("quiz.html", "quiz/index.html", **ctx)

    # Diet plan pages
    diet_dir = CONTENT / "diet"
    diet_plans = []
    if diet_dir.exists():
        # Load in a fixed order
        diet_order = ["lose-weight-fast", "lose-weight-healthy", "gain-muscle", "feel-healthier"]
        for slug in diet_order:
            f = diet_dir / f"{slug}.json"
            if f.exists():
                diet_plans.append(json.loads(f.read_text()))
        # Also pick up any extras
        for f in sorted(diet_dir.glob("*.json")):
            slug = f.stem
            if slug not in diet_order:
                diet_plans.append(json.loads(f.read_text()))
    if diet_plans:
        render("diet-index.html", "diet/index.html", diet_plans=diet_plans, **ctx)
        for plan in diet_plans:
            render("diet.html", f"diet/{plan['slug']}/index.html",
                   plan=plan, diet_plans=diet_plans, **ctx)

    # Guides index page
    render("guides-index.html", "guides/index.html", guides=guides, **ctx)

    # 404 page
    render("404.html", "404.html", **ctx)

    # Sitemap
    from datetime import date as _date
    today = _date.today().isoformat()

    def sm_url(path, priority="0.6", changefreq="monthly"):
        loc = f"{site['base_url']}/{path}/" if path else f"{site['base_url']}/"
        return f'  <url><loc>{loc}</loc><lastmod>{today}</lastmod><changefreq>{changefreq}</changefreq><priority>{priority}</priority></url>\n'

    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += sm_url("", "1.0", "weekly")
    sitemap += sm_url("compare", "0.9", "weekly")
    sitemap += sm_url("free-gym-trial", "0.9", "weekly")
    sitemap += sm_url("gym-alerts", "0.7", "weekly")
    sitemap += sm_url("quiz", "0.8", "monthly")
    sitemap += sm_url("about", "0.5", "yearly")
    sitemap += sm_url("privacy", "0.3", "yearly")
    sitemap += sm_url("guides", "0.7", "monthly")
    sitemap += sm_url("diet", "0.8", "monthly")
    if posts:
        sitemap += sm_url("deals", "0.8", "daily")
    for g in gyms:
        sitemap += sm_url(f"gym/{g['slug']}", "0.85", "monthly")
    for c in cities:
        sitemap += sm_url(f"gym/{c['slug']}", "0.8", "monthly")
    # Gym×city intersection pages
    for gym in gyms:
        gym_city_names = [lc.lower() for lc in gym.get("locations", [])]
        for city in cities:
            if city["name"].lower() in gym_city_names and gym["slug"] in city.get("gyms_available", []):
                sitemap += sm_url(f"gym/{gym['slug']}/{city['slug']}", "0.75", "monthly")
    sitemap += sm_url("personal-trainers/auckland", "0.8", "weekly")
    for pt in pts:
        sitemap += sm_url(f"personal-trainers/{pt['slug']}", "0.7", "monthly")
    for g in guides:
        sitemap += sm_url(f"guides/{g['slug']}", "0.75", "monthly")
    if posts:
        for p in posts:
            sitemap += sm_url(f"deals/{p['slug']}", "0.8", "weekly")
    for dp in diet_plans:
        sitemap += sm_url(f"diet/{dp['slug']}", "0.8", "monthly")
    sitemap += "</urlset>"
    (OUT / "sitemap.xml").write_text(sitemap)

    # robots.txt — allow all AI search/citation bots, block training-only scrapers
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\n"
        "User-agent: GPTBot\nAllow: /\n\n"
        "User-agent: ChatGPT-User\nAllow: /\n\n"
        "User-agent: PerplexityBot\nAllow: /\n\n"
        "User-agent: ClaudeBot\nAllow: /\n\n"
        "User-agent: anthropic-ai\nAllow: /\n\n"
        "User-agent: Google-Extended\nAllow: /\n\n"
        "User-agent: Bingbot\nAllow: /\n\n"
        "User-agent: CCBot\nDisallow: /\n\n"
        f"Sitemap: {site['base_url']}/sitemap.xml\n"
    )

    # llms.txt — context file for AI systems
    (OUT / "llms.txt").write_text(
        "# NZ Gym Guide\n\n"
        "NZ Gym Guide is an independent gym comparison site for New Zealand.\n"
        "We compare gym memberships, prices, contracts, and features across major NZ gym chains.\n\n"
        "## What We Cover\n\n"
        "- Side-by-side gym membership comparisons (price, contract, features)\n"
        "- City guides: Auckland, Wellington, Christchurch, Hamilton, Tauranga, Dunedin\n"
        "- Gym reviews for Anytime Fitness, Les Mills, Jetts, Snap Fitness, Gym Society, and more\n"
        "- Free 'Find My Gym' quiz to match users to the best gym for their needs\n"
        "- Cheapest gym guides and 24/7 gym guides for NZ\n"
        "- Free diet plans (lose weight, gain muscle, feel healthier)\n"
        "- Current gym deals and promotions\n\n"
        "## Key Pages\n\n"
        f"- Compare all gyms: {site['base_url']}/compare/\n"
        f"- Find My Gym quiz: {site['base_url']}/quiz/\n"
        f"- Auckland gyms: {site['base_url']}/gym/auckland/\n"
        f"- Wellington gyms: {site['base_url']}/gym/wellington/\n"
        f"- Cheapest gym NZ: {site['base_url']}/guides/cheapest-gym-nz/\n"
        f"- Best 24/7 gym NZ: {site['base_url']}/guides/best-247-gym-nz/\n\n"
        "## About\n\n"
        "Independent, unsponsored gym comparisons. Pricing data is updated regularly.\n"
        f"Contact: {site['contact_email']}\n"
    )

    # CNAME for GitHub Pages
    (OUT / "CNAME").write_text("nzgymguide.co.nz")

    print(f"\nBuild complete → {OUT}/")


if __name__ == "__main__":
    build()
