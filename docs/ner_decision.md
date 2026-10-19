# Architectural Decision Record: NER Adapter & Dependency Selection (Phase 4)

**Decision Date:** 2026-10-18  
**Author:** Antigravity Senior Engineer Agent  
**Context:** LEAKGUARD Rebuild of AI-Data-Leak-Detection  
**Status:** **ACCEPTED**  

---

## 1. Executive Summary & Recommendation

In Phase 4, we conducted an empirical, measurement-driven benchmark to evaluate whether Named Entity Recognition (NER) frameworks (specifically **spaCy** and **Microsoft Presidio**) should be incorporated into the LEAKGUARD production pipeline.

Four candidate configurations were evaluated on the held-out **VALIDATION split** (796 messages, 1,001 ground-truth entities) measuring exact and relaxed entity matching ($P, R, F_1, F_2$), scan latency distributions ($p_{50}, p_{95}$ across 200 consecutive scans), model initialization times, and memory utilization against a **1 GB (1,024 MB) idle budget**:

- **Candidate A:** Phase 3 Core Only (Deterministic Regex + Secret Detector).
- **Candidate B:** Phase 3 Core + spaCy `en_core_web_sm` (restricted strictly to `PERSON`).
- **Candidate C:** Phase 3 Core + Presidio with custom India recognizers.
- **Candidate D:** Microsoft Presidio Default Standalone (out-of-the-box configuration).

### Formal Recommendation:
1. **SHIP Candidate B (Phase 3 Core + spaCy `en_core_web_sm` for `PERSON`):**
   - Incorporating spaCy restricted strictly to `PERSON` increases overall validation **Exact Micro $F_2$ by +7.49 points** (from 0.4630 to 0.5379) and **Relaxed Micro $F_2$ by +7.56 points** (from 0.5198 to 0.5954).
   - Achieves **72.22% exact recall** (91/126 detected) and **74.60% relaxed recall** on human personal names (`PERSON`), an entity class impossible to detect via deterministic regexes.
   - Resource overhead is minimal: **181.5 MB peak RSS** (**17.72% of the 1 GB budget**), leaving over **840 MB of memory headroom** for Streamlit Cloud execution. Scan latency ($p_{50}: 13.87\text{ ms}, p_{95}: 20.97\text{ ms}$) remains well within real-time interactive thresholds (<50 ms).
2. **REJECT Microsoft Presidio (Candidates C and D):**
   - Out-of-the-box Presidio (Candidate D) fails catastrophically on the benchmark (**Exact Micro $F_1: 0.2745, F_2: 0.2150$**). It has 0.0% recall on Indian PANs, database passwords, developer API tokens, and Indian bank account numbers.
   - Presidio with custom recognizers (Candidate C) yields a lower overall $F_1$ score than Candidate B (0.5748 vs 0.5774), introduces higher tail latency ($p_{95}: 33.73\text{ ms}$), and pulls in a bloated transitive dependency graph (`phonenumbers`, `tldextract`, `pyyaml`).
   - `presidio-analyzer` will **NOT** enter `requirements.txt`.

---

## 2. Empirical Benchmark Results Table

All metrics below are computed from actual runs recorded in [`reports/ner_benchmark.json`](file:///c:/Users/user/Downloads/AI-Data-Leak-Detection-main/AI-Data-Leak-Detection-main/reports/ner_benchmark.json) on the 796 validation split messages.

| Metric / Attribute | Config A (Phase 3 Core) | Config B (Core + spaCy `sm`) | Config C (Core + Presidio Custom) | Config D (Presidio Default) |
|---|---|---|---|---|
| **Architecture** | Regex + Secret | Regex + Secret + spaCy | Regex + Secret + Presidio | Standalone Presidio |
| **Dependencies Added** | None | `spacy`, `en_core_web_sm` | `spacy`, `presidio-analyzer` | `presidio-analyzer` |
| **Exact Micro Precision** | **0.7374** | 0.6577 | 0.6548 | 0.5095 |
| **Exact Micro Recall** | 0.4236 | **0.5145** | 0.5145 | 0.1878 |
| **Exact Micro $F_1$** | 0.5381 | **0.5774** | 0.5748 | 0.2745 |
| **Exact Micro $F_2$** | 0.4630 | **0.5379** | 0.5370 | 0.2150 |
| **Relaxed Micro $F_1$** | 0.6041 | **0.6390** | 0.6362 | 0.3168 |
| **Relaxed Micro $F_2$** | 0.5198 | **0.5954** | 0.5944 | 0.2481 |
| **PERSON Exact $P / R / F_1$**| 0.0 / 0.0 / 0.0 | **0.4375 / 0.7222 / 0.5449** | 0.4396 / 0.7222 / 0.5465 | 0.4062 / 0.7222 / 0.5200 |
| **PERSON Relaxed $P / R / F_1$**| 0.0 / 0.0 / 0.0 | **0.4519 / 0.7460 / 0.5629** | 0.4541 / 0.7460 / 0.5646 | 0.4196 / 0.7460 / 0.5371 |
| **PAN Exact Recall** | **1.0000** (25/25) | **1.0000** (25/25) | **1.0000** (25/25) | 0.0000 (0/25) |
| **Password Exact Recall** | 0.1851 (67/362) | 0.1851 (67/362) | 0.1851 (67/362) | 0.0000 (0/362) |
| **API Key Exact Recall** | 0.5460 (184/337) | 0.5460 (184/337) | 0.5460 (184/337) | 0.0000 (0/337) |
| **Init / Load Time** | **0.01 ms** | 408.74 ms | 11,114.40 ms | 610.77 ms |
| **Latency $p_{50}$ (200 scans)**| **0.09 ms** | 13.87 ms | 14.56 ms | 15.79 ms |
| **Latency $p_{95}$ (200 scans)**| **0.17 ms** | **20.97 ms** | 33.73 ms | 22.63 ms |
| **Baseline RSS** | 152.53 MB | 152.54 MB | 161.98 MB | 169.04 MB |
| **Peak RSS** | 152.54 MB | 181.45 MB | 167.30 MB | 172.16 MB |
| **Memory Delta ($\Delta$ RSS)** | **0.01 MB** | 28.91 MB | 0.00 MB | 3.12 MB |
| **1 GB Budget Utilization** | **14.90%** | **17.72%** | 16.34% | 16.81% |

---

## 3. Detailed Comparative Analysis

### 3.1 Why Presidio Default Fails (Candidate D)
Out-of-the-box Microsoft Presidio AnalyzerEngine produced an Exact Micro $F_1$ score of only **0.2745**.
1. **Complete Blindness to Developer Secrets:** Presidio lacks native recognizers for assignment passwords (`password = "..."`) or cloud provider API tokens (`AKIA...`, `ghp_...`, `xoxb-...`). It missed 100% of passwords (0/362) and 100% of API keys (0/337).
2. **Ignorance of Indian Regulatory Taxonomies:** Presidio has zero support for Indian Permanent Account Numbers (PAN) and Aadhaar numbers by default, yielding 0% recall across all PAN entities (0/25).
3. **Noisy False Positives:** Default regexes for URLs and phone numbers produced 181 false positives across the validation set.

### 3.2 Why spaCy `en_core_web_sm` is Superior for Personal Names
Personal human names (`PERSON`) cannot be recognized by regular expressions without prohibitive false-positive rates on common vocabulary.
- Candidate B leverages `en_core_web_sm` strictly scoped to `{"PERSON"}`.
- It detects **91 out of 126** personal names with exact character offsets ($R = 72.22\%$), and 94 out of 126 with relaxed overlap ($R = 74.60\%$).
- By restricting the adapter to `PERSON`, we prevent spaCy from overriding or competing with our mathematically validated regex detectors on cards, account numbers, and government IDs.

### 3.3 Memory Budget Impact
- **Budget Ceiling:** 1,024.0 MB (Streamlit Community Cloud free tier limit).
- **Candidate B Peak Memory:** 181.45 MB total process RSS.
- **Delta Allocated by spaCy:** 28.91 MB.
- **Budget Utilization:** 17.72% (leaves **842.55 MB** available headroom).
- **Conclusion:** Candidate B easily complies with the 1 GB constraint with extensive safety margin.

---

## 4. Implementation & Deployment Strategy

1. **Protocol Decoupling (`src/leakguard/detection/ner_adapter.py`):**
   - `NERAdapterProtocol` defines standard interfaces: `is_available()`, `get_status()`, and `detect(text)`.
   - `SpacyNERAdapter` implements lazy loading: the model is not loaded at import time, preventing startup latency when NER is not required.
   - If `spacy` or `en_core_web_sm` is not present, `is_available()` returns `False`, `get_status()` returns `"NER unavailable: ..."`, and `detect()` safely yields `[]`. The core pipeline continues executing with 100% reliability.
2. **Streamlit Community Cloud Deployment:**
   - In `requirements.txt`, we specify the pinned wheel distribution:
     ```text
     spacy==3.8.16
     https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
     ```
   - Marked `# to verify at deployment` per project requirements.
3. **Testing Resilience:**
   - All 46 Phase 3 test cases plus 5 new Phase 4 test cases pass unconditionally (51 passed in 6.2s).
   - Core codebase maintains zero UI dependencies.
