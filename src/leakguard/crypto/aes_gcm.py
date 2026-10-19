"""AES-256-GCM authenticated symmetric encryption demo module for LEAKGUARD.

Implements NIST SP 800-38D standard AEAD using the `cryptography` library.
Features:
- 256-bit ephemeral key generation held strictly in memory.
- Unique 96-bit (12-byte) cryptographically secure random nonces per encryption.
- Authenticated Associated Data (AAD) support to bind context to ciphertext.
- Tamper-evident message authentication tag verification (128-bit / 16-byte).
- Strict secret masking: raw secret key values are never exposed or logged.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_SIZE_BITS = 256
NONCE_SIZE_BYTES = 12
TAG_SIZE_BYTES = 16


class CryptographicError(Exception):
    """Base exception for cryptographic errors."""


class AuthenticationFailedError(CryptographicError):
    """Raised when authentication tag verification fails (ciphertext or AAD tampered)."""


@dataclass(frozen=True)
class EncryptedPayload:
    """Immutable container for AES-GCM ciphertext, nonce, and associated data.

    In the cryptography library implementation of AES-GCM, the 16-byte
    authentication tag is appended to the end of the ciphertext.
    """

    nonce: bytes
    ciphertext: bytes
    associated_data: bytes | None = None

    def __post_init__(self) -> None:
        if len(self.nonce) != NONCE_SIZE_BYTES:
            raise ValueError(
                f"Nonce must be exactly {NONCE_SIZE_BYTES} bytes (received {len(self.nonce)})"
            )
        if len(self.ciphertext) < TAG_SIZE_BYTES:
            raise ValueError(
                f"Ciphertext must include at least {TAG_SIZE_BYTES}-byte authentication tag"
            )

    @property
    def tag(self) -> bytes:
        """The 16-byte authentication tag appended by AES-GCM."""
        return self.ciphertext[-TAG_SIZE_BYTES:]

    @property
    def raw_ciphertext(self) -> bytes:
        """Ciphertext payload excluding the trailing authentication tag."""
        return self.ciphertext[:-TAG_SIZE_BYTES]

    def to_dict(self) -> dict[str, str | None]:
        """Serialize payload components to base64 strings for inspection or export."""
        return {
            "nonce_hex": self.nonce.hex(),
            "tag_hex": self.tag.hex(),
            "ciphertext_b64": base64.b64encode(self.raw_ciphertext).decode("ascii"),
            "full_payload_b64": base64.b64encode(self.ciphertext).decode("ascii"),
            "associated_data": (
                self.associated_data.decode("utf-8", errors="replace")
                if self.associated_data
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EncryptedPayload:
        """Construct an EncryptedPayload from serialized dictionary."""
        nonce = bytes.fromhex(data["nonce_hex"])
        full_payload = base64.b64decode(data["full_payload_b64"])
        aad_raw = data.get("associated_data")
        aad_bytes = aad_raw.encode("utf-8") if aad_raw else None
        return cls(nonce=nonce, ciphertext=full_payload, associated_data=aad_bytes)


def generate_ephemeral_key() -> bytes:
    """Generate a fresh 256-bit cryptographically secure random symmetric key.

    Held strictly in memory and never written to disk or logged.
    """
    return AESGCM.generate_key(bit_length=KEY_SIZE_BITS)


def generate_nonce() -> bytes:
    """Generate a fresh 96-bit (12-byte) cryptographically secure random nonce.

    Must NEVER be reused with the same key.
    """
    return os.urandom(NONCE_SIZE_BYTES)


def mask_key_preview(key: bytes) -> str:
    """Return a privacy-safe masked preview of a cryptographic key.

    Reveals at most the first and last 4 hex characters to prevent secret leakage.
    Example: 'a1b2...c3d4 (256-bit AES-GCM Ephemeral)'
    """
    hex_key = key.hex()
    return f"{hex_key[:4]}...{hex_key[-4:]} (256-bit AES-GCM Ephemeral)"


def encrypt_message(
    plaintext: str | bytes,
    key: bytes,
    associated_data: str | bytes | None = None,
) -> EncryptedPayload:
    """Encrypt a plaintext message using AES-256-GCM with a fresh random nonce.

    Args:
        plaintext: The message string or bytes to encrypt.
        key: 32-byte (256-bit) AES key.
        associated_data: Optional authenticated metadata (AAD) bound to the ciphertext.

    Returns:
        EncryptedPayload containing the fresh nonce, ciphertext with appended auth tag,
        and associated data.
    """
    if len(key) != 32:
        raise ValueError(f"AES-256 key must be exactly 32 bytes (received {len(key)})")

    data_bytes = plaintext.encode("utf-8") if isinstance(plaintext, str) else plaintext
    aad_bytes = (
        associated_data.encode("utf-8")
        if isinstance(associated_data, str)
        else (associated_data or b"")
    )

    nonce = generate_nonce()
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, data_bytes, aad_bytes)

    return EncryptedPayload(
        nonce=nonce,
        ciphertext=ciphertext_with_tag,
        associated_data=aad_bytes if associated_data else None,
    )


def decrypt_message(payload: EncryptedPayload, key: bytes) -> str:
    """Decrypt an EncryptedPayload using AES-256-GCM and verify its authentication tag.

    Args:
        payload: EncryptedPayload with nonce, ciphertext, tag, and optional associated data.
        key: 32-byte (256-bit) AES key.

    Returns:
        Decrypted UTF-8 plaintext string.

    Raises:
        AuthenticationFailedError: If tag verification fails due to ciphertext tampering,
            AAD tampering, or incorrect cryptographic key.
        ValueError: If key size is invalid.
    """
    if len(key) != 32:
        raise ValueError(f"AES-256 key must be exactly 32 bytes (received {len(key)})")

    aad_bytes = payload.associated_data or b""
    aesgcm = AESGCM(key)

    try:
        decrypted_bytes = aesgcm.decrypt(payload.nonce, payload.ciphertext, aad_bytes)
        return decrypted_bytes.decode("utf-8")
    except InvalidTag as exc:
        raise AuthenticationFailedError(
            "Cryptographic authentication failed: ciphertext or associated data has been "
            "tampered with, or an incorrect decryption key was provided."
        ) from exc


def tamper_payload(payload: EncryptedPayload, byte_index: int = 0) -> EncryptedPayload:
    """Create a tampered copy of an EncryptedPayload by flipping a bit in the ciphertext.

    Used strictly for educational demonstrations of AES-GCM integrity protection.
    """
    mutable = bytearray(payload.ciphertext)
    target_idx = byte_index % len(mutable)
    mutable[target_idx] ^= 0x01  # Flip 1 bit

    return EncryptedPayload(
        nonce=payload.nonce,
        ciphertext=bytes(mutable),
        associated_data=payload.associated_data,
    )
