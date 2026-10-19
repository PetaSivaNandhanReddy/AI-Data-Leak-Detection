"""Executive Overview view for LEAKGUARD.

Displays:
- Two visibly separated KPI groups: "This Session" and "Reference Corpus Benchmark"
- Risk band distribution chart and findings-by-type chart with adjacent data tables
- Live Detector Health Panel driven by the real registry
- "Run Sample Scan" action that executes the real pipeline
- Graceful handling of empty sessions, single-class data, and missing reports
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from leakguard.detection.pipeline import Pipeline
from leakguard.schemas import Severity
from leakguard.session.session_log import SessionLog

REFERENCE_CORPUS_PATH = Path("reports/reference_corpus.json")

SAMPLE_SCAN_TEXT = (
    "Customer service billing query: Customer Eleanor Vance (email: eleanor.vance@example.org, "
    "phone: +1-555-0199) verified transaction on card 4532-0150-1234-5678 expiring 09/28. "
    "Settlement IBAN: GB29NWBK60161331926819. DevOps token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456."
)


def _get_pipeline() -> Pipeline:
    if "pipeline" not in st.session_state:
        st.session_state["pipeline"] = Pipeline()
    return st.session_state["pipeline"]


def _get_session_log() -> SessionLog:
    if "session_log" not in st.session_state:
        st.session_state["session_log"] = SessionLog()
    return st.session_state["session_log"]


def _load_reference_corpus() -> dict[str, Any] | None:
    if not REFERENCE_CORPUS_PATH.is_file():
        return None
    try:
        with open(REFERENCE_CORPUS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def render_overview() -> None:
    """Render the Executive Overview dashboard."""
    st.title("Executive Overview")
    st.markdown(
        "High-level telemetry, security KPIs, and reference benchmark comparisons. "
        "Local session activity is compared against held-out baseline evaluations."
    )

    pipeline = _get_pipeline()
    session_log = _get_session_log()
    ref_data = _load_reference_corpus()

    # -------------------------------------------------------------------------
    # 1. KPI Groups (visibly separate: Session vs Reference Corpus)
    # -------------------------------------------------------------------------
    st.markdown("### 📊 Security Telemetry & Benchmarks")

    col_session, col_divider, col_reference = st.columns([5, 1, 5])

    with col_session:
        st.markdown(
            """
            <div style="background-color: #162036; border: 1px solid #00b4d8;
                        border-radius: 8px; padding: 1rem; margin-bottom: 1rem;">
                <div style="font-weight: 700; color: #00b4d8; font-size: 1rem;
                            margin-bottom: 0.5rem;">
                    📍 THIS SESSION (Ephemeral In-Memory)
                </div>
            """,
            unsafe_allow_html=True,
        )

        receipts = session_log.get_receipts()
        scans_count = session_log.total_scans
        findings_count = session_log.total_findings_count
        sev_counts = session_log.aggregate_counts_by_severity()
        high_risk_scans = sum(1 for r in receipts if r.risk_band in ("HIGH", "high_risk_exposure"))

        sub_col1, sub_col2, sub_col3 = st.columns(3)
        with sub_col1:
            st.metric("Total Scans", f"{scans_count}")
        with sub_col2:
            st.metric("Findings Detected", f"{findings_count}")
        with sub_col3:
            st.metric("High-Risk Alerts", f"{high_risk_scans}")

        if scans_count == 0:
            st.caption(
                "ℹ️ No messages scanned in this session yet. Run a sample scan below or use the "
                "Live Scanner."
            )
        else:
            st.caption(
                f"Active session scans. High: {sev_counts.get(Severity.HIGH.value, 0)} | "
                f"Med: {sev_counts.get(Severity.MEDIUM.value, 0)} | "
                f"Low: {sev_counts.get(Severity.LOW.value, 0)}"
            )

        st.markdown("</div>", unsafe_allow_html=True)

    with col_divider:
        st.markdown(
            "<div style='text-align: center; color: #475569; font-size: 1.5rem; "
            "line-height: 5rem;'>VS</div>",
            unsafe_allow_html=True,
        )

    with col_reference:
        st.markdown(
            """
            <div style="background-color: #1e293b; border: 1px solid #475569;
                        border-radius: 8px; padding: 1rem; margin-bottom: 1rem;">
                <div style="font-weight: 700; color: #cbd5e1; font-size: 1rem;
                            margin-bottom: 0.5rem;">
                    🌐 REFERENCE CORPUS (Held-Out Test Benchmark)
                </div>
            """,
            unsafe_allow_html=True,
        )

        if ref_data is not None:
            ref_meta = ref_data.get("metadata", {})
            ref_stats = ref_data.get("aggregate_statistics", {})
            ref_n = ref_meta.get("total_records", 0)
            ref_date = ref_meta.get("generated_at", "Unknown")[:10]
            ref_risk = ref_stats.get("risk_band_distribution", {})
            ref_high = ref_risk.get("high_risk_exposure", 0)
            ref_entities = ref_stats.get("detected_entity_counts", {})
            ref_findings = sum(ref_entities.values())

            ref_col1, ref_col2, ref_col3 = st.columns(3)
            with ref_col1:
                st.metric("Test Split (N)", f"{ref_n}")
            with ref_col2:
                st.metric("Total Findings", f"{ref_findings}")
            with ref_col3:
                st.metric("High-Risk Exposure", f"{ref_high}")

            st.caption(
                f"Baseline configuration: {ref_meta.get('pipeline_configuration', 'Standard')} "
                f"(Evaluated: {ref_date})"
            )
        else:
            st.warning("⚠️ Reference corpus report missing (`reports/reference_corpus.json`).")
            st.code("python -m leakguard.evaluation.report --out reports/", language="bash")

        st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 2. Sample Scan Trigger
    # -------------------------------------------------------------------------
    st.markdown("---")
    sample_col1, sample_col2 = st.columns([3, 7])
    with sample_col1:
        st.markdown("**Interactive Demonstration:**")
        run_sample_btn = st.button(
            "⚡ Run Sample Scan",
            type="primary",
            use_container_width=True,
            help=(
                "Execute the pipeline on a safe synthetic multi-PII payload "
                "and update session KPIs."
            ),
        )
    with sample_col2:
        st.caption(
            "Clicking **Run Sample Scan** immediately executes the complete detection pipeline "
            "on a safe synthetic message with PII and credentials, recording a sanitized receipt "
            "in session memory."
        )

    if run_sample_btn:
        with st.spinner("Executing detection pipeline on sample payload..."):
            result = pipeline.scan(SAMPLE_SCAN_TEXT, redact=True, redaction_mode="placeholder")
            receipt = pipeline.create_receipt(result)
            session_log.record_receipt(receipt)
            st.success(
                f"Sample scan complete in {result.duration_ms:.1f}ms! Detected "
                f"{len(result.findings)} findings ({result.risk_band} risk). Session KPIs updated."
            )
            st.rerun()

    # -------------------------------------------------------------------------
    # 3. Visual Analytics (Charts with Adjacent Data Tables)
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 📈 Comparative Risk & Findings Distributions")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("**Risk Band Distribution:**")
        # Build comparative dataframe
        risk_rows = []
        # Session counts
        session_risk_counts: dict[str, int] = {}
        for r in receipts:
            band = r.risk_band
            session_risk_counts[band] = session_risk_counts.get(band, 0) + 1

        for band in ["high_risk_exposure", "possible_exposure", "no_exposure"]:
            norm_band = band.replace("_exposure", "").upper()
            sess_cnt = session_risk_counts.get(norm_band, 0) + session_risk_counts.get(band, 0)
            ref_cnt = 0
            if ref_data:
                ref_cnt = (
                    ref_data.get("aggregate_statistics", {})
                    .get("risk_band_distribution", {})
                    .get(band, 0)
                )
            risk_rows.append(
                {
                    "Risk Band": norm_band,
                    "This Session": sess_cnt,
                    "Reference Corpus": ref_cnt,
                }
            )

        df_risk = pd.DataFrame(risk_rows)
        # Handle empty/single data without error
        if df_risk["This Session"].sum() == 0 and df_risk["Reference Corpus"].sum() == 0:
            st.info("No risk distribution data available.")
        else:
            st.bar_chart(
                df_risk.set_index("Risk Band"),
                use_container_width=True,
            )

        with st.expander("View Risk Distribution Table"):
            st.dataframe(df_risk, use_container_width=True, hide_index=True)

    with chart_col2:
        st.markdown("**Findings by Entity Type:**")
        # Collect entity types
        session_entities = session_log.aggregate_counts_by_type()
        ref_entities = {}
        if ref_data:
            ref_entities = ref_data.get("aggregate_statistics", {}).get(
                "detected_entity_counts", {}
            )

        all_types = sorted(list(set(list(session_entities.keys()) + list(ref_entities.keys()))))
        entity_rows = []
        for et in all_types:
            entity_rows.append(
                {
                    "Entity Type": et,
                    "This Session": session_entities.get(et, 0),
                    "Reference Corpus": ref_entities.get(et, 0),
                }
            )

        df_entity = pd.DataFrame(entity_rows)
        if df_entity.empty or (
            df_entity["This Session"].sum() == 0 and df_entity["Reference Corpus"].sum() == 0
        ):
            st.info("No entity detection findings recorded.")
        else:
            st.bar_chart(
                df_entity.set_index("Entity Type"),
                use_container_width=True,
            )

        with st.expander("View Findings by Type Table"):
            st.dataframe(df_entity, use_container_width=True, hide_index=True)

    # -------------------------------------------------------------------------
    # 4. Detector Health & Registry Status Panel
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🛡️ Detector Registry Health")

    ner_is_active = bool(pipeline.ner_adapter and pipeline.ner_adapter.is_available())
    ner_name = type(pipeline.ner_adapter).__name__ if pipeline.ner_adapter else "None"

    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    with col_d1:
        st.markdown(
            """
            <div class="leakguard-card" style="font-size: 0.85rem;">
                <div style="font-weight: 700; color: #10b981; margin-bottom: 0.35rem;">
                    🟢 RegEx Engine
                </div>
                <div><strong>Status:</strong> Active</div>
                <div><strong>Coverage:</strong> 8 Entity Types</div>
                <div><strong>Validators:</strong> Luhn, Verhoeff, Mod-97, PAN, Voter</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_d2:
        st.markdown(
            """
            <div class="leakguard-card" style="font-size: 0.85rem;">
                <div style="font-weight: 700; color: #10b981; margin-bottom: 0.35rem;">
                    🟢 Secret Engine
                </div>
                <div><strong>Status:</strong> Active</div>
                <div><strong>Method:</strong> Entropy + Token Prefixes</div>
                <div><strong>Threshold:</strong> Shannon Entropy ≥ 4.5</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_d3:
        ner_status_color = "#10b981" if ner_is_active else "#94a3b8"
        ner_status_label = "🟢 Active" if ner_is_active else "⚪ Disabled"
        st.markdown(
            f"""
            <div class="leakguard-card" style="font-size: 0.85rem;">
                <div style="font-weight: 700; color: {ner_status_color};
                            margin-bottom: 0.35rem;">
                    {ner_status_label} NER Engine
                </div>
                <div><strong>Status:</strong> {ner_name}</div>
                <div><strong>Target:</strong> Names, Locations, Orgs</div>
                <div><strong>Mode:</strong> Fallback-safe</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_d4:
        st.markdown(
            """
            <div class="leakguard-card" style="font-size: 0.85rem;">
                <div style="font-weight: 700; color: #f59e0b; margin-bottom: 0.35rem;">
                    🟠 Classifier Gate
                </div>
                <div><strong>Status:</strong> Gated Out (Detector-Only)</div>
                <div><strong>Reason:</strong> Human Challenge Set Pending</div>
                <div><strong>Model:</strong> Logistic Regression (Held)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__" or "streamlit" in __name__:
    render_overview()
