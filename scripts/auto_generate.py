#!/usr/bin/env python3
"""
Auto-generates 5 gym articles per day for nzgymguide.co.nz.
Uses Groq API for content, affiliate links and deals from site data.
Run daily via systemd timer.

Usage:
  python3 scripts/auto_generate.py            # generate today's 5 posts
  python3 scripts/auto_generate.py --dry-run  # preview topics only
  python3 scripts/auto_generate.py --rebuild  # rebuild + push only
  python3 scripts/auto_generate.py --force    # regenerate even if done today
  python3 scripts/auto_generate.py --count 10 # generate N posts
"""

import json
import os
import re
import sys
import subprocess
import hashlib
import argparse
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Load .env
env_file = ROOT / '.env'
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

from groq import Groq

GROQ_MODEL = "llama-3.3-70b-versatile"
client = Groq(api_key=os.environ['GROQ_API_KEY'])

# ── Load data ─────────────────────────────────────────────────────────────────

def load_data():
    gyms   = json.loads((ROOT / 'data/gyms.json').read_text())
    cities = json.loads((ROOT / 'data/cities.json').read_text())
    site   = json.loads((ROOT / 'data/site.json').read_text())
    deals  = json.loads((ROOT / 'data/deals.json').read_text())
    return gyms, cities, site, deals

# ── Article types ─────────────────────────────────────────────────────────────

ARTICLE_TYPES = [
    'city_deals',       # Best gym deals in [city] this month
    'gym_review',       # [Gym] review — is it worth it?
    'comparison',       # [Gym1] vs [Gym2] in [city]
    'budget_guide',     # Cheapest gyms in [city] — no contract
    'chain_deals',      # [Chain] current NZ deals and promos
    'suburb_guide',     # Best gyms near [suburb], [city]
    'exercise_nz',      # Exercise NZ subsidy guide for [city]
]

MONTHS = ['January','February','March','April','May','June',
          'July','August','September','October','November','December']

# ── Topic pools ───────────────────────────────────────────────────────────────

def build_typed_pools(gyms, cities):
    pools = {t: [] for t in ARTICLE_TYPES}

    for city in cities:
        pools['city_deals'].append({'type': 'city_deals', 'city': city})
        pools['budget_guide'].append({'type': 'budget_guide', 'city': city})
        pools['exercise_nz'].append({'type': 'exercise_nz', 'city': city})
        for suburb in city.get('suburbs', [])[:4]:
            pools['suburb_guide'].append({'type': 'suburb_guide', 'city': city, 'suburb': suburb})

    for gym in gyms:
        pools['gym_review'].append({'type': 'gym_review', 'gym': gym})
        pools['chain_deals'].append({'type': 'chain_deals', 'gym': gym})

    # Gym vs gym comparison pairs
    for i, g1 in enumerate(gyms):
        for g2 in gyms[i+1:]:
            pools['comparison'].append({'type': 'comparison', 'gym1': g1, 'gym2': g2})

    return pools

def pick_todays_topics(pools, n=5):
    """One article per type, rotating through each type's pool by date."""
    today_str = date.today().isoformat()
    topics = []
    used_types = set()

    for atype in ARTICLE_TYPES * 4:
        if len(topics) >= n:
            break
        if atype in used_types:
            continue
        pool = pools.get(atype, [])
        if not pool:
            continue
        seed = int(hashlib.md5(f"{today_str}:{atype}".encode()).hexdigest(), 16)
        idx = seed % len(pool)
        topics.append(pool[idx])
        used_types.add(atype)

    return topics

def already_generated(slug):
    return (ROOT / 'content/posts' / f'{slug}.json').exists()

# ── Slug generation ───────────────────────────────────────────────────────────

def topic_slug(topic):
    today = date.today().strftime('%Y-%m')
    month = MONTHS[date.today().month - 1].lower()
    t = topic['type']

    if t == 'city_deals':
        return f"{topic['city']['slug']}-gym-deals-{today}"
    elif t == 'gym_review':
        return f"{topic['gym']['slug']}-review-nz-{today}"
    elif t == 'comparison':
        return f"{topic['gym1']['slug']}-vs-{topic['gym2']['slug']}-nz"
    elif t == 'budget_guide':
        return f"cheapest-gyms-{topic['city']['slug']}-{today}"
    elif t == 'chain_deals':
        return f"{topic['gym']['slug']}-deals-nz-{month}-{date.today().year}"
    elif t == 'suburb_guide':
        suburb = re.sub(r'[^a-z0-9]+', '-', topic['suburb'].lower()).strip('-')
        return f"gyms-near-{suburb}-{topic['city']['slug']}"
    elif t == 'exercise_nz':
        return f"exercise-nz-subsidy-{topic['city']['slug']}-{date.today().year}"
    return f"nz-gym-guide-{today}"

# ── Context builders ──────────────────────────────────────────────────────────

def gym_context(gym):
    p = gym.get('pricing', {})
    f = gym.get('features', {})
    feature_list = [k.replace('_', ' ') for k, v in f.items() if v][:6]
    price_range = f"${p.get('weekly_from',0):.2f}–${p.get('weekly_to',p.get('weekly_from',0)):.2f}/week"
    return (
        f"Gym: {gym['name']} NZ.\n"
        f"Type: {gym.get('type','')}\n"
        f"Price: from {price_range}.\n"
        f"Joining fee: ${p.get('joining_fee',0)}. {p.get('joining_fee_note','')}\n"
        f"Nationwide: {'Yes' if gym.get('nationwide') else 'Selected cities'}.\n"
        f"Features: {', '.join(feature_list)}.\n"
        f"Best for: {gym.get('best_for','')}.\n"
        f"Watch out: {gym.get('watch_out','')}.\n"
        f"Verdict: {gym.get('verdict','')[:200]}"
    )

def city_context(city):
    return (
        f"City: {city['name']}, NZ.\n"
        f"Population: {city.get('population',''):,}.\n"
        f"Available gyms: {', '.join(city.get('gyms_available',[]))}.\n"
        f"Cheapest option: {city.get('cheapest_option','')}.\n"
        f"Best value: {city.get('best_value','')}.\n"
        f"Premium pick: {city.get('premium_pick','')}.\n"
        f"No-contract pick: {city.get('no_contract_pick','')}.\n"
        f"Key suburbs: {', '.join(city.get('suburbs',[])[:6])}.\n"
        f"Intro: {city.get('intro','')[:250]}"
    )

def deals_context(deals):
    lines = []
    for d in deals.get('current_deals', []):
        lines.append(f"- {d['gym']}: {d['title']} — {d['saving']}")
    exnz = deals.get('exercise_nz', {})
    lines.append(f"- Exercise NZ subsidy: {exnz.get('saving','')} for eligible members ({exnz.get('eligibility','')})")
    return "Current NZ gym deals:\n" + '\n'.join(lines)

SYSTEM_PROMPT = """You are a practical, honest NZ gym comparison writer for nzgymguide.co.nz.
Write for New Zealanders comparing gym memberships. Tone: direct, helpful, price-focused.
Always include real prices, contract lengths, and honest pros/cons.
Mention Exercise NZ's subsidy scheme (40-70% off) where relevant to the topic.
Output valid JSON only — no markdown, no extra text outside the JSON object."""

# ── Prompt builders ───────────────────────────────────────────────────────────

def build_prompt(topic, deals):
    month = MONTHS[date.today().month - 1]
    year = date.today().year
    t = topic['type']

    if t == 'city_deals':
        city = topic['city']
        ctx = city_context(city) + '\n\n' + deals_context(deals)
        instruction = (
            f"Write 'Best Gym Deals in {city['name']} — {month} {year}'. "
            f"Cover: current joining deals and free trial offers at {city['name']} gyms, "
            f"the Exercise NZ subsidy scheme (40-70% off for eligible members), "
            f"which gyms are best value right now, and 4-5 money-saving tips for joining a gym in {city['name']}."
        )

    elif t == 'gym_review':
        gym = topic['gym']
        ctx = gym_context(gym) + '\n\n' + deals_context(deals)
        instruction = (
            f"Write an honest '{gym['name']} NZ Review — {year}'. "
            f"Cover: what you get for the price, contract terms and cancellation policy, "
            f"facility quality, group classes availability, pros and cons, "
            f"who it's best for (and who should avoid it), and current deals. "
            f"Be honest about any gotchas like rolling contracts or fee hikes."
        )

    elif t == 'comparison':
        g1, g2 = topic['gym1'], topic['gym2']
        ctx = gym_context(g1) + '\n\n' + gym_context(g2) + '\n\n' + deals_context(deals)
        instruction = (
            f"Write '{g1['name']} vs {g2['name']} NZ — Which Should You Join?'. "
            f"Compare: price per week, contract length, cancellation policy, "
            f"facilities and classes, locations in NZ, 24/7 access, and overall value. "
            f"Include a comparison table. Give a clear verdict with a recommended choice "
            f"based on different member types (budget, no-contract, premium, 24/7 access)."
        )

    elif t == 'budget_guide':
        city = topic['city']
        ctx = city_context(city) + '\n\n' + deals_context(deals)
        instruction = (
            f"Write 'Cheapest Gyms in {city['name']} — No Contract Options {year}'. "
            f"Cover: the most affordable gym options in {city['name']} with prices, "
            f"no-contract (pay-as-you-go or month-to-month) options, "
            f"the Exercise NZ subsidy scheme as the best way to get the biggest discount, "
            f"and a price comparison table of all major chains available in {city['name']}."
        )

    elif t == 'chain_deals':
        gym = topic['gym']
        ctx = gym_context(gym) + '\n\n' + deals_context(deals)
        # Find this gym's deal if available
        gym_deals = [d for d in deals.get('current_deals', []) if gym['slug'] in d.get('chains', [])]
        deal_note = gym_deals[0]['description'] if gym_deals else "check website for current offers"
        instruction = (
            f"Write '{gym['name']} NZ Deals & Promotions — {month} {year}'. "
            f"Current deal: {deal_note}. "
            f"Cover: current promotions and how to claim them, "
            f"the best time of year to join {gym['name']} for deals, "
            f"whether the joining fee can be waived, "
            f"how {gym['name']} compares to the Exercise NZ subsidy scheme, "
            f"and 4-5 tips for getting the best deal on a {gym['name']} membership."
        )

    elif t == 'suburb_guide':
        city = topic['city']
        suburb = topic['suburb']
        ctx = city_context(city) + '\n\n' + deals_context(deals)
        instruction = (
            f"Write 'Best Gyms Near {suburb}, {city['name']} — {year} Guide'. "
            f"Cover: which gym chains have locations near or in {suburb}, "
            f"typical drive/walk times from {suburb} to each gym, "
            f"price comparison for the {suburb}/{city['name']} area, "
            f"and a recommendation for the best gym for different member types "
            f"(budget, 24/7 access, group classes, premium)."
        )

    elif t == 'exercise_nz':
        city = topic['city']
        exnz = deals.get('exercise_nz', {})
        ctx = city_context(city)
        instruction = (
            f"Write 'How to Get 40-70% Off Your Gym Membership in {city['name']} via Exercise NZ'. "
            f"Explain: what the Exercise NZ subsidised gym membership scheme is, "
            f"who is eligible (new members or inactive for 12+ months), "
            f"how to claim the subsidy step by step, "
            f"which gyms in {city['name']} participate (use exercise.org.nz/subsidised-gym-membership), "
            f"and how much you could save on a 12-month membership at different gym tiers. "
            f"Include the Exercise NZ website URL prominently."
        )

    else:
        city = topic.get('city', {})
        ctx = city_context(city) if city else deals_context(deals)
        instruction = f"Write a useful NZ gym membership guide."

    schema = json.dumps({
        "title": "Full SEO title (under 70 chars)",
        "short_title": "Short title (under 30 chars)",
        "meta_desc": "SEO meta description (150-160 chars)",
        "intro": "2-3 sentence intro paragraph",
        "reading_time": 5,
        "sections": [
            {
                "heading": "Section heading",
                "body": "2-3 paragraphs body text (use <p> tags)",
                "list": ["optional bullet points"],
                "table": {
                    "headers": ["Gym", "Price/week", "Contract", "Best for"],
                    "rows": [["Les Mills", "$17.99+", "12 months", "Group classes"]]
                },
                "cta": {
                    "text": "CTA text",
                    "url": "https://example.com",
                    "affiliate": True
                }
            }
        ]
    }, indent=2)

    return (
        f"CONTEXT:\n{ctx}\n\n"
        f"TASK: {instruction}\n\n"
        f"OUTPUT: Return a JSON object (4–6 sections, omit 'list', 'table', 'cta' keys "
        f"when not relevant to that section):\n{schema}"
    )

# ── Generate one article ──────────────────────────────────────────────────────

def generate_article(topic, deals, slug):
    prompt = build_prompt(topic, deals)
    print(f"  Calling Groq ({GROQ_MODEL})...")

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=3000,
    )

    data = json.loads(response.choices[0].message.content)
    data['slug'] = slug
    data['updated'] = date.today().strftime('%B %Y')
    data['auto_generated'] = True
    data['generated_date'] = date.today().isoformat()
    data.setdefault('reading_time', 5)

    # Ensure last section has an affiliate CTA
    if data.get('sections') and 'cta' not in data['sections'][-1]:
        # Pick a relevant affiliate based on topic type
        t = topic['type']
        if t in ('city_deals', 'budget_guide', 'exercise_nz'):
            cta_url = deals.get('exercise_nz', {}).get('url', 'https://www.exercise.org.nz/subsidised-gym-membership/')
            cta_text = "Check Exercise NZ subsidy eligibility"
        elif t == 'gym_review' and topic.get('gym', {}).get('website'):
            cta_url = topic['gym']['website']
            cta_text = f"View {topic['gym']['name']} membership prices"
        elif t == 'chain_deals' and topic.get('gym', {}).get('website'):
            cta_url = topic['gym']['website']
            cta_text = f"Claim current {topic['gym']['name']} deal"
        else:
            cta_url = "https://www.exercise.org.nz/subsidised-gym-membership/"
            cta_text = "Compare NZ gym deals"
        data['sections'][-1]['cta'] = {"text": cta_text, "url": cta_url, "affiliate": True}

    return data

def save_article(data):
    slug = data['slug']
    out = ROOT / 'content/posts' / f'{slug}.json'
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"  Saved: content/posts/{slug}.json")
    return out

# ── Build & push ──────────────────────────────────────────────────────────────

def rebuild_and_push(dry_run=False):
    if dry_run:
        print("[dry-run] Would rebuild and push")
        return
    print("\nRebuilding site...")
    result = subprocess.run(
        ['/usr/bin/python3', 'build.py'],
        cwd=ROOT, capture_output=True, text=True
    )
    if result.returncode != 0:
        print("BUILD ERROR:", result.stderr[-500:])
        return False
    last = [l for l in result.stdout.splitlines() if l.strip()][-1]
    print(f"  {last}")

    today = date.today().isoformat()
    subprocess.run(['git', 'add', '-A'], cwd=ROOT)
    subprocess.run(['git', 'commit', '-m', f'Auto-generate 5 gym articles — {today}'], cwd=ROOT)
    push = subprocess.run(['git', 'push'], cwd=ROOT, capture_output=True, text=True)
    if push.returncode == 0:
        print("  Pushed to GitHub Pages")
    else:
        print("  Push failed:", push.stderr[:200])
    return True

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--rebuild', action='store_true')
    parser.add_argument('--force',   action='store_true')
    parser.add_argument('--count',   type=int, default=5)
    args = parser.parse_args()

    gyms, cities, site, deals = load_data()

    if args.rebuild:
        rebuild_and_push()
        return

    pools  = build_typed_pools(gyms, cities)
    topics = pick_todays_topics(pools, n=args.count)

    print(f"\nToday's {len(topics)} gym articles ({date.today().isoformat()}):\n")
    for i, topic in enumerate(topics, 1):
        slug = topic_slug(topic)
        exists = already_generated(slug)
        if topic['type'] == 'comparison':
            label = f"{topic['gym1']['name']} vs {topic['gym2']['name']}"
        elif 'gym' in topic:
            label = topic['gym']['name']
        elif 'city' in topic and 'suburb' in topic:
            label = f"{topic['suburb']}, {topic['city']['name']}"
        elif 'city' in topic:
            label = topic['city']['name']
        else:
            label = '?'
        print(f"  {i}. [{topic['type']:15}] {label:35} — {slug}")
        print(f"     {'EXISTS' if exists else 'WILL GENERATE'}")

    if args.dry_run:
        print("\n[dry-run] No files written.")
        return

    generated = []
    for i, topic in enumerate(topics, 1):
        slug = topic_slug(topic)
        if already_generated(slug) and not args.force:
            print(f"\n[{i}/{len(topics)}] Skipping (exists): {slug}")
            continue
        print(f"\n[{i}/{len(topics)}] Generating: {slug}")
        try:
            data = generate_article(topic, deals, slug)
            save_article(data)
            generated.append(slug)
        except Exception as e:
            print(f"  ERROR: {e}")

    if generated:
        print(f"\nGenerated {len(generated)} articles.")
        rebuild_and_push()
    else:
        print("\nNothing new to generate today.")

if __name__ == '__main__':
    main()
