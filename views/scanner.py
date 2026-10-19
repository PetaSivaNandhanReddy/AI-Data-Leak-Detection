"""Live Scanner view for LEAKGUARD.

Provides real-time interactive text scanning, severity scoring, annotated
highlighting via html-escaped rendering, interactive evidence rail,
filtering, and sanitized export.
"""

from __future__ import annotations

import streamlit as st

from leakguard.config import settings
from leakguard.detection.pipeline import Pipeline
from leakguard.export.safe_export import (
    export_findings_csv,
    export_findings_json,
    format_safe_display_value,
)
from leakguard.schemas import ScanResult, Severity
from leakguard.session.security import SessionSecurity
from leakguard.session.session_log import SessionLog
from leakguard.ui.render import render_annotated

SAMPLE_OPTIONS = {
    "Custom Input (Type or Paste)": "",
    "Clean Message (No sensitive data)": (
        "Good morning team, the project sync is scheduled for 3:00 PM today. "
        "Please review the slide deck and bring your progress updates for sprint 4."
    ),
    "Customer Support (PII: Email, Phone, Person)": (
        "Customer message: Hello support, my name is Eleanor Vance and my account email "
        "is eleanor.vance@example.org. You can also reach me at +1-555-0199 for updates."
    ),
    "Financial Query (Card, IBAN)": (
        "Payment reconciliation notice: processed transaction on card 4532-0150-1234-5678 "
        "expiring 11/28. Source settlement bank IBAN is GB29NWBK60161331926819."
    ),
    "Developer Secrets (API Key, Token, Password)": (
        "Internal DevOps alert: please revoke token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456 "
        "and update database password Hunter2#123 before deployment."
    ),
    "Mixed Data Leak (Credentials & Identity)": (
        "Employee records update: Rajesh Kumar (PAN: ABCDE1234F, Aadhaar: 2345 6789 0123) "
        "has temporary secret wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY assigned."
    ),
    "Adversarial XSS Injection Test": (
        "<script>alert('xss')</script> <img src=x onerror='alert(1)'> "
        "[Test Link](javascript:alert(1)) `cat /etc/passwd`"
    ),
    "Oversized Input (> 20,000 Chars)": ("LEAKGUARD_OVERSIZED_PAYLOAD_" * 1000),
}

SEVERITY_ICONS = {
    Severity.CRITICAL: "🚨",
    Severity.HIGH: "🔴",
    Severity.MEDIUM: "🟡",
    Severity.LOW: "🟢",
}


def _get_pipeline() -> Pipeline:
    if "pipeline" not in st.session_state:
        st.session_state["pipeline"] = Pipeline()
    return st.session_state["pipeline"]


def _get_session_log() -> SessionLog:
    if "session_log" not in st.session_state:
        st.session_state["session_log"] = SessionLog()
    return st.session_state["session_log"]


def _get_session_security() -> SessionSecurity:
    if "session_security" not in st.session_state:
        st.session_state["session_security"] = SessionSecurity()
    return st.session_state["session_security"]


def _remediation_advice(entity_type: str, severity: Severity) -> str:
    if severity in (Severity.CRITICAL, Severity.HIGH):
        if entity_type in ("API_KEY", "SECRET_TOKEN", "PASSWORD"):
            return (
                "Rotate the exposed secret immediately. Revoke active tokens "
                "and audit access logs for unauthorized use."
            )
        if entity_type in ("CARD", "IBAN", "ACCOUNT_NUMBER"):
            return (
                "Notify security and fraud response teams. Mask card numbers to last 4 digits "
                "in accordance with PCI-DSS."
            )
        return (
            "Sanitize communication channel and redact sensitive identifier before "
            "persistence or external transmission."
        )
    if severity == Severity.MEDIUM:
        return "Review privacy sharing policy. Ensure proper masking and consent before storage."
    return "Low-risk informational finding. Verify recipient authorization and standard redaction."


def render_scanner() -> None:
    """Render the Live Scanner interface."""
    st.title("Live Scanner")
    st.markdown(
        "Inspect text and communications in real time for PII, high-entropy secrets, "
        "and compliance exposures. All processing is strictly local."
    )

    # Initialize session state keys
    if "scanner_input" not in st.session_state:
        st.session_state["scanner_input"] = ""
    if "scanner_result" not in st.session_state:
        st.session_state["scanner_result"] = None
    if "scanner_selected_sample" not in st.session_state:
        st.session_state["scanner_selected_sample"] = "Custom Input (Type or Paste)"

    max_len = settings.max_input_length

    # Safe Sample Selector
    def on_sample_change() -> None:
        choice = st.session_state["sample_picker"]
        st.session_state["scanner_selected_sample"] = choice
        sample_text = SAMPLE_OPTIONS[choice]
        if sample_text:
            st.session_state["scanner_text_area"] = sample_text
            st.session_state["scanner_input"] = sample_text

    st.selectbox(
        "Load a Safe Demonstration Sample:",
        options=list(SAMPLE_OPTIONS.keys()),
        index=list(SAMPLE_OPTIONS.keys()).index(st.session_state["scanner_selected_sample"]),
        key="sample_picker",
        on_change=on_sample_change,
        help="Predefined synthetic examples to test regexes, secrets, and edge cases.",
    )

    # Text input area
    current_text = st.text_area(
        "Input Text to Analyze:",
        value=st.session_state.get("scanner_input", ""),
        height=180,
        key="scanner_text_area",
        placeholder="Paste communication, message payload, or log snippet here...",
        help=f"Safety limit: maximum {max_len:,} characters.",
    )
    st.session_state["scanner_input"] = current_text

    char_count = len(current_text)
    is_over_limit = char_count > max_len

    # Character count counter
    col_count, col_status = st.columns([2, 3])
    with col_count:
        if is_over_limit:
            st.markdown(
                f"<span style='color: #ef4444; font-weight: 700;'>"
                f"⚠️ Character Count: {char_count:,} / {max_len:,} (Exceeded limit)</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<span style='color: #94a3b8;'>"
                f"Character Count: <strong>{char_count:,}</strong> / {max_len:,}</span>",
                unsafe_allow_html=True,
            )

    with col_status:
        pipe = _get_pipeline()
        ner_status = (
            "spaCy Active"
            if (pipe.ner_adapter and pipe.ner_adapter.is_available())
            else "Detector-Only (NER disabled)"
        )
        st.markdown(
            f"<div style='text-align: right; color: #94a3b8; font-size: 0.85rem;'>"
            f"Engine: <strong>Rules + RegEx + Secrets</strong> | {ner_status}</div>",
            unsafe_allow_html=True,
        )

    def on_clear() -> None:
        st.session_state["scanner_input"] = ""
        st.session_state["scanner_text_area"] = ""
        st.session_state["scanner_result"] = None
        st.session_state["scanner_selected_sample"] = "Custom Input (Type or Paste)"

    # Action Buttons
    col_btn_analyze, col_btn_clear, _ = st.columns([2, 2, 6])
    with col_btn_analyze:
        analyze_clicked = st.button("🔍 Analyze Message", type="primary", use_container_width=True)
    with col_btn_clear:
        st.button("🧹 Clear", on_click=on_clear, use_container_width=True)

    if analyze_clicked:
        if not current_text.strip():
            st.info("Please enter or select text before running analysis.")
            st.session_state["scanner_result"] = None
        elif is_over_limit:
            st.error(
                f"Input text exceeds maximum allowed length of {max_len:,} characters "
                f"(received {char_count:,} characters). Please reduce the input size."
            )
            st.session_state["scanner_result"] = None
        else:
            with st.spinner("Analyzing text for PII and sensitive patterns..."):
                try:
                    pipeline = _get_pipeline()
                    result = pipeline.scan(current_text, redact=True, redaction_mode="placeholder")
                    session_log = _get_session_log()
                    receipt = pipeline.create_receipt(result)
                    session_log.record_receipt(receipt)
                    st.session_state["scanner_result"] = result
                except ValueError as exc:
                    st.error(str(exc))
                    st.session_state["scanner_result"] = None
                except Exception:
                    st.error(
                        "An error occurred during analysis. Raw input text has been safeguarded."
                    )
                    st.session_state["scanner_result"] = None

    # Results Presentation
    result: ScanResult | None = st.session_state.get("scanner_result")
    if result is not None:
        st.markdown("---")
        # Risk Header Banner
        risk_class = f"risk-badge-{result.risk_band.lower()}"
        banner_summary = (
            f"Findings: <strong>{len(result.findings)}</strong> | "
            f"Max Severity: <strong>{result.max_severity.value.upper()}</strong> | "
            f"Latency: <strong>{result.duration_ms:.1f}ms</strong>"
        )
        st.markdown(
            f"""
            <div class="leakguard-card leakguard-reveal">
                <div style="display: flex; justify-content: space-between; align-items: center;
                            flex-wrap: wrap; gap: 0.5rem;">
                    <div>
                        <span style="font-weight: 700;">Overall Risk Assessment:</span>
                        <span class="leakguard-badge {risk_class}" style="margin-left: 0.5rem;">
                            {result.risk_band} RISK (Score: {result.overall_rule_score:.2f})
                        </span>
                    </div>
                    <div style="font-size: 0.85rem; color: #94a3b8;">
                        {banner_summary}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        card_style = "white-space: pre-wrap; word-break: break-word; line-height: 1.6;"
        if not result.findings:
            st.success("✅ No sensitive data or credential patterns detected in this message.")
            st.markdown("**Inspected Text (Strictly Escaped):**")
            annotated_html = render_annotated(current_text, [])
            st.markdown(
                f'<div class="leakguard-card" style="{card_style}">{annotated_html}</div>',
                unsafe_allow_html=True,
            )
        else:
            # Filters persisted in session_state
            st.markdown("### Findings & Inspection")

            # Extract available severities and types
            available_severities = sorted(list({f.severity.value for f in result.findings}))
            available_types = sorted(list({f.entity_type for f in result.findings}))

            filter_col1, filter_col2, filter_col3 = st.columns([3, 3, 2])
            with filter_col1:
                selected_severities = st.multiselect(
                    "Filter by Severity:",
                    options=available_severities,
                    default=st.session_state.get("scanner_sev_filter", available_severities),
                    key="scanner_sev_multiselect",
                )
                st.session_state["scanner_sev_filter"] = selected_severities

            with filter_col2:
                selected_types = st.multiselect(
                    "Filter by Entity Type:",
                    options=available_types,
                    default=st.session_state.get("scanner_type_filter", available_types),
                    key="scanner_type_multiselect",
                )
                st.session_state["scanner_type_filter"] = selected_types

            with filter_col3:
                show_redacted_toggle = st.checkbox(
                    "Preview Redacted Output",
                    value=st.session_state.get("scanner_show_redacted", False),
                    key="scanner_show_redacted_box",
                )
                st.session_state["scanner_show_redacted"] = show_redacted_toggle

            # Filter findings
            filtered_findings = [
                f
                for f in result.findings
                if f.severity.value in selected_severities and f.entity_type in selected_types
            ]

            # Layout: Annotated View / Redacted View & Evidence Rail
            col_main, col_rail = st.columns([5, 3])

            with col_main:
                if show_redacted_toggle and result.redacted_text is not None:
                    st.markdown("**Redacted Text Preview (Sanitized):**")
                    st.code(result.redacted_text, language="text")
                else:
                    st.markdown("**Annotated Text (Strictly Escaped):**")
                    annotated_html = render_annotated(current_text, filtered_findings)
                    st.markdown(
                        f'<div class="leakguard-card" style="{card_style}">{annotated_html}</div>',
                        unsafe_allow_html=True,
                    )

                # Findings Table
                st.markdown(f"**Detected Findings ({len(filtered_findings)} displayed):**")
                if not filtered_findings:
                    st.info("No findings match the current filter selection.")
                else:
                    table_rows = []
                    for f in filtered_findings:
                        safe_val = format_safe_display_value(f.entity_type, f.length, max_reveal=0)
                        sev_icon = SEVERITY_ICONS.get(f.severity, "ℹ️")
                        rule_score_str = (
                            f"{f.rule_score:.2f}" if f.rule_score is not None else "no score"
                        )
                        table_rows.append(
                            {
                                "ID": f.id,
                                "Entity": safe_val,
                                "Type": f.entity_type,
                                "Severity": f"{sev_icon} {f.severity.value}",
                                "Detector": f.detector,
                                "Range": f"[{f.start}:{f.end}]",
                                "Rule Score": rule_score_str,
                                "Rationale": f.rationale,
                            }
                        )
                    st.dataframe(table_rows, use_container_width=True, hide_index=True)

            with col_rail:
                st.markdown("**Evidence Rail:**")
                if filtered_findings:
                    finding_ids = [f.id for f in filtered_findings]
                    selected_id = st.selectbox(
                        "Inspect Specific Finding:",
                        options=finding_ids,
                        format_func=lambda fid: next(
                            f"{f.entity_type} ({f.severity.value}) - ID {fid}"
                            for f in filtered_findings
                            if f.id == fid
                        ),
                        key="scanner_evidence_select",
                    )
                    selected_finding = next(
                        (f for f in filtered_findings if f.id == selected_id), None
                    )
                    if selected_finding:
                        safe_display = format_safe_display_value(
                            selected_finding.entity_type, selected_finding.length, max_reveal=0
                        )
                        remediation = _remediation_advice(
                            selected_finding.entity_type, selected_finding.severity
                        )
                        sev_icon = SEVERITY_ICONS.get(selected_finding.severity, "")
                        offset_str = (
                            f"start {selected_finding.start}, end {selected_finding.end} "
                            f"(length: {selected_finding.length})"
                        )
                        st.markdown(
                            f"""
                            <div class="leakguard-card" style="font-size: 0.9rem;">
                                <div style="font-weight: 700; margin-bottom: 0.5rem;
                                            color: #00b4d8;">
                                    Finding Details: {selected_finding.id}
                                </div>
                                <div style="margin-bottom: 0.35rem;">
                                    <strong>Entity Type:</strong> {selected_finding.entity_type}
                                </div>
                                <div style="margin-bottom: 0.35rem;">
                                    <strong>Severity:</strong> {sev_icon}
                                    {selected_finding.severity.value}
                                </div>
                                <div style="margin-bottom: 0.35rem;">
                                    <strong>Display Value:</strong> <code>{safe_display}</code>
                                </div>
                                <div style="margin-bottom: 0.35rem;">
                                    <strong>Offsets:</strong> {offset_str}
                                </div>
                                <div style="margin-bottom: 0.35rem;">
                                    <strong>Source Detector:</strong> {selected_finding.detector}
                                </div>
                                <div style="margin-bottom: 0.5rem;">
                                    <strong>Rationale:</strong> {selected_finding.rationale}
                                </div>
                                <div style="background-color: #1e293b;
                                            border-left: 3px solid #00b4d8;
                                            padding: 0.5rem; border-radius: 4px;
                                            font-size: 0.82rem;">
                                    <strong>Remediation:</strong> {remediation}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                else:
                    st.caption("No finding selected.")

            # Sanitized Export Options
            st.markdown("---")
            st.markdown("**Sanitized Data Export:**")
            st.caption(
                "Exported records contain sanitized display values and metadata only. "
                "Raw user input text and credentials are never included."
            )
            col_exp_csv, col_exp_json, _ = st.columns([3, 3, 4])
            with col_exp_csv:
                csv_data = export_findings_csv(result.findings)
                st.download_button(
                    label="📥 Export Findings (CSV)",
                    data=csv_data,
                    file_name="leakguard_findings.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with col_exp_json:
                json_data = export_findings_json(result.findings)
                st.download_button(
                    label="📥 Export Findings (JSON)",
                    data=json_data,
                    file_name="leakguard_findings.json",
                    mime="application/json",
                    use_container_width=True,
                )


if __name__ == "__main__" or "streamlit" in __name__:
    render_scanner()
