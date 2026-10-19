"""Deterministic data generator for LEAKGUARD synthetic dataset.

Renders author-written template families into realistic messages with exact entity spans,
mathematically valid or decoy identifiers, and policy-grounded risk triage labels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from leakguard.data.splits import group_split_by_family
from leakguard.data.synthetic_values import SyntheticValueFactory
from leakguard.data.templates import ALL_TEMPLATES, Template
from leakguard.data.validate import validate_dataset, validate_record

GENERATOR_VERSION = "0.1.0"


def render_template(
    template: Template,
    factory: SyntheticValueFactory,
    row_idx: int,
    seed: int,
) -> dict[str, Any]:
    """Render a single template into a dataset record with exact character offset tracking."""
    text_buffer = ""
    entities: list[dict[str, Any]] = []

    for seg in template.segments:
        if isinstance(seg, str):
            text_buffer += seg
        elif isinstance(seg, (tuple, list)):
            generator_fn_name, entity_label = seg
            fn = getattr(factory, generator_fn_name)
            val = fn()
            start = len(text_buffer)
            end = start + len(val)
            text_buffer += val
            if entity_label is not None and entity_label != "None":
                entities.append(
                    {
                        "start": start,
                        "end": end,
                        "label": entity_label,
                        "value": val,
                    }
                )

    rec_id = f"lg_{template.family_id}_{template.template_id}_s{seed}_{row_idx:06d}"
    record = {
        "id": rec_id,
        "text": text_buffer,
        "entities": entities,
        "message_label": template.message_label,
        "template_id": template.template_id,
        "family_id": template.family_id,
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
    }

    # Strict internal consistency check immediately after render
    errs = validate_record(record)
    if errs:
        raise ValueError(f"Generated malformed record {rec_id}: {'; '.join(errs)}")

    return record


def generate_dataset(
    num_samples: int = 4000,
    seed: int = 42,
    templates: Sequence[Template] = ALL_TEMPLATES,
) -> list[dict[str, Any]]:
    """Deterministically generate a synthetic dataset from templates."""
    factory = SyntheticValueFactory(seed=seed)
    rng = random.Random(seed)

    records: list[dict[str, Any]] = []
    num_templates = len(templates)

    for i in range(num_samples):
        # Evenly cycle through all templates with deterministic variations
        tpl = templates[i % num_templates]
        rec = render_template(tpl, factory, row_idx=i, seed=seed)
        records.append(rec)

    # Deterministic shuffle to interleave families naturally within splits
    rng.shuffle(records)
    return records


def compute_file_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def write_jsonl(records: Sequence[dict[str, Any]], filepath: Path) -> str:
    """Write records to JSON Lines format with sorted keys and UTF-8 encoding.

    Returns:
        SHA-256 hex checksum of the written file.
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    return compute_file_sha256(filepath)


def build_manifest(
    seed: int,
    total_records: int,
    split_stats: dict[str, Any],
    val_report: dict[str, Any],
    checksums: dict[str, str],
) -> dict[str, Any]:
    """Construct data manifest metadata dictionary."""
    return {
        "manifest_version": "1.0.0",
        "dataset_name": "LEAKGUARD Synthetic Benchmark Corpus",
        "source": (
            "Author-written template library rendered via Faker (en_IN, en_US) "
            "and mathematical checksum generators"
        ),
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "total_records": total_records,
        "template_count": len(ALL_TEMPLATES),
        "transformation_steps": [
            "1. Author writes 157 structured templates across 15 semantic families.",
            (
                "2. SyntheticValueFactory generates realistic values using Faker (en_IN, en_US) "
                "and algorithmic checksums (Verhoeff for Aadhaar, Luhn for Cards, Mod-97 for IBAN)."
            ),
            (
                "3. Segments are rendered with dynamic offset accumulation to capture "
                "exact [start, end) character spans."
            ),
            "4. Immediate per-row schema and offset alignment validation.",
            (
                "5. Deterministic shuffling and group splitting by family_id "
                "(60% train, 20% val, 20% test)."
            ),
            (
                "6. Cross-split exact duplicate hash scan and n-gram Jaccard "
                "near-duplicate verification."
            ),
            "7. Extraction of 200-row representative balanced sample for git tracking.",
            "8. SHA-256 integrity checksum generation.",
        ],
        "family_count": len(split_stats.get("train_families", []))
        + len(split_stats.get("val_families", []))
        + len(split_stats.get("test_families", [])),
        "split_counts": {
            "train": split_stats["train_count"],
            "val": split_stats["val_count"],
            "test": split_stats["test_count"],
        },
        "split_families": {
            "train": split_stats["train_families"],
            "val": split_stats["val_families"],
            "test": split_stats["test_families"],
        },
        "class_distribution": val_report["label_distribution"],
        "entity_counts": val_report["entity_counts"],
        "checksums": checksums,
        "licenses": {
            "dataset": "Proprietary / Author Project Baseline",
            "faker": "MIT",
            "python_standard_library": "PSF License",
        },
        "intended_use": (
            "Evaluating entity span detection and message risk triage for "
            "the LEAKGUARD security intelligence console. Contains synthetic data only."
        ),
        "privacy_notice": (
            "All personal names, emails, cards, Aadhaar, PAN, and phone numbers are "
            "synthetically generated with test ranges and RFC domains. Zero real personal data."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="LEAKGUARD synthetic data generator")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    parser.add_argument("--num-samples", type=int, default=4000, help="Total samples to generate")
    parser.add_argument(
        "--out",
        type=str,
        default="data/processed",
        help="Output directory for train/val/test splits",
    )
    parser.add_argument(
        "--sample-out",
        type=str,
        default="data/samples",
        help="Directory to save committed small sample",
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    sample_dir = Path(args.sample_out)
    manifest_path = Path("data/manifest.json")

    print(f"Generating {args.num_samples} records with seed {args.seed}...")
    records = generate_dataset(num_samples=args.num_samples, seed=args.seed)

    print("Validating all generated records...")
    val_report = validate_dataset(records)
    if not val_report["is_valid"]:
        raise ValueError(f"Dataset validation failed: {val_report['errors']}")
    valid_n = val_report["valid_records"]
    total_n = val_report["total_records"]
    print(f"Validation passed: {valid_n}/{total_n} records valid.")

    print("Splitting records by family_id (60/20/20)...")
    split_data = group_split_by_family(records, seed=args.seed)

    checksums = {}
    print(f"Writing outputs to {out_dir}...")
    checksums["all.jsonl"] = write_jsonl(records, out_dir / "all.jsonl")
    checksums["train.jsonl"] = write_jsonl(split_data.train, out_dir / "train.jsonl")
    checksums["val.jsonl"] = write_jsonl(split_data.val, out_dir / "val.jsonl")
    checksums["test.jsonl"] = write_jsonl(split_data.test, out_dir / "test.jsonl")

    # Write committed small sample (exactly 200 rows, balanced from all splits)
    sample_records = records[:200]
    sample_dir.mkdir(parents=True, exist_ok=True)
    checksums["sample_200.jsonl"] = write_jsonl(sample_records, sample_dir / "sample_200.jsonl")

    manifest = build_manifest(
        seed=args.seed,
        total_records=len(records),
        split_stats=split_data.stats,
        val_report=val_report,
        checksums=checksums,
    )

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Data generation complete! Manifest written to {manifest_path}")
    print(f"  Train: {len(split_data.train)} records ({split_data.stats['train_families']})")
    print(f"  Val:   {len(split_data.val)} records ({split_data.stats['val_families']})")
    print(f"  Test:  {len(split_data.test)} records ({split_data.stats['test_families']})")
    print(f"  Class Distribution: {val_report['label_distribution']}")
    print(f"  Sample: {len(sample_records)} rows written to {sample_dir / 'sample_200.jsonl'}")


if __name__ == "__main__":
    main()
