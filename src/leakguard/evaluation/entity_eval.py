"""Entity-level evaluation metrics and error gallery extraction for LEAKGUARD.

Computes exact and relaxed span matching metrics:
  - Exact match: label matches AND start/end offsets align identically.
  - Relaxed match: label matches AND spans overlap by at least 1 character.
  - Per-type and Micro/Macro aggregated Precision, Recall, F1, and F2.
  - FP / FN galleries extracting false positive and false negative examples for error analysis.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any

from leakguard.schemas import Finding


@dataclass(frozen=True)
class EntityMetrics:
    """Evaluation metrics for a specific entity type or aggregate."""

    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    f2: float

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to serializable dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class ErrorGalleryItem:
    """An individual false positive or false negative span for error analysis."""

    sample_id: str
    error_type: str  # "FP" or "FN"
    entity_type: str
    start: int
    end: int
    text_snippet: str
    rationale: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert error item to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class EntityEvalResult:
    """Comprehensive entity evaluation outcome."""

    exact_by_type: dict[str, EntityMetrics]
    relaxed_by_type: dict[str, EntityMetrics]
    exact_micro: EntityMetrics
    exact_macro: EntityMetrics
    relaxed_micro: EntityMetrics
    relaxed_macro: EntityMetrics
    fp_gallery: list[ErrorGalleryItem]
    fn_gallery: list[ErrorGalleryItem]

    def to_dict(self) -> dict[str, Any]:
        """Convert evaluation results to dictionary."""
        return {
            "exact_micro": self.exact_micro.to_dict(),
            "exact_macro": self.exact_macro.to_dict(),
            "exact_by_type": {k: v.to_dict() for k, v in self.exact_by_type.items()},
            "relaxed_micro": self.relaxed_micro.to_dict(),
            "relaxed_macro": self.relaxed_macro.to_dict(),
            "relaxed_by_type": {k: v.to_dict() for k, v in self.relaxed_by_type.items()},
            "fp_gallery": [item.to_dict() for item in self.fp_gallery],
            "fn_gallery": [item.to_dict() for item in self.fn_gallery],
        }


def compute_metrics_from_counts(tp: int, fp: int, fn: int) -> EntityMetrics:
    """Compute precision, recall, F1, and F2 from TP, FP, FN counts."""
    p_denom = tp + fp
    precision = tp / p_denom if p_denom > 0 else 0.0

    r_denom = tp + fn
    recall = tp / r_denom if r_denom > 0 else 0.0

    f1_denom = precision + recall
    f1 = (2.0 * precision * recall) / f1_denom if f1_denom > 0 else 0.0

    f2_denom = (4.0 * precision) + recall
    f2 = (5.0 * precision * recall) / f2_denom if f2_denom > 0 else 0.0

    return EntityMetrics(
        tp=tp,
        fp=fp,
        fn=fn,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        f2=round(f2, 4),
    )


def compute_macro_average(metrics_by_type: dict[str, EntityMetrics]) -> EntityMetrics:
    """Compute unweighted macro average across entity types."""
    if not metrics_by_type:
        return compute_metrics_from_counts(0, 0, 0)

    n = len(metrics_by_type)
    avg_p = sum(m.precision for m in metrics_by_type.values()) / n
    avg_r = sum(m.recall for m in metrics_by_type.values()) / n
    avg_f1 = sum(m.f1 for m in metrics_by_type.values()) / n
    avg_f2 = sum(m.f2 for m in metrics_by_type.values()) / n

    total_tp = sum(m.tp for m in metrics_by_type.values())
    total_fp = sum(m.fp for m in metrics_by_type.values())
    total_fn = sum(m.fn for m in metrics_by_type.values())

    return EntityMetrics(
        tp=total_tp,
        fp=total_fp,
        fn=total_fn,
        precision=round(avg_p, 4),
        recall=round(avg_r, 4),
        f1=round(avg_f1, 4),
        f2=round(avg_f2, 4),
    )


def evaluate_dataset_entities(
    records: list[dict[str, Any]],
    predictions_list: list[list[Finding]],
    max_gallery_items: int = 25,
) -> EntityEvalResult:
    """Evaluate entity extraction across an entire dataset of records.

    Args:
        records: Ground truth records containing 'id', 'text', and 'entities'.
        predictions_list: Parallel list of predicted Finding objects per record.
        max_gallery_items: Maximum number of error examples to capture in gallery.
    """
    if len(records) != len(predictions_list):
        raise ValueError("Length of records and predictions_list must match exactly")

    exact_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])  # [tp, fp, fn]
    relaxed_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])

    fp_gallery: list[ErrorGalleryItem] = []
    fn_gallery: list[ErrorGalleryItem] = []

    for rec, preds in zip(records, predictions_list, strict=True):
        sample_id = rec.get("id", "unknown_id")
        text = rec["text"]
        gt_entities = rec.get("entities", [])

        # Collect all unique labels present in GT or Predictions for this record
        record_labels = {g["label"] for g in gt_entities} | {p.entity_type for p in preds}

        for label in record_labels:
            gt_label = [g for g in gt_entities if g["label"] == label]
            pred_label = [p for p in preds if p.entity_type == label]

            # 1. Exact Matching
            matched_gt_exact: set[int] = set()
            matched_pred_exact: set[int] = set()

            for p_idx, p in enumerate(pred_label):
                for g_idx, g in enumerate(gt_label):
                    if g_idx in matched_gt_exact:
                        continue
                    if p.start == g["start"] and p.end == g["end"]:
                        matched_gt_exact.add(g_idx)
                        matched_pred_exact.add(p_idx)
                        break

            tp_exact = len(matched_gt_exact)
            fp_exact = len(pred_label) - tp_exact
            fn_exact = len(gt_label) - tp_exact

            exact_counts[label][0] += tp_exact
            exact_counts[label][1] += fp_exact
            exact_counts[label][2] += fn_exact

            # Error gallery extraction (exact mismatch)
            for p_idx, p in enumerate(pred_label):
                if p_idx not in matched_pred_exact and len(fp_gallery) < max_gallery_items:
                    snippet = text[max(0, p.start - 15) : min(len(text), p.end + 15)]
                    fp_gallery.append(
                        ErrorGalleryItem(
                            sample_id=sample_id,
                            error_type="FP",
                            entity_type=p.entity_type,
                            start=p.start,
                            end=p.end,
                            text_snippet=snippet,
                            rationale=p.rationale,
                        )
                    )

            for g_idx, g in enumerate(gt_label):
                if g_idx not in matched_gt_exact and len(fn_gallery) < max_gallery_items:
                    snippet = text[max(0, g["start"] - 15) : min(len(text), g["end"] + 15)]
                    fn_gallery.append(
                        ErrorGalleryItem(
                            sample_id=sample_id,
                            error_type="FN",
                            entity_type=g["label"],
                            start=g["start"],
                            end=g["end"],
                            text_snippet=snippet,
                            rationale=f"Ground truth value: {g.get('value', '')}",
                        )
                    )

            # 2. Relaxed Matching (positive overlap)
            matched_gt_rel: set[int] = set()
            matched_pred_rel: set[int] = set()

            for p_idx, p in enumerate(pred_label):
                for g_idx, g in enumerate(gt_label):
                    if g_idx in matched_gt_rel:
                        continue
                    if max(p.start, g["start"]) < min(p.end, g["end"]):
                        matched_gt_rel.add(g_idx)
                        matched_pred_rel.add(p_idx)
                        break

            tp_rel = len(matched_gt_rel)
            fp_rel = len(pred_label) - tp_rel
            fn_rel = len(gt_label) - tp_rel

            relaxed_counts[label][0] += tp_rel
            relaxed_counts[label][1] += fp_rel
            relaxed_counts[label][2] += fn_rel

    # Compute per-type and micro/macro summaries
    exact_by_type = {
        label: compute_metrics_from_counts(c[0], c[1], c[2]) for label, c in exact_counts.items()
    }
    relaxed_by_type = {
        label: compute_metrics_from_counts(c[0], c[1], c[2]) for label, c in relaxed_counts.items()
    }

    total_exact_tp = sum(c[0] for c in exact_counts.values())
    total_exact_fp = sum(c[1] for c in exact_counts.values())
    total_exact_fn = sum(c[2] for c in exact_counts.values())
    exact_micro = compute_metrics_from_counts(total_exact_tp, total_exact_fp, total_exact_fn)
    exact_macro = compute_macro_average(exact_by_type)

    total_rel_tp = sum(c[0] for c in relaxed_counts.values())
    total_rel_fp = sum(c[1] for c in relaxed_counts.values())
    total_rel_fn = sum(c[2] for c in relaxed_counts.values())
    relaxed_micro = compute_metrics_from_counts(total_rel_tp, total_rel_fp, total_rel_fn)
    relaxed_macro = compute_macro_average(relaxed_by_type)

    return EntityEvalResult(
        exact_by_type=exact_by_type,
        relaxed_by_type=relaxed_by_type,
        exact_micro=exact_micro,
        exact_macro=exact_macro,
        relaxed_micro=relaxed_micro,
        relaxed_macro=relaxed_macro,
        fp_gallery=fp_gallery,
        fn_gallery=fn_gallery,
    )
