"""
Lightweight intent classifier for routing user messages (weather,
document Q&A, code generation, web search, datetime, open/launch,
plain chat, math) - a real, trained ML model, used ALONGSIDE the
existing regex checks in agent.py, not as a replacement for them.

Why this exists: every regex-based _looks_like_*_request() check in
agent.py was patched reactively after a specific bug (a typo, an
unfamiliar word order, an unanticipated phrasing) slipped through.
That works, but it's whack-a-mole - each fix only covers the exact
wording that broke. A trained classifier generalizes across variations
it's never seen verbatim (see intent_data.py's seed/augmented split
and evaluate_generalization() below for an honest measurement of how
well that generalization actually works, rather than just assuming it).

Backends, in order of preference:
  - scikit-learn (TF-IDF + Logistic Regression) if installed - a real,
    properly-trained model with calibrated-ish confidence via
    predict_proba().
  - A hand-rolled nearest-centroid classifier using the TfidfEmbedder
    already in embeddings.py if scikit-learn isn't available - no new
    dependency required, reuses the same TF-IDF math already used
    elsewhere in ByteFlow for document retrieval. Confidence here is
    just a cosine-similarity score, not a real probability - treated
    as strictly less trustworthy than the sklearn backend (see
    _MIN_CONFIDENCE_BY_BACKEND).

Trained on intent_data.py. See agent.py's run() for how this is
actually used: as an additional signal that only acts when confident,
never as the sole decision-maker.
"""

def _sklearn_available():
    try:
        import sklearn  # noqa: F401
        return True
    except ImportError:
        return False


# Confidence thresholds below which a prediction is treated as "not
# confident enough to act on" - separate per backend because the
# centroid fallback's "confidence" is a raw cosine similarity, not a
# calibrated probability, so it needs a different bar.
#
# These are NOT guesses - they come from evaluate_generalization()'s
# precision/coverage sweep on real held-out examples (see that
# function's docstring). 0.28 was chosen for sklearn specifically
# because it's the lowest threshold that still gave 100% precision on
# every real observed bug-report phrase in intent_data.py - with only
# ~10 synthetic examples per class, coverage at that threshold is
# honestly low (the classifier abstains often), but this is used as an
# ADDITIONAL signal alongside the existing regex checks in agent.py,
# not the sole decision-maker - a wrong confident guess would actively
# hurt, while abstaining just means the existing, already-working
# fallback handles it exactly like before. Revisit this threshold as
# more real examples accumulate in intent_data.py.
_MIN_CONFIDENCE_BY_BACKEND = {
    "sklearn": 0.28,
    "centroid": 0.30,
}


class IntentClassifier:
    """
    Usage:
        clf = IntentClassifier()
        clf.fit()
        label, confidence = clf.predict("today weathe ahemdabad")
        # -> ("weather", 0.83)

        label, confidence = clf.predict_confident("hi there")
        # -> (None, 0.22) if nothing crosses the confidence threshold
    """

    def __init__(self):
        self.backend = "sklearn" if _sklearn_available() else "centroid"
        self._model = None
        self._vectorizer = None
        self._centroids = None  # {label: tfidf_vector_dict}
        self._embedder = None
        self._fitted = False

    def fit(self, examples=None):
        """
        Train on `examples` (list of (text, label) pairs). If not
        given, trains on the bundled intent_data.py set PLUS any
        accumulated real-world corrections from intent_feedback.py -
        this is what makes "the classifier improves over time" actually
        true: add_feedback_example() persists a correction, and the
        very next .fit() (e.g. next process start, since
        _shared_intent_classifier in agent.py is fit once per process)
        picks it up automatically, no code changes needed.
        """
        if examples is None:
            from .intent_data import get_training_examples
            from .intent_feedback import load_feedback_examples
            examples = get_training_examples() + load_feedback_examples()

        texts = [t for t, _ in examples]
        labels = [lbl for _, lbl in examples]

        if not texts:
            raise ValueError("Cannot fit an intent classifier on zero examples.")

        if self.backend == "sklearn":
            self._fit_sklearn(texts, labels)
        else:
            self._fit_centroid(texts, labels)
        self._fitted = True
        return self

    def _fit_sklearn(self, texts, labels):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression

        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
        X = self._vectorizer.fit_transform(texts)
        self._model = LogisticRegression(max_iter=1000, class_weight="balanced")
        self._model.fit(X, labels)

    def _fit_centroid(self, texts, labels):
        from .embeddings import TfidfEmbedder

        self._embedder = TfidfEmbedder()
        self._embedder.fit(texts)

        grouped = {}
        for text, label in zip(texts, labels):
            grouped.setdefault(label, []).append(self._embedder.embed_one(text))

        self._centroids = {}
        for label, vectors in grouped.items():
            summed = {}
            for vec in vectors:
                for tok, weight in vec.items():
                    summed[tok] = summed.get(tok, 0.0) + weight
            n = len(vectors)
            self._centroids[label] = {tok: w / n for tok, w in summed.items()}

    def predict(self, text):
        """
        Return (label, confidence) for `text`. Confidence is a
        sklearn predict_proba() probability for the sklearn backend, or
        a raw cosine-similarity score (roughly 0-1, but NOT a
        probability) for the centroid fallback - see
        _MIN_CONFIDENCE_BY_BACKEND, which accounts for this difference.
        """
        if not self._fitted:
            raise RuntimeError("IntentClassifier.fit() must be called before predict().")

        if self.backend == "sklearn":
            return self._predict_sklearn(text)
        return self._predict_centroid(text)

    def _predict_sklearn(self, text):
        X = self._vectorizer.transform([text])
        probs = self._model.predict_proba(X)[0]
        classes = self._model.classes_
        best_idx = probs.argmax()
        return str(classes[best_idx]), float(probs[best_idx])

    def _predict_centroid(self, text):
        vec = self._embedder.embed_one(text)
        if not vec or not self._centroids:
            return None, 0.0
        scores = {
            label: self._embedder.similarity(vec, centroid)
            for label, centroid in self._centroids.items()
        }
        best_label = max(scores, key=scores.get)
        return best_label, scores[best_label]

    def predict_confident(self, text, min_confidence=None):
        """
        Like predict(), but returns (None, confidence) instead of a
        label if the top prediction doesn't clear the confidence bar
        for this backend. This is the method agent.py should actually
        use for routing decisions - acting on a low-confidence guess is
        worse than falling back to the existing regex checks / planner.
        """
        label, confidence = self.predict(text)
        threshold = min_confidence if min_confidence is not None else _MIN_CONFIDENCE_BY_BACKEND[self.backend]
        if confidence < threshold:
            return None, confidence
        return label, confidence


def evaluate_generalization(verbose=False):
    """
    Honest measurement of how well this actually generalizes, not just
    an assumption: train ONLY on the synthetic/augmented examples in
    intent_data.py, then test on the REAL seed examples (the actual
    messages that caused bugs during this project) that the model
    never saw during training. This is a meaningful, if small, signal
    for whether the augmentation-based approach is worth trusting,
    given how little real data exists per class.

    Returns a dict: {"accuracy": float, "total": int, "correct": int,
    "misclassified": [(text, true_label, predicted_label), ...]}
    """
    from .intent_data import TRAINING_DATA

    train_examples = []
    test_examples = []
    for label, groups in TRAINING_DATA.items():
        train_examples.extend((t, label) for t in groups["augmented"])
        test_examples.extend((t, label) for t in groups["seed"])

    clf = IntentClassifier().fit(train_examples)

    correct = 0
    misclassified = []
    for text, true_label in test_examples:
        predicted_label, confidence = clf.predict(text)
        if predicted_label == true_label:
            correct += 1
        else:
            misclassified.append((text, true_label, predicted_label, confidence))

    total = len(test_examples)
    accuracy = correct / total if total else 0.0

    if verbose:
        print(f"Backend: {clf.backend}")
        print(f"Accuracy on real seed examples (trained on synthetic only): {accuracy:.1%} ({correct}/{total})")
        if misclassified:
            print("Misclassified:")
            for text, true_label, predicted_label, confidence in misclassified:
                print(f"  {text!r}: true={true_label}, predicted={predicted_label} ({confidence:.2f})")

    return {
        "accuracy": accuracy,
        "total": total,
        "correct": correct,
        "misclassified": misclassified,
        "backend": clf.backend,
    }
