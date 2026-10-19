"""Unit and integration tests for NER adapter and fallback mechanisms.

Verifies:
  - NERAdapterProtocol conformance
  - Graceful fallback when models or packages are absent (no crashes)
  - Accurate PERSON detection and offset alignment
  - Pipeline integration with NER enabled vs absent
  - Presidio adapter compatibility
"""

from __future__ import annotations

from leakguard.detection.ner_adapter import (
    NERAdapterProtocol,
    PresidioNERAdapter,
    SpacyNERAdapter,
)
from leakguard.detection.pipeline import Pipeline
from leakguard.schemas import Severity


def test_ner_adapter_protocol_conformance():
    """Verify SpacyNERAdapter and PresidioNERAdapter satisfy NERAdapterProtocol."""
    spacy_adapter = SpacyNERAdapter()
    presidio_adapter = PresidioNERAdapter()

    assert isinstance(spacy_adapter, NERAdapterProtocol)
    assert isinstance(presidio_adapter, NERAdapterProtocol)
    assert spacy_adapter.name == "ner"
    assert presidio_adapter.name == "presidio"


def test_spacy_adapter_graceful_missing_model_fallback():
    """Verify adapter handles nonexistent models safely without throwing exceptions."""
    adapter = SpacyNERAdapter(model_name="nonexistent_mock_model_12345")

    # Should not raise exception
    assert not adapter.is_available()
    status = adapter.get_status()
    assert "NER unavailable:" in status
    assert "nonexistent_mock_model_12345" in status

    # Calling detect on unavailable adapter returns empty list
    findings = adapter.detect("Priya Sharma was reviewing the document.")
    assert findings == []


def test_spacy_adapter_person_detection():
    """Verify spaCy adapter extracts personal names with exact character offsets."""
    adapter = SpacyNERAdapter(model_name="en_core_web_sm", target_labels={"PERSON"})
    if not adapter.is_available():
        return  # Graceful skip if model cannot be loaded in test runner

    sample_text = "Engineering update: Lead developer Aarav Sharma reviewed the migration."
    findings = adapter.detect(sample_text)

    person_findings = [f for f in findings if f.entity_type == "PERSON"]
    assert len(person_findings) >= 1

    f = person_findings[0]
    assert f.entity_type == "PERSON"
    assert f.detector == "ner"
    assert f.severity == Severity.LOW

    # Verify exact character offset alignment
    extracted_slice = sample_text[f.start : f.end]
    assert "Aarav Sharma" in extracted_slice
    assert f.display_value.endswith("(PERSON)")
    assert "Aarav Sharma" not in f.display_value  # Masked display value


def test_pipeline_integration_with_and_without_ner():
    """Verify Pipeline functions identically when NER is absent and enhances detection
    when present.
    """
    text = (
        "Project lead Priya Sharma updated credentials: "
        "AWS_KEY: AKIAIOSFODNN7EXAMPLE, email: priya@corp.in"
    )

    # 1. Pipeline with NO NER (Phase 3 behavior)
    pipe_no_ner = Pipeline(ner_adapter=None)
    res_no_ner = pipe_no_ner.scan(text)

    types_no_ner = {f.entity_type for f in res_no_ner.findings}
    assert "API_KEY" in types_no_ner
    assert "EMAIL" in types_no_ner
    assert "PERSON" not in types_no_ner

    # 2. Pipeline with spaCy NER (Phase 4 Candidate B)
    spacy_adapter = SpacyNERAdapter("en_core_web_sm")
    if not spacy_adapter.is_available():
        return

    pipe_with_ner = Pipeline(ner_adapter=spacy_adapter)
    res_with_ner = pipe_with_ner.scan(text)

    types_with_ner = {f.entity_type for f in res_with_ner.findings}
    assert "API_KEY" in types_with_ner
    assert "EMAIL" in types_with_ner
    assert "PERSON" in types_with_ner

    # Priority check: regex/secret take precedence in aggregator
    for f in res_with_ner.findings:
        if f.entity_type == "API_KEY":
            assert f.detector == "secret"
        elif f.entity_type == "EMAIL":
            assert f.detector == "regex"


def test_presidio_adapter_detection():
    """Verify Presidio adapter processes text and yields mapped findings."""
    adapter = PresidioNERAdapter(use_custom_recognizers=True)
    if not adapter.is_available():
        return

    text = "Contact support at help@company.org or phone +91 98765 43210."
    findings = adapter.detect(text)

    types = {f.entity_type for f in findings}
    assert len(types) > 0
    for f in findings:
        assert f.detector == "presidio"
        assert text[f.start : f.end]
