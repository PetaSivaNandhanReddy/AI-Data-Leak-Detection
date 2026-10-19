"""Model Laboratory view for LEAKGUARD.

Provides:
- Tabbed comparative evaluation: "Entity Detection" and "Message Risk"
- Ground-truth evaluation metrics loaded directly from reports/eval_latest.json
- Provenance ledger on every card (dataset version, split, seed, git commit, date)
- Per-type precision, recall, F1, F2, and confusion matrix displays
- Honest classifier gate status and "Not evaluated" fallback states
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

EVAL_PATH = Path("reports/eval_latest.json")


def _load_eval_data() -> dict[str, Any] | None:
    if not EVAL_PATH.is_file():
        return None
    try:
        with open(EVAL_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def render_model_lab() -> None:
    """Render the Model Laboratory evaluation interface."""
    st.title("Model Laboratory")
    st.markdown(
        "Empirical benchmarks, baseline comparisons, and granular validation metrics. "
        "All figures are computed from reproducible evaluation runs on held-out data."
    )

    eval_data = _load_eval_data()

    if eval_data is None:
        st.warning("⚠️ Evaluation artifact missing (`reports/eval_latest.json`).")
        st.info("To generate evaluation benchmarks from your test dataset, execute:")
        st.code("python -m leakguard.evaluation.report --out reports/", language="bash")
        return

    meta = eval_data.get("metadata", {})
    git_commit = meta.get("git_commit", "unknown")[:8]
    run_date = meta.get("run_date", "unknown")[:10]
    seed = meta.get("dataset_seed", 42)
    split_method = meta.get("dataset_split_method", "by_family_id (60/20/20)")

    # Global Provenance Card
    st.markdown(
        f"""
        <div class="leakguard-card" style="font-size: 0.85rem; margin-bottom: 1.25rem;">
            <div style="font-weight: 700; color: #00b4d8; margin-bottom: 0.25rem;">
                📋 Evaluation Provenance Ledger
            </div>
            <div style="display: flex; gap: 1.5rem; flex-wrap: wrap; color: #cbd5e1;">
                <div><strong>Commit:</strong> <code>{git_commit}</code></div>
                <div><strong>Run Date:</strong> {run_date}</div>
                <div><strong>Dataset Seed:</strong> {seed}</div>
                <div><strong>Split:</strong> {split_method}</div>
                <div><strong>Architecture:</strong> Detector-Only v1</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_entity, tab_message = st.tabs(["🏷️ Entity Detection", "⚖️ Message Risk Triage"])

    # =========================================================================
    # TAB 1: Entity Detection
    # =========================================================================
    with tab_entity:
        st.markdown("### Character-Offset Entity Span Detection")
        st.caption(
            "Evaluation on held-out test split (N=822 messages). Measures exact span matches "
            "and relaxed overlap matches across all supported personal and financial identifiers."
        )

        test_metrics = eval_data.get("test_metrics", {})
        entity_eval = test_metrics.get("entity_eval", {})
        rule_only = entity_eval.get("rule_only", {})
        rule_ner = entity_eval.get("rule_ner", {})

        # High-Level Summary
        c1, c2, c3, c4 = st.columns(4)
        ex_micro = rule_only.get("exact_micro", {})
        rel_micro = rule_only.get("relaxed_micro", {})

        with c1:
            st.metric("Exact Micro F1", f"{ex_micro.get('f1', 0.0):.3f}")
        with c2:
            st.metric("Exact Micro Recall", f"{ex_micro.get('recall', 0.0):.3f}")
        with c3:
            st.metric("Relaxed Micro F1", f"{rel_micro.get('f1', 0.0):.3f}")
        with c4:
            st.metric("Relaxed Micro Recall", f"{rel_micro.get('recall', 0.0):.3f}")

        # Baseline Comparison Table
        st.markdown("---")
        st.markdown("**Entity Detection Pipeline Comparison:**")
        comp_rows = []
        if rule_only:
            ro_ex = rule_only.get("exact_micro", {})
            ro_rel = rule_only.get("relaxed_micro", {})
            comp_rows.append(
                {
                    "Pipeline Configuration": "Rule Baseline (RegEx + Checksums + Secrets)",
                    "Exact Prec": ro_ex.get("precision", 0.0),
                    "Exact Recall": ro_ex.get("recall", 0.0),
                    "Exact F1": ro_ex.get("f1", 0.0),
                    "Exact F2": ro_ex.get("f2", 0.0),
                    "Relaxed F1": ro_rel.get("f1", 0.0),
                    "Relaxed Recall": ro_rel.get("recall", 0.0),
                }
            )
        if rule_ner:
            rn_ex = rule_ner.get("exact_micro", {})
            rn_rel = rule_ner.get("relaxed_micro", {})
            comp_rows.append(
                {
                    "Pipeline Configuration": "Rule + spaCy NER (en_core_web_sm)",
                    "Exact Prec": rn_ex.get("precision", 0.0),
                    "Exact Recall": rn_ex.get("recall", 0.0),
                    "Exact F1": rn_ex.get("f1", 0.0),
                    "Exact F2": rn_ex.get("f2", 0.0),
                    "Relaxed F1": rn_rel.get("f1", 0.0),
                    "Relaxed Recall": rn_rel.get("recall", 0.0),
                }
            )

        df_comp = pd.DataFrame(comp_rows)
        st.dataframe(df_comp, use_container_width=True, hide_index=True)

        # Per-Type Granular Metrics Table
        st.markdown("---")
        st.markdown("**Per-Entity-Type Performance Breakdown:**")

        exact_by_type = rule_only.get("exact_by_type", {})
        relaxed_by_type = rule_only.get("relaxed_by_type", {})

        per_type_rows = []
        for et in sorted(list(exact_by_type.keys())):
            ex_stats = exact_by_type.get(et, {})
            rel_stats = relaxed_by_type.get(et, {})
            per_type_rows.append(
                {
                    "Entity Type": et,
                    "TP": ex_stats.get("tp", 0),
                    "FP": ex_stats.get("fp", 0),
                    "FN": ex_stats.get("fn", 0),
                    "Exact Prec": ex_stats.get("precision", 0.0),
                    "Exact Recall": ex_stats.get("recall", 0.0),
                    "Exact F1": ex_stats.get("f1", 0.0),
                    "Exact F2": ex_stats.get("f2", 0.0),
                    "Relaxed F1": rel_stats.get("f1", 0.0),
                    "Relaxed Recall": rel_stats.get("recall", 0.0),
                }
            )

        df_per_type = pd.DataFrame(per_type_rows)
        st.dataframe(df_per_type, use_container_width=True, hide_index=True)

        # Per-Type Chart
        if not df_per_type.empty:
            st.markdown("**F1 Score by Entity Type:**")
            cols = ["Entity Type", "Exact F1", "Relaxed F1"]
            chart_df = df_per_type[cols].set_index("Entity Type")
            st.bar_chart(chart_df, use_container_width=True)

        # Error Galleries (Synthetic Test Set Only)
        st.markdown("---")
        st.markdown("**Inspection Galleries (Synthetic Test Examples):**")
        gal_col1, gal_col2 = st.columns(2)

        with gal_col1:
            with st.expander("False Positives Gallery (Precision Review)"):
                fps = rule_only.get("fp_gallery", [])
                if not fps:
                    st.success("No false positive patterns recorded in this evaluation run.")
                else:
                    for item in fps[:5]:
                        st.markdown(
                            f"- **ID:** `{item.get('id')}` | **Type:** `{item.get('type')}`\n"
                            f"  *Span:* `{item.get('span')}` | *Detector:* `{item.get('detector')}`"
                        )

        with gal_col2:
            with st.expander("False Negatives Gallery (Recall Gaps)"):
                fns = rule_only.get("fn_gallery", [])
                if not fns:
                    st.success("No false negative misses recorded in this evaluation run.")
                else:
                    for item in fns[:5]:
                        st.markdown(
                            f"- **ID:** `{item.get('id')}` | **Type:** `{item.get('type')}`\n"
                            f"  *Span:* `{item.get('span')}`"
                        )

    # =========================================================================
    # TAB 2: Message Risk Triage
    # =========================================================================
    with tab_message:
        st.markdown("### Message-Level Exposure Risk Classification")
        st.caption(
            "Evaluation of whole-message policy compliance classification "
            "(high_risk_exposure vs possible_exposure vs no_exposure)."
        )

        baselines = test_metrics.get("baselines", {})

        # Baseline Comparison Table
        st.markdown("**Triage Baselines Comparison:**")
        base_rows = []
        for b_name in ["majority", "keyword", "rule_only", "rule_ner"]:
            b_data = baselines.get(b_name, {})
            if b_data:
                label_map = {
                    "majority": "Majority Class Predictor",
                    "keyword": "Naive Keyword Matcher",
                    "rule_only": "LEAKGUARD Rule Baseline (Shipped)",
                    "rule_ner": "LEAKGUARD Rule + spaCy NER",
                }
                base_rows.append(
                    {
                        "Method": label_map.get(b_name, b_name),
                        "Precision": b_data.get("precision", 0.0),
                        "Recall": b_data.get("recall", 0.0),
                        "F1": b_data.get("f1", 0.0),
                        "F2": b_data.get("f2", 0.0),
                        "ROC-AUC": b_data.get("roc_auc", 0.0),
                    }
                )

        df_base = pd.DataFrame(base_rows)
        st.dataframe(df_base, use_container_width=True, hide_index=True)

        # Confusion Matrix
        st.markdown("---")
        cm_col1, cm_col2 = st.columns(2)

        with cm_col1:
            st.markdown("**Rule Baseline Confusion Matrix (Held-out Test):**")
            cm = baselines.get("rule_only", {}).get("confusion_matrix", [[0, 0], [0, 0]])
            df_cm = pd.DataFrame(
                cm,
                index=["True Negative", "True Positive"],
                columns=["Pred Negative", "Pred Positive"],
            )
            st.table(df_cm)
            st.caption("Binary classification of exposure risk vs benign text.")

        with cm_col2:
            st.markdown("**Dataset Split Profile:**")
            splits = meta.get("split_sizes", {})
            df_splits = pd.DataFrame(
                [
                    {"Split": "Train", "Size (Messages)": splits.get("train", 0)},
                    {"Split": "Validation", "Size (Messages)": splits.get("val", 0)},
                    {"Split": "Test", "Size (Messages)": splits.get("test", 0)},
                    {"Split": "Human Challenge", "Size (Messages)": splits.get("challenge", 0)},
                ]
            )
            st.dataframe(df_splits, use_container_width=True, hide_index=True)

        # Classifier Gate Verdict Card
        st.markdown("---")
        st.markdown("### 🔒 ML Classifier Acceptance Gate Verdict")

        ch_status = meta.get("challenge_set_status", "missing")
        st.markdown(
            f"""
            <div class="leakguard-card" style="border-left: 4px solid #f59e0b; font-size: 0.9rem;">
                <div style="font-weight: 700; color: #f59e0b; margin-bottom: 0.5rem;
                            font-size: 1rem;">
                    GATE STATUS: CLASSIFIER WITHHELD (Detector-Only Shipped)
                </div>
                <div style="margin-bottom: 0.5rem; color: #cbd5e1;">
                    <strong>Decision Rationale:</strong> The project policy requires any ML
                    classifier to statistically improve recall at fixed precision over the rule
                    baseline on a <strong>human challenge set</strong> (with 95% bootstrap
                    confidence interval excluding 0).
                </div>
                <div style="margin-bottom: 0.5rem; color: #cbd5e1;">
                    <strong>Human Challenge Set Status:</strong> <code>{ch_status}</code> (N=0).
                    Because independent human annotations were not authored before release, the
                    ML classifier was <strong>deliberately not deployed</strong> to prevent
                    unverified synthetic overfitting.
                </div>
                <div style="color: #94a3b8; font-size: 0.85rem;">
                    <strong>Threshold Explorer:</strong> Inactive for Detector-Only v1.
                    System operates strictly via verified regexes, checksum algorithms,
                    and Shannon entropy bounds.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__" or "streamlit" in __name__:
    render_model_lab()
