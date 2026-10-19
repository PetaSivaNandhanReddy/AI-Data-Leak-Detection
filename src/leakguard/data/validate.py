"""Validation module for LEAKGUARD synthetic and annotated datasets.

Enforces:
- Schema conformance (required keys, correct types)
- Strict character offset alignment (text[start:end] == value)
- Unicode safety (valid UTF-8, no orphaned surrogates)
- Non-empty text
- Valid message_label triage
- Valid entity label taxonomy
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

VALID_MESSAGE_LABELS = {
    "no_exposure",
    "possible_exposure",
    "high_risk_exposure",
}

VALID_ENTITY_LABELS = {
    "EMAIL",
    "PHONE",
    "PERSON",
    "CARD",
    "AADHAAR",
    "PAN",
    "IBAN",
    "ACCOUNT_NUMBER",
    "VOTER_ID",
    "PASSWORD",
    "API_KEY",
    "SECRET_TOKEN",
}

REQUIRED_KEYS = {
    "id": str,
    "text": str,
    "entities": list,
    "message_label": str,
    "template_id": str,
    "family_id": str,
    "generator_version": str,
    "seed": int,
}


def validate_record(record: dict[str, Any]) -> list[str]:
    """Validate a single dataset record against schema, offsets, and label standards.

    Returns:
        List of error description strings. An empty list indicates a valid record.
    """
    errors: list[str] = []

    # 1. Check required keys and types
    for key, expected_type in REQUIRED_KEYS.items():
        if key not in record:
            errors.append(f"Missing required key '{key}'")
        elif not isinstance(record[key], expected_type):
            actual_type = type(record[key]).__name__
            errors.append(f"Key '{key}' expected type {expected_type.__name__}, got {actual_type}")

    if errors:
        return errors  # Cannot proceed with deep checks if basic keys are missing

    text: str = record["text"]

    # 2. Text validation
    if not text.strip():
        errors.append("Record text is empty or contains only whitespace")

    try:
        text.encode("utf-8")
    except UnicodeEncodeError as exc:
        errors.append(f"Text contains invalid Unicode: {exc}")

    # 3. Message label validation
    msg_label = record["message_label"]
    if msg_label not in VALID_MESSAGE_LABELS:
        valid_labels = sorted(VALID_MESSAGE_LABELS)
        errors.append(f"Invalid message_label '{msg_label}'. Must be one of {valid_labels}")

    # 4. Entities and character offset alignment
    entities: list[dict[str, Any]] = record["entities"]
    spans: list[tuple[int, int]] = []

    for idx, ent in enumerate(entities):
        if not isinstance(ent, dict):
            errors.append(f"Entity at index {idx} is not a dictionary")
            continue

        for ent_key in ("start", "end", "label", "value"):
            if ent_key not in ent:
                errors.append(f"Entity {idx} missing key '{ent_key}'")

        start = ent.get("start")
        end = ent.get("end")
        label = ent.get("label")
        val = ent.get("value")

        if not isinstance(start, int) or not isinstance(end, int):
            errors.append(f"Entity {idx} start/end must be integers")
            continue

        if start < 0:
            errors.append(f"Entity {idx} start offset cannot be negative: {start}")
        if end > len(text):
            errors.append(f"Entity {idx} end offset ({end}) exceeds text length ({len(text)})")
        if start >= end:
            errors.append(f"Entity {idx} start ({start}) must be strictly less than end ({end})")
            continue

        if label not in VALID_ENTITY_LABELS:
            valid_ents = sorted(VALID_ENTITY_LABELS)
            errors.append(f"Entity {idx} has invalid label '{label}'. Must be in {valid_ents}")

        # CRITICAL: Strict offset alignment check
        actual_slice = text[start:end]
        if actual_slice != val:
            errors.append(
                f"Entity {idx} offset alignment failure for '{label}': "
                f"text[{start}:{end}] is '{actual_slice}', recorded value is '{val}'"
            )

        spans.append((start, end))

    # 5. Check for entity overlaps (unless identical or nesting is documented)
    sorted_spans = sorted(spans, key=lambda s: (s[0], s[1]))
    for i in range(len(sorted_spans) - 1):
        curr_start, curr_end = sorted_spans[i]
        next_start, next_end = sorted_spans[i + 1]
        if curr_end > next_start:
            errors.append(
                f"Overlapping entity spans detected: [{curr_start}, {curr_end}) "
                f"overlaps with [{next_start}, {next_end})"
            )

    return errors


def validate_dataset(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Validate an entire collection of dataset records and produce a summary report."""
    total = len(records)
    valid_count = 0
    all_errors: dict[str, list[str]] = {}
    label_distribution: dict[str, int] = {}
    entity_counts: dict[str, int] = {}

    for idx, rec in enumerate(records):
        rec_id = rec.get("id", f"record_{idx}")
        errs = validate_record(rec)
        if errs:
            all_errors[rec_id] = errs
        else:
            valid_count += 1
            lbl = rec["message_label"]
            label_distribution[lbl] = label_distribution.get(lbl, 0) + 1
            for ent in rec.get("entities", []):
                ent_lbl = ent["label"]
                entity_counts[ent_lbl] = entity_counts.get(ent_lbl, 0) + 1

    return {
        "total_records": total,
        "valid_records": valid_count,
        "invalid_records": len(all_errors),
        "is_valid": len(all_errors) == 0,
        "label_distribution": label_distribution,
        "entity_counts": entity_counts,
        "errors": all_errors,
    }
