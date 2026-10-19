"""Detection modules for LEAKGUARD."""

from leakguard.detection.aggregator import aggregate_findings
from leakguard.detection.ner_adapter import (
    NERAdapterProtocol,
    PresidioNERAdapter,
    SpacyNERAdapter,
)
from leakguard.detection.regex_detector import RegexDetector
from leakguard.detection.secret_detector import SecretDetector
from leakguard.detection.validators import (
    validate_iban,
    validate_luhn,
    validate_pan,
    validate_verhoeff,
    validate_voter_id,
)

__all__ = [
    "NERAdapterProtocol",
    "PresidioNERAdapter",
    "RegexDetector",
    "SecretDetector",
    "SpacyNERAdapter",
    "aggregate_findings",
    "validate_iban",
    "validate_luhn",
    "validate_pan",
    "validate_verhoeff",
    "validate_voter_id",
]
