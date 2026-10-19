# LEAKGUARD Dataset Card

**Dataset Name:** LEAKGUARD Synthetic Benchmark Corpus  
**Version:** 1.0.0 (Generator version 0.1.0, seed 42)  
**Created:** 2026-10-18  
**Format:** JSON Lines (`.jsonl`) with exact UTF-8 character spans  
**License:** Synthetic generation pipeline licensed under MIT / Author Project Baseline; Faker dependency licensed under MIT.  

---

## 1. Dataset Description

The LEAKGUARD Synthetic Benchmark Corpus is a purpose-built, leak-safe dataset designed for training and evaluating data loss prevention (DLP) models, regex detectors, and security risk triage systems.

Unlike naive synthetic datasets that randomize single words or conflate any entity match with a leak, this corpus:
1. Distinguishes **entity-level detection** (where entities reside via character offsets `[start, end)`) from **message-level risk triage** (`no_exposure`, `possible_exposure`, `high_risk_exposure`).
2. Implements **author-written template families** (157 templates across 15 families) representing realistic developer chat, cloud configuration, banking transfers, KYC submissions, support tickets, and benign documentation.
3. Uses **mathematically valid test formats** (Verhoeff algorithm for Aadhaar in test prefixes, Luhn algorithm for payment cards in test BINs, ISO 7064 Mod-97-10 for IBAN) alongside negative decoys (non-Luhn card numbers, non-Verhoeff numbers, order IDs, version strings, RFC documentation domains).
4. Strictly isolates templates using **group splits by `family_id`** (60% train, 20% validation, 20% test) with proven zero cross-split exact or near-duplicate leakage.

---

## 2. Dataset Structure and Schema

Each row is a single UTF-8 JSON object formatted as follows:

```json
{
  "id": "lg_fam_cloud_infra_tpl_cloud_01_s42_000000",
  "text": "AWS credentials for prod migration: AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE and secret password=P@ssw0rd!2026. Do not commit!",
  "entities": [
    {
      "start": 54,
      "end": 74,
      "label": "API_KEY",
      "value": "AKIAIOSFODNN7EXAMPLE"
    },
    {
      "start": 96,
      "end": 109,
      "label": "PASSWORD",
      "value": "P@ssw0rd!2026"
    }
  ],
  "message_label": "high_risk_exposure",
  "template_id": "tpl_cloud_01",
  "family_id": "fam_cloud_infra",
  "generator_version": "0.1.0",
  "seed": 42
}
```

### Field Definitions

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Unique identifier incorporating family, template, seed, and row index |
| `text` | `string` | The complete raw message text (supports multiline and Unicode) |
| `entities` | `list[object]` | List of sensitive entity spans (`start`, `end`, `label`, `value`) |
| `message_label` | `string` | Risk tier: `no_exposure`, `possible_exposure`, or `high_risk_exposure` |
| `template_id` | `string` | Identifier of the originating template |
| `family_id` | `string` | Semantic family identifier used for group splitting |
| `generator_version` | `string` | Version of the generation engine (`0.1.0`) |
| `seed` | `integer` | Random seed used for generation (`42`) |

---

## 3. Dataset Statistics

Generated with `--seed 42` (total 4,000 records):

### 3.1 Split Distribution (Group Split by `family_id`)

| Split | Record Count | Percentage | Assigned Families |
|---|---|---|---|
| **Train** | 2,382 | 59.55% | `fam_cloud_infra`, `fam_customer_support`, `fam_decoy_negative`, `fam_dev_logs`, `fam_ecommerce_orders`, `fam_fin_cards`, `fam_multiline_tickets`, `fam_policy_guidance`, `fam_unicode_samples` (9 families) |
| **Validation** | 796 | 19.90% | `fam_casing_variants`, `fam_credentials_chat`, `fam_credentials_git` (3 families) |
| **Test** | 822 | 20.55% | `fam_banking_in`, `fam_hr_recruitment`, `fam_identity_in` (3 families) |
| **Total** | 4,000 | 100.0% | 15 families (157 templates) |

*Verification:* Zero family overlap between splits. Zero exact duplicates (normalized SHA-256) and zero near duplicates (word 3-gram Jaccard > 0.85) across splits.

### 3.2 Message-Level Class Distribution

| Class | Count | Percentage | Policy Description |
|---|---|---|---|
| `high_risk_exposure` | 1,553 | 38.83% | Live-shaped credentials, active cloud tokens, full payment card numbers |
| `possible_exposure` | 1,497 | 37.42% | Personal contact info, Indian identity numbers, domestic bank accounts |
| `no_exposure` | 950 | 23.75% | Safe placeholders, RFC test domains, non-PII order/tracking IDs, policy text |

### 3.3 Entity Type Frequencies

| Entity Type | Instances | Description / Validation Standard |
|---|---|---|
| `PERSON` | 1,497 | Indian and Western personal names (`en_IN`, `en_US`) |
| `EMAIL` | 884 | RFC 5322 synthetic emails on non-existent domains |
| `PHONE` | 781 | Indian mobile (`+91`) and international formats |
| `PASSWORD` | 725 | Plaintext credentials in code/chat contexts |
| `API_KEY` | 700 | AWS, GitHub, Slack, and Bearer test tokens |
| `CARD` | 336 | 16-digit payment cards in test BINs with valid Luhn |
| `ACCOUNT_NUMBER` | 284 | Domestic bank account numbers (11–14 digits) |
| `PAN` | 206 | Indian Permanent Account Numbers (alphanumeric structure) |
| `AADHAAR` | 181 | 12-digit Indian national identity with valid Verhoeff checksum |
| `IBAN` | 52 | International bank account numbers passing ISO 7064 Mod-97 |
| `VOTER_ID` | 52 | Indian Voter ID (EPIC format: 3 letters + 7 digits) |

---

## 4. Privacy, Safety, and Ethical Considerations

1. **Zero Real Personal Data:** All personal names, email addresses, phone numbers, and identity codes are synthesized via pseudo-random number generators and seeded Faker instances.
2. **Clearly Non-Functional Credentials:**
   - Email domains use non-routable or documentation-reserved domains (`example.com`, `corp-cloud-internal.in`).
   - Cards use standard test ranges (e.g. Visa `4000 00...`).
   - Aadhaar numbers use unassigned `9999` test prefixes.
   - API tokens use standard test fragments (e.g. `AKIAIOSFODNN7EXAMPLE`).
3. **No Secret Ingestion:** The dataset generation process requires zero network access, connects to no external APIs, and commits zero raw files.

---

## 5. Intended Use and Limitations

### Intended Use
- Benchmarking NER detectors, regex rules, and machine learning classifiers for data leak prevention.
- Evaluating redaction accuracy without risking real data exposure.
- Headless testing of the LEAKGUARD console.

### Limitations
- **Synthetic Distribution:** Template-generated language may exhibit lower stylistic diversity than real human chat. To address this, evaluations must be cross-referenced against the human-written challenge set (`data/challenge/`).
- **Not a Production DLP Oracle:** Satisfying synthetic benchmarks does not guarantee coverage of adversarial zero-day credential formats.
