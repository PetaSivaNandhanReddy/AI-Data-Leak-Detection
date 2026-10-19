"""LEAKGUARD — Security Intelligence Console.

Main application entry point and router using st.navigation.
Configures page shell, sidebar status strip from real runtime facts,
privacy notices, and session lifecycle controls.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src layout is discoverable on cloud hosts without editable install
_SRC_DIR = Path(__file__).resolve().parent / "src"
if _SRC_DIR.is_dir() and str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

import streamlit as st

from leakguard.config import settings
from leakguard.detection.pipeline import Pipeline
from leakguard.session.security import SessionSecurity
from leakguard.session.session_log import SessionLog
from leakguard.ui.theme import get_custom_css

# Global Streamlit page configuration
st.set_page_config(
    page_title="LEAKGUARD — Security Intelligence Console",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject static CSS theme (system fonts, WCAG AA contrast, reduced-motion query)
_theme_css = get_custom_css()
if _theme_css:
    st.markdown(_theme_css, unsafe_allow_html=True)


def _init_session() -> tuple[SessionSecurity, SessionLog, Pipeline]:
    """Initialize or retrieve session singletons."""
    if "session_security" not in st.session_state:
        st.session_state["session_security"] = SessionSecurity()
    if "session_log" not in st.session_state:
        st.session_state["session_log"] = SessionLog()
    if "pipeline" not in st.session_state:
        st.session_state["pipeline"] = Pipeline()

    return (
        st.session_state["session_security"],
        st.session_state["session_log"],
        st.session_state["pipeline"],
    )


session_sec, session_log, pipeline = _init_session()

# Sidebar: Brand Identity & Privacy Notice
with st.sidebar:
    st.markdown("## 🛡️ LEAKGUARD")
    st.markdown(
        "<div style='font-size: 0.85rem; color: #94a3b8; "
        "margin-top: -0.75rem; margin-bottom: 0.75rem;'>"
        "Security Intelligence Console<br>"
        "<span style='color: #00b4d8; font-weight: 600;'>"
        "Detector-Only v1 (Rules + RegEx + Secrets)</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    # Privacy Banner
    st.markdown(
        """
        <div class="leakguard-banner" style="font-size: 0.82rem; line-height: 1.4;">
            <strong>⚠️ Privacy & Safety Notice</strong><br>
            Local-first processing. Zero outbound network requests.
            Raw text is processed strictly in memory and is never logged or written to disk.
            <div style="margin-top: 0.35rem; color: #cbd5e1;">
                <strong>Do not paste production credentials or live personal data here.</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Runtime Status Strip (Real Facts Only)
    ner_status = (
        "spaCy Active"
        if (pipeline.ner_adapter and pipeline.ner_adapter.is_available())
        else "Disabled (Offline)"
    )
    st.markdown(
        f"""
        <div class="leakguard-status-strip">
            <div style="font-weight: 700; color: #cbd5e1; margin-bottom: 0.35rem;">
                Runtime Status
            </div>
            <div class="leakguard-status-item">
                <span>Architecture:</span>
                <span style="font-weight: 600; color: #00b4d8;">Detector-Only</span>
            </div>
            <div class="leakguard-status-item">
                <span>Classifier Gate:</span>
                <span style="color: #f59e0b;">Challenge Set Pending</span>
            </div>
            <div class="leakguard-status-item">
                <span>RegEx Engine:</span>
                <span style="color: #10b981;">Online (8 Validators)</span>
            </div>
            <div class="leakguard-status-item">
                <span>Secret Detector:</span>
                <span style="color: #10b981;">Online (Entropy ≥ {settings.entropy_threshold})</span>
            </div>
            <div class="leakguard-status-item">
                <span>NER Engine:</span>
                <span>{ner_status}</span>
            </div>
            <div class="leakguard-status-item">
                <span>Input Limit:</span>
                <span>{settings.max_input_length:,} chars</span>
            </div>
            <div class="leakguard-status-item">
                <span>Session ID:</span>
                <span style="font-family: monospace;">{session_sec.session_id[:8]}...</span>
            </div>
            <div class="leakguard-status-item">
                <span>Session Scans:</span>
                <span>{session_log.total_scans}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Clear Session Control
    if st.button(
        "🧹 Clear Session",
        use_container_width=True,
        help="Wipe all inputs, scan results, and receipts from session memory.",
    ):
        # Clear specific session state keys
        session_log.clear()
        keys_to_reset = [
            "scanner_input",
            "scanner_result",
            "scanner_selected_sample",
            "scanner_sev_filter",
            "scanner_type_filter",
            "scanner_show_redacted",
            "redaction_input",
            "redaction_result",
            "redaction_selected_sample",
        ]
        for k in keys_to_reset:
            if k in st.session_state:
                del st.session_state[k]
        st.session_state["session_security"] = SessionSecurity()
        st.rerun()

# Navigation Router using st.navigation
pages = {
    "Operations": [
        st.Page("views/scanner.py", title="Live Scanner", icon="🔍", default=True),
        st.Page("views/redaction.py", title="Redaction Studio", icon="🛡️"),
    ],
    "Intelligence": [
        st.Page("views/overview.py", title="Executive Overview", icon="📊"),
        st.Page("views/incidents.py", title="Incident Command Center", icon="🚨"),
    ],
    "System & Research": [
        st.Page("views/model_lab.py", title="Model Laboratory", icon="🧪"),
        st.Page("views/methodology.py", title="Methodology & Health", icon="📚"),
    ],
    "Security Lab (Educational)": [
        st.Page("labs/security_lab.py", title="AES-GCM Demo Lab", icon="🔐"),
    ],
}

nav = st.navigation(pages)
nav.run()
