"""Cryptographic primitives and AEAD wrappers for LEAKGUARD educational lab."""

from __future__ import annotations

from leakguard.crypto.aes_gcm import (
    AuthenticationFailedError,
    CryptographicError,
    EncryptedPayload,
    decrypt_message,
    encrypt_message,
    generate_ephemeral_key,
    generate_nonce,
    mask_key_preview,
    tamper_payload,
)

__all__ = [
    "AuthenticationFailedError",
    "CryptographicError",
    "EncryptedPayload",
    "decrypt_message",
    "encrypt_message",
    "generate_ephemeral_key",
    "generate_nonce",
    "mask_key_preview",
    "tamper_payload",
]
