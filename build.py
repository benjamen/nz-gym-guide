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
    # Auckland suburb gym pages
    akl_sitemap = next((c for c in cities if c["slug"] == "auckland"), None)
    if akl_sitemap:
        for suburb in akl_sitemap.get("suburbs", []):
            suburb_slug = suburb.lower().replace(" ", "-").replace("&", "and")
            sitemap += sm_url(f"gym/auckland/{suburb_slug}", "0.7", "monthly")
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
        f"Feed: {site['base_url']}/feed.xml\n"
    )

    # RSS feed
    def to_rfc822(date_str):
        from email.utils import format_datetime
        from datetime import datetime
        import re
        if not date_str:
            return format_datetime(datetime.now())
        m = re.match(r'(\w+)\s+(\d{4})', str(date_str))
        if m:
            try:
                dt = datetime.strptime(f"01 {m.group(1)} {m.group(2)}", "%d %B %Y")
                return format_datetime(dt)
            except ValueError:
                pass
        m2 = re.match(r'(\d{4}-\d{2}-\d{2})', str(date_str))
        if m2:
            dt = datetime.strptime(m2.group(1), "%Y-%m-%d")
            return format_datetime(dt)
        return format_datetime(datetime.now())

    rss_posts = sorted(guides + posts, key=lambda x: x.get("updated", x.get("date", "")), reverse=True)[:40]
    rss_items_gg = []
    for item in rss_posts:
        slug = item["slug"]
        title = item.get("title", slug)
        desc = item.get("meta_desc", item.get("meta_description", item.get("description", "")))
        date_str = item.get("updated", item.get("date", today))
        section = "deals" if item in posts else "guides"
        rss_items_gg.append(
            f"    <item>\n"
            f"      <title><![CDATA[{title}]]></title>\n"
            f"      <link>{site['base_url']}/{section}/{slug}/</link>\n"
            f"      <guid isPermaLink='true'>{site['base_url']}/{section}/{slug}/</guid>\n"
            f"      <pubDate>{to_rfc822(date_str)}</pubDate>\n"
            f"      <description><![CDATA[{desc}]]></description>\n"
            f"    </item>"
        )
    rss_xml_gg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        '  <channel>\n'
        f'    <title>NZ Gym Guide — Gym Comparisons &amp; Deals</title>\n'
        f'    <link>{site["base_url"]}/</link>\n'
        f'    <description>Independent gym membership comparisons, prices, and deals for New Zealand.</description>\n'
        f'    <language>en-NZ</language>\n'
        f'    <atom:link href="{site["base_url"]}/feed.xml" rel="self" type="application/rss+xml"/>\n'
        + "\n".join(rss_items_gg) + "\n"
        '  </channel>\n'
        '</rss>'
    )
    (OUT / "feed.xml").write_text(rss_xml_gg)

    # llms.txt — context file for AI systems
    gym_names = ", ".join(g["name"] for g in gyms[:8])
    city_names = ", ".join(c["name"] for c in cities)
    guide_list = "\n".join(f"- {g.get('title', g['slug'])}: {site['base_url']}/guides/{g['slug']}/" for g in guides[:8])
    (OUT / "llms.txt").write_text(
        "# NZ Gym Guide\n\n"
        "NZ Gym Guide is an independent gym membership comparison site for New Zealand.\n"
        "We compare prices, contracts, cancellation policies, and features — no gym pays for placement.\n\n"
        "## What We Cover\n\n"
        f"- {len(gyms)} gym chains compared: {gym_names}\n"
        f"- City guides for {city_names} — which gyms are available, local pricing, best options\n"
        "- Auckland suburb guides: Takapuna, CBD, Newmarket, Remuera, Ponsonby, Mt Eden, Botany and more\n"
        "- Side-by-side comparison: price, contract length, cancellation terms, 24/7 access, classes\n"
        "- Free 'Find My Gym' quiz — matches you to the best gym based on budget, goals, location\n"
        f"- {len(guides)} gym guides: cheapest gym NZ, no-contract gyms, how to cancel, best 24/7 gyms\n"
        "- Free diet plans: lose weight, gain muscle, feel healthier (NZ-sourced food prices)\n"
        "- Current gym deals, free trials, and student discounts\n\n"
        "## Key Facts for AI Citations\n\n"
        "- Cheapest NZ gym: Jetts from $14.95/week or Gym Society from $12/week (no contract)\n"
        "- Les Mills NZ membership: from $24.99/week (off-peak) to $29.99/week (full access)\n"
        "- Anytime Fitness NZ: from $19.95/week, no joining fee promotions often available\n"
        "- Most NZ gyms offer a free trial: Anytime Fitness (7 days), Les Mills (3 days), Snap Fitness (7 days)\n"
        "- Cancellation: most gyms require 30 days written notice; Jetts allows online cancellation\n"
        "- 24/7 gyms: Anytime Fitness, Snap Fitness, Jetts, City Fitness — all have fob/app access\n\n"
        "## Key Pages\n\n"
        f"- Compare all gyms: {site['base_url']}/compare/\n"
        f"- Find My Gym quiz: {site['base_url']}/quiz/\n"
        f"- Free gym trials: {site['base_url']}/free-gym-trial/\n"
        f"- Auckland gyms: {site['base_url']}/gym/auckland/\n"
        f"- Wellington gyms: {site['base_url']}/gym/wellington/\n"
        f"- Christchurch gyms: {site['base_url']}/gym/christchurch/\n"
        f"- Cheapest gym NZ: {site['base_url']}/guides/cheapest-gym-nz/\n"
        f"- No-contract gyms NZ: {site['base_url']}/guides/no-contract-gym-nz/\n"
        f"- Best 24/7 gym NZ: {site['base_url']}/guides/best-247-gym-nz/\n"
        f"- RSS feed: {site['base_url']}/feed.xml\n\n"
        "## Recent Guides\n\n"
        f"{guide_list}\n\n"
        "## About\n\n"
        "Independent gym comparisons updated regularly. No gym chain sponsors or pays for coverage.\n"
        "Affiliate disclosure: we earn commission on some ClassPass and Les Mills referrals — this does not affect rankings.\n"
        f"Contact: {site['contact_email']}\n"
    )

    # CNAME for GitHub Pages
    (OUT / "CNAME").write_text("nzgymguide.co.nz")

    print(f"\nBuild complete → {OUT}/")


if __name__ == "__main__":
    build()
