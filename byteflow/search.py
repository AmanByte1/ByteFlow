"""
Lightweight, fully-offline semantic-ish search over text entries.

No external dependencies, no model downloads. Uses classic TF-IDF
(term frequency - inverse document frequency) + cosine similarity,
backed by an inverted index for fast lookup as memory grows.

This is intentionally simple: it matches on shared meaningful words,
not true semantic meaning (it won't know "dog" and "puppy" are related).
It's a solid, zero-cost upgrade over "only look at the last N messages",
and the TextIndex class is structured so a real embedding-based index
could be swapped in later without changing the calling code.
"""

import math
import re
from collections import defaultdict

_WORD_RE = re.compile(r"[a-zA-Z0-9]+")

# Common English words that carry little distinguishing meaning for search.
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
    "my", "your", "his", "its", "our", "their",
    "and", "or", "but", "if", "so", "to", "of", "in", "on", "at", "for",
    "with", "as", "by", "from", "about", "into", "this", "that", "these", "those",
    "do", "does", "did", "have", "has", "had", "will", "would", "can", "could",
    "should", "what", "who", "when", "where", "why", "how",
}


def _simple_stem(word):
    """
    Very lightweight suffix stripping (not a real stemmer like Porter's,
    just enough to fold common plurals/verb forms together so 'dog' and
    'dogs', or 'learn' and 'learning', count as the same token).
    Intentionally conservative to avoid mangling short/irregular words.
    """
    if len(word) <= 3:
        return word
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("ing") and len(word) > 5:
        return word[:-3]
    if word.endswith("es") and len(word) > 4:
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def tokenize(text):
    """Lowercase, extract words, drop stopwords, lightly stem."""
    words = _WORD_RE.findall(text.lower())
    return [_simple_stem(w) for w in words if w not in _STOPWORDS and len(w) > 1]


class TextIndex:
    """
    An inverted-index-backed TF-IDF search over a growing list of text entries.

    Usage:
        idx = TextIndex()
        idx.add(0, "my name is Aman")
        idx.add(1, "I love hiking on weekends")
        idx.search("what's my name", top_k=3)  # -> [(0, score), ...]

    Designed to be rebuilt cheaply from a list of (id, text) pairs, since
    ByteFlow's memory is small enough (thousands of entries) that this
    stays fast without needing a persistent on-disk index.
    """

    def __init__(self):
        self.doc_tokens = {}            # doc_id -> token list
        self.inverted_index = defaultdict(set)  # token -> set of doc_ids
        self.doc_count = 0

    def add(self, doc_id, text):
        tokens = tokenize(text)
        self.doc_tokens[doc_id] = tokens
        for tok in set(tokens):
            self.inverted_index[tok].add(doc_id)
        self.doc_count += 1

    def _idf(self, token):
        doc_freq = len(self.inverted_index.get(token, ()))
        if doc_freq == 0:
            return 0.0
        # standard smoothed IDF
        return math.log((self.doc_count + 1) / (doc_freq + 1)) + 1.0

    def _tf_vector(self, tokens):
        counts = defaultdict(int)
        for t in tokens:
            counts[t] += 1
        total = len(tokens) or 1
        return {t: c / total for t, c in counts.items()}

    def _tfidf_vector(self, tokens):
        tf = self._tf_vector(tokens)
        return {t: freq * self._idf(t) for t, freq in tf.items()}

    @staticmethod
    def _cosine(vec_a, vec_b):
        common = set(vec_a) & set(vec_b)
        if not common:
            return 0.0
        dot = sum(vec_a[t] * vec_b[t] for t in common)
        norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
        norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query, top_k=5, min_score=0.05):
        """
        Return up to top_k (doc_id, score) pairs most relevant to query,
        sorted by descending score. Only docs sharing at least one
        meaningful token with the query are considered (via the
        inverted index), so this stays fast even with a lot of history.
        """
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # candidate docs = union of postings lists for query tokens
        candidates = set()
        for tok in query_tokens:
            candidates |= self.inverted_index.get(tok, set())

        if not candidates:
            return []

        query_vec = self._tfidf_vector(query_tokens)

        scored = []
        for doc_id in candidates:
            doc_vec = self._tfidf_vector(self.doc_tokens[doc_id])
            score = self._cosine(query_vec, doc_vec)
            if score >= min_score:
                scored.append((doc_id, score))

        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]
