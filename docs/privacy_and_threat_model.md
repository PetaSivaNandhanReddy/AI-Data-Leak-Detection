# LEAKGUARD Privacy Architecture and Threat Model

This document specifies the privacy guarantees, threat model, mitigation strategies, and dependency justifications implemented in LEAKGUARD. Every guarantee documented below is backed by automated tests.

---

## 1. Core Privacy Principles

LEAKGUARD operates as an in-memory, zero-retention sensitive data detection and redaction engine. Its architecture adheres to the following privacy invariants:

1. **Zero Raw Text Persistence:** Input text is processed strictly in-memory during a single scan cycle. Raw text is never stored in files, databases, or local storage.
2. **Pure Metadata Logging:** Application logs record only coarse operational metadata (character lengths, processing durations in milliseconds, finding counts by severity). No raw user input or candidate secret values appear in logs.
3. **Planted Sentinel Scrubbing:** A dedicated `SanitizedPrivacyFilter` intercepts and scrubs potential secrets or registered test sentinels from log records and exception messages.
4. **Formula-Injection Neutralization:** All CSV and receipt exports prepend a single quote (`'`) to any cell beginning with spreadsheet formula triggers (`=`, `+`, `-`, `@`, tab `\t`, carriage return `\r`, line feed `\n`), neutralizing command execution in Excel, LibreOffice, and Google Sheets.
5. **Display Value Masking:** Findings exported or displayed in receipts follow the rule: `type + length bucket + masked form` with a default maximum reveal of 0 characters. Credentials (`PASSWORD`, `API_KEY`, `SECRET_TOKEN`) strictly reveal zero characters under all configurations.
6. **Session-Isolated Pseudonyms & IDs:** Identifiers and pseudonyms use UUID4 or HMAC-SHA256 with an ephemeral per-session 256-bit secret key (`secrets.token_bytes(32)`). Identical PII processed across different sessions yields completely different pseudonyms, preventing reverse rainbow table or dictionary guessing attacks.
7. **HTML / XSS Neutralization:** The UI rendering layer (`leakguard.ui.render.render_annotated`) applies `html.escape(..., quote=True)` to every segment (unmatched text, highlighted finding spans, entity types, and rationales), preventing script execution or markdown exploitation.
8. **Cache Isolation:** Caching mechanisms (such as `@st.cache_data` or `@functools.lru_cache`) never accept raw user input text as a cache key.
9. **Zero Outbound Telemetry / Network Calls:** All regex detectors, rule engines, and spaCy NER models operate 100% locally. No outbound HTTP/HTTPS requests or external telemetry calls exist anywhere in `src/leakguard/`.

---

## 2. Threat Model Matrix

The threat matrix below is derived from the LEAKGUARD security specification and references only components currently implemented and tested:

| Threat | Attack Vector / Scenario | Implemented Mitigation | Residual Risk | Backing Test |
|---|---|---|---|---|
| **Visitor pastes real secrets into demo** | User inputs production API keys, credentials, or personal PII. | Ephemeral processing, zero database persistence, zero raw text in logs, and automated redaction engine. | Sensitive text remains in process RAM for the duration of the scan request. | `test_planted_sentinel_never_logged_during_success_or_failure`, `test_pipeline_runtime_does_not_accumulate_state` |
| **Formula injection via export** | Attacker crafts text like `=cmd\|'/c calc'!A0` or `@SUM(...)` designed to execute code when exported CSV is opened in Excel. | `neutralize_csv_formula` prepends a single quote (`'`) to cells starting with `=`, `+`, `-`, `@`, `\t`, `\r`, `\n`. | Viewer application bugs or non-standard CSV consumers ignoring standard text escaping. | `test_formula_injection_neutralized_in_isolation`, `test_safe_export_findings_csv_neutralizes_injection`, `test_safe_export_receipt_csv_neutralizes_injection` |
| **XSS & Markdown Injection** | User crafts malicious inputs containing `<script>`, `<img onerror=...>`, or `[x](javascript:...)`. | `render_annotated` strictly calls `html.escape(quote=True)` on all text slices and finding attributes. | Vulnerabilities in external rendering hosts or browser rendering engines. | `test_render_annotated_escapes_xss_and_markdown`, `test_render_annotated_with_malicious_finding_attributes` |
| **Cross-user / cross-session correlation** | Attacker analyzes exported IDs or logs across sessions to correlate repeated occurrences of low-entropy PII (e.g. emails). | Session-isolated random IDs (UUID4) and HMAC-SHA256 pseudonyms using an ephemeral 256-bit random session key. | Attacker obtaining full host process memory dump. | `test_session_ids_unique_per_session`, `test_hmac_pseudonyms_differ_across_sessions`, `test_pseudonym_cannot_be_inverted_by_simple_hash_guessing` |
| **Denial of Service (ReDoS & Oversized Input)** | Attacker submits extremely large payloads (e.g. megabytes of text) or repetitive backtracking strings. | Strict input length cap (default 20,000 characters) enforced at entry; linear-time deterministic regexes. | Sub-quadratic processing delay for inputs near the 20,000-character cap. | `test_pipeline_enforces_input_cap_without_echoing_raw_text` |
| **Accidental secret leakage in logs** | Exception handlers or debug log statements print raw user input or unmasked credentials. | Pipeline logging records only lengths and durations; `SanitizedPrivacyFilter` scrubs planted sentinels and common secret patterns. | Structured logging of unhandled native C-extension crashes (e.g. segfaults in Python runtime). | `test_planted_sentinel_never_logged_during_success_or_failure` |
| **Data leakage via global caching** | Framework caching decorators (`@st.cache_data`) memoize function results using raw input as cache keys. | Static AST verification ensures no cache decorator accepts raw user input text. | Developer adding unreviewed caching in future UI updates. | `test_no_streamlit_cache_on_user_text` |
| **Data exfiltration via network** | Compromised dependency or accidental code initiates outbound HTTP requests to external servers. | Zero outbound network calls in `src/leakguard/`; static AST test bans `requests`, `urllib.request`, `http.client`, `socket`, `aiohttp`, `httpx`. | Malicious binary wheel injection bypassing AST static analysis. | `test_no_outbound_network_calls_in_src` |

---

## 3. Dependency Review

All direct project dependencies pinned in `requirements.txt` are audited and justified below:

| Package | Version | Classification | Purpose and Justification |
|---|---|---|---|
| `streamlit` | `1.66.0` | UI Presentation | Interactive web dashboard, real-time redaction demo, and audit receipt viewer. Does not handle storage or backend orchestration. |
| `pandas` | `3.0.6` | Data Structures | Structured tabular representation for evaluation benchmark reports and receipt logs. |
| `scikit-learn` | `1.9.1` | ML & Evaluation | Feature extraction and precision/recall evaluation metrics calculation. |
| `spacy` | `3.8.16` | Natural Language Processing | Lightweight NER engine for detecting `PERSON` entities (Candidate B from Phase 4 benchmark). Runs 100% locally with `en_core_web_sm`. |
| `cryptography` | `42.0.0+` | Cryptography & Security Lab | Industry-standard cryptographic primitives implementing authenticated AES-256-GCM encryption for the educational Security Lab. |

### Security Audit Status
- Tool: `pip-audit` version 2.10.0
- Command: `pip-audit -r requirements.txt`
- Result: **0 known vulnerabilities found.**
