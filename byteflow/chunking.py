"""
Text chunking - splits long text into overlapping pieces so search can
land on the relevant paragraph inside a big document or a long stretch
of chat history, instead of only ever matching a whole (possibly huge,
possibly tiny) entry as a single unit.

This is the "chunk" half of a RAG (retrieval-augmented generation)
pipeline. The other half - turning chunks into vectors for similarity
search - lives in embeddings.py.

Chunking strategy: split on paragraph/sentence boundaries where
possible (so chunks read naturally, not mid-sentence), pack chunks up
to a target size, and overlap consecutive chunks slightly so a fact
that happens to sit right at a chunk boundary isn't invisible to
search no matter which side of the cut it landed on.
"""

import re

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def split_into_sentences(text):
    """Naive but effective sentence splitter - splits after ./!/? followed by whitespace."""
    text = text.strip()
    if not text:
        return []
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def _force_split(text, max_chars):
    """
    Last-resort splitter for a single 'sentence' that's still too long
    on its own (e.g. unpunctuated text, code, log dumps). Breaks on
    whitespace near the max_chars boundary rather than mid-word where
    possible, falling back to a hard character cut if there's no
    whitespace to break on at all.
    """
    pieces = []
    remaining = text
    while len(remaining) > max_chars:
        cut = remaining.rfind(" ", 0, max_chars)
        if cut <= 0:
            cut = max_chars  # no whitespace found - hard cut
        pieces.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        pieces.append(remaining)
    return pieces


def chunk_text(text, max_chars=600, overlap_chars=100):
    """
    Split `text` into a list of chunk strings, each up to ~max_chars,
    breaking on sentence boundaries where possible rather than mid-word.
    Consecutive chunks overlap by ~overlap_chars so content near a
    chunk boundary still gets full context in at least one chunk.

    Short text (shorter than max_chars) returns a single chunk - this
    function is a no-op for anything already small, which is the common
    case for normal chat messages.

    Falls back to a hard whitespace-based split for any single
    "sentence" that's still too long on its own (unpunctuated text,
    code, log dumps) - chunk_text() never returns a chunk wildly larger
    than max_chars, regardless of input punctuation.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    sentences = split_into_sentences(text)
    if not sentences:
        return _force_split(text, max_chars)

    # expand any individual sentence that's itself too long
    expanded = []
    for s in sentences:
        if len(s) > max_chars:
            expanded.extend(_force_split(s, max_chars))
        else:
            expanded.append(s)
    sentences = expanded

    chunks = []
    current = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence) + 1  # +1 for the joining space

        if current and current_len + sentence_len > max_chars:
            chunk_str = " ".join(current)
            chunks.append(chunk_str)

            # start the next chunk with a bit of overlap from the tail
            # of the previous one, so boundary-straddling facts aren't lost
            overlap_sentences = []
            overlap_len = 0
            for s in reversed(current):
                if overlap_len + len(s) > overlap_chars:
                    break
                overlap_sentences.insert(0, s)
                overlap_len += len(s) + 1
            current = overlap_sentences
            current_len = overlap_len

        current.append(sentence)
        current_len += sentence_len

    if current:
        chunks.append(" ".join(current))

    return chunks


def chunk_with_metadata(text, source, max_chars=600, overlap_chars=100):
    """
    Like chunk_text(), but returns a list of dicts with metadata,
    convenient for feeding straight into a vector store:
        [{"text": "...", "source": source, "chunk_index": 0}, ...]
    """
    pieces = chunk_text(text, max_chars=max_chars, overlap_chars=overlap_chars)
    return [
        {"text": piece, "source": source, "chunk_index": i}
        for i, piece in enumerate(pieces)
    ]
