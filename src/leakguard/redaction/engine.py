"""Segment-based redaction engine for sensitive text sanitization.

Builds sanitized output by concatenating non-sensitive text slices and replacement tokens
in a single pass, avoiding repeated in-place string replacements that corrupt character offsets.

Supports three redaction modes:
- placeholder (default): Replaces entity with typed tag, e.g. `[REDACTED_EMAIL]`
- mask: Masks characters with asterisk (`*`), optionally retaining last 2 characters
- remove: Completely removes the entity substring
"""

from __future__ import annotations

from collections.abc import Sequence

from leakguard.schemas import Finding, RedactionResult


def redact_text(
    text: str,
    findings: Sequence[Finding],
    mode: str = "placeholder",
    mask_char: str = "*",
    reveal_last_chars: int = 2,
) -> RedactionResult:
    """Redact sensitive findings from text in a single non-destructive pass.

    Returns:
        RedactionResult containing the redacted text, mode, count of entities redacted,
        and an exact mapping of ((original_start, original_end), (output_start, output_end)).
    """
    if not findings:
        return RedactionResult(
            redacted_text=text,
            mode=mode,
            original_to_output_spans=(),
            entities_redacted_count=0,
        )

    # Sort findings strictly by start offset
    sorted_findings = sorted(findings, key=lambda f: f.start)

    output_segments: list[str] = []
    span_mappings: list[tuple[tuple[int, int], tuple[int, int]]] = []

    last_index = 0
    current_output_len = 0

    for f in sorted_findings:
        # 1. Append unmodified non-entity text preceding this finding
        if f.start > last_index:
            unmodified_slice = text[last_index : f.start]
            output_segments.append(unmodified_slice)
            current_output_len += len(unmodified_slice)

        # 2. Compute replacement string according to mode
        original_val = text[f.start : f.end]
        if mode == "placeholder":
            replacement = f"[REDACTED_{f.entity_type}]"
        elif mode == "mask":
            if len(original_val) <= reveal_last_chars or reveal_last_chars <= 0:
                replacement = mask_char * len(original_val)
            else:
                masked_part = mask_char * (len(original_val) - reveal_last_chars)
                revealed_part = original_val[-reveal_last_chars:]
                replacement = masked_part + revealed_part
        elif mode == "remove":
            replacement = ""
        else:
            raise ValueError(
                f"Unknown redaction mode '{mode}'. Choose from 'placeholder', 'mask', 'remove'."
            )

        # 3. Track output span mapping
        out_start = current_output_len
        out_end = current_output_len + len(replacement)
        span_mappings.append(((f.start, f.end), (out_start, out_end)))

        # 4. Append replacement
        output_segments.append(replacement)
        current_output_len += len(replacement)

        last_index = f.end

    # 5. Append trailing unmodified text
    if last_index < len(text):
        trailing_slice = text[last_index:]
        output_segments.append(trailing_slice)
        current_output_len += len(trailing_slice)

    redacted_str = "".join(output_segments)

    return RedactionResult(
        redacted_text=redacted_str,
        mode=mode,
        original_to_output_spans=tuple(span_mappings),
        entities_redacted_count=len(sorted_findings),
    )
