# LEAKGUARD Evaluation Methodology & Statistical Framework

**Document Version:** 1.0.0  
**Phase:** 5 (Evaluation and Gated Classifier Experiment)  
**Author:** Antigravity Senior Engineer Agent  
**Context:** LEAKGUARD Rebuild of AI-Data-Leak-Detection  

---

## 1. Overview and Core Philosophy

The LEAKGUARD evaluation methodology adheres to strict security intelligence and empirical testing standards:
1. **Separation of Policy Risk from Syntactic Presence (F-01 / F-02):** Merely finding an entity token does not automatically imply a high-risk leak. Messages with benign documentation domains (`user@example.com`), explicit placeholders (`<API_KEY>`), or software versions (`v2.4.1`) must be evaluated as `no_exposure`.
2. **Leakage-Free Group Splitting:** Splitting data at random across records causes severe template memorization and data leakage. All synthetic data splits are partitioned strictly by `family_id` (60% Train, 20% Validation, 20% Test), ensuring zero shared templates or semantic families between splits.
3. **Dual-Tiered Evaluation:**
   - **Entity-Level:** Exact and relaxed span overlap matching per entity type, micro-average, and macro-average.
   - **Message-Level:** Binary exposure risk categorization, ROC-AUC, PR-AUC, Confusion Matrix, FNR at fixed recall targets, and bootstrap 95% Confidence Intervals.
4. **Empirical Gate for Machine Learning:** To prevent shipping models that merely memorize synthetic templates, a machine learning classifier may **only** be released in v1 if it beats the transparent rule baseline on an independent, human-written challenge benchmark with a 95% confidence interval excluding zero improvement.

---

## 2. Entity-Level Evaluation Standards

### 2.1 Character Offset Grounding
Entity offsets represent 0-indexed half-open intervals `[start, end)` into the unnormalized Unicode input text. Slicing `text[start:end]` strictly recovers the ground truth or predicted substring.

### 2.2 Exact Span Matching
A predicted finding $p$ is deemed a True Positive ($TP$) under **Exact Matching** if and only if:
$$\text{label}(p) = \text{label}(g) \quad \land \quad \text{start}(p) = \text{start}(g) \quad \land \quad \text{end}(p) = \text{end}(g)$$
where $g$ is an unmatched ground truth entity. Each ground truth entity can be matched at most once.

### 2.3 Relaxed Span Matching
A predicted finding $p$ is deemed a True Positive ($TP$) under **Relaxed Matching** if:
$$\text{label}(p) = \text{label}(g) \quad \land \quad \max(\text{start}(p), \text{start}(g)) < \min(\text{end}(p), \text{end}(g))$$
(i.e., non-empty character intersection).

### 2.4 Metrics Computed
For True Positives ($TP$), False Positives ($FP$), and False Negatives ($FN$):
$$\text{Precision} = \frac{TP}{TP + FP}, \quad \text{Recall} = \frac{TP}{TP + FN}$$
$$F_1 = \frac{2 \cdot P \cdot R}{P + R}, \quad F_2 = \frac{5 \cdot P \cdot R}{4 \cdot P + R}$$

$F_2$ is tracked as a primary operational metric because in data leak defense, failing to alert on an active credential or identity leak ($FN$) carries higher operational risk than investigating a false alarm ($FP$).

---

## 3. Message-Level Evaluation & Confidence Intervals

### 3.1 Binary Risk Exposure Definition
For policy evaluation, messages are mapped to binary ground truth:
$$y = \begin{cases} 1 & \text{if } \text{message\_label} \in \{\text{possible\_exposure}, \text{high\_risk\_exposure}\} \\ 0 & \text{if } \text{message\_label} = \text{no\_exposure} \end{cases}$$

### 3.2 Non-Parametric Bootstrap Confidence Intervals
To report statistically rigorous uncertainty without assuming Gaussian distributions, 95% confidence intervals are estimated via non-parametric bootstrap resampling:
- **Resamples:** $B = 1,000$ iterations with replacement.
- **Random Seed:** 42 for exact determinism.
- **Bounds:** Empirical 2.5th and 97.5th percentiles: $[\theta_{0.025}^*, \theta_{0.975}^*]$.

### 3.3 Fixed Recall Thresholding (FNR @ 95% Recall)
In enterprise DLP and security operations, models are frequently operated at fixed high recall targets (e.g., capturing at least 95% of leaks). The False Negative Rate at 95% target recall is computed as:
$$\text{FNR}_{95} = \frac{FN}{TP + FN} \quad \text{at operating threshold } \theta \text{ where } \text{Recall}(\theta) \ge 0.95$$

---

## 4. Machine Learning Experiment Design

### 4.1 Architectures Evaluated
1. **Word N-Gram Pipeline:** `TfidfVectorizer(ngram_range=(1, 2), max_features=10000, sublinear_tf=True)` + `LogisticRegression(class_weight='balanced')`.
2. **Character N-Gram Pipeline:** `TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), max_features=15000, sublinear_tf=True)` + `LogisticRegression(class_weight='balanced')`.

### 4.2 Leakage Prevention Guarantees
- Vectorizer dictionaries and IDF weights are fit **strictly** on the training split fold.
- Inverse regularization strength ($C \in \{0.1, 1.0, 10.0\}$) and decision thresholds ($\theta \in [0.30, 0.70]$) are tuned **strictly** on the validation split fold.
- The held-out test split is evaluated **exactly once** for final reporting.

### 4.3 Human Challenge Gate Policy
A machine learning classifier will **NOT** ship in production if:
1. The human challenge benchmark set is missing or unverified.
2. The ML model fails to demonstrate a statistically significant $F_1$ or $F_2$ improvement over the rule baseline with a 95% bootstrap CI excluding zero difference.

---

## 5. Limitations & Threats to Validity

1. **Synthetic Template Regularity:** While our dataset generator utilizes 15 semantic families, 157 distinct templates, and mathematical checksum algorithms, synthetic sentences inherently exhibit lower grammatical variance and slang than real enterprise chat logs.
2. **Vocabulary Shift on Free-Form Text:** Keyword-dependent ML classifiers trained on synthetic templates risk over-weighting specific template carrier phrases.
3. **Absence of Human Challenge Set:** In Phase 5, the evaluation framework operates on synthetic splits because the independent human challenge set has not yet been authored. Consequently, machine learning models are marked **NOT SHIPPED**, and the Phase 5 gate is explicitly marked **GATE: NOT PASSED** until human benchmark evidence is supplied.
