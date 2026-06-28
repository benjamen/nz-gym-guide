#!/usr/bin/env python3
"""
Auto-generates 4 daily posts for nzgymguide.co.nz.
  1. Exercise tip       — workout and training advice for NZ gym-goers
  2. Gym deals          — NZ gym deals, promos, and price guides
  3. Health information — health, wellness and fitness info for New Zealanders
  4. Nutrition & food   — eating for fitness, NZ supplements, meal prep, protein

Uses Groq API (llama-3.3-70b-versatile) for content generation.
Run daily via cron / systemd timer.

Usage:
  python3 scripts/auto_generate.py            # generate today's 4 posts
  python3 scripts/auto_generate.py --dry-run  # preview topics only
  python3 scripts/auto_generate.py --rebuild  # rebuild + push only
  python3 scripts/auto_generate.py --force    # regenerate even if done today
  python3 scripts/auto_generate.py --count 5  # generate N posts
  python3 scripts/auto_generate.py --type nutrition  # one specific type
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
VENV_PYTHON = ROOT / 'venv' / 'bin' / 'python'
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

MONTHS = ['January','February','March','April','May','June',
          'July','August','September','October','November','December']

# ── Load data ─────────────────────────────────────────────────────────────────

def load_data():
    gyms   = json.loads((ROOT / 'data/gyms.json').read_text())
    cities = json.loads((ROOT / 'data/cities.json').read_text())
    site   = json.loads((ROOT / 'data/site.json').read_text())
    deals  = json.loads((ROOT / 'data/deals.json').read_text())
    return gyms, cities, site, deals

# ── Exercise tip topic pools ──────────────────────────────────────────────────

EXERCISE_TOPICS = [
    # Beginner guides
    {"slug_base": "gym-beginner-guide-nz",       "title": "The Complete Beginner's Guide to Starting a Gym in NZ",
     "angle": "first-timer guide: what to expect, etiquette, what to bring, how to structure your first 4 weeks"},
    {"slug_base": "how-to-start-weight-training-nz", "title": "How to Start Weight Training in NZ — Beginner's Plan",
     "angle": "beginner weight training: free weights vs machines, compound movements, progressive overload, what NZ gyms have the best weights areas"},
    {"slug_base": "gym-routine-nz-beginners",    "title": "Simple Gym Routine for NZ Beginners — 3 Days a Week",
     "angle": "3-day full-body beginner program, sets/reps explained, rest times, warm-up and cool-down"},

    # Cardio & fitness
    {"slug_base": "best-cardio-gym-nz",          "title": "Best Cardio Workouts at the Gym in NZ 2026",
     "angle": "treadmill, rowing, bike, stair climber — calorie burn comparison, HIIT vs steady state, which NZ gym has best cardio equipment"},
    {"slug_base": "hiit-workout-nz-gyms",        "title": "HIIT Workouts in NZ Gyms — F45, Orangetheory vs DIY",
     "angle": "comparing boutique HIIT studios to doing your own HIIT at a standard gym, cost comparison, effectiveness"},
    {"slug_base": "swimming-fitness-nz",         "title": "Swimming for Fitness in NZ — Best Pools and Gym Access",
     "angle": "which NZ gyms have pools, YMCA vs Les Mills vs council pools, cost comparison, swimming workout routines"},

    # Strength & training
    {"slug_base": "strength-training-women-nz",  "title": "Strength Training for Women in NZ — What the Research Says",
     "angle": "busting myths, progressive overload, which NZ gyms have good free weights areas, contours vs standard gym for women"},
    {"slug_base": "compound-exercises-nz",       "title": "5 Compound Exercises Every NZ Gym Member Should Do",
     "angle": "squat, deadlift, bench press, row, overhead press — technique tips, why they're effective, beginner alternatives"},
    {"slug_base": "gym-split-routine-nz",        "title": "Gym Split Routines Explained — Which Is Best for NZ Members?",
     "angle": "full body vs upper/lower vs push/pull/legs, how many days per week, which suits different NZ gym membership types"},

    # Classes & boutique
    {"slug_base": "les-mills-classes-guide-nz",  "title": "Les Mills NZ Class Guide — Which Class Should You Take?",
     "angle": "BodyPump, BodyCombat, BodyBalance, RPM, SH'BAM, GRIT — what each involves, calorie burn, who it suits"},
    {"slug_base": "f45-vs-orangetheory-nz",      "title": "F45 vs Orangetheory in NZ — Which HIIT Studio Wins?",
     "angle": "detailed comparison: format, price, results, community, which type of person each suits, NZ locations"},
    {"slug_base": "yoga-fitness-supplement-nz",  "title": "How Yoga Complements Gym Training — NZ Guide",
     "angle": "active recovery, flexibility for lifters, which yoga styles work for gym-goers, ClassPass yoga options in NZ"},

    # Practical tips
    {"slug_base": "gym-bag-essentials-nz",       "title": "What to Pack in Your Gym Bag — NZ Essentials",
     "angle": "practical packing list for NZ gym-goers, what NZ gyms provide vs bring your own, locker tips"},
    {"slug_base": "gym-etiquette-nz",            "title": "Gym Etiquette in NZ — Unwritten Rules Explained",
     "angle": "rack your weights, wipe machines, headphones, personal space, peak hour tips, specific NZ gym cultures"},
    {"slug_base": "staying-motivated-gym-nz",    "title": "How to Actually Stick to the Gym — NZ Research-Backed Tips",
     "angle": "habit formation, accountability, tracking, when to go (morning vs evening), gym buddy culture in NZ"},
    {"slug_base": "home-vs-gym-nz",              "title": "Home Gym vs Gym Membership in NZ — Real Cost Comparison",
     "angle": "upfront equipment cost vs monthly membership, space requirements, what you miss at home, break-even analysis"},
    {"slug_base": "pre-workout-nutrition-nz",    "title": "What to Eat Before and After the Gym — NZ Advice",
     "angle": "timing meals around training, simple NZ-available pre/post workout foods, hydration in NZ climate"},
    {"slug_base": "gym-recovery-nz",             "title": "Gym Recovery — How Rest Days Make You Fitter",
     "angle": "muscle repair science, DOMS, active recovery options at NZ gyms (sauna, pool, yoga), sleep and training"},
]

# ── Nutrition & food topic pools ─────────────────────────────────────────────

NUTRITION_TOPICS = [
    # Pre/post workout nutrition
    {"slug_base": "pre-workout-food-nz",          "title": "What to Eat Before the Gym in NZ — Timing and Food Guide",
     "angle": "meal timing 1-3 hours before training, quick options from NZ supermarkets, fasted training pros/cons, simple carb+protein combos"},
    {"slug_base": "post-workout-meal-nz",         "title": "Best Post-Workout Meals for NZ Gym-Goers",
     "angle": "protein synthesis window myth vs reality, practical post-gym meals using NZ ingredients, quick options for busy people, budget ideas"},
    {"slug_base": "pre-workout-morning-gym-nz",   "title": "Eating Before a Morning Gym Session in NZ — What Actually Works",
     "angle": "early morning training with minimal food, banana vs protein shake, fasted cardio evidence, what NZ dietitians recommend"},

    # Protein
    {"slug_base": "protein-sources-nz",           "title": "Best Protein Sources for NZ Gym-Goers — Cheap and Effective",
     "angle": "eggs, chicken, canned tuna, cottage cheese, legumes available at NZ supermarkets, cost per gram of protein comparison"},
    {"slug_base": "protein-powder-nz-compare",    "title": "Best Protein Powder in NZ 2026 — Honest Comparison",
     "angle": "Myprotein, Bulk Nutrients, Optimum Nutrition, No Regrets NZ — price per serve, taste, availability, where to buy in NZ"},
    {"slug_base": "plant-protein-nz",             "title": "Plant-Based Protein for NZ Gym-Goers — Complete Guide",
     "angle": "complete vs incomplete proteins, tofu, tempeh, legumes, pea protein powders available in NZ, hitting protein targets on a plant-based diet"},
    {"slug_base": "protein-on-a-budget-nz",       "title": "How to Hit Your Protein Goals on a NZ Budget",
     "angle": "cheapest protein per gram at Pak'nSave, Woolworths, Countdown — eggs, canned tuna, chicken thighs, Greek yoghurt, lentils with NZ prices"},

    # Supplements
    {"slug_base": "creatine-nz-guide",            "title": "Creatine in NZ — Does It Work and Where to Buy It",
     "angle": "what creatine monohydrate does, evidence summary, dosing protocol, NZ brands vs imported, price comparison, who benefits most"},
    {"slug_base": "supplements-worth-it-nz",      "title": "Which Gym Supplements Are Actually Worth It in NZ?",
     "angle": "evidence tier list: creatine (strong), caffeine (strong), protein (food first), BCAAs (weak), fat burners (skip) — NZ context and prices"},
    {"slug_base": "collagen-women-gym-nz",        "title": "Collagen Supplements for Women Who Work Out — NZ Guide",
     "angle": "what collagen does for joints and skin, evidence quality, best time to take it, NZ brands available, cost vs food sources"},
    {"slug_base": "caffeine-pre-workout-nz",      "title": "Caffeine vs Pre-Workout Supplements in NZ — What's Better?",
     "angle": "coffee as pre-workout, caffeine dose for performance, comparing cheap caffeine to expensive pre-workouts, NZ prices, avoiding crash"},

    # Meal prep & practical eating
    {"slug_base": "meal-prep-gym-nz",             "title": "Meal Prep for NZ Gym-Goers — Simple Weekly Plan",
     "angle": "Sunday batch cook strategy, 4-5 high-protein meals using NZ supermarket staples, portion sizing for gym goals, containers and storage"},
    {"slug_base": "budget-gym-nutrition-nz",      "title": "Eating for the Gym on a NZ Budget — Under $100/Week",
     "angle": "weekly meal plan hitting protein targets for under $100 at NZ supermarkets, Pak'nSave staples, avoiding expensive 'health foods'"},
    {"slug_base": "supermarket-gym-food-nz",      "title": "Best Gym Foods at NZ Supermarkets — Woolworths and Pak'nSave",
     "angle": "practical shopping list for gym-goers, high-protein staples at NZ supermarkets, which health foods are overpriced vs worth it"},

    # Fat loss & body composition
    {"slug_base": "fat-loss-nutrition-nz",        "title": "Nutrition for Fat Loss in NZ — What Actually Works",
     "angle": "calorie deficit fundamentals, protein to preserve muscle, NZ-practical food swaps, debunking NZ diet fads, sustainable approach"},
    {"slug_base": "bulking-nz-diet",              "title": "Bulking Diet for NZ Gym-Goers — How to Gain Muscle Without the Fat",
     "angle": "clean bulk vs dirty bulk, calorie surplus targets, NZ high-calorie healthy foods, timing protein around workouts, realistic expectations"},

    # Specific diets
    {"slug_base": "keto-gym-nz",                  "title": "Keto and the Gym in NZ — Can You Build Muscle on Low Carb?",
     "angle": "keto for strength vs cardio performance, adaptation period, NZ keto food costs, who it suits and who it doesn't, practical tips"},
    {"slug_base": "intermittent-fasting-gym-nz",  "title": "Intermittent Fasting and Gym Training in NZ — Honest Guide",
     "angle": "16:8 and training windows, muscle loss risk, performance impact, who IF suits (and who it doesn't), NZ dietitian consensus"},

    # Hydration & recovery nutrition
    {"slug_base": "hydration-gym-nz",             "title": "Hydration for NZ Gym-Goers — How Much Water Do You Really Need?",
     "angle": "NZ climate and sweat rates, electrolytes vs plain water, sports drinks vs water, signs of dehydration during training, practical tips"},
    {"slug_base": "nutrition-gym-women-nz",       "title": "Nutrition for Women Who Lift — NZ Guide",
     "angle": "higher protein needs for body recomposition, iron for active women in NZ, hormone cycle and nutrition, NZ food sources, avoiding under-eating"},
]

# ── Health information topic pools ────────────────────────────────────────────

HEALTH_TOPICS = [
    # Physical health
    {"slug_base": "exercise-mental-health-nz",   "title": "Exercise and Mental Health in NZ — What the Research Shows",
     "angle": "NZ mental health stats, how regular exercise reduces anxiety and depression, which gym formats help most, NZ resources"},
    {"slug_base": "physical-activity-guidelines-nz", "title": "NZ Physical Activity Guidelines 2026 — How Much Exercise Do You Need?",
     "angle": "Ministry of Health guidelines for adults, children, and older NZers, how gyms help meet them, easy ways to get started"},
    {"slug_base": "benefits-gym-membership-nz",  "title": "10 Proven Health Benefits of a Regular Gym Habit",
     "angle": "cardiovascular health, bone density, mental health, weight management, longevity — backed by research, NZ context"},
    {"slug_base": "heart-health-exercise-nz",    "title": "Heart Health and Exercise in NZ — What Your Gym Habit Does for You",
     "angle": "NZ heart disease stats, how cardio training improves heart health, target heart rate zones, gym options in NZ"},
    {"slug_base": "obesity-exercise-nz",         "title": "Exercise for Weight Management in NZ — Honest Advice",
     "angle": "NZ obesity rates, calorie deficit vs exercise, what works, which gym formats burn the most calories, realistic expectations"},
    {"slug_base": "strength-bone-density-nz",    "title": "Weight Training and Bone Health — Why Strength Matters as You Age",
     "angle": "NZ osteoporosis rates, how resistance training builds bone density, which NZ gyms cater to older members, safe programming"},
    {"slug_base": "exercise-diabetes-nz",        "title": "Exercise and Diabetes Management in NZ — A Practical Guide",
     "angle": "NZ diabetes stats, how exercise improves insulin sensitivity, safe gym practices, which gym formats suit diabetics"},

    # Lifestyle & wellness
    {"slug_base": "sleep-exercise-nz",           "title": "Sleep and Exercise — How the Gym Improves Your Sleep",
     "angle": "sleep research and exercise, best time to work out for sleep, how gym routine resets circadian rhythm"},
    {"slug_base": "desk-job-exercise-nz",        "title": "Gym Tips for Desk Workers in NZ — Countering a Sedentary Job",
     "angle": "sitting health risks, which exercises counteract desk posture, best gym visits for office workers, lunchtime gym options"},
    {"slug_base": "exercise-over-50-nz",         "title": "Getting Fit After 50 in NZ — Best Gyms and Programmes",
     "angle": "safe exercise for over 50s, YMCA community focus, Les Mills age-friendly classes, Contours for women, joint-friendly options"},
    {"slug_base": "exercise-anxiety-nz",         "title": "Using Exercise to Manage Anxiety in NZ",
     "angle": "anxiety statistics NZ, exercise as medicine, which gym types reduce anxiety (yoga, walking, swimming), getting started safely"},
    {"slug_base": "postpartum-exercise-nz",      "title": "Exercise After Having a Baby in NZ — Returning to the Gym Safely",
     "angle": "postpartum recovery timeline, pelvic floor, which gyms have crèche (YMCA, Les Mills), Contours for gentle return"},

    # Nutrition & supplements
    {"slug_base": "protein-gym-nz",              "title": "How Much Protein Do You Need? A Guide for NZ Gym Members",
     "angle": "NZ protein sources, how much per kg for different goals, whey vs plant-based, NZ brands vs imports"},
    {"slug_base": "hydration-exercise-nz",       "title": "Hydration and Exercise in NZ — How Much Water Do You Really Need?",
     "angle": "NZ climate considerations, signs of dehydration, electrolytes, what's on offer at NZ gym water stations vs bringing your own"},
    {"slug_base": "supplements-gym-nz",          "title": "Do You Need Supplements for the Gym? An Honest NZ Guide",
     "angle": "creatine, caffeine, protein powder — what works, what doesn't, NZ supplement brands, saving money vs results"},

    # Specific populations
    {"slug_base": "kids-exercise-nz",            "title": "Physical Activity for Kids in NZ — Family Gym Options",
     "angle": "NZ guidelines for children's activity, which NZ gyms are family-friendly, YMCA swimming and crèche, holiday programmes"},
    {"slug_base": "student-gym-nz",              "title": "How NZ Students Can Afford the Gym — Deals and Tips",
     "angle": "student discounts at major NZ chains, university rec centres, ClassPass student rate, Exercise NZ subsidy for students"},
]

# ── Gym deal topic pools (extends existing city_deals and chain_deals) ────────

DEAL_ARTICLE_TYPES = ['city_deals', 'gym_review', 'comparison', 'budget_guide', 'chain_deals', 'suburb_guide', 'exercise_nz']

# ── Build all pools ───────────────────────────────────────────────────────────

def build_all_pools(gyms, cities):
    """Build pools for all article types."""
    pools = {t: [] for t in DEAL_ARTICLE_TYPES}
    pools['exercise_tips'] = []
    pools['health_info']   = []
    pools['nutrition']     = []

    for city in cities:
        pools['city_deals'].append({'type': 'city_deals', 'city': city})
        pools['budget_guide'].append({'type': 'budget_guide', 'city': city})
        pools['exercise_nz'].append({'type': 'exercise_nz', 'city': city})
        for suburb in city.get('suburbs', [])[:4]:
            pools['suburb_guide'].append({'type': 'suburb_guide', 'city': city, 'suburb': suburb})

    for gym in gyms:
        pools['gym_review'].append({'type': 'gym_review', 'gym': gym})
        pools['chain_deals'].append({'type': 'chain_deals', 'gym': gym})

    for i, g1 in enumerate(gyms):
        for g2 in gyms[i+1:]:
            pools['comparison'].append({'type': 'comparison', 'gym1': g1, 'gym2': g2})

    for t in EXERCISE_TOPICS:
        pools['exercise_tips'].append({'type': 'exercise_tips', 'topic': t})
    for t in HEALTH_TOPICS:
        pools['health_info'].append({'type': 'health_info', 'topic': t})
    for t in NUTRITION_TOPICS:
        pools['nutrition'].append({'type': 'nutrition', 'topic': t})

    return pools

def pick_by_date(pool, atype):
    """Rotate through a pool deterministically by date+type."""
    if not pool:
        return None
    seed = int(hashlib.md5(f"{date.today().isoformat()}:{atype}".encode()).hexdigest(), 16)
    return pool[seed % len(pool)]

def pick_todays_four(pools):
    """
    Always pick exactly 4 topics for the day:
      1. An exercise tip
      2. A gym deal (rotating through city_deals, chain_deals, comparison, budget_guide)
      3. Health information
      4. Nutrition & food
    """
    topics = []

    # 1. Exercise tip
    ex = pick_by_date(pools['exercise_tips'], 'exercise_tips')
    if ex:
        topics.append(ex)

    # 2. Gym deal — rotate deal types by week
    deal_types = ['city_deals', 'chain_deals', 'comparison', 'budget_guide', 'exercise_nz']
    week = date.today().isocalendar()[1]
    deal_type = deal_types[week % len(deal_types)]
    deal = pick_by_date(pools.get(deal_type, []), deal_type)
    if not deal:
        deal = pick_by_date(pools['city_deals'], 'city_deals')
    if deal:
        topics.append(deal)

    # 3. Health information
    hi = pick_by_date(pools['health_info'], 'health_info')
    if hi:
        topics.append(hi)

    # 4. Nutrition & food
    nu = pick_by_date(pools['nutrition'], 'nutrition')
    if nu:
        topics.append(nu)

    return topics

def pick_todays_topics(pools, n=4):
    """Wrapper used by --count flag."""
    if n == 4:
        return pick_todays_four(pools)
    # For --count > 4, fill extra slots from remaining deal types
    base = pick_todays_four(pools)
    extra_types = ['gym_review', 'suburb_guide', 'comparison', 'chain_deals']
    used = 0
    while len(base) < n and used < len(extra_types):
        t = extra_types[used]
        item = pick_by_date(pools.get(t, []), t + str(used))
        if item:
            base.append(item)
        used += 1
    return base[:n]

def already_generated(slug):
    return (ROOT / 'content/posts' / f'{slug}.json').exists()

# ── Slug generation ───────────────────────────────────────────────────────────

def topic_slug(topic):
    today = date.today().strftime('%Y-%m')
    month = MONTHS[date.today().month - 1].lower()
    t = topic['type']

    if t == 'exercise_tips':
        base = topic['topic']['slug_base']
        return f"{base}-{today}"
    elif t == 'health_info':
        base = topic['topic']['slug_base']
        return f"{base}-{today}"
    elif t == 'nutrition':
        base = topic['topic']['slug_base']
        return f"{base}-{today}"
    elif t == 'city_deals':
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

def topic_label(topic):
    t = topic['type']
    if t in ('exercise_tips', 'health_info', 'nutrition'):
        return topic['topic']['title']
    elif t == 'comparison':
        return f"{topic['gym1']['name']} vs {topic['gym2']['name']}"
    elif 'gym' in topic:
        return topic['gym']['name']
    elif 'city' in topic and 'suburb' in topic:
        return f"{topic['suburb']}, {topic['city']['name']}"
    elif 'city' in topic:
        return topic['city']['name']
    return '?'

# ── Context builders ──────────────────────────────────────────────────────────

def gym_context(gym):
    p = gym.get('pricing', {})
    f = gym.get('features', {})
    feature_list = [k.replace('_', ' ') for k, v in f.items() if v][:6]
    price_range = f"${p.get('weekly_from',0):.2f}–${p.get('weekly_to', p.get('weekly_from',0)):.2f}/week"
    return (
        f"Gym: {gym['name']} NZ.\n"
        f"Type: {gym.get('type','')}\n"
        f"Price: from {price_range}.\n"
        f"Joining fee: ${p.get('joining_fee',0)}. {p.get('joining_fee_note','')}\n"
        f"Nationwide: {'Yes' if gym.get('nationwide') else 'Selected cities'}.\n"
        f"Features: {', '.join(feature_list)}.\n"
        f"Best for: {gym.get('best_for','')}\n"
        f"Watch out: {gym.get('watch_out','')}\n"
        f"Verdict: {gym.get('verdict','')[:200]}"
    )

def city_context(city):
    return (
        f"City: {city['name']}, NZ.\n"
        f"Population: {city.get('population',''):,}.\n"
        f"Available gyms: {', '.join(city.get('gyms_available',[]))}.\n"
        f"Cheapest option: {city.get('cheapest_option','')}\n"
        f"Best value: {city.get('best_value','')}\n"
        f"Premium pick: {city.get('premium_pick','')}\n"
        f"No-contract pick: {city.get('no_contract_pick','')}\n"
        f"Key suburbs: {', '.join(city.get('suburbs',[])[:6])}\n"
        f"Intro: {city.get('intro','')[:250]}"
    )

def deals_context(deals):
    lines = []
    for d in deals.get('current_deals', []):
        lines.append(f"- {d['gym']}: {d['title']} — {d['saving']}")
    exnz = deals.get('exercise_nz', {})
    lines.append(f"- Exercise NZ subsidy: {exnz.get('saving','')} for eligible members ({exnz.get('eligibility','')})")
    return "Current NZ gym deals:\n" + '\n'.join(lines)

SYSTEM_PROMPT = """You are a practical, honest NZ gym and fitness writer for nzgymguide.co.nz.
Write for New Zealanders. Tone: direct, helpful, evidence-based, not salesy.
For gym deal posts: always include real prices, contract lengths, honest pros/cons.
For exercise posts: give practical, actionable advice with clear structure.
For health posts: cite NZ-relevant statistics and use NZ English spelling (programme, colour, organisation).
Mention Exercise NZ's subsidised gym scheme (40-70% off) where relevant.
Output valid JSON only — no markdown, no extra text outside the JSON object."""

# ── Prompt builders ───────────────────────────────────────────────────────────

def build_prompt(topic, deals):
    month = MONTHS[date.today().month - 1]
    year = date.today().year
    t = topic['type']

    if t == 'exercise_tips':
        tp = topic['topic']
        ctx = f"Site: nzgymguide.co.nz — NZ gym comparison and fitness advice.\nMonth: {month} {year}."
        instruction = (
            f"Write a practical exercise guide: '{tp['title']}'. "
            f"Focus angle: {tp['angle']}. "
            f"Write for NZ gym-goers. Include: actionable advice, 4–6 sections with clear headings, "
            f"a beginner-friendly tone, practical tips specific to what NZ gyms offer, "
            f"and where relevant mention which NZ gym chains (City Fitness, Les Mills, Jetts, Anytime Fitness, etc.) "
            f"best support this type of training. End with a CTA linking to /compare/ or /quiz/."
        )

    elif t == 'health_info':
        tp = topic['topic']
        ctx = f"Site: nzgymguide.co.nz — NZ gym comparison and fitness advice.\nMonth: {month} {year}."
        instruction = (
            f"Write a health and fitness information article: '{tp['title']}'. "
            f"Focus angle: {tp['angle']}. "
            f"Write for New Zealanders. Use NZ English spelling. Include: "
            f"relevant NZ health statistics or context where possible, "
            f"evidence-based advice (reference research without full citations), "
            f"practical steps readers can take, "
            f"and how a gym membership helps — with links to relevant NZ gym options. "
            f"4–6 sections. End with a CTA to /quiz/ or /compare/."
        )

    elif t == 'nutrition':
        tp = topic['topic']
        ctx = f"Site: nzgymguide.co.nz — NZ gym comparison and fitness advice.\nMonth: {month} {year}."
        instruction = (
            f"Write a practical nutrition and food guide for NZ gym-goers: '{tp['title']}'. "
            f"Focus angle: {tp['angle']}. "
            f"Write for New Zealanders. Use NZ English spelling. Include: "
            f"practical, evidence-based advice (not fad-diet hype), "
            f"NZ-specific context (local supermarkets, brands, and prices where relevant), "
            f"actionable tips gym-goers can use this week, "
            f"and 4–6 sections with clear headings. "
            f"Where relevant, mention affordable NZ protein sources or supplements. "
            f"End with a CTA to /compare/ or /quiz/."
        )

    elif t == 'city_deals':
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
            f"Be honest about any gotchas."
        )

    elif t == 'comparison':
        g1, g2 = topic['gym1'], topic['gym2']
        ctx = gym_context(g1) + '\n\n' + gym_context(g2) + '\n\n' + deals_context(deals)
        instruction = (
            f"Write '{g1['name']} vs {g2['name']} NZ — Which Should You Join?'. "
            f"Compare: price per week, contract length, cancellation, facilities, locations, 24/7 access, overall value. "
            f"Include a comparison table. Give a clear verdict with recommended choice per member type."
        )

    elif t == 'budget_guide':
        city = topic['city']
        ctx = city_context(city) + '\n\n' + deals_context(deals)
        instruction = (
            f"Write 'Cheapest Gyms in {city['name']} — No Contract Options {year}'. "
            f"Cover: most affordable options with prices, no-contract alternatives, "
            f"Exercise NZ subsidy as the biggest discount available, "
            f"and a price comparison table of chains available in {city['name']}."
        )

    elif t == 'chain_deals':
        gym = topic['gym']
        ctx = gym_context(gym) + '\n\n' + deals_context(deals)
        gym_deals = [d for d in deals.get('current_deals', []) if gym['slug'] in d.get('chains', [])]
        deal_note = gym_deals[0]['description'] if gym_deals else "check website for current offers"
        instruction = (
            f"Write '{gym['name']} NZ Deals & Promotions — {month} {year}'. "
            f"Current deal note: {deal_note}. "
            f"Cover: how to claim current promotions, best time of year to join, "
            f"whether joining fee can be waived, comparison vs Exercise NZ subsidy, "
            f"and 4-5 tips for getting the best deal."
        )

    elif t == 'suburb_guide':
        city = topic['city']
        suburb = topic['suburb']
        ctx = city_context(city) + '\n\n' + deals_context(deals)
        instruction = (
            f"Write 'Best Gyms Near {suburb}, {city['name']} — {year} Guide'. "
            f"Cover: which gym chains are near {suburb}, typical commute times, "
            f"price comparison for the area, and a recommendation per member type "
            f"(budget, 24/7 access, group classes, premium)."
        )

    elif t == 'exercise_nz':
        city = topic['city']
        exnz = deals.get('exercise_nz', {})
        ctx = city_context(city)
        instruction = (
            f"Write 'How to Get 40-70% Off Your Gym Membership in {city['name']} via Exercise NZ'. "
            f"Explain: what the Exercise NZ subsidised gym scheme is, who is eligible, "
            f"how to claim step by step, which gyms in {city['name']} participate, "
            f"and how much you could save. Include exercise.org.nz URL prominently."
        )

    else:
        ctx = deals_context(deals)
        instruction = "Write a useful NZ gym membership guide."

    schema = json.dumps({
        "title": "Full SEO title (under 70 chars)",
        "short_title": "Short title (under 30 chars)",
        "meta_desc": "SEO meta description (150-160 chars)",
        "intro": "2-3 sentence intro paragraph",
        "reading_time": 5,
        "sections": [
            {
                "heading": "Section heading",
                "body": "2-3 paragraphs body text",
                "list": ["optional bullet points — include when useful"],
                "table": {
                    "headers": ["Col1", "Col2", "Col3"],
                    "rows": [["val1", "val2", "val3"]]
                },
                "cta": {"text": "CTA text", "url": "https://example.com", "affiliate": True}
            }
        ]
    }, indent=2)

    return (
        f"CONTEXT:\n{ctx}\n\n"
        f"TASK: {instruction}\n\n"
        f"OUTPUT: Return a JSON object with 4–6 sections. "
        f"Omit 'list', 'table', 'cta' keys when not relevant to that section:\n{schema}"
    )

# ── Generate one article ──────────────────────────────────────────────────────

def generate_article(topic, deals, slug):
    prompt = build_prompt(topic, deals)
    print(f"  Calling Groq ({GROQ_MODEL})…")

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
    data['post_type'] = topic['type']
    data.setdefault('reading_time', 5)

    # Ensure last section always has a CTA
    if data.get('sections') and 'cta' not in data['sections'][-1]:
        t = topic['type']
        if t == 'exercise_tips':
            cta_url, cta_text = '/quiz/', 'Find the right NZ gym for your goals →'
        elif t == 'nutrition':
            cta_url, cta_text = '/compare/', 'Compare NZ gym memberships →'
        elif t == 'health_info':
            cta_url, cta_text = '/compare/', 'Compare NZ gym memberships →'
        elif t in ('city_deals', 'budget_guide', 'exercise_nz'):
            cta_url = deals.get('exercise_nz', {}).get('url', 'https://www.exercise.org.nz/subsidised-gym-membership/')
            cta_text = 'Check Exercise NZ subsidy eligibility →'
        elif t in ('gym_review', 'chain_deals') and topic.get('gym', {}).get('website'):
            cta_url = topic['gym']['website']
            cta_text = f"View {topic['gym']['name']} membership prices →"
        else:
            cta_url, cta_text = '/compare/', 'Compare all NZ gym memberships →'
        data['sections'][-1]['cta'] = {"text": cta_text, "url": cta_url, "affiliate": False}

    return data

def save_article(data):
    slug = data['slug']
    out = ROOT / 'content/posts' / f'{slug}.json'
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"  ✓ Saved: content/posts/{slug}.json")
    return out

# ── Build & push ──────────────────────────────────────────────────────────────

def rebuild_and_push(dry_run=False):
    if dry_run:
        print("[dry-run] Would rebuild and push")
        return
    print("\nRebuilding site…")
    python = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable
    result = subprocess.run(
        [python, 'build.py'],
        cwd=ROOT, capture_output=True, text=True
    )
    if result.returncode != 0:
        print("BUILD ERROR:", result.stderr[-500:])
        return False
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    print(f"  {lines[-1]}" if lines else "  Built.")

    today = date.today().isoformat()
    subprocess.run(['git', 'add', '-A'], cwd=ROOT)
    msg = f'Daily posts: exercise tip + gym deal + health info + nutrition — {today}'
    subprocess.run(['git', 'commit', '-m', msg], cwd=ROOT)
    push = subprocess.run(['git', 'push'], cwd=ROOT, capture_output=True, text=True)
    if push.returncode == 0:
        print("  ✓ Pushed to GitHub Pages → nzgymguide.co.nz")
    else:
        print("  Push failed:", push.stderr[:200])
    return True

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Generate daily NZ gym posts')
    parser.add_argument('--dry-run', action='store_true', help='Preview topics only, no files written')
    parser.add_argument('--rebuild', action='store_true', help='Rebuild + push without generating')
    parser.add_argument('--force',   action='store_true', help='Regenerate even if done today')
    parser.add_argument('--count',   type=int, default=4, help='Number of posts to generate (default 4)')
    parser.add_argument('--type',    choices=['exercise_tips','health_info','nutrition','city_deals','gym_review',
                                              'comparison','budget_guide','chain_deals','suburb_guide','exercise_nz'],
                        help='Force a specific article type')
    args = parser.parse_args()

    gyms, cities, site, deals = load_data()

    if args.rebuild:
        rebuild_and_push()
        return

    pools  = build_all_pools(gyms, cities)
    topics = pick_todays_topics(pools, n=args.count)

    if args.type:
        pool = pools.get(args.type, [])
        if pool:
            item = pick_by_date(pool, args.type)
            if item:
                topics = [item]

    print(f"\n📅 {date.today().strftime('%A %d %B %Y')} — generating {len(topics)} posts:\n")
    for i, topic in enumerate(topics, 1):
        slug = topic_slug(topic)
        exists = already_generated(slug)
        category = {
            'exercise_tips': '🏋️  Exercise tip',
            'health_info':   '🏥  Health info',
            'nutrition':     '🥗  Nutrition',
            'city_deals':    '💰  City deals',
            'chain_deals':   '🏷️  Chain deals',
            'gym_review':    '⭐  Gym review',
            'comparison':    '⚖️   Comparison',
            'budget_guide':  '💸  Budget guide',
            'suburb_guide':  '📍  Suburb guide',
            'exercise_nz':   '🇳🇿  Exercise NZ',
        }.get(topic['type'], topic['type'])
        print(f"  {i}. {category}")
        print(f"     {topic_label(topic)}")
        print(f"     slug: {slug}")
        print(f"     {'⚠️  EXISTS — will skip' if exists and not args.force else '✓ Will generate'}\n")

    if args.dry_run:
        print("[dry-run] No files written.")
        return

    generated = []
    for i, topic in enumerate(topics, 1):
        slug = topic_slug(topic)
        if already_generated(slug) and not args.force:
            print(f"[{i}/{len(topics)}] Skipping (exists): {slug}")
            continue
        print(f"[{i}/{len(topics)}] Generating: {slug}")
        try:
            data = generate_article(topic, deals, slug)
            save_article(data)
            generated.append(slug)
        except Exception as e:
            print(f"  ✗ ERROR: {e}")

    if generated:
        print(f"\n✓ Generated {len(generated)} posts.")
        rebuild_and_push()
    else:
        print("\nNothing new to generate today.")

if __name__ == '__main__':
    main()
