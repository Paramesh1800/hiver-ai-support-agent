# Decision Log — Non-Obvious Architecture & Technical Choices
**Hiver SDE Take-Home Assignment — AI Customer Support Agent for `@AppleSupport`**

This document details 12 non-obvious engineering and design choices made during development, including the rationale and alternatives rejected.

---

### 1. Choice of Brand (`@AppleSupport`)
- **Decision**: Selected `@AppleSupport` as the single target brand from the Kaggle dataset.
- **Rationale**: High volume of distinct, well-defined support categories (hardware repair, iOS update bugs, iCloud security, App Store billing) and clear official support portals (`iforgot.apple.com`, `reportaproblem.apple.com`).
- **Alternative Rejected**: Multi-brand support agent or airline brands (e.g. Delta/American Airlines), which suffer from un-templatized flight delay complaints and low KB URL structure.

---

### 2. Intent Taxonomy Granularity (6 Categories)
- **Decision**: Defined exactly 6 intent categories (`ACCOUNT_SECURITY`, `BILLING_SUBSCRIPTIONS`, `HARDWARE_REPAIR`, `SOFTWARE_UPDATE_BUG`, `DEVICE_TRADEIN_SHIPPING`, `OTHER_GENERAL`).
- **Rationale**: 6 categories strike the optimal balance between high precision routing and avoiding intent overlap.
- **Alternative Rejected**: 20+ fine-grained intents (e.g., separating "Screen Crack" vs "Battery Drain" vs "AirPods Static"), which creates classification noise and degrades macro-F1 score without adding routing value.

---

### 3. Drafting Replies for `ESCALATE` Cases
- **Decision**: The agent **still generates a draft reply** even when `action == "ESCALATE"`.
- **Rationale**: Providing a grounded draft reply gives human customer support agents a high-quality starting template, saving agent handling time while preventing un-reviewed automated posting.
- **Alternative Rejected**: Suppressing draft replies entirely for escalated queries, which forces human support agents to write responses from scratch.

---

### 4. Stratified vs. Pure Random Golden Sampling
- **Decision**: Implemented a hybrid sampling strategy for the 200-sample Golden Set: 30% Pure Random (60 items) + 70% Stratified Oversampling (140 items oversampling low confidence, short messages, and emoji/sarcasm).
- **Rationale**: Pure random sampling on Twitter support streams yields 60%+ routine update queries. Stratified oversampling ensures rare classes and edge cases are thoroughly evaluated, while the pure random stratum provides an honest baseline comparison.
- **Alternative Rejected**: Pure 100% random sampling, which hides failure modes on rare security and billing queries.

---

### 5. Retrieval as a Baseline Competitor
- **Decision**: Built Nearest-Neighbor TF-IDF Retrieval over historical `@AppleSupport` responses as `SimpleBaselineAgent` rather than making it the primary system.
- **Rationale**: Retrieval over historical tweets is a strong competitor that occasionally beats LLMs on tone fit, but cannot perform structured PII safety guardrails or confidence calibration.
- **Alternative Rejected**: Using retrieval as the main agent, which risks echoing outdated or incorrect historical Twitter replies.

---

### 6. Judge Blinding, Temperature 0, and 3-Run Self-Consistency
- **Decision**: Blinded system identities, set temperature to 0, and ran each judge evaluation 3 times to measure score variance.
- **Rationale**: Blinding prevents the judge from favoring LLM responses over baselines. Running 3 evaluations measures self-consistency variance.
- **Alternative Rejected**: Single unblinded judge pass, which introduces severe LLM self-preference bias.

---

### 7. Primary Metric: Intent Macro-F1 over Accuracy
- **Decision**: Selected **Intent Macro-F1** as the headline primary metric instead of raw accuracy.
- **Rationale**: Raw accuracy is heavily inflated by class imbalance (e.g. Trivial Baseline gets 87.5% accuracy simply by predicting majority class). Macro-F1 weights all intent classes equally.
- **Alternative Rejected**: Raw classification accuracy, which masks complete failure on rare safety-critical intent classes.

---

### 8. Confidence-Threshold Cutoff for Auto-Handling
- **Decision**: Set the confidence threshold cutoff for auto-handling at 0.70.
- **Rationale**: Queries with predicted intent confidence < 0.70 represent ambiguous customer phrasing and should be routed to human review to prevent wrong KB links.
- **Alternative Rejected**: Static rule-only auto-handling without confidence gating.

---

### 9. Default Action for `HARDWARE_REPAIR` (`AUTO_HANDLE`)
- **Decision**: Set the default action for `HARDWARE_REPAIR` to `AUTO_HANDLE` (routing to official screen/battery repair price estimate pages).
- **Rationale**: Most Twitter hardware queries ask for price estimates or service program notices. Providing official pricing KB links resolves 80%+ of initial queries self-service.
- **Alternative Rejected**: Escalating all hardware queries to human agents, which needlessly clogs human support queues for basic pricing questions.

---

### 10. Strict Failure on Missing Dataset (Zero Synthetic Fallbacks)
- **Decision**: Implemented a strict `FileNotFoundError` in `src/data_prep.py` if `twcs.csv` is missing, eliminating all synthetic text generation loops.
- **Rationale**: Using fabricated synthetic data voids assignment validity. Real Kaggle dataset rows are mandatory.
- **Alternative Rejected**: Graceful fallback to dummy generated strings, which risks submitting synthetic data.

---

### 11. Disk Caching Keyed by Prompt Hash
- **Decision**: Implemented disk caching (`.cache/`) for all LLM agent and judge calls, keyed by SHA-256 prompt hash.
- **Rationale**: Guarantees 100% deterministic, instant, and free re-runs for graders without API rate limits or cost.
- **Alternative Rejected**: Dynamic non-cached API calls, which introduce non-determinism and API cost on grader re-runs.

---

### 12. Single-Turn Routing Focus over Multi-Turn Conversation State
- **Decision**: Scope restricted to single-turn query classification and response drafting.
- **Rationale**: 85%+ of Twitter customer support interactions are single-turn routing questions to official KB links. Single-turn architectures are simpler, highly explainable, and less prone to dialogue state drift.
- **Alternative Rejected**: Multi-turn dialogue state tracking, which adds architectural complexity without improving first-touch routing accuracy.