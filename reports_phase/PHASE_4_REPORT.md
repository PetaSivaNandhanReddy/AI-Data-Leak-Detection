# Phase 4 Report — Optional NER Adapter and Presidio/spaCy Benchmark

**Project:** LEAKGUARD Rebuild of AI-Data-Leak-Detection  
**Phase:** 4 (Optional NER Adapter and Presidio/spaCy Benchmark)  
**Execution Date:** 2026-10-18  
**Auditor / Engineer:** Antigravity Senior Engineer Agent  
**Branch:** `feature/leakguard-rebuild`  
**Target Environment:** Python 3.11.9 (Windows 11 host)  

---

## 1. Executive Summary

Phase 4 evaluated whether Named Entity Recognition (NER) frameworks (specifically **spaCy** and **Microsoft Presidio**) provide justifiable accuracy gains over deterministic pattern rules, and whether their latency and memory profiles fit within the **1 GB (1,024 MB) idle memory budget** required for Streamlit Community Cloud:

1. **Protocol-Driven NER Adapter Architecture (`src/leakguard/detection/ner_adapter.py`):**
   - Implemented `NERAdapterProtocol` establishing standard interfaces (`is_available()`, `get_status()`, `detect()`).
   - Implemented `SpacyNERAdapter` with lazy loading, scoped strictly to the entity types it is evaluated for (default: `PERSON`).
   - Implemented `PresidioNERAdapter` wrapping Microsoft Presidio AnalyzerEngine in both custom and default configurations.
   - Built-in graceful degradation: when packages or models are missing, adapters report `"NER unavailable: ..."` without throwing runtime exceptions, and `Pipeline` degrades cleanly to Phase 3 core behavior.
2. **Standardized Comparative Benchmark (`src/leakguard/evaluation/ner_benchmark.py`):**
   - Executed benchmark on the held-out **VALIDATION split** (796 records, 1,001 ground-truth entities).
   - Evaluated 4 candidate configurations:
     - **Config A:** Phase 3 Core Detectors Only (Regex + Secret).
     - **Config B:** Phase 3 Core + spaCy `en_core_web_sm` for `PERSON` only.
     - **Config C:** Phase 3 Core + Presidio with custom India recognizers.
     - **Config D:** Presidio Default Standalone (out-of-the-box Microsoft Presidio AnalyzerEngine).
   - Measured exact and relaxed matching ($P, R, F_1, F_2$), latency distributions ($p_{50}, p_{95}$ on 200 scans), and memory usage via `psutil` against the 1 GB ceiling.
   - Saved raw benchmark JSON to [`reports/ner_benchmark.json`]([REDACTED_LOCAL_URI]).
3. **Decisions Documented in Decision Memo (`docs/ner_decision.md`):**
   - **ACCEPTED:** Candidate B (Phase 3 Core + spaCy `en_core_web_sm` for `PERSON`). It increases validation Exact Micro $F_2$ by **+7.49 points** (from 0.4630 to 0.5379) and achieves **72.22% recall** on `PERSON`, while consuming only **181.45 MB peak RSS (17.72% of budget)**, leaving **>840 MB** headroom.
   - **REJECTED:** Microsoft Presidio. Presidio Default (Config D) collapsed on the benchmark with an Exact Micro $F_1$ of only **0.2745**, completely missing Indian PANs, database passwords, developer tokens, and bank accounts. Presidio Custom (Config C) added higher latency ($p_{95}: 33.73\text{ ms}$) without exceeding Candidate B accuracy ($F_1: 0.5748$ vs $0.5774$).
4. **Dependency Strategy:**
   - Added `spacy==3.8.16` and the pinned model wheel URL (`https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl`) to `requirements.txt` marked `# to verify at deployment`.
   - Maintained optional extra `ner = ["spacy>=3.7.0,<3.9.0", "presidio-analyzer>=2.2.350"]` in `pyproject.toml`.
   - `presidio-analyzer` was deliberately excluded from `requirements.txt`.
5. **Quality and Regression Verification:**
   - 100% test pass rate across 51 unit and integration tests (including tests proving core passes when the model is absent).
   - Clean linting and formatting via `ruff check` and `ruff format`.
   - 0 real secrets detected across 58 repository files.

---

## 2. Command Execution & Real Results

### 2.1 Benchmark Execution

**Command:**
```powershell
.\.venv\Scripts\python.exe -m leakguard.evaluation.ner_benchmark
```

**Real Output Summary:**
```text
Loaded 796 validation records from data/processed/val.jsonl

================================================================================
STARTING CANDIDATE CONFIGURATION BENCHMARK
================================================================================

Evaluating: Configuration A (Phase 3 Core Only) ...
  -> Exact Micro F1: 0.5381 | F2: 0.4630 | Relaxed Micro F1: 0.6041 | F2: 0.5198
  -> Latency p50: 0.09ms | p95: 0.17ms | Peak RSS: 152.5 MB (14.9% of 1GB)
  -> PERSON Exact P: 0.0000, R: 0.0000, F1: 0.0000
  -> PERSON Relaxed P: 0.0000, R: 0.0000, F1: 0.0000

Evaluating: Configuration B (Phase 3 + spaCy en_core_web_sm) ...
  -> Exact Micro F1: 0.5774 | F2: 0.5379 | Relaxed Micro F1: 0.6390 | F2: 0.5954
  -> Latency p50: 13.87ms | p95: 20.97ms | Peak RSS: 181.5 MB (17.7% of 1GB)
  -> PERSON Exact P: 0.4375, R: 0.7222, F1: 0.5449
  -> PERSON Relaxed P: 0.4519, R: 0.7460, F1: 0.5629

Evaluating: Configuration C (Phase 3 + Presidio Custom) ...
  -> Exact Micro F1: 0.5748 | F2: 0.5370 | Relaxed Micro F1: 0.6362 | F2: 0.5944
  -> Latency p50: 14.56ms | p95: 33.73ms | Peak RSS: 167.3 MB (16.3% of 1GB)
  -> PERSON Exact P: 0.4396, R: 0.7222, F1: 0.5465
  -> PERSON Relaxed P: 0.4541, R: 0.7460, F1: 0.5646

Evaluating: Configuration D (Presidio Default Standalone) ...
  -> Exact Micro F1: 0.2745 | F2: 0.2150 | Relaxed Micro F1: 0.3168 | F2: 0.2481
  -> Latency p50: 15.79ms | p95: 22.63ms | Peak RSS: 172.2 MB (16.8% of 1GB)
  -> PERSON Exact P: 0.4062, R: 0.7222, F1: 0.5200
  -> PERSON Relaxed P: 0.4196, R: 0.7460, F1: 0.5371

Raw benchmark metrics saved to: reports/ner_benchmark.json
```

### 2.2 Test Suite Execution

**Command:**
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

**Real Output:**
```text
...................................................                      [100%]
51 passed in 6.20s
```

### 2.3 Style and Formatting Checks

**Command:**
```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
```

**Real Output:**
```text
All checks passed!
50 files already formatted
```

### 2.4 Secret Audit

**Command:**
```powershell
.\.venv\Scripts\python.exe scratch/scan_secrets.py
```

**Real Output:**
```text
Scanned 58 files.
ZERO real secrets found. All detected patterns are documented non-functional test tokens.
```

---

## 3. Benchmark Comparison Table

All metrics below reflect the evaluation on the held-out validation set (796 messages):

| Metric / Dimension | Config A (Phase 3 Core) | Config B (Core + spaCy `sm`) | Config C (Core + Presidio Custom) | Config D (Presidio Default) |
|---|---|---|---|---|
| **Exact Micro $F_1$** | 0.5381 | **0.5774** | 0.5748 | 0.2745 |
| **Exact Micro $F_2$** | 0.4630 | **0.5379** | 0.5370 | 0.2150 |
| **Relaxed Micro $F_1$** | 0.6041 | **0.6390** | 0.6362 | 0.3168 |
| **Relaxed Micro $F_2$** | 0.5198 | **0.5954** | 0.5944 | 0.2481 |
| **PERSON Exact $P / R / F_1$** | 0.0 / 0.0 / 0.0 | **0.4375 / 0.7222 / 0.5449** | 0.4396 / 0.7222 / 0.5465 | 0.4062 / 0.7222 / 0.5200 |
| **PERSON Relaxed $P / R / F_1$**| 0.0 / 0.0 / 0.0 | **0.4519 / 0.7460 / 0.5629** | 0.4541 / 0.7460 / 0.5646 | 0.4196 / 0.7460 / 0.5371 |
| **PAN Exact Recall** | **1.0000** (25/25) | **1.0000** (25/25) | **1.0000** (25/25) | 0.0000 (0/25) |
| **Password Exact Recall** | **0.1851** (67/362) | **0.1851** (67/362) | **0.1851** (67/362) | 0.0000 (0/362) |
| **API Key Exact Recall** | **0.5460** (184/337) | **0.5460** (184/337) | **0.5460** (184/337) | 0.0000 (0/337) |
| **Scan Latency $p_{50}$** | **0.09 ms** | 13.87 ms | 14.56 ms | 15.79 ms |
| **Scan Latency $p_{95}$** | **0.17 ms** | **20.97 ms** | 33.73 ms | 22.63 ms |
| **Peak Process RSS** | 152.54 MB | 181.45 MB | 167.30 MB | 172.16 MB |
| **$\Delta$ RSS Allocated** | **0.01 MB** | 28.91 MB | 0.00 MB | 3.12 MB |
| **1 GB Budget Utilization** | **14.90%** | **17.72%** | 16.34% | 16.81% |

---

## 4. Files Created, Changed, and Deleted

### 4.1 Files Created
- `src/leakguard/detection/ner_adapter.py`: `NERAdapterProtocol`, `SpacyNERAdapter` (lazy loading, scoped to `PERSON`), and `PresidioNERAdapter`.
- `src/leakguard/evaluation/__init__.py`: Evaluation module namespace.
- `src/leakguard/evaluation/ner_benchmark.py`: Comparative benchmark runner computing exact/relaxed metrics and memory profiles.
- `tests/test_ner_adapter.py`: 5 unit and integration tests verifying protocol compliance, missing-model fallbacks, and pipeline integration.
- `docs/ner_decision.md`: Formal Architectural Decision Record documenting the empirical findings and shipping recommendation.
- `reports/ner_benchmark.json`: Complete raw JSON benchmark output with system metadata, per-type metrics, and latency/memory records.
- `reports_phase/PHASE_4_REPORT.md`: This Phase 4 engineering and acceptance report.

### 4.2 Files Changed
- `src/leakguard/detection/pipeline.py`: Added optional `ner_adapter: NERAdapterProtocol | None = None` support with lazy execution and aggregator integration.
- `src/leakguard/detection/__init__.py`: Exported `NERAdapterProtocol`, `SpacyNERAdapter`, and `PresidioNERAdapter`.
- `pyproject.toml`: Added `[project.optional-dependencies] ner = ["spacy>=3.7.0,<3.9.0", "presidio-analyzer>=2.2.350"]`.
- `requirements.txt`: Added `spacy==3.8.16` and the pinned wheel URL for `en_core_web_sm-3.8.0` marked `# to verify at deployment`.

### 4.3 Files Deleted
- None.

---

## 5. Architectural Decisions Made & Why

1. **Protocol Decoupling Over Hard Coupling:** All NER components implement `NERAdapterProtocol`. The core pipeline does not depend on spaCy or Presidio being installed; if absent, `is_available()` returns `False` and `Pipeline` degrades cleanly to pure pattern matching.
2. **Restricting spaCy to `PERSON`:** Scoping `SpacyNERAdapter` strictly to `{"PERSON"}` prevents general-purpose NER entities (`ORG`, `GPE`, `CARDINAL`, `DATE`) from corrupting or overriding high-precision regex detectors on cards, account numbers, and government IDs.
3. **Rejection of Presidio:** Despite being a popular open-source PII tool, Presidio out-of-the-box produced a 0.2745 $F_1$ score due to its complete blindness to developer credentials and non-US regulatory formats. Its heavy dependency chain and higher latency ($p_{95}: 33.73\text{ ms}$) provide no value over `SpacyNERAdapter`.
4. **Streamlit Deployment Packaging:** Pinned the `en_core_web_sm` wheel directly from GitHub releases in `requirements.txt`. This avoids network download timeouts or failures via `spacy download` in restricted container build environments.

---

## 6. Known Limitations & Unresolved Issues

1. **Precision on Single-Token Common Surnames:** `en_core_web_sm` achieves 43.75% exact precision on `PERSON` because single capitalized words in short informal contexts (e.g., greetings or sentence-starting nouns) are occasionally tagged as personal names.
2. **Non-English Personal Names:** `en_core_web_sm` is an English model; while it identifies standard Western and transliterated Indian names (e.g., "Aarav Sharma", "Priya Patel"), names written in native Indic scripts (Devanagari, Tamil) are not tagged as `PERSON` by the English model.

---

## 7. Acceptance Criteria Verification

| Acceptance Criterion | Required Target | Actual Result | Status |
|---|---|---|---|
| Benchmark table produced from real runs | Validated on validation split | **Generated from 796 validation records; saved to `reports/ner_benchmark.json`** | **PASS** |
| Decision documented | Architectural decision memo written | **Comprehensive ADR written to `docs/ner_decision.md`** | **PASS** |
| Core passes tests with optional model ABSENT | Zero crashes when model missing | **Verified in `test_spacy_adapter_graceful_missing_model_fallback` & `test_pipeline_integration_with_and_without_ner`** | **PASS** |
| Test suite pass rate | 100% pass | **51 passed in 6.20s** | **PASS** |
| Code quality & linting | Clean ruff check/format | **50 files cleanly formatted; all checks passed** | **PASS** |
| Secret scanning | 0 credentials committed | **58 files scanned; 0 real secrets detected** | **PASS** |

---

## 8. Gate Status & Next Steps

### GATE: PASSED

Phase 4 is fully completed. All benchmark measurements are authentic, reproducible from one command (`python -m leakguard.evaluation.ner_benchmark`), and documented in the repository.

### Next Prompt to Run:
**PROMPT 5 — Evaluation and gated classifier experiment** (from `ANTIGRAVITY_PHASE_PROMPTS.md`).
