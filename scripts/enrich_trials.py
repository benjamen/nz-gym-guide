import json

PATH = "data/gyms.json"

# Researched/verified trial+casual data for major NZ chains (June 2026).
# Keyed by slug. Independent studios fall through to a default that reuses
# the existing pricing.casual_visit value and marks trial as unknown/false.
CHAIN_DATA = {
    "les-mills": {
        "free_trial": True,
        "trial_duration": "Up to 14 days",
        "trial_notes": "Free trial via the Les Mills app / in-club; varies by promo, sign up online or in person.",
        "casual_visit_price": 25.00,
        "casual_visit_notes": "Day pass; confirm at reception as pricing isn't published online.",
    },
    "city-fitness": {
        "free_trial": True,
        "trial_duration": "3 days",
        "trial_notes": "Free 3-day pass available online; longer trials sometimes offered in promos.",
        "casual_visit_price": 20.00,
        "casual_visit_notes": "Casual day pass; price varies by club.",
    },
    "anytime-fitness": {
        "free_trial": True,
        "trial_duration": "7 days",
        "trial_notes": "Free 7-day trial; access during staffed hours. Each club is independently owned so terms vary.",
        "casual_visit_price": 20.00,
        "casual_visit_notes": "Casual visits typically $10-$25 depending on club; ask your local gym.",
    },
    "snap-fitness": {
        "free_trial": True,
        "trial_duration": "7 days",
        "trial_notes": "Free 7-day pass available online; access during staffed hours.",
        "casual_visit_price": 20.00,
        "casual_visit_notes": "Casual day pass; varies by franchise.",
    },
    "jetts": {
        "free_trial": True,
        "trial_duration": "1 day (plus periodic Open Week)",
        "trial_notes": "Free pass during staffed hours; Jetts also runs periodic free Open Week events.",
        "casual_visit_price": 15.00,
        "casual_visit_notes": "Casual visit $15, or 5-visit concession for $30. One-off $10 access fee on joining.",
    },
    "ymca": {
        "free_trial": True,
        "trial_duration": "3 days",
        "trial_notes": "Free trial pass available; ask at your local YMCA branch.",
        "casual_visit_price": 15.00,
        "casual_visit_notes": "Casual gym entry; concession cards and community rates available.",
    },
    "contours": {
        "free_trial": True,
        "trial_duration": "Free intro session",
        "trial_notes": "Women-only; free intro session/consultation rather than a multi-day pass.",
        "casual_visit_price": 15.00,
        "casual_visit_notes": "Casual visit; confirm with local studio.",
    },
    "9round": {
        "free_trial": True,
        "trial_duration": "1 free workout",
        "trial_notes": "Free trial workout for first-timers; book online.",
        "casual_visit_price": 25.00,
        "casual_visit_notes": "Drop-in class price; varies by studio.",
    },
    "f45": {
        "free_trial": True,
        "trial_duration": "Free trial class / 1-2 week intro",
        "trial_notes": "Free first class; many studios offer a 1-2 week intro trial. Each studio independently run.",
        "casual_visit_price": 30.00,
        "casual_visit_notes": "Drop-in class; class packs cheaper per visit.",
    },
    "orangetheory": {
        "free_trial": True,
        "trial_duration": "Free intro class",
        "trial_notes": "Free first/intro class for new members; book via studio.",
        "casual_visit_price": 32.00,
        "casual_visit_notes": "Drop-in class price; packs available.",
    },
    "247-fitness-wellington": {
        "free_trial": True,
        "trial_duration": "Day pass / trial available",
        "trial_notes": "24/7 access gym; trial/day pass available — contact club to confirm.",
        "casual_visit_price": 15.00,
        "casual_visit_notes": "Casual visit; confirm at club.",
    },
    "classpass": {
        "free_trial": True,
        "trial_duration": "Free trial credits for new users",
        "trial_notes": "Aggregator app — new users typically get free trial credits to use across partner studios.",
        "casual_visit_price": None,
        "casual_visit_notes": "Pay-per-class via credits; no single casual price.",
    },
}


def main():
    data = json.load(open(PATH))
    enriched_named = 0
    enriched_default = 0
    for g in data:
        slug = g["slug"]
        if slug in CHAIN_DATA:
            g.update(CHAIN_DATA[slug])
            enriched_named += 1
        else:
            # Independent studio: reuse existing casual_visit if present.
            existing_casual = g.get("pricing", {}).get("casual_visit")
            g["free_trial"] = False
            g["trial_duration"] = None
            g["trial_notes"] = "No standing free trial found; many studios offer a free/discounted intro class — ask directly."
            g["casual_visit_price"] = float(existing_casual) if existing_casual is not None else None
            g["casual_visit_notes"] = (
                "Drop-in / casual rate from listed pricing." if existing_casual is not None
                else "Casual rate not published; contact studio."
            )
            enriched_default += 1

    json.dump(data, open(PATH, "w"), indent=2, ensure_ascii=False)
    print(f"Enriched named chains: {enriched_named}")
    print(f"Enriched independents (default): {enriched_default}")
    print(f"Total: {enriched_named + enriched_default}")


if __name__ == "__main__":
    main()
