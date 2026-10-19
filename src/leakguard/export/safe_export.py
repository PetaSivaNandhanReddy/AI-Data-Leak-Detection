"""Privacy-preserving export utilities for LEAKGUARD findings and audit receipts.

Guarantees:
- Never includes raw input text or unmasked secrets
- Neutralizes CSV formula injection (=, +, -, @, tab, CR, LF prefixes)
- Display value rule: type + length bucket + masked form (configurable max reveal, default 0)
- Pure standard-library implementation (csv, json, io)
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Sequence
from typing import Any

from leakguard.schemas import Finding, ScanReceipt

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")
ZERO_REVEAL_TYPES = frozenset({"PASSWORD", "API_KEY", "SECRET_TOKEN"})


def neutralize_csv_formula(val: Any) -> Any:
    """Neutralize potential CSV/spreadsheet formula injection.

    Prepends a single quote (') if the string begins with any formula trigger
    (=, +, -, @, tab, carriage return, line feed), ensuring spreadsheet
    applications (Excel, Sheets, Calc) treat the cell as plain text.
    """
    if isinstance(val, str) and val.startswith(FORMULA_PREFIXES):
        return f"'{val}"
    return val


def get_length_bucket(length: int) -> str:
    """Classify character length into privacy-preserving coarse buckets."""
    if length <= 8:
        return "1-8 chars"
    if length <= 20:
        return "9-20 chars"
    if length <= 50:
        return "21-50 chars"
    return "51+ chars"


def format_safe_display_value(
    entity_type: str,
    length: int,
    raw_val: str | None = None,
    max_reveal: int = 0,
) -> str:
    """Format sanitized display value according to the rule:
    type + length bucket + masked form, with configurable maximum reveal (default 0).

    Sensitive credentials (passwords, tokens, API keys) never reveal any characters,
    regardless of max_reveal.
    """
    bucket = get_length_bucket(length)

    if max_reveal <= 0 or raw_val is None or entity_type in ZERO_REVEAL_TYPES:
        masked_form = "*" * min(length, 8)
    else:
        reveal_count = min(max_reveal, length)
        revealed = raw_val[-reveal_count:]
        masked_form = f"{'*' * min(length - reveal_count, 8)}{revealed}"

    return f"[{entity_type} | {bucket} | {masked_form}]"


def finding_to_sanitized_dict(
    finding: Finding,
    max_reveal: int = 0,
    raw_val: str | None = None,
) -> dict[str, Any]:
    """Convert a Finding into a sanitized dictionary for export."""
    safe_display = format_safe_display_value(
        entity_type=finding.entity_type,
        length=finding.length,
        raw_val=raw_val,
        max_reveal=max_reveal,
    )
    return {
        "id": finding.id,
        "entity_type": finding.entity_type,
        "severity": finding.severity.value,
        "display_value": safe_display,
        "length": finding.length,
        "start": finding.start,
        "end": finding.end,
        "detector": finding.detector,
        "rationale": finding.rationale,
    }


def export_findings_csv(
    findings: Sequence[Finding],
    max_reveal: int = 0,
    raw_values: dict[str, str] | None = None,
) -> str:
    """Export sanitized findings to CSV format with formula injection neutralization."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    headers = [
        "id",
        "entity_type",
        "severity",
        "display_value",
        "length",
        "start",
        "end",
        "detector",
        "rationale",
    ]
    writer.writerow(headers)

    raw_values = raw_values or {}
    for f in findings:
        raw_val = raw_values.get(f.id)
        d = finding_to_sanitized_dict(f, max_reveal=max_reveal, raw_val=raw_val)
        row = [
            neutralize_csv_formula(d["id"]),
            neutralize_csv_formula(d["entity_type"]),
            neutralize_csv_formula(d["severity"]),
            neutralize_csv_formula(d["display_value"]),
            d["length"],
            d["start"],
            d["end"],
            neutralize_csv_formula(d["detector"]),
            neutralize_csv_formula(d["rationale"]),
        ]
        writer.writerow(row)

    return output.getvalue()


def export_findings_json(
    findings: Sequence[Finding],
    max_reveal: int = 0,
    raw_values: dict[str, str] | None = None,
    indent: int = 2,
) -> str:
    """Export sanitized findings to JSON string."""
    raw_values = raw_values or {}
    items = [
        finding_to_sanitized_dict(f, max_reveal=max_reveal, raw_val=raw_values.get(f.id))
        for f in findings
    ]
    return json.dumps(items, indent=indent)


def export_receipt_json(receipt: ScanReceipt, indent: int = 2) -> str:
    """Export sanitized audit receipt to JSON string."""
    data = {
        "id": receipt.id,
        "timestamp": receipt.timestamp,
        "text_length": receipt.text_length,
        "duration_ms": receipt.duration_ms,
        "detectors_run": list(receipt.detectors_run),
        "finding_counts_by_type": receipt.finding_counts_by_type,
        "finding_counts_by_severity": receipt.finding_counts_by_severity,
        "max_severity": receipt.max_severity.value,
        "risk_band": receipt.risk_band,
        "overall_rule_score": receipt.overall_rule_score,
    }
    return json.dumps(data, indent=indent)


def export_receipt_csv(receipt: ScanReceipt) -> str:
    """Export sanitized audit receipt to CSV summary with formula injection neutralization."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    headers = [
        "receipt_id",
        "timestamp",
        "text_length",
        "duration_ms",
        "max_severity",
        "risk_band",
        "overall_rule_score",
        "total_findings",
    ]
    writer.writerow(headers)

    total_findings = sum(receipt.finding_counts_by_type.values())
    row = [
        neutralize_csv_formula(receipt.id),
        neutralize_csv_formula(receipt.timestamp),
        receipt.text_length,
        receipt.duration_ms,
        neutralize_csv_formula(receipt.max_severity.value),
        neutralize_csv_formula(receipt.risk_band),
        receipt.overall_rule_score,
        total_findings,
    ]
    writer.writerow(row)
    return output.getvalue()
