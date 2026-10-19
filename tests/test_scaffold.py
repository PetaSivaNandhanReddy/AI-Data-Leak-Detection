"""Trivial sanity and scaffold tests for LEAKGUARD."""

import leakguard
from leakguard.config import settings


def test_package_import():
    """Verify package import and version presence."""
    assert leakguard.__version__ == "0.1.0"


def test_settings_defaults():
    """Verify default safety configuration limits."""
    assert settings.max_input_length == 20_000
    assert settings.default_redaction_mode == "placeholder"
