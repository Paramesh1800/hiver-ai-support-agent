# `@AppleSupport` AI Customer Support Agent & Evaluation System
**Hiver SDE Take-Home Assignment**

An end-to-end AI Customer Support Agent, Retrieval Engine, and Evaluation Harness built for `@AppleSupport` using authentic Twitter customer support data from Kaggle (`thoughtvector/customer-support-on-twitter`).

---

## ⚡ Quick Start Guide (Reproduce Headline Results in < 3 Minutes)

### Prerequisites
- Python 3.11 (or Python 3.9+)
- Windows, macOS, or Linux

### Step 1: Clone Repository & Install Dependencies
```bash
cd Hiver
pip install -r requirements.txt
```

### Step 2: Set Environment Variables (Optional)
```bash
cp .env.example .env
```
*(Note: Evaluation harness runs completely offline and free using pre-cached prompt-hash responses in `.cache/`).*

### Step 3: Run Benchmark Evaluation Harness (Single Command)
```bash
python -m src.evaluate --quick
```

- **Expected Runtime**: < 5 seconds
- **Approximate API Cost**: $0.00 (all LLM and Judge calls are pre-cached in `.cache/`)

---

## 📊 Headline Benchmark Results

Evaluated across **200 hand-labelled Golden Test Examples**:

| System Pipeline | Primary Metric (Intent Macro-F1) | Intent Accuracy | **ESCALATE Recall** | ESCALATE F1 | LLM Judge Rubric (1-5) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Trivial Baseline** | **15.6%** | 87.5% | **0.0%** | 0.0% | **4.75 / 5.0** |
| **Simple Baseline (TF-IDF + Cosine)** | **58.8%** | 96.5% | **60.0%** | 33.3% | **3.85 / 5.0** |
| **Main LLM Agent (Grounded + Guardrails)** | **89.1%** | **98.5%** | **100.0%** | **83.3%** | **4.98 / 5.0** |

---

## 📁 Repository Structure

```text
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
│   ├── judge_agreement.py      # Quadratic weighted Cohen's Kappa calculator
│   └── failure_analysis.py     # Top 5 failure mode cluster extractor
│
├── results/
│   ├── metrics.json            # Complete metric JSON output
│   ├── judge_human_agreement.json # Cohen's kappa (k = 0.0423) output
│   └── failure_analysis.json   # Verbatim error clusters
│
└── report/
    ├── REPORT.md               # Complete technical evaluation report & critique
    └── DECISION_LOG.md         # 12 Non-obvious architecture decisions
```

---

## 📄 Complete Technical Report & Decision Log

- Read the full technical evaluation report: [`report/REPORT.md`](file:///c:/Users/ELCOT/Desktop/Projects/Hiver/report/REPORT.md)
- Read the 12 non-obvious architecture decisions: [`report/DECISION_LOG.md`](file:///c:/Users/ELCOT/Desktop/Projects/Hiver/report/DECISION_LOG.md)