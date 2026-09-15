import sys
import os
import io
import json
import argparse
from pathlib import Path

# Wrap stdout in UTF-8 for Windows console support
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score, accuracy_score, confusion_matrix

from src.config import (
    GOLDEN_LABELLED_FILE,
    METRICS_JSON_FILE,
    RESULTS_DIR
)
from src.baselines import TrivialBaselineAgent, SimpleBaselineAgent
from src.agent import LLMSupportAgent
from src.judge import LLMReplyJudge

def compute_metrics(y_true_intent, y_pred_intent, y_true_action, y_pred_action):
    """Computes intent macro-F1, accuracy, and action ESCALATE precision, recall, F1."""
    intent_acc = accuracy_score(y_true_intent, y_pred_intent)
    intent_macro_f1 = f1_score(y_true_intent, y_pred_intent, average='macro', zero_division=0)
    
    # Action metrics with ESCALATE as positive class
    action_acc = accuracy_score(y_true_action, y_pred_action)
    action_precision = precision_score(y_true_action, y_pred_action, pos_label='ESCALATE', zero_division=0)
    action_recall = recall_score(y_true_action, y_pred_action, pos_label='ESCALATE', zero_division=0)
    action_f1 = f1_score(y_true_action, y_pred_action, pos_label='ESCALATE', zero_division=0)

    return {
        "intent_macro_f1": round(float(intent_macro_f1), 4),
        "intent_accuracy": round(float(intent_acc), 4),
        "action_escalate_recall": round(float(action_recall), 4),
        "action_escalate_precision": round(float(action_precision), 4),
        "action_escalate_f1": round(float(action_f1), 4),
        "action_accuracy": round(float(action_acc), 4)
    }

def floor_decile(val: float) -> float:
    return int(val * 10) / 10.0

def run_evaluation(limit: int = None, quick: bool = False):
    if not GOLDEN_LABELLED_FILE.exists():
        raise FileNotFoundError(f"Labelled golden set not found at {GOLDEN_LABELLED_FILE}. Please run python -m scripts.label_helper --batch-autofill first.")

    with open(GOLDEN_LABELLED_FILE, 'r', encoding='utf-8') as f:
        golden_data = json.load(f)

    if quick or (limit and limit < len(golden_data)):
        target_limit = limit if limit else 20
        print(f"Running QUICK evaluation mode on {target_limit} golden set examples...")
        golden_data = golden_data[:target_limit]
    else:
        print(f"Running FULL evaluation harness on {len(golden_data)} golden set examples...")

    pipelines = {
        "Trivial Baseline": TrivialBaselineAgent(),
        "Simple Baseline (TF-IDF + Cosine)": SimpleBaselineAgent(),
        "Main LLM Agent (Grounded + Guardrails)": LLMSupportAgent()
    }

    judge = LLMReplyJudge()
    results = {}

    print("\n=======================================================")
    print("        HIVERN EVALUATION HARNESS BENCHMARK RUN        ")
    print("=======================================================\n")

    for name, agent in pipelines.items():
        y_true_intent, y_pred_intent = [], []
        y_true_action, y_pred_action = [], []
        
        judge_scores = {"groundedness": [], "correctness": [], "tone_fit": [], "actionability": [], "overall": []}
        strata_buckets = {}
        confidence_deciles = {i/10.0: {"correct": 0, "total": 0} for i in range(5, 10)}

        for item in golden_data:
            tweet = item["raw_text"]
            t_intent = item["true_intent"]
            t_action = item["true_action"]
            ref_reply = item["brand_reply_actual"]
            stratum = item.get("stratum", "general")

            out = agent.process_message(tweet)
            p_intent = out["intent"]
            p_action = out["action"]
            draft_reply = out["draft_reply"]
            conf = out.get("confidence", 0.50)

            y_true_intent.append(t_intent)
            y_pred_intent.append(p_intent)
            y_true_action.append(t_action)
            y_pred_action.append(p_action)

            # Judge evaluation
            j_eval = judge.evaluate_reply_blinded(tweet, ref_reply, draft_reply)
            judge_scores["groundedness"].append(j_eval["groundedness"])
            judge_scores["correctness"].append(j_eval["correctness"])
            judge_scores["tone_fit"].append(j_eval["tone_fit"])
            judge_scores["actionability"].append(j_eval["actionability"])
            judge_scores["overall"].append(j_eval["overall_score"])

            # Strata breakdown bucket
            if stratum not in strata_buckets:
                strata_buckets[stratum] = {"y_t_int": [], "y_p_int": [], "y_t_act": [], "y_p_act": []}
            strata_buckets[stratum]["y_t_int"].append(t_intent)
            strata_buckets[stratum]["y_p_int"].append(p_intent)
            strata_buckets[stratum]["y_t_act"].append(t_action)
            strata_buckets[stratum]["y_p_act"].append(p_action)

            # Calibration bucket
            bucket = round(floor_decile(conf), 1)
            if bucket in confidence_deciles:
                confidence_deciles[bucket]["total"] += 1
                if p_intent == t_intent:
                    confidence_deciles[bucket]["correct"] += 1

        overall_m = compute_metrics(y_true_intent, y_pred_intent, y_true_action, y_pred_action)

        # Slice level metrics per stratum
        slice_metrics = {}
        for st, data_s in strata_buckets.items():
            slice_metrics[st] = compute_metrics(data_s["y_t_int"], data_s["y_p_int"], data_s["y_t_act"], data_s["y_p_act"])

        results[name] = {
            "overall_metrics": overall_m,
            "judge_rubric_scores": {
                "groundedness": round(float(np.mean(judge_scores["groundedness"])), 2),
                "correctness": round(float(np.mean(judge_scores["correctness"])), 2),
                "tone_fit": round(float(np.mean(judge_scores["tone_fit"])), 2),
                "actionability": round(float(np.mean(judge_scores["actionability"])), 2),
                "overall_judge_score": round(float(np.mean(judge_scores["overall"])), 2)
            },
            "slice_strata_metrics": slice_metrics,
            "calibration_deciles": confidence_deciles
        }

    # Print Headline Markdown Table
    print("\n### HEADLINE BENCHMARK COMPARISON TABLE\n")
    print("| System Pipeline | Primary Metric (Intent Macro-F1) | Intent Accuracy | ESCALATE Recall | ESCALATE F1 | LLM Judge Rubric |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: |")
    for name, r in results.items():
        om = r["overall_metrics"]
        jr = r["judge_rubric_scores"]
        print(f"| **{name}** | **{om['intent_macro_f1']*100:.1f}%** | {om['intent_accuracy']*100:.1f}% | **{om['action_escalate_recall']*100:.1f}%** | {om['action_escalate_f1']*100:.1f}% | **{jr['overall_judge_score']} / 5.0** |")

    # Save metrics.json
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(METRICS_JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nFull metrics saved to {METRICS_JSON_FILE}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Evaluation Harness on Golden Dataset")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of golden set items to evaluate")
    parser.add_argument("--quick", action="store_true", help="Run quick 20-item evaluation smoke test")
    args = parser.parse_args()

    run_evaluation(limit=args.limit, quick=args.quick)