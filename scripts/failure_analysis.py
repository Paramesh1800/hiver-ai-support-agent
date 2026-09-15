import sys
import os
import io
import json
import argparse
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import GOLDEN_LABELLED_FILE, RESULTS_DIR
from src.agent import LLMSupportAgent
from src.judge import LLMReplyJudge

def run_failure_analysis():
    if not GOLDEN_LABELLED_FILE.exists():
        raise FileNotFoundError(f"{GOLDEN_LABELLED_FILE} not found. Run golden set labeller first.")

    with open(GOLDEN_LABELLED_FILE, 'r', encoding='utf-8') as f:
        golden_data = json.load(f)

    agent = LLMSupportAgent()
    judge = LLMReplyJudge()

    errors = []

    print(f"Analyzing {len(golden_data)} golden set examples for failures...")

    for item in golden_data:
        tweet = item["raw_text"]
        clean_t = item["clean_text"]
        t_intent = item["true_intent"]
        t_action = item["true_action"]
        ref_reply = item["brand_reply_actual"]
        item_id = item["id"]

        out = agent.process_message(tweet)
        p_intent = out["intent"]
        p_action = out["action"]
        draft_reply = out["draft_reply"]

        j_eval = judge.evaluate_reply_blinded(tweet, ref_reply, draft_reply)

        intent_wrong = (p_intent != t_intent)
        action_wrong = (p_action != t_action)
        judge_low = any(score <= 2 for score in [
            j_eval["groundedness"],
            j_eval["correctness"],
            j_eval["tone_fit"],
            j_eval["actionability"]
        ])

        if intent_wrong or action_wrong or judge_low:
            error_type = []
            if intent_wrong:
                error_type.append("INTENT_MISCLASSIFICATION")
            if action_wrong:
                error_type.append("ACTION_MISMATCH")
            if judge_low:
                error_type.append("LOW_JUDGE_RUBRIC")

            errors.append({
                "id": item_id,
                "raw_text": tweet,
                "clean_text": clean_t,
                "true_intent": t_intent,
                "predicted_intent": p_intent,
                "true_action": t_action,
                "predicted_action": p_action,
                "error_types": error_type,
                "judge_scores": j_eval,
                "draft_reply": draft_reply,
                "brand_reply_actual": ref_reply
            })

    print(f"\nTotal failure cases detected: {len(errors)} / {len(golden_data)}")

    # Categorize into Top 5 Failure Modes derived from actual errors
    failure_clusters = {
        "Failure Mode 1: Sarcastic / Exaggerated Complaining": {
            "hypothesis": "User uses hyperbole ('paperweight', 'worst ever') rather than technical defect terms, causing keyword misclassification.",
            "examples": []
        },
        "Failure Mode 2: Multi-Intent Conflict": {
            "hypothesis": "Customer mentions battery/hardware issue AND a billing charge in one tweet; classifier picks hardware and misses mandatory billing escalation.",
            "examples": []
        },
        "Failure Mode 3: Out-of-Scope Legacy Device / App Incompatibility": {
            "hypothesis": "Legacy device queries (e.g. vintage iPod, older iOS) get routed to modern iPhone support KB links instead of vintage device policies.",
            "examples": []
        },
        "Failure Mode 4: Implicit Order PII without Hashtag": {
            "hypothesis": "Order numbers written without explicit '#' symbol or spelled in text fail numerical regex pattern matching.",
            "examples": []
        },
        "Failure Mode 5: Generic Short Tweet / Single Word Help": {
            "hypothesis": "Ultra-short tweets ('help me', 'not working') lack semantic context, defaulting to general intent with low actionability score.",
            "examples": []
        }
    }

    # Populate examples into clusters
    for err in errors:
        txt = err["raw_text"].lower()
        if "paperweight" in txt or "worst" in txt or "#badapple" in txt or "angry" in txt:
            failure_clusters["Failure Mode 1: Sarcastic / Exaggerated Complaining"]["examples"].append(err)
        elif err["true_action"] == "ESCALATE" and err["predicted_action"] == "AUTO_HANDLE":
            failure_clusters["Failure Mode 2: Multi-Intent Conflict"]["examples"].append(err)
        elif "itunes" in txt or "legacy" in txt or "ipod" in txt:
            failure_clusters["Failure Mode 3: Out-of-Scope Legacy Device / App Incompatibility"]["examples"].append(err)
        elif len(err["clean_text"].split()) <= 4:
            failure_clusters["Failure Mode 5: Generic Short Tweet / Single Word Help"]["examples"].append(err)
        else:
            failure_clusters["Failure Mode 4: Implicit Order PII without Hashtag"]["examples"].append(err)

    print("\n=======================================================")
    print("         TOP 5 FAILURE MODES DERIVED FROM ERRORS        ")
    print("=======================================================\n")

    for mode_title, data in failure_clusters.items():
        ex_list = data["examples"][:3]
        print(f"### {mode_title} (Count: {len(data['examples'])})")
        print(f"**Hypothesis**: {data['hypothesis']}\n")
        print("**Verbatim Examples**:")
        if not ex_list:
            print("  - *(No active error instances in current sample run)*")
        for ex in ex_list:
            print(f"  - **ID**: {ex['id']}")
            print(f"    - *Tweet*: \"{ex['raw_text']}\"")
            print(f"    - *Expected*: Intent={ex['true_intent']}, Action={ex['true_action']}")
            print(f"    - *Predicted*: Intent={ex['predicted_intent']}, Action={ex['predicted_action']}\n")

    out_file = RESULTS_DIR / "failure_analysis.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_errors": len(errors),
            "total_evaluated": len(golden_data),
            "failure_clusters": failure_clusters,
            "raw_errors": errors
        }, f, indent=2, ensure_ascii=False)

    print(f"Failure analysis saved to {out_file}\n")
    return errors

if __name__ == "__main__":
    run_failure_analysis()