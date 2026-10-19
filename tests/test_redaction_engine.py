"""Unit and property-based tests for segment-based redaction engine.

Includes property-based testing over 1,000 generated cases asserting:
1. Non-span text invariance (characters outside entity spans are 100% unchanged)
2. Offset mapping consistency
3. Redaction mode conformance
"""

import random

from leakguard.redaction.engine import redact_text
from leakguard.schemas import Finding, Severity


def test_redaction_modes():
    """Verify placeholder, mask, and remove redaction behaviors."""
    text = "User email is alice@corp.in and phone is 9876543210."
    f_email = Finding(
        id="f1",
        entity_type="EMAIL",
        start=14,
        end=27,
        detector="regex",
        severity=Severity.MEDIUM,
        display_value="alice@corp.in",
        rationale="email",
    )
    f_phone = Finding(
        id="f2",
        entity_type="PHONE",
        start=41,
        end=51,
        detector="regex",
        severity=Severity.MEDIUM,
        display_value="9876543210",
        rationale="phone",
    )
    findings = [f_email, f_phone]

    # 1. Placeholder mode
    res_ph = redact_text(text, findings, mode="placeholder")
    assert res_ph.redacted_text == "User email is [REDACTED_EMAIL] and phone is [REDACTED_PHONE]."
    assert res_ph.entities_redacted_count == 2
    assert len(res_ph.original_to_output_spans) == 2

    # 2. Mask mode
    res_mask = redact_text(text, findings, mode="mask", reveal_last_chars=2)
    # email: 13 chars -> 11 asterisks + 'in'
    assert "User email is ***********in and phone is ********10." == res_mask.redacted_text

    # 3. Remove mode
    res_rem = redact_text(text, findings, mode="remove")
    assert res_rem.redacted_text == "User email is  and phone is ."


def test_redaction_property_tests_1000_cases():
    """Property test verifying non-span text invariance over 1,000 generated cases (seed=42).

    Property: For every text slice between finding boundaries, text[last_end:f.start]
    must appear exactly unchanged in the output string.
    """
    seed = 42
    rng = random.Random(seed)
    num_cases = 1000

    words = [
        "alpha",
        "beta",
        "gamma",
        "delta",
        "system",
        "transfer",
        "user",
        "internal",
        "data",
        "log",
    ]
    entity_types = ["EMAIL", "CARD", "AADHAAR", "PAN", "PASSWORD", "API_KEY"]

    for case_idx in range(num_cases):
        # Generate random sentence fragments with embedded entity slots
        num_segments = rng.randint(1, 6)
        text_parts = []
        simulated_findings = []
        current_len = 0

        for seg_idx in range(num_segments):
            # Normal text fragment
            prefix = " ".join(rng.choice(words) for _ in range(rng.randint(2, 5))) + " "
            text_parts.append(prefix)
            current_len += len(prefix)

            # Simulated entity
            ent_type = rng.choice(entity_types)
            val = f"VAL_{ent_type}_{rng.randint(1000, 9999)}"
            start = current_len
            end = start + len(val)
            text_parts.append(val)
            current_len += len(val)

            simulated_findings.append(
                Finding(
                    id=f"case_{case_idx}_f_{seg_idx}",
                    entity_type=ent_type,
                    start=start,
                    end=end,
                    detector="regex",
                    severity=Severity.HIGH,
                    display_value=f"[MASKED_{ent_type}]",
                    rationale="property test",
                )
            )

        full_text = "".join(text_parts)

        # Apply redaction
        result = redact_text(full_text, simulated_findings, mode="placeholder")

        # Invariance Assertion 1: Length of span mappings matches findings count
        assert len(result.original_to_output_spans) == len(simulated_findings)

        # Invariance Assertion 2: Non-entity text is strictly identical
        last_orig_end = 0
        last_out_end = 0
        for orig_span, out_span in result.original_to_output_spans:
            orig_s, orig_e = orig_span
            out_s, out_e = out_span

            # Slice of original text prior to entity
            orig_slice = full_text[last_orig_end:orig_s]
            # Slice of output text prior to entity replacement
            out_slice = result.redacted_text[last_out_end:out_s]

            assert orig_slice == out_slice, (
                f"Non-span text corrupted in case {case_idx}!\n"
                f"Expected: '{orig_slice}'\nGot: '{out_slice}'"
            )

            last_orig_end = orig_e
            last_out_end = out_e

        # Check final trailing segment
        assert full_text[last_orig_end:] == result.redacted_text[last_out_end:]
