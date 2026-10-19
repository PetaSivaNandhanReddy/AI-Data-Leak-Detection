"""Configuration module for LEAKGUARD.

Defines global limits, risk thresholds, and pipeline settings.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings and safety limits with environment variable overrides."""

    max_input_length: int = int(os.getenv("LEAKGUARD_MAX_INPUT_LENGTH", "20000"))
    max_reveal_chars: int = int(os.getenv("LEAKGUARD_MAX_REVEAL_CHARS", "0"))
    entropy_threshold: float = float(os.getenv("LEAKGUARD_ENTROPY_THRESHOLD", "4.5"))
    default_redaction_mode: str = os.getenv("LEAKGUARD_DEFAULT_REDACTION_MODE", "placeholder")
    log_level: str = os.getenv("LEAKGUARD_LOG_LEVEL", "INFO")
    session_expiry_seconds: int = int(os.getenv("LEAKGUARD_SESSION_EXPIRY_SECONDS", "3600"))


settings = Settings()
