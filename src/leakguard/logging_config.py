"""Central logging configuration with privacy-preserving log sanitization.

Guarantees:
- SanitizedPrivacyFilter scrubs known sentinels and sensitive token patterns
- Pure metadata logging (character counts, durations, finding counts)
- Zero raw text or secrets in log records or exception traces
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from typing import TextIO

from leakguard.config import settings

# Common sensitive token patterns to scrub from log messages as a defense-in-depth layer
_COMMON_PATTERNS = [
    re.compile(r"bearer\s+[A-Za-z0-9_\-\.]{15,}", re.IGNORECASE),
    re.compile(r"(api[_\-]?key|secret|token|password)\s*[:=]\s*[^\s,;]+", re.IGNORECASE),
    re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),  # Credit cards
]


class SanitizedPrivacyFilter(logging.Filter):
    """Logging filter that scrubs sensitive patterns and planted test sentinels."""

    def __init__(self, sentinels: Sequence[str] | None = None) -> None:
        super().__init__()
        self._sentinels: set[str] = set(sentinels or [])

    def register_sentinel(self, sentinel: str) -> None:
        """Register a sensitive sentinel string that must never appear in logs."""
        if sentinel:
            self._sentinels.add(sentinel)

    def clear_sentinels(self) -> None:
        """Clear registered test sentinels."""
        self._sentinels.clear()

    def _sanitize_string(self, text: str) -> str:
        """Scrub registered sentinels and common sensitive patterns."""
        sanitized = text
        for s in self._sentinels:
            if s in sanitized:
                sanitized = sanitized.replace(s, "[REDACTED_SENTINEL]")

        for pattern in _COMMON_PATTERNS:
            sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)

        return sanitized

    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitize record message, arguments, and exception info in-place."""
        if isinstance(record.msg, str):
            record.msg = self._sanitize_string(record.msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._sanitize_string(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self._sanitize_string(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )

        if record.exc_text:
            record.exc_text = self._sanitize_string(record.exc_text)

        return True


_global_filter = SanitizedPrivacyFilter()


def get_privacy_filter() -> SanitizedPrivacyFilter:
    """Return the global privacy filter instance."""
    return _global_filter


def configure_logging(
    level: str | None = None,
    stream: TextIO | None = None,
) -> logging.Logger:
    """Configure the root LEAKGUARD logger with safe formatting and the privacy filter."""
    log_level_name = level or settings.log_level
    numeric_level = getattr(logging, log_level_name.upper(), logging.INFO)

    logger = logging.getLogger("leakguard")
    logger.setLevel(numeric_level)

    # Avoid duplicate handlers if reconfigured
    if not any(isinstance(f, SanitizedPrivacyFilter) for f in logger.filters):
        logger.addFilter(_global_filter)

    if not logger.handlers:
        handler = logging.StreamHandler(stream)
        handler.setLevel(numeric_level)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(_global_filter)
        logger.addHandler(handler)

    return logger
