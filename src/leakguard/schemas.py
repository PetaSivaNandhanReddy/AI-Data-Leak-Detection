"""Data contracts and schemas for LEAKGUARD findings, scan results, and receipts.

All dataclasses are frozen to guarantee immutability. Character offsets are
strictly 0-indexed Python Unicode code-point half-open intervals [start, end)
into the ORIGINAL, unnormalized string.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Severity(StrEnum):
    """Severity levels for detected entities and overall scan risk."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def level(self) -> int:
        """Numeric rank for ordering severity comparisons."""
        order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        return order[self.value]

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, Severity):
            return self.level >= other.level
        return NotImplemented

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, Severity):
            return self.level > other.level
        return NotImplemented

    def __le__(self, other: Any) -> bool:
        if isinstance(other, Severity):
            return self.level <= other.level
        return NotImplemented

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Severity):
            return self.level < other.level
        return NotImplemented


def compute_safe_display_value(entity_type: str, raw_val: str, max_revealed_chars: int = 2) -> str:
    """Format a safe display string for findings that never exposes secrets.

    Reveals at most the final 2 characters (e.g. for card/account recognition),
    or zero characters for authentication secrets and passwords.
    """
    clean = raw_val.strip()
    if entity_type in {"PASSWORD", "API_KEY", "SECRET_TOKEN"}:
        return f"[{entity_type}:{len(clean)} chars masked]"

    if len(clean) <= max_revealed_chars:
        return f"[{entity_type}:masked]"

    revealed = clean[-max_revealed_chars:]
    masked_length = len(clean) - max_revealed_chars
    return f"{'*' * min(masked_length, 8)}{revealed} ({entity_type})"


@dataclass(frozen=True)
class Finding:
    """An individual sensitive entity detected in the text.

    Offsets refer strictly to the original input string.
    """

    id: str
    entity_type: str
    start: int
    end: int
    detector: str
    severity: Severity
    display_value: str
    rationale: str
    rule_score: float | None = None
    model_prob: float | None = None
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError(f"start offset cannot be negative: {self.start}")
        if self.end <= self.start:
            raise ValueError(
                f"end offset ({self.end}) must be strictly greater than start ({self.start})"
            )
        if not self.provenance:
            object.__setattr__(self, "provenance", (self.detector,))

    @property
    def span(self) -> tuple[int, int]:
        return (self.start, self.end)

    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass(frozen=True)
class RedactionResult:
    """Outcome of a text redaction operation."""

    redacted_text: str
    mode: str
    original_to_output_spans: tuple[tuple[tuple[int, int], tuple[int, int]], ...]
    entities_redacted_count: int


@dataclass(frozen=True)
class ScanResult:
    """Complete results of analyzing a text message."""

    findings: tuple[Finding, ...]
    raw_text_length: int
    processed_at: str
    max_severity: Severity
    overall_rule_score: float
    risk_band: str  # no_exposure | possible_exposure | high_risk_exposure
    risk_rationale: tuple[str, ...]
    detector_counts: dict[str, int]
    duration_ms: float
    redacted_text: str | None = None

    @property
    def has_findings(self) -> bool:
        return len(self.findings) > 0


@dataclass(frozen=True)
class ScanReceipt:
    """Sanitized, privacy-safe audit record of a scan operation.

    Strictly contains NO raw input text and NO hashes of sensitive values.
    """

    id: str
    timestamp: str
    text_length: int
    duration_ms: float
    detectors_run: tuple[str, ...]
    finding_counts_by_type: dict[str, int]
    finding_counts_by_severity: dict[str, int]
    max_severity: Severity
    risk_band: str
    overall_rule_score: float
