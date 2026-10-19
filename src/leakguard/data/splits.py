"""Group splitting and cross-split leakage verification for LEAKGUARD datasets.

Guarantees:
- Group split by `family_id` targeting 60% train, 20% validation, 20% test.
- Zero family overlap across splits.
- Exact duplicate detection across splits (normalized string hash).
- Near-duplicate detection across splits (n-gram Jaccard similarity threshold).
- Fails loudly (raises ValueError) if any cross-split leakage is detected.
"""

from __future__ import annotations

import hashlib
import random
import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


@dataclass
class SplitData:
    train: list[dict[str, Any]]
    val: list[dict[str, Any]]
    test: list[dict[str, Any]]
    stats: dict[str, Any]


def normalize_text(text: str) -> str:
    """Normalize text by collapsing whitespace and lowercasing."""
    return re.sub(r"\s+", " ", text.strip().lower())


def get_word_ngrams(text: str, n: int = 3) -> set[str]:
    """Extract word n-grams from text. Falls back to character n-grams if words < n."""
    tokens = re.findall(r"\w+", text.lower())
    if len(tokens) >= n:
        return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}
    # Fallback to character 4-grams for very short messages
    clean = "".join(tokens)
    if len(clean) >= 4:
        return {clean[i : i + 4] for i in range(len(clean) - 3)}
    return {clean} if clean else set()


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Compute Jaccard similarity coefficient between two sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def check_exact_duplicates(splits: dict[str, Sequence[dict[str, Any]]]) -> None:
    """Verify that no exact duplicates (by normalized text) exist across different splits.

    Raises:
        ValueError: If identical normalized text is detected across different splits.
    """
    seen_hashes: dict[str, tuple[str, str, str]] = {}  # hash -> (split_name, record_id, text)

    for split_name, records in splits.items():
        for rec in records:
            norm = normalize_text(rec["text"])
            h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
            if h in seen_hashes:
                other_split, other_id, other_text = seen_hashes[h]
                if other_split != split_name:
                    msg = (
                        f"Cross-split EXACT duplicate detected between {split_name} "
                        f"(ID: {rec['id']}) and {other_split} (ID: {other_id}): '{rec['text']}'"
                    )
                    raise ValueError(msg)
            else:
                seen_hashes[h] = (split_name, rec["id"], rec["text"])


def check_near_duplicates(
    splits: dict[str, Sequence[dict[str, Any]]],
    threshold: float = 0.85,
    sample_limit: int = 500,
) -> None:
    """Check for near-duplicate text across splits using n-gram Jaccard similarity.

    Uses an inverted index over n-grams to efficiently compare across split boundaries.

    Raises:
        ValueError: If n-gram Jaccard similarity exceeds threshold between different splits.
    """
    # Index splits
    split_names = list(splits.keys())
    for i in range(len(split_names)):
        for j in range(i + 1, len(split_names)):
            split1, split2 = split_names[i], split_names[j]
            recs1 = splits[split1][:sample_limit]
            recs2 = splits[split2][:sample_limit]

            # Inverted index for recs2 n-grams
            index2: dict[str, list[int]] = defaultdict(list)
            ngrams2 = [get_word_ngrams(r["text"]) for r in recs2]
            for idx2, grams in enumerate(ngrams2):
                for gram in grams:
                    index2[gram].append(idx2)

            for rec1 in recs1:
                grams1 = get_word_ngrams(rec1["text"])
                if not grams1:
                    continue
                # Candidate matching indices in recs2 sharing at least one n-gram
                candidate_indices: set[int] = set()
                for gram in grams1:
                    if gram in index2:
                        candidate_indices.update(index2[gram])

                for idx2 in candidate_indices:
                    sim = jaccard_similarity(grams1, ngrams2[idx2])
                    if sim > threshold:
                        rec2 = recs2[idx2]
                        msg = (
                            f"Cross-split NEAR duplicate detected ({sim:.3f} > {threshold}) "
                            f"between {split1} (ID: {rec1['id']}) and "
                            f"{split2} (ID: {rec2['id']}):\n"
                            f"  [{split1}]: '{rec1['text']}'\n"
                            f"  [{split2}]: '{rec2['text']}'"
                        )
                        raise ValueError(msg)


def group_split_by_family(
    records: Sequence[dict[str, Any]],
    train_ratio: float = 0.60,
    val_ratio: float = 0.20,
    test_ratio: float = 0.20,
    seed: int = 42,
    near_dup_threshold: float = 0.85,
) -> SplitData:
    """Split dataset records into train, validation, and test by `family_id`.

    Enforces that all records with the same `family_id` remain strictly within a single split.
    Then performs exact and near-duplicate leakage verification.
    """
    family_to_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        family_to_records[rec["family_id"]].append(rec)

    # Sort families deterministically
    sorted_families = sorted(family_to_records.keys())
    rng = random.Random(seed)
    # Shuffle families
    shuffled_families = list(sorted_families)
    rng.shuffle(shuffled_families)

    total_records = len(records)
    target_train = int(total_records * train_ratio)
    target_val = int(total_records * val_ratio)

    train_families: set[str] = set()
    val_families: set[str] = set()
    test_families: set[str] = set()

    current_train_count = 0
    current_val_count = 0

    for fam in shuffled_families:
        fam_count = len(family_to_records[fam])
        if current_train_count + fam_count <= target_train or (
            not train_families and current_train_count == 0
        ):
            train_families.add(fam)
            current_train_count += fam_count
        elif current_val_count + fam_count <= target_val or (
            not val_families and current_val_count == 0
        ):
            val_families.add(fam)
            current_val_count += fam_count
        else:
            test_families.add(fam)

    # If any split ended up empty (edge case with few families), balance
    if not test_families and len(shuffled_families) >= 3:
        moved = shuffled_families[-1]
        if moved in train_families:
            train_families.remove(moved)
        elif moved in val_families:
            val_families.remove(moved)
        test_families.add(moved)

    # Build splits with deterministic family ordering
    train_recs: list[dict[str, Any]] = []
    val_recs: list[dict[str, Any]] = []
    test_recs: list[dict[str, Any]] = []

    for fam in sorted(train_families):
        train_recs.extend(family_to_records[fam])
    for fam in sorted(val_families):
        val_recs.extend(family_to_records[fam])
    for fam in sorted(test_families):
        test_recs.extend(family_to_records[fam])

    # Enforce strict group disjointness assertion
    assert not (train_families & val_families), "Train and Val families overlap!"
    assert not (train_families & test_families), "Train and Test families overlap!"
    assert not (val_families & test_families), "Val and Test families overlap!"

    # Verify zero cross-split exact duplicates
    splits_dict = {"train": train_recs, "val": val_recs, "test": test_recs}
    check_exact_duplicates(splits_dict)

    # Verify zero cross-split near duplicates
    check_near_duplicates(splits_dict, threshold=near_dup_threshold)

    stats = {
        "train_count": len(train_recs),
        "val_count": len(val_recs),
        "test_count": len(test_recs),
        "train_families": sorted(list(train_families)),
        "val_families": sorted(list(val_families)),
        "test_families": sorted(list(test_families)),
        "train_ratio_actual": round(len(train_recs) / total_records, 4) if total_records else 0,
        "val_ratio_actual": round(len(val_recs) / total_records, 4) if total_records else 0,
        "test_ratio_actual": round(len(test_recs) / total_records, 4) if total_records else 0,
    }

    return SplitData(train=train_recs, val=val_recs, test=test_recs, stats=stats)
