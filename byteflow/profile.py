"""
Long-term "profile" memory: durable facts extracted from conversations,
kept separate from raw chat history (see memory.py).

Raw chat history (Memory) grows unbounded and is full of throwaway
messages ("ok thanks", "lol", "what's 2+2"). Profile is the distilled,
durable layer: short standalone facts worth carrying into every future
conversation - your name, preferences, ongoing projects, corrections
you've made. This is what makes ByteFlow feel like it's "getting to
know you" over time, rather than just replaying a longer transcript.

Facts are deduplicated by normalized text, so repeating yourself doesn't
create duplicate entries. Like Memory, this persists to a JSON file so
it survives across separate runs of your program.
"""

import json
import os
import re
from datetime import datetime, timezone


def _normalize(text):
    """Loose normalization for duplicate detection (case/punctuation-insensitive)."""
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


class Profile:
    def __init__(self, path=None):
        self.path = path
        self.facts = []  # list of {"fact": str, "added": iso timestamp}

        if self.path and os.path.exists(self.path):
            self._load()

    def add_fact(self, fact):
        """
        Add a durable fact if it's not a near-duplicate of an existing one.
        Returns True if added, False if it was a duplicate (no-op).
        """
        fact = fact.strip()
        if not fact:
            return False

        normalized = _normalize(fact)
        for existing in self.facts:
            if _normalize(existing["fact"]) == normalized:
                return False  # already known, don't duplicate

        self.facts.append({
            "fact": fact,
            "added": datetime.now(timezone.utc).isoformat(),
        })

        if self.path:
            self._save()

        return True

    def all_facts(self):
        return [f["fact"] for f in self.facts]

    def remove_fact(self, fact_text):
        """Remove a fact by exact or normalized-match text. Returns True if removed."""
        normalized = _normalize(fact_text)
        before = len(self.facts)
        self.facts = [f for f in self.facts if _normalize(f["fact"]) != normalized]
        removed = len(self.facts) < before
        if removed and self.path:
            self._save()
        return removed

    def clear(self):
        self.facts = []
        if self.path:
            self._save()

    def format(self):
        """Render facts as a short bullet list for prompt injection."""
        if not self.facts:
            return "(no known facts yet)"
        return "\n".join(f"- {f['fact']}" for f in self.facts)

    def _save(self):
        try:
            tmp_path = f"{self.path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.facts, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.path)
        except OSError as e:
            print(f"[Profile] Warning: failed to save profile to {self.path}: {e}")

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self.facts = data
        except (OSError, json.JSONDecodeError) as e:
            print(f"[Profile] Warning: could not load profile from {self.path} ({e}). Starting fresh.")
            self.facts = []
