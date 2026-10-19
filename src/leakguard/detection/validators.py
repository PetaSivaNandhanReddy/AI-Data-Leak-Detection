"""Pure mathematical and structural validators for high-assurance entity verification.

Includes:
- Luhn checksum algorithm for payment card numbers (ISO/IEC 7812)
- Verhoeff checksum algorithm for Indian Aadhaar numbers
- ISO 7064 Mod-97-10 check digits for International Bank Account Numbers (IBAN)
- Structural and status validation for Indian Permanent Account Numbers (PAN)
- Structural validation for Indian Voter ID (EPIC)
"""

from __future__ import annotations

import re

# --- Verhoeff Tables for Aadhaar Checksum ---
_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def validate_verhoeff(num_str: str) -> bool:
    """Validate that an Aadhaar number is 12 digits and satisfies the Verhoeff checksum.

    Separators (spaces and hyphens) are ignored. Rejects trivial repetitive sequences.
    """
    clean = re.sub(r"[\s\-]+", "", num_str)
    if len(clean) != 12 or not clean.isdigit():
        return False
    if len(set(clean)) == 1:
        return False  # All identical digits (e.g. 000000000000)

    c = 0
    for i, digit in enumerate(reversed(clean)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(digit)]]
    return c == 0


def validate_luhn(card_str: str) -> bool:
    """Validate a card number string (13-19 digits) via the Luhn checksum algorithm.

    Strips whitespace and hyphens before calculating.
    """
    clean = re.sub(r"[\s\-]+", "", card_str)
    if not clean.isdigit() or len(clean) < 13 or len(clean) > 19:
        return False
    if len(set(clean)) == 1:
        return False  # Trivial repetitive sequence

    digits = [int(c) for c in clean]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def validate_iban(iban_str: str) -> bool:
    """Validate an International Bank Account Number using ISO 7064 Mod-97-10."""
    clean = re.sub(r"\s+", "", iban_str.upper())
    if len(clean) < 15 or len(clean) > 34 or not clean.isalnum():
        return False
    # First 2 chars must be country alpha, next 2 must be digits
    if not clean[:2].isalpha() or not clean[2:4].isdigit():
        return False

    rearranged = clean[4:] + clean[:4]
    numeric_str = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    try:
        return int(numeric_str) % 97 == 1
    except ValueError:
        return False


_PAN_REGEX = re.compile(r"^[A-Z]{3}[PCHFATBLJGD][A-Z]\d{4}[A-Z]$")


def validate_pan(pan_str: str) -> bool:
    """Validate an Indian Permanent Account Number (PAN) structure and taxpayer category.

    Format: 5 letters, 4 digits, 1 letter. The 4th letter designates status:
    P - Person, C - Company, H - HUF, F - Firm, A - AOP, T - Trust,
    B - BOI, L - Local Authority, J - AJP, G - Government, D - Department/Defense.
    """
    clean = pan_str.strip().upper()
    return bool(_PAN_REGEX.match(clean))


_VOTER_ID_REGEX = re.compile(r"^[A-Z]{3}\d{7}$")


def validate_voter_id(voter_id_str: str) -> bool:
    """Validate an Indian Electoral Photo Identity Card (EPIC / Voter ID).

    Standard format: 3 uppercase letters followed by 7 numeric digits.
    """
    clean = voter_id_str.strip().upper()
    return bool(_VOTER_ID_REGEX.match(clean))
