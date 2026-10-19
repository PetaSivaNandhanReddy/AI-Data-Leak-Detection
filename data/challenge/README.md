# Human-Written Challenge Benchmark Set

**Directory:** `data/challenge/`  
**Purpose:** Independent evaluation benchmark authored entirely by human practitioners, completely free of automated template scripts.  
**Target Size:** 150 – 300 messages  
**Status:** Reserved & protocol documented (Phase 2). Author writes messages prior to model evaluation (Phase 4/5).  

---

## 1. Why a Human-Written Challenge Set is Mandatory (F-02)

Automated synthetic generators (even with hundreds of templates) produce structured linguistic patterns. A machine learning model or regex detector evaluated solely on synthetic templates risks measuring **template memorization** rather than true data leak detection capability.

The Human-Written Challenge Set serves as the **ultimate evaluation gate**:
- The author writes 150–300 messages by hand without consulting the generator templates.
- It tests realistic developer informal language, slang, typos, obfuscated secrets, multiline logs, and creative decoys.
- **Classifier Ship Gate:** The machine learning classifier will **only** be released in v1 if it beats the transparent rule baseline on this human challenge set with a 95% confidence interval excluding zero improvement.

---

## 2. Authoring Procedure & Guidelines

### Step 1: Writing Messages
Create messages across realistic enterprise and developer channels:
1. **Developer Chat (Slack / Discord / Teams):**
   - Quick questions sharing temporary passwords, tokens, or staging credentials.
   - Code snippets with environment variables or connection strings.
2. **Version Control & CI/CD (GitHub / GitLab):**
   - Git commit messages with accidental tokens.
   - PR review comments citing configuration secrets.
   - Bug reports containing unmasked stack traces.
3. **Indian Banking & Identity Scenarios:**
   - Client messages sharing Aadhaar or PAN details for KYC.
   - Payment transfer requests with domestic bank account numbers and IFSC codes.
4. **Hard Negatives & Decoys:**
   - Benign discussions about security policies.
   - Documentation snippets with `<PLACEHOLDER>` tokens or `user@example.com`.
   - Order IDs, package tracking numbers, software version tags (`v2.4.1`), UUIDs, and git commit hashes.

### Step 2: Format and Schema
Save completed messages to `data/challenge/challenge_set.jsonl`. Every row must be a valid JSON object matching the LEAKGUARD schema:

```json
{
  "id": "challenge_001",
  "text": "Hey Amit, can you verify this client KYC? PAN: ABCDE1234F for candidate Sunita Sharma.",
  "entities": [
    {
      "start": 51,
      "end": 61,
      "label": "PAN",
      "value": "ABCDE1234F"
    },
    {
      "start": 76,
      "end": 89,
      "label": "PERSON",
      "value": "Sunita Sharma"
    }
  ],
  "message_label": "possible_exposure",
  "author": "human_curator",
  "notes": "KYC review message with PAN and personal name"
}
```

### Step 3: Verification
Run the dataset validator to confirm schema conformance and exact character-offset alignment:

```bash
python -c "
import json
from leakguard.data.validate import validate_record
with open('data/challenge/challenge_set.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        errs = validate_record(json.loads(line))
        if errs:
            print(f'Validation error: {errs}')
"
```

---

## 3. Class Balance Recommendations

For the 150–300 messages, aim for an approximate balance:
- ~35% `high_risk_exposure` (active credentials, database strings, private keys, payment cards)
- ~35% `possible_exposure` (personal contact information, KYC identity documents, bank accounts)
- ~30% `no_exposure` (hard negatives, documentation examples, safe placeholders, benign conversations)
