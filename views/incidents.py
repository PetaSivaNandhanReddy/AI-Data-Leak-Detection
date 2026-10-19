"""Incident Command Center view for LEAKGUARD.

Provides:
- Searchable, sortable, paginated audit trail of scan receipts
- Persistent session filters (severity, risk band, incident ID)
- Detailed incident inspection (findings counts, duration, remediation)
- Interactive timeline chart with adjacent data table
- Toggle to browse held-out reference corpus benchmark incidents
- Formula-safe sanitized CSV and JSON export with privacy notices
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from leakguard.export.safe_export import neutralize_csv_formula
from leakguard.schemas import ScanReceipt
from leakguard.session.session_log import SessionLog

REFERENCE_CORPUS_PATH = Path("reports/reference_corpus.json")


def _get_session_log() -> SessionLog:
    if "session_log" not in st.session_state:
        st.session_state["session_log"] = SessionLog()
    return st.session_state["session_log"]


def _load_reference_incidents() -> list[dict[str, Any]]:
    if not REFERENCE_CORPUS_PATH.is_file():
        return []
    try:
        with open(REFERENCE_CORPUS_PATH, encoding="utf-8") as f:
            data = json.load(f)
            return data.get("sample_scans", [])
    except Exception:
        return []


def _receipts_to_csv(receipts: list[dict[str, Any]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    headers = [
        "incident_id",
        "source",
        "timestamp",
        "risk_band",
        "overall_rule_score",
        "total_findings",
        "text_length",
        "duration_ms",
    ]
    writer.writerow(headers)
    for r in receipts:
        writer.writerow(
            [
                neutralize_csv_formula(r.get("id")),
                neutralize_csv_formula(r.get("source")),
                neutralize_csv_formula(r.get("timestamp")),
                neutralize_csv_formula(r.get("risk_band")),
                r.get("overall_rule_score"),
                r.get("findings_count"),
                r.get("text_length"),
                r.get("duration_ms"),
            ]
        )
    return output.getvalue()


def _remediation_advice(risk_band: str, max_severity: str) -> str:
    if "high" in risk_band.lower() or max_severity in ("HIGH", "CRITICAL"):
        return (
            "Immediate Remediation: Quarantine communication, revoke exposed secrets, "
            "and alert data protection response teams. Audit persistence layers for leaks."
        )
    if "possible" in risk_band.lower() or max_severity == "MEDIUM":
        return (
            "Standard Triage: Apply redaction policies before archival or external transmission. "
            "Verify recipient consent."
        )
    return "Informational: Standard monitoring applies. Verify authorized data sharing."


def render_incidents() -> None:
    """Render the Incident Command Center interface."""
    st.title("Incident Command Center")
    st.markdown(
        "Audit trail, chronological timeline, and metadata inspection for all messages analyzed "
        "in this session. Ephemeral memory ensures raw text is never preserved."
    )

    session_log = _get_session_log()
    session_receipts: list[ScanReceipt] = session_log.get_receipts()

    # Reference corpus browse toggle
    browse_ref = st.checkbox(
        "Browse Reference Corpus Incidents (Held-Out Benchmark Data)",
        value=st.session_state.get("incidents_browse_ref", False),
        key="incidents_browse_ref_checkbox",
        help="Inspect precomputed reference scans from the held-out test split.",
    )
    st.session_state["incidents_browse_ref"] = browse_ref

    # Normalize incident records into unified dictionaries
    unified_records: list[dict[str, Any]] = []

    # 1. Add session records
    for r in session_receipts:
        tot_findings = sum(r.finding_counts_by_type.values())
        unified_records.append(
            {
                "id": r.id,
                "source": "Session Scan",
                "timestamp": r.timestamp,
                "risk_band": r.risk_band,
                "max_severity": r.max_severity.value,
                "overall_rule_score": r.overall_rule_score,
                "findings_count": tot_findings,
                "text_length": r.text_length,
                "duration_ms": r.duration_ms,
                "detectors": list(r.detectors_run),
                "type_breakdown": dict(r.finding_counts_by_type),
                "severity_breakdown": dict(r.finding_counts_by_severity),
            }
        )

    # 2. Add reference records if toggled
    if browse_ref:
        ref_samples = _load_reference_incidents()
        for idx, s in enumerate(ref_samples):
            unified_records.append(
                {
                    "id": s.get("id", f"ref_{idx}"),
                    "source": "Reference Benchmark",
                    "timestamp": "2026-10-18T19:07:05Z",
                    "risk_band": s.get("predicted_risk_band", "unknown"),
                    "max_severity": (
                        "HIGH" if "high" in s.get("predicted_risk_band", "") else "MEDIUM"
                    ),
                    "overall_rule_score": s.get("overall_rule_score", 0.0),
                    "findings_count": s.get("findings_count", 0),
                    "text_length": s.get("text_length", 0),
                    "duration_ms": 1.2,
                    "detectors": ["regex", "secret", "spacy_ner"],
                    "type_breakdown": {"BENCHMARK": s.get("findings_count", 0)},
                    "severity_breakdown": {"REFERENCE": s.get("findings_count", 0)},
                }
            )

    # Empty State check
    if not unified_records:
        st.info(
            "📋 **No incidents logged yet.**\n\n"
            "No messages have been analyzed in this interactive session. You can:\n"
            "- Go to the **Live Scanner** to scan a message.\n"
            "- Check the **'Browse Reference Corpus Incidents'** toggle to explore baseline data."
        )
        return

    # -------------------------------------------------------------------------
    # Filters & Search Bar (persisted in session_state)
    # -------------------------------------------------------------------------
    st.markdown("### 🔍 Filter and Search Audit Records")

    f_col1, f_col2, f_col3, f_col4 = st.columns([3, 2, 2, 2])

    with f_col1:
        search_query = st.text_input(
            "Search Incident ID:",
            value=st.session_state.get("incidents_search_query", ""),
            key="incidents_search_input",
            placeholder="e.g. rcpt_ or lg_fam_",
        )
        st.session_state["incidents_search_query"] = search_query

    # Available risk bands and sources
    available_risks = sorted(list({r["risk_band"] for r in unified_records}))
    available_sources = sorted(list({r["source"] for r in unified_records}))

    with f_col2:
        selected_risks = st.multiselect(
            "Risk Band:",
            options=available_risks,
            default=st.session_state.get("incidents_risk_filter", available_risks),
            key="incidents_risk_multiselect",
        )
        st.session_state["incidents_risk_filter"] = selected_risks

    with f_col3:
        selected_sources = st.multiselect(
            "Data Source:",
            options=available_sources,
            default=st.session_state.get("incidents_source_filter", available_sources),
            key="incidents_source_multiselect",
        )
        st.session_state["incidents_source_filter"] = selected_sources

    with f_col4:
        sort_by = st.selectbox(
            "Sort Order:",
            options=["Newest First", "Highest Risk Score", "Most Findings", "Oldest First"],
            index=0,
            key="incidents_sort_select",
        )

    # Apply Filters
    filtered = [
        r
        for r in unified_records
        if (not search_query or search_query.lower() in r["id"].lower())
        and (r["risk_band"] in selected_risks)
        and (r["source"] in selected_sources)
    ]

    # Apply Sorting
    if sort_by == "Newest First":
        filtered.sort(key=lambda r: r["timestamp"], reverse=True)
    elif sort_by == "Oldest First":
        filtered.sort(key=lambda r: r["timestamp"])
    elif sort_by == "Highest Risk Score":
        filtered.sort(key=lambda r: r["overall_rule_score"], reverse=True)
    elif sort_by == "Most Findings":
        filtered.sort(key=lambda r: r["findings_count"], reverse=True)

    # -------------------------------------------------------------------------
    # Timeline Analytics & Trend
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### ⏱️ Incident Activity Timeline")

    df_timeline = pd.DataFrame(
        [
            {
                "Incident ID": r["id"],
                "Source": r["source"],
                "Timestamp": r["timestamp"][:19].replace("T", " "),
                "Rule Score": r["overall_rule_score"],
                "Findings": r["findings_count"],
            }
            for r in filtered
        ]
    )

    t_col1, t_col2 = st.columns([6, 4])
    with t_col1:
        if not df_timeline.empty:
            chart_data = df_timeline[["Timestamp", "Rule Score"]].set_index("Timestamp")
            st.line_chart(chart_data, use_container_width=True)
        else:
            st.caption("No timeline data matching current filters.")

    with t_col2:
        with st.expander("View Activity Timeline Table", expanded=True):
            st.dataframe(df_timeline, use_container_width=True, hide_index=True)

    # -------------------------------------------------------------------------
    # Incident List with Pagination & Detail Expanders
    # -------------------------------------------------------------------------
    st.markdown("---")
    p_col1, p_col2 = st.columns([8, 2])
    with p_col1:
        st.markdown(f"### 📑 Incident Audit Records ({len(filtered)} matching)")
    with p_col2:
        page_size = st.selectbox(
            "Page Size:", options=[5, 10, 25], index=0, key="incidents_page_size"
        )

    if not filtered:
        st.info("No incident records match the active filter criteria.")
    else:
        # Calculate pagination
        total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
        page_num = st.number_input(
            "Page:",
            min_value=1,
            max_value=total_pages,
            value=1,
            step=1,
            key="incidents_page_num",
        )
        start_idx = (page_num - 1) * page_size
        end_idx = min(start_idx + page_size, len(filtered))
        page_records = filtered[start_idx:end_idx]

        for inc in page_records:
            source_badge = "📍 Session" if inc["source"] == "Session Scan" else "🌐 Reference"
            risk_label = inc["risk_band"].upper()
            exp_title = (
                f"{source_badge} | {inc['id']} — {risk_label} "
                f"(Score: {inc['overall_rule_score']:.1f}, Findings: {inc['findings_count']})"
            )
            with st.expander(exp_title):
                d_col1, d_col2 = st.columns(2)
                with d_col1:
                    st.markdown(f"**Incident ID:** `{inc['id']}`")
                    st.markdown(f"**Timestamp:** `{inc['timestamp']}`")
                    st.markdown(f"**Risk Band:** `{inc['risk_band']}`")
                    st.markdown(f"**Rule Score:** `{inc['overall_rule_score']:.2f}`")
                    st.markdown(f"**Max Severity:** `{inc['max_severity']}`")

                with d_col2:
                    st.markdown(f"**Processed Characters:** `{inc['text_length']}`")
                    st.markdown(f"**Analysis Latency:** `{inc['duration_ms']:.1f}ms`")
                    st.markdown(f"**Detectors Run:** `{', '.join(inc['detectors'])}`")
                    st.markdown(f"**Entity Breakdown:** `{inc['type_breakdown']}`")

                # Remediation Guidance
                remediation = _remediation_advice(inc["risk_band"], inc["max_severity"])
                st.markdown(
                    f"""
                    <div style="background-color: #1e293b; border-left: 3px solid #00b4d8;
                                padding: 0.5rem 0.75rem; border-radius: 4px; margin-top: 0.5rem;
                                font-size: 0.85rem;">
                        <strong>Remediation Guidance:</strong> {remediation}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # -------------------------------------------------------------------------
    # Sanitized Export Options
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 📥 Sanitized Incident Export")
    st.caption(
        "🔒 **Privacy Guarantee:** Audit records contain sanitized operational metadata, "
        "timestamps, and aggregate finding counts only. "
        "Raw messages and secrets are NEVER exported."
    )

    csv_data = _receipts_to_csv(filtered)
    json_data = json.dumps(filtered, indent=2)

    exp_col1, exp_col2, _ = st.columns([3, 3, 4])
    with exp_col1:
        st.download_button(
            label="📥 Export Filtered Audit (CSV)",
            data=csv_data,
            file_name="leakguard_incident_audit.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with exp_col2:
        st.download_button(
            label="📥 Export Filtered Audit (JSON)",
            data=json_data,
            file_name="leakguard_incident_audit.json",
            mime="application/json",
            use_container_width=True,
        )


if __name__ == "__main__" or "streamlit" in __name__:
    render_incidents()
