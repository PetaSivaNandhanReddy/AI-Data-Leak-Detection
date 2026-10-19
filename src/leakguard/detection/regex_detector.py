"""High-precision regex detector for standard personal, financial, and identity entities.

All regular expressions are linear-time (O(N)), avoiding catastrophic backtracking.
Checksum verification (Luhn, Verhoeff, Mod-97) is strictly integrated into detection
to eliminate false positives on non-sensitive numbers.
"""

from __future__ import annotations

import re

from leakguard.detection.validators import (
    validate_iban,
    validate_luhn,
    validate_pan,
    validate_verhoeff,
    validate_voter_id,
)
from leakguard.schemas import Finding, Severity, compute_safe_display_value

# RFC documentation domains that signify benign/test examples
_RFC_DOC_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "example.edu",
    "test.invalid",
    "invalid",
}

# --- Linear-time Regular Expressions ---
_EMAIL_RE = re.compile(r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b")

# Indian mobile: starting with 6-9, optional +91 or 0 prefix
_PHONE_IN_RE = re.compile(r"(?:\+91[\s\-]?)?(?:0)?[6-9]\d{4}[\s\-]?\d{5}\b")

# International/US phone formats
_PHONE_INTL_RE = re.compile(r"\+1[\s\-]\(?\d{3}\)?[\s\-]\d{3}[\s\-]\d{4}\b")

# Date guard to avoid false positive phone matches on dates (YYYY-MM-DD or DD-MM-YYYY)
_DATE_RE = re.compile(r"\b(?:\d{4}[\-\/]\d{1,2}[\-\/]\d{1,2}|\d{1,2}[\-\/]\d{1,2}[\-\/]\d{4})\b")

# Version string guard (e.g. v2.4.1)
_VERSION_RE = re.compile(r"\bv\d+\.\d+(?:\.\d+)?\b")

# Payment cards (13-19 digits, spaced or hyphenated in 4-digit blocks or raw)
_CARD_CANDIDATE_RE = re.compile(r"\b(?:\d{4}[\s\-]){3}\d{4}\b|\b\d{13,19}\b")

# Aadhaar: 12 digits, cannot start with 0 or 1, spaced as 4-4-4 or raw
_AADHAAR_CANDIDATE_RE = re.compile(r"\b[2-9]\d{3}[\s]\d{4}[\s]\d{4}\b|\b[2-9]\d{11}\b")

# PAN: 5 letters, 4 digits, 1 letter
_PAN_CANDIDATE_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")

# Voter ID (EPIC): 3 letters, 7 digits
_VOTER_ID_CANDIDATE_RE = re.compile(r"\b[A-Z]{3}\d{7}\b")

# IBAN candidate: 2 letters, 2 digits, up to 30 alphanumeric characters
_IBAN_CANDIDATE_RE = re.compile(
    r"\b[A-Z]{2}\d{2}(?:[\s]?[A-Z0-9]{4}){2,7}(?:[\s]?[A-Z0-9]{1,4})?\b"
)

# Domestic bank account context keywords
_BANK_CONTEXT_RE = re.compile(
    r"(?i)\b(?:account(?:\s*no\.?|\s*num(?:ber)?)?|a/c(?:\s*no\.?)?|acct|ifsc|neft|rtgs|imps|beneficiary|bank|payout)\b"
)
_ACCOUNT_NUM_CANDIDATE_RE = re.compile(r"\b\d{9,18}\b")


class RegexDetector:
    """Detects personal identifiers, cards, identity codes, and banking details via regex."""

    def __init__(self, name: str = "regex"):
        self.name = name

    def detect(self, text: str) -> list[Finding]:
        """Scan input text and return list of detected findings."""
        findings: list[Finding] = []

        # Find date and version exclusion spans
        excluded_spans: list[tuple[int, int]] = []
        for match in _DATE_RE.finditer(text):
            excluded_spans.append((match.start(), match.end()))
        for match in _VERSION_RE.finditer(text):
            excluded_spans.append((match.start(), match.end()))

        def is_excluded(start: int, end: int) -> bool:
            return any(s <= start and end <= e for s, e in excluded_spans)

        # 1. EMAIL
        for match in _EMAIL_RE.finditer(text):
            val = match.group(1)
            start, end = match.start(1), match.end(1)
            domain = val.split("@")[-1].lower()
            is_rfc_doc = domain in _RFC_DOC_DOMAINS
            severity = Severity.LOW if is_rfc_doc else Severity.MEDIUM
            rationale = (
                "RFC documentation-reserved email domain"
                if is_rfc_doc
                else "RFC 5322 electronic mail address"
            )
            findings.append(
                Finding(
                    id=f"re_email_{start}_{end}",
                    entity_type="EMAIL",
                    start=start,
                    end=end,
                    detector=self.name,
                    severity=severity,
                    display_value=compute_safe_display_value("EMAIL", val),
                    rationale=rationale,
                )
            )

        # 2. PAYMENT CARDS (Luhn verified)
        for match in _CARD_CANDIDATE_RE.finditer(text):
            val = match.group(0)
            start, end = match.start(), match.end()
            if is_excluded(start, end):
                continue
            if validate_luhn(val):
                findings.append(
                    Finding(
                        id=f"re_card_{start}_{end}",
                        entity_type="CARD",
                        start=start,
                        end=end,
                        detector=self.name,
                        severity=Severity.HIGH,
                        display_value=compute_safe_display_value("CARD", val),
                        rationale="Payment card primary account number passing Luhn checksum",
                    )
                )

        # 3. AADHAAR (Verhoeff verified)
        for match in _AADHAAR_CANDIDATE_RE.finditer(text):
            val = match.group(0)
            start, end = match.start(), match.end()
            if is_excluded(start, end):
                continue
            if validate_verhoeff(val):
                findings.append(
                    Finding(
                        id=f"re_aadhaar_{start}_{end}",
                        entity_type="AADHAAR",
                        start=start,
                        end=end,
                        detector=self.name,
                        severity=Severity.HIGH,
                        display_value=compute_safe_display_value("AADHAAR", val),
                        rationale=(
                            "12-digit Indian national identity number passing Verhoeff checksum"
                        ),
                    )
                )

        # 4. PAN (Structural regex & status code verified)
        for match in _PAN_CANDIDATE_RE.finditer(text):
            val = match.group(0)
            start, end = match.start(), match.end()
            if validate_pan(val):
                findings.append(
                    Finding(
                        id=f"re_pan_{start}_{end}",
                        entity_type="PAN",
                        start=start,
                        end=end,
                        detector=self.name,
                        severity=Severity.HIGH,
                        display_value=compute_safe_display_value("PAN", val),
                        rationale="Indian Permanent Account Number with valid taxpayer status code",
                    )
                )

        # 5. VOTER ID (EPIC)
        for match in _VOTER_ID_CANDIDATE_RE.finditer(text):
            val = match.group(0)
            start, end = match.start(), match.end()
            if validate_voter_id(val):
                findings.append(
                    Finding(
                        id=f"re_voter_{start}_{end}",
                        entity_type="VOTER_ID",
                        start=start,
                        end=end,
                        detector=self.name,
                        severity=Severity.MEDIUM,
                        display_value=compute_safe_display_value("VOTER_ID", val),
                        rationale="Indian Electoral Photo Identity Card (EPIC) format",
                    )
                )

        # 6. IBAN (ISO 7064 Mod-97-10 verified)
        for match in _IBAN_CANDIDATE_RE.finditer(text):
            val = match.group(0)
            start, end = match.start(), match.end()
            if validate_iban(val):
                findings.append(
                    Finding(
                        id=f"re_iban_{start}_{end}",
                        entity_type="IBAN",
                        start=start,
                        end=end,
                        detector=self.name,
                        severity=Severity.MEDIUM,
                        display_value=compute_safe_display_value("IBAN", val),
                        rationale=(
                            "International Bank Account Number passing ISO 7064 Mod-97-10 checksum"
                        ),
                    )
                )

        # 7. PHONE (Indian and International)
        # Check Indian phone numbers
        phone_matches: list[tuple[int, int, str]] = []
        for match in _PHONE_IN_RE.finditer(text):
            start, end = match.start(), match.end()
            if not is_excluded(start, end):
                phone_matches.append((start, end, match.group(0)))
        # Check international phone numbers
        for match in _PHONE_INTL_RE.finditer(text):
            start, end = match.start(), match.end()
            if not is_excluded(start, end):
                phone_matches.append((start, end, match.group(0)))

        for start, end, val in phone_matches:
            # Verify candidate doesn't collide with card or aadhaar
            if not any(f.start <= start and end <= f.end for f in findings):
                findings.append(
                    Finding(
                        id=f"re_phone_{start}_{end}",
                        entity_type="PHONE",
                        start=start,
                        end=end,
                        detector=self.name,
                        severity=Severity.MEDIUM,
                        display_value=compute_safe_display_value("PHONE", val),
                        rationale="Telephone / mobile number format",
                    )
                )

        # 8. ACCOUNT NUMBER (Requires adjacent banking context)
        # Find all context keyword positions
        context_spans = [m.span() for m in _BANK_CONTEXT_RE.finditer(text)]
        if context_spans:
            for match in _ACCOUNT_NUM_CANDIDATE_RE.finditer(text):
                start, end = match.start(), match.end()
                val = match.group(0)
                # Ensure this span isn't already a card, aadhaar, or phone
                if any(f.start <= start and end <= f.end for f in findings):
                    continue
                # Check proximity to banking context keywords (within 40 characters)
                has_context = any(
                    abs(start - ctx_end) <= 40 or abs(ctx_start - end) <= 40
                    for ctx_start, ctx_end in context_spans
                )
                if has_context:
                    findings.append(
                        Finding(
                            id=f"re_account_{start}_{end}",
                            entity_type="ACCOUNT_NUMBER",
                            start=start,
                            end=end,
                            detector=self.name,
                            severity=Severity.MEDIUM,
                            display_value=compute_safe_display_value("ACCOUNT_NUMBER", val),
                            rationale="Domestic bank account number in banking keyword context",
                        )
                    )

        # Sort findings by start offset
        findings.sort(key=lambda f: f.start)
        return findings
