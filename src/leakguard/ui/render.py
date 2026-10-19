"""UI rendering helpers with strict HTML/XSS escaping.

Guarantees:
- Every segment (unmatched text, sensitive text within findings, entity types,
  severities, rationales) is strictly escaped via html.escape(..., quote=True).
- Neutralizes all XSS injection vectors (<script>, <img onerror>, javascript: URIs).
- Pure text output safe for inclusion in Streamlit or raw HTML contexts.
"""

from __future__ import annotations

import html
from collections.abc import Sequence

from leakguard.schemas import Finding


def render_annotated(text: str, findings: Sequence[Finding]) -> str:
    """Render text with annotated finding highlights, strictly escaping all segments.

    Args:
        text: Original unescaped input string.
        findings: Detected findings to highlight.

    Returns:
        Safe HTML string with <mark> tags around findings and all contents escaped.
    """
    if not text:
        return ""

    if not findings:
        return html.escape(text, quote=True)

    sorted_findings = sorted(findings, key=lambda f: (f.start, f.end))

    segments: list[str] = []
    cursor = 0
    total_len = len(text)

    for f in sorted_findings:
        start = max(0, min(f.start, total_len))
        end = max(start, min(f.end, total_len))

        if end <= start:
            continue

        if start < cursor:
            if end <= cursor:
                continue
            start = cursor

        if start > cursor:
            normal_slice = text[cursor:start]
            segments.append(html.escape(normal_slice, quote=True))

        finding_slice = text[start:end]
        escaped_slice = html.escape(finding_slice, quote=True)
        escaped_type = html.escape(f.entity_type, quote=True)
        escaped_sev = html.escape(f.severity.value.lower(), quote=True)
        escaped_rationale = html.escape(f.rationale, quote=True)
        escaped_id = html.escape(f.id, quote=True)

        highlight = (
            f'<mark class="leakguard-finding finding-{escaped_sev}" '
            f'data-id="{escaped_id}" '
            f'data-entity="{escaped_type}" '
            f'title="{escaped_type} ({escaped_sev.upper()}): {escaped_rationale}">'
            f"{escaped_slice}"
            f"</mark>"
        )
        segments.append(highlight)
        cursor = end

    if cursor < total_len:
        segments.append(html.escape(text[cursor:], quote=True))

    return "".join(segments)
