"""
Growing feedback store for the intent classifier: real (text, label)
examples added after the fact - typically because the classifier
abstained or guessed wrong on something real, and a person confirmed
what the correct label actually was.

Kept as a separate, append-only JSON file rather than editing
intent_data.py directly, for a few reasons:
  - intent_data.py's seed/augmented split documents what's REAL
    observed-bug data vs synthetic filler; mixing in later corrections
    would blur that distinction.
  - This file is per-installation state (like memory.json), not part
    of the shipped codebase - it lives in ~/.byteflow/ alongside the
    conversation memory and profile facts, not inside the package.
  - Corrections can be reviewed/pruned independently of the curated
    training set (see list_feedback_examples() / clear_feedback()).

IntentClassifier.fit() (see intent_classifier.py) automatically merges
these in alongside intent_data.py's bundled examples, so adding a
correction here is enough to improve the next retrain - no code
changes needed.
"""

import json
import os

from .intent_data import LABELS


def _default_feedback_path():
    return os.path.join(os.path.expanduser("~"), ".byteflow", "intent_feedback.json")


def add_feedback_example(text, label, path=None):
    """
    Record a real (text, label) correction for future retraining.

    Raises ValueError if `label` isn't one of intent_data.py's known
    LABELS - catches a typo'd label at the point of entry rather than
    silently creating a new, effectively-unused class later.
    """
    text = text.strip()
    label = label.strip().lower()

    if not text:
        raise ValueError("Cannot add an empty example.")
    if label not in LABELS:
        raise ValueError(f"Unknown label {label!r}. Known labels: {', '.join(LABELS)}")

    path = path or _default_feedback_path()
    examples = _load_raw(path)
    examples.append({"text": text, "label": label})

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(examples, f, indent=2)

    return len(examples)


def load_feedback_examples(path=None):
    """Return accumulated feedback as (text, label) pairs, ready to
    concatenate with intent_data.get_training_examples()."""
    path = path or _default_feedback_path()
    return [(e["text"], e["label"]) for e in _load_raw(path)]


def _load_raw(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return [e for e in data if isinstance(e, dict) and "text" in e and "label" in e]
    except (json.JSONDecodeError, OSError):
        # A corrupt feedback file should degrade to "no feedback yet",
        # never crash training - same philosophy as memory.py's
        # handling of a corrupt memory.json.
        return []


def clear_feedback(path=None):
    """Delete all accumulated feedback examples. Does not touch the
    curated seed/augmented data in intent_data.py."""
    path = path or _default_feedback_path()
    if os.path.exists(path):
        os.remove(path)
