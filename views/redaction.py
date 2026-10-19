"""Redaction Studio view for LEAKGUARD.

Provides side-by-side text redaction with configurable modes (placeholder,
mask, remove), highlighting, sanitized text/metadata download, and edge-case
demonstrations (overlapping findings and Unicode combining marks).
"""

from __future__ import annotations

import json

import streamlit as st

from leakguard.config import settings
from leakguard.detection.pipeline import Pipeline
from leakguard.export.safe_export import export_findings_json
from leakguard.schemas import ScanResult
from leakguard.ui.render import render_annotated

REDACTION_SAMPLES = {
    "Custom Input (Type or Paste)": "",
    "Standard Multi-Entity PII": (
        "Dear Support, my name is Marcus Brody, contact email marcus.brody@example.com, "
        "mobile +1-555-0188. My PAN is ABCDE1234F and Aadhaar is 9876 5432 1098."
    ),
    "Overlapping & Adjacent Credentials": (
        "DevOps notification: developer John Doe (john.doe@example.com) generated GitHub token "
        "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456 and test card 4532-0150-1234-5678 for staging."
    ),
    "Unicode Combining Marks & Emoji Sample": (
        "Customer service note: café manager René François (email: rené.françois@example.fr, "
        "mobile: +33 1 42 68 55 55) 🔐 requested password reset for account Hunter2#123."
    ),
}

MODE_DESCRIPTIONS = {
    "placeholder": (
        "Replaces sensitive entities with descriptive placeholders like "
        "[EMAIL], [CARD], [SECRET_TOKEN]."
    ),
    "mask": "Overwrites sensitive characters with asterisks (***) matching the span length.",
    "remove": "Completely excises the sensitive text span from the document.",
}


def _get_pipeline() -> Pipeline:
    if "pipeline" not in st.session_state:
        st.session_state["pipeline"] = Pipeline()
    return st.session_state["pipeline"]


def render_redaction() -> None:
    """Render the Redaction Studio interface."""
    st.title("Redaction Studio")
    st.markdown(
        "Safely sanitize messages and logs before export or sharing. Inspect side-by-side "
        "previews across redaction modes."
    )

    # Required Warning Banner
    st.warning(
        "⚠️ **Automatic Redaction Notice:** Automatic redaction reduces risk but cannot guarantee "
        "100% omission of all sensitive context. Novel structures or conversational leaks "
        "may require manual verification. Always perform human verification before dissemination."
    )

    # Session State keys
    if "redaction_input" not in st.session_state:
        st.session_state["redaction_input"] = ""
    if "redaction_result" not in st.session_state:
        st.session_state["redaction_result"] = None
    if "redaction_selected_sample" not in st.session_state:
        st.session_state["redaction_selected_sample"] = "Custom Input (Type or Paste)"
    if "redaction_mode" not in st.session_state:
        st.session_state["redaction_mode"] = settings.default_redaction_mode

    max_len = settings.max_input_length

    # Sample Picker
    def on_sample_change() -> None:
        choice = st.session_state["redaction_sample_picker"]
        st.session_state["redaction_selected_sample"] = choice
        sample_text = REDACTION_SAMPLES[choice]
        if sample_text:
            st.session_state["redaction_text_area"] = sample_text
            st.session_state["redaction_input"] = sample_text

    st.selectbox(
        "Select a Demonstration Sample (Includes Overlap & Unicode Cases):",
        options=list(REDACTION_SAMPLES.keys()),
        index=list(REDACTION_SAMPLES.keys()).index(st.session_state["redaction_selected_sample"]),
        key="redaction_sample_picker",
        on_change=on_sample_change,
        help="Test standard PII, overlapping matches, or Unicode combining characters.",
    )

    # Input Area
    input_text = st.text_area(
        "Text to Redact:",
        value=st.session_state.get("redaction_input", ""),
        height=140,
        key="redaction_text_area",
        placeholder="Paste text requiring sanitization here...",
    )
    st.session_state["redaction_input"] = input_text

    char_count = len(input_text)
    is_over_limit = char_count > max_len

    # Redaction Mode Selector
    col_mode, col_mode_info = st.columns([2, 3])
    with col_mode:
        selected_mode = st.radio(
            "Redaction Mode:",
            options=["placeholder", "mask", "remove"],
            index=["placeholder", "mask", "remove"].index(st.session_state["redaction_mode"]),
            key="redaction_mode_radio",
            horizontal=True,
        )
        st.session_state["redaction_mode"] = selected_mode

    with col_mode_info:
        st.info(f"**{selected_mode.capitalize()} Mode:** {MODE_DESCRIPTIONS[selected_mode]}")

    def on_clear_redaction() -> None:
        st.session_state["redaction_input"] = ""
        st.session_state["redaction_text_area"] = ""
        st.session_state["redaction_result"] = None
        st.session_state["redaction_selected_sample"] = "Custom Input (Type or Paste)"

    # Actions
    col_btn_run, col_btn_clear, _ = st.columns([2, 2, 6])
    with col_btn_run:
        redact_clicked = st.button("🛡️ Redact & Sanitize", type="primary", use_container_width=True)
    with col_btn_clear:
        st.button(
            "🧹 Clear",
            key="redaction_clear_btn",
            on_click=on_clear_redaction,
            use_container_width=True,
        )

    if redact_clicked:
        if not input_text.strip():
            st.info("Please enter or select text before running redaction.")
            st.session_state["redaction_result"] = None
        elif is_over_limit:
            st.error(
                f"Input text exceeds maximum allowed length of {max_len:,} characters "
                f"(received {char_count:,} characters). Please reduce the input size."
            )
            st.session_state["redaction_result"] = None
        else:
            with st.spinner("Executing detection and span redaction..."):
                try:
                    pipeline = _get_pipeline()
                    res = pipeline.scan(input_text, redact=True, redaction_mode=selected_mode)
                    st.session_state["redaction_result"] = res
                except ValueError as exc:
                    st.error(str(exc))
                    st.session_state["redaction_result"] = None
                except Exception:
                    st.error(
                        "An error occurred during redaction. Raw input text has been safeguarded."
                    )
                    st.session_state["redaction_result"] = None

    # Redaction Output & Side-by-Side Comparison
    result: ScanResult | None = st.session_state.get("redaction_result")
    if result is not None:
        st.markdown("---")
        st.markdown("### Side-by-Side Verification")

        # Metric summary strip
        st.markdown(
            f"""
            <div class="leakguard-card leakguard-reveal" style="font-size: 0.9rem;">
                Processed <strong>{result.raw_text_length}</strong> chars in
                <strong>{result.duration_ms:.1f}ms</strong>.
                Redacted <strong>{len(result.findings)}</strong> sensitive entities using
                <strong>{selected_mode}</strong> mode.
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("**Original Text (Annotated Findings):**")
            annotated_html = render_annotated(input_text, result.findings)
            card_style = "min-height: 180px; white-space: pre-wrap; word-break: break-word;"
            st.markdown(
                f'<div class="leakguard-card" style="{card_style}">{annotated_html}</div>',
                unsafe_allow_html=True,
            )

        with col_right:
            st.markdown("**Sanitized Output (Ready for Sharing):**")
            sanitized_text = result.redacted_text or ""
            st.code(sanitized_text, language="text")

        # Download options
        st.markdown("---")
        st.markdown("**Export Sanitized Results:**")
        col_dl_txt, col_dl_json, _ = st.columns([3, 3, 4])
        with col_dl_txt:
            st.download_button(
                label="📥 Download Sanitized Text (.txt)",
                data=sanitized_text,
                file_name="sanitized_message.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with col_dl_json:
            export_payload = {
                "processed_at": result.processed_at,
                "redaction_mode": selected_mode,
                "raw_text_length": result.raw_text_length,
                "sanitized_text_length": len(sanitized_text),
                "findings": json.loads(export_findings_json(result.findings)),
            }
            st.download_button(
                label="📥 Download Findings Metadata (.json)",
                data=json.dumps(export_payload, indent=2),
                file_name="redaction_findings_metadata.json",
                mime="application/json",
                use_container_width=True,
            )


if __name__ == "__main__" or "streamlit" in __name__:
    render_redaction()
