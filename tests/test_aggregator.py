"""Unit tests for finding aggregation, overlap resolution, and provenance retention."""

from leakguard.detection.aggregator import aggregate_findings
from leakguard.schemas import Finding, Severity


def test_aggregator_no_overlap():
    """Verify non-overlapping findings from different detectors are both preserved."""
    f1 = Finding(
        id="f1",
        entity_type="EMAIL",
        start=0,
        end=15,
        detector="regex",
        severity=Severity.MEDIUM,
        display_value="user@example.com",
        rationale="email match",
    )
    f2 = Finding(
        id="f2",
        entity_type="API_KEY",
        start=20,
        end=40,
        detector="secret",
        severity=Severity.CRITICAL,
        display_value="[API_KEY:masked]",
        rationale="api key match",
    )

    merged = aggregate_findings([[f1], [f2]])
    assert len(merged) == 2
    assert merged[0].id == "f1"
    assert merged[1].id == "f2"


def test_aggregator_secret_priority_over_regex():
    """Verify that when secret and regex overlap, secret detector takes precedence."""
    # Regex matched a broad token, but secret detector identified a specific credential
    f_regex = Finding(
        id="f_reg",
        entity_type="CARD",
        start=10,
        end=30,
        detector="regex",
        severity=Severity.HIGH,
        display_value="4000...99",
        rationale="regex card match",
    )
    f_secret = Finding(
        id="f_sec",
        entity_type="PASSWORD",
        start=10,
        end=30,
        detector="secret",
        severity=Severity.CRITICAL,
        display_value="[PASSWORD:masked]",
        rationale="password assignment",
    )

    merged = aggregate_findings([[f_regex], [f_secret]])
    assert len(merged) == 1
    winner = merged[0]
    assert winner.detector == "secret"
    assert winner.entity_type == "PASSWORD"
    # Crucial: Provenance retains both detectors!
    assert "regex" in winner.provenance
    assert "secret" in winner.provenance


def test_aggregator_longer_span_and_earlier_start():
    """Verify longer span wins when detector and severity are equal."""
    f_short = Finding(
        id="short",
        entity_type="PHONE",
        start=5,
        end=15,
        detector="regex",
        severity=Severity.MEDIUM,
        display_value="9876543210",
        rationale="phone match",
    )
    f_long = Finding(
        id="long",
        entity_type="PHONE",
        start=5,
        end=20,
        detector="regex",
        severity=Severity.MEDIUM,
        display_value="+91 98765 43210",
        rationale="international phone match",
    )

    merged = aggregate_findings([[f_short], [f_long]])
    assert len(merged) == 1
    assert merged[0].id == "long"
    assert merged[0].end == 20
