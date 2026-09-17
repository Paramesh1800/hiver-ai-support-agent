# @AppleSupport AI Customer Support Agent & Evaluation System
**Hiver SDE Take-Home Assignment — Production-Grade Support Pipeline & Non-Synthetic Evaluation Harness**

An end-to-end AI Customer Support Agent, Retrieval Engine, and Evaluation Harness built for @AppleSupport using authentic Twitter customer support data from Kaggle (`thoughtvector/customer-support-on-twitter`).

---

## ⚡ Quick Start Guide (Reproduce Benchmark Results)

### Prerequisites
- Python 3.9+ (Tested on Python 3.11 / 3.14)
- Windows, macOS, or Linux

### Step 1: Clone Repository & Install Dependencies
```bash
git clone https://github.com/Paramesh1800/hiver-ai-support-agent.git
cd Hiver
pip install -r requirements.txt
```

### Step 2: Set Environment Variables (Optional)
```bash
cp .env.example .env
```
*(Note: Evaluation harness runs completely offline and free using pre-cached prompt-hash responses in .cache/).*

### Step 3: Run Full Benchmark Evaluation Harness
```bash
python -m src.evaluate
```

- **Expected Runtime**: < 10 seconds
- **Approximate API Cost**: $0.00 (all LLM and Judge calls are pre-cached in `.cache/`)

---

## 📊 Headline Benchmark Results

Evaluated across the **200 hand-labelled Golden Test Examples** (100% strictly excluded from training/retrieval index):

| System Pipeline | Primary Metric (Intent Macro-F1) | Intent Accuracy | **ESCALATE Recall** | ESCALATE F1 | LLM Judge Rubric (1-5) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Trivial Baseline** | **15.6%** | 87.5% | **0.0%** | 0.0% | **2.75 / 5.0** |
| **Simple Baseline (TF-IDF + Cosine)** | **58.2%** | 96.0% | **60.0%** | 35.3% | **4.45 / 5.0** |
| **Main LLM Agent (Grounded + Guardrails)** | **89.1%** | **98.5%** | **100.0%** | **83.3%** | **5.00 / 5.0** |

All benchmark metrics are saved to [`results/metrics.json`](file:///c:/Users/ELCOT/Desktop/Projects/Hiver/results/metrics.json).

---

## 🛠️ Reproduction & Evaluation Scripts Reference

All scripts support interactive terminal workflows, crash resilience, single-item incremental saving, and resumability.

### 1. Interactive Golden Set Intent Tagging CLI
Manually label intent categories and action routing for golden set tweets:
```bash
python -m scripts.label_helper
```
*(Saves incrementally to `data/golden/golden_set_labelled.json` after every single entry).*

### 2. Live Terminal Blinded Human Reply Scoring CLI
Manually score candidate replies across 4 rubric axes (Groundedness, Correctness, Tone Fit, Actionability) on a 1–5 scale:
```bash
python -m scripts.score_replies
```
*(Saves incrementally to [`results/human_scores.json`](file:///c:/Users/ELCOT/Desktop/Projects/Hiver/results/human_scores.json) after every single entry).*

### 3. Human vs. LLM Judge Agreement Calculator
Compute Quadratic Weighted Cohen's Kappa ($\kappa$) and Spearman correlation ($\rho$) between human scores and LLM judge scores:
```bash
python -m scripts.compute_agreement
```
- **Real Human Evaluation Sample**: $N = 50$ items
- **Quadratic Weighted Cohen's Kappa**: $\kappa = 0.0423$
- **Spearman Correlation**: $\rho = -0.0882$
- **Sanity Guardrail**: Automatically prints a warning if $\kappa > 0.95$ to detect programmatically generated scores.

### 4. Failure Mode Analyzer
Extract top verbatim error modes from the 200-item golden set run:
```bash
python -m scripts.failure_analysis
```
*(Saves error clusters to [`results/failure_analysis.json`](file:///c:/Users/ELCOT/Desktop/Projects/Hiver/results/failure_analysis.json)).*

---

## 🏗️ Architecture & Key Components

### 1. Intent Taxonomy (6 Categories)
- **ACCOUNT_SECURITY**: Password reset, 2FA lockout, Apple ID security alert (`iforgot.apple.com`).
- **BILLING_SUBSCRIPTIONS**: Card charge dispute, unexpected App Store subscription (`reportaproblem.apple.com`).
- **HARDWARE_REPAIR**: Battery drain, cracked screen, AirPods static/charging case issue.
- **SOFTWARE_UPDATE_BUG**: iOS/macOS update freeze, storage calculation bug, app crash.
- **DEVICE_TRADEIN_SHIPPING**: Order tracking delay, trade-in kit return shipping.
- **OTHER_GENERAL**: General setup questions, Move to iOS app, store hours.

### 2. Safety & Action Routing
- **AUTO_HANDLE**: Provide grounded Apple KB links for self-service resolution.
- **ESCALATE**: Mandatory routing to private DM / security portal for PII, account credentials, and billing disputes.

### 3. Blinded 4-Axis LLM-as-a-Judge
- **Rubric Axes**: Groundedness, Correctness, Tone Fit, Actionability (1-5 scale).
- **Blinded System Identity**: Model cannot distinguish LLM draft replies from baseline canned replies.
- **3-Run Variance Tracking**: Evaluates each item 3 times with `temperature=0` to track variance.

---

## 📁 Repository Structure

```
Hiver/
├── README.md                      # Project overview, quick start & benchmark guide
├── requirements.txt               # Pinned Python dependencies
├── CREDITS.md                     # Dataset & library attributions and citations
├── .env.example                   # Sample environment variable template
├── .gitignore                     # Git ignore configuration
│
├── src/                           # Core pipeline source code
│   ├── config.py                  # Paths, constants, seed & environment setup
│   ├── data_prep.py               # Kaggle CSV cleaner, thread builder & KB chunker
│   ├── agent.py                   # Grounded LLM Agent with guardrails & intent router
│   ├── baselines.py               # Trivial baseline & Simple TF-IDF + Cosine model
│   ├── judge.py                   # Blinded 4-axis LLM-as-a-Judge evaluation engine
│   └── evaluate.py                # Main benchmark evaluation harness runner
│
├── scripts/                       # Reproduction & evaluation workflow scripts
│   ├── build_golden_set.py        # Stratified golden test set sampler
│   ├── label_helper.py            # Interactive CLI for intent labeling
│   ├── score_replies.py           # Terminal-based human rubric scoring CLI
│   ├── compute_agreement.py       # Cohen's Kappa & Spearman correlation calculator
│   ├── judge_agreement.py         # Judge-human agreement computation module
│   └── failure_analysis.py        # Failure mode cluster extraction script
│
├── data/                          # Data directory
│   ├── raw/                       # Raw Kaggle twcs.csv dataset (gitignored)
│   ├── subsample/                 # Reconstructed AppleSupport dataset
│   │   └── apple_support_subsample.json
│   ├── golden/                    # Hand-annotated Golden Evaluation Set
│   │   ├── LABELLING_GUIDE.md     # Taxonomy & annotation guidelines
│   │   ├── golden_set_unlabelled.csv
│   │   └── golden_set_labelled.json
│   ├── apple_support_threads.json # Multi-turn reconstructed threads
│   ├── build_datasets.py         # Dataset preparation script
│   ├── eval_results.json          # Cached evaluation benchmark outputs
│   ├── golden_eval_set.json       # Formatted golden evaluation dataset
│   └── historical_support_kb.json # Grounding Knowledge Base index
│
├── results/                       # Benchmark metrics & outputs
│   ├── metrics.json               # Benchmark metric results across models
│   ├── human_scores.json          # Human rubric scores (50 items)
│   ├── judge_human_agreement.json # Inter-annotator & judge agreement metrics
│   └── failure_analysis.json      # Verbatim error cluster analysis
│
└── report/                        # Technical documentation & decision logs
    ├── REPORT.md                  # Complete technical evaluation report
    └── DECISION_LOG.md            # Architecture & engineering decision logs
```

---

## 📄 Complete Technical Documentation

- Read the full technical evaluation report: [`report/REPORT.md`](file:///c:/Users/ELCOT/Desktop/Projects/Hiver/report/REPORT.md)
- Read the 12 non-obvious architecture decisions: [`report/DECISION_LOG.md`](file:///c:/Users/ELCOT/Desktop/Projects/Hiver/report/DECISION_LOG.md)
- Read the annotation guidelines: [`data/golden/LABELLING_GUIDE.md`](file:///c:/Users/ELCOT/Desktop/Projects/Hiver/data/golden/LABELLING_GUIDE.md)

