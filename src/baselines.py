import sys
import os
import re
import json
import argparse
from pathlib import Path

# Fix sys.path FIRST before importing project modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity

from src.config import (
    SUBSAMPLE_FILE,
    RANDOM_SEED
)
from intent_taxonomy import INTENT_TAXONOMY, check_mandatory_escalation

class TrivialBaselineAgent:
    """
    Trivial Baseline:
    - Always predicts majority intent ('OTHER_GENERAL')
    - Always predicts majority action ('AUTO_HANDLE')
    - Reply is a fixed canned string.
    """
    def __init__(self, majority_intent: str = "OTHER_GENERAL", majority_action: str = "AUTO_HANDLE"):
        self.majority_intent = majority_intent
        self.majority_action = majority_action
        self.canned_reply = "Sorry to hear that — DM us and we'll help."

    def process_message(self, customer_tweet: str, context: str = "") -> dict:
        return {
            "intent": self.majority_intent,
            "confidence": 0.50,
            "draft_reply": self.canned_reply,
            "action": self.majority_action,
            "reason": "Trivial baseline majority class prediction."
        }

class SimpleBaselineAgent:
    """
    Simple Baseline:
    - Intent: TF-IDF + Logistic Regression trained on subsample
    - Action: Keyword / Regex ruleset for ESCALATE decision
    - Reply: Nearest-neighbour retrieval (TF-IDF cosine similarity) returning actual brand reply
    """
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=2500, stop_words='english', ngram_range=(1, 2))
        self.clf = LogisticRegression(random_state=RANDOM_SEED, max_iter=500)
        self.subsample_data = []
        self.subsample_matrix = None
        self.is_fitted = False
        self._fit_on_subsample()

    def _fit_on_subsample(self):
        if not SUBSAMPLE_FILE.exists():
            print(f"Warning: {SUBSAMPLE_FILE} not found. Baseline running in un-fitted mode.")
            return

        with open(SUBSAMPLE_FILE, 'r', encoding='utf-8') as f:
            self.subsample_data = json.load(f)

        clean_texts = [d.get("clean_text", "") for d in self.subsample_data]
        
        # Pseudo-labels for training logistic regression from keyword taxonomy heuristics
        train_labels = []
        for d in self.subsample_data:
            txt = d.get("clean_text", "").lower()
            intent = "OTHER_GENERAL"
            for it, details in INTENT_TAXONOMY.items():
                if any(kw in txt for kw in details["keywords"]):
                    intent = it
                    break
            train_labels.append(intent)

        # Fit TF-IDF Vectorizer and Logistic Regression
        self.subsample_matrix = self.vectorizer.fit_transform(clean_texts)
        self.clf.fit(self.subsample_matrix, train_labels)
        self.is_fitted = True
        print(f"SimpleBaselineAgent successfully fitted on {len(self.subsample_data)} subsample records.")

    def process_message(self, customer_tweet: str, context: str = "") -> dict:
        if not self.is_fitted or not self.subsample_data:
            return {
                "intent": "OTHER_GENERAL",
                "confidence": 0.50,
                "draft_reply": "Thanks for contacting Apple Support! Please DM us for help.",
                "action": "AUTO_HANDLE",
                "reason": "Unfitted fallback."
            }

        # 1. Intent via TF-IDF + Logistic Regression
        query_vec = self.vectorizer.transform([customer_tweet])
        predicted_intent = self.clf.predict(query_vec)[0]
        probs = self.clf.predict_proba(query_vec)[0]
        confidence = float(np.max(probs))

        # 2. Action via Keyword / Regex Rule Set
        tweet_lower = customer_tweet.lower()
        mandatory_esc, reason_esc = check_mandatory_escalation(customer_tweet)

        # Keyword list for simple baseline escalation rules
        escalate_kws = ["order #", "order number", "serial number", "refund", "charged", "credit card", "apple id", "password", "locked", "hacked", "stolen", "lawyer", "sue", "police", "unauthorized"]
        has_esc_kw = any(kw in tweet_lower for kw in escalate_kws)

        if mandatory_esc:
            action = "ESCALATE"
            reason = reason_esc
        elif has_esc_kw or INTENT_TAXONOMY.get(predicted_intent, {}).get("default_action") == "ESCALATE":
            action = "ESCALATE"
            reason = "Keyword/regex rule triggered escalation."
        else:
            action = "AUTO_HANDLE"
            reason = "Keyword rule set allowed auto-handling."

        # 3. Reply via Nearest-Neighbour Retrieval (TF-IDF Cosine Similarity)
        similarities = cosine_similarity(query_vec, self.subsample_matrix)[0]
        best_idx = int(np.argmax(similarities))
        retrieved_record = self.subsample_data[best_idx]
        draft_reply = retrieved_record.get("brand_reply_actual", "Please check support.apple.com for help.")

        return {
            "intent": predicted_intent,
            "confidence": round(confidence, 2),
            "draft_reply": draft_reply,
            "action": action,
            "reason": reason,
            "retrieved_source_id": retrieved_record.get("id", ""),
            "retrieved_similarity": round(float(similarities[best_idx]), 3)
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Baseline Agents")
    parser.add_argument("--limit", type=int, default=5, help="Number of test tweets to evaluate")
    args = parser.parse_args()

    print("Testing Trivial Baseline Agent:")
    trivial = TrivialBaselineAgent()
    sample_tweet = "@AppleSupport I see an unauthorized charge of $14.99 on my credit card! Refund please."
    print(json.dumps(trivial.process_message(sample_tweet), indent=2))

    print("\nTesting Simple Baseline Agent (TF-IDF + Logistic Regression + Cosine Retrieval):")
    simple = SimpleBaselineAgent()
    print(json.dumps(simple.process_message(sample_tweet), indent=2))