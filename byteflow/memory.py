import json
import os
from datetime import datetime, timezone

from .search import TextIndex


class Memory:
    """
    Conversation memory for an Agent.

    By default this is in-memory only (matches the original behavior).
    Pass a `path` to persist history to a JSON file on disk, so the
    agent "remembers" across separate process runs.

    Supports two ways of recalling the past:
      - get_recent(n): the last n entries, in order (what was just said)
      - search(query, top_k): the entries most relevant to a query,
        regardless of how long ago they were said (offline TF-IDF search,
        see byteflow/search.py)
    """

    def __init__(self, path=None, max_history=1000):
        self.path = path
        self.max_history = max_history
        self.history = []

        self._index = TextIndex()
        self._index_dirty = True  # rebuild index lazily on first search

        if self.path and os.path.exists(self.path):
            self._load()

    # -----------------------------
    # CORE API (unchanged behavior)
    # -----------------------------
    def add(self, role, content):
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.history.append(entry)
        self._index_dirty = True

        # keep memory bounded so the file/list can't grow forever
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
            self._index_dirty = True

        if self.path:
            self._save()

    def get_recent(self, n=5):
        return self.history[-n:]

    def search(self, query, top_k=5):
        """
        Return the entries most relevant to `query`, regardless of
        when they were said. Useful for recalling something mentioned
        long ago that wouldn't show up in get_recent().

        Returns a list of (entry, score) tuples, highest relevance first.
        """
        if self._index_dirty:
            self._rebuild_index()

        results = self._index.search(query, top_k=top_k)
        return [(self.history[doc_id], score) for doc_id, score in results]

    def _rebuild_index(self):
        self._index = TextIndex()
        for i, entry in enumerate(self.history):
            self._index.add(i, entry["content"])
        self._index_dirty = False

    def clear(self):
        self.history = []
        self._index_dirty = True
        if self.path:
            self._save()

    # -----------------------------
    # PERSISTENCE
    # -----------------------------
    def _save(self):
        """Write history to disk. Best-effort: a failed save shouldn't crash the agent."""
        try:
            tmp_path = f"{self.path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.path)  # atomic write
        except OSError as e:
            print(f"[Memory] Warning: failed to save memory to {self.path}: {e}")

    def _load(self):
        """Load history from disk. A corrupt/missing file starts fresh instead of crashing."""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self.history = data
        except (OSError, json.JSONDecodeError) as e:
            print(f"[Memory] Warning: could not load memory from {self.path} ({e}). Starting fresh.")
            self.history = []
