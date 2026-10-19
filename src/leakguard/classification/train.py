"""Machine learning text classification experiment for LEAKGUARD data leak detection.

Trains and evaluates TF-IDF + LogisticRegression linear classifiers:
  1. Word n-gram variant: TF-IDF (1, 2)-grams + LogisticRegression.
  2. Character n-gram variant: TF-IDF char_wb (3, 5)-grams + LogisticRegression.

Methodological Guarantees:
  - Vectorizer fit strictly on training split only.
  - Hyperparameters (C) and decision threshold tuned on validation split only.
  - Held-out test split evaluated strictly once.
  - Challenge set evaluated without tuning.
  - Ship gate enforced: shipped only if model beats rule baseline on human challenge set.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline as SklearnPipeline

from leakguard.evaluation.message_eval import evaluate_message_predictions


@dataclass(frozen=True)
class ModelExperimentResult:
    """Outcome of training and evaluating a classifier candidate."""

    model_name: str
    variant: str
    best_c: float
    best_threshold: float
    val_metrics: dict[str, Any]
    test_metrics: dict[str, Any]
    challenge_metrics: str | dict[str, Any]
    shipped: bool
    rejection_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return asdict(self)


def load_dataset_split(path: str | Path) -> tuple[list[str], list[int], list[dict[str, Any]]]:
    """Load texts, binary labels (1=leak exposure, 0=no exposure), and raw dicts."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Dataset split not found at: {path}")

    texts: list[str] = []
    labels: list[int] = []
    records: list[dict[str, Any]] = []

    with open(p, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            is_leak = (
                1 if rec.get("message_label") in {"possible_exposure", "high_risk_exposure"} else 0
            )
            texts.append(rec["text"])
            labels.append(is_leak)
            records.append(rec)

    return texts, labels, records


def train_and_tune_model(
    train_texts: list[str],
    train_labels: list[int],
    val_texts: list[str],
    val_labels: list[int],
    variant: str = "word_ngrams",
    seed: int = 42,
) -> tuple[SklearnPipeline, float, float, dict[str, Any]]:
    """Fit vectorizer on train only, tune C and threshold on validation split."""
    c_candidates = [0.1, 1.0, 10.0]
    threshold_candidates = [0.30, 0.40, 0.50, 0.60, 0.70]

    best_f1 = -1.0
    best_c = 1.0
    best_th = 0.50
    best_pipeline: SklearnPipeline | None = None
    best_val_metrics: dict[str, Any] = {}

    for c in c_candidates:
        if variant == "word_ngrams":
            vec = TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=10000,
                sublinear_tf=True,
            )
        elif variant == "char_ngrams":
            vec = TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                max_features=15000,
                sublinear_tf=True,
            )
        else:
            raise ValueError(f"Unknown classifier variant: {variant}")

        clf = LogisticRegression(
            C=c,
            class_weight="balanced",
            random_state=seed,
            max_iter=1000,
        )

        pipe = SklearnPipeline([("tfidf", vec), ("clf", clf)])
        pipe.fit(train_texts, train_labels)

        # Tune decision threshold on validation set
        val_probs = pipe.predict_proba(val_texts)[:, 1]

        for th in threshold_candidates:
            val_preds = (val_probs >= th).astype(int)
            metrics = evaluate_message_predictions(
                val_labels, val_preds, val_probs, n_resamples=200, seed=seed
            )
            if metrics.f1 > best_f1:
                best_f1 = metrics.f1
                best_c = c
                best_th = th
                best_pipeline = pipe
                best_val_metrics = metrics.to_dict()

    if best_pipeline is None:
        raise RuntimeError("Failed to fit classification pipeline")

    return best_pipeline, best_c, best_th, best_val_metrics


def run_experiment(
    train_path: str = "data/processed/train.jsonl",
    val_path: str = "data/processed/val.jsonl",
    test_path: str = "data/processed/test.jsonl",
    challenge_path: str = "data/challenge/challenge_set.jsonl",
    seed: int = 42,
) -> dict[str, ModelExperimentResult]:
    """Train candidate models, evaluate on held-out test split, and evaluate gate
    against challenge set.
    """
    train_texts, train_labels, _ = load_dataset_split(train_path)
    val_texts, val_labels, _ = load_dataset_split(val_path)
    test_texts, test_labels, _ = load_dataset_split(test_path)

    has_challenge = Path(challenge_path).is_file()
    if has_challenge:
        ch_texts, ch_labels, _ = load_dataset_split(challenge_path)
    else:
        ch_texts, ch_labels = [], []

    results: dict[str, ModelExperimentResult] = {}
    variants = ["word_ngrams", "char_ngrams"]

    for var in variants:
        m_name = f"lr_{var}"
        pipe, best_c, best_th, val_met = train_and_tune_model(
            train_texts, train_labels, val_texts, val_labels, variant=var, seed=seed
        )

        # Single evaluation on held-out test split
        test_probs = pipe.predict_proba(test_texts)[:, 1]
        test_preds = (test_probs >= best_th).astype(int)
        test_met = evaluate_message_predictions(
            test_labels, test_preds, test_probs, n_resamples=1000, seed=seed
        ).to_dict()

        # Evaluation on challenge set (if present)
        if has_challenge and ch_texts:
            ch_probs = pipe.predict_proba(ch_texts)[:, 1]
            ch_preds = (ch_probs >= best_th).astype(int)
            ch_met: str | dict[str, Any] = evaluate_message_predictions(
                ch_labels, ch_preds, ch_probs, n_resamples=1000, seed=seed
            ).to_dict()
            shipped = False
            rejection_reason = (
                "Challenge set evaluation completed; requires CI improvement verification."
            )
        else:
            ch_met = "no challenge set yet"
            shipped = False
            rejection_reason = (
                "Human challenge benchmark set is missing in data/challenge/. "
                "Per project policy, ML models cannot ship without empirical evidence "
                "beating rule baselines on human-written data."
            )

        results[m_name] = ModelExperimentResult(
            model_name=m_name,
            variant=var,
            best_c=best_c,
            best_threshold=best_th,
            val_metrics=val_met,
            test_metrics=test_met,
            challenge_metrics=ch_met,
            shipped=shipped,
            rejection_reason=rejection_reason,
        )

    return results


if __name__ == "__main__":
    exp_res = run_experiment()
    for name, res in exp_res.items():
        print(f"\n--- {name} ---")
        print(f"Best C: {res.best_c}, Best Threshold: {res.best_threshold}")
        print(f"Val F1: {res.val_metrics['f1']}, Test F1: {res.test_metrics['f1']}")
        print(f"Challenge set: {res.challenge_metrics}")
        print(f"Shipped: {res.shipped} ({res.rejection_reason})")
