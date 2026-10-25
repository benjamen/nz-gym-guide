#!/usr/bin/env python3
"""Merge near-duplicate deal articles into the one page kept per topic.

The generator used to put the month in the slug, so it rewrote the same topic every
month at a new URL. Each older copy was marked noindex with a `canonical_slug` pointing
at the newer one. Rather than keep dozens of thin duplicates alive, this moves every
page that has a `canonical_slug` to content/_merged/ (out of the build, still in git
history), writes content/redirects.json so the old URLs redirect to the survivor, and
rewrites internal links to the survivor.

  python3 scripts/consolidate_canonical_duplicates.py          # dry run: print the plan
  python3 scripts/consolidate_canonical_duplicates.py --apply  # do it
"""

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"


def load_posts():
    return {f.stem: (f, json.loads(f.read_text(encoding="utf-8"))) for f in sorted(POSTS.glob("*.json"))}


def survivor(slug, posts):
    seen = {slug}
    while True:
        nxt = posts[slug][1].get("canonical_slug")
        if not nxt or nxt not in posts or nxt in seen:
            return slug
        seen.add(nxt)
        slug = nxt


def rewrite_links(old, new):
    pattern = re.compile(r"/deals/" + re.escape(old) + r"(?=[/\"'#?\s)\\])")
    changed = 0
    for path in [*(ROOT / "content").rglob("*.json"), *(ROOT / "data").glob("*.json"), *(ROOT / "layouts").glob("*.html")]:
        if "_merged" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        out = pattern.sub(f"/deals/{new}", text)
        if out != text:
            path.write_text(out, encoding="utf-8")
            changed += 1
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    posts = load_posts()
    plan = {s: survivor(s, posts) for s, (_, d) in posts.items() if d.get("canonical_slug")}
    plan = {s: t for s, t in plan.items() if s != t}
    for old, new in plan.items():
        print(f"merge {old}  ->  {new}")
    print(f"\n{len(plan)} pages into {len(set(plan.values()))} survivors")
    if not args.apply:
        print("(dry run: nothing changed)")
        return

    redirects_path = ROOT / "content" / "redirects.json"
    redirects = json.loads(redirects_path.read_text()) if redirects_path.exists() else {}
    merged_dir = ROOT / "content" / "_merged" / "posts"
    merged_dir.mkdir(parents=True, exist_ok=True)
    for old, new in plan.items():
        subprocess.run(["git", "mv", str(posts[old][0]), str(merged_dir / posts[old][0].name)], cwd=ROOT, check=True)
        redirects[f"deals/{old}"] = f"deals/{new}"
        rewrite_links(old, new)
    redirects_path.write_text(json.dumps(redirects, indent=2, sort_keys=True) + "\n")
    print(f"Moved {len(plan)} files, {len(redirects)} redirects in content/redirects.json")


if __name__ == "__main__":
    main()
