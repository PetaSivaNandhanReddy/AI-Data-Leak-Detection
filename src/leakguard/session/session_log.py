"""In-memory session log for audit receipts.

Stores sanitized ScanReceipt records in memory during a single interactive session.
Strict privacy guarantees:
- No raw text stored or logged
- No hashes of sensitive values
- Ephemeral, resets on process exit or explicit clear()
"""

from __future__ import annotations

from leakguard.schemas import ScanReceipt, Severity


class SessionLog:
    """In-memory collection of audit receipts generated within an active user session."""

    def __init__(self) -> None:
        self._receipts: list[ScanReceipt] = []

    def record_receipt(self, receipt: ScanReceipt) -> None:
        """Append a new sanitized scan receipt to session memory."""
        self._receipts.append(receipt)

    def get_receipts(self) -> list[ScanReceipt]:
        """Return all stored receipts in chronological order."""
        return list(self._receipts)

    def get_receipt(self, receipt_id: str) -> ScanReceipt | None:
        """Find a receipt by its unique random ID."""
        for r in self._receipts:
            if r.id == receipt_id:
                return r
        return None

    @property
    def total_scans(self) -> int:
        """Total number of scans completed in this session."""
        return len(self._receipts)

    @property
    def total_findings_count(self) -> int:
        """Total count of sensitive findings detected across all session scans."""
        return sum(sum(r.finding_counts_by_type.values()) for r in self._receipts)

    def aggregate_counts_by_severity(self) -> dict[str, int]:
        """Aggregate total finding counts across all receipts by severity."""
        totals: dict[str, int] = {s.value: 0 for s in Severity}
        for r in self._receipts:
            for sev, count in r.finding_counts_by_severity.items():
                totals[sev] = totals.get(sev, 0) + count
        return totals

    def aggregate_counts_by_type(self) -> dict[str, int]:
        """Aggregate total finding counts across all receipts by entity type."""
        totals: dict[str, int] = {}
        for r in self._receipts:
            for ent_type, count in r.finding_counts_by_type.items():
                totals[ent_type] = totals.get(ent_type, 0) + count
        return totals

    def clear(self) -> None:
        """Clear all session records."""
        self._receipts.clear()
