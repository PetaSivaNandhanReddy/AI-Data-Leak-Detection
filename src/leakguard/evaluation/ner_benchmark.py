"""Benchmark and evaluation suite for NER adapter candidate configurations.

Evaluates 4 configurations on the held-out VALIDATION split:
  - Configuration A: Phase 3 detectors only (Regex + Secret)
  - Configuration B: A + spaCy en_core_web_sm for PERSON
  - Configuration C: A + Presidio with custom recognizers
  - Configuration D: Presidio default configuration (standalone)

Measures:
  - Entity-level exact and relaxed matching (Precision, Recall, F1, F2) per type & micro/macro
  - Model load / initialization time
  - Latency distribution (p50, p95) on 200 consecutive scans
  - Process memory footprint (baseline, peak, delta RSS) via psutil against 1 GB budget
"""

from __future__ import annotations

import json
import os
import platform
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psutil

from leakguard.detection.ner_adapter import PresidioNERAdapter, SpacyNERAdapter
from leakguard.detection.pipeline import Pipeline
from leakguard.schemas import Finding


@dataclass
class MatchCounts:
    """True positives, false positives, and false negatives for an entity class."""

    tp: int = 0
    fp: int = 0
    fn: int = 0

    def compute_metrics(self) -> dict[str, float]:
        """Compute P, R, F1, F2 from counts."""
        precision = self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 0.0
        recall = self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0.0
        denom_f1 = precision + recall
        f1 = (2.0 * precision * recall) / denom_f1 if denom_f1 > 0 else 0.0
        denom_f2 = (4.0 * precision) + recall
        f2 = (5.0 * precision * recall) / denom_f2 if denom_f2 > 0 else 0.0
        return {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "f2": round(f2, 4),
        }


def evaluate_record(
    ground_truth: list[dict[str, Any]],
    predictions: list[Finding],
    exact_counts: dict[str, MatchCounts],
    relaxed_counts: dict[str, MatchCounts],
) -> None:
    """Evaluate predictions against ground truth for a single record."""
    all_types = {g["label"] for g in ground_truth} | {p.entity_type for p in predictions}

    for t in all_types:
        gt_t = [g for g in ground_truth if g["label"] == t]
        pred_t = [p for p in predictions if p.entity_type == t]

        # 1. Exact Matching
        matched_gt_exact: set[int] = set()
        matched_pred_exact: set[int] = set()

        for p_idx, p in enumerate(pred_t):
            for g_idx, g in enumerate(gt_t):
                if g_idx in matched_gt_exact:
                    continue
                if p.start == g["start"] and p.end == g["end"]:
                    matched_gt_exact.add(g_idx)
                    matched_pred_exact.add(p_idx)
                    break

        exact_tp = len(matched_gt_exact)
        exact_fp = len(pred_t) - exact_tp
        exact_fn = len(gt_t) - exact_tp

        exact_counts[t].tp += exact_tp
        exact_counts[t].fp += exact_fp
        exact_counts[t].fn += exact_fn

        # 2. Relaxed Matching (positive character overlap)
        matched_gt_relaxed: set[int] = set()
        matched_pred_relaxed: set[int] = set()

        for p_idx, p in enumerate(pred_t):
            for g_idx, g in enumerate(gt_t):
                if g_idx in matched_gt_relaxed:
                    continue
                # Overlap exists if max(start) < min(end)
                if max(p.start, g["start"]) < min(p.end, g["end"]):
                    matched_gt_relaxed.add(g_idx)
                    matched_pred_relaxed.add(p_idx)
                    break

        relaxed_tp = len(matched_gt_relaxed)
        relaxed_fp = len(pred_t) - relaxed_tp
        relaxed_fn = len(gt_t) - relaxed_tp

        relaxed_counts[t].tp += relaxed_tp
        relaxed_counts[t].fp += relaxed_fp
        relaxed_counts[t].fn += relaxed_fn


def aggregate_macro_micro(
    counts_by_type: dict[str, MatchCounts],
) -> tuple[dict[str, float], dict[str, float]]:
    """Compute micro- and macro-averaged metrics across all entity types."""
    micro = MatchCounts()
    p_list: list[float] = []
    r_list: list[float] = []
    f1_list: list[float] = []
    f2_list: list[float] = []

    for counts in counts_by_type.values():
        micro.tp += counts.tp
        micro.fp += counts.fp
        micro.fn += counts.fn

        m = counts.compute_metrics()
        p_list.append(m["precision"])
        r_list.append(m["recall"])
        f1_list.append(m["f1"])
        f2_list.append(m["f2"])

    micro_metrics = micro.compute_metrics()

    n = max(len(p_list), 1)
    macro_metrics = {
        "precision": round(sum(p_list) / n, 4),
        "recall": round(sum(r_list) / n, 4),
        "f1": round(sum(f1_list) / n, 4),
        "f2": round(sum(f2_list) / n, 4),
    }

    return micro_metrics, macro_metrics


def run_benchmark(val_path: str = "data/processed/val.jsonl") -> dict[str, Any]:
    """Execute complete comparative benchmark on the validation split."""
    process = psutil.Process(os.getpid())
    val_file = Path(val_path)
    if not val_file.is_file():
        raise FileNotFoundError(f"Validation split file not found at: {val_path}")

    # Read validation records
    records: list[dict[str, Any]] = []
    with open(val_file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"Loaded {len(records)} validation records from {val_path}")

    # Package version introspection
    import spacy
    import spacy.util

    try:
        import presidio_analyzer

        presidio_ver = getattr(presidio_analyzer, "__version__", "2.2.364")
    except Exception:
        presidio_ver = "unavailable"

    nlp_meta = spacy.load("en_core_web_sm").meta
    model_name = nlp_meta.get("name", "core_web_sm")
    model_version = nlp_meta.get("version", "3.8.0")
    model_size_mb = 12.8  # Wheel distribution size

    # Candidate definitions
    candidates: list[dict[str, Any]] = [
        {
            "id": "config_a",
            "name": "Configuration A (Phase 3 Core Only)",
            "description": "Deterministic Regex + Secret Detector (zero NER)",
            "init_fn": lambda: Pipeline(ner_adapter=None),
            "runner_fn": lambda inst, text: inst.scan(text, redact=False).findings,
        },
        {
            "id": "config_b",
            "name": "Configuration B (Phase 3 + spaCy en_core_web_sm)",
            "description": "Phase 3 Core + spaCy small model for PERSON entities only",
            "init_fn": lambda: Pipeline(
                ner_adapter=SpacyNERAdapter("en_core_web_sm", target_labels={"PERSON"})
            ),
            "runner_fn": lambda inst, text: inst.scan(text, redact=False).findings,
        },
        {
            "id": "config_c",
            "name": "Configuration C (Phase 3 + Presidio Custom)",
            "description": "Phase 3 Core + Presidio with custom India recognizers",
            "init_fn": lambda: Pipeline(
                ner_adapter=PresidioNERAdapter(use_custom_recognizers=True)
            ),
            "runner_fn": lambda inst, text: inst.scan(text, redact=False).findings,
        },
        {
            "id": "config_d",
            "name": "Configuration D (Presidio Default Standalone)",
            "description": "Out-of-the-box Microsoft Presidio AnalyzerEngine (zero custom rules)",
            "init_fn": lambda: PresidioNERAdapter(use_custom_recognizers=False),
            "runner_fn": lambda inst, text: inst.detect(text),
        },
    ]

    benchmark_results: dict[str, Any] = {
        "metadata": {
            "date": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "spacy_version": spacy.__version__,
            "presidio_version": presidio_ver,
            "model_name": f"en_{model_name}",
            "model_version": model_version,
            "model_size_mb": model_size_mb,
            "validation_records": len(records),
            "memory_budget_mb": 1024.0,
        },
        "configurations": {},
    }

    print("\n" + "=" * 80, flush=True)
    print("STARTING CANDIDATE CONFIGURATION BENCHMARK", flush=True)
    print("=" * 80, flush=True)

    for cand in candidates:
        cid = cand["id"]
        cname = cand["name"]
        print(f"\nEvaluating: {cname} ...", flush=True)

        # 1. Measure load / init time
        baseline_rss = process.memory_info().rss / (1024 * 1024)
        t_load_start = time.perf_counter()
        instance = cand["init_fn"]()
        # Warm up adapter load
        if hasattr(instance, "ner_adapter") and instance.ner_adapter is not None:
            instance.ner_adapter.load()
        elif hasattr(instance, "load"):
            instance.load()
        load_time_ms = (time.perf_counter() - t_load_start) * 1000.0

        # 2. Measure latency on 200 consecutive scans
        scan_latencies: list[float] = []
        for i in range(min(200, len(records))):
            txt = records[i]["text"]
            t0 = time.perf_counter()
            _ = cand["runner_fn"](instance, txt)
            scan_latencies.append((time.perf_counter() - t0) * 1000.0)

        scan_latencies.sort()
        p50_lat = scan_latencies[len(scan_latencies) // 2]
        p95_lat = scan_latencies[int(len(scan_latencies) * 0.95)]

        # 3. Memory measurements
        peak_rss = process.memory_info().rss / (1024 * 1024)
        mem_delta = max(peak_rss - baseline_rss, 0.0)
        budget_pct = (peak_rss / 1024.0) * 100.0

        # 4. Accuracy evaluation over the entire validation split
        exact_counts: dict[str, MatchCounts] = defaultdict(MatchCounts)
        relaxed_counts: dict[str, MatchCounts] = defaultdict(MatchCounts)

        for rec in records:
            txt = rec["text"]
            gt = rec["entities"]
            preds = cand["runner_fn"](instance, txt)
            evaluate_record(gt, preds, exact_counts, relaxed_counts)

        # Per-type and aggregate metrics
        exact_by_type = {t: counts.compute_metrics() for t, counts in exact_counts.items()}
        relaxed_by_type = {t: counts.compute_metrics() for t, counts in relaxed_counts.items()}

        exact_micro, exact_macro = aggregate_macro_micro(exact_counts)
        relaxed_micro, relaxed_macro = aggregate_macro_micro(relaxed_counts)

        config_report = {
            "id": cid,
            "name": cname,
            "description": cand["description"],
            "performance": {
                "load_time_ms": round(load_time_ms, 2),
                "latency_p50_ms": round(p50_lat, 2),
                "latency_p95_ms": round(p95_lat, 2),
                "baseline_rss_mb": round(baseline_rss, 2),
                "peak_rss_mb": round(peak_rss, 2),
                "delta_rss_mb": round(mem_delta, 2),
                "budget_utilization_pct": round(budget_pct, 2),
            },
            "metrics": {
                "exact": {
                    "micro": exact_micro,
                    "macro": exact_macro,
                    "per_type": exact_by_type,
                },
                "relaxed": {
                    "micro": relaxed_micro,
                    "macro": relaxed_macro,
                    "per_type": relaxed_by_type,
                },
            },
        }

        benchmark_results["configurations"][cid] = config_report

        print(
            f"  -> Exact Micro F1: {exact_micro['f1']:.4f} | F2: {exact_micro['f2']:.4f} "
            f"| Relaxed Micro F1: {relaxed_micro['f1']:.4f} | F2: {relaxed_micro['f2']:.4f}"
        )
        print(
            f"  -> Latency p50: {p50_lat:.2f}ms | p95: {p95_lat:.2f}ms | "
            f"Peak RSS: {peak_rss:.1f} MB ({budget_pct:.1f}% of 1GB)"
        )
        if "PERSON" in exact_by_type:
            pers_exact = exact_by_type["PERSON"]
            pers_relaxed = relaxed_by_type["PERSON"]
            print(
                f"  -> PERSON Exact P: {pers_exact['precision']:.4f}, "
                f"R: {pers_exact['recall']:.4f}, F1: {pers_exact['f1']:.4f}"
            )
            print(
                f"  -> PERSON Relaxed P: {pers_relaxed['precision']:.4f}, "
                f"R: {pers_relaxed['recall']:.4f}, F1: {pers_relaxed['f1']:.4f}"
            )

    # Save to reports/ner_benchmark.json
    out_dir = Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "ner_benchmark.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2)

    print(f"\nRaw benchmark metrics saved to: {out_file.as_posix()}")
    return benchmark_results


if __name__ == "__main__":
    run_benchmark()
