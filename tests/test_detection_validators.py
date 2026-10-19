"""Unit tests for mathematical and structural entity validators."""

from leakguard.detection.validators import (
    validate_iban,
    validate_luhn,
    validate_pan,
    validate_verhoeff,
    validate_voter_id,
)


def test_validate_luhn_known_values():
    """Test Luhn checksum on known valid test cards and invalid variations."""
    # Known valid test card numbers (Visa test prefix 4000)
    valid_cards = [
        "4000 0012 3456 7899",
        "4000-0012-3456-7899",
        "4000001234567899",
        "4111 1111 1111 1111",
        "5105 1051 0510 5100",
    ]
    for card in valid_cards:
        assert validate_luhn(card) is True, f"Expected {card} to be valid"

    # Known invalid card numbers
    invalid_cards = [
        "4000 0012 3456 7890",  # Check digit corrupted
        "1234 5678 9012 3456",  # Arbitrary sequence
        "0000 0000 0000 0000",  # Repetitive trivial sequence
        "12345",  # Too short
        "abcd-efgh-ijkl-mnop",  # Non-numeric
    ]
    for card in invalid_cards:
        assert validate_luhn(card) is False, f"Expected {card} to be invalid"


def test_validate_verhoeff_known_values():
    """Test Verhoeff checksum algorithm on valid and invalid 12-digit Aadhaar values."""
    # Constructed valid Verhoeff 12-digit values in non-allocated 9999 test prefix
    valid_aadhaar = [
        "9999 4105 2815",
        "9999-4105-2815",
        "999941052815",
        "9999 0000 0016",
        "9999 1234 5678",
    ]
    for num in valid_aadhaar:
        assert validate_verhoeff(num) is True, f"Expected {num} to be valid Verhoeff"

    # Invalid Aadhaar values
    invalid_aadhaar = [
        "9999 4105 2810",  # Last digit corrupted
        "1234 5678 9012",  # Invalid check digit
        "0000 0000 0000",  # Trivial repetitive
        "999912345",  # Less than 12 digits
        "99991234567890",  # More than 12 digits
    ]
    for num in invalid_aadhaar:
        assert validate_verhoeff(num) is False, f"Expected {num} to be invalid Verhoeff"


def test_validate_iban_known_values():
    """Test ISO 7064 Mod-97-10 on valid and invalid IBAN strings."""
    # Known valid IBAN formats with check digits
    valid_ibans = [
        "GB82 WEST 1234 5698 7654 32",
        "GB82WEST12345698765432",
        "DE89 3704 0044 0532 0130 00",
        "FR14 2004 1010 0505 0001 3M02 606",
    ]
    for iban in valid_ibans:
        assert validate_iban(iban) is True, f"Expected {iban} to be valid IBAN"

    # Invalid IBAN formats
    invalid_ibans = [
        "GB00 WEST 1234 5698 7654 32",  # Check digits corrupted (00)
        "1234 5678 9012 3456 78",  # Missing country code
        "DE89",  # Too short
        "GB82 WEST 1234 5698 7654 39",  # Wrong check digits
    ]
    for iban in invalid_ibans:
        assert validate_iban(iban) is False, f"Expected {iban} to be invalid IBAN"


def test_validate_pan_known_values():
    """Test Indian PAN structural regex and 4th character taxpayer category."""
    # Valid PANs (4th character is P, C, H, F, A, T, B, L, J, G)
    valid_pans = [
        "ABCDE1234F",
        "BNZPS5432K",
        "XYZCA9876L",
        "AAATA1111B",
    ]
    for pan in valid_pans:
        assert validate_pan(pan) is True, f"Expected {pan} to be valid PAN"

    # Invalid PANs
    invalid_pans = [
        "ABCDE12345",  # Ends with digit instead of letter
        "ABCD12345F",  # Only 4 initial letters
        "ABCXE1234F",  # 4th letter 'X' is not a valid status code
        "ABCDEF1234",  # Too many letters
        "MODULE123A",  # 7 letters
    ]
    for pan in invalid_pans:
        assert validate_pan(pan) is False, f"Expected {pan} to be invalid PAN"


def test_validate_voter_id_known_values():
    """Test Indian Voter ID (EPIC) format (3 letters + 7 digits)."""
    valid_voter_ids = ["XYZ1234567", "ABC9876543", "IND0000001"]
    for vid in valid_voter_ids:
        assert validate_voter_id(vid) is True, f"Expected {vid} to be valid Voter ID"

    invalid_voter_ids = [
        "AB12345678",  # 2 letters + 8 digits
        "ABCD123456",  # 4 letters + 6 digits
        "XYZ123456",  # Only 6 digits
        "1234567890",  # All numeric
    ]
    for vid in invalid_voter_ids:
        assert validate_voter_id(vid) is False, f"Expected {vid} to be invalid Voter ID"


def test_severity_comparisons_and_schemas():
    """Test Severity ordering comparison operators and safe display calculations."""
    from leakguard.schemas import Finding, Severity, compute_safe_display_value

    assert Severity.LOW < Severity.MEDIUM < Severity.HIGH < Severity.CRITICAL
    assert Severity.CRITICAL > Severity.HIGH > Severity.MEDIUM > Severity.LOW
    assert Severity.HIGH >= Severity.HIGH
    assert Severity.LOW <= Severity.LOW
    assert (Severity.HIGH == "not_a_severity") is False
    assert Severity.HIGH > Severity.LOW
    assert Severity.LOW <= Severity.HIGH
    assert Severity.HIGH >= Severity.MEDIUM

    # compute_safe_display_value
    assert compute_safe_display_value("PASSWORD", "supersecret123") == "[PASSWORD:14 chars masked]"
    assert compute_safe_display_value("EMAIL", "ab") == "[EMAIL:masked]"
    assert "89" in compute_safe_display_value("CARD", "4000123456789")

    # Finding post-init validation
    finding = Finding(
        id="f1",
        entity_type="EMAIL",
        start=0,
        end=5,
        detector="regex",
        severity=Severity.LOW,
        display_value="*****",
        rationale="test",
    )
    assert finding.span == (0, 5)
    assert finding.length == 5
