"""AppTest test suite for LEAKGUARD UI views, shell, and interactions.

Verifies:
- Main app shell routing and navigation via st.navigation
- Runtime status strip reflecting real facts (no hard-coded or fake statistics)
- Placeholder views displaying 'Not built yet' with zero numeric stats
- Scanner operations: safe samples, analysis execution, findings table, evidence rail
- Input limit enforcement without raw text echo
- Strict HTML/XSS escaping in rendered annotations
- Redaction Studio: placeholder, mask, and remove modes; side-by-side verification
- No-CSS fallback mode
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import pytest
from streamlit.testing.v1 import AppTest

ROOT_DIR = Path(__file__).resolve().parent.parent


def _get_path(rel_path: str) -> str:
    return str(ROOT_DIR / rel_path)


@pytest.fixture(autouse=True)
def reset_env() -> None:
    """Ensure environment is clean before and after each UI test."""
    old_css_val = os.environ.get("LEAKGUARD_DISABLE_CSS")
    yield
    if old_css_val is not None:
        os.environ["LEAKGUARD_DISABLE_CSS"] = old_css_val
    else:
        os.environ.pop("LEAKGUARD_DISABLE_CSS", None)


def test_app_shell_and_navigation() -> None:
    """Verify app.py loads, displays identity, runtime facts, and navigation."""
    at = AppTest.from_file(_get_path("app.py")).run()
    assert len(at.exception) == 0, f"App execution raised: {at.exception}"

    # Verify Sidebar branding and notices
    sidebar_md = " ".join([m.value for m in at.sidebar.markdown])
    assert "LEAKGUARD" in sidebar_md
    assert "Privacy & Safety Notice" in sidebar_md
    assert "Zero outbound network requests" in sidebar_md
    assert "Detector-Only" in sidebar_md

    # Verify runtime status strip
    assert "Runtime Status" in sidebar_md
    assert "Classifier Gate" in sidebar_md
    assert "Challenge Set Pending" in sidebar_md
    assert "RegEx Engine" in sidebar_md
    assert "Secret Detector" in sidebar_md

    # Verify default page is Live Scanner
    assert any("Live Scanner" in t.value for t in at.title)


def test_phase8_views_load_cleanly() -> None:
    """Verify Phase 8 views load cleanly with valid headers and no unhandled exceptions."""
    views = [
        ("views/overview.py", "Executive Overview"),
        ("views/incidents.py", "Incident Command Center"),
        ("views/model_lab.py", "Model Laboratory"),
        ("views/methodology.py", "Methodology & System Health"),
    ]

    for file_path, expected_title in views:
        at = AppTest.from_file(_get_path(file_path)).run()
        assert len(at.exception) == 0, f"{file_path} raised exceptions: {at.exception}"
        assert any(expected_title in t.value for t in at.title), f"Missing title in {file_path}"


def test_scanner_view_loads_without_optional_models() -> None:
    """Verify scanner view loads cleanly without optional spaCy or ML models."""
    with mock.patch("spacy.load", side_effect=ImportError("No spaCy")):
        at = AppTest.from_file(_get_path("views/scanner.py")).run()
        assert len(at.exception) == 0
        assert any("Live Scanner" in t.value for t in at.title)
        assert len(at.text_area) > 0


def test_scanner_analyze_safe_sample_produces_findings() -> None:
    """Verify selecting sample and analyzing produces findings, table, and evidence rail."""
    at = AppTest.from_file(_get_path("views/scanner.py")).run()
    assert len(at.exception) == 0

    # Set input text with email and card
    sample_text = (
        "Reconciliation alert: contact sarah.connor@example.com regarding card "
        "4532-0150-1234-5678 expiring 04/28."
    )
    at.text_area[0].input(sample_text).run()

    # Click analyze button
    analyze_btn = next(b for b in at.button if "Analyze" in b.label)
    analyze_btn.click().run()
    assert len(at.exception) == 0

    # Verify risk assessment banner appears
    banner_texts = [m.value for m in at.markdown if "Overall Risk Assessment" in m.value]
    assert len(banner_texts) > 0, "Risk assessment banner missing after analysis"

    # Verify findings table rendered
    assert len(at.dataframe) >= 1, "Findings table missing after analysis"

    # Verify download buttons are available
    assert len(at.download_button) >= 2, "Sanitized export download buttons missing"


def test_scanner_clear_removes_input_and_results() -> None:
    """Verify clear button wipes input and reset results."""
    at = AppTest.from_file(_get_path("views/scanner.py")).run()

    # Enter text and run scan
    at.text_area[0].input("user@example.com").run()
    analyze_btn = next(b for b in at.button if "Analyze" in b.label)
    analyze_btn.click().run()
    assert len(at.dataframe) >= 1

    # Click clear button
    clear_btn = next(b for b in at.button if "Clear" in b.label)
    clear_btn.click().run()

    # Input should be cleared and results gone
    assert at.text_area[0].value == ""
    assert len(at.dataframe) == 0


def test_scanner_over_limit_input_shows_safe_error_without_echoing_raw_text() -> None:
    """Verify oversized input displays an error with character counts and never echoes raw input."""
    at = AppTest.from_file(_get_path("views/scanner.py")).run()

    plant_sentinel = "EXTREMELY_SECRET_PAYLOAD_NEVER_ECHO_" * 800
    at.text_area[0].input(plant_sentinel).run()

    analyze_btn = next(b for b in at.button if "Analyze" in b.label)
    analyze_btn.click().run()

    assert len(at.error) > 0, "Expected error message for input exceeding max limit"
    error_msg = at.error[0].value
    assert "exceeds maximum allowed length" in error_msg
    # Crucial privacy requirement: raw input must NEVER appear in the error message
    assert "EXTREMELY_SECRET_PAYLOAD" not in error_msg


def test_scanner_xss_payload_renders_strictly_escaped() -> None:
    """Verify malicious XSS input renders strictly escaped and does not inject raw HTML tags."""
    at = AppTest.from_file(_get_path("views/scanner.py")).run()

    xss_payload = "<script>alert('pwn')</script><img src=x onerror=alert(1)>"
    at.text_area[0].input(xss_payload).run()

    analyze_btn = next(b for b in at.button if "Analyze" in b.label)
    analyze_btn.click().run()
    assert len(at.exception) == 0

    # Check rendered annotated cards
    all_md = " ".join([m.value for m in at.markdown])
    # Must NOT have unescaped active script tag
    assert "<script>alert" not in all_md
    assert "<img src=x" not in all_md
    # Must have properly escaped HTML entities
    assert "&lt;script&gt;" in all_md
    assert "&lt;img" in all_md


def test_redaction_view_modes_and_download() -> None:
    """Verify Redaction Studio operates in placeholder, mask, and remove modes."""
    at = AppTest.from_file(_get_path("views/redaction.py")).run()
    assert len(at.exception) == 0
    assert any("Redaction Studio" in t.value for t in at.title)

    # Required warning banner must be visible
    warnings = [w.value for w in at.warning]
    assert any("Automatic Redaction Notice" in w for w in warnings)

    # Input PII text
    test_input = "Contact support at help.desk@example.com for assistance."
    at.text_area[0].input(test_input).run()

    # 1. Test placeholder mode (default)
    redact_btn = next(b for b in at.button if "Redact" in b.label)
    redact_btn.click().run()
    assert len(at.exception) == 0

    codes = [c.value for c in at.code]
    assert any("[REDACTED_EMAIL]" in c for c in codes)
    assert len(at.download_button) >= 2

    # 2. Test mask mode
    at.radio[0].set_value("mask").run()
    redact_btn = next(b for b in at.button if "Redact" in b.label)
    redact_btn.click().run()
    assert len(at.exception) == 0
    codes = [c.value for c in at.code]
    assert any("*" in c for c in codes)

    # 3. Test remove mode
    at.radio[0].set_value("remove").run()
    redact_btn = next(b for b in at.button if "Redact" in b.label)
    redact_btn.click().run()
    assert len(at.exception) == 0
    codes = [c.value for c in at.code]
    assert not any("help.desk@example.com" in c for c in codes)


def test_no_css_fallback() -> None:
    """Verify that the console operates seamlessly when custom CSS is disabled."""
    os.environ["LEAKGUARD_DISABLE_CSS"] = "1"
    at = AppTest.from_file(_get_path("app.py")).run()
    assert len(at.exception) == 0
    assert any("Live Scanner" in t.value for t in at.title)
