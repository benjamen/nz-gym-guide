# NZ Gym Guide

SEO content site at nzgymguide.co.nz — compares gym memberships across NZ. Python static site generator (SSG).

## What it does
Compares national gym chains and local studios by city. Monetised via affiliate links (Les Mills/Awin, ClassPass/Impact, Orangetheory/Impact, Myprotein/Awin).

## Structure
- `data/gyms.json` — all gym chain data (pricing, features, reviews)
- `data/cities.json` — city pages (which gyms available, local gym listings)
- `data/deals.json` — current deals
- `build.py` — SSG build script
- `content/gyms/` — per-gym markdown pages
- `content/cities/` — per-city markdown pages
- `layouts/` — Jinja2 templates

## Cities covered
Auckland, Wellington, Christchurch, Hamilton, Tauranga, Dunedin, Palmerston North, Rotorua, New Plymouth

## Gyms in data
National chains: Les Mills, City Fitness, Anytime Fitness, Snap Fitness, Jetts, YMCA, F45, ClassPass, Orangetheory, Contours, 9Round

## Notes
- GA4 tracking: G-4R8CXM89FV
- Contact: instituteofbba@gmail.com
- GitHub Pages deploy
