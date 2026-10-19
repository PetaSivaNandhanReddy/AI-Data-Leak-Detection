# Phase 2 Report — Data and Label Design

**Project:** LEAKGUARD Rebuild of AI-Data-Leak-Detection  
**Phase:** 2 (Data and Label Design)  
**Execution Date:** 2026-10-18  
**Auditor / Engineer:** Antigravity Senior Engineer Agent  
**Branch:** `feature/leakguard-rebuild`  
**Target Environment:** Python 3.11.9 (Windows 11 host)  

---

## 1. Executive Summary

Phase 2 established a leak-safe, reproducible data generation and evaluation framework for LEAKGUARD:
1. **Annotation Guidelines:** Authored `docs/annotation_guidelines.md` establishing 11 entity types (`EMAIL`, `PHONE`, `PERSON`, `CARD`, `AADHAAR`, `PAN`, `IBAN`, `ACCOUNT_NUMBER`, `VOTER_ID`, `PASSWORD`, `API_KEY`/`SECRET_TOKEN`) alongside decoys, hard negatives, and three policy-grounded message-level risk tiers (`no_exposure`, `possible_exposure`, `high_risk_exposure`) with positive, negative, and borderline examples.
2. **Deterministic Template Generator:** Authored `src/leakguard/data/synthetic_values.py`, `src/leakguard/data/templates.py`, and `src/leakguard/data/generate.py`. Created 157 author-written templates across 15 semantic families. Fake values utilize Faker (`en_IN`, `en_US` locales) combined with mathematical checksum algorithms:
   - Payment cards: 16-digit test BINs satisfying Luhn checksum algorithm.
   - Aadhaar: 12-digit numbers satisfying Verhoeff checksum algorithm within non-allocated `9999` test prefixes.
   - Indian PAN: Structured alphanumeric format regex (`[A-Z]{5}[0-9]{4}[A-Z]`).
   - IBAN: ISO 7064 Mod-97-10 check digits.
   - Cloud tokens and passwords: Clearly non-functional test tokens (`AKIA...`, `ghp_...`, `xoxb-...`, `Bearer eyJ...`).
   - Decoys and hard negatives: Non-Luhn 16-digit numbers, non-Verhoeff numbers, tracking/order IDs (`ORD-992...`), version tags (`v2.4.1`), safe placeholders (`<INSERT_API_KEY>`), RFC documentation emails (`user@example.com`, `admin@example.org`).
3. **Strict Offset Alignment:** Every generated row defines exact `[start, end)` half-open Python Unicode code-point offsets such that `text[start:end] == value` is guaranteed by construction and verified by validation.
4. **Group Splitting & Leakage Prevention:** Implemented `src/leakguard/data/splits.py` performing group splits strictly by `family_id` (60% train, 20% validation, 20% test). Enforces zero cross-split family overlap, zero exact duplicate text (via normalized SHA-256 hashes), and zero near-duplicates (via inverted-index n-gram Jaccard similarity > 0.85).
5. **Schema and Dataset Validation:** Implemented `src/leakguard/data/validate.py` validating schema types, character-offset alignment, non-empty text, Unicode validity, and label taxonomy.
6. **Data Manifest & Data Card:** Generated `data/manifest.json` (source, generator version 0.1.0, seed 42, split counts, checksums, licenses, transformation steps) and wrote comprehensive documentation in `docs/data_card.md`.
7. **Human Challenge Benchmark Reservation:** Documented human-authoring protocol and schema guidelines in `data/challenge/README.md` for the upcoming 150–300 message human-written evaluation set.
8. **Committed Sample:** Extracted exactly 200 representative, balanced records to `data/samples/sample_200.jsonl` for version control. Bulk training data (`data/processed/`) remains properly ignored.
9. **Proven Determinism & Security:** Proved byte-identical reproducibility across independent runs, green linting/formatting (`ruff check`, `ruff format`), 100% test pass rate (`pytest -q`, 14 passed), and zero real secrets detected.

---

## 2. Dataset Statistics (Computed)

Total records generated: **4,000** (seed: 42, generator version: 0.1.0).

### 2.1 Group Splits (by `family_id`)

| Split | Records | Ratio | Template Families Assigned |
|---|---|---|---|
| **Train** | 2,382 | 59.55% | `fam_cloud_infra`, `fam_customer_support`, `fam_decoy_negative`, `fam_dev_logs`, `fam_ecommerce_orders`, `fam_fin_cards`, `fam_multiline_tickets`, `fam_policy_guidance`, `fam_unicode_samples` (9 families) |
| **Validation** | 796 | 19.90% | `fam_casing_variants`, `fam_credentials_chat`, `fam_credentials_git` (3 families) |
| **Test** | 822 | 20.55% | `fam_banking_in`, `fam_hr_recruitment`, `fam_identity_in` (3 families) |
| **Total** | 4,000 | 100.0% | 15 families (157 templates) |

*Family Overlap:* **0** families shared between any splits.  
*Cross-Split Exact Duplicates:* **0** normalized text matches.  
*Cross-Split Near Duplicates (Jaccard > 0.85):* **0** near-duplicate pairs.

### 2.2 Message-Level Class Distribution

| Class | Count | Percentage | Description |
|---|---|---|---|
| `high_risk_exposure` | 1,553 | 38.83% | Active credentials, API keys, database URLs, full credit cards |
| `possible_exposure` | 1,497 | 37.42% | Personal contact info, Indian identity documents, domestic bank accounts |
| `no_exposure` | 950 | 23.75% | Safe placeholders, RFC documentation domains, order IDs, security policy text |

### 2.3 Entity Type Instance Counts

| Entity Type | Count | Validation Standard |
|---|---|---|
| `PERSON` | 1,497 | Synthetic human names across `en_IN` and `en_US` Faker locales |
| `EMAIL` | 884 | RFC 5322 synthetic emails on non-routable domains |
| `PHONE` | 781 | Indian mobile (`+91`) and international phone numbers |
| `PASSWORD` | 725 | Synthetic plaintext passwords in code/chat |
| `API_KEY` | 700 | Non-functional test tokens (`AKIA...`, `ghp_...`, `xoxb-...`, `Bearer...`) |
| `CARD` | 336 | 16-digit cards in test BINs passing Luhn checksum algorithm |
| `ACCOUNT_NUMBER` | 284 | Domestic bank account numbers (11–14 digits) |
| `PAN` | 206 | Indian Permanent Account Numbers matching statutory regex structure |
| `AADHAAR` | 181 | 12-digit Indian national identity passing Verhoeff algorithm |
| `IBAN` | 52 | International bank account numbers passing ISO 7064 Mod-97-10 |
| `VOTER_ID` | 52 | Indian Voter ID (EPIC format: 3 letters + 7 digits) |

---

## 3. Commands Run and Real Results

| Command | Working Directory | Exit Code | Real Output Summary |
|---|---|---|---|
| `pip install faker` | Workspace root (`.venv`) | 0 | `Successfully installed faker-40.43.0` |
| `python -m leakguard.data.generate --seed 42 --out data/processed` | Workspace root | 0 | Generated 4000 records; 4000/4000 valid; splits written; manifest created |
| `python scratch/test_determinism.py` | Workspace root | 0 | `SUCCESS: All files byte-identical across runs!` |
| `pytest -q tests/test_data_validation.py` | Workspace root | 0 | `............ [100%]` (12 passed in 2.35s) |
| `pytest -q` | Workspace root | 0 | `.............. [100%]` (14 passed in 2.65s) |
| `ruff check .` | Workspace root | 0 | `All checks passed!` |
| `ruff format --check .` | Workspace root | 0 | `24 files already formatted` |
| `pip-audit -r requirements-dev.txt` | Workspace root | 0 | `No known vulnerabilities found` |
| `python scratch/scan_secrets.py` | Workspace root | 0 | `Scanned 31 files. ZERO real secrets found.` |

### Integrity Verification (SHA-256 Checksums)

- `data/manifest.json`: `d1263598a6d89e315691ceeae4fbda2da9672a112be6993c597c7b575d95bade`
- `data/samples/sample_200.jsonl`: `af9c1675d8af40a45ab2ed6cf77dbaa23295f7f86b4eb6358a64da84a4b59df3`
- `data/processed/train.jsonl`: `4f3cfcf1125d09742291eac05258f6195f9346bb8c6c6886b5a7ef0805d10e7d`
- `data/processed/val.jsonl`: `6e77592c6a2e02cad99ca9dfb141ee1256189e6dc52c2b462431dc9b51a77f48`
- `data/processed/test.jsonl`: `d76b89dc408ecc109fdca59ee9f15001b1b4341af0e5100e1f71a3b8a4768bf6`
- `data/processed/all.jsonl`: `d8cb434e312b1c6af7f33be2c4f78838c2c7c2b65df8c4880e66315ff4cb0d70`

---

## 4. Files Created, Changed, and Deleted

### Files Created
- `docs/annotation_guidelines.md` (entity taxonomy, message risk tiers, offset rules, decoys)
- `docs/data_card.md` (dataset card, split statistics, entity frequencies, privacy guarantees)
- `src/leakguard/data/__init__.py` (package exports)
- `src/leakguard/data/synthetic_values.py` (checksum algorithms, Indian/global generators, decoys)
- `src/leakguard/data/templates.py` (157 author-written templates across 15 families)
- `src/leakguard/data/splits.py` (family-level group split, exact and near duplicate detection)
- `src/leakguard/data/validate.py` (schema, offset alignment, Unicode, label validation)
- `src/leakguard/data/generate.py` (deterministic CLI generator and manifest builder)
- `data/manifest.json` (dataset provenance, checksums, seed, transformation steps)
- `data/challenge/README.md` (procedure and schema for human-written challenge set)
- `data/samples/sample_200.jsonl` (200-row representative balanced sample for git tracking)
- `tests/test_data_validation.py` (12 unit and integration tests)
- `reports_phase/PHASE_2_REPORT.md` (this report)

### Files Changed
- `requirements-dev.txt` (pinned `faker==40.43.0`)
- `pyproject.toml` (added scratch to ruff exclude, added per-file-ignore for E501 in `data/templates.py`)

### Files Deleted
- **None** (zero files deleted or destructively modified)

---

## 5. Decisions Made and Why

1. **Segment-Level Dynamic Offset Tracking:** Instead of rendering text and doing substring search (which causes ambiguity when values repeat), templates are defined as sequences of literals and dynamic slots. Spans are calculated during rendering, guaranteeing 100% exact character offset alignment.
2. **Mathematical Checksum Algorithms:** Implemented Verhoeff for Aadhaar (using non-allocated `9999` test prefixes), Luhn for payment cards (in test BINs), and ISO 7064 Mod-97-10 for IBAN. This ensures detectors and classifiers evaluate genuine syntactic structures without risking real identity leaks.
3. **Group Splitting by Family:** Random row splits cause the model to memorize template phrasing between train and test. Group splitting by `family_id` guarantees that evaluation tests generalization to completely unseen template structures.
4. **Secondary Source (Nannigalaxy) Skipped:** Per prompt instruction ("OPTIONAL SECONDARY SOURCE (only if I ask)... If you cannot access it, skip and report"), no manual download was requested or provided; skipped cleanly with zero impact on primary dataset generation.

---

## 6. Unresolved Issues & Risks

- **Human Challenge Set Creation:** The human-written challenge set (`data/challenge/challenge_set.jsonl`, 150–300 messages) must be authored by the user before Phase 4/5 evaluation. The template schema and authoring protocol are fully documented in `data/challenge/README.md`.
- **Template Diversity vs Real World:** While 157 templates across 15 families provide strong coverage of enterprise communication styles, evaluating solely on synthetic data can overestimate classifier capability. The human challenge set remains the definitive release gate.

---

## 7. Exact Next Steps

1. Commit Phase 2 changes to `feature/leakguard-rebuild`.
2. Review Phase 2 report and verify gate passage.
3. Proceed to **Phase 3: Core Detection Pipeline and Redaction Engine** (`PROMPT 3`).

---

## 8. Gate Acceptance Criteria & Status

| Acceptance Criterion | Verification Evidence | Status |
|---|---|---|
| **Deterministic Generation Proven** | `python scratch/test_determinism.py` confirmed 100% byte-identical outputs across consecutive runs for all generated files | **PASS** |
| **Zero Cross-Split Family Overlap** | Verified `train_families`, `val_families`, `test_families` are completely disjoint sets (9 train, 3 val, 3 test) | **PASS** |
| **Zero Cross-Split Near-Duplicates** | Inverted-index n-gram Jaccard similarity check passed with zero near-duplicates > 0.85; exact normalized hash check passed | **PASS** |
| **All Spans Align** | 4,000 / 4,000 records pass `validate_record` with `text[start:end] == value` verified byte-for-byte | **PASS** |
| **Data Card & Guidelines Complete** | `docs/annotation_guidelines.md` and `docs/data_card.md` authored with complete taxonomies and statistics | **PASS** |
| **Class Balance & Counts Reported Honestly** | Computed counts from `manifest.json`: 1553 high risk (38.8%), 1497 possible (37.4%), 950 no exposure (23.8%) | **PASS** |
| **No Real Personal Data** | Synthesized using `en_IN`/`en_US` Faker with test card ranges, non-allocated Aadhaar prefixes, RFC domains; zero secrets found | **PASS** |
| **Unit & Integration Tests Pass** | `pytest -q` (14 passed), `ruff check .` (passed), `pip-audit` (0 vulnerabilities) | **PASS** |

### **GATE: PASSED**
