# LEAKGUARD System Limitations

This document provides transparent disclosure of known boundaries, design trade-offs, and technical limitations of the LEAKGUARD detection and redaction engine.

---

## 1. Detection and Generalization Boundaries

### Synthetic Benchmark Bounds
The detection pipeline and baseline metrics are derived from a 6,000-sample synthetic dataset (`data/processed/`) covering Indian PII, global personal data, financial identifiers, and technical credentials. While synthetic samples reflect realistic enterprise templates, real-world leaks often exhibit:
- Deliberate obfuscation (e.g. leetspeak, zero-width spaces, character interleaving).
- Non-standard formatting (e.g. spelling out card numbers in natural language words).
- Emerging API key formats not captured by current prefix-based regexes.

### Named Entity Recognition (`PERSON`)
Detection of individual names utilizes spaCy's `en_core_web_sm` model (Candidate B selected during Phase 4). Known limitations include:
- Reduced recall on single-token nicknames or isolated mononyms lacking surrounding grammatical context.
- Potential false negatives on non-Latin scripts or regional transliterated names not present in the small English model's training vocabulary.
- Pipeline throughput overhead: running spaCy adds ~15–30 ms per message compared to pure deterministic regex evaluation.

### Shannon Entropy Heuristics
Secret detection combines pattern anchors with Shannon entropy calculation (threshold: 4.5 bits/char). While effective at surfacing high-entropy credentials:
- Harmless random identifiers (e.g. Git commit SHAs, database UUIDs, content hashes) may trigger false-positive risk warnings if context is ambiguous.
- Low-entropy or common dictionary passwords (e.g. `password123!`) rely on keyword proximity rather than entropy calculations.

---

## 2. Architectural and Runtime Constraints

### In-Memory Lifetime
LEAKGUARD enforces a strict zero-retention policy: input text is never written to disk, databases, or local storage. However:
- Text resides in process virtual memory (RAM) during the scan execution cycle until garbage-collected by the Python runtime.
- Multi-tenant shared server deployments require standard containerization (e.g. Docker, Kubernetes namespaces) to prevent host-level memory inspection across tenants.

### Input Size Limits
To mitigate Regular Expression Denial of Service (ReDoS) and memory exhaustion attacks:
- Input text is capped at `LEAKGUARD_MAX_INPUT_LENGTH` (default: 20,000 characters).
- Inputs exceeding this cap are rejected with a safe `ValueError` specifying the character count, without echoing raw input text.
- Processing bulk documents or multimegabyte log files requires external chunking prior to calling LEAKGUARD.

### Cryptographic Scope
- LEAKGUARD is an audit, detection, and redaction engine; it is not a hardware security module (HSM) or enterprise key management system (KMS).
- Session pseudonyms generated via HMAC-SHA256 protect against rainbow table guessing attacks within individual user sessions, but are not intended as persistent irreversible cryptographic tokens.
- Cryptographic encryption demonstrations (implemented in Phase 8b Security Lab) are strictly scoped to educational demonstration of AES-GCM mechanics using ephemeral in-memory keys, and must not be used as a production key management service.
