"""
Embedder interface - turns text into a vector representation for
similarity search. This is the swappable half of the RAG pipeline
(chunking.py is the other half).

Two implementations:
  - TfidfEmbedder (default, used today): builds on the existing
    TF-IDF + cosine similarity machinery in search.py. Zero new
    dependencies, zero model download, fully offline out of the box.
    Matches on shared words, not true semantic meaning.
  - SentenceTransformerEmbedder (optional, real embeddings): uses the
    'sentence-transformers' library and a downloaded model for genuine
    semantic similarity ("dog" and "puppy" are recognized as related).
    Requires `pip install sentence-transformers` and a one-time model
    download (~100-400MB depending on model) - still fully offline
    after that initial download, no per-query network calls.

Both implement the same interface (embed_one, embed_many, similarity),
so VectorStore (see vector_store.py) works identically regardless of
which embedder backs it - swapping one for the other is a one-line
change, not a rewrite.
"""

from abc import ABC, abstractmethod

from .search import tokenize


class Embedder(ABC):
    """Abstract interface every embedder backend implements."""

    @abstractmethod
    def embed_one(self, text):
        """Return a vector representation of a single piece of text."""
        raise NotImplementedError

    def embed_many(self, texts):
        """Return a list of vectors, one per input text. Default
        implementation just calls embed_one() in a loop; backends with
        a faster batched path (like a real model) can override this."""
        return [self.embed_one(t) for t in texts]

    @abstractmethod
    def similarity(self, vec_a, vec_b):
        """Return a similarity score between two vectors - higher means
        more similar. Scale/range depends on the backend, but within
        one backend's vectors, scores are comparable to each other."""
        raise NotImplementedError


class TfidfEmbedder(Embedder):
    """
    Default, fully-offline embedder with no extra dependencies. A
    "vector" here is a TF-IDF weight dict ({token: weight}), and
    similarity is cosine similarity over those dicts - exactly the
    math already used in search.py's TextIndex, exposed here through
    the standard Embedder interface so it's swappable with a real
    model without changing any calling code.

    Needs to see the whole corpus before embedding (TF-IDF's IDF term
    depends on document frequency across everything), so call
    fit(all_texts) once before embed_one()/embed_many() for accurate
    weighting. Without fit(), it still works but falls back to
    per-text term frequency only (no IDF weighting).
    """

    def __init__(self):
        self._df = {}       # token -> number of fitted documents containing it
        self._doc_count = 0

    def fit(self, texts):
        """Compute document frequencies across `texts` for IDF weighting.
        Call this once with the full corpus before embedding individual
        pieces, for properly weighted vectors. Safe to call again later
        to refit as the corpus grows (e.g. after adding new chunks)."""
        self._df = {}
        self._doc_count = len(texts)
        for text in texts:
            tokens = set(tokenize(text))
            for tok in tokens:
                self._df[tok] = self._df.get(tok, 0) + 1

    def _idf(self, token):
        import math
        doc_freq = self._df.get(token, 0)
        if doc_freq == 0 or self._doc_count == 0:
            return 1.0  # neutral weight when we have no corpus stats yet
        return math.log((self._doc_count + 1) / (doc_freq + 1)) + 1.0

    def embed_one(self, text):
        tokens = tokenize(text)
        if not tokens:
            return {}
        counts = {}
        for t in tokens:
            counts[t] = counts.get(t, 0) + 1
        total = len(tokens)
        return {t: (c / total) * self._idf(t) for t, c in counts.items()}

    def similarity(self, vec_a, vec_b):
        common = set(vec_a) & set(vec_b)
        if not common:
            return 0.0
        dot = sum(vec_a[t] * vec_b[t] for t in common)
        norm_a = sum(v * v for v in vec_a.values()) ** 0.5
        norm_b = sum(v * v for v in vec_b.values()) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class SentenceTransformerEmbedder(Embedder):
    """
    Real semantic embeddings via the 'sentence-transformers' library.
    Optional - requires `pip install sentence-transformers` and a
    one-time model download. Fully offline after that download (the
    model runs locally; no per-query network calls).

    Usage:
        embedder = SentenceTransformerEmbedder()  # downloads model on first use
        store = VectorStore(embedder=embedder)

    Swap-in replacement for TfidfEmbedder - same interface, genuinely
    understands semantic similarity (e.g. "dog" and "puppy") rather
    than only matching shared words.
    """

    def __init__(self, model_name="all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "SentenceTransformerEmbedder requires 'sentence-transformers'. "
                "Install it with: pip install sentence-transformers\n"
                "(This will also download a model on first use, ~80-400MB "
                "depending on model_name - fully offline after that.)"
            ) from e

        self._model = SentenceTransformer(model_name)

    def embed_one(self, text):
        return self._model.encode(text, convert_to_numpy=True)

    def embed_many(self, texts):
        return list(self._model.encode(texts, convert_to_numpy=True))

    def similarity(self, vec_a, vec_b):
        import numpy as np
        dot = float(np.dot(vec_a, vec_b))
        norm_a = float(np.linalg.norm(vec_a))
        norm_b = float(np.linalg.norm(vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


def sentence_transformers_available():
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False
