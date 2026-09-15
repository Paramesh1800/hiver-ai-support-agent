# @AppleSupport AI Customer Support Agent & Evaluation System
**Hiver SDE Take-Home Assignment — Production-Grade Support Pipeline & Non-Synthetic Evaluation Harness**

An end-to-end AI Customer Support Agent, Retrieval Engine, and Evaluation Harness built for @AppleSupport using authentic Twitter customer support data from Kaggle (	houghtvector/customer-support-on-twitter).

---

## ⚡ Quick Start Guide (Reproduce Benchmark Results)

### Prerequisites
- Python 3.9+ (Tested on Python 3.11 / 3.14)
- Windows, macOS, or Linux

### Step 1: Clone Repository & Install Dependencies
`ash
git clone https://github.com/Paramesh1800/hiver-ai-support-agent.git
cd Hiver
pip install -r requirements.txt
`

### Step 2: Set Environment Variables (Optional)
`ash
cp .env.example .env
`
*(Note: Evaluation harness runs completely offline and free using pre-cached prompt-hash responses in .cache/).*

### Step 3: Run Full Benchmark Evaluation Harness
`ash
python -m src.evaluate
`

- **Expected Runtime**: < 10 seconds
- **Approximate API Cost**: .00 (all LLM and Judge calls are pre-cached in .cache/)

---

## 📊 Headline Benchmark Results

Evaluated across the **200 hand-labelled Golden Test Examples** (100% strictly excluded from training/retrieval index):

| System Pipeline | Primary Metric (Intent Macro-F1) | Intent Accuracy | **ESCALATE Recall** | ESCALATE F1 | LLM Judge Rubric (1-5) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Trivial Baseline** | **15.6%** | 87.5% | **0.0%** | 0.0% | **2.75 / 5.0** |
| **Simple Baseline (TF-IDF + Cosine)** | **58.2%** | 96.0% | **60.0%** | 35.3% | **4.45 / 5.0** |
| **Main LLM Agent (Grounded + Guardrails)** | **89.1%** | **98.5%** | **100.0%** | **83.3%** | **5.00 / 5.0** |

All benchmark metrics are saved to [
esults/metrics.json](file:///c:/Users/ELCOT/Desktop/Projects/Hiver/results/metrics.json).

---

## 🛠️ Reproduction & Evaluation Scripts Reference

All scripts support interactive terminal workflows, crash resilience, single-item incremental saving, and resumability.

### 1. Interactive Golden Set Intent Tagging CLI
Manually label intent categories and action routing for golden set tweets:
`ash
python -m scripts.label_helper
`
*(Saves incrementally to data/golden/golden_set_labelled.json after every single entry).*

### 2. Live Terminal Blinded Human Reply Scoring CLI
Manually score candidate replies across 4 rubric axes (Groundedness, Correctness, Tone Fit, Actionability) on a 1–5 scale:
`ash
python -m scripts.score_replies
`
*(Saves incrementally to 
esults/human_scores.json after every single entry).*

### 3. Human vs. LLM Judge Agreement Calculator
Compute Quadratic Weighted Cohen's Kappa ($) and Spearman correlation ($) between human scores and LLM judge scores:
`ash
python -m scripts.compute_agreement
`
- **Real Human Evaluation Sample**:  = 50$ items
- **Quadratic Weighted Cohen's Kappa**:  = 0.0423$
- **Spearman Correlation**:  = -0.0882$
- **Sanity Guardrail**: Automatically prints a warning if  > 0.95$ to detect programmatically generated scores.

### 4. Failure Mode Analyzer
Extract top verbatim error modes from the 200-item golden set run:
`ash
python -m scripts.failure_analysis
`
*(Saves error clusters to 
esults/failure_analysis.json).*

---

## 🏗️ Architecture & Key Components

### 1. Intent Taxonomy (6 Categories)
- ACCOUNT_SECURITY: Password reset, 2FA lockout, Apple ID security alert (iforgot.apple.com).
- BILLING_SUBSCRIPTIONS: Card charge dispute, unexpected App Store subscription (
eportaproblem.apple.com).
- HARDWARE_REPAIR: Battery drain, cracked screen, AirPods static/charging case issue.
- SOFTWARE_UPDATE_BUG: iOS/macOS update freeze, storage calculation bug, app crash.
- DEVICE_TRADEIN_SHIPPING: Order tracking delay, trade-in kit return shipping.
- OTHER_GENERAL: General setup questions, Move to iOS app, store hours.

### 2. Safety & Action Routing
- AUTO_HANDLE: Provide grounded Apple KB links for self-service resolution.
- ESCALATE: Mandatory routing to private DM / security portal for PII, account credentials, and billing disputes.

### 3. Blinded 4-Axis LLM-as-a-Judge
- **Rubric Axes**: Groundedness, Correctness, Tone Fit, Actionability (1-5 scale).
- **Blinded System Identity**: Model cannot distinguish LLM draft replies from baseline canned replies.
- **3-Run Variance Tracking**: Evaluates each item 3 times with 	emperature=0 to track variance.

---

## 📁 Repository Structure

`	ext
Hiver/
├── README.md                   # Quick start & reproduction guide
├── requirements.txt            # Pinned dependencies
├── .env.example                # Sample environment file
├── CREDITS.md                  # Dataset and library citations
├── .gitignore                  # Excludes raw data & cache
│
├── data/
│   ├── raw/                    # Raw Kaggle twcs.csv (gitignored)
│   ├── subsample/              # Authentic AppleSupport subsample (3,646 threads, committed)
│   └── golden/                 # 200 Hand-labelled Golden Evaluation Set (committed)
│       ├── LABELLING_GUIDE.md  # Human annotation rules & guidelines
│       ├── golden_set_unlabelled.csv
│       └── golden_set_labelled.json
│
├── src/
│   ├── config.py               # Cross-platform pathlib.Path paths & RANDOM_SEED=42
│   ├── data_prep.py            # Kaggle CSV cleaner & thread reconstructor
│   ├── agent.py                # Main LLM Support Agent with retrieval grounding
│   ├── baselines.py            # Trivial & Simple (TF-IDF + Cosine Retrieval) baselines
│   ├── judge.py                # LLM-as-a-Judge (4 rubric axes, blinded, 3-run variance)
│   └── evaluate.py             # Evaluation harness & benchmark runner
│
├── scripts/
│   ├── build_golden_set.py     # Stratified golden set sampler
│   ├── label_helper.py         # Interactive CLI labeller
│   ├── score_replies.py        # Live terminal human rubric scorer
│   ├── compute_agreement.py    # Quadratic weighted Cohen's Kappa calculator & sanity guardrail
│   └── failure_analysis.py     # Top 5 failure mode cluster extractor
│
├── results/
│   ├── metrics.json            # Complete metric JSON output
│   ├── human_scores.json       # Live human scores (50 items x 4 axes)
│   ├── judge_human_agreement.json # Cohen's kappa (k = 0.0423) output
│   └── failure_analysis.json   # Verbatim error clusters
│
└── report/
    ├── REPORT.md               # Complete technical evaluation report & critique
    └── DECISION_LOG.md         # 12 Non-obvious architecture decisions
`

---

## 📄 Complete Technical Documentation

- Read the full technical evaluation report: [
eport/REPORT.md](file:///c:/Users/ELCOT/Desktop/Projects/Hiver/report/REPORT.md)
- Read the 12 non-obvious architecture decisions: [
eport/DECISION_LOG.md](file:///c:/Users/ELCOT/Desktop/Projects/Hiver/report/DECISION_LOG.md)
- Read the annotation guidelines: [data/golden/LABELLING_GUIDE.md](file:///c:/Users/ELCOT/Desktop/Projects/Hiver/data/golden/LABELLING_GUIDE.md)
