"""Core detection and redaction pipeline for LEAKGUARD.

Coordinates input validation, detector execution, overlap aggregation,
rule-based risk scoring, and text redaction. Safe error handling ensures
raw input text is never echoed in exception messages.
"""

from __future__ import annotations

import argparse
import logging
import time
import uuid
from datetime import UTC, datetime

from leakguard.config import settings
from leakguard.detection.aggregator import aggregate_findings
from leakguard.detection.ner_adapter import NERAdapterProtocol
from leakguard.detection.regex_detector import RegexDetector
from leakguard.detection.secret_detector import SecretDetector
from leakguard.redaction.engine import redact_text
from leakguard.risk.scoring import score_message
from leakguard.schemas import ScanReceipt, ScanResult

logger = logging.getLogger("leakguard.pipeline")


class Pipeline:
    """Core analysis pipeline coordinating detectors, aggregation, scoring, and redaction."""

    def __init__(
        self,
        max_input_length: int = settings.max_input_length,
        entropy_threshold: float = settings.entropy_threshold,
        ner_adapter: NERAdapterProtocol | None = None,
    ):
        self.max_input_length = max_input_length
        self.regex_detector = RegexDetector(name="regex")
        self.secret_detector = SecretDetector(name="secret", entropy_threshold=entropy_threshold)
        self.ner_adapter = ner_adapter

    def scan(
        self,
        text: str,
        redact: bool = True,
        redaction_mode: str = settings.default_redaction_mode,
    ) -> ScanResult:
        """Analyze text for sensitive data and calculate policy risk.

        Args:
            text: Raw input string.
            redact: Whether to generate a sanitized redacted version.
            redaction_mode: Mode ('placeholder', 'mask', 'remove').

        Raises:
            ValueError: If input length exceeds safety cap. Never echoes raw input.
            TypeError: If input is not a string.
        """
        if not isinstance(text, str):
            raise TypeError("Input text must be a string")

        if len(text) > self.max_input_length:
            logger.warning(
                "Scan rejected: input length %d exceeds maximum limit %d",
                len(text),
                self.max_input_length,
            )
            raise ValueError(
                f"Input text exceeds maximum allowed length of {self.max_input_length} characters "
                f"(received {len(text)} characters)."
            )

        logger.info(
            "Scan initiated (text_length=%d, max_input=%d)",
            len(text),
            self.max_input_length,
        )
        start_time = time.perf_counter()
        now_iso = datetime.now(UTC).isoformat()

        # 1. Run independent detectors
        finding_lists = [
            self.regex_detector.detect(text),
            self.secret_detector.detect(text),
        ]
        if self.ner_adapter is not None and self.ner_adapter.is_available():
            finding_lists.append(self.ner_adapter.detect(text))

        # 2. Resolve overlaps and merge provenances
        aggregated = aggregate_findings(finding_lists)

        # 3. Rule-based risk scoring
        score_res = score_message(text, aggregated)

        # 4. Segment-based redaction
        redacted_str: str | None = None
        if redact:
            redaction_res = redact_text(text, score_res.scored_findings, mode=redaction_mode)
            redacted_str = redaction_res.redacted_text

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Count findings by detector
        detector_counts: dict[str, int] = {}
        for f in score_res.scored_findings:
            detector_counts[f.detector] = detector_counts.get(f.detector, 0) + 1

        logger.info(
            "Scan completed in %.2fms (findings=%d, risk=%s)",
            duration_ms,
            len(score_res.scored_findings),
            score_res.risk_band,
        )

        return ScanResult(
            findings=score_res.scored_findings,
            raw_text_length=len(text),
            processed_at=now_iso,
            max_severity=score_res.max_severity,
            overall_rule_score=score_res.overall_rule_score,
            risk_band=score_res.risk_band,
            risk_rationale=score_res.rationales,
            detector_counts=detector_counts,
            duration_ms=round(duration_ms, 2),
            redacted_text=redacted_str,
        )

    def create_receipt(self, result: ScanResult) -> ScanReceipt:
        """Generate a sanitized, privacy-safe audit receipt.

        Guaranteed: NO raw input text and NO hashes of sensitive values.
        """
        receipt_id = f"rcpt_{uuid.uuid4().hex[:12]}"

        finding_counts_by_type: dict[str, int] = {}
        finding_counts_by_severity: dict[str, int] = {}

        for f in result.findings:
            t = f.entity_type
            s = f.severity.value
            finding_counts_by_type[t] = finding_counts_by_type.get(t, 0) + 1
            finding_counts_by_severity[s] = finding_counts_by_severity.get(s, 0) + 1

        return ScanReceipt(
            id=receipt_id,
            timestamp=result.processed_at,
            text_length=result.raw_text_length,
            duration_ms=result.duration_ms,
            detectors_run=("regex", "secret"),
            finding_counts_by_type=finding_counts_by_type,
            finding_counts_by_severity=finding_counts_by_severity,
            max_severity=result.max_severity,
            risk_band=result.risk_band,
            overall_rule_score=result.overall_rule_score,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="LEAKGUARD Core Detection Pipeline CLI")
    parser.add_argument(
        "--demo", action="store_true", help="Run demonstration on safe synthetic sample"
    )
    args = parser.parse_args()

    if args.demo:
        print("=== LEAKGUARD Detection Pipeline — Demonstration Mode ===")
        # Safe built-in demonstration sample containing fake credentials and Indian PII
        demo_text = (
            "Urgent: Developer deployment configuration.\n"
            "Contact lead: Aarav Sharma (priya.dev@internal-corp.in, +91 98450 12345).\n"
            "AWS Access Key: AKIAIOSFODNN7EXAMPLE\n"
            "Database master credentials: password = 'ProdStagingAdmin!9921'\n"
            "Customer refund: Card 4000 0012 3456 7899, Aadhaar 9999 4105 2815, PAN ABCDE1234F.\n"
            "Documentation link: https://api.example.com/v1/health"
        )
        pipeline = Pipeline()
        result = pipeline.scan(demo_text, redact=True, redaction_mode="placeholder")
        receipt = pipeline.create_receipt(result)

        print("\n[SCAN RESULT]")
        print(f"  Processed in: {result.duration_ms:.2f} ms")
        print(f"  Text Length:  {result.raw_text_length} chars")
        print(f"  Risk Band:    {result.risk_band} (Rule Score: {result.overall_rule_score}/100)")
        print(f"  Max Severity: {result.max_severity.value}")
        print(f"  Findings Detected ({len(result.findings)}):")
        for idx, f in enumerate(result.findings, start=1):
            print(
                f"    {idx}. [{f.severity.value}] {f.entity_type} @ ({f.start}:{f.end}) "
                f"via {f.detector} — {f.display_value} ({f.rationale})"
            )

        print("\n[RATIONALES]")
        for r in result.risk_rationale:
            print(f"  - {r}")

        print(f"\n[REDACTED OUTPUT (PLACEHOLDER MODE)]\n{result.redacted_text}")

        print("\n[SANITIZED SCAN RECEIPT]")
        print(f"  Receipt ID:    {receipt.id}")
        print(f"  Timestamp:     {receipt.timestamp}")
        print(f"  Total Length:  {receipt.text_length}")
        print(f"  Counts By Type: {receipt.finding_counts_by_type}")
        print(f"  Counts By Sev:  {receipt.finding_counts_by_severity}")
        print("==========================================================")
    else:
        print("Use --demo to run pipeline demo on a safe synthetic sample.")


if __name__ == "__main__":
    main()
