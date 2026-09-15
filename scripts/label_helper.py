import sys
import os
import io
import json
import csv
import argparse
from pathlib import Path

# Wrap stdout for cross-platform terminal compatibility
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    GOLDEN_UNLABELLED_FILE,
    GOLDEN_LABELLED_FILE,
    LABELLING_GUIDE_FILE
)
from intent_taxonomy import INTENT_TAXONOMY

INTENT_MENU = {
    "1": "ACCOUNT_SECURITY",
    "2": "BILLING_SUBSCRIPTIONS",
    "3": "HARDWARE_REPAIR",
    "4": "SOFTWARE_UPDATE_BUG",
    "5": "DEVICE_TRADEIN_SHIPPING",
    "6": "OTHER_GENERAL"
}

def run_label_helper():
    """
    Interactive CLI tool for live human labelling of the Golden Evaluation Set.
    Requires live terminal input for every single entry. Zero placeholders or default values.
    Saves to disk after every single item for 100% crash resilience and resumability.
    """
    if not GOLDEN_UNLABELLED_FILE.exists():
        print(f"Error: Unlabelled dataset not found at {GOLDEN_UNLABELLED_FILE}.")
        print("Please run: python -m scripts.build_golden_set first.")
        sys.exit(1)

    with open(GOLDEN_UNLABELLED_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        unlabelled_records = list(reader)

    total_count = len(unlabelled_records)

    # Resume capability: check existing labelled records
    labelled_records = []
    if GOLDEN_LABELLED_FILE.exists():
        try:
            with open(GOLDEN_LABELLED_FILE, 'r', encoding='utf-8') as f:
                labelled_records = json.load(f)
        except Exception:
            labelled_records = []

    labelled_ids = {r["id"] for r in labelled_records}

    print("\n=======================================================")
    print("   @AppleSupport GOLDEN SET MANUAL LABELLING TOOL CLI   ")
    print("=======================================================")
    print(f"Loaded {total_count} items from {GOLDEN_UNLABELLED_FILE}")
    print(f"Already labelled: {len(labelled_records)} / {total_count}")
    print("Press Ctrl+C at any time to pause and exit. Progress is saved after EVERY item.\n")

    for idx, item in enumerate(unlabelled_records):
        item_id = item["id"]
        if item_id in labelled_ids:
            continue

        os.system('cls' if os.name == 'nt' else 'clear')
        print("=======================================================")
        print(f" PROGRESS: Labelled {len(labelled_records)} / {total_count} items (Item ID: {item_id})")
        print(f" Stratum:  {item.get('stratum', 'general')}")
        print("=======================================================\n")
        print(f"RAW CUSTOMER TWEET:\n  \"{item['raw_text']}\"\n")
        print(f"CLEAN TWEET TEXT:\n  \"{item['clean_text']}\"\n")
        print(f"ACTUAL HISTORICAL BRAND REPLY (For Context):\n  \"{item['brand_reply_actual']}\"\n")
        print("-------------------------------------------------------")
        print("INTENT MENU:")
        print("  [1] ACCOUNT_SECURITY        (Apple ID lockout, 2FA, password reset)")
        print("  [2] BILLING_SUBSCRIPTIONS   (Card charge, refund, iTunes billing)")
        print("  [3] HARDWARE_REPAIR         (Battery drain, screen crack, AirPods static)")
        print("  [4] SOFTWARE_UPDATE_BUG     (iOS/macOS bug, crash, freeze, storage calc)")
        print("  [5] DEVICE_TRADEIN_SHIPPING (Order tracking, trade-in kit delay)")
        print("  [6] OTHER_GENERAL           (How-to setup, Move to iOS, store hours)")
        print("-------------------------------------------------------")

        # 1. Prompt Intent (Strict Validation - No default / placeholder allowed)
        chosen_intent = None
        while chosen_intent is None:
            inp = input("Select Intent Number [1-6]: ").strip()
            if inp in INTENT_MENU:
                chosen_intent = INTENT_MENU[inp]
            else:
                print("❌ Invalid input! Please enter an integer between 1 and 6.")

        # 2. Prompt Action (Strict Validation - No default / placeholder allowed)
        chosen_action = None
        while chosen_action is None:
            act_inp = input("Select Action [A = AUTO_HANDLE, E = ESCALATE]: ").strip().upper()
            if act_inp == 'A':
                chosen_action = "AUTO_HANDLE"
            elif act_inp == 'E':
                chosen_action = "ESCALATE"
            else:
                print("❌ Invalid input! Please type 'A' for AUTO_HANDLE or 'E' for ESCALATE.")

        # 3. Optional Note Field
        note_inp = input("Optional Note (Press Enter to skip): ").strip()

        record_entry = {
            "id": item_id,
            "raw_text": item["raw_text"],
            "clean_text": item["clean_text"],
            "stratum": item.get("stratum", "general"),
            "brand_reply_actual": item["brand_reply_actual"],
            "true_intent": chosen_intent,
            "true_action": chosen_action,
            "notes": note_inp
        }

        labelled_records.append(record_entry)
        labelled_ids.add(item_id)

        # INCREMENTAL SAVE: Save after every single entry to guarantee zero data loss
        GOLDEN_LABELLED_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(GOLDEN_LABELLED_FILE, 'w', encoding='utf-8') as f:
            json.dump(labelled_records, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Item {item_id} saved! ({len(labelled_records)} / {total_count} complete)")

    print(f"\n🎉 ALL {total_count} GOLDEN SET ITEMS HAVE BEEN MANUALLY LABELLED!")
    print(f"Labelled dataset saved to: {GOLDEN_LABELLED_FILE}\n")

if __name__ == "__main__":
    try:
        run_label_helper()
    except KeyboardInterrupt:
        print("\n\nPaused labelling session. Your progress was saved to disk.")
        sys.exit(0)