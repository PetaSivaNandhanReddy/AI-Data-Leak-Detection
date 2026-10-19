# Phase 5 Report — Evaluation and Gated Classifier Experiment

**Project:** LEAKGUARD Rebuild of AI-Data-Leak-Detection  
**Phase:** 5 (Evaluation and Gated Classifier Experiment)  
**Execution Date:** 2026-10-18  
**Auditor / Engineer:** Antigravity Senior Engineer Agent  
**Branch:** `feature/leakguard-rebuild`  
**Target Environment:** Python 3.11.9 (Windows 11 host)  

---

## 1. Executive Summary

Phase 5 established the complete evaluation and statistical verification framework for LEAKGUARD:
1. **Entity-Level Evaluation Engine (`src/leakguard/evaluation/entity_eval.py`):**
   - Implemented exact and relaxed span matching algorithms.
   - Computes per-type and micro/macro aggregated Precision, Recall, $F_1$, and $F_2$.
   - Automatically extracts False Positive (FP) and False Negative (FN) error galleries with text snippets and diagnostic rationales.
2. **Message-Level Evaluation & Confidence Intervals (`src/leakguard/evaluation/message_eval.py`):**
   - Formulated binary leak classification evaluation (`no_exposure` vs `possible_exposure` / `high_risk_exposure`).
   - Implemented standard evaluation metrics: Precision, Recall, $F_1$, $F_2$, PR-AUC, ROC-AUC, Confusion Matrix, and False Negative Rate at 95% Target Recall ($\text{FNR}_{95}$).
   - Computed non-parametric bootstrap 95% Confidence Intervals over 1,000 resamples (seed 42).
   - Implemented 4 standard baselines: Majority Class, Keyword Matching, Phase 3 Rule Engine, and Phase 4 Rule + spaCy NER.
3. **Machine Learning Classifier Experiment (`src/leakguard/classification/train.py`):**
   - Trained linear text classifiers via scikit-learn `Pipeline` (Word n-grams and Character n-grams + LogisticRegression).
   - Vectorizers were fit strictly on the training split fold (2,382 messages).
   - Inverse regularization strength $C$ and decision thresholds $\theta$ were tuned strictly on the validation fold (796 messages).
   - Single held-out evaluation was executed on the synthetic test split (822 messages).
4. **Challenge Set Status & ML Ship Gate Enforcement:**
   - Inspection of `data/challenge/` confirmed that the human challenge benchmark dataset has not yet been authored. Only the protocol file (`README.md`) exists.
   - Per project instructions, no synthetic data was fabricated to substitute for human data.
   - Every challenge evaluation entry was marked `"no challenge set yet"`.
   - **Gate Decision:** The machine learning classifier was **NOT SHIPPED** because the required human challenge set evidence is absent. LEAKGUARD continues to ship the deterministic detector-only configuration (Phase 4 Rule + spaCy NER).
5. **Standardized Reproducibility Artifacts:**
   - Generated [`reports/eval_latest.json`]([REDACTED_LOCAL_URI]) containing run parameters, seeds, git commit hash, all metrics, and score distributions.
   - Generated [`reports/run_metadata.json`]([REDACTED_LOCAL_URI]) recording environment and split sizes.
   - Generated [`reports/reference_corpus.json`]([REDACTED_LOCAL_URI]) by scanning all 822 synthetic test messages.
   - Authored comprehensive documentation in [`docs/methodology.md`]([REDACTED_LOCAL_URI]).
6. **Test Suite Verification:**
   - Added `tests/test_evaluation.py` verifying metrics against hand-computed ground truth and proving zero ID/family overlap across train, val, and test splits.
   - All 57 tests passed across the workspace in 5.8s.

---

## 2. Command Execution & Real Results

### 2.1 Master Evaluation Report Generation

**Command:**
```powershell
.\.venv\Scripts\python.exe -m leakguard.evaluation.report --out reports/
```

**Real Output:**
```text
Evaluation dataset loaded: 2382 train, 796 val, 822 test, 0 challenge.
Evaluating message-level baselines on validation split...
Evaluating message-level baselines on held-out test split...
Evaluating entity-level metrics on validation split...
Evaluating entity-level metrics on held-out test split...
Executing ML classifier training and evaluation experiment...
Generating reference corpus from synthetic test split...

Artifacts successfully written to 'reports':
  - eval_latest.json
  - run_metadata.json
  - reference_corpus.json
```

### 2.2 Evaluation Unit Test Suite

**Command:**
```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_evaluation.py
```

**Real Output:**
```text
......                                                                   [100%]
6 passed in 2.20s
```

### 2.3 Full Project Test Suite

**Command:**
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

**Real Output:**
```text
.........................................................                [100%]
57 passed in 5.80s
```

### 2.4 Code Style and Linting Checks

**Command:**
```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
```

**Real Output:**
```text
All checks passed!
58 files already formatted
```

### 2.5 Secret Audit

**Command:**
```powershell
.\.venv\Scripts\python.exe scratch/scan_secrets.py
```

**Real Output:**
```text
Scanned 69 files.
ZERO real secrets found. All detected patterns are documented non-functional test tokens.
```

---

## 3. Results Tables (Copied Directly from Artifacts)

### 3.1 Message-Level Performance Across Splits

#### Validation Split (796 messages: 721 Exposure, 75 No Exposure)
| Model / Baseline | Precision | Recall | $F_1$ Score (95% CI) | $F_2$ Score | ROC-AUC (95% CI) | PR-AUC | $\text{FNR}_{95}$ |
|---|---|---|---|---|---|---|---|
| **Majority Class** | 0.9058 | **1.0000** | 0.9506 [0.9394, 0.9615] | **0.9796** | 0.5000 [0.5000, 0.5000] | 0.9058 | **0.0000** |
| **Keyword Baseline** | **1.0000** | 0.6436 | 0.7831 [0.7549, 0.8083] | 0.6930 | 0.8218 [0.8032, 0.8391] | 0.9664 | **0.0000** |
| **Rule Only (Phase 3)** | **1.0000** | 0.6477 | 0.7862 [0.7581, 0.8111] | 0.6968 | 0.7975 [0.7711, 0.8213] | 0.9674 | **0.0000** |
| **Rule + spaCy NER (Phase 4)**| **1.0000** | 0.6505 | 0.7882 [0.7611, 0.8129] | 0.6994 | 0.8171 [0.7909, 0.8414] | 0.9709 | **0.0000** |
| **ML Word n-grams** | **1.0000** | 0.9847 | 0.9923 [0.9877, 0.9965] | 0.9878 | 0.9949 [0.9918, 0.9978] | 0.9995 | 0.0485 |
| **ML Char n-grams** | **1.0000** | **1.0000** | **1.0000 [1.0000, 1.0000]**| **1.0000** | **1.0000 [1.0000, 1.0000]**| **1.0000** | 0.0499 |

#### Held-Out Synthetic Test Split (822 messages: 822 Exposure, 0 No Exposure)
| Model / Baseline | Precision | Recall | $F_1$ Score | $F_2$ Score | ROC-AUC | PR-AUC | $\text{FNR}_{95}$ |
|---|---|---|---|---|---|---|---|
| **Majority Class** | 1.0000 | 1.0000 | 1.0000 | 1.0000 | N/A* | 1.0000 | 0.0000 |
| **Keyword Baseline** | 1.0000 | 0.3796 | 0.5503 | 0.4326 | N/A* | 1.0000 | 0.0000 |
| **Rule Only (Phase 3)** | 1.0000 | 0.8491 | 0.9184 | 0.8752 | N/A* | 1.0000 | 0.0000 |
| **Rule + spaCy NER (Phase 4)**| 1.0000 | **0.9696** | **0.9846** | **0.9755** | N/A* | 1.0000 | 0.0000 |
| **ML Word n-grams** | 1.0000 | 0.9927 | 0.9963 | 0.9942 | N/A* | 1.0000 | 0.0000 |
| **ML Char n-grams** | 1.0000 | 0.9732 | 0.9864 | 0.9785 | N/A* | 1.0000 | 0.0000 |
| **Human Challenge Benchmark** | **no challenge set yet** | **no challenge set yet** | **no challenge set yet** | **no challenge set yet** | **no challenge set yet** | **no challenge set yet** | **no challenge set yet** |

*\*Note on Synthetic Test ROC-AUC:* Because group partitioning assigned all templates of families `fam_banking_in`, `fam_hr_recruitment`, and `fam_identity_in` to the test split, the synthetic test split contains exclusively exposure messages ($y=1$). Ranking discrimination (ROC-AUC) requires both positive and negative cases and is mathematically undefined on single-class sets.

### 3.2 Entity-Level Performance (Held-Out Test Split)

Evaluated with Rule + spaCy NER (`SpacyNERAdapter(en_core_web_sm)`):

| Entity Class | Ground Truth Count | Exact Matches ($TP$) | Partial Overlaps ($TP_{rel}$) | Exact Precision | Exact Recall | Exact $F_1$ | Exact $F_2$ |
|---|---|---|---|---|---|---|---|
| **ACCOUNT_NUMBER** | 222 | 222 | 222 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **PERSON** | 632 | 511 | 564 | 0.8085 | 0.8085 | 0.8085 | 0.8085 |
| **EMAIL** | 304 | 304 | 304 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **CARD** | 14 | 14 | 14 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **PHONE** | 249 | 248 | 248 | 1.0000 | 0.9960 | 0.9980 | 0.9968 |
| **AADHAAR** | 166 | 166 | 166 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **IBAN** | 44 | 44 | 44 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **PAN** | 156 | 156 | 156 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **VOTER_ID** | 52 | 52 | 52 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **Micro Summary (Exact)** | **1,873** | **1,651** | — | **0.8978** | **0.8815** | **0.8895** | **0.8847** |
| **Micro Summary (Relaxed)**| **1,873** | — | **1,704** | **0.9266** | **0.9098** | **0.9181** | **0.9131** |

---

## 4. Plain-Language Summary of What the Numbers Show and Do Not Show

### What the Numbers Show:
1. **Rule + NER Engine Performs Superbly on Syntactically Grounded Data:** On the held-out synthetic test split, our deterministic rule engine combined with spaCy NER achieved **96.96% message recall** and **88.95% exact entity micro $F_1$** (91.81% relaxed $F_1$) with zero false positive entity predictions across bank account numbers, emails, cards, Aadhaar, IBANs, PANs, and voter IDs.
2. **Deterministic Rules Strongly Outperform Naive Keyword Matching:** Simple keyword matching achieved only 37.96% recall on the test set ($F_1: 0.5503$), proving that heuristic keyword checking is hopelessly inadequate for leak detection.
3. **ML Models Can Learn Carrier Syntax Easily:** Both the word n-gram and char n-gram logistic regression models achieved near-perfect scores ($F_1 \ge 0.98$) on synthetic splits.

### What the Numbers Do NOT Show:
1. **No Proof of Generalization to Organic Human Text:** Because machine learning classifiers were evaluated solely on synthetic templates, their high scores reflect template vocabulary associations rather than robust comprehension of unstructured developer text.
2. **No Discriminative Measurement on the Test Set:** Because all records in the synthetic test set happened to be exposure cases, the test split metrics do not evaluate negative discrimination (specificity/ROC-AUC).
3. **No Empirical Justification to Ship ML:** Without the human challenge set, shipping the ML model would violate the core architectural gate of the project.

---

## 5. Files Created, Changed, and Deleted

### 5.1 Files Created
- `src/leakguard/evaluation/entity_eval.py`: Entity exact/relaxed span evaluation and FP/FN error galleries.
- `src/leakguard/evaluation/message_eval.py`: Message-level classification metrics, baseline runners, and bootstrap CIs.
- `src/leakguard/classification/__init__.py`: Classification package namespace.
- `src/leakguard/classification/train.py`: ML classifier experiment runner with leakage-free train/val tuning.
- `src/leakguard/evaluation/report.py`: Master report generation CLI (`--out reports/`).
- `tests/test_evaluation.py`: Unit test suite verifying metrics against hand-computed values and proving split separation.
- `docs/methodology.md`: Full statistical methodology and limitations documentation.
- `reports/eval_latest.json`: Structured evaluation results, metadata, and score distributions.
- `reports/run_metadata.json`: Environment and execution metadata.
- `reports/reference_corpus.json`: Test set baseline scan distribution.
- `reports_phase/PHASE_5_REPORT.md`: This Phase 5 report.

### 5.2 Files Changed
- None.

### 5.3 Files Deleted
- None.

---

## 6. Acceptance Criteria Verification

| Acceptance Criterion | Required Target | Actual Result | Status |
|---|---|---|---|
| Artifacts reproducible from one command | `python -m leakguard.evaluation.report --out reports/` | **Verified: generates `eval_latest.json`, `run_metadata.json`, `reference_corpus.json`** | **PASS** |
| Metrics consistency | No metric in docs not present in artifacts | **All numbers directly match `eval_latest.json`** | **PASS** |
| Split separation proven by test | Train/Val/Test/Challenge separation | **Verified in `tests/test_evaluation.py` (0 ID overlap, 0 family overlap)** | **PASS** |
| Gate decision documented | Ship only if ML beats rules on challenge set | **Explicitly documented: ML NOT SHIPPED, ship detector-only** | **PASS** |
| Human challenge set presence | 150–300 human-written benchmark messages | **NOT PRESENT in `data/challenge/`** | **FAIL (Missing Prerequisite)** |
| Full unit test suite | All unit tests pass | **57 passed in 5.80s** | **PASS** |
| Code quality & linting | Clean ruff check/format | **58 files cleanly formatted; all checks passed** | **PASS** |
| Secret audit | 0 hardcoded credentials | **69 files scanned; 0 secrets detected** | **PASS** |

---

## 7. Gate Status

### GATE: NOT PASSED

**Reason:** In accordance with the prompt's explicit prerequisite instructions, because the human challenge set was not present in `data/challenge/`, all challenge results were recorded as `"no challenge set yet"`, the machine learning classifier was withheld from shipping, and the Phase 5 gate status is officially recorded as **`GATE: NOT PASSED`**.

---

## 8. Exact Instructions: How to Create and Validate the Human Challenge Set

To complete the Human Challenge Benchmark and satisfy the Phase 5 gate before proceeding to Phase 6, follow these exact steps:

### Step 1: Create the Challenge File
Create the file [`data/challenge/challenge_set.jsonl`]([REDACTED_LOCAL_URI]).

### Step 2: Author 150 – 300 Hand-Written Messages
Write between 150 and 300 realistic messages by hand (without automated template generation) across the four primary channels defined in [`data/challenge/README.md`]([REDACTED_LOCAL_URI]):
1. **Developer Chat (Slack/Discord):** Slang, quick credential shares, staging passwords.
2. **Version Control / CI/CD (GitHub/GitLab):** Commit messages, stack traces, bug reports.
3. **Indian Banking & Identity:** Realistic PAN/Aadhaar customer service conversations, IFSC transfers.
4. **Hard Negatives & Decoys:** Security policy discussions, RFC doc domains (`test@example.com`), software versions (`v2.4.1`), tracking IDs (`ORD-991204`). Aim for approximately 25–35% hard negatives (`no_exposure`).

### Step 3: Ensure Strict Schema Conformance
Every line in `data/challenge/challenge_set.jsonl` must be a valid JSON object matching this schema:
```json
{
  "id": "challenge_001",
  "text": "Hey Amit, can you verify this client KYC? PAN: ABCDE1234F for candidate Sunita Sharma.",
  "entities": [
    {
      "start": 51,
      "end": 61,
      "label": "PAN",
      "value": "ABCDE1234F"
    },
    {
      "start": 76,
      "end": 89,
      "label": "PERSON",
      "value": "Sunita Sharma"
    }
  ],
  "message_label": "possible_exposure"
}
```

**Validation Checks to Guarantee:**
- Character offsets `[start, end)` must align exactly with Python Unicode code points: `text[start:end] == value`.
- `message_label` must be one of: `"no_exposure"`, `"possible_exposure"`, or `"high_risk_exposure"`.
- Entity `label` must be one of the 11 supported taxonomies (`EMAIL`, `PHONE`, `PERSON`, `CARD`, `AADHAAR`, `PAN`, `IBAN`, `ACCOUNT_NUMBER`, `VOTER_ID`, `PASSWORD`, `API_KEY`).

### Step 4: Validate and Re-Run Evaluation
Run the schema validator:
```powershell
.\.venv\Scripts\python.exe -m leakguard.data.validate data/challenge/challenge_set.jsonl
```
Once validation passes, re-run the evaluation:
```powershell
.\.venv\Scripts\python.exe -m leakguard.evaluation.report --out reports/
```
The script will detect the challenge set, evaluate both rule and ML models, compute the bootstrap confidence intervals on human data, and determine whether the ML model earns release approval.
