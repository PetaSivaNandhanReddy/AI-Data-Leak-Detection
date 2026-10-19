"""Privacy, security, edge cases, and adversarial input tests for the LEAKGUARD pipeline."""

import logging
import time
from pathlib import Path

import pytest

from leakguard.detection.pipeline import Pipeline
from leakguard.session.session_log import SessionLog


def test_sentinel_secret_never_leaked_in_logs_receipts_or_exceptions(caplog):
    """Verify that a planted sensitive credential never appears in logs, receipts, or exceptions.

    Planted secret is constructed dynamically from fragments to avoid static scanner alerts.
    """
    secret_prefix = "SENTINEL_" + "PLANTED_"
    secret_body = "SECRET_TOKEN_99214_SUPER_CONFIDENTIAL"
    planted_secret = secret_prefix + secret_body

    test_message = f"Database configuration error: password = '{planted_secret}' on internal node."

    pipeline = Pipeline()

    # Capture logs while running pipeline
    with caplog.at_level(logging.DEBUG):
        result = pipeline.scan(test_message, redact=True, redaction_mode="placeholder")
        receipt = pipeline.create_receipt(result)

    # 1. Assert sentinel secret never appears in any captured logs
    for record in caplog.records:
        assert planted_secret not in record.message
        assert secret_body not in record.message

    # 2. Assert sentinel secret never appears in the audit receipt
    receipt_dict = receipt.__dict__
    for _key, val in receipt_dict.items():
        assert planted_secret not in str(val)
        assert secret_body not in str(val)

    # 3. Assert sentinel secret is redacted in output text
    assert planted_secret not in result.redacted_text

    # 4. Assert display_value in findings masks the secret
    for f in result.findings:
        assert planted_secret not in f.display_value


def test_oversized_input_rejected_without_echo():
    """Verify inputs exceeding max_input_length are rejected safely without echoing raw text."""
    oversized_length = 20_001
    oversized_text = "A" * oversized_length

    pipeline = Pipeline(max_input_length=20_000)

    with pytest.raises(ValueError) as exc_info:
        pipeline.scan(oversized_text)

    error_msg = str(exc_info.value)
    assert "exceeds maximum allowed length of 20000" in error_msg
    # Ensure raw user text is never echoed in error string
    assert "AAAAA" not in error_msg


def test_empty_and_whitespace_input():
    """Verify empty and whitespace inputs produce zero findings without errors."""
    pipeline = Pipeline()
    for empty_sample in ("", "   ", "\n\n\t  \n"):
        res = pipeline.scan(empty_sample)
        assert len(res.findings) == 0
        assert res.risk_band == "no_exposure"
        assert res.overall_rule_score == 0.0


def test_unicode_and_multiline_support():
    """Verify Unicode scripts (Devanagari, Tamil, emojis) and multiline messages."""
    pipeline = Pipeline()
    multiline_unicode = (
        "नमस्ते!\n"
        "Customer: Priya Sharma 🇮🇳\n"
        "Email: priya.sharma@internal-corp.in\n"
        "Card: 4000 0012 3456 7899 💳\n"
        "धन्यवाद!"
    )
    res = pipeline.scan(multiline_unicode)
    assert len(res.findings) >= 2

    # Verify character offsets align exactly in multiline Unicode text
    for f in res.findings:
        actual_slice = multiline_unicode[f.start : f.end]
        if f.entity_type == "EMAIL":
            assert actual_slice == "priya.sharma@internal-corp.in"
        elif f.entity_type == "CARD":
            assert actual_slice == "4000 0012 3456 7899"


def test_adversarial_timing_linear_complexity():
    """Adversarial test verifying linear-time regex execution without catastrophic backtracking."""
    pipeline = Pipeline()

    # Adversarial patterns that typically trigger exponential backtracking in vulnerable regexes
    pathological_strings = [
        "a" * 15_000,
        ("password=" + "a" * 100) * 100,
        ("4000 " * 2000),
        ("support@" + "a" * 200) * 50,
    ]

    for sample in pathological_strings:
        start = time.perf_counter()
        _ = pipeline.scan(sample)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        # Entire scan must complete in under 250 milliseconds
        assert elapsed_ms < 250.0, (
            f"Adversarial scan took {elapsed_ms:.1f}ms on {len(sample)} chars"
        )


def test_session_log_zero_raw_text_storage():
    """Verify SessionLog stores only sanitized receipts and no raw user text."""
    session = SessionLog()
    pipeline = Pipeline()

    secret_raw = "password = 'MySecretPassword123!'"
    res = pipeline.scan(secret_raw)
    receipt = pipeline.create_receipt(res)

    session.record_receipt(receipt)
    assert session.total_scans == 1
    assert session.total_findings_count >= 1
    assert session.get_receipt(receipt.id) == receipt
    assert session.get_receipt("non_existent_id") is None

    sev_counts = session.aggregate_counts_by_severity()
    assert sev_counts.get("CRITICAL", 0) >= 1

    type_counts = session.aggregate_counts_by_type()
    assert type_counts.get("PASSWORD", 0) >= 1

    stored_receipts = session.get_receipts()
    assert len(stored_receipts) == 1

    # Assert no raw text or password in stored receipt
    receipt_str = str(stored_receipts[0].__dict__)
    assert "MySecretPassword123!" not in receipt_str
    assert "password =" not in receipt_str

    session.clear()
    assert session.total_scans == 0
    assert len(session.get_receipts()) == 0


def test_no_ui_imports_in_core_package():
    """Assert that core package src/leakguard contains zero UI imports (Streamlit, Gradio, etc.)."""
    src_dir = Path("src/leakguard")
    py_files = list(src_dir.rglob("*.py"))

    forbidden_modules = ["streamlit", "gradio", "tkinter"]

    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8")
        for line_no, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for mod in forbidden_modules:
                assert f"import {mod}" not in stripped, (
                    f"Forbidden UI import '{mod}' found in core file {py_file}:{line_no}"
                )
                assert f"from {mod}" not in stripped, (
                    f"Forbidden UI import '{mod}' found in core file {py_file}:{line_no}"
                )
