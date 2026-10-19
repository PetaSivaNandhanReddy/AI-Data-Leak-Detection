"""Unit and AppTest tests for AES-256-GCM Cryptographic Security Lab.

Verifies:
- Round-trip encryption and decryption with Authenticated Associated Data (AAD)
- Tampered ciphertext rejection (bit flip in payload raises AuthenticationFailedError)
- Tampered AAD rejection
- Wrong-key decryption rejection
- 10,000 fresh encryptions produce 10,000 strictly unique nonces (no collision)
- Privacy masking: raw keys are never leaked in previews or logs
- Streamlit AppTest: page loads cleanly, disclaimer displayed, interactive flows
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from leakguard.crypto.aes_gcm import (
    AuthenticationFailedError,
    EncryptedPayload,
    decrypt_message,
    encrypt_message,
    generate_ephemeral_key,
    generate_nonce,
    mask_key_preview,
    tamper_payload,
)

ROOT_DIR = Path(__file__).resolve().parent.parent


def _get_path(rel_path: str) -> str:
    return str(ROOT_DIR / rel_path)


# ---------------------------------------------------------------------------
# Cryptographic Primitive Tests
# ---------------------------------------------------------------------------


def test_aes_gcm_round_trip() -> None:
    """Verify AES-GCM round trip encryption and decryption preserves plaintext."""
    key = generate_ephemeral_key()
    message = "Sensitive audit event [ID: 9942]: Zero leakage detected."
    aad = "context=audit_log;version=1.0"

    payload = encrypt_message(message, key, associated_data=aad)
    assert isinstance(payload, EncryptedPayload)
    assert len(payload.nonce) == 12
    assert len(payload.tag) == 16
    assert payload.ciphertext != message.encode("utf-8")

    decrypted = decrypt_message(payload, key)
    assert decrypted == message


def test_aes_gcm_tampered_ciphertext_rejected() -> None:
    """Verify modifying any bit in the ciphertext causes authentication tag failure."""
    key = generate_ephemeral_key()
    message = "Classified operational directive."
    payload = encrypt_message(message, key, associated_data="org=security")

    tampered = tamper_payload(payload, byte_index=0)
    assert tampered.ciphertext != payload.ciphertext

    with pytest.raises(AuthenticationFailedError, match="authentication failed"):
        decrypt_message(tampered, key)


def test_aes_gcm_tampered_aad_rejected() -> None:
    """Verify altering associated data causes authentication tag failure."""
    key = generate_ephemeral_key()
    message = "Classified operational directive."
    payload = encrypt_message(message, key, associated_data="org=security")

    # Tamper with AAD
    tampered_aad_payload = EncryptedPayload(
        nonce=payload.nonce,
        ciphertext=payload.ciphertext,
        associated_data=b"org=attacker",
    )

    with pytest.raises(AuthenticationFailedError, match="authentication failed"):
        decrypt_message(tampered_aad_payload, key)


def test_aes_gcm_wrong_key_rejected() -> None:
    """Verify attempting to decrypt with a different 256-bit key fails tag verification."""
    key_alice = generate_ephemeral_key()
    key_bob = generate_ephemeral_key()
    assert key_alice != key_bob

    payload = encrypt_message("Confidential memo.", key_alice)

    with pytest.raises(AuthenticationFailedError):
        decrypt_message(payload, key_bob)


def test_aes_gcm_10000_unique_nonces() -> None:
    """Verify 10,000 generated nonces are strictly unique (zero collision in 96-bit space)."""
    nonces = {generate_nonce() for _ in range(10_000)}
    assert len(nonces) == 10_000


def test_no_secret_key_leakage_in_preview() -> None:
    """Verify key mask helper never reveals full raw secret key material."""
    key = b"\x01" * 32
    preview = mask_key_preview(key)
    assert key.hex() not in preview
    assert "..." in preview
    assert "256-bit AES-GCM Ephemeral" in preview


def test_encrypted_payload_serialization_and_validation() -> None:
    """Verify EncryptedPayload dictionary serialization and size validation rules."""
    key = generate_ephemeral_key()
    payload = encrypt_message("Diagnostic telemetry payload", key, associated_data="tag=v1")

    # Serialization roundtrip
    p_dict = payload.to_dict()
    restored = EncryptedPayload.from_dict(p_dict)
    assert restored.nonce == payload.nonce
    assert restored.ciphertext == payload.ciphertext
    assert restored.associated_data == payload.associated_data
    assert decrypt_message(restored, key) == "Diagnostic telemetry payload"

    # Validation errors on invalid nonce / ciphertext sizes
    with pytest.raises(ValueError, match="Nonce must be exactly 12 bytes"):
        EncryptedPayload(nonce=b"short", ciphertext=b"\x00" * 20)

    with pytest.raises(ValueError, match="Ciphertext must include at least 16-byte"):
        EncryptedPayload(nonce=b"\x00" * 12, ciphertext=b"short")

    # Validation errors on invalid key size in encrypt/decrypt
    with pytest.raises(ValueError, match="key must be exactly 32 bytes"):
        encrypt_message("data", b"invalid_short_key")

    with pytest.raises(ValueError, match="key must be exactly 32 bytes"):
        decrypt_message(payload, b"invalid_short_key")


# ---------------------------------------------------------------------------
# Streamlit AppTest UI Tests
# ---------------------------------------------------------------------------


def test_security_lab_apptest_page_load() -> None:
    """Verify security lab view loads cleanly with disclaimer and masked key preview."""
    at = AppTest.from_file(_get_path("labs/security_lab.py")).run()
    assert len(at.exception) == 0

    all_titles = [t.value for t in at.title]
    assert any("AES-GCM Security Lab" in t for t in all_titles)

    # Educational Disclaimer Banner
    all_md = " ".join([m.value for m in at.markdown])
    assert "Educational Cryptography Lab Notice" in all_md
    assert "not a production key management service" in all_md
    assert "intentionally dropped" in all_md

    # Plaintext input area is disabled to prevent accepting user secrets
    assert len(at.text_area) > 0
    assert at.text_area[0].disabled is True


def test_security_lab_apptest_encryption_and_tamper_flow() -> None:
    """Verify interactive encryption, tampering, and decryption behavior in AppTest."""
    at = AppTest.from_file(_get_path("labs/security_lab.py")).run()
    assert len(at.exception) == 0

    # 1. Click Encrypt button
    encrypt_btn = next(b for b in at.button if "Encrypt with AES-256-GCM" in b.label)
    encrypt_btn.click().run()
    assert len(at.exception) == 0
    assert any("successfully encrypted" in s.value for s in at.success)

    # Envelope components rendered in code blocks
    assert len(at.code) >= 3

    # 2. Decrypt with valid key
    decrypt_btn = next(b for b in at.button if "Decrypt with Valid Key" in b.label)
    decrypt_btn.click().run()
    assert len(at.exception) == 0
    assert any("Decryption & Tag Verification Succeeded" in s.value for s in at.success)

    # 3. Tamper with ciphertext
    tamper_btn = next(b for b in at.button if "Tamper Ciphertext" in b.label)
    tamper_btn.click().run()
    assert len(at.exception) == 0
    assert any("This payload has been tampered with" in w.value for w in at.warning)

    # 4. Decrypt tampered payload -> must show authentication failed error
    decrypt_btn = next(b for b in at.button if "Decrypt with Valid Key" in b.label)
    decrypt_btn.click().run()
    assert len(at.exception) == 0
    assert any("Authentication Failed" in e.value for e in at.error)

    # 5. Wrong key button test
    wrong_key_btn = next(b for b in at.button if "Decrypt with Wrong Key" in b.label)
    wrong_key_btn.click().run()
    assert len(at.exception) == 0
    assert any("Tag Verification Failed (Expected)" in e.value for e in at.error)
