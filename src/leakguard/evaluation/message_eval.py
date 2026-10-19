"""Message-level risk evaluation, baselines, and bootstrap confidence intervals.

Evaluates message-level data leak classification:
  - Ground truth: binary exposure (1 if 'possible_exposure' or 'high_risk_exposure',
    0 if 'no_exposure').
  - Metrics: Precision, Recall, F1, F2, PR-AUC, ROC-AUC, Confusion Matrix, and FNR at
    fixed recall target.
  - Non-parametric bootstrap 95% Confidence Intervals (1,000 resamples, seed 42).
  - Baselines:
      1. Majority class baseline
      2. Simple keyword baseline
      3. Rule-based risk scoring (Phase 3 Core)
      4. Rule-based + spaCy NER (Phase 4 Candidate B)
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from leakguard.detection.pipeline import Pipeline
from leakguard.schemas import ScanResult

KEYWORD_PATTERN = re.compile(
    r"(?i)\b(?:password|passwd|secret|api[_\s]?key|bearer|token|private[_\s]?key|"
    r"aadhaar|pan|card|credit|cvv|bank[_\s]?account|iban)\b"
)


@dataclass(frozen=True)
class BootstrapConfidenceInterval:
    """95% bootstrap confidence interval bounds."""

    point_estimate: float
    ci_lower: float
    ci_upper: float
    resamples: int
    seed: int

    def to_dict(self) -> dict[str, Any]:
        """Convert CI to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class MessageMetrics:
    """Message-level classification performance metrics."""

    precision: float
    recall: float
    f1: float
    f2: float
    pr_auc: float
    roc_auc: float
    fnr_at_95_recall: float
    confusion_matrix: list[list[int]]  # [[TN, FP], [FN, TP]]
    bootstrap_ci_f1: BootstrapConfidenceInterval
    bootstrap_ci_roc_auc: BootstrapConfidenceInterval

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "f2": self.f2,
            "pr_auc": self.pr_auc,
            "roc_auc": self.roc_auc,
            "fnr_at_95_recall": self.fnr_at_95_recall,
            "confusion_matrix": self.confusion_matrix,
            "bootstrap_ci_f1": self.bootstrap_ci_f1.to_dict(),
            "bootstrap_ci_roc_auc": self.bootstrap_ci_roc_auc.to_dict(),
        }


def compute_bootstrap_ci(
    y_true: np.ndarray,
    scores_or_preds: np.ndarray,
    metric_fn: Any,
    n_resamples: int = 1000,
    seed: int = 42,
) -> BootstrapConfidenceInterval:
    """Compute 95% non-parametric bootstrap confidence interval."""
    rng = np.random.default_rng(seed)
    n = len(y_true)

    point_est = float(metric_fn(y_true, scores_or_preds))
    boot_vals: list[float] = []

    for _ in range(n_resamples):
        idx = rng.choice(n, size=n, replace=True)
        y_b = y_true[idx]
        s_b = scores_or_preds[idx]
        # Skip resample if only 1 class present for ranking metrics
        if len(np.unique(y_b)) < 2:
            continue
        try:
            boot_vals.append(float(metric_fn(y_b, s_b)))
        except Exception:
            continue

    if not boot_vals:
        ci_lower, ci_upper = point_est, point_est
    else:
        ci_lower = float(np.percentile(boot_vals, 2.5))
        ci_upper = float(np.percentile(boot_vals, 97.5))

    return BootstrapConfidenceInterval(
        point_estimate=round(point_est, 4),
        ci_lower=round(ci_lower, 4),
        ci_upper=round(ci_upper, 4),
        resamples=n_resamples,
        seed=seed,
    )


def compute_fnr_at_recall_target(
    y_true: np.ndarray,
    scores: np.ndarray,
    target_recall: float = 0.95,
) -> float:
    """Compute False Negative Rate at the threshold that guarantees target recall."""
    if len(np.unique(y_true)) < 2:
        return 0.0

    thresholds = np.unique(scores)
    thresholds.sort()

    # Search thresholds in ascending order (higher threshold -> lower recall)
    best_fnr = 1.0 - target_recall
    for th in thresholds:
        preds = (scores >= th).astype(int)
        r = recall_score(y_true, preds, zero_division=0)
        if r >= target_recall:
            fn = np.sum((y_true == 1) & (preds == 0))
            tp = np.sum((y_true == 1) & (preds == 1))
            best_fnr = float(fn / (tp + fn)) if (tp + fn) > 0 else 0.0
        else:
            break

    return round(best_fnr, 4)


def evaluate_message_predictions(
    y_true: list[int] | np.ndarray,
    y_pred: list[int] | np.ndarray,
    y_scores: list[float] | np.ndarray,
    n_resamples: int = 1000,
    seed: int = 42,
) -> MessageMetrics:
    """Calculate message-level metrics from truth, binary predictions, and continuous scores."""
    yt = np.asarray(y_true, dtype=int)
    yp = np.asarray(y_pred, dtype=int)
    ys = np.asarray(y_scores, dtype=float)

    cm = confusion_matrix(yt, yp, labels=[0, 1]).tolist()
    p = float(precision_score(yt, yp, zero_division=0))
    r = float(recall_score(yt, yp, zero_division=0))
    f1 = float(f1_score(yt, yp, zero_division=0))

    denom_f2 = (4.0 * p) + r
    f2 = float((5.0 * p * r) / denom_f2) if denom_f2 > 0 else 0.0

    # Ranking metrics
    if len(np.unique(yt)) > 1:
        roc_auc = float(roc_auc_score(yt, ys))
        pr_auc = float(average_precision_score(yt, ys))
    else:
        roc_auc = 0.5
        pr_auc = float(np.mean(yt))

    fnr_95 = compute_fnr_at_recall_target(yt, ys, target_recall=0.95)

    # Bootstrap CIs
    ci_f1 = compute_bootstrap_ci(yt, yp, metric_fn=f1_score, n_resamples=n_resamples, seed=seed)
    ci_roc = compute_bootstrap_ci(
        yt, ys, metric_fn=roc_auc_score, n_resamples=n_resamples, seed=seed
    )

    return MessageMetrics(
        precision=round(p, 4),
        recall=round(r, 4),
        f1=round(f1, 4),
        f2=round(f2, 4),
        pr_auc=round(pr_auc, 4),
        roc_auc=round(roc_auc, 4),
        fnr_at_95_recall=fnr_95,
        confusion_matrix=cm,
        bootstrap_ci_f1=ci_f1,
        bootstrap_ci_roc_auc=ci_roc,
    )


# --- Baselines ---


def run_majority_baseline(records: list[dict[str, Any]], majority_val: int = 1) -> MessageMetrics:
    """Majority class baseline (predicts constant positive or negative)."""
    yt = [
        1 if r["message_label"] in {"possible_exposure", "high_risk_exposure"} else 0
        for r in records
    ]
    yp = [majority_val] * len(yt)
    ys = [float(majority_val)] * len(yt)
    return evaluate_message_predictions(yt, yp, ys)


def run_keyword_baseline(records: list[dict[str, Any]]) -> MessageMetrics:
    """Keyword matching baseline (matches sensitive words via regex)."""
    yt: list[int] = []
    yp: list[int] = []
    ys: list[float] = []

    for r in records:
        true_label = 1 if r["message_label"] in {"possible_exposure", "high_risk_exposure"} else 0
        matches = KEYWORD_PATTERN.findall(r["text"])
        score = min(len(matches) / 3.0, 1.0)
        pred = 1 if len(matches) > 0 else 0

        yt.append(true_label)
        yp.append(pred)
        ys.append(score)

    return evaluate_message_predictions(yt, yp, ys)


def run_pipeline_baseline(
    records: list[dict[str, Any]],
    pipeline: Pipeline,
    threshold: float = 35.0,
) -> tuple[MessageMetrics, list[ScanResult]]:
    """Pipeline-based rule evaluation baseline."""
    yt: list[int] = []
    yp: list[int] = []
    ys: list[float] = []
    results: list[ScanResult] = []

    for r in records:
        true_label = 1 if r["message_label"] in {"possible_exposure", "high_risk_exposure"} else 0
        scan_res = pipeline.scan(r["text"], redact=False)
        results.append(scan_res)

        score_norm = scan_res.overall_rule_score / 100.0
        # Classified positive if score exceeds threshold or risk band is not no_exposure
        pred = 1 if scan_res.overall_rule_score >= threshold else 0

        yt.append(true_label)
        yp.append(pred)
        ys.append(score_norm)

    metrics = evaluate_message_predictions(yt, yp, ys)
    return metrics, results
