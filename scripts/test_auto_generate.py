#!/usr/bin/env python3
"""
Regression test for auto_generate.py's pick_by_date() cooldown fallback bug.

Root cause (found 2026-09-17 GTM review, confirmed via live sitemap audit):
pick_by_date()'s fallback, used when every pool candidate is in cooldown,
was `return pool[start]` — the raw hash-selected candidate, which could
itself still be in cooldown. That silently defeated the 75-day cooldown
meant to stop topics regenerating as near-duplicates, and duplicates
re-accumulated (e.g. `budget-gym-nutrition-nz` regenerated 2026-08-31 and
again 2026-09-04, both inside the 75-day window — see nzgymguide.md's
2026-09-17 wiki entry).

Fix: when every candidate is in cooldown, fall back to the least-recently
generated candidate (the one closest to exiting cooldown) instead of the
raw hash pick, so the cooldown constraint is respected as much as possible
instead of being silently ignored — while still never returning None and
blocking the generator from running.

Run: venv/bin/python scripts/test_auto_generate.py
"""
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import auto_generate as ag


class FixedToday(date):
    """A date subclass that fixes date.today() for the duration of a test."""
    _fixed = date(2026, 9, 18)

    @classmethod
    def today(cls):
        return cls._fixed


class PickByDateCooldownFallbackTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / 'content' / 'posts').mkdir(parents=True)
        self._orig_root = ag.ROOT
        self._orig_date = ag.date
        ag.ROOT = self.tmp
        ag.date = FixedToday

    def tearDown(self):
        ag.ROOT = self._orig_root
        ag.date = self._orig_date
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_post(self, slug, generated_date):
        path = self.tmp / 'content' / 'posts' / f'{slug}.json'
        path.write_text(json.dumps({'slug': slug, 'generated_date': generated_date}))

    def test_fallback_picks_least_recently_used_not_raw_hash_candidate(self):
        """When every candidate is in cooldown, the fallback must genuinely
        minimise cooldown violation (least-recently-used), not silently
        ignore the cooldown by returning whatever the raw hash picked.

        For date 2026-09-18 + atype 'exercise_tips', pick_by_date()'s
        deterministic hash lands on index 1 ('topic-b') — verified via the
        same md5-of-(date, atype) formula pick_by_date() itself uses. This
        test deliberately makes 'topic-b' the *most* recently generated (5
        days ago, deepest in cooldown) so the old buggy fallback
        (`return pool[start]`) and the fixed least-recently-used fallback
        disagree: the old code would wrongly return 'topic-b', the fix must
        return 'topic-a' (40 days ago — the real least-recently-used one).
        """
        pool = [
            {'type': 'exercise_tips', 'topic': {'slug_base': 'topic-a'}},
            {'type': 'exercise_tips', 'topic': {'slug_base': 'topic-b'}},
            {'type': 'exercise_tips', 'topic': {'slug_base': 'topic-c'}},
        ]
        # All three are inside the 75-day COOLDOWN_DAYS window.
        self._write_post('topic-a-2026-08', (FixedToday.today() - timedelta(days=40)).isoformat())
        self._write_post('topic-b-2026-09', (FixedToday.today() - timedelta(days=5)).isoformat())
        self._write_post('topic-c-2026-08', (FixedToday.today() - timedelta(days=20)).isoformat())

        # Confirm the assumption above still holds (guards against this test
        # silently becoming a no-op if pick_by_date()'s hash formula ever
        # changes without updating this test).
        seed = int(hashlib.md5(f"{FixedToday.today().isoformat()}:exercise_tips".encode()).hexdigest(), 16)
        self.assertEqual(seed % len(pool), 1, "test setup assumption about the hash start index is stale")

        result = ag.pick_by_date(pool, 'exercise_tips')

        self.assertIsNotNone(result, "pick_by_date() must still return a topic, not None")
        self.assertEqual(
            result['topic']['slug_base'], 'topic-a',
            "when every candidate is in cooldown, the fallback must pick the "
            "least-recently-used one (topic-a, 40 days ago) instead of "
            "silently ignoring the cooldown via the raw hash-selected pick "
            "(which would wrongly return topic-b, only 5 days old)",
        )

    def test_cooldown_still_respected_when_a_candidate_is_free(self):
        """Sanity check the normal (non-fallback) path is unaffected: a
        candidate that is NOT in cooldown must always win."""
        pool = [
            {'type': 'exercise_tips', 'topic': {'slug_base': 'hot-topic'}},
            {'type': 'exercise_tips', 'topic': {'slug_base': 'cold-topic'}},
        ]
        self._write_post('hot-topic-2026-09', (FixedToday.today() - timedelta(days=5)).isoformat())
        # cold-topic has never been generated -> not in cooldown.
        result = ag.pick_by_date(pool, 'exercise_tips')
        self.assertEqual(result['topic']['slug_base'], 'cold-topic')


if __name__ == '__main__':
    unittest.main()
