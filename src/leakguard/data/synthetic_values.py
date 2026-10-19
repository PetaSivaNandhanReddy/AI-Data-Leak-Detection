"""Deterministic generation of realistic but non-functional synthetic identifiers and credentials.

Provides mathematically structured test values for:
- Payment cards (Luhn checksum algorithm, test ranges)
- Aadhaar (Verhoeff checksum algorithm, unallocated test prefixes)
- Indian PAN (Income Tax Dept format regex)
- Indian Voter ID (EPIC format)
- IBAN (ISO 7064 Mod-97-10 check digits)
- Domestic Bank Accounts & IFSC
- Cloud API keys and tokens (AWS, GitHub, Slack, Bearer JWT)
- Realistic passwords and credential strings
- Decoys, invalid checksums, and documentation placeholders
"""

from __future__ import annotations

import random

from faker import Faker

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

_VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def compute_verhoeff(num_str: str) -> int:
    """Compute Verhoeff check digit for a string of digits."""
    c = 0
    for i, digit in enumerate(reversed(num_str)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[(i + 1) % 8][int(digit)]]
    return _VERHOEFF_INV[c]


def validate_verhoeff(num_str: str) -> bool:
    """Validate that the full numeric string satisfies the Verhoeff algorithm."""
    clean = "".join(ch for ch in num_str if ch.isdigit())
    if not clean:
        return False
    c = 0
    for i, digit in enumerate(reversed(clean)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(digit)]]
    return c == 0


# --- Luhn Algorithm for Payment Cards ---
def compute_luhn(prefix_digits: str) -> int:
    """Compute check digit for prefix so that complete string satisfies Luhn."""
    total = 0
    for i, ch in enumerate(reversed(prefix_digits)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - (total % 10)) % 10


def validate_luhn(card_str: str) -> bool:
    """Validate that the card number satisfies the Luhn algorithm."""
    digits = [int(c) for c in card_str if c.isdigit()]
    if len(digits) < 13:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# --- IBAN Helpers ---
def compute_iban_check(country: str, bban: str) -> str:
    """Compute 2 check digits for country code and BBAN per ISO 7064 Mod 97-10."""
    temp = bban + country + "00"
    numeric = "".join(str(ord(c) - 55) if c.isalpha() else c for c in temp)
    rem = int(numeric) % 97
    check_val = 98 - rem
    return f"{check_val:02d}"


def validate_iban(iban_str: str) -> bool:
    """Validate an IBAN string via ISO 7064 Mod-97-10."""
    clean = "".join(c.upper() for c in iban_str if c.isalnum())
    if len(clean) < 15 or len(clean) > 34:
        return False
    rearranged = clean[4:] + clean[:4]
    numeric = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    return int(numeric) % 97 == 1


class SyntheticValueFactory:
    """Deterministic generator for synthetic entities, decoys, and placeholders."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
        # Seed both en_IN and en_US locales for diverse Indian & international data
        Faker.seed(seed)
        self.fake_in = Faker("en_IN")
        self.fake_us = Faker("en_US")
        self.fake_in.seed_instance(seed)
        self.fake_us.seed_instance(seed + 1)

    def name(self) -> str:
        """Generate human name (mixed Indian and Western)."""
        if self.rng.random() < 0.65:
            return f"{self.fake_in.first_name()} {self.fake_in.last_name()}"
        return f"{self.fake_us.first_name()} {self.fake_us.last_name()}"

    def email(self) -> str:
        """Generate realistic corporate/personal email on non-existent test domain."""
        user = f"{self.fake_in.first_name().lower()}.{self.fake_in.last_name().lower()}"
        domains = [
            "corp-cloud-internal.in",
            "fintech-sys-dev.co.in",
            "secure-node-gateway.net",
            "apex-analytics-lab.io",
            "devops-mail-relay.org",
        ]
        return f"{user}@{self.rng.choice(domains)}"

    def decoy_email(self) -> str:
        """RFC documentation-reserved benign email."""
        local = self.rng.choice(["support", "info", "admin", "contact", "developer", "sample.user"])
        rfc_domain = self.rng.choice(["example.com", "example.org", "example.net", "test.invalid"])
        return f"{local}@{rfc_domain}"

    def phone(self) -> str:
        """Generate phone number with Indian mobile or international format."""
        if self.rng.random() < 0.70:
            prefix = self.rng.choice(["9", "8", "7", "6"])
            rest = "".join(str(self.rng.randint(0, 9)) for _ in range(9))
            num = prefix + rest
            fmt = self.rng.choice(
                [
                    f"+91 {num[:5]} {num[5:]}",
                    f"+91-{num[:5]}-{num[5:]}",
                    f"0{num}",
                    f"+91{num}",
                ]
            )
            return fmt
        area = self.rng.randint(201, 899)
        exchange = self.rng.randint(200, 899)
        subscriber = self.rng.randint(1000, 9999)
        return f"+1-{area}-{exchange}-{subscriber}"

    def card_number(self) -> str:
        """Generate a 16-digit card number with valid Luhn checksum in test ranges."""
        # Non-allocated test BIN prefixes (4000 00.. or 5105 10..)
        bin_prefix = self.rng.choice(["400000", "510510", "411111", "601100"])
        middle = "".join(str(self.rng.randint(0, 9)) for _ in range(9))
        prefix = bin_prefix + middle
        chk = compute_luhn(prefix)
        raw = prefix + str(chk)
        if self.rng.random() < 0.5:
            return f"{raw[:4]} {raw[4:8]} {raw[8:12]} {raw[12:]}"
        return f"{raw[:4]}-{raw[4:8]}-{raw[8:12]}-{raw[12:]}"

    def decoy_card_number(self) -> str:
        """16-digit number that deliberately fails Luhn (order ID or decoy)."""
        raw = "".join(str(self.rng.randint(0, 9)) for _ in range(16))
        # Ensure it fails Luhn
        if validate_luhn(raw):
            last_digit = (int(raw[-1]) + 1) % 10
            raw = raw[:-1] + str(last_digit)
        if self.rng.random() < 0.5:
            return f"{raw[:4]} {raw[4:8]} {raw[8:12]} {raw[12:]}"
        return f"{raw[:4]}-{raw[4:8]}-{raw[8:12]}-{raw[12:]}"

    def aadhaar(self) -> str:
        """Generate a 12-digit Aadhaar number with valid Verhoeff checksum in 9999 test prefix."""
        # Prefix 9999 is reserved and not issued to real residents
        prefix = "9999" + "".join(str(self.rng.randint(0, 9)) for _ in range(7))
        chk = compute_verhoeff(prefix)
        raw = prefix + str(chk)
        if self.rng.random() < 0.6:
            return f"{raw[:4]} {raw[4:8]} {raw[8:]}"
        return raw

    def decoy_aadhaar(self) -> str:
        """12-digit number that fails Verhoeff (e.g. transaction sequence)."""
        raw = "".join(str(self.rng.randint(1, 9)) for _ in range(12))
        if validate_verhoeff(raw):
            last_digit = (int(raw[-1]) + 1) % 10
            raw = raw[:-1] + str(last_digit)
        if self.rng.random() < 0.5:
            return f"{raw[:4]} {raw[4:8]} {raw[8:]}"
        return raw

    def pan(self) -> str:
        """Generate a valid Indian PAN (5 letters, 4 digits, 1 letter)."""
        first3 = "".join(self.rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(3))
        fourth = self.rng.choice(["P", "C", "H", "F", "A", "T", "B"])
        fifth = self.rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        digits = "".join(str(self.rng.randint(0, 9)) for _ in range(4))
        check_letter = self.rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        return f"{first3}{fourth}{fifth}{digits}{check_letter}"

    def decoy_pan(self) -> str:
        """Decoy string resembling PAN but with invalid structure."""
        first4 = "".join(self.rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(4))
        digits = "".join(str(self.rng.randint(0, 9)) for _ in range(5))
        letter = self.rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        return f"{first4}{digits}{letter}"

    def voter_id(self) -> str:
        """Generate Indian Voter ID / EPIC code (3 uppercase letters + 7 digits)."""
        letters = "".join(self.rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(3))
        digits = "".join(str(self.rng.randint(0, 9)) for _ in range(7))
        return f"{letters}{digits}"

    def iban(self) -> str:
        """Generate valid IBAN with correct ISO 7064 Mod-97 check digits."""
        country = self.rng.choice(["GB", "DE", "FR", "NL"])
        if country == "GB":
            bban = "WEST" + "".join(str(self.rng.randint(0, 9)) for _ in range(14))
        elif country == "DE":
            bban = "".join(str(self.rng.randint(0, 9)) for _ in range(18))
        elif country == "FR":
            bban = "".join(str(self.rng.randint(0, 9)) for _ in range(23))
        else:
            bban = "ABNA" + "".join(str(self.rng.randint(0, 9)) for _ in range(10))
        chk = compute_iban_check(country, bban)
        full = f"{country}{chk}{bban}"
        # Format in 4-character blocks
        return " ".join(full[i : i + 4] for i in range(0, len(full), 4))

    def account_number(self) -> str:
        """Generate domestic bank account number (11-14 digits)."""
        length = self.rng.randint(11, 14)
        first = self.rng.choice(["1", "2", "3", "5", "9"])
        rest = "".join(str(self.rng.randint(0, 9)) for _ in range(length - 1))
        return first + rest

    def ifsc(self) -> str:
        """Generate Indian Financial System Code."""
        bank = self.rng.choice(["SBIN", "HDFC", "ICIC", "PUNB", "BARB", "UTIB"])
        branch = "".join(str(self.rng.randint(0, 9)) for _ in range(6))
        return f"{bank}0{branch}"

    def password(self) -> str:
        """Generate high-entropy password for credentials."""
        words = ["P@ssw0rd", "AdminKey", "SecureRoot", "StagingPass", "CloudNode", "SecretProd"]
        syms = ["!", "@", "#", "$", "%", "&", "*"]
        num = self.rng.randint(100, 9999)
        return f"{self.rng.choice(words)}{self.rng.choice(syms)}{num}"

    def api_key(self) -> str:
        """Generate fake cloud API keys with official vendor prefixes."""
        key_type = self.rng.choice(["aws", "github", "slack", "bearer"])
        if key_type == "aws":
            # Clearly marked test key
            chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            token = "".join(self.rng.choice(chars) for _ in range(16))
            return f"AKIA{token}"
        if key_type == "github":
            chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            token = "".join(self.rng.choice(chars) for _ in range(36))
            return f"ghp_test_{token[:31]}"
        if key_type == "slack":
            t1 = "".join(str(self.rng.randint(0, 9)) for _ in range(12))
            t2 = "".join(str(self.rng.randint(0, 9)) for _ in range(12))
            chars = "abcdefghijklmnopqrstuvwxyz0123456789"
            t3 = "".join(self.rng.choice(chars) for _ in range(24))
            return f"xoxb-{t1}-{t2}-{t3}"
        # Bearer token
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        jwt_head = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        jwt_body = "".join(self.rng.choice(chars) for _ in range(24))
        jwt_sig = "".join(self.rng.choice(chars) for _ in range(16))
        return f"Bearer {jwt_head}.{jwt_body}.{jwt_sig}"

    def decoy_placeholder(self) -> str:
        """Safe placeholder that indicates no real leak."""
        placeholders = [
            "<INSERT_API_KEY_HERE>",
            "YOUR_SECRET_TOKEN",
            "${ENV_DATABASE_PASSWORD}",
            "<REDACTED_BY_POLICY>",
            "TODO_PASTE_KEY",
            "PLACEHOLDER_TOKEN_xyz",
        ]
        return self.rng.choice(placeholders)

    def decoy_order_id(self) -> str:
        """Tracking or order identifier."""
        prefix = self.rng.choice(["ORD", "TRK", "TXN", "INV", "PKG"])
        digits = "".join(str(self.rng.randint(0, 9)) for _ in range(10))
        return f"{prefix}-{digits}"

    def decoy_version(self) -> str:
        """Software version string."""
        return f"v{self.rng.randint(1, 14)}.{self.rng.randint(0, 30)}.{self.rng.randint(0, 9)}"
