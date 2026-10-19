"""Session security, random identifier, and keyed pseudonymization utilities.

Guarantees:
- Ephemeral random session keys (secrets.token_bytes)
- Per-session UUID4 identifiers
- Keyed HMAC-SHA256 pseudonyms ensuring identical PII in different sessions
  yields distinct, uncorrelatable pseudonyms
- Protects low-entropy PII from reverse rainbow table / dictionary guessing attacks
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid


class SessionSecurity:
    """Session security manager providing isolated identifiers and HMAC pseudonyms."""

    def __init__(
        self,
        session_id: str | None = None,
        session_key: bytes | None = None,
    ) -> None:
        self.session_id: str = session_id or str(uuid.uuid4())
        self._session_key: bytes = session_key or secrets.token_bytes(32)

    def generate_random_id(self, prefix: str = "id") -> str:
        """Generate an unguessable UUID4-based identifier."""
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def generate_pseudonym(self, value: str, prefix: str = "psn", length: int = 12) -> str:
        """Generate a session-keyed HMAC-SHA256 pseudonym for a sensitive value.

        Because the HMAC key is ephemeral and unique per session:
        - Identical values across different sessions produce distinct pseudonyms.
        - Guessing attacks (e.g. hashing common emails or names) cannot reverse the pseudonym.
        """
        mac = hmac.new(self._session_key, value.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{prefix}_{mac[:length]}"

    def verify_pseudonym(
        self, value: str, pseudonym: str, prefix: str = "psn", length: int = 12
    ) -> bool:
        """Verify whether a value matches a given pseudonym within this session."""
        expected = self.generate_pseudonym(value, prefix=prefix, length=length)
        return hmac.compare_digest(expected, pseudonym)


def generate_session_id() -> str:
    """Generate a random UUID4 session identifier."""
    return str(uuid.uuid4())
