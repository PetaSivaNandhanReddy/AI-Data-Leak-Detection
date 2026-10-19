"""Unit tests for rule-based risk scoring engine."""

from leakguard.risk.scoring import score_message
from leakguard.schemas import Finding, Severity


def test_scoring_no_findings():
    """Verify zero score and no_exposure band when no findings exist."""
    res = score_message("Hello team, great job on the release!", [])
    assert res.overall_rule_score == 0.0
    assert res.risk_band == "no_exposure"
    assert res.max_severity == Severity.LOW


def test_scoring_high_risk_secret():
    """Verify password with production context reaches high_risk_exposure band."""
    f = Finding(
        id="f1",
        entity_type="PASSWORD",
        start=20,
        end=35,
        detector="secret",
        severity=Severity.CRITICAL,
        display_value="[PASSWORD:masked]",
        rationale="credential assignment",
    )
    text = "Deploying to prod: password = 'SecretAdminPass99!'"
    res = score_message(text, [f])

    assert res.overall_rule_score >= 70.0
    assert res.risk_band == "high_risk_exposure"
    assert res.max_severity == Severity.CRITICAL
    assert any("Infrastructure or operational context" in r for r in res.rationales)


def test_scoring_benign_documentation_reducer():
    """Verify documentation marker reduces risk score below high risk."""
    f = Finding(
        id="f1",
        entity_type="EMAIL",
        start=10,
        end=29,
        detector="regex",
        severity=Severity.LOW,
        display_value="support@example.com",
        rationale="RFC documentation-reserved email domain",
    )
    text = "Contact support@example.com for API documentation questions."
    res = score_message(text, [f])

    assert res.risk_band == "no_exposure"
    assert any("Documentation, mock, or test markers" in r for r in res.rationales)


def test_scoring_multi_entity_cooccurrence_booster():
    """Verify co-occurrence of identity documents with names/contacts triggers booster."""
    f_aadhaar = Finding(
        id="f1",
        entity_type="AADHAAR",
        start=10,
        end=24,
        detector="regex",
        severity=Severity.HIGH,
        display_value="9999...15",
        rationale="12-digit Indian national identity number passing Verhoeff checksum",
    )
    f_pan = Finding(
        id="f2",
        entity_type="PAN",
        start=30,
        end=40,
        detector="regex",
        severity=Severity.HIGH,
        display_value="ABCDE1234F",
        rationale="Indian Permanent Account Number",
    )
    text = "KYC file: 9999 4105 2815, PAN ABCDE1234F"
    res = score_message(text, [f_aadhaar, f_pan])

    assert res.overall_rule_score >= 50.0
    assert any("co-occur" in r.lower() for r in res.rationales)
