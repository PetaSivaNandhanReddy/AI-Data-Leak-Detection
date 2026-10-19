"""Rule-based risk scoring engine for data leak detection.

Calculates a deterministic rule score (0 to 100) based on base entity weights,
security context boosters, and benign reducers.

Outputs are explicitly categorized as a "rule score, not a probability".
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from leakguard.schemas import Finding, Severity

# --- Base Entity Weights (0 to 100) ---
BASE_WEIGHTS: dict[str, float] = {
    "PASSWORD": 85.0,
    "API_KEY": 85.0,
    "SECRET_TOKEN": 85.0,
    "CARD": 80.0,
    "AADHAAR": 65.0,
    "PAN": 60.0,
    "ACCOUNT_NUMBER": 55.0,
    "IBAN": 55.0,
    "VOTER_ID": 45.0,
    "EMAIL": 40.0,
    "PHONE": 40.0,
    "PERSON": 30.0,
}

_SENSITIVE_CONTEXT_RE = re.compile(
    r"(?i)\b(?:prod|production|staging|database|db|root|admin|secret|leak|compromised|urgent|revoke)\b"
)

_BENIGN_CONTEXT_RE = re.compile(
    r"(?i)\b(?:example\.com|example\.org|test\.invalid|placeholder|mock|sample|template|documentation)\b"
)


@dataclass(frozen=True)
class ScoringResult:
    """Outcome of rule-based risk evaluation."""

    overall_rule_score: float
    risk_band: str  # no_exposure | possible_exposure | high_risk_exposure
    max_severity: Severity
    rationales: tuple[str, ...]
    scored_findings: tuple[Finding, ...]


def score_message(text: str, findings: Sequence[Finding]) -> ScoringResult:
    """Compute transparent, rule-based risk score and severity for detected findings."""
    if not findings:
        return ScoringResult(
            overall_rule_score=0.0,
            risk_band="no_exposure",
            max_severity=Severity.LOW,
            rationales=("No sensitive entities detected in text",),
            scored_findings=(),
        )

    rationales: list[str] = []

    # 1. Base Score: Maximum base weight among detected entities
    max_base_weight = 0.0
    highest_entity = ""
    for f in findings:
        weight = BASE_WEIGHTS.get(f.entity_type, 30.0)
        if weight > max_base_weight:
            max_base_weight = weight
            highest_entity = f.entity_type

    score = max_base_weight
    rationales.append(f"Base score {max_base_weight:.0f} from highest entity '{highest_entity}'")

    # 2. Boosters
    # Booster A: Checksum verified (+10)
    has_checksum = any(
        "checksum" in f.rationale.lower() or "luhn" in f.rationale.lower() for f in findings
    )
    if has_checksum:
        score += 10.0
        rationales.append("Booster +10: Mathematical checksum (Luhn/Verhoeff/IBAN) verified")

    # Booster B: Sensitive security/infrastructure context (+15)
    if _SENSITIVE_CONTEXT_RE.search(text):
        score += 15.0
        rationales.append("Booster +15: Infrastructure or operational context keywords detected")

    # Booster C: Entity co-occurrence (+15)
    unique_types = {f.entity_type for f in findings}
    if len(unique_types) >= 2:
        # High impact co-occurrences (e.g. Identity + Name, or Email + Password)
        if ("PASSWORD" in unique_types or "API_KEY" in unique_types) and len(unique_types) > 1:
            score += 20.0
            rationales.append(
                "Booster +20: Authentication secret co-occurs with user/service identifier"
            )
        else:
            score += 10.0
            rationales.append("Booster +10: Multiple distinct entity types co-occur in message")

    # 3. Reducers
    # Reducer A: Benign documentation / test markers (-40)
    if _BENIGN_CONTEXT_RE.search(text):
        score -= 40.0
        rationales.append("Reducer -40: Documentation, mock, or test markers detected in text")

    # Reducer B: Single low-sensitivity entity with no other context (-15)
    if len(findings) == 1 and highest_entity in {"EMAIL", "PHONE", "PERSON"}:
        score -= 15.0
        rationales.append("Reducer -15: Isolated standard contact identifier")

    # Clamp score strictly to [0.0, 100.0]
    final_score = max(0.0, min(100.0, score))

    # Determine risk band and overall severity
    if final_score >= 70.0:
        risk_band = "high_risk_exposure"
        max_severity = Severity.CRITICAL
    elif final_score >= 25.0:
        risk_band = "possible_exposure"
        max_severity = Severity.MEDIUM if final_score < 50.0 else Severity.HIGH
    else:
        risk_band = "no_exposure"
        max_severity = Severity.LOW

    # Update findings with rule score and final severity
    scored_findings: list[Finding] = []
    for f in findings:
        item_base = BASE_WEIGHTS.get(f.entity_type, 30.0)
        scored_findings.append(
            Finding(
                id=f.id,
                entity_type=f.entity_type,
                start=f.start,
                end=f.end,
                detector=f.detector,
                severity=f.severity,
                display_value=f.display_value,
                rationale=f.rationale,
                rule_score=round(item_base, 1),
                model_prob=None,
                provenance=f.provenance,
            )
        )

    return ScoringResult(
        overall_rule_score=round(final_score, 1),
        risk_band=risk_band,
        max_severity=max_severity,
        rationales=tuple(rationales),
        scored_findings=tuple(scored_findings),
    )
