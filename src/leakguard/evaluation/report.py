"""Master evaluation report generator for LEAKGUARD.

CLI entrypoint:
  python -m leakguard.evaluation.report --out reports/

Orchestrates:
  - Entity-level evaluation on validation and test splits (exact/relaxed P, R, F1, F2).
  - Message-level evaluation on validation and test splits (Majority, Keyword, Rule, Rule+NER).
  - Machine learning classification experiment evaluation.
  - Generates:
      1. reports/eval_latest.json
      2. reports/run_metadata.json
      3. reports/reference_corpus.json
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from leakguard.classification.train import run_experiment
from leakguard.detection.ner_adapter import SpacyNERAdapter
from leakguard.detection.pipeline import Pipeline
from leakguard.evaluation.entity_eval import evaluate_dataset_entities
from leakguard.evaluation.message_eval import (
    run_keyword_baseline,
    run_majority_baseline,
    run_pipeline_baseline,
)


def get_git_commit() -> str:
    """Retrieve current git commit hash if available."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        )
        return out.strip()
    except Exception:
        return "git-unavailable"


def build_evaluation_report(
    train_path: str = "data/processed/train.jsonl",
    val_path: str = "data/processed/val.jsonl",
    test_path: str = "data/processed/test.jsonl",
    challenge_path: str = "data/challenge/challenge_set.jsonl",
    out_dir: str = "reports",
) -> dict[str, Any]:
    """Execute complete evaluation protocol and persist standardized artifacts."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Load splits
    def _read_records(p_str: str) -> list[dict[str, Any]]:
        p = Path(p_str)
        if not p.is_file():
            return []
        with open(p, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    train_recs = _read_records(train_path)
    val_recs = _read_records(val_path)
    test_recs = _read_records(test_path)
    ch_recs = _read_records(challenge_path)

    has_challenge = len(ch_recs) > 0

    print(
        f"Evaluation dataset loaded: {len(train_recs)} train, {len(val_recs)} val, "
        f"{len(test_recs)} test, {len(ch_recs)} challenge."
    )

    # 2. Pipeline instances
    rule_pipe = Pipeline(ner_adapter=None)
    rule_ner_pipe = Pipeline(
        ner_adapter=SpacyNERAdapter("en_core_web_sm", target_labels={"PERSON"})
    )

    # 3. Message-level baseline evaluations
    print("Evaluating message-level baselines on validation split...")
    val_majority = run_majority_baseline(val_recs)
    val_keyword = run_keyword_baseline(val_recs)
    val_rule, _ = run_pipeline_baseline(val_recs, rule_pipe)
    val_rule_ner, _ = run_pipeline_baseline(val_recs, rule_ner_pipe)

    print("Evaluating message-level baselines on held-out test split...")
    test_majority = run_majority_baseline(test_recs)
    test_keyword = run_keyword_baseline(test_recs)
    test_rule, test_rule_scans = run_pipeline_baseline(test_recs, rule_pipe)
    test_rule_ner, test_rule_ner_scans = run_pipeline_baseline(test_recs, rule_ner_pipe)

    # 4. Entity-level evaluations
    print("Evaluating entity-level metrics on validation split...")
    val_preds_rule = [rule_pipe.scan(r["text"], redact=False).findings for r in val_recs]
    val_entity_rule = evaluate_dataset_entities(val_recs, val_preds_rule)

    val_preds_ner = [rule_ner_pipe.scan(r["text"], redact=False).findings for r in val_recs]
    val_entity_ner = evaluate_dataset_entities(val_recs, val_preds_ner)

    print("Evaluating entity-level metrics on held-out test split...")
    test_preds_rule = [s.findings for s in test_rule_scans]
    test_entity_rule = evaluate_dataset_entities(test_recs, test_preds_rule)

    test_preds_ner = [s.findings for s in test_rule_ner_scans]
    test_entity_ner = evaluate_dataset_entities(test_recs, test_preds_ner)

    # 5. Machine Learning Classifier Experiment
    print("Executing ML classifier training and evaluation experiment...")
    ml_experiment_results = run_experiment(
        train_path=train_path,
        val_path=val_path,
        test_path=test_path,
        challenge_path=challenge_path,
    )

    # 6. Build Reference Corpus from Test Split
    print("Generating reference corpus from synthetic test split...")
    type_counts: dict[str, int] = {}
    sev_counts: dict[str, int] = {}
    risk_band_counts: dict[str, int] = {}
    scan_items: list[dict[str, Any]] = []

    for rec, scan_res in zip(test_recs, test_rule_ner_scans, strict=True):
        risk_band_counts[scan_res.risk_band] = risk_band_counts.get(scan_res.risk_band, 0) + 1
        for f in scan_res.findings:
            type_counts[f.entity_type] = type_counts.get(f.entity_type, 0) + 1
            sev_counts[f.severity.value] = sev_counts.get(f.severity.value, 0) + 1

        scan_items.append(
            {
                "id": rec["id"],
                "text_length": len(rec["text"]),
                "ground_truth_label": rec["message_label"],
                "predicted_risk_band": scan_res.risk_band,
                "overall_rule_score": scan_res.overall_rule_score,
                "findings_count": len(scan_res.findings),
            }
        )

    ref_corpus = {
        "metadata": {
            "title": "LEAKGUARD Reference Corpus (Synthetic Test Split)",
            "description": "Baseline reference scan distribution on held-out test data.",
            "total_records": len(test_recs),
            "generated_at": datetime.now(UTC).isoformat(),
            "pipeline_configuration": "Rule + spaCy NER (en_core_web_sm)",
        },
        "aggregate_statistics": {
            "risk_band_distribution": risk_band_counts,
            "detected_entity_counts": type_counts,
            "severity_distribution": sev_counts,
        },
        "sample_scans": scan_items[:50],  # First 50 records as reference gallery
    }

    ref_corpus_file = out_path / "reference_corpus.json"
    with open(ref_corpus_file, "w", encoding="utf-8") as f:
        json.dump(ref_corpus, f, indent=2)

    # 7. Metadata and Artifact Assembly
    run_date = datetime.now(UTC).isoformat()
    git_commit = get_git_commit()

    import sklearn
    import spacy

    run_meta = {
        "run_date": run_date,
        "git_commit": git_commit,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "package_versions": {
            "sklearn": sklearn.__version__,
            "spacy": spacy.__version__,
        },
        "dataset_split_method": "by_family_id (60/20/20)",
        "dataset_seed": 42,
        "split_sizes": {
            "train": len(train_recs),
            "val": len(val_recs),
            "test": len(test_recs),
            "challenge": len(ch_recs),
        },
        "challenge_set_status": "present" if has_challenge else "missing",
    }

    run_meta_file = out_path / "run_metadata.json"
    with open(run_meta_file, "w", encoding="utf-8") as f:
        json.dump(run_meta, f, indent=2)

    # Stored score distributions for threshold exploration
    threshold_scores = [
        {
            "id": rec["id"],
            "y_true": 1
            if rec["message_label"] in {"possible_exposure", "high_risk_exposure"}
            else 0,
            "rule_score": round(scan.overall_rule_score, 2),
            "risk_band": scan.risk_band,
        }
        for rec, scan in zip(test_recs, test_rule_ner_scans, strict=True)
    ]

    eval_latest = {
        "metadata": run_meta,
        "challenge_set_evaluation": ("evaluated" if has_challenge else "no challenge set yet"),
        "validation_metrics": {
            "baselines": {
                "majority": val_majority.to_dict(),
                "keyword": val_keyword.to_dict(),
                "rule_only": val_rule.to_dict(),
                "rule_ner": val_rule_ner.to_dict(),
            },
            "entity_eval": {
                "rule_only": val_entity_rule.to_dict(),
                "rule_ner": val_entity_ner.to_dict(),
            },
        },
        "test_metrics": {
            "baselines": {
                "majority": test_majority.to_dict(),
                "keyword": test_keyword.to_dict(),
                "rule_only": test_rule.to_dict(),
                "rule_ner": test_rule_ner.to_dict(),
            },
            "entity_eval": {
                "rule_only": test_entity_rule.to_dict(),
                "rule_ner": test_entity_ner.to_dict(),
            },
        },
        "ml_classifier_experiment": {k: v.to_dict() for k, v in ml_experiment_results.items()},
        "threshold_explorer_scores": threshold_scores,
    }

    eval_latest_file = out_path / "eval_latest.json"
    with open(eval_latest_file, "w", encoding="utf-8") as f:
        json.dump(eval_latest, f, indent=2)

    print(f"\nArtifacts successfully written to '{out_path.as_posix()}':")
    print(f"  - {eval_latest_file.name}")
    print(f"  - {run_meta_file.name}")
    print(f"  - {ref_corpus_file.name}")

    return eval_latest


def main() -> None:
    """CLI handler."""
    parser = argparse.ArgumentParser(description="Generate LEAKGUARD evaluation report.")
    parser.add_argument("--out", type=str, default="reports", help="Output directory for reports")
    args = parser.parse_args()

    build_evaluation_report(out_dir=args.out)


if __name__ == "__main__":
    main()
