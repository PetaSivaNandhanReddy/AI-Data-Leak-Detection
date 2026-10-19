# LEAKGUARD — Cryptographic Security Lab (AES-256-GCM)

## 1. Overview & Purpose

The **LEAKGUARD Cryptographic Security Lab** (`labs/security_lab.py`) provides an interactive educational demonstration of modern **Authenticated Encryption with Associated Data (AEAD)** using **AES-256-GCM** (NIST SP 800-38D).

The lab allows security engineers and analysts to inspect the inner mechanics of symmetric authenticated encryption, verify cryptographic envelope integrity, and observe how tampering and key mismatches are detected and rejected.

> [!WARNING]
> **Educational Sandbox Only:** The Security Lab is an educational demonstration tool and **NOT a production Key Management Service (KMS)**. All symmetric keys generated in the lab are ephemeral, stored exclusively in temporary session memory, and destroyed on session reset or browser close. Production deployments must integrate with hardened hardware or cloud KMS solutions (e.g., AWS KMS, HashiCorp Vault).

---

## 2. Legacy Prototype vs Rebuild Architecture

The legacy notebook prototype (`notebooks/legacy/crypogracy_legacy.ipynb`) contained an experimental cryptographic pipeline that combined **RSA-2048 + AES-256 (EAX mode)** via `pycryptodome`.

### Key Differences & Architectural Decisions

| Aspect | Legacy Notebook Prototype | LEAKGUARD Rebuild (Phase 8b) | Architectural Rationale |
| :--- | :--- | :--- | :--- |
| **Cipher Suite** | RSA-2048 + AES-EAX | **AES-256-GCM (NIST SP 800-38D)** | Standardized, hardware-accelerated AEAD primitive; eliminates asymmetric envelope complexity for local audit logging. |
| **Library** | `pycryptodome` | **`cryptography` (hazmat AEAD)** | Actively maintained, FIPS/NIST validated, memory-safe CFFI bindings with routine vulnerability auditing. |
| **RSA Status** | Static RSA PEM files on disk | **Intentionally Dropped** | Legacy RSA lacked key rotation, authenticated headers, and secure hardware storage. Replaced with clean AES-GCM envelope. |
| **Key Lifecycle** | Static file-based keys (`public.pem`) | **Ephemeral In-Memory Only** | 256-bit keys generated via OS CSPRNG (`os.urandom`); zero disk persistence; masked UI previews. |
| **Nonce Generation**| Ad-hoc byte concatenation | **96-Bit Random Nonce ($2^{96}$ Space)** | Fresh nonce generated strictly per encryption; stored with ciphertext; zero nonce reuse. |
| **Integrity / Tag** | EAX mode custom tag packing | **Standard 128-bit Authentication Tag** | Native AEAD tag automatically authenticated; tampering immediately raises `InvalidTag`. |
| **Associated Data** | Not supported | **Full AAD Support** | Binds cleartext protocol metadata (routing IDs, audit version) to tag without encryption. |

---

## 3. Cryptographic Invariants & Guarantees

1. **Key Confidentiality:**
   - Keys are 256-bit cryptographically secure random values generated in memory.
   - The full secret key is never logged, printed, or exposed in the UI. Previews use `mask_key_preview()` revealing only the first 4 and last 4 hex characters (`a1b2...c3d4`).
2. **Nonce Uniqueness:**
   - Each encryption operation generates a unique 96-bit (12-byte) nonce via `os.urandom(12)`.
   - Verified by test suite generating 10,000 consecutive encryptions with zero collisions.
3. **Tamper Evident Integrity:**
   - Flipping any single bit in the ciphertext or modifying cleartext Associated Data (AAD) causes immediate cryptographic authentication failure (`AuthenticationFailedError`).
   - Unauthenticated plaintext is never released to the caller upon verification failure.
4. **Zero Production Secret Input:**
   - Free-form secret entry is disabled; users select from safe synthetic demonstration samples to avoid accidental credential disclosure.

---

## 4. Cryptographic Envelope Data Contract

The `EncryptedPayload` dataclass defines the serialized wire representation:

```python
@dataclass(frozen=True)
class EncryptedPayload:
    nonce: bytes  # 12 bytes (96 bits)
    ciphertext: bytes  # Raw ciphertext + 16-byte authentication tag
    associated_data: bytes | None = None
```

### Serialization Format
- `nonce_hex`: 24-character hexadecimal representation of the 96-bit nonce.
- `tag_hex`: 32-character hexadecimal representation of the 128-bit authentication tag.
- `ciphertext_b64`: Standard Base64 encoding of the ciphertext body.
- `associated_data`: UTF-8 metadata string authenticated into the tag.

---

## 5. Verification & Testing

The security lab is validated by `tests/test_security_lab.py`:
- `test_aes_gcm_round_trip`: Verifies complete plaintext recovery with AAD.
- `test_aes_gcm_tampered_ciphertext_rejected`: Verifies single-bit ciphertext modification is rejected.
- `test_aes_gcm_tampered_aad_rejected`: Verifies AAD tampering is rejected.
- `test_aes_gcm_wrong_key_rejected`: Verifies wrong-key decryption failure.
- `test_aes_gcm_10000_unique_nonces`: Verifies collision resistance across 10,000 nonces.
- `test_no_secret_key_leakage_in_preview`: Verifies masking invariants.
- `test_security_lab_apptest_*`: Verifies UI rendering, educational banners, and interactive flows.
