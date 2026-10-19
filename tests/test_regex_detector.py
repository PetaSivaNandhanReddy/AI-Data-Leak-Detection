"""Unit tests for RegexDetector covering personal, financial, and identity entities."""

from leakguard.detection.regex_detector import RegexDetector
from leakguard.schemas import Severity


def test_regex_detector_email():
    """Verify email detection on regular and RFC documentation domains."""
    detector = RegexDetector()
    text = "Send reports to priya.sharma@internal-corp.in and docs to support@example.com."
    findings = detector.detect(text)

    emails = [f for f in findings if f.entity_type == "EMAIL"]
    assert len(emails) == 2

    corp_email = next(f for f in emails if "internal-corp.in" in text[f.start : f.end])
    assert corp_email.severity == Severity.MEDIUM
    assert text[corp_email.start : corp_email.end] == "priya.sharma@internal-corp.in"

    doc_email = next(f for f in emails if "example.com" in text[f.start : f.end])
    assert doc_email.severity == Severity.LOW
    assert "RFC documentation" in doc_email.rationale


def test_regex_detector_phone_and_date_guard():
    """Verify Indian and US phone numbers while ensuring dates and versions are not flagged."""
    detector = RegexDetector()
    text = (
        "Call +91 98765 43210 or 09845012345 regarding release v2.4.1 scheduled on 2026-10-18. "
        "US office: +1 555-019-2834."
    )
    findings = detector.detect(text)

    phones = [f for f in findings if f.entity_type == "PHONE"]
    assert len(phones) >= 2

    phone_texts = [text[f.start : f.end] for f in phones]
    # Date and version must NOT be in detected phone values
    assert not any("2026-10-18" in pt for pt in phone_texts)
    assert not any("v2.4.1" in pt for pt in phone_texts)


def test_regex_detector_card():
    """Verify Luhn-valid payment card numbers are detected and invalid decoys are ignored."""
    detector = RegexDetector()
    text = (
        "Charged test card 4000 0012 3456 7899 successfully. "
        "Decoy order number 1234 5678 9012 3456 was rejected."
    )
    findings = detector.detect(text)

    cards = [f for f in findings if f.entity_type == "CARD"]
    assert len(cards) == 1
    assert text[cards[0].start : cards[0].end] == "4000 0012 3456 7899"
    assert cards[0].severity == Severity.HIGH


def test_regex_detector_aadhaar():
    """Verify 12-digit Aadhaar numbers passing Verhoeff algorithm are detected."""
    detector = RegexDetector()
    text = "Customer KYC: Aadhaar 9999 4105 2815 verified. Decoy sequence 1234 5678 9012 discarded."
    findings = detector.detect(text)

    aadhaar = [f for f in findings if f.entity_type == "AADHAAR"]
    assert len(aadhaar) == 1
    assert text[aadhaar[0].start : aadhaar[0].end] == "9999 4105 2815"
    assert aadhaar[0].severity == Severity.HIGH


def test_regex_detector_pan_and_voter_id():
    """Verify Indian PAN and Voter ID formats."""
    detector = RegexDetector()
    text = "Taxpayer PAN: ABCDE1234F | Voter EPIC: XYZ1234567 | Invalid PAN: ABCDE12345"
    findings = detector.detect(text)

    pans = [f for f in findings if f.entity_type == "PAN"]
    assert len(pans) == 1
    assert text[pans[0].start : pans[0].end] == "ABCDE1234F"

    voters = [f for f in findings if f.entity_type == "VOTER_ID"]
    assert len(voters) == 1
    assert text[voters[0].start : voters[0].end] == "XYZ1234567"


def test_regex_detector_iban():
    """Verify IBAN detection with ISO 7064 Mod-97 check."""
    detector = RegexDetector()
    text = "Wire payout to GB82 WEST 1234 5698 7654 32 immediately."
    findings = detector.detect(text)

    ibans = [f for f in findings if f.entity_type == "IBAN"]
    assert len(ibans) == 1
    assert text[ibans[0].start : ibans[0].end] == "GB82 WEST 1234 5698 7654 32"


def test_regex_detector_account_number_with_context():
    """Verify bank account numbers are flagged only in context of banking keywords."""
    detector = RegexDetector()
    text_with_context = "Transfer funds to Account No: 918273645019 with IFSC SBIN0001234."
    text_without_context = "Tracking number is 918273645019 for the package delivery."

    findings_with = detector.detect(text_with_context)
    accounts = [f for f in findings_with if f.entity_type == "ACCOUNT_NUMBER"]
    assert len(accounts) == 1
    assert text_with_context[accounts[0].start : accounts[0].end] == "918273645019"

    findings_without = detector.detect(text_without_context)
    assert not any(f.entity_type == "ACCOUNT_NUMBER" for f in findings_without)
