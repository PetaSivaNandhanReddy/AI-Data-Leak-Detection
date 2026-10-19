"""Detector for credentials, provider API tokens, database connection strings, and private keys.

Supports:
- Canonical provider token formats (AWS, GitHub, Slack, JWT/Bearer)
- Assignment-context detection (e.g. password=..., api_key: ...)
- Shannon entropy calculation as a weak supporting signal (documented as noisy)
- Safe handling of documentation placeholders and environment variable references
"""

from __future__ import annotations

import math
import re
from collections import Counter

from leakguard.schemas import Finding, Severity, compute_safe_display_value

# Known benign placeholder prefixes and markers
_PLACEHOLDER_MARKERS = (
    "<",
    ">",
    "TODO",
    "YOUR_",
    "INSERT_",
    "ENTER_",
    "${",
    "%",
    "PLACEHOLDER",
    "REDACTED",
    "DUMMY",
    "EXAMPLE",
)


def shannon_entropy(text: str) -> float:
    """Compute Shannon entropy in bits per symbol.

    NOTE: Documented as a weak supporting signal. High entropy alone does not prove
    a string is a leak, and low entropy secrets (e.g. simple passwords) exist.
    """
    if not text:
        return 0.0
    counts = Counter(text)
    length = len(text)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


# --- Provider Token Patterns (Linear-Time) ---
_AWS_KEY_RE = re.compile(r"\b(AKIA[0-9A-Z]{16})\b")
_GITHUB_PAT_RE = re.compile(r"\b(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})\b")
_SLACK_TOKEN_RE = re.compile(r"\b(xox[baprs]-[0-9a-zA-Z-]{10,64})\b")
_BEARER_JWT_RE = re.compile(r"\bBearer\s+(eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)\b")
_PEM_PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")

# Connection strings: postgres://user:password@host...
_CONN_STRING_RE = re.compile(
    r"\b(?:postgres|postgresql|mysql|mongodb|redis|amqp)://[a-zA-Z0-9_.-]+:([^\s\"';]+)@(?:[a-zA-Z0-9_.-]+(?::\d+)?(?:/[^\s\"';]*)?)"
)

# Assignment context: password = "...", api_key: "..."
_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|db_pass|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\s*[:=]\s*[\"']?([^\s\"';,\n]{4,})[\"']?"
)


class SecretDetector:
    """Specialized detector for active API keys, private keys, connection strings, and passwords."""

    def __init__(self, name: str = "secret", entropy_threshold: float = 3.5):
        self.name = name
        self.entropy_threshold = entropy_threshold

    def is_placeholder(self, value: str) -> bool:
        """Check if value is an intentional template placeholder or variable reference."""
        upper = value.upper().strip()
        return any(marker in upper for marker in _PLACEHOLDER_MARKERS)

    def detect(self, text: str) -> list[Finding]:
        """Scan text and return detected credential findings."""
        findings: list[Finding] = []

        # 1. AWS Access Keys
        for match in _AWS_KEY_RE.finditer(text):
            val = match.group(1)
            start, end = match.start(1), match.end(1)
            is_mock = self.is_placeholder(val) or "EXAMPLE" in val
            findings.append(
                Finding(
                    id=f"sec_aws_{start}_{end}",
                    entity_type="API_KEY",
                    start=start,
                    end=end,
                    detector=self.name,
                    severity=Severity.LOW if is_mock else Severity.CRITICAL,
                    display_value=compute_safe_display_value("API_KEY", val),
                    rationale="AWS IAM Access Key ID format (AKIA)",
                )
            )

        # 2. GitHub Personal Access Tokens
        for match in _GITHUB_PAT_RE.finditer(text):
            val = match.group(1)
            start, end = match.start(1), match.end(1)
            is_mock = self.is_placeholder(val) or "test" in val.lower()
            findings.append(
                Finding(
                    id=f"sec_gh_{start}_{end}",
                    entity_type="API_KEY",
                    start=start,
                    end=end,
                    detector=self.name,
                    severity=Severity.LOW if is_mock else Severity.CRITICAL,
                    display_value=compute_safe_display_value("API_KEY", val),
                    rationale="GitHub Personal Access Token prefix (ghp_/github_pat_)",
                )
            )

        # 3. Slack Tokens
        for match in _SLACK_TOKEN_RE.finditer(text):
            val = match.group(1)
            start, end = match.start(1), match.end(1)
            findings.append(
                Finding(
                    id=f"sec_slack_{start}_{end}",
                    entity_type="API_KEY",
                    start=start,
                    end=end,
                    detector=self.name,
                    severity=Severity.CRITICAL,
                    display_value=compute_safe_display_value("API_KEY", val),
                    rationale="Slack API token prefix (xox*)",
                )
            )

        # 4. Bearer JWT
        for match in _BEARER_JWT_RE.finditer(text):
            val = match.group(1)
            start, end = match.start(1), match.end(1)
            findings.append(
                Finding(
                    id=f"sec_jwt_{start}_{end}",
                    entity_type="SECRET_TOKEN",
                    start=start,
                    end=end,
                    detector=self.name,
                    severity=Severity.CRITICAL,
                    display_value=compute_safe_display_value("SECRET_TOKEN", val),
                    rationale="Bearer JSON Web Token (JWT) header and payload",
                )
            )

        # 5. Private Key Headers
        for match in _PEM_PRIVATE_KEY_RE.finditer(text):
            val = match.group(0)
            start, end = match.start(), match.end()
            findings.append(
                Finding(
                    id=f"sec_pkey_{start}_{end}",
                    entity_type="SECRET_TOKEN",
                    start=start,
                    end=end,
                    detector=self.name,
                    severity=Severity.CRITICAL,
                    display_value=compute_safe_display_value("SECRET_TOKEN", val),
                    rationale="Cryptographic private key header block",
                )
            )

        # 6. Database Connection String with Credentials
        for match in _CONN_STRING_RE.finditer(text):
            password_val = match.group(1)
            start, end = match.start(1), match.end(1)
            if not self.is_placeholder(password_val):
                findings.append(
                    Finding(
                        id=f"sec_dbpass_{start}_{end}",
                        entity_type="PASSWORD",
                        start=start,
                        end=end,
                        detector=self.name,
                        severity=Severity.CRITICAL,
                        display_value=compute_safe_display_value("PASSWORD", password_val),
                        rationale="Plaintext database password embedded in URI connection string",
                    )
                )

        # 7. Assignment Context (password=..., api_key=...)
        for match in _ASSIGNMENT_RE.finditer(text):
            key_name = match.group(1).lower()
            val = match.group(2)
            start, end = match.start(2), match.end(2)

            # Avoid re-detecting spans already captured by provider token patterns
            if any(f.start <= start and end <= f.end for f in findings):
                continue

            if self.is_placeholder(val):
                continue

            ent_type = "PASSWORD" if "pass" in key_name or "pwd" in key_name else "API_KEY"
            ent_entropy = shannon_entropy(val)
            entropy_note = (
                f"; elevated entropy (H={ent_entropy:.2f})"
                if ent_entropy >= self.entropy_threshold
                else ""
            )

            findings.append(
                Finding(
                    id=f"sec_assign_{start}_{end}",
                    entity_type=ent_type,
                    start=start,
                    end=end,
                    detector=self.name,
                    severity=Severity.CRITICAL if ent_type == "PASSWORD" else Severity.HIGH,
                    display_value=compute_safe_display_value(ent_type, val),
                    rationale=f"Credential assigned to variable '{key_name}'{entropy_note}",
                )
            )

        findings.sort(key=lambda f: f.start)
        return findings
