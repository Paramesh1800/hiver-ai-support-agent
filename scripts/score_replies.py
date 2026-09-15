import sys
import os
import io
import json
import random
import argparse
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    GOLDEN_LABELLED_FILE,
    RESULTS_DIR,
    RANDOM_SEED
)
from src.baselines import TrivialBaselineAgent, SimpleBaselineAgent
from src.agent import LLMSupportAgent

HUMAN_SCORES_FILE = RESULTS_DIR / "human_scores.json"

def prompt_score_axis(axis_name: str, description: str) -> int:
    """Prompts live terminal input for an integer 1-5. Strictly no default or placeholder allowed."""
    while True:
        inp = input(f"Score {axis_name} (1-5) [{description}]: ").strip()
        if inp in ["1", "2", "3", "4", "5"]:
            return int(inp)
        print("❌ Invalid input! Must be an integer between 1 and 5 (1 = Terrible/Wrong, 5 = Excellent).")

def run_score_replies(sample_size: int = 50):
    if not GOLDEN_LABELLED_FILE.exists():
        print(f"Error: Golden labelled dataset not found at {GOLDEN_LABELLED_FILE}.")
        print("Please complete golden set labelling first: python -m scripts.label_helper")
        sys.exit(1)

    with open(GOLDEN_LABELLED_FILE, 'r', encoding='utf-8') as f:
        golden_data = json.load(f)

    # Deterministic 50-item sample using fixed RANDOM_SEED
    random.seed(RANDOM_SEED)
    sample_indices = random.sample(range(len(golden_data)), min(sample_size, len(golden_data)))
    sample_data = [golden_data[i] for i in sample_indices]

    # Instantiate pipelines to generate blinded candidate replies
    trivial_agent = TrivialBaselineAgent()
    simple_agent = SimpleBaselineAgent()
    main_agent = LLMSupportAgent()

    # Pre-generate candidate replies for blinded presentation
    candidate_items = []
    for idx, item in enumerate(sample_data):
        tweet = item["raw_text"]
        ref_reply = item["brand_reply_actual"]
        item_id = item["id"]

        out_t = trivial_agent.process_message(tweet)["draft_reply"]
        out_s = simple_agent.process_message(tweet)["draft_reply"]
        out_m = main_agent.process_message(tweet)["draft_reply"]

        # Randomly select ONE draft reply per item for blinded scoring
        choices = [out_t, out_s, out_m]
        chosen_reply = choices[idx % len(choices)]

        candidate_items.append({
            "id": item_id,
            "raw_text": tweet,
            "clean_text": item["clean_text"],
            "brand_reply_actual": ref_reply,
            "candidate_draft_reply": chosen_reply
        })

    # Resumability check: load existing human scores
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    existing_scores = {}
    if HUMAN_SCORES_FILE.exists():
        try:
            with open(HUMAN_SCORES_FILE, 'r', encoding='utf-8') as f:
                existing_scores = json.load(f)
        except Exception:
            existing_scores = {}

    total_target = len(candidate_items)

    print("\n=======================================================")
    print("    @AppleSupport MANUAL REPLY RUBRIC SCORING CLI      ")
    print("=======================================================")
    print(f"Target Sample: {total_target} blinded candidate replies")
    print(f"Already Scored: {len(existing_scores)} / {total_target}")
    print("Press Ctrl+C to pause and exit. Progress is saved after EVERY item.\n")

    for idx, item in enumerate(candidate_items):
        item_id = item["id"]
        if item_id in existing_scores:
            continue

        os.system('cls' if os.name == 'nt' else 'clear')
        print("=======================================================")
        print(f" PROGRESS: Scored {len(existing_scores)} / {total_target} items (Item ID: {item_id})")
        print("=======================================================\n")
        print(f"CUSTOMER RAW QUERY:\n  \"{item['raw_text']}\"\n")
        print(f"REFERENCE HISTORICAL BRAND REPLY:\n  \"{item['brand_reply_actual']}\"\n")
        print(f"CANDIDATE DRAFT REPLY TO EVALUATE (BLINDED):\n  \"{item['candidate_draft_reply']}\"\n")
        print("-------------------------------------------------------")
        print("RUBRIC GUIDELINES (1 = Terrible, 3 = Average, 5 = Excellent):")
        print("  1. Groundedness: Correctly grounded in official KB / DM escalation?")
        print("  2. Correctness: Factually accurate with zero invented links/policies?")
        print("  3. Tone Fit: Matches empathetic, professional @AppleSupport voice?")
        print("  4. Actionability: Provides concrete, clear next step for customer?")
        print("-------------------------------------------------------\n")

        # Prompt each axis individually with strict live terminal validation
        g = prompt_score_axis("Groundedness", "1-5")
        c = prompt_score_axis("Correctness", "1-5")
        t = prompt_score_axis("Tone Fit", "1-5")
        a = prompt_score_axis("Actionability", "1-5")

        overall = round((g + c + t + a) / 4.0, 2)

        existing_scores[item_id] = {
            "id": item_id,
            "raw_text": item["raw_text"],
            "brand_reply_actual": item["brand_reply_actual"],
            "candidate_draft_reply": item["candidate_draft_reply"],
            "groundedness": g,
            "correctness": c,
            "tone_fit": t,
            "actionability": a,
            "overall_score": overall
        }

        # INCREMENTAL SAVE: Save to disk after every single item
        with open(HUMAN_SCORES_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_scores, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Item {item_id} scored & saved! ({len(existing_scores)} / {total_target} complete)")

    print(f"\n🎉 ALL {total_target} ITEMS MANUALLY SCORED!")
    print(f"Human rubric scores saved to: {HUMAN_SCORES_FILE}\n")

if __name__ == "__main__":
    try:
        run_score_replies()
    except KeyboardInterrupt:
        print("\n\nPaused scoring session. Your progress was saved to disk.")
        sys.exit(0)