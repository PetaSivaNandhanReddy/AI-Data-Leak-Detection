"""Unit and integration tests for data generation, schema validation, and group splitting."""

import json
from pathlib import Path

import pytest

from leakguard.data.generate import generate_dataset
from leakguard.data.splits import (
    check_exact_duplicates,
    check_near_duplicates,
    group_split_by_family,
)
from leakguard.data.synthetic_values import (
    SyntheticValueFactory,
    compute_iban_check,
    compute_luhn,
    compute_verhoeff,
    validate_iban,
    validate_luhn,
    validate_verhoeff,
)
from leakguard.data.templates import ALL_TEMPLATES, FAMILY_MAP
from leakguard.data.validate import validate_dataset, validate_record


def test_verhoeff_algorithm():
    """Verify Verhoeff checksum generation and validation."""
    prefix = "99991234567"
    chk = compute_verhoeff(prefix)
    valid_aadhaar = prefix + str(chk)
    assert validate_verhoeff(valid_aadhaar) is True

    # Mutate last digit - must fail
    invalid_aadhaar = prefix + str((chk + 1) % 10)
    assert validate_verhoeff(invalid_aadhaar) is False


def test_luhn_algorithm():
    """Verify Luhn checksum calculation and validation."""
    prefix = "400000123456789"
    chk = compute_luhn(prefix)
    valid_card = prefix + str(chk)
    assert validate_luhn(valid_card) is True

    # Mutate last digit - must fail
    invalid_card = prefix + str((chk + 1) % 10)
    assert validate_luhn(invalid_card) is False


def test_iban_algorithm():
    """Verify ISO 7064 Mod-97-10 IBAN generation and validation."""
    country = "GB"
    bban = "WEST12345698765432"
    chk = compute_iban_check(country, bban)
    valid_iban = f"{country}{chk}{bban}"
    assert validate_iban(valid_iban) is True

    # Corrupt check digits
    invalid_iban = f"{country}00{bban}"
    assert validate_iban(invalid_iban) is False


def test_synthetic_value_factory():
    """Verify synthetic value factory produces conforming entities."""
    factory = SyntheticValueFactory(seed=123)

    # Aadhaar
    aadhaar = factory.aadhaar()
    assert validate_verhoeff(aadhaar) is True

    decoy_aadhaar = factory.decoy_aadhaar()
    assert validate_verhoeff(decoy_aadhaar) is False

    # Card
    card = factory.card_number()
    assert validate_luhn(card) is True

    decoy_card = factory.decoy_card_number()
    assert validate_luhn(decoy_card) is False

    # PAN
    pan = factory.pan()
    assert len(pan) == 10
    assert pan[:3].isalpha()
    assert pan[3] in "PCHFATB"
    assert pan[4].isalpha()
    assert pan[5:9].isdigit()
    assert pan[9].isalpha()

    # IBAN
    iban = factory.iban()
    assert validate_iban(iban) is True


def test_template_catalog_count_and_structure():
    """Verify template library size, families, and structure."""
    assert 150 <= len(ALL_TEMPLATES) <= 250, (
        f"Template count {len(ALL_TEMPLATES)} out of target 150-250 range"
    )
    assert len(FAMILY_MAP) >= 12, "Expected at least 12 distinct families"

    seen_ids = set()
    for tpl in ALL_TEMPLATES:
        assert tpl.template_id not in seen_ids, f"Duplicate template ID: {tpl.template_id}"
        seen_ids.add(tpl.template_id)
        assert tpl.message_label in {"no_exposure", "possible_exposure", "high_risk_exposure"}
        assert len(tpl.segments) > 0


def test_dataset_generation_and_exact_span_alignment():
    """Verify generated dataset records align perfectly on character offsets."""
    records = generate_dataset(num_samples=100, seed=42)
    assert len(records) == 100

    report = validate_dataset(records)
    assert report["is_valid"] is True
    assert report["valid_records"] == 100
    assert len(report["errors"]) == 0

    # Explicit check on entity span slicing
    for rec in records:
        text = rec["text"]
        for ent in rec["entities"]:
            start = ent["start"]
            end = ent["end"]
            expected_val = ent["value"]
            actual_val = text[start:end]
            assert actual_val == expected_val, (
                f"Mismatch in record {rec['id']}: expected '{expected_val}', got '{actual_val}'"
            )


def test_validate_record_catches_offset_corruption():
    """Verify that corrupting character offsets triggers validation errors."""
    records = generate_dataset(num_samples=5, seed=99)
    rec = dict(records[0])

    if rec["entities"]:
        corrupted = dict(rec)
        corrupted["entities"] = [dict(e) for e in rec["entities"]]
        # Corrupt start offset
        corrupted["entities"][0]["start"] += 1
        errors = validate_record(corrupted)
        assert len(errors) > 0
        assert any("offset alignment failure" in err for err in errors)


def test_validate_record_catches_empty_text():
    """Verify that empty text is rejected."""
    bad_rec = {
        "id": "bad_01",
        "text": "   ",
        "entities": [],
        "message_label": "no_exposure",
        "template_id": "tpl_test",
        "family_id": "fam_test",
        "generator_version": "0.1.0",
        "seed": 42,
    }
    errors = validate_record(bad_rec)
    assert any("empty or contains only whitespace" in err for err in errors)


def test_group_split_zero_family_overlap():
    """Verify group splitting by family_id achieves 100% disjoint family sets."""
    records = generate_dataset(num_samples=300, seed=42)
    split_data = group_split_by_family(records, seed=42)

    train_fams = set(split_data.stats["train_families"])
    val_fams = set(split_data.stats["val_families"])
    test_fams = set(split_data.stats["test_families"])

    assert not (train_fams & val_fams), "Train and Val share families"
    assert not (train_fams & test_fams), "Train and Test share families"
    assert not (val_fams & test_fams), "Val and Test share families"

    assert len(split_data.train) > 0
    assert len(split_data.val) > 0
    assert len(split_data.test) > 0


def test_cross_split_exact_duplicate_detection():
    """Verify that duplicate normalized text across splits raises ValueError."""
    train_recs = [{"id": "t1", "text": "Secret password is P@ssw0rd!2026 for admin"}]
    val_recs = [{"id": "v1", "text": "Different content here"}]
    test_recs = [{"id": "te1", "text": "  secret  PASSWORD is p@ssw0rd!2026 for admin  "}]

    splits = {"train": train_recs, "val": val_recs, "test": test_recs}
    with pytest.raises(ValueError, match="Cross-split EXACT duplicate detected"):
        check_exact_duplicates(splits)


def test_cross_split_near_duplicate_detection():
    """Verify that high n-gram Jaccard overlap across splits raises ValueError."""
    text1 = "urgent critical leak revoke aws access key found in public git repository immediately"
    text2 = "urgent critical leak revoke aws access key found in public git repository please"

    train_recs = [{"id": "t1", "text": text1}]
    val_recs = [{"id": "v1", "text": text2}]

    splits = {"train": train_recs, "val": val_recs}
    with pytest.raises(ValueError, match="Cross-split NEAR duplicate detected"):
        check_near_duplicates(splits, threshold=0.70)


def test_committed_sample_200_validity():
    """Verify data/samples/sample_200.jsonl conforms completely to schema and offsets."""
    sample_file = Path("data/samples/sample_200.jsonl")
    if not sample_file.exists():
        pytest.skip(
            "data/samples/sample_200.jsonl is gitignored to comply with GitHub Push Protection"
        )

    records = []
    with open(sample_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    assert len(records) == 200, f"Expected 200 sample records, found {len(records)}"

    report = validate_dataset(records)
    assert report["is_valid"] is True, f"Sample validation failed: {report['errors']}"
    assert report["valid_records"] == 200
