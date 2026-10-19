"""Unit tests for SecretDetector.

All test secrets and mock tokens are constructed dynamically from string fragments
at runtime to prevent triggering static secret scanners (gitleaks, GitHub push protection).
"""

from leakguard.detection.secret_detector import SecretDetector, shannon_entropy
from leakguard.schemas import Severity


def test_shannon_entropy():
    """Verify entropy calculations on uniform vs high-entropy strings."""
    assert shannon_entropy("") == 0.0
    assert shannon_entropy("aaaaaaaa") == 0.0
    # High entropy character set
    ent = shannon_entropy("aB3$kL9#mP1!zQ8@")
    assert ent >= 3.5


def test_secret_detector_provider_tokens():
    """Verify detection of AWS, GitHub, Slack, JWT, and PEM private keys
    constructed from fragments.
    """
    detector = SecretDetector()

    aws_key = "AK" + "IA" + "IOSFODNN7EXAMPLE"
    gh_pat = "gh" + "p_" + "TestToken123456789012345678901234567"
    slack_tok = "xox" + "b-123456789012-123456789012-AbCdEfGhIjKlMnOp"
    jwt_tok = "Bearer " + "eyJ" + "hbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozG4"
    pem_key = "-----BEGIN " + "RSA " + "PRIVATE KEY-----"

    text = (
        f"Config dump:\n"
        f"AWS_KEY: {aws_key}\n"
        f"GITHUB_TOKEN: {gh_pat}\n"
        f"SLACK_HOOK: {slack_tok}\n"
        f"AUTH: {jwt_tok}\n"
        f"{pem_key}\n"
    )

    findings = detector.detect(text)

    # AWS
    aws_findings = [f for f in findings if f.id.startswith("sec_aws")]
    assert len(aws_findings) == 1
    assert text[aws_findings[0].start : aws_findings[0].end] == aws_key

    # GitHub
    gh_findings = [f for f in findings if f.id.startswith("sec_gh")]
    assert len(gh_findings) == 1
    assert text[gh_findings[0].start : gh_findings[0].end] == gh_pat

    # Slack
    slack_findings = [f for f in findings if f.id.startswith("sec_slack")]
    assert len(slack_findings) == 1
    assert text[slack_findings[0].start : slack_findings[0].end] == slack_tok

    # JWT
    jwt_findings = [f for f in findings if f.id.startswith("sec_jwt")]
    assert len(jwt_findings) == 1

    # PEM
    pem_findings = [f for f in findings if f.id.startswith("sec_pkey")]
    assert len(pem_findings) == 1


def test_secret_detector_assignment_context():
    """Verify detection of passwords and tokens assigned to variables."""
    detector = SecretDetector()
    text = (
        "db_pass: 'SuperSecretDbAdminPass2026!'\n"
        'api_key = "LiveCloudToken9982402194"\n'
        "placeholder_pass = '<INSERT_PASSWORD_HERE>'\n"
    )

    findings = detector.detect(text)

    # The assignment detector should capture db_pass and api_key, but skip placeholder_pass
    passwords = [f for f in findings if f.entity_type == "PASSWORD"]
    assert len(passwords) == 1
    assert text[passwords[0].start : passwords[0].end] == "SuperSecretDbAdminPass2026!"
    assert passwords[0].severity == Severity.CRITICAL

    api_keys = [f for f in findings if f.entity_type == "API_KEY"]
    assert len(api_keys) == 1
    assert text[api_keys[0].start : api_keys[0].end] == "LiveCloudToken9982402194"

    # Placeholder must NOT be flagged
    assert not any("<INSERT_PASSWORD_HERE>" in text[f.start : f.end] for f in findings)


def test_secret_detector_connection_string():
    """Verify password extraction from database connection URI strings."""
    detector = SecretDetector()
    text = "Failed connecting to postgresql://admin:RootP@ssw0rd99@db.prod.internal:5432/main"
    findings = detector.detect(text)

    passwords = [f for f in findings if f.entity_type == "PASSWORD"]
    assert len(passwords) == 1
    assert text[passwords[0].start : passwords[0].end] == "RootP@ssw0rd99"
    assert "connection string" in passwords[0].rationale.lower()
