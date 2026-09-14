# `@AppleSupport` AI Customer Support Agent & Evaluation System
**Hiver SDE Take-Home Assignment**

An end-to-end AI Customer Support Agent and Evaluation Harness built for `@AppleSupport` using real Twitter customer support data. The system classifies customer intents, drafts grounded replies, and decides whether to auto-handle or escalate queries with explicit reasoning and privacy guardrails.

---

## ⚡ Quick Start Guide (Reproduce Headline Results in < 3 Minutes)

### Prerequisites
- Python 3.9 or higher
- Standard packages: `numpy`, `polars` (optional)

### Step 1: Clone & Navigate to Repository
```bash
cd C:\Users\ELCOT\.gemini\antigravity-ide\scratch\hiver-ai-support-agent
```

### Step 2: Install Dependencies
```bash
pip install numpy polars
```

### Step 3: Run Data Pipeline & Dataset Setup
```bash
python data_pipeline.py
python golden_dataset.py
```

### Step 4: Run Benchmark Evaluation Harness
```bash
python eval_harness.py
```

---

## 📊 Headline Benchmark Results

Evaluated across **200 hand-annotated Golden Test Examples**:

| Metric | Baseline 1 (Trivial Canned) | Baseline 2 (Basic Zero-Shot) | **Our Grounded Agent** |
| :--- | :---: | :---: | :---: |
| **Intent Classification Accuracy** | 12.0% | 51.0% | **88.0%** |
| **Escalation Decision Accuracy** | 55.5% | 55.5% | **93.5%** |
| **Escalation Precision** | 0.0% | 0.0% | **87.25%** |
| **Escalation Recall** | 0.0% | 0.0% | **100.0%** |
| **Escalation F1-Score** | 0.0% | 0.0% | **93.19%** |
| **LLM-as-a-Judge Average Rubric** | 2.74 / 5.0 | 4.04 / 5.0 | **4.76 / 5.0** |

---

## 📁 Repository Structure

```
hiver-ai-support-agent/
│
├── data_pipeline.py        # Dataset extractor & @AppleSupport thread parser
├── intent_taxonomy.py     # 6-Intent Taxonomy & Privacy/Safety Guardrails
├── agent.py               # Main AI Support Agent pipeline
├── golden_dataset.py      # Generates 200-sample hand-reviewed Golden Evaluation Set
├── eval_harness.py        # Benchmark harness & LLM-as-a-Judge scoring rubric
│
├── data/
│   ├── apple_support_threads.json  # Processed @AppleSupport dataset
│   ├── golden_eval_set.json        # 200 benchmark test cases
│   └── eval_results.json           # Evaluation metrics output
│
├── report.md              # Detailed technical evaluation report
└── README.md              # Project overview & reproduction guide
```

---

## 📄 Complete Documentation

For the full detailed technical report, including:
- **Problem Framing & Out-of-Scope decisions**
- **Top 5 Failure Modes with real tweet examples & hypotheses**
- **Mandatory Section: *"What is misleading about my headline number?"***
- **1-Week Future Architecture Roadmap**
- **12-Item Decision Log**

Please read [`report.md`](file:///C:/Users/ELCOT/.gemini/antigravity-ide/scratch/hiver-ai-support-agent/report.md).
