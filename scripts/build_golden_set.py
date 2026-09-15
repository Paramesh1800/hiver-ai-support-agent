import sys
import os
import json
import csv
import re
import random
import argparse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    SUBSAMPLE_FILE,
    GOLDEN_UNLABELLED_FILE,
    RANDOM_SEED
)
from intent_taxonomy import INTENT_TAXONOMY, check_mandatory_escalation

def simple_classify_intent(text: str) -> tuple[str, float]:
    """Keyword intent classifier used for stratification."""
    text_lower = text.lower()
    scores = {intent: 0 for intent in INTENT_TAXONOMY}

    for intent, details in INTENT_TAXONOMY.items():
        for kw in details["keywords"]:
            if kw in text_lower:
                scores[intent] += 2 if len(kw) > 4 else 1

    best_intent = max(scores, key=scores.get)
    max_score = scores[best_intent]

    if max_score == 0:
        return "OTHER_GENERAL", 0.50

    confidence = min(0.95, 0.60 + (max_score * 0.10))
    return best_intent, confidence

def is_emoji_profanity_sarcasm(text: str) -> bool:
    """Detect presence of emoji, profanity, exaggeration, or sarcasm keywords."""
    text_lower = text.lower()
    sarcasm_kws = ["paperweight", "thanks for nothing", "badapple", "sucks", "horrible", "worst", "terrible", "useless", "garbage", "trash"]
    for kw in sarcasm_kws:
        if kw in text_lower:
            return True
    # Check for punctuation intensity or non-ascii / emoji
    if "!!" in text or "??" in text or "!" in text:
        return True
    if any(ord(char) > 127 for char in text):
        return True
    return False

def build_golden_set(limit: int = 200):
    """
    Samples 200 real inbound messages from subsample into golden_set_unlabelled.csv using stratified sampling.
    """
    if not SUBSAMPLE_FILE.exists():
        raise FileNotFoundError(f"Subsample dataset not found at {SUBSAMPLE_FILE}. Please run python -m src.data_prep first.")

    with open(SUBSAMPLE_FILE, 'r', encoding='utf-8') as f:
        threads = json.load(f)

    print(f"Loaded {len(threads)} authentic threads from {SUBSAMPLE_FILE} for golden set sampling.")

    # Annotate candidates with metadata for stratification
    candidates = []
    for item in threads:
        raw_text = item.get("raw_text", "")
        clean_text = item.get("clean_text", "")
        reply = item.get("brand_reply_actual", "")
        
        intent, confidence = simple_classify_intent(raw_text)
        mandatory_esc, _ = check_mandatory_escalation(raw_text)
        is_esc = mandatory_esc or (INTENT_TAXONOMY[intent]["default_action"] == "ESCALATE")
        word_count = len(clean_text.split())
        has_emoji_sarcasm = is_emoji_profanity_sarcasm(raw_text)

        candidates.append({
            "id": item["id"],
            "raw_text": raw_text,
            "clean_text": clean_text,
            "brand_reply_actual": reply,
            "predicted_intent": intent,
            "confidence": confidence,
            "is_escalate": is_esc,
            "word_count": word_count,
            "has_emoji_sarcasm": has_emoji_sarcasm
        })

    random.seed(RANDOM_SEED)
    random.shuffle(candidates)

    selected = []
    selected_ids = set()

    def add_candidate(cand, stratum_name):
        if cand["id"] not in selected_ids and len(selected) < limit:
            selected_ids.add(cand["id"])
            selected.append({
                "id": f"golden_{len(selected)+1:03d}",
                "raw_text": cand["raw_text"],
                "clean_text": cand["clean_text"],
                "stratum": stratum_name,
                "brand_reply_actual": cand["brand_reply_actual"],
                "true_intent": "",
                "true_action": "",
                "notes": ""
            })

    # Target stratum quotas for 200 total limit
    # 30% Pure Random (~60)
    # 70% Stratified Oversampling (~140)
    
    pure_random_target = int(limit * 0.30)
    
    # 1. Sample Pure Random Stratum first (30%)
    for cand in candidates:
        if len([s for s in selected if s["stratum"] == "pure_random"]) >= pure_random_target:
            break
        add_candidate(cand, "pure_random")

    # 2. Stratified Oversample: Low-confidence predictions
    for cand in candidates:
        if cand["confidence"] <= 0.65:
            add_candidate(cand, "stratified_low_confidence")

    # 3. Stratified Oversample: ESCALATE predictions
    for cand in candidates:
        if cand["is_escalate"]:
            add_candidate(cand, "stratified_escalate")

    # 4. Stratified Oversample: Emoji / Sarcasm / Profanity
    for cand in candidates:
        if cand["has_emoji_sarcasm"]:
            add_candidate(cand, "stratified_emoji_profanity")

    # 5. Stratified Oversample: Short messages (<5 words)
    for cand in candidates:
        if cand["word_count"] <= 5:
            add_candidate(cand, "stratified_short")

    # 6. Fill remaining quota by intent coverage
    intent_groups = {intent: [] for intent in INTENT_TAXONOMY}
    for cand in candidates:
        intent_groups[cand["predicted_intent"]].append(cand)

    for intent, group in intent_groups.items():
        for cand in group:
            if len(selected) >= limit:
                break
            add_candidate(cand, f"stratified_intent_{intent.lower()}")

    # Fill any remaining with candidates
    for cand in candidates:
        if len(selected) >= limit:
            break
        add_candidate(cand, "stratified_general")

    print(f"Selected {len(selected)} unlabelled benchmark examples across strata:")
    stratum_counts = {}
    for item in selected:
        st = item["stratum"]
        stratum_counts[st] = stratum_counts.get(st, 0) + 1
    for st, count in stratum_counts.items():
        print(f"  • {st}: {count}")

    # Write to data/golden/golden_set_unlabelled.csv
    GOLDEN_UNLABELLED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(GOLDEN_UNLABELLED_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "raw_text", "clean_text", "stratum", "brand_reply_actual", "true_intent", "true_action", "notes"
        ])
        writer.writeheader()
        writer.writerows(selected)

    print(f"Successfully saved unlabelled golden set to {GOLDEN_UNLABELLED_FILE}")
    return selected

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build unlabelled golden evaluation dataset.")
    parser.add_argument("--limit", type=int, default=200, help="Number of examples in golden set (default 200)")
    args = parser.parse_args()

    build_golden_set(limit=args.limit)