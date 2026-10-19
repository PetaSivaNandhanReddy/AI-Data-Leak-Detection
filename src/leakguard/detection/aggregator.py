"""Finding aggregator and deterministic overlap resolution engine.

Overlap Resolution Protocol:
--------------------------------------------------------------------------------------
Priority Attribute  | Criterion                         | Rationale
--------------------+-----------------------------------+-----------------------------
1. Detector Priority| secret > regex > ner              | Explicit secret formats &
                    |                                   | tokens take precedence.
2. Severity Level   | CRITICAL > HIGH > MEDIUM > LOW    | Higher risk takes precedence.
3. Span Length      | Longer span wins (end - start)    | Prefers more complete match.
4. Start Index      | Earlier start index wins          | Natural reading order tie-break.
--------------------+-----------------------------------+-----------------------------

Provenance Retention:
When an overlap is resolved and two findings are merged, the winning finding retains
all detector names from both findings in its `provenance` tuple.
"""

from __future__ import annotations

from collections.abc import Sequence

from leakguard.schemas import Finding

DETECTOR_PRIORITIES: dict[str, int] = {
    "secret": 3,
    "regex": 2,
    "ner": 1,
}


def _ranking_key(f: Finding) -> tuple[int, int, int, int]:
    """Sort key for finding precedence (higher is better)."""
    det_rank = DETECTOR_PRIORITIES.get(f.detector, 0)
    sev_rank = f.severity.level
    span_len = f.length
    earlier_start = -f.start
    return (det_rank, sev_rank, span_len, earlier_start)


def _spans_overlap(f1: Finding, f2: Finding) -> bool:
    """Return True if two findings overlap in character offsets."""
    return max(f1.start, f2.start) < min(f1.end, f2.end)


def aggregate_findings(findings_lists: Sequence[Sequence[Finding]]) -> list[Finding]:
    """Merge findings from multiple detectors, resolving character span overlaps.

    Retains full detector provenance on merged findings.
    """
    flat: list[Finding] = []
    for fl in findings_lists:
        flat.extend(fl)

    if not flat:
        return []

    # Sort candidates by start offset, then by ranking key descending
    flat.sort(key=lambda f: (f.start, -_ranking_key(f)[0], -_ranking_key(f)[1]))

    merged: list[Finding] = []

    for candidate in flat:
        # Check for overlaps with already admitted findings
        overlapping_indices = [
            i for i, admitted in enumerate(merged) if _spans_overlap(admitted, candidate)
        ]

        if not overlapping_indices:
            merged.append(candidate)
        else:
            # Resolve against all overlapping admitted findings
            all_involved = [merged[i] for i in overlapping_indices] + [candidate]
            # Best finding according to ranking key
            winner = max(all_involved, key=_ranking_key)

            # Combine provenances
            combined_provenance: list[str] = []
            for item in all_involved:
                for prov in item.provenance:
                    if prov not in combined_provenance:
                        combined_provenance.append(prov)

            # Build replacement winner with unified provenance
            resolved_winner = Finding(
                id=winner.id,
                entity_type=winner.entity_type,
                start=winner.start,
                end=winner.end,
                detector=winner.detector,
                severity=winner.severity,
                display_value=winner.display_value,
                rationale=winner.rationale,
                rule_score=winner.rule_score,
                model_prob=winner.model_prob,
                provenance=tuple(sorted(combined_provenance)),
            )

            # Remove previous overlapping entries and insert resolved winner
            merged = [item for i, item in enumerate(merged) if i not in overlapping_indices]
            merged.append(resolved_winner)

    # Final sort strictly by start offset
    merged.sort(key=lambda f: f.start)
    return merged
