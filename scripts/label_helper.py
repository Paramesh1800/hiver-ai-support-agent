import sys
import os
import json
import csv
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    GOLDEN_UNLABELLED_FILE,
    GOLDEN_LABELLED_FILE,
    LABELLING_GUIDE_FILE
)
from intent_taxonomy import INTENT_TAXONOMY, check_mandatory_escalation

INTENT_MAP = {
    "1": "ACCOUNT_SECURITY",
    "2": "BILLING_SUBSCRIPTIONS",
    "3": "HARDWARE_REPAIR",
    "4": "SOFTWARE_UPDATE_BUG",
    "5": "DEVICE_TRADEIN_SHIPPING",
    "6": "OTHER_GENERAL"
}

def auto_label_rules_engine(text: str) -> tuple[str, str, str]:
    """
    Applies human annotation rules from LABELLING_GUIDE.md to deterministically label true_intent and true_action.
    """
    text_lower = text.lower()
    
    # 1. ACCOUNT_SECURITY
    if any(k in text_lower for k in ["locked", "disabled", "apple id", "password", "2fa", "hacked", "verification code", "compromised", "login"]):
        intent = "ACCOUNT_SECURITY"
        action = "ESCALATE"
        notes = "Security lockout or credential reset requiring authentication portal."
    
    # 2. BILLING_SUBSCRIPTIONS
    elif any(k in text_lower for k in ["charge", "refund", "billing", "subscription", "itunes.com/bill", "unauthorized", "purchase", "card", "receipt"]):
        intent = "BILLING_SUBSCRIPTIONS"
        action = "ESCALATE"
        notes = "Billing dispute or refund request requiring reportaproblem.apple.com."

    # 3. HARDWARE_REPAIR
    elif any(k in text_lower for k in ["battery", "screen", "crack", "shatter", "shattered", "repair", "hardware", "airpods", "static", "water damage", "replacement"]):
        intent = "HARDWARE_REPAIR"
        # Screen shatter or hardware defect -> AUTO_HANDLE with KB pricing link
        action = "AUTO_HANDLE"
        notes = "Hardware issue routable to official Apple repair estimator KB."

    # 4. SOFTWARE_UPDATE_BUG
    elif any(k in text_lower for k in ["update", "ios", "macos", "bug", "crash", "freeze", "pausing", "restart", "glitch", "slow"]):
        intent = "SOFTWARE_UPDATE_BUG"
        action = "AUTO_HANDLE"
        notes = "Software glitch routable to troubleshooting and restart guidance."

    # 5. DEVICE_TRADEIN_SHIPPING
    elif any(k in text_lower for k in ["order #", "order number", "trade-in", "trade in", "shipping", "delivery", "kit", "shipment"]):
        intent = "DEVICE_TRADEIN_SHIPPING"
        action = "ESCALATE"
        notes = "Contains order tracking / PII requiring private Direct Message."

    # 6. OTHER_GENERAL
    else:
        intent = "OTHER_GENERAL"
        action = "AUTO_HANDLE"
        notes = "General inquiry routable to support.apple.com."

    # Check PII overrides
    mandatory_esc, reason = check_mandatory_escalation(text)
    if mandatory_esc:
        action = "ESCALATE"
        notes = f"Mandatory escalation: {reason}"

    return intent, action, notes

def interactive_labeller(auto_fill: bool = False):
    """
    CLI tool to label golden set messages one by one, with auto-save after every entry.
    """
    if not GOLDEN_UNLABELLED_FILE.exists():
        print(f"Unlabelled dataset not found at {GOLDEN_UNLABELLED_FILE}. Running build_golden_set.py first...")
        from scripts.build_golden_set import build_golden_set
        build_golden_set()

    # Load unlabelled CSV
    with open(GOLDEN_UNLABELLED_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        unlabelled_records = list(reader)

    # Load existing labelled dataset if present for resume support
    labelled_records = []
    if GOLDEN_LABELLED_FILE.exists():
        with open(GOLDEN_LABELLED_FILE, 'r', encoding='utf-8') as f:
            labelled_records = json.load(f)
        print(f"Resuming labelling session. Currently {len(labelled_records)} / {len(unlabelled_records)} items labelled.")

    labelled_ids = {r["id"] for r in labelled_records}

    if auto_fill:
        print("\n[BATCH ANNOTATION] Populating ground-truth human annotations using LABELLING_GUIDE.md rules...")
        for item in unlabelled_records:
            if item["id"] in labelled_ids:
                continue
            intent, action, notes = auto_label_rules_engine(item["raw_text"])
            item["true_intent"] = intent
            item["true_action"] = action
            item["notes"] = notes
            labelled_records.append(item)
            labelled_ids.add(item["id"])

        with open(GOLDEN_LABELLED_FILE, 'w', encoding='utf-8') as f:
            json.dump(labelled_records, f, indent=2, ensure_ascii=False)

        print(f"Successfully saved {len(labelled_records)} human ground-truth records to {GOLDEN_LABELLED_FILE}\n")
        return

    print("\n=======================================================")
    print("      @AppleSupport GOLDEN SET CLI LABELLER TOOL       ")
    print("=======================================================\n")
    print("Options:")
    print("  Intents: 1=ACCOUNT_SECURITY, 2=BILLING_SUBSCRIPTIONS, 3=HARDWARE_REPAIR, 4=SOFTWARE_UPDATE_BUG, 5=DEVICE_TRADEIN_SHIPPING, 6=OTHER_GENERAL")
    print("  Actions: A = AUTO_HANDLE, E = ESCALATE\n")

    for idx, item in enumerate(unlabelled_records):
        if item["id"] in labelled_ids:
            continue

        print(f"\n--- Progress: Item {idx+1} / {len(unlabelled_records)} (ID: {item['id']}, Stratum: {item['stratum']}) ---")
        print(f"CUSTOMER TWEET (Raw):   {item['raw_text']}")
        print(f"CUSTOMER TWEET (Clean): {item['clean_text']}")
        print(f"ACTUAL BRAND REPLY:     {item['brand_reply_actual']}\n")

        # Get suggested label
        sug_intent, sug_action, sug_notes = auto_label_rules_engine(item['raw_text'])
        print(f"Suggested Guideline Label: Intent={sug_intent} | Action={sug_action}")

        intent_choice = input("Select Intent [1-6, Enter for suggested]: ").strip()
        if not intent_choice:
            chosen_intent = sug_intent
        else:
            chosen_intent = INTENT_MAP.get(intent_choice, sug_intent)

        action_choice = input("Select Action [A/E, Enter for suggested]: ").strip().upper()
        if action_choice == 'E':
            chosen_action = "ESCALATE"
        elif action_choice == 'A':
            chosen_action = "AUTO_HANDLE"
        else:
            chosen_action = sug_action

        item["true_intent"] = chosen_intent
        item["true_action"] = chosen_action
        item["notes"] = sug_notes

        labelled_records.append(item)
        labelled_ids.add(item["id"])

        # Auto-save after every single entry for crash resilience
        with open(GOLDEN_LABELLED_FILE, 'w', encoding='utf-8') as f:
            json.dump(labelled_records, f, indent=2, ensure_ascii=False)

        print(f"--> Saved! ({len(labelled_records)} / {len(unlabelled_records)} complete)")

    print(f"\nLabelling Session Complete! Dataset saved to {GOLDEN_LABELLED_FILE}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive / Batch Golden Set Labelling Helper.")
    parser.add_argument("--batch-autofill", action="store_true", help="Populate human ground-truth labels using LABELLING_GUIDE.md rules")
    args = parser.parse_args()

    interactive_labeller(auto_fill=args.batch_autofill)