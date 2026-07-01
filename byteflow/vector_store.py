"""
VectorStore - combines chunking.py and embeddings.py into a real
retrieval-augmented (RAG) pipeline: text goes in (chunked first if
long), gets embedded, and similarity search finds the most relevant
chunks for a query - regardless of which entry or document they
originally came from.

This sits alongside (and can replace) Memory's simpler get_recent()/
search() for cases where you want chunk-level retrieval over long
documents or long chat history, not just whole-entry matching.

Default embedder is TfidfEmbedder (fully offline, no dependencies).
Pass a different Embedder (e.g. SentenceTransformerEmbedder) for real
semantic search - same VectorStore code works unchanged either way.
"""

import json
import os

from .chunking import chunk_with_metadata
from .embeddings import TfidfEmbedder


class VectorStore:
    """
    A simple, persistent, chunk-aware vector store.

    Usage:
        store = VectorStore(path="my_vectors.json")
        store.add_document("notes.txt about my project...", source="notes.txt")
        store.add_document("a short chat message", source="chat:42")
        results = store.search("what did I say about my project?", top_k=3)
        # -> [{"text": ..., "source": ..., "score": ...}, ...]

    Long text passed to add_document() is automatically chunked (see
    chunking.py); short text becomes a single chunk, so this is safe
    to call uniformly for both whole documents and individual chat
    messages without the caller needing to think about chunking.
    """

    def __init__(self, embedder=None, path=None, chunk_max_chars=600, chunk_overlap_chars=100):
        self.embedder = embedder or TfidfEmbedder()
        self.path = path
        self.chunk_max_chars = chunk_max_chars
        self.chunk_overlap_chars = chunk_overlap_chars

        # each entry: {"text": str, "source": str, "chunk_index": int, "vector": dict}
        self.entries = []

        if self.path and os.path.exists(self.path):
            self._load()
        self._refit_embedder()

    def add_document(self, text, source):
        """
        Add `text` to the store, chunking it first if it's long.
        `source` is a free-form label (e.g. a filename or a memory
        entry id) used to trace results back to where they came from.
        Returns the number of chunks added.
        """
        chunks = chunk_with_metadata(
            text, source, max_chars=self.chunk_max_chars, overlap_chars=self.chunk_overlap_chars
        )
        if not chunks:
            return 0

        # TF-IDF quality depends on corpus-wide document frequency, so
        # refit across everything (existing + new) before embedding the
        # new chunks - cheap enough at the scale this store is meant for.
        all_texts = [e["text"] for e in self.entries] + [c["text"] for c in chunks]
        if hasattr(self.embedder, "fit"):
            self.embedder.fit(all_texts)

        for chunk in chunks:
            vector = self.embedder.embed_one(chunk["text"])
            self.entries.append({**chunk, "vector": vector})

        # existing entries' vectors were computed under the old (smaller)
        # corpus stats - recompute them too, so scores stay comparable
        if hasattr(self.embedder, "fit"):
            for entry in self.entries:
                entry["vector"] = self.embedder.embed_one(entry["text"])

        if self.path:
            self._save()

        return len(chunks)

    def search(self, query, top_k=5, min_score=0.05):
        """
        Return up to top_k chunks most relevant to `query`, sorted by
        descending score. Each result is a dict:
            {"text": ..., "source": ..., "chunk_index": ..., "score": ...}
        """
        if not self.entries:
            return []

        query_vector = self.embedder.embed_one(query)
        if isinstance(query_vector, dict) and not query_vector:
            return []

        scored = []
        for entry in self.entries:
            score = self.embedder.similarity(query_vector, entry["vector"])
            if score >= min_score:
                scored.append({
                    "text": entry["text"],
                    "source": entry["source"],
                    "chunk_index": entry["chunk_index"],
                    "score": score,
                })

        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:top_k]

    def remove_source(self, source):
        """Remove all chunks belonging to `source` (e.g. when a document
        is deleted/replaced). Returns the number of chunks removed."""
        before = len(self.entries)
        self.entries = [e for e in self.entries if e["source"] != source]
        removed = before - len(self.entries)
        if removed and self.path:
            self._save()
        return removed

    def clear(self):
        self.entries = []
        if self.path:
            self._save()

    def _refit_embedder(self):
        if self.entries and hasattr(self.embedder, "fit"):
            self.embedder.fit([e["text"] for e in self.entries])

    def _save(self):
        try:
            tmp_path = f"{self.path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.entries, f, ensure_ascii=False)
            os.replace(tmp_path, self.path)
        except OSError as e:
            print(f"[VectorStore] Warning: failed to save to {self.path}: {e}")

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self.entries = data
        except (OSError, json.JSONDecodeError) as e:
            print(f"[VectorStore] Warning: could not load from {self.path} ({e}). Starting fresh.")
            self.entries = []
