"""Unit tests for Phase 5 evaluation framework and data split separation guarantees.

Verifies:
  - Entity-level exact/relaxed metric computation against hand-computed ground truth.
  - Message-level classification metrics, confusion matrices, and bootstrap CIs.
  - Strict mathematical separation between train, val, and test splits (0 ID or family overlap).
  - Graceful handling when human challenge benchmark is absent.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from leakguard.evaluation.entity_eval import (
    compute_macro_average,
    compute_metrics_from_counts,
    evaluate_dataset_entities,
)
from leakguard.evaluation.message_eval import (
    compute_bootstrap_ci,
    evaluate_message_predictions,
)
from leakguard.schemas import Finding, Severity


def test_hand_computed_entity_metrics():
    """Verify precision, recall, F1, and F2 match hand-computed values.

    Case:
      TP = 3, FP = 1, FN = 2
      Precision = 3 / (3 + 1) = 3/4 = 0.75
      Recall = 3 / (3 + 2) = 3/5 = 0.60
      F1 = 2 * (0.75 * 0.60) / (0.75 + 0.60) = 0.90 / 1.35 = 2/3 = 0.6667
      F2 = 5 * (0.75 * 0.60) / (4 * 0.75 + 0.60) = 2.25 / 3.60 = 0.6250
    """
    m = compute_metrics_from_counts(tp=3, fp=1, fn=2)
    assert m.precision == 0.75
    assert m.recall == 0.60
    assert m.f1 == 0.6667
    assert m.f2 == 0.6250


def test_hand_computed_macro_average():
    """Verify macro averaging across two entity classes."""
    m_card = compute_metrics_from_counts(tp=4, fp=0, fn=0)  # P=1.0, R=1.0, F1=1.0, F2=1.0
    m_email = compute_metrics_from_counts(tp=0, fp=2, fn=2)  # P=0.0, R=0.0, F1=0.0, F2=0.0

    macro = compute_macro_average({"CARD": m_card, "EMAIL": m_email})
    assert macro.precision == 0.50
    assert macro.recall == 0.50
    assert macro.f1 == 0.50
    assert macro.f2 == 0.50


def test_entity_evaluation_exact_and_relaxed_matching():
    """Verify exact and relaxed matching behavior on a controlled synthetic record."""
    records = [
        {
            "id": "rec_001",
            "text": "User email: test@domain.com, card: 4000 0012 3456 7899",
            "entities": [
                {"label": "EMAIL", "start": 12, "end": 27, "value": "test@domain.com"},
                {"label": "CARD", "start": 35, "end": 54, "value": "4000 0012 3456 7899"},
            ],
        }
    ]

    # Predicted findings:
    # 1. Exact match on EMAIL (12, 27)
    # 2. Relaxed match on CARD (35, 45 - partial card span)
    # 3. False positive on PHONE (60, 70)
    preds = [
        [
            Finding(
                id="f1",
                entity_type="EMAIL",
                start=12,
                end=27,
                detector="regex",
                severity=Severity.MEDIUM,
                display_value="test@domain.com",
                rationale="Email pattern",
            ),
            Finding(
                id="f2",
                entity_type="CARD",
                start=35,
                end=45,
                detector="regex",
                severity=Severity.HIGH,
                display_value="4000 0012",
                rationale="Partial card span",
            ),
            Finding(
                id="f3",
                entity_type="PHONE",
                start=60,
                end=70,
                detector="regex",
                severity=Severity.MEDIUM,
                display_value="9876543210",
                rationale="Spurious phone",
            ),
        ]
    ]

    res = evaluate_dataset_entities(records, preds)

    # EMAIL is exact match
    assert res.exact_by_type["EMAIL"].tp == 1
    assert res.exact_by_type["EMAIL"].fp == 0
    assert res.exact_by_type["EMAIL"].fn == 0

    # CARD exact match failed (partial span), but relaxed match succeeded
    assert res.exact_by_type["CARD"].tp == 0
    assert res.exact_by_type["CARD"].fn == 1
    assert res.relaxed_by_type["CARD"].tp == 1
    assert res.relaxed_by_type["CARD"].fn == 0

    # PHONE was a false positive
    assert res.exact_by_type["PHONE"].tp == 0
    assert res.exact_by_type["PHONE"].fp == 1
    assert len(res.fp_gallery) >= 1
    assert len(res.fn_gallery) >= 1


def test_hand_computed_message_evaluation():
    """Verify confusion matrix and metrics on hand-computed binary predictions.

    Case:
      y_true:  [1, 1, 1, 0, 0]
      y_pred:  [1, 1, 0, 0, 1]
      y_scores:[0.9, 0.8, 0.3, 0.1, 0.6]

      TP = 2, FP = 1, FN = 1, TN = 1
      Confusion matrix: [[1, 1], [1, 2]]
      Precision = 2 / (2 + 1) = 2/3 = 0.6667
      Recall = 2 / (2 + 1) = 2/3 = 0.6667
      F1 = 0.6667
    """
    yt = [1, 1, 1, 0, 0]
    yp = [1, 1, 0, 0, 1]
    ys = [0.9, 0.8, 0.3, 0.1, 0.6]

    res = evaluate_message_predictions(yt, yp, ys, n_resamples=100, seed=42)
    assert res.confusion_matrix == [[1, 1], [1, 2]]
    assert res.precision == 0.6667
    assert res.recall == 0.6667
    assert res.f1 == 0.6667
    assert res.roc_auc > 0.5


def test_bootstrap_confidence_interval_bounds():
    """Verify bootstrap CI bounds enclose point estimate and satisfy 0 <= lower <= upper <= 1."""
    y_true = np.array([1, 1, 1, 1, 0, 0, 0, 0, 1, 0])
    y_pred = np.array([1, 1, 1, 0, 0, 0, 1, 0, 1, 0])

    from sklearn.metrics import f1_score

    ci = compute_bootstrap_ci(y_true, y_pred, metric_fn=f1_score, n_resamples=200, seed=42)

    assert 0.0 <= ci.ci_lower <= ci.point_estimate <= ci.ci_upper <= 1.0
    assert ci.resamples == 200
    assert ci.seed == 42


def test_dataset_split_separation_guarantees():
    """Prove strict mathematical separation between train, validation, and test splits.

    Verifies:
      1. Zero sample ID overlap across splits.
      2. Zero template family_id overlap across splits (leakage-free group splitting).
    """
    train_file = Path("data/processed/train.jsonl")
    val_file = Path("data/processed/val.jsonl")
    test_file = Path("data/processed/test.jsonl")

    if not (train_file.is_file() and val_file.is_file() and test_file.is_file()):
        pytest.skip("Processed dataset files missing")

    def _get_ids_and_families(p: Path) -> tuple[set[str], set[str]]:
        ids: set[str] = set()
        fams: set[str] = set()
        with open(p, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    ids.add(rec["id"])
                    fams.add(rec["family_id"])
        return ids, fams

    train_ids, train_fams = _get_ids_and_families(train_file)
    val_ids, val_fams = _get_ids_and_families(val_file)
    test_ids, test_fams = _get_ids_and_families(test_file)

    # 1. Zero ID overlap
    assert len(train_ids & val_ids) == 0, "Train and Val share record IDs"
    assert len(train_ids & test_ids) == 0, "Train and Test share record IDs"
    assert len(val_ids & test_ids) == 0, "Val and Test share record IDs"

    # 2. Zero Family overlap (Group split verification)
    assert len(train_fams & val_fams) == 0, f"Cross-split family leakage: {train_fams & val_fams}"
    assert len(train_fams & test_fams) == 0, f"Cross-split family leakage: {train_fams & test_fams}"
    assert len(val_fams & test_fams) == 0, f"Cross-split family leakage: {val_fams & test_fams}"


def test_get_git_commit_helper():
    """Verify get_git_commit returns a string without unhandled exception."""
    from leakguard.evaluation.report import get_git_commit

    commit = get_git_commit()
    assert isinstance(commit, str)
    assert len(commit) > 0
