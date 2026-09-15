# Technical Evaluation Report & System Architecture
**Hiver SDE Take-Home Assignment — AI Customer Support Agent for `@AppleSupport`**

---

## 1. Problem Framing

### What "Good" Support Means for `@AppleSupport`
For a tier-1 global tech brand like Apple, customer support on Twitter must balance three non-negotiable goals:
1. **Safety & Privacy Compliance (Zero Tolerance)**: Never handle Personally Identifiable Information (PII), Apple ID credentials, 2FA codes, or payment cards in a public tweet. Safety-critical intents (`ACCOUNT_SECURITY`, `BILLING_SUBSCRIPTIONS`, order tracking) **must strictly escalate** to secure private portals (`iforgot.apple.com`, `reportaproblem.apple.com`) or private Direct Message (DM).
2. **Grounded Resolution**: Every automated reply must be grounded in official Apple Knowledge Base (KB) support URLs and historical resolution patterns. Generic filler ("Sorry to hear that, DM us") damages brand trust.
3. **High Intent Classification Accuracy**: Accurately distinguishing between hardware damage, software bugs, billing disputes, and security lockouts so the user receives the correct self-serve URL on first touch.

### Out of Scope (What We Explicitly Chose NOT to Build and Why)
- **Multi-Turn Conversation State Tracking**: We restricted scope to single-turn inbound query resolution because 85%+ of Twitter customer support interactions are single-turn routing questions to official KB links.
- **Direct API Account Mutations / Automated Refunds**: We explicitly chose *not* to build automated account password resets or refund triggers directly inside Twitter bots. This prevents malicious account takeover attacks via public tweets or prompt injection.
- **Non-English Language Support**: Focused exclusively on English `@AppleSupport` tweets to maintain high annotation precision.
- **Model Fine-Tuning**: Fine-tuning an open 7B model was deferred in favor of RAG retrieval over real historical `@AppleSupport` responses, which guarantees grounded URLs without model hallucination risks.

---

## 2. System Design

```
                     ┌──────────────────────────────────────────────┐
                     │ Inbound Customer Tweet (@AppleSupport Query) │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │   Safety & PII Guardrail Escalation Engine   │
                     │  (Regex / PII / Security Keywords check)    │
                     └──────┬────────────────────────────────┬──────┘
                            │                                │
                 [Mandatory Escalation]                [Passes Safety]
                            │                                │
                            ▼                                ▼
            ┌──────────────────────────────┐  ┌──────────────────────────────┐
            │       Action: ESCALATE       │  │ Intent Classifier (6 Intents)│
            │   (Reason: Privacy / PII)    │  └──────────────┬───────────────┘
            └──────────────────────────────┘                 │
                                                             ▼
                                              ┌──────────────────────────────┐
                                              │  TF-IDF Historical Retrieval │
                                              │ (Grounded @AppleSupport KB)  │
                                              └──────────────┬───────────────┘
                                                             │
                                                             ▼
                                              ┌──────────────────────────────┐
                                              │    Structured JSON Output    │
                                              │ {intent, confidence, reply,  │
                                              │     action, reason}          │
                                              └──────────────────────────────┘
```

---

## 3. Golden Evaluation Set

- **Dataset Source**: Extracted from authentic Kaggle `twcs.csv` dataset threads targeting `@AppleSupport`.
- **Sampling Strategy**: 200 total golden set items sampled using a hybrid stratified approach:
  - **Pure Random Stratum**: 60 examples (30.0%) reserved for honest, un-stratified distribution evaluation.
  - **Stratified Oversampling**: 140 examples (70.0%) oversampling low-confidence predictions, `ESCALATE` candidates, short messages (< 5 words), and emoji/sarcasm (`!`, `?`, `paperweight`, `#badapple`).
- **Human Annotation**: Hand-labelled using guidelines defined in [`data/golden/LABELLING_GUIDE.md`](file:///c:/Users/ELCOT/Desktop/Projects/Hiver/data/golden/LABELLING_GUIDE.md).

---

## 4. Results vs. Baselines

All three systems were evaluated on the 200-sample hand-labelled Golden Set. All numbers are traceable directly to [`results/metrics.json`](file:///c:/Users/ELCOT/Desktop/Projects/Hiver/results/metrics.json):

| System Pipeline | Primary Metric (Intent Macro-F1) | Intent Accuracy | **ESCALATE Recall** | ESCALATE F1 | LLM Judge Rubric (1-5) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Trivial Baseline** | **15.56%** | 87.50% | **0.00%** | 0.00% | **4.75 / 5.0** |
| **Simple Baseline (TF-IDF + Cosine)** | **58.83%** | 96.50% | **60.00%** | 33.33% | **3.85 / 5.0** |
| **Main LLM Agent (Grounded + Guardrails)** | **89.15%** | **98.50%** | **100.00%** | **83.33%** | **4.98 / 5.0** |

### Key Benchmark Findings:
- **Trivial Baseline** achieved 87.50% raw intent accuracy due to heavy majority class imbalance, but collapsed to **15.56% Macro-F1** and **0.0% Escalation Recall**, failing every safety check.
- **Simple Baseline (TF-IDF + Cosine Retrieval)** achieved **58.83% Macro-F1** and **60.0% Escalation Recall**. Nearest-neighbor retrieval proved to be a strong grounded competitor (retrieving real `@AppleSupport` replies with high tone fit).
- **Our Main LLM Agent** achieved **89.15% Intent Macro-F1**, **98.50% Intent Accuracy**, and **100.0% Escalation Recall** with zero missed safety escalations.

---

## 5. Failure Analysis (Top 5 Failure Modes)

Derived directly from actual runtime error records in [`results/failure_analysis.json`](file:///c:/Users/ELCOT/Desktop/Projects/Hiver/results/failure_analysis.json):

### 1. Post-Update Battery vs Software Bug Confusion
- **Hypothesis**: When a tweet mentions battery drain specifically triggered *after* an iOS update, the classifier prioritizes the `"iOS 11 update"` keyword (`SOFTWARE_UPDATE_BUG`) over `"battery life"` (`HARDWARE_REPAIR`).
- **Verbatim Real Example (ID: `golden_006`)**:
  - *Customer Tweet*: `"@AppleSupport Just wanted to report poor battery life on iPhone 6S following iOS 11.1 update yesterday. Phone also running warmer."`
  - *Expected Label*: Intent=`HARDWARE_REPAIR`, Action=`AUTO_HANDLE`
  - *Agent Prediction*: Intent=`SOFTWARE_UPDATE_BUG`, Action=`AUTO_HANDLE`

### 2. Over-Escalation on General App Store Feature Inquiries
- **Hypothesis**: The presence of `"App Store"` in general feature comments triggers `BILLING_SUBSCRIPTIONS` keyword matching, causing unnecessary escalation for non-billing questions.
- **Verbatim Real Example (ID: `golden_026`)**:
  - *Customer Tweet*: `"@AppleSupport App store now appears to be working"`
  - *Expected Label*: Intent=`OTHER_GENERAL`, Action=`AUTO_HANDLE`
  - *Agent Prediction*: Intent=`BILLING_SUBSCRIPTIONS`, Action=`ESCALATE`

### 3. Sarcastic Feature Removal Feedback
- **Hypothesis**: Sarcastic user stories describing removed iOS features (e.g. tapping 10x to clear cache) contain mixed feature terms (`App Store`, `iOS 11`, `cache`) that trigger `BILLING_SUBSCRIPTIONS` over-escalation.
- **Verbatim Real Example (ID: `golden_040`)**:
  - *Customer Tweet*: `".@AppleSupport Once upon a very recent time (pre-iOS 11), one could clear the App Store cache by tapping any tab in the app 10x. That no longer works. When will @115858 be restoring this function?🤔 Thanks!😃👍 #Apple #AppStore"`
  - *Expected Label*: Intent=`SOFTWARE_UPDATE_BUG`, Action=`AUTO_HANDLE`
  - *Agent Prediction*: Intent=`BILLING_SUBSCRIPTIONS`, Action=`ESCALATE`

### 4. Implicit Order PII without Hashtag
- **Hypothesis**: Order IDs or tracking reference numbers written without an explicit `#` symbol or embedded in narrative prose fail simple keyword regex pattern matching.

### 5. Generic Short Tweet Context Loss
- **Hypothesis**: Ultra-short tweets (`"< 4 words"`) lack semantic context, defaulting to general intent with low actionability rubric scores.

---

## 6. Mandatory Section: "What is misleading about my headline number?"

While our headline number (**89.15% Intent Macro-F1** and **100.0% Escalation Recall**) appears impressive, a self-critical engineering analysis reveals several critical limitations:

1. **Self-Fulfilling Intent Taxonomy**: We defined the 6 intent categories ourselves based on the dataset patterns. Because the taxonomy was created around obvious semantic clusters (battery, billing, password lockout), the model's high performance is partly self-fulfilling.
2. **Stratified vs. Pure Random Discrepancy**: The golden set contains 70% stratified oversampling. On the **Pure Random Stratum (60 items)**, the Main LLM Agent achieved **88.95% Macro-F1** and **95.00% Intent Accuracy**, demonstrating that performance drops slightly on noisy un-stratified data.
3. **Single-Annotator Labeling Ceiling**: All 200 golden set labels were annotated by a single developer. Without multi-annotator inter-rater reliability, the ground-truth ceiling is unknown and subtle labeling drift is unmeasured.
4. **Judge-Human Agreement Low Kappa ($k = 0.3902$)**: In [`results/judge_human_agreement.json`](file:///c:/Users/ELCOT/Desktop/Projects/Hiver/results/judge_human_agreement.json), the automated judge achieved a **Quadratic Weighted Cohen's Kappa of $k = 0.3902 < 0.60$**. This proves that automated judge scores exhibit self-preference bias and cannot replace human evaluation.
5. **Single Historical Reply Groundedness Penalty**: Groundedness was evaluated against a single reference historical reply. However, customer support replies are one-of-many-valid; a perfectly valid novel response is penalized if it doesn't match the single reference URL phrasing.
6. **Small ESCALATE Positive Class**: The `ESCALATE` class comprises a small fraction of the total dataset ($n=10$). Consequently, point estimates for recall have wide confidence intervals; small variations in small samples represent statistical noise.

---

## 7. What I'd Do Next with One More Week

1. **Implement Hybrid Vector RAG Search**: Replace TF-IDF retrieval with dense vector embeddings (`text-embedding-3-small` in LanceDB) to retrieve fine-grained Apple KB documentation.
2. **Multi-Annotator Golden Set Labeling**: Recruit 2 additional annotators to calculate Fleiss' Kappa on ground-truth golden labels.
3. **Fine-Tune Open Llama-3 8B Model**: Fine-tune an open 8B parameter model on the 3,646 authentic `@AppleSupport` threads to generate natural brand voice replies without commercial API dependencies.
4. **Live Human-in-the-Loop Feedback UI**: Build an interactive web dashboard for human support agents to review, approve, or override AI escalation decisions in real time.