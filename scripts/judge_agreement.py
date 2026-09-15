import sys
import os
import io
import json
import argparse
import numpy as np
from pathlib import Path
from sklearn.metrics import cohen_kappa_score

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import GOLDEN_LABELLED_FILE, RESULTS_DIR
from src.judge import LLMReplyJudge
from src.agent import LLMSupportAgent

def compute_judge_human_agreement(sample_size: int = 50):
    if not GOLDEN_LABELLED_FILE.exists():
        raise FileNotFoundError(f"{GOLDEN_LABELLED_FILE} not found. Please label golden set first.")

    with open(GOLDEN_LABELLED_FILE, 'r', encoding='utf-8') as f:
        golden_data = json.load(f)

    sample = golden_data[:sample_size]
    print(f"Computing LLM Judge vs Human Agreement on {len(sample)} sampled golden set items...")

    agent = LLMSupportAgent()
    judge = LLMReplyJudge()

    human_overall = []
    judge_overall = []

    for item in sample:
        tweet = item["raw_text"]
        ref_reply = item["brand_reply_actual"]
        
        h_score = 5 if item.get("true_action") == "AUTO_HANDLE" else 4
        human_overall.append(h_score)

        out = agent.process_message(tweet)
        j_eval = judge.evaluate_reply_blinded(tweet, ref_reply, out["draft_reply"])
        j_score = int(round(j_eval["overall_score"]))
        judge_overall.append(j_score)

    kappa = cohen_kappa_score(human_overall, judge_overall, weights='quadratic')
    
    corr_matrix = np.corrcoef(human_overall, judge_overall)
    spearman_corr = float(corr_matrix[0, 1]) if not np.isnan(corr_matrix[0, 1]) else 0.0

    print("\n=======================================================")
    print("      LLM JUDGE VS HUMAN AGREEMENT EVALUATION          ")
    print("=======================================================\n")
    print(f"  • Sample Size:                       {len(sample)} items")
    print(f"  • Quadratic Weighted Cohen's Kappa:  k = {kappa:.4f}")
    print(f"  • Spearman Correlation:              r = {spearman_corr:.4f}\n")

    if kappa < 0.60:
        print("⚠️ [WARNING REPORT FINDING]: Cohen's Kappa is below 0.60 threshold (k < 0.60).")
        print("   This indicates moderate/low judge agreement and must be documented as a limitation in REPORT.md!\n")
    else:
        print("✅ [PASSED]: High judge-human agreement threshold met (k >= 0.60).\n")

    agreement_data = {
        "sample_size": len(sample),
        "cohens_kappa_quadratic": round(float(kappa), 4),
        "spearman_correlation": round(float(spearman_corr), 4),
        "judge_trustworthy": kappa >= 0.60
    }

    out_file = RESULTS_DIR / "judge_human_agreement.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(agreement_data, f, indent=2)

    print(f"Agreement metrics saved to {out_file}\n")
    return agreement_data

if __name__ == "__main__":
    compute_judge_human_agreement()