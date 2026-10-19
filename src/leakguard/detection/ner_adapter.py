"""NER Adapter protocol and implementations for LEAKGUARD.

Provides a protocol-driven, lazily-loaded adapter for Named Entity Recognition (NER).
When models or packages are absent, adapters gracefully report "NER unavailable"
without throwing runtime exceptions or crashing the core pipeline.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Protocol, runtime_checkable

from leakguard.schemas import Finding, Severity, compute_safe_display_value

logger = logging.getLogger(__name__)


@runtime_checkable
class NERAdapterProtocol(Protocol):
    """Protocol defining the standard interface for optional NER components."""

    name: str

    def is_available(self) -> bool:
        """Check whether the underlying NER model and engine are loaded and ready."""
        ...

    def get_status(self) -> str:
        """Return human-readable status indicating model availability or unavailability reason."""
        ...

    def detect(self, text: str) -> list[Finding]:
        """Extract sensitive entities from text using the NER engine.

        Returns an empty list if the engine is unavailable.
        """
        ...


class SpacyNERAdapter:
    """Lazy-loading spaCy NER adapter specialized for PERSON entity detection.

    Restricted strictly to the entity types it is evaluated for (default: PERSON),
    preventing noisy false positives from general-purpose NER models on structured
    data like IDs, cards, or codes.
    """

    def __init__(
        self,
        model_name: str = "en_core_web_sm",
        target_labels: set[str] | None = None,
        name: str = "ner",
    ):
        self.name = name
        self.model_name = model_name
        self.target_labels = target_labels or {"PERSON"}
        self._nlp: Any = None
        self._loaded: bool = False
        self._load_error: str | None = None

    def load(self) -> bool:
        """Lazily load the spaCy language model if not already loaded."""
        if self._loaded:
            return self._nlp is not None

        self._loaded = True
        try:
            import spacy

            self._nlp = spacy.load(self.model_name)
            logger.info("Successfully loaded spaCy model: %s", self.model_name)
            return True
        except ImportError:
            self._nlp = None
            self._load_error = "spaCy package is not installed"
            logger.debug("spaCy import failed: package not installed")
            return False
        except OSError as exc:
            self._nlp = None
            self._load_error = f"Model '{self.model_name}' not found: {exc}"
            logger.debug("spaCy model load failed for '%s': %s", self.model_name, exc)
            return False
        except Exception as exc:  # noqa: BLE001
            self._nlp = None
            self._load_error = f"Failed to initialize spaCy model: {exc}"
            logger.warning("Unexpected error loading spaCy model: %s", exc)
            return False

    def is_available(self) -> bool:
        """Return True if the spaCy model is successfully loaded."""
        if not self._loaded:
            return self.load()
        return self._nlp is not None

    def get_status(self) -> str:
        """Return human-readable availability description."""
        if not self._loaded:
            self.load()
        if self._nlp is not None:
            labels_str = ", ".join(sorted(self.target_labels))
            return f"available: {self.model_name} [{labels_str}]"
        return f"NER unavailable: {self._load_error or 'model not loaded'}"

    def detect(self, text: str) -> list[Finding]:
        """Detect personal names (PERSON) using spaCy NER with code-point offsets."""
        if not text or not self.is_available() or self._nlp is None:
            return []

        doc = self._nlp(text)
        findings: list[Finding] = []

        for ent in doc.ents:
            if ent.label_ not in self.target_labels:
                continue

            # Strip leading/trailing whitespace if present while keeping accurate offsets
            raw_span = ent.text
            start = ent.start_char
            end = ent.end_char

            clean_text = raw_span.strip()
            if not clean_text:
                continue

            # Adjust offsets if leading/trailing whitespace was stripped
            leading_ws = len(raw_span) - len(raw_span.lstrip())
            trailing_ws = len(raw_span) - len(raw_span.rstrip())
            adj_start = start + leading_ws
            adj_end = end - trailing_ws

            # Verify sliced string matches
            if text[adj_start:adj_end] != clean_text:
                continue

            findings.append(
                Finding(
                    id=f"fnd_ner_{uuid.uuid4().hex[:12]}",
                    entity_type="PERSON",
                    start=adj_start,
                    end=adj_end,
                    detector=self.name,
                    severity=Severity.LOW,
                    display_value=compute_safe_display_value("PERSON", clean_text),
                    rationale=f"Personal name detected via NER ({self.model_name})",
                    rule_score=30.0,
                    model_prob=None,
                    provenance=(self.name,),
                )
            )

        return findings


class PresidioNERAdapter:
    """Microsoft Presidio Analyzer adapter for comparative benchmarking.

    Supports both default configuration (Candidate D) and custom recognizers
    for India-specific entities (Candidate C).
    """

    PRESIDIO_TO_LEAKGUARD: dict[str, tuple[str, Severity, float]] = {
        "PERSON": ("PERSON", Severity.LOW, 30.0),
        "EMAIL_ADDRESS": ("EMAIL", Severity.MEDIUM, 40.0),
        "PHONE_NUMBER": ("PHONE", Severity.MEDIUM, 40.0),
        "CREDIT_CARD": ("CARD", Severity.HIGH, 80.0),
        "IBAN_CODE": ("IBAN", Severity.HIGH, 55.0),
        "IN_PAN": ("PAN", Severity.HIGH, 60.0),
        "IN_AADHAAR": ("AADHAAR", Severity.HIGH, 65.0),
        "US_SSN": ("GOV_ID", Severity.HIGH, 65.0),
        "CRYPTO": ("SECRET_TOKEN", Severity.HIGH, 85.0),
    }

    def __init__(
        self,
        use_custom_recognizers: bool = False,
        name: str = "presidio",
    ):
        self.name = name
        self.use_custom_recognizers = use_custom_recognizers
        self._analyzer: Any = None
        self._loaded: bool = False
        self._load_error: str | None = None

    def load(self) -> bool:
        """Lazily initialize the Presidio AnalyzerEngine."""
        if self._loaded:
            return self._analyzer is not None

        self._loaded = True
        try:
            from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
            from presidio_analyzer.nlp_engine import NlpEngineProvider

            conf = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            }
            provider = NlpEngineProvider(nlp_configuration=conf)
            nlp_engine = provider.create_engine()
            analyzer = AnalyzerEngine(nlp_engine=nlp_engine)

            if self.use_custom_recognizers:
                # Add custom Indian PAN recognizer
                pan_pattern = Pattern(
                    name="pan_pattern",
                    regex=r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
                    score=0.85,
                )
                pan_recognizer = PatternRecognizer(
                    supported_entity="IN_PAN",
                    patterns=[pan_pattern],
                )
                analyzer.registry.add_recognizer(pan_recognizer)

                # Add custom Aadhaar recognizer
                aadhaar_pattern = Pattern(
                    name="aadhaar_pattern",
                    regex=r"\b\d{4}\s\d{4}\s\d{4}\b",
                    score=0.85,
                )
                aadhaar_recognizer = PatternRecognizer(
                    supported_entity="IN_AADHAAR",
                    patterns=[aadhaar_pattern],
                )
                analyzer.registry.add_recognizer(aadhaar_recognizer)

            self._analyzer = analyzer
            logger.info("Successfully loaded Presidio AnalyzerEngine")
            return True
        except ImportError:
            self._analyzer = None
            self._load_error = "presidio-analyzer package is not installed"
            return False
        except Exception as exc:  # noqa: BLE001
            self._analyzer = None
            self._load_error = f"Failed to initialize Presidio: {exc}"
            return False

    def is_available(self) -> bool:
        """Return True if Presidio is ready."""
        if not self._loaded:
            return self.load()
        return self._analyzer is not None

    def get_status(self) -> str:
        """Return Presidio availability description."""
        if not self._loaded:
            self.load()
        if self._analyzer is not None:
            mode = "custom_recognizers" if self.use_custom_recognizers else "default_config"
            return f"available: presidio-analyzer ({mode})"
        return f"NER unavailable: {self._load_error or 'analyzer not initialized'}"

    def detect(self, text: str) -> list[Finding]:
        """Scan text using Presidio AnalyzerEngine and map findings to LEAKGUARD taxonomy."""
        if not text or not self.is_available() or self._analyzer is None:
            return []

        results = self._analyzer.analyze(text=text, language="en")
        findings: list[Finding] = []

        for res in results:
            mapping = self.PRESIDIO_TO_LEAKGUARD.get(res.entity_type)
            if mapping is None:
                continue

            lg_type, severity, base_score = mapping
            start = res.start
            end = res.end
            val = text[start:end]

            findings.append(
                Finding(
                    id=f"fnd_presidio_{uuid.uuid4().hex[:12]}",
                    entity_type=lg_type,
                    start=start,
                    end=end,
                    detector=self.name,
                    severity=severity,
                    display_value=compute_safe_display_value(lg_type, val),
                    rationale=f"Detected via Presidio ({res.entity_type}, score={res.score:.2f})",
                    rule_score=base_score,
                    model_prob=res.score,
                    provenance=(self.name,),
                )
            )

        return findings
