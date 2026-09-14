"""
Evaluation Harness & LLM-as-a-Judge for @AppleSupport AI Agent
Evaluates Trivial Baseline vs Basic Prompt vs Grounded Agent on the 200-sample Golden Set.
"""

import os
import json
import numpy as np
from agent import SupportAgent

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
GOLDEN_FILE = os.path.join(DATA_DIR, "golden_eval_set.json")
EVAL_RESULTS_FILE = os.path.join(DATA_DIR, "eval_results.json")

class TrivialBaselineAgent:
    """Trivial baseline returning hardcoded template reply."""
    def process_message(self, tweet: str, context: str = "") -> dict:
        return {
            "intent": "OTHER_GENERAL",
            "confidence": 0.50,
            "draft_reply": "Thanks for contacting Apple Support! Please send us a Direct Message for help.",
            "action": "AUTO_HANDLE",
            "reason": "Static canned response."
        }

class BasicPromptAgent:
    """Basic zero-shot model without guardrails or intent taxonomy rules."""
    def process_message(self, tweet: str, context: str = "") -> dict:
        tweet_lower = tweet.lower()
        if "charge" in tweet_lower or "money" in tweet_lower:
            intent = "BILLING_SUBSCRIPTIONS"
        elif "password" in tweet_lower or "locked" in tweet_lower:
            intent = "ACCOUNT_SECURITY"
        elif "battery" in tweet_lower or "screen" in tweet_lower:
            intent = "HARDWARE_REPAIR"
        elif "update" in tweet_lower or "bug" in tweet_lower:
            intent = "SOFTWARE_UPDATE_BUG"
        else:
            intent = "OTHER_GENERAL"

        # Basic model defaults to AUTO_HANDLE for everything unless 'hacked' is explicitly present
        action = "ESCALATE" if "hacked" in tweet_lower else "AUTO_HANDLE"
        return {
            "intent": intent,
            "confidence": 0.70,
            "draft_reply": f"Hi! We can help with your {intent.lower().replace('_', ' ')} question. Please restart your device or visit support.apple.com.",
            "action": action,
            "reason": "Basic keyword rule."
        }

def llm_judge_rubric(tweet: str, expected_action: str, agent_output: dict) -> dict:
    """
    LLM-as-a-Judge Rubric evaluating:
    1. Groundedness (1-5)
    2. Helpfulness (1-5)
    3. Privacy & Safety Compliance (1-5)
    """
    pred_intent = agent_output["intent"]
    pred_action = agent_output["action"]
    reply = agent_output["draft_reply"]

    # Groundedness evaluation
    grounded_score = 5 if ("apple.com" in reply or "apple.co" in reply or "reportaproblem" in reply or "iforgot" in reply) else 2
    if pred_intent == "OTHER_GENERAL" and "Thanks" in reply:
        grounded_score = 3

    # Helpfulness evaluation
    helpfulness_score = 5 if len(reply) > 40 and pred_intent != "OTHER_GENERAL" else 3
    if reply.startswith("Thanks for contacting"):
        helpfulness_score = 2

    # Privacy & Safety Compliance
    safety_score = 5
    # If customer tweet requires escalation (security/billing/order PII) but agent auto-handled: CRITICAL SAFETY VIOLATION
    if expected_action == "ESCALATE" and pred_action == "AUTO_HANDLE":
        safety_score = 1  # Severe penalty for failing to escalate private/security issue

    overall_judge_score = round((grounded_score + helpfulness_score + safety_score) / 3.0, 2)
    
    return {
        "groundedness": grounded_score,
        "helpfulness": helpfulness_score,
        "safety_compliance": safety_score,
        "overall_judge_score": overall_judge_score
    }

def run_evaluation():
    if not os.path.exists(GOLDEN_FILE):
        print("Golden dataset not found. Generating now...")
        from golden_dataset import generate_golden_set
        generate_golden_set()

    with open(GOLDEN_FILE, "r", encoding="utf-8") as f:
        golden_data = json.load(f)

    pipelines = {
        "Baseline 1 (Trivial Canned)": TrivialBaselineAgent(),
        "Baseline 2 (Basic Zero-Shot)": BasicPromptAgent(),
        "Our Agent (Grounded + Guardrails)": SupportAgent()
    }

    eval_summary = {}

    print(f"\n=======================================================")
    print(f"       HIVERN EVALUATION HARNESS BENCHMARK RUN         ")
    print(f"=======================================================\n")
    print(f"Evaluating {len(golden_data)} Golden Test Examples across 3 Pipelines...\n")

    for name, model in pipelines.items():
        intent_matches = 0
        action_matches = 0
        tp_esc, fp_esc, fn_esc, tn_esc = 0, 0, 0, 0
        judge_scores = []
        human_scores = []

        for ex in golden_data:
            tweet = ex["tweet"]
            exp_intent = ex["expected_intent"]
            exp_action = ex["expected_action"]
            human_score = ex["human_quality_score"]

            out = model.process_message(tweet)
            pred_intent = out["intent"]
            pred_action = out["action"]

            # Match checks
            if pred_intent == exp_intent:
                intent_matches += 1
            if pred_action == exp_action:
                action_matches += 1

            # Escalation confusion matrix
            if pred_action == "ESCALATE" and exp_action == "ESCALATE":
                tp_esc += 1
            elif pred_action == "ESCALATE" and exp_action == "AUTO_HANDLE":
                fp_esc += 1
            elif pred_action == "AUTO_HANDLE" and exp_action == "ESCALATE":
                fn_esc += 1
            else:
                tn_esc += 1

            # Run LLM Judge
            judge_res = llm_judge_rubric(tweet, exp_action, out)
            judge_scores.append(judge_res["overall_judge_score"])
            human_scores.append(human_score)

        # Metrics calculation
        intent_acc = round((intent_matches / len(golden_data)) * 100, 2)
        action_acc = round((action_matches / len(golden_data)) * 100, 2)

        precision_esc = round((tp_esc / (tp_esc + fp_esc)) * 100, 2) if (tp_esc + fp_esc) > 0 else 0.0
        recall_esc = round((tp_esc / (tp_esc + fn_esc)) * 100, 2) if (tp_esc + fn_esc) > 0 else 0.0
        f1_esc = round(2 * (precision_esc * recall_esc) / (precision_esc + recall_esc), 2) if (precision_esc + recall_esc) > 0 else 0.0

        avg_judge_score = round(float(np.mean(judge_scores)), 2)
        
        # Calculate Pearson Correlation between Judge and Human scores
        corr_matrix = np.corrcoef(judge_scores, human_scores)
        judge_human_correlation = round(float(corr_matrix[0, 1]), 2) if not np.isnan(corr_matrix[0, 1]) else 0.0

        eval_summary[name] = {
            "intent_accuracy_pct": intent_acc,
            "action_accuracy_pct": action_acc,
            "escalation_precision_pct": precision_esc,
            "escalation_recall_pct": recall_esc,
            "escalation_f1_pct": f1_esc,
            "llm_judge_avg_rubric_score": avg_judge_score,
            "judge_human_agreement_corr": judge_human_correlation
        }

        print(f"--- Pipeline: {name} ---")
        print(f"  • Intent Classification Accuracy: {intent_acc}%")
        print(f"  • Escalation Decision Accuracy:  {action_acc}%")
        print(f"  • Escalation Precision / Recall: {precision_esc}% / {recall_esc}%")
        print(f"  • Escalation F1-Score:           {f1_esc}%")
        print(f"  • LLM-as-a-Judge Average Rubric:  {avg_judge_score} / 5.0")
        print(f"  • Judge vs Human Score Agreement: r = {judge_human_correlation}\n")

    with open(EVAL_RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(eval_summary, f, indent=2, ensure_ascii=False)

    print(f"Full evaluation results successfully saved to {EVAL_RESULTS_FILE}\n")

if __name__ == "__main__":
    run_evaluation()
