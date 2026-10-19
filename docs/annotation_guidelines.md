# LEAKGUARD — Data Annotation & Labeling Guidelines

**Document Version:** 1.0.0  
**Phase:** Phase 2 (Data & Label Design)  
**Task Scope:** Entity Span Annotation (NER/DLP) and Message-Level Risk Classification  

---

## 1. Overview and Core Principles

LEAKGUARD evaluates data leaks at two distinct granularities:
1. **Entity-Level Spans:** Exact character offsets (`[start, end)`) marking sensitive identifiers, credentials, and financial instruments within the original UTF-8 code point sequence.
2. **Message-Level Risk:** Policy-driven risk triage classifying the entire message into one of three risk tiers:
   - `no_exposure`
   - `possible_exposure`
   - `high_risk_exposure`

> **Fundamental Principle (F-01 / F-02):**  
> *Presence of an entity does not automatically equate to a high-risk data leak.*  
> A public documentation example (e.g., `user@example.com`) or an empty placeholder (`<YOUR_API_KEY>`) contains syntactic patterns of entities, but zero security exposure. Conversely, an API key or password posted in chat represents an active high-risk compromise. Labeling must reflect security policy and context, not naive keyword matching.

---

## 2. Character Offset Standards

All entity spans **MUST** follow strict character-offset standards:
- Offsets are 0-indexed half-open intervals: `[start, end)`.
- Slicing `text[start:end]` must yield the exact string recorded in the entity annotation.
- Offsets refer to Python Unicode code points on the raw, unnormalized string. No whitespace stripping or Unicode normalization may be applied prior to span calculation.
- Leading or trailing punctuation (such as enclosing quotation marks, trailing periods, commas, or parentheses) must **NOT** be included in the entity span unless it is an intrinsic part of the syntax.

---

## 3. Entity Type Taxonomy

The detector recognizes the following entity classes, along with explicit decoy/hard-negative rules.

### 3.1 `EMAIL`
- **Definition:** Standard RFC 5322 electronic mail addresses (`local-part@domain`).
- **Positive Examples:**
  - `priya.sharma@internal-corp.in`
  - `dev.ops-lead@fintech-service.co.uk`
- **Negative / Decoy Examples:**
  - `support@example.com` *(Documentation-reserved domain: flagged as decoy / no_exposure)*
  - `test-user@test.invalid` *(RFC 2606 reserved TLD: no_exposure)*
  - `mailto:` *(protocol prefix: excluded from span)*
- **Borderline / Edge Cases:**
  - In `mailto:rohit@startup.io?subject=Help`, the span is only `rohit@startup.io`.

### 3.2 `PHONE`
- **Definition:** Telephone and mobile numbers formatted in international (`+91`, `+1`, etc.) or national formats, with standard separators (spaces, hyphens).
- **Positive Examples:**
  - `+91 98765 43210` (India standard 10-digit mobile with country code)
  - `+1-555-0199` (North American standard)
  - `09823012345`
- **Negative / Decoy Examples:**
  - `1-800-555-0199` (toll-free fictional directory numbers used as benign decoys)
  - `2026-10-18` (Date formatted with hyphens — NOT a phone number)
  - `v2.4.1` (Software release version string)
- **Borderline / Edge Cases:**
  - Sequence of digits shorter than 7 digits without calling code: Reject as ambiguous numeric string.

### 3.3 `PERSON`
- **Definition:** Human personal names (first, middle, last), covering both Western and Indian naming conventions.
- **Positive Examples:**
  - `Aarav Nambiar`
  - `Sunita Deshmukh`
  - `David K. Miller`
- **Negative / Decoy Examples:**
  - `Apache Kafka` (Software / Technology name)
  - `State Bank of India` (Organization, not an individual person)
  - `John Doe` / `Jane Doe` (Generic placeholder names in mock templates)
- **Borderline / Edge Cases:**
  - Single-word common nouns capitalized at the start of a sentence (`May I assist you?` vs `May Patel`). Only proper human names in context are annotated.

### 3.4 `CARD` (Payment Card Number)
- **Definition:** 13-to-19 digit primary account numbers (PAN) formatted with or without delimiters (spaces or dashes) for Visa, MasterCard, RuPay, Amex, Discover.
- **Positive Examples (Test / Fake Values):**
  - Fake cards satisfying the Luhn checksum algorithm generated strictly within test ranges (e.g., test prefixes `4000 0012 3456 ...` or `5105 1051 ...`).
- **Negative / Decoy Examples:**
  - `9999-9999-9999-9999` (Invalid Luhn checksum decoy)
  - `1234567890123456` (Sequential numbers failing Luhn)
  - `ORD-2026-948102394` (Order/tracking identifier)
- **Borderline / Edge Cases:**
  - Masked cards such as `4111-XXXX-XXXX-1111`: Annotated as `CARD_MASKED` or ignored if fewer than 6 actionable digits remain.

### 3.5 `AADHAAR` (India Unique Identification Number)
- **Definition:** 12-digit Indian national identity number, usually formatted as 3 groups of 4 digits separated by spaces (`XXXX XXXX XXXX`).
- **Positive Examples (Synthetic Valid Checksum):**
  - `9999 4105 2814` (12 digits passing Verhoeff checksum algorithm, using non-allocated test prefixes).
- **Negative / Decoy Examples:**
  - `1234 5678 9012` (Fails Verhoeff checksum — decoy)
  - `0000 0000 0000` (All zeros or invalid Verhoeff — decoy)
  - `TXN 849204829104` (12-digit transaction ID)
- **Borderline / Edge Cases:**
  - 12 consecutive digits in a URL path (e.g., `/items/102938475610`): Context must not suggest an Aadhaar card.

### 3.6 `PAN` (India Permanent Account Number)
- **Definition:** 10-character alphanumeric identifier issued by the Indian Income Tax Department, with the regex structure `^[A-Z]{5}[0-9]{4}[A-Z]$` (where the 4th letter signifies status, e.g., 'P' for Individual).
- **Positive Examples:**
  - `ABCDE1234F`
  - `BNZPS5432K`
- **Negative / Decoy Examples:**
  - `ABCDE12345` (5 letters + 5 numbers: invalid PAN structure)
  - `MODULE123A` (7 letters + 3 numbers: invalid)
  - `SHA256:E3B0C44298FC` (Cryptographic hash)
- **Borderline / Edge Cases:**
  - Model serial numbers or promotional codes following a 5-alpha/4-digit/1-alpha pattern without taxpayer context.

### 3.7 `IBAN` (International Bank Account Number)
- **Definition:** Up to 34 alphanumeric characters consisting of a 2-letter country code, 2 check digits, and country-specific BBAN, passing the ISO 7064 Mod-97-10 checksum.
- **Positive Examples:**
  - `GB82 WEST 1234 5698 7654 32` (UK IBAN passing mod-97)
  - `DE89 3704 0044 0532 0130 00` (German IBAN passing mod-97)
- **Negative / Decoy Examples:**
  - `GB00 ABCD 0000 0000 00` (Fails mod-97 check)
  - `INV-2026-EU-99238` (Invoice code)

### 3.8 `ACCOUNT_NUMBER` (Domestic Bank Account Number)
- **Definition:** 9-to-18 digit domestic bank account numbers found adjacent to routing terms, IFSC codes (`[A-Z]{4}0[A-Z0-9]{6}`), or banking keywords.
- **Positive Examples:**
  - `A/C No: 918273645019` with IFSC `HDFC0001234`
  - `Account: 10293847561`
- **Negative / Decoy Examples:**
  - Standalone 10-digit number without banking context (defaults to possible phone or generic number).
  - Tracking numbers: `FEDEX-9281738291`.

### 3.9 `VOTER_ID` (India EPIC Card)
- **Definition:** Electoral Photo Identity Card (EPIC) alphanumeric code: 3 uppercase letters followed by 7 numeric digits (`^[A-Z]{3}[0-9]{7}$`).
- **Positive Examples:**
  - `XYZ1234567`
  - `ABC9876543`
- **Negative / Decoy Examples:**
  - `AB12345678` (2 letters + 8 digits: invalid EPIC format)

### 3.10 `PASSWORD`
- **Definition:** Plaintext passwords, authentication secrets, database credentials, or private credentials exposed in code, configuration, or chat.
- **Positive Examples:**
  - `password = "P@ssw0rd2026!#"`
  - `db_pass: 'SecretAdminDb99'`
- **Negative / Decoy Examples:**
  - `password = "<ENTER_PASSWORD_HERE>"` (Template placeholder: no_exposure)
  - `Password must be at least 8 characters long.` (Security policy guidance)
  - `password: **********` (Masked value)
- **Borderline / Edge Cases:**
  - Single word dictionary words in general conversation (`"What is the password to enter the club?"` -> no secret exposed).

### 3.11 `API_KEY` / `SECRET_TOKEN`
- **Definition:** High-entropy authentication keys, cloud provider credentials (AWS access keys `AKIA[0-9A-Z]{16}`, GitHub personal access tokens `ghp_[A-Za-z0-9]{36}`, Slack tokens `xox[baprs]-[0-9A-Za-z-]{10,48}`, generic bearer tokens `Bearer eyJ...`, JWTs, private keys).
- **Positive Examples (Clearly non-functional synthetic tokens):**
  - `AKIAIOSFODNN7EXAMPLE` (Standard documentation test key)
  - `ghp_FakeTokenForTestingDocumentationOnly1234`
  - `xoxb-PLACEHOLDER-DOCUMENTATION-TOKEN`
- **Negative / Decoy Examples:**
  - `api_key = "YOUR_API_KEY"` (Template placeholder)
  - `api_key: None` (Null configuration)
  - `commit 4f3b7c9e01a2d3e4f5a6b7c8d9e0f1a2b3c4d5e6` (Git commit hash)
  - `uuid: 550e8400-e29b-41d4-a716-446655440000` (Standard UUID)

---

## 4. Message-Level Risk Policy Taxonomy

Every message is assigned exactly one risk category according to the following criteria.

```
+-----------------------------------------------------------------------------------------+
|                                    MESSAGE RISK TIERS                                   |
+----------------------+---------------------------------+--------------------------------+
|  `no_exposure`       |  `possible_exposure`            |  `high_risk_exposure`          |
|                      |                                 |                                |
|  - Zero entities     |  - Business/contact info        |  - Live passwords & API keys   |
|  - Safe placeholders |  - Single personal identifier   |  - Full payment card + CVV/exp |
|  - RFC doc domains   |  - Bank account without secret  |  - Aadhaar / PAN combinations  |
|  - Decoys & negatives|  - Low-sensitivity internal logs|  - Database dumps & credentials|
+----------------------+---------------------------------+--------------------------------+
```

### 4.1 `no_exposure` (Safe / Benign / Negative)
A message containing no actionable sensitive data, or containing syntax patterns that are explicitly benign, non-functional, or placeholders.

- **Criteria:**
  1. Everyday conversational messages, code snippets without secrets, marketing copy.
  2. Syntactic matches that are documentation domains (`example.com`, `example.org`, `test.invalid`).
  3. Evident placeholders: `<INSERT_KEY>`, `YOUR_PASSWORD_HERE`, `TODO: add token`.
  4. Decoys failing mathematical validation (cards failing Luhn, Aadhaar failing Verhoeff).
  5. Policy statements or discussions of security without exposing actual secrets.

- **Examples:**
  - *"Hey team, don't forget to push your branch before the standup tomorrow at 10 AM."*
  - *"To authenticate, replace the placeholder in `curl -H 'Authorization: Bearer <TOKEN>' https://api.example.com/v1`."*
  - *"Tracking number for package is ORD-99281928491-DEL."*

### 4.2 `possible_exposure` (Medium Sensitivity / Context Dependent)
A message containing personal contact details or financial identifiers in an unauthenticated or low-security context, where the data is sensitive or regulated (e.g. GDPR, DPDP) but does not immediately grant system access or cause irreversible credential takeover.

- **Criteria:**
  1. Direct personal contact details (personal email + phone number) shared in a message.
  2. Identity documents (Aadhaar, PAN, Voter ID) mentioned in correspondence without accompanying passwords or financial keys.
  3. Bank account number and IFSC code shared for legitimate peer transfer.
  4. Employee names linked with internal organizational role or project code.

- **Examples:**
  - *"Please find Rahul Verma's contact details for the candidate interview: rahul.v@personalmail.in, +91 98450 11223."*
  - *"For the vendor refund, transfer the amount to Account 309482019482, IFSC SBIN0001234, beneficiary Sunita Rao."*
  - *"Here is my PAN for the tax deduction verification: ABCDE1234F."*

### 4.3 `high_risk_exposure` (Critical / Urgent Security Breach)
A message containing active authentication credentials, cloud/API tokens, full payment card records, or combinations of private identifiers that allow immediate unauthorized access, account takeover, or severe data compromise.

- **Criteria:**
  1. Plaintext passwords or connection strings exposing database credentials (`postgres://user:pass@host/db`).
  2. Cloud provider, SaaS, or payment gateway API keys / tokens (`AKIA...`, `ghp_...`, `stripe_sk_...`).
  3. Private cryptographic keys (e.g. PEM private key headers `-----BEGIN [TYPE] PRIVATE KEY-----`).
  4. Complete payment card data (Luhn-valid PAN + expiry + CVV).
  5. Bulk identity/credential dumps (e.g., list of compromised username/passwords or Aadhaar + PAN + Bank login).

- **Examples:**
  - *"Quick hotfix for staging: use AWS access key AKIAIOSFODNN7EXAMPLE and secret <MOCK_SECRET_KEY> to upload the build."*
  - *"DB connection failed on prod. The root credentials are admin / Str0ngP@ssw0rd!2026 at db.internal.net."*
  - *"Found this unencrypted customer export: Card 4000 0012 3456 7890, Exp 08/28, CVV 392, Holder Amit Kumar."*

---

## 5. Borderline Resolution Protocol

When an annotator or automated validator encounters an ambiguous instance, apply these strict tie-breaking rules:

| Ambiguity | Rule | Rationale |
|---|---|---|
| Card number valid by Luhn, but marked as `TEST_CARD` in context | Label entity as `CARD`, but message risk as `no_exposure` if clearly a test fixture, or `possible_exposure` if in production repo. | Prevents false alarms on documented test suites while tracking entity syntax. |
| Email is `@example.com` or `@test.invalid` | Do NOT annotate as a leak entity. Message label = `no_exposure`. | Explicitly reserved RFC domains are never sensitive. |
| Aadhaar / PAN fails mathematical checksum (Verhoeff / format) | Do NOT annotate as valid entity. Keep as negative decoy. Message label = `no_exposure`. | Checksum failure proves value is not a genuine identity document. |
| API key with placeholder prefix e.g. `AKIA_MOCK_PLACEHOLDER` | Annotate as decoy. Message label = `no_exposure`. | Explicit mock token cannot compromise cloud infrastructure. |
| Name + Email + Phone together in email signature | Annotate all three entity spans. Message label = `possible_exposure`. | Business contact cards are personal data under privacy regulations, but not catastrophic leaks. |
| Single password without username | Annotate span as `PASSWORD`. Message label = `high_risk_exposure`. | Plaintext secrets must always be treated as high risk regardless of surrounding context. |

---

## 6. Machine-Readable Schema Specification

Each generated or annotated dataset row conforms strictly to the following JSON structure:

```json
{
  "id": "gen_f01_t001_s42_000001",
  "text": "Please transfer payment to Account: 10293847561 with IFSC: HDFC0001234, holder: Aarav Nambiar.",
  "entities": [
    {
      "start": 36,
      "end": 47,
      "label": "ACCOUNT_NUMBER",
      "value": "10293847561"
    },
    {
      "start": 82,
      "end": 95,
      "label": "PERSON",
      "value": "Aarav Nambiar"
    }
  ],
  "message_label": "possible_exposure",
  "template_id": "tpl_banking_transfer_01",
  "family_id": "fam_banking",
  "generator_version": "0.1.0",
  "seed": 42
}
```
