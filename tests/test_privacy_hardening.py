"""Comprehensive privacy, security hardening, and threat-model verification tests.

Verifies:
1. CSV formula-injection neutralization on all trigger prefixes (=, +, -, @, tab, CR, LF).
2. Display value masking rule (type + length bucket + masked form; 0-char default).
3. Session-isolated random IDs and unguessable HMAC pseudonyms.
4. Input cap enforcement and safe error messages (no raw text echoed).
5. XSS and markdown payload escaping in ui/render.py.
6. Zero cache storage of raw user text (static AST check and pipeline runtime check).
7. Planted sentinel secret scrubbed from all logging records (success and failure).
8. Zero outbound network calls across all modules in src/leakguard.
"""

from __future__ import annotations

import ast
import io
from pathlib import Path

import pytest

from leakguard.detection.pipeline import Pipeline
from leakguard.export.safe_export import (
    export_findings_csv,
    export_receipt_csv,
    format_safe_display_value,
    get_length_bucket,
    neutralize_csv_formula,
)
from leakguard.logging_config import configure_logging, get_privacy_filter
from leakguard.schemas import Finding, ScanReceipt, Severity
from leakguard.session.security import SessionSecurity, generate_session_id
from leakguard.ui.render import render_annotated


# ---------------------------------------------------------------------------
# 1. CSV Formula-Injection Neutralization
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "prefix,payload",
    [
        ("=", "=SUM(A1:B10)"),
        ("+", "+cmd|'/c calc'!A0"),
        ("-", "-10+20"),
        ("@", "@SUM(1+1)"),
        ("\t", "\t=cmd|'/c calc'!A0"),
        ("\r", "\r=1+1"),
        ("\n", "\n=1+1"),
    ],
)
def test_formula_injection_neutralized_in_isolation(prefix: str, payload: str):
    """Ensure any string starting with a formula trigger is prepended with a single quote."""
    neutralized = neutralize_csv_formula(payload)
    assert neutralized.startswith("'"), f"Failed for prefix: {repr(prefix)}"
    assert neutralized[1:] == payload


def test_safe_export_findings_csv_neutralizes_injection():
    """Ensure exported CSV neutralizes malicious payloads in finding fields."""
    malicious_finding = Finding(
        id="=cmd|'/c calc'!A0",
        entity_type="+EXCEL_FORMULA",
        start=0,
        end=10,
        detector="@detector",
        severity=Severity.HIGH,
        display_value="-display_val",
        rationale="\t=evil_formula()",
    )
    csv_out = export_findings_csv([malicious_finding])

    # Ensure dangerous prefixes are neutralized with leading quote
    assert "'=cmd|'/c calc'!A0" in csv_out
    assert "'+EXCEL_FORMULA" in csv_out
    assert "'@detector" in csv_out
    assert "[+EXCEL_FORMULA | 9-20 chars | ********]" in csv_out
    assert "'\t=evil_formula()" in csv_out


def test_safe_export_receipt_csv_neutralizes_injection():
    """Ensure receipt CSV export neutralizes formula prefixes."""
    receipt = ScanReceipt(
        id="=malicious_rcpt",
        timestamp="+2026-10-19T00:00:00Z",
        text_length=100,
        duration_ms=12.5,
        detectors_run=("regex",),
        finding_counts_by_type={},
        finding_counts_by_severity={},
        max_severity=Severity.LOW,
        risk_band="@high_risk",
        overall_rule_score=0.1,
    )
    csv_out = export_receipt_csv(receipt)
    assert "'=malicious_rcpt" in csv_out
    assert "'+2026-10-19" in csv_out
    assert "'@high_risk" in csv_out


# ---------------------------------------------------------------------------
# 2. Display Value Rule (Type + Length Bucket + Masked Form)
# ---------------------------------------------------------------------------
def test_length_bucket_categorization():
    """Verify length bucketing into standard coarse ranges."""
    assert get_length_bucket(4) == "1-8 chars"
    assert get_length_bucket(8) == "1-8 chars"
    assert get_length_bucket(12) == "9-20 chars"
    assert get_length_bucket(20) == "9-20 chars"
    assert get_length_bucket(25) == "21-50 chars"
    assert get_length_bucket(50) == "21-50 chars"
    assert get_length_bucket(64) == "51+ chars"


def test_safe_display_value_zero_reveal_default():
    """Default maximum reveal must be 0 characters, completely masking values."""
    res = format_safe_display_value(
        entity_type="EMAIL",
        length=18,
        raw_val="alice@corp-sec.com",
        max_reveal=0,
    )
    assert res == "[EMAIL | 9-20 chars | ********]"
    assert "alice" not in res
    assert "corp" not in res


def test_safe_display_value_configurable_reveal():
    """Allowed reveal must expose only the trailing N characters up to limit."""
    res = format_safe_display_value(
        entity_type="PHONE",
        length=10,
        raw_val="9876543210",
        max_reveal=2,
    )
    assert res == "[PHONE | 9-20 chars | ********10]"


def test_safe_display_value_credentials_never_reveal():
    """Passwords and tokens must NEVER reveal characters even if max_reveal > 0."""
    for ent_type in ("PASSWORD", "API_KEY", "SECRET_TOKEN"):
        res = format_safe_display_value(
            entity_type=ent_type,
            length=32,
            raw_val="super_secret_production_api_key_xyz",
            max_reveal=4,
        )
        assert res == f"[{ent_type} | 21-50 chars | ********]"
        assert "xyz" not in res
        assert "secret" not in res


# ---------------------------------------------------------------------------
# 3. Session Security, Isolated IDs, and HMAC Pseudonymity
# ---------------------------------------------------------------------------
def test_session_ids_unique_per_session():
    """Verify session IDs are distinct random UUID4 strings."""
    s1 = SessionSecurity()
    s2 = SessionSecurity()
    assert s1.session_id != s2.session_id
    assert generate_session_id() != generate_session_id()


def test_hmac_pseudonyms_differ_across_sessions():
    """Identical sensitive values in different sessions MUST yield distinct pseudonyms."""
    s1 = SessionSecurity()
    s2 = SessionSecurity()

    sensitive_pii = "priya.sharma@internal.corp.in"
    p1 = s1.generate_pseudonym(sensitive_pii)
    p2 = s2.generate_pseudonym(sensitive_pii)

    assert p1 != p2
    assert s1.verify_pseudonym(sensitive_pii, p1) is True
    assert s2.verify_pseudonym(sensitive_pii, p1) is False


def test_pseudonym_cannot_be_inverted_by_simple_hash_guessing():
    """Guarantees that an observer guessing sha256(val) cannot match the session pseudonym."""
    import hashlib

    s = SessionSecurity()
    known_val = "secret_password_123"
    psn = s.generate_pseudonym(known_val)

    # An attacker computing plain sha256 guesses gets no match
    naive_hash = hashlib.sha256(known_val.encode("utf-8")).hexdigest()
    assert naive_hash[:12] != psn.replace("psn_", "")


# ---------------------------------------------------------------------------
# 4. Input Cap and Safe Error Messages
# ---------------------------------------------------------------------------
def test_pipeline_enforces_input_cap_without_echoing_raw_text():
    """Ensure oversized inputs raise ValueError with character count, never echoing text."""
    p = Pipeline(max_input_length=50)
    oversized_secret_text = "TOP_SECRET_PAYLOAD_" * 10  # 190 chars

    with pytest.raises(ValueError) as exc_info:
        p.scan(oversized_secret_text)

    msg = str(exc_info.value)
    assert "Input text exceeds maximum allowed length of 50 characters" in msg
    assert "TOP_SECRET" not in msg
    assert oversized_secret_text not in msg


def test_pipeline_type_error_does_not_echo_raw_text():
    """Ensure invalid types raise TypeError without echoing arbitrary content."""
    p = Pipeline()
    with pytest.raises(TypeError) as exc_info:
        p.scan(12345)  # type: ignore

    assert "Input text must be a string" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 5. UI Render Skeleton & XSS/Markdown Payload Neutralization
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "payload,forbidden_pattern",
    [
        ("<script>alert('xss')</script>", "<script>"),
        ("<img src=x onerror=alert(1)>", "<img"),
        ("[click](javascript:alert(1))", "<a href="),
        ("`curl http://attacker.com`", "<script>"),
        ("Hello & Goodbye <World> '\"'", "& < >"),
    ],
)
def test_render_annotated_escapes_xss_and_markdown(payload: str, forbidden_pattern: str):
    """Verify render_annotated strictly html.escapes all normal and finding segments."""
    rendered = render_annotated(payload, [])
    assert forbidden_pattern not in rendered
    assert "<script>" not in rendered
    assert "<img" not in rendered


def test_render_annotated_with_malicious_finding_attributes():
    """Ensure malicious content inside Finding fields and spans is completely escaped."""
    malicious_text = "Target: <script>alert(document.cookie)</script> is vulnerable."
    findings = [
        Finding(
            id="<script>bad_id</script>",
            entity_type='<b onmouseover="alert(1)">EVIL</b>',
            start=8,
            end=47,
            detector='"><script>',
            severity=Severity.HIGH,
            display_value="[EVIL:masked]",
            rationale='"><img src=x onerror=alert(2)>',
        )
    ]
    html_out = render_annotated(malicious_text, findings)

    assert "<script>" not in html_out
    assert "</script>" not in html_out
    assert "<img" not in html_out
    assert 'onmouseover="' not in html_out
    assert "&lt;script&gt;" in html_out
    assert '<mark class="leakguard-finding finding-high"' in html_out


# ---------------------------------------------------------------------------
# 6. Cache and Global State Isolation
# ---------------------------------------------------------------------------
def test_no_streamlit_cache_on_user_text():
    """Static AST check verifying no st.cache_* decorators exist on functions taking text."""
    src_dir = Path("src/leakguard")
    for py_file in src_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    dec_name = ""
                    if isinstance(decorator, ast.Name):
                        dec_name = decorator.id
                    elif isinstance(decorator, ast.Attribute):
                        dec_name = decorator.attr
                    elif isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Name):
                            dec_name = decorator.func.id
                        elif isinstance(decorator.func, ast.Attribute):
                            dec_name = decorator.func.attr

                    # Check for cache decorators
                    if "cache" in dec_name.lower():
                        arg_names = [arg.arg for arg in node.args.args]
                        assert "text" not in arg_names, (
                            f"Function '{node.name}' in {py_file} caches user text!"
                        )


def test_pipeline_runtime_does_not_accumulate_state():
    """Runtime test verifying Pipeline does not accumulate scanned raw text in object state."""
    p = Pipeline()
    secret_a = "alpha_secret_text_9876543210"
    secret_b = "beta_secret_text_1234567890"

    p.scan(secret_a)
    p.scan(secret_b)

    # Check instance dictionary and attributes
    for attr, val in p.__dict__.items():
        assert secret_a not in str(val), f"Secret A found in pipeline attribute '{attr}'"
        assert secret_b not in str(val), f"Secret B found in pipeline attribute '{attr}'"


# ---------------------------------------------------------------------------
# 7. Privacy Logging & Planted Sentinel Scrubbing
# ---------------------------------------------------------------------------
def test_planted_sentinel_never_logged_during_success_or_failure():
    """Ensure a planted sentinel secret NEVER appears in logs during successful or failing scans."""
    log_stream = io.StringIO()
    configure_logging(level="INFO", stream=log_stream)
    privacy_filter = get_privacy_filter()

    planted_sentinel = "PLANTED_SENTINEL_SECRET_TOKEN_XYZ987654321"
    privacy_filter.register_sentinel(planted_sentinel)

    try:
        p = Pipeline(max_input_length=100)

        # 1. Successful scan with sentinel
        valid_text = f"Deployment token is: {planted_sentinel}"
        p.scan(valid_text)

        # 2. Failing scan with sentinel (exceeding length cap)
        failing_text = f"{planted_sentinel} " * 10
        with pytest.raises(ValueError):
            p.scan(failing_text)

        captured_logs = log_stream.getvalue()
        assert planted_sentinel not in captured_logs
        assert (
            "[REDACTED_SENTINEL]" in captured_logs
            or "Scan initiated" in captured_logs
            or "Scan rejected" in captured_logs
        )
    finally:
        privacy_filter.clear_sentinels()


# ---------------------------------------------------------------------------
# 8. Zero Outbound Network Calls Static Verification
# ---------------------------------------------------------------------------
def test_no_outbound_network_calls_in_src():
    """Static AST check verifying zero external network libraries are imported in src/leakguard."""
    forbidden_modules = {
        "requests",
        "urllib.request",
        "http.client",
        "aiohttp",
        "httpx",
        "socket",
    }
    src_dir = Path("src/leakguard")

    for py_file in src_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_modules:
                        assert not alias.name.startswith(forbidden), (
                            f"Forbidden network import '{alias.name}' detected in {py_file}"
                        )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for forbidden in forbidden_modules:
                    assert not mod.startswith(forbidden), (
                        f"Forbidden network from-import '{mod}' detected in {py_file}"
                    )
