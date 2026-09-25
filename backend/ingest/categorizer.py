"""Transaction category baseline — TF-IDF + LR when sklearn is present, else keywords."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

_SKLEARN_AVAILABLE = False
try:
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    from sklearn.linear_model import LogisticRegression  # type: ignore
    from sklearn.pipeline import Pipeline  # type: ignore

    _SKLEARN_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dep
    TfidfVectorizer = None  # type: ignore[misc, assignment]
    LogisticRegression = None  # type: ignore[misc, assignment]
    Pipeline = None  # type: ignore[misc, assignment]


# Keyword rules used when sklearn is unavailable (and as cold-start fallback).
_KEYWORD_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Groceries", ("loblaws", "metro", "no frills", "costco", "walmart", "freshco", "sobeys")),
    ("Dining", ("tim hortons", "starbucks", "uber eats", "doordash", "mcdonald", "restaurant", "sushi", "pizza", "chipotle", "a&w", "harvey", "popeyes")),
    ("Transport", ("uber", "lyft", "presto", "shell", "esso", "petro", "gas")),
    ("Subscriptions", ("netflix", "spotify", "apple.com/bill", "disney+", "youtube premium")),
    ("Utilities", ("hydro", "enbridge", "rogers", "bell", "telus", "internet")),
    ("Rent", ("rent", "landlord", "property management")),
    ("Income", ("payroll", "salary", "direct deposit", "wage")),
    ("Transfers", ("interac", "e-transfer", "transfer")),
    ("Bank Fees", ("nsf", "service charge", "atm fee", "overdraft")),
]


@dataclass
class CategorizerMetrics:
    accuracy: float
    macro_f1: float
    n_train: int
    n_test: int
    backend: str
    per_class: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accuracy": self.accuracy,
            "macro_f1": self.macro_f1,
            "n_train": self.n_train,
            "n_test": self.n_test,
            "backend": self.backend,
            "per_class": dict(self.per_class),
        }


def _text(description: str, merchant: str | None = None) -> str:
    parts = [description or ""]
    if merchant:
        parts.append(merchant)
    return " ".join(parts).strip().lower()


def categorize_keywords(description: str, merchant: str | None = None) -> str:
    """Simple keyword fallback categorizer."""
    hay = _text(description, merchant)
    for category, needles in _KEYWORD_RULES:
        for needle in needles:
            if needle in hay:
                return category
    return "Uncategorized"


class TransactionCategorizer:
    """Baseline categorizer. Prefers sklearn TF-IDF + LogisticRegression when installed."""

    def __init__(self) -> None:
        self._pipeline: Any = None
        self.backend = "keywords"

    @property
    def sklearn_available(self) -> bool:
        return _SKLEARN_AVAILABLE

    def fit(self, texts: Sequence[str], labels: Sequence[str]) -> TransactionCategorizer:
        if not texts or not labels or len(texts) != len(labels):
            raise ValueError("texts and labels must be non-empty and equal length")
        if _SKLEARN_AVAILABLE:
            self._pipeline = Pipeline(
                [
                    ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
                    (
                        "clf",
                        LogisticRegression(max_iter=500, solver="lbfgs", multi_class="auto"),
                    ),
                ]
            )
            self._pipeline.fit(list(texts), list(labels))
            self.backend = "tfidf_logreg"
        else:
            self._pipeline = None
            self.backend = "keywords"
        return self

    def predict(self, description: str, merchant: str | None = None) -> str:
        text = _text(description, merchant)
        if self._pipeline is not None:
            return str(self._pipeline.predict([text])[0])
        return categorize_keywords(description, merchant)

    def predict_many(self, items: Sequence[tuple[str, str | None]]) -> list[str]:
        return [self.predict(d, m) for d, m in items]


def _macro_f1(y_true: Sequence[str], y_pred: Sequence[str]) -> tuple[float, dict[str, float]]:
    labels = sorted(set(y_true) | set(y_pred))
    f1s: dict[str, float] = {}
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1s[label] = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
    macro = sum(f1s.values()) / len(f1s) if f1s else 0.0
    return macro, f1s


def train_and_evaluate(
    examples: Sequence[tuple[str, str, str | None]] | None = None,
) -> CategorizerMetrics:
    """Train on a tiny synthetic set and return placeholder metrics.

    Each example is ``(label, description, merchant)``.
    """
    if examples is None:
        examples = _SYNTHETIC_TRAIN

    # Hold out last 20% (min 1) for a tiny eval split
    n = len(examples)
    n_test = max(1, n // 5)
    n_train = n - n_test
    train, test = examples[:n_train], examples[n_train:]

    texts = [_text(d, m) for _, d, m in train]
    labels = [lab for lab, _, _ in train]
    clf = TransactionCategorizer().fit(texts, labels)

    y_true = [lab for lab, _, _ in test]
    y_pred = [clf.predict(d, m) for _, d, m in test]
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    acc = correct / len(y_true) if y_true else 0.0
    macro, per_class = _macro_f1(y_true, y_pred)
    return CategorizerMetrics(
        accuracy=round(acc, 4),
        macro_f1=round(macro, 4),
        n_train=n_train,
        n_test=len(test),
        backend=clf.backend,
        per_class={k: round(v, 4) for k, v in per_class.items()},
    )


def categorize(description: str, merchant: str | None = None) -> str:
    """One-shot categorize using keyword rules (no fitted model required)."""
    return categorize_keywords(description, merchant)


_SYNTHETIC_TRAIN: list[tuple[str, str, str | None]] = [
    ("Groceries", "POS LOBLAWS #1234 TORONTO ON", "Loblaws"),
    ("Groceries", "METRO #8821", "Metro"),
    ("Groceries", "NO FRILLS STORE 4512", "No Frills"),
    ("Dining", "TIM HORTONS #5678", "Tim Hortons"),
    ("Dining", "SQ *STARBUCKS COFFEE", "Starbucks"),
    ("Dining", "UBER EATS TORONTO", "Uber Eats"),
    ("Transport", "UBER TRIP", "Uber"),
    ("Transport", "SHELL GAS STATION", "Shell"),
    ("Subscriptions", "NETFLIX.COM", "Netflix"),
    ("Subscriptions", "SPOTIFY P22A1", "Spotify"),
    ("Utilities", "ROGERS INTERNET", "Rogers"),
    ("Utilities", "TORONTO HYDRO", "Toronto Hydro"),
    ("Income", "PAYROLL DEPOSIT ACME INC", None),
    ("Income", "DIRECT DEPOSIT SALARY", None),
    ("Bank Fees", "NSF FEE", None),
    ("Bank Fees", "ATM FEE WITHDRAWAL", None),
    ("Transfers", "INTERAC E-TRANSFER SENT", None),
    ("Rent", "INTERAC RENT PAYMENT", None),
    ("Dining", "MCDONALDS RESTAURANT", "McDonalds"),
    ("Groceries", "COSTCO WHOLESALE", "Costco"),
]
