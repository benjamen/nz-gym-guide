# NZ Gym Guide — SEO Audit Report (June 2026)

**Site:** https://nzgymguide.co.nz
**Audited:** 2026-06-13
**Auditor:** seo-nzgg (seo-scan-team)
**Build:** 354 pages generated, 0 build errors, 0 broken JSON-LD blocks after fixes.

---

## Executive Summary

The site was already in **strong technical SEO shape** before this audit. `build.py` generates a complete `sitemap.xml` (342 URLs), a `robots.txt` (with AI-bot rules + sitemap pointer), and an `llms.txt`. The base template ships canonical tags, full Open Graph + Twitter Card tags, and WebSite + Organization JSON-LD. Gym, city, guide and gym-city templates all carry rich schema (SportsActivityLocation, LocalBusiness, AggregateRating, Review, Article, BreadcrumbList, FAQPage).

The audit found **one high-severity structural-data bug** (invalid FAQ JSON-LD on 122 programmatic pages) plus a batch of medium on-page issues (title/description lengths) and minor gaps (image CLS, generic OG titles on programmatic pages, weak internal linking from city hubs). All were fixed directly. Three content stubs were created to fill planned gaps.

---

## Issues Found

| Severity | Issue | File(s) | Fixed? |
|----------|-------|---------|--------|
| **High** | FAQPage JSON-LD invalid — each `Question` object was missing a closing brace, breaking structured data on **122 gym×city pages** (no FAQ rich-result eligibility) | `layouts/gym-city.html` (lines 24,26,28,30) | ✅ Yes |
| Medium | 27 guide `title` fields >60 chars (SERP truncation) | `content/guides/*.json` | ✅ Yes |
| Medium | 16 guide `meta_desc` too short (<120c) or too long (>165c) | `content/guides/*.json` | ✅ Yes |
| Medium | 10 post `meta_desc` too long (up to 231c); 1 post `title` >60c | `content/posts/*.json` | ✅ Yes |
| Medium | gym×city pages emitted generic `og:title`/`twitter:title` ("NZ Gym Guide") instead of page-specific | `layouts/gym-city.html` | ✅ Yes |
| Low | Facility `<img>` had no `width`/`height` attributes (CLS risk) | `layouts/gym.html` (line 510) | ✅ Yes |
| Low | City hub pages (`/gym/<city>/`) did not link to their in-depth city guide or key national guides (weak internal linking) | `layouts/city.html` | ✅ Yes |
| Low | City template title 64c (minor truncation) | `layouts/city.html` | ✅ Yes |
| Low | gym×city template title 63c | `layouts/gym-city.html` | ✅ Yes |
| Info | ~25 individual gym pages still have titles >62c, driven by long real brand names (e.g. "Wellington Regional Aquatic Centre (WRAC)"). Not fixable without truncating brand names. | `layouts/gym.html` (data-driven) | ⚠️ Accepted |

---

## Fixes Applied

### Technical / Structured Data
- **Fixed invalid FAQ JSON-LD on 122 programmatic gym×city pages.** Each `Question` object in `gym-city.html` was closed with one `}` instead of two (`| tojson }}}` → `| tojson }}}}`), so `acceptedAnswer` closed but the parent `Question` did not. All 354 pages now validate as JSON. This restores FAQ rich-result eligibility across the largest page cluster on the site.
- **Added page-specific OG + Twitter meta** (`og_title2`, `og_desc2`, `tw_title2`, `tw_desc2` blocks) to `gym-city.html` so shared/programmatic pages no longer fall back to the generic site title.
- **Added `width="400" height="200"` to the facility gallery `<img>`** in `gym.html` to reserve layout space and prevent Cumulative Layout Shift.

### On-Page (titles & meta descriptions)
- Rewrote **27 guide titles** to ≤60 chars, keyword-first (e.g. "Best Gym for Teenagers NZ 2026 — Age Rules & Prices").
- Rewrote **16 guide meta descriptions** into the 120–160 char sweet spot, preserving primary keyword + a value/CTA phrase.
- Trimmed **10 post meta descriptions** (some were 200–231 chars) and shortened **1 post title** to ≤60 chars.
- Shortened the **city** and **gym×city** template titles so the common cases sit ≤60 chars.

### Internal Linking
- Added a **"More \<City\> Gym Guides & Advice"** section to every city hub page (`city.html`), linking to that city's in-depth guide (`/guides/<city>-gym-guide-2026/`) plus Cheapest Gym NZ, Best No-Contract Gym NZ, and How to Cancel. This passes authority from high-intent city hubs into the guide cluster (previously those guides were only linked from the guides index).

---

## Content Stubs Created

All three are valid, build-ready guide JSON files (include the template-required fields **and** the requested stub metadata: `h1`, `focus_keyword`, `schema_type`, `h2_outline`). They render at `/guides/<slug>/`, appear in the sitemap, and are linked from the guides index.

| Slug | Target Keyword | Pillar | Rationale |
|------|----------------|--------|-----------|
| `best-gym-for-students-nz` | "best gym for students nz" | Goal-specific | High commercial intent, strong student-discount + campus-gym angle; gap in Tier 4 of content strategy. |
| `free-gym-alternatives-nz` | "free gym nz" | Top-of-funnel | Builds topical authority (council outdoor gyms, free trials, home workouts); planned in strategy but missing. |
| `is-les-mills-worth-it-nz` | "is les mills worth it nz" | Verdict/review | High-intent "worth it" query for NZ's biggest premium brand; planned Tier 5, missing. |

---

## Remaining Recommendations (need human action / future work)

1. **Verify FAQ rich results in Google Search Console** after the next deploy — the gym×city FAQ fix should make 122 pages eligible; confirm via the Rich Results Test and monitor impressions.
2. **Resolve pending affiliate placeholders.** `data/site.json` still has `PENDING_IHERB_CODE`, `PENDING_AWIN`, and `PENDING_SIGNUP` statuses for iHerb and Gymshark — these links currently point to non-monetised/placeholder URLs.
3. **Add real `og:image` per page type.** All pages share one static `og-image.svg`. Branded per-template OG images (gym logo, city name) would lift social CTR. Note: many crawlers prefer PNG/JPG over SVG for OG images — consider a raster fallback.
4. **Long gym-page titles (~25 pages).** Driven by long real venue names. If SERP truncation hurts CTR, consider a `short_name` field in `gyms.json` for the `<title>` while keeping the full name in `<h1>`.
5. **Build the remaining planned comparison/cancellation pages** from `content-strategy/strategy.md` that are still missing (e.g. `ymca-vs-anytime-fitness-nz`, `9round-vs-f45-nz`, `is-anytime-fitness-worth-it-nz`).
6. **Topic-aware "Related guides"** in `guide.html` — the footer currently hard-codes the same 4 related links on every guide. Driving these from a per-guide `related` array (or by category) would tighten the internal-link graph further.
7. **Confirm `static/img/og-image.svg` and favicon assets exist** in the deployed output (referenced by base template).
8. **Python env note:** `build.py` requires the project venv (`./.venv/bin/python build.py`) — Jinja2 is not in the system Python. Worth documenting in the deploy script/CI.

---

## Build Verification

```
./.venv/bin/python build.py  → Build complete, exit 0
Pages generated:        354
Sitemap URLs:           342
Broken JSON-LD blocks:  0   (was 122 before the gym-city fix)
robots.txt sitemap:     present
```
